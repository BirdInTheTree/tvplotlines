#!/usr/bin/env python3
"""Least-to-Most decomposition experiment: GOT S01.

Runs 4 conditions comparing different decomposition levels:
  A (vanilla, 1 pass)  — read from existing file
  B (2-pass)           — merged format+plotlines → per-episode events
  C (3-pass)           — tvplotlines pipeline with --skip-review
  D (4-pass, full)     — read from existing file

Metrics:
  Coverage:     fraction of synopsis sentences reflected in events (word overlap >30%)
  Arc:          mean fraction of 7 narrative functions covered per plotline
  Coh_sep:      embedding-based cohesion-separation score (excluding case_of_the_week)
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from openai import OpenAI

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT = Path(__file__).resolve().parent.parent.parent
EXPERIMENT = PROJECT / "experiments" / "least-to-most"
SYNOPSES_DIR = Path(
    os.environ.get(
        "SYNOPSES_DIR",
        str(Path.home() / "Projects/1-projects/tvplotlines-app/data/synopses"),
    )
)

VANILLA_PATH = PROJECT / "experiments" / "vanilla-vs-pipeline" / "got_vanilla.json"
FOURPASS_PATH = Path.home() / "Projects/1-projects/tvplotlines-app/data/results/got_s01_result.json"

TWOPASS_RESULT = EXPERIMENT / "got_2pass_result.json"
TWOPASS_METRICS = EXPERIMENT / "got_2pass_metrics.json"
THREEPASS_RESULT = EXPERIMENT / "got_3pass_result.json"
THREEPASS_METRICS = EXPERIMENT / "got_3pass_metrics.json"

ALL_FUNCTIONS = {"setup", "inciting_incident", "escalation", "turning_point", "crisis", "climax", "resolution"}

# ---------------------------------------------------------------------------
# Synopsis loading
# ---------------------------------------------------------------------------

def load_synopses() -> dict[str, str]:
    """Load GOT S01 synopses, keyed by episode ID."""
    synopses = {}
    for p in sorted(SYNOPSES_DIR.glob("GOT_S01E*.txt")):
        match = re.search(r"S\d{2}E\d{2}", p.stem)
        if match:
            synopses[match.group()] = p.read_text(encoding="utf-8")
    return synopses


# ---------------------------------------------------------------------------
# Condition B: 2-pass pipeline
# ---------------------------------------------------------------------------

_STAGE1_SYSTEM = """You are a story editor. You receive synopses for a full season of a TV show.

Your task: analyze the synopses and produce a single JSON response with:
1. Series format classification (serial/procedural/hybrid/limited), is_ensemble flag, and story_engine.
2. Main cast members.
3. Plotlines with full Story DNA (hero, goal, obstacle, stakes), type (serialized/case_of_the_week/runner), rank (A/B/C/null for runners), nature, and confidence.

## Plotline naming
- Use "Hero: Theme" format for names (e.g. "Ned: Honor")
- id = one snake_case word matching the theme

## Story DNA
Every plotline: hero (who drives it) + goal (what they want) + obstacle (what blocks them) + stakes (what happens if they fail).

## Types
- serialized: spans multiple episodes
- case_of_the_week: opens and closes within one episode
- runner: minor recurring thread, incomplete DNA

## Ranks
- A: the plotline the series is about
- B: second in importance
- C: third, lighter
- null: for runners only

## Nature
- plot-led: external antagonist
- character-led: hero IS the problem
- theme-led: systemic problem

## Confidence
- solid: full Story DNA clear
- partial: hero and goal clear, rest unclear
- inferred: plotline implied, structure incomplete

## is_ensemble
- true if no single protagonist, 2+ A-rank plotlines

Response — strictly JSON, no markdown wrapping:
{
  "format": "serial",
  "is_ensemble": true,
  "story_engine": "...",
  "cast": [{"id": "...", "name": "...", "aliases": [...]}],
  "plotlines": [
    {
      "id": "...", "name": "Hero: Theme", "hero": "cast_id",
      "goal": "...", "obstacle": "...", "stakes": "...",
      "type": "serialized", "rank": "A", "nature": "character-led",
      "confidence": "solid"
    }
  ]
}"""

_STAGE2_SYSTEM = """You are a story editor breaking down a single episode scene by scene.

You receive: show title, season, format, story_engine, cast, plotlines with Story DNA, and one episode synopsis.

## Event
One action that changes the situation. Be specific: include character names, what happens, dramatic consequence.

## Function
Each event's position in the plotline's dramatic structure:
- setup: introduces the plotline, status quo
- inciting_incident: the event that starts the plotline (one per plotline, does not repeat)
- escalation: raises stakes (can repeat)
- turning_point: changes direction
- crisis: lowest point, true dilemma
- climax: peak of conflict, irreversible outcome
- resolution: conflict resolved, aftermath

## Characters
Use cast ids. For guests use "guest:short_name".

## also_affects
If an event primarily belongs to one plotline but also advances another, list the secondary plotline ids.

Response — strictly JSON, no markdown wrapping:
{
  "episode": "S01E01",
  "events": [
    {
      "event": "description",
      "plotline": "plotline_id",
      "function": "setup",
      "characters": ["cast_id"],
      "also_affects": ["other_plotline_id"]
    }
  ]
}"""


def run_2pass(synopses: dict[str, str]) -> dict:
    """Run the 2-pass condition: merged stage1 → sequential stage2."""
    # Reuse the tvplotlines LLM infrastructure
    sys.path.insert(0, str(PROJECT / "src"))
    from tvplotlines.llm import LLMConfig, call_llm, call_llm_parallel

    config = LLMConfig(provider="anthropic", model="claude-sonnet-4-20250514")

    # Stage 1: format + plotlines in one call
    print("  Stage 1: format + plotlines...")
    user_msg = json.dumps({
        "show": "Game of Thrones",
        "season": 1,
        "synopses": [
            {"episode": eid, "text": text}
            for eid, text in sorted(synopses.items())
        ],
    }, ensure_ascii=False)

    stage1 = call_llm(_STAGE1_SYSTEM, user_msg, config)

    # Stage 2: per-episode event assignment
    print("  Stage 2: per-episode events...")
    system2 = _STAGE2_SYSTEM
    user_messages = []
    episode_ids = []
    for eid in sorted(synopses.keys()):
        episode_ids.append(eid)
        user_messages.append(json.dumps({
            "show": "Game of Thrones",
            "season": 1,
            "episode": eid,
            "format": stage1["format"],
            "story_engine": stage1.get("story_engine", ""),
            "cast": stage1.get("cast", []),
            "plotlines": stage1.get("plotlines", []),
            "synopsis": synopses[eid],
        }, ensure_ascii=False))

    stage2_results = call_llm_parallel(system2, user_messages, config, cache_system=True)

    # Assemble result
    episodes = []
    for data, eid in zip(stage2_results, episode_ids):
        data["episode"] = eid
        episodes.append(data)

    result = {
        "format": stage1.get("format"),
        "is_ensemble": stage1.get("is_ensemble"),
        "story_engine": stage1.get("story_engine"),
        "cast": stage1.get("cast", []),
        "plotlines": stage1.get("plotlines", []),
        "episodes": episodes,
    }
    return result


# ---------------------------------------------------------------------------
# Condition C: 3-pass (skip review)
# ---------------------------------------------------------------------------

def run_3pass(synopses: dict[str, str]) -> None:
    """Run the 3-pass condition via CLI."""
    synopsis_files = sorted(SYNOPSES_DIR.glob("GOT_S01E*.txt"))
    cmd = [
        sys.executable, "-m", "tvplotlines", "run",
        *[str(f) for f in synopsis_files],
        "--show", "Game of Thrones",
        "--season", "1",
        "--pass2-mode", "batch",
        "--skip-review",
        "-o", str(THREEPASS_RESULT),
    ]
    print(f"  Running: {' '.join(cmd[-8:])}")
    subprocess.run(cmd, check=True, cwd=str(PROJECT))


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if len(s) > 10]


def _word_set(text: str) -> set[str]:
    """Extract lowercase word set from text."""
    return set(re.findall(r'\b[a-z]{3,}\b', text.lower()))


def compute_coverage(synopses: dict[str, str], episodes: list[dict]) -> float:
    """Fraction of synopsis sentences reflected in events (word overlap >30%)."""
    total_sentences = 0
    covered_sentences = 0

    for ep in episodes:
        eid = ep.get("episode", "")
        synopsis = synopses.get(eid, "")
        if not synopsis:
            continue

        sentences = _split_sentences(synopsis)
        total_sentences += len(sentences)

        event_texts = [e.get("event", "") for e in ep.get("events", [])]
        # Build combined word set from all events
        event_words = set()
        for et in event_texts:
            event_words |= _word_set(et)

        for sent in sentences:
            sent_words = _word_set(sent)
            if not sent_words:
                continue
            overlap = len(sent_words & event_words) / len(sent_words)
            if overlap > 0.30:
                covered_sentences += 1

    if total_sentences == 0:
        return 1.0
    return covered_sentences / total_sentences


def compute_arc_completeness(episodes: list[dict], plotlines: list[dict]) -> float:
    """Mean fraction of 7 narrative functions covered per plotline."""
    plotline_ids = [p.get("id") for p in plotlines]
    if not plotline_ids:
        return 0.0

    functions_per_plotline: dict[str, set[str]] = {pid: set() for pid in plotline_ids}

    for ep in episodes:
        for event in ep.get("events", []):
            pid = event.get("plotline")
            func = event.get("function")
            if pid in functions_per_plotline and func in ALL_FUNCTIONS:
                functions_per_plotline[pid].add(func)

    fractions = [len(funcs) / len(ALL_FUNCTIONS) for funcs in functions_per_plotline.values()]
    return sum(fractions) / len(fractions) if fractions else 0.0


def compute_coh_sep(episodes: list[dict], plotlines: list[dict]) -> float:
    """Embedding-based cohesion-separation score, excluding case_of_the_week."""
    # Collect events per plotline (excluding case_of_the_week)
    cotw_ids = {p["id"] for p in plotlines if p.get("type") == "case_of_the_week"}
    plotline_ids = [p["id"] for p in plotlines if p["id"] not in cotw_ids]

    events_by_plotline: dict[str, list[str]] = {pid: [] for pid in plotline_ids}
    for ep in episodes:
        for event in ep.get("events", []):
            pid = event.get("plotline")
            if pid in events_by_plotline:
                events_by_plotline[pid].append(event.get("event", ""))

    # Remove empty plotlines
    events_by_plotline = {k: v for k, v in events_by_plotline.items() if v}
    if len(events_by_plotline) < 2:
        return 0.0

    # Get embeddings
    all_texts = []
    labels = []
    for pid, texts in events_by_plotline.items():
        for t in texts:
            all_texts.append(t)
            labels.append(pid)

    if not all_texts:
        return 0.0

    client = OpenAI()
    # Batch embed in chunks of 100
    embeddings = []
    for i in range(0, len(all_texts), 100):
        batch = all_texts[i:i+100]
        resp = client.embeddings.create(model="text-embedding-3-small", input=batch)
        embeddings.extend([d.embedding for d in resp.data])

    emb_matrix = np.array(embeddings)

    # Compute cohesion (mean intra-plotline cosine sim) and separation (mean inter-plotline cosine sim)
    unique_labels = list(events_by_plotline.keys())
    label_arr = np.array(labels)

    # Normalize for cosine similarity
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normed = emb_matrix / norms

    # Cosine similarity matrix
    sim_matrix = normed @ normed.T

    intra_sims = []
    inter_sims = []

    for i in range(len(all_texts)):
        for j in range(i + 1, len(all_texts)):
            if label_arr[i] == label_arr[j]:
                intra_sims.append(sim_matrix[i, j])
            else:
                inter_sims.append(sim_matrix[i, j])

    cohesion = np.mean(intra_sims) if intra_sims else 0.0
    separation = np.mean(inter_sims) if inter_sims else 0.0

    # Coh_sep = cohesion - separation (higher is better: tight clusters, well-separated)
    return float(cohesion - separation)


def compute_metrics(synopses: dict[str, str], data: dict) -> dict:
    """Compute all metrics for a condition."""
    episodes = data.get("episodes", [])
    plotlines = data.get("plotlines", [])

    total_events = sum(len(ep.get("events", [])) for ep in episodes)
    num_plotlines = len(plotlines)

    coverage = compute_coverage(synopses, episodes)
    arc = compute_arc_completeness(episodes, plotlines)
    coh_sep = compute_coh_sep(episodes, plotlines)

    return {
        "events": total_events,
        "lines": num_plotlines,
        "coverage": round(coverage, 3),
        "arc_mean": round(arc, 3),
        "coh_sep": round(coh_sep, 4),
        "plotlines": [p.get("name", p.get("id", "?")) for p in plotlines],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    synopses = load_synopses()
    print(f"Loaded {len(synopses)} synopses")

    EXPERIMENT.mkdir(parents=True, exist_ok=True)

    # --- Condition B: 2-pass ---
    if TWOPASS_RESULT.exists():
        print("Condition B (2-pass): loading existing result")
        twopass_data = json.loads(TWOPASS_RESULT.read_text())
    else:
        print("Condition B (2-pass): running...")
        twopass_data = run_2pass(synopses)
        TWOPASS_RESULT.write_text(
            json.dumps(twopass_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  Saved to {TWOPASS_RESULT}")

    # --- Condition C: 3-pass ---
    if THREEPASS_RESULT.exists():
        print("Condition C (3-pass): loading existing result")
    else:
        print("Condition C (3-pass): running pipeline with --skip-review...")
        run_3pass(synopses)
    threepass_data = json.loads(THREEPASS_RESULT.read_text())

    # --- Load existing conditions A and D ---
    print("Condition A (vanilla): loading existing result")
    vanilla_data = json.loads(VANILLA_PATH.read_text())

    print("Condition D (4-pass): loading existing result")
    fourpass_data = json.loads(FOURPASS_PATH.read_text())

    # --- Compute metrics for all conditions ---
    print("\nComputing metrics...")

    metrics_a = compute_metrics(synopses, vanilla_data)
    print(f"  A (vanilla): {metrics_a['events']} events, {metrics_a['lines']} lines")

    metrics_b = compute_metrics(synopses, twopass_data)
    TWOPASS_METRICS.write_text(json.dumps(metrics_b, ensure_ascii=False, indent=2))
    print(f"  B (2-pass):  {metrics_b['events']} events, {metrics_b['lines']} lines")

    metrics_c = compute_metrics(synopses, threepass_data)
    THREEPASS_METRICS.write_text(json.dumps(metrics_c, ensure_ascii=False, indent=2))
    print(f"  C (3-pass):  {metrics_c['events']} events, {metrics_c['lines']} lines")

    metrics_d = compute_metrics(synopses, fourpass_data)
    print(f"  D (4-pass):  {metrics_d['events']} events, {metrics_d['lines']} lines")

    # --- Print comparison table ---
    print("\n" + "=" * 75)
    print(f"{'Condition':<16} {'Passes':>6} {'Events':>7} {'Lines':>6} {'Coverage':>9} {'Arc':>6} {'Coh_sep':>8}")
    print("-" * 75)

    rows = [
        ("A (vanilla)", 1, metrics_a),
        ("B (2-pass)", 2, metrics_b),
        ("C (3-pass)", 3, metrics_c),
        ("D (4-pass)", 4, metrics_d),
    ]
    for label, passes, m in rows:
        print(
            f"{label:<16} {passes:>6} {m['events']:>7} {m['lines']:>6} "
            f"{m['coverage']:>8.3f} {m['arc_mean']:>6.3f} {m['coh_sep']:>8.4f}"
        )
    print("=" * 75)


if __name__ == "__main__":
    main()
