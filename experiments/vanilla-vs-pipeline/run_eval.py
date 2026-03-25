"""
Evaluate vanilla vs pipeline plotline analysis using LLM-as-judge
and task-based evaluation.
"""

import json
import os
import sys
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-4-20250514"
TEMPERATURE = 0
MAX_SUMMARY_CHARS = 6000

BASE_DIR = Path(__file__).parent
APP_RESULTS = Path("/Users/nvashko/Projects/1-projects/tvplotlines-app/data/results")


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def truncate(text: str, limit: int = MAX_SUMMARY_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... [TRUNCATED]"


def summarize_vanilla(data: dict) -> str:
    """Create a textual summary of vanilla results."""
    lines = []
    lines.append("PLOTLINES:")
    for pl in data["plotlines"]:
        lines.append(f"  - {pl['name']} (hero: {pl['hero']})")

    lines.append("\nEPISODE EVENTS:")
    for ep in data["episodes"]:
        lines.append(f"\n  {ep['episode']}:")
        for ev in ep["events"]:
            lines.append(f"    [{ev['function']}] {ev['event']} → plotline: {ev['plotline']}")

    return "\n".join(lines)


def summarize_pipeline(data: dict) -> str:
    """Create a textual summary of pipeline results."""
    lines = []

    if "context" in data:
        ctx = data["context"]
        lines.append(f"CONTEXT: {ctx.get('genre', '')} | {ctx.get('format', '')} | engine: {ctx.get('story_engine', '')}")
        lines.append(f"  ensemble: {ctx.get('is_ensemble')} | anthology: {ctx.get('is_anthology')}")

    lines.append("\nPLOTLINES:")
    for pl in data["plotlines"]:
        lines.append(f"  - {pl['name']} (hero: {pl['hero']}, rank: {pl.get('rank', '?')}, type: {pl.get('type', '?')})")
        if pl.get("goal"):
            lines.append(f"    goal: {pl['goal']}")
        if pl.get("obstacle"):
            lines.append(f"    obstacle: {pl['obstacle']}")
        if pl.get("stakes"):
            lines.append(f"    stakes: {pl['stakes']}")

    lines.append("\nEPISODE EVENTS:")
    for ep in data["episodes"]:
        lines.append(f"\n  {ep['episode']}:")
        if ep.get("theme"):
            lines.append(f"    theme: {ep['theme']}")
        for ev in ep["events"]:
            chars = ", ".join(ev.get("characters") or [])
            also = ", ".join(ev.get("also_affects") or [])
            line = f"    [{ev['function']}] {ev['event']} → plotline: {ev['plotline']}"
            if chars:
                line += f" | chars: {chars}"
            if also:
                line += f" | also: {also}"
            lines.append(line)
        if ep.get("interactions"):
            for inter in ep["interactions"]:
                lines.append(f"    interaction: {inter}")

    return "\n".join(lines)


def call_claude(system: str, user: str) -> str:
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        temperature=TEMPERATURE,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


# ── LLM-as-judge ──

JUDGE_SYSTEM = """You are an expert TV narrative analyst evaluating the quality of automated plotline extraction results.
You will be given two analyses of the same TV season: one from a "vanilla" (single-pass) approach and one from a "pipeline" (multi-pass) approach.
Rate each on a 1-5 scale for:
- depth: How deeply does the analysis capture character motivations, thematic layers, and narrative subtext?
- structure: How well does it identify narrative structure (setup, escalation, turning points, climax, resolution)?
- completeness: How thoroughly does it cover all significant plotlines and story events?
- usefulness: How useful would this analysis be for a screenwriter or narrative researcher?

Return ONLY valid JSON (no markdown code fences) with this exact schema:
{
  "vanilla": {"depth": N, "structure": N, "completeness": N, "usefulness": N},
  "pipeline": {"depth": N, "structure": N, "completeness": N, "usefulness": N},
  "winner": "vanilla" or "pipeline" or "tie",
  "reason": "one sentence explanation"
}"""


def run_judge(show_name: str, vanilla_summary: str, pipeline_summary: str) -> dict:
    prompt = f"""Show: {show_name}

=== VANILLA ANALYSIS ===
{vanilla_summary}

=== PIPELINE ANALYSIS ===
{pipeline_summary}

Rate each analysis 1-5 on depth, structure, completeness, usefulness. Return JSON."""

    response = call_claude(JUDGE_SYSTEM, prompt)
    # Strip markdown fences if present
    text = response.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)


# ── Task-based eval ──

TASK_SYSTEM = """You are a narrative analyst. You will be given plotline analysis data for a TV show season.
Answer the question using ONLY the provided data. Do not use any external knowledge about the show.
If the data does not contain enough information to answer the question, respond with exactly: INSUFFICIENT DATA
Otherwise, provide a concise answer (2-4 sentences)."""


MADMEN_QUESTIONS = [
    "What is Don Draper's main internal conflict?",
    "How does Don's marriage change across the season?",
    "What role does Peggy play in the narrative structure?",
    "Which plotline drives the season finale?",
    "How do Pete and Don's arcs interact?",
]

GOT_QUESTIONS = [
    "What is Ned Stark's fatal flaw?",
    "How does Daenerys transform across the season?",
    "What narrative function does the supernatural threat serve?",
    "Which episode contains the main turning point?",
    "How do the Stark and Lannister plotlines converge?",
]


def run_task_eval(analysis_text: str, question: str) -> dict:
    """Ask a question using only the analysis data. Returns answer and whether data was sufficient."""
    truncated = truncate(analysis_text)
    prompt = f"""=== ANALYSIS DATA ===
{truncated}

=== QUESTION ===
{question}"""

    answer = call_claude(TASK_SYSTEM, prompt)
    is_sufficient = "INSUFFICIENT DATA" not in answer.upper()
    return {"question": question, "answer": answer, "is_sufficient": is_sufficient}


def run_show_eval(show_name: str, vanilla_path: str, pipeline_path: str, questions: list, output_path: str):
    print(f"\n{'='*60}")
    print(f"Evaluating: {show_name}")
    print(f"{'='*60}")

    vanilla_data = load_json(vanilla_path)
    pipeline_data = load_json(pipeline_path)

    vanilla_summary = summarize_vanilla(vanilla_data)
    pipeline_summary = summarize_pipeline(pipeline_data)

    print(f"  Vanilla summary: {len(vanilla_summary)} chars")
    print(f"  Pipeline summary: {len(pipeline_summary)} chars")

    # A. LLM-as-judge
    print("  Running LLM-as-judge...")
    judge_result = run_judge(show_name, vanilla_summary, pipeline_summary)
    print(f"  Winner: {judge_result['winner']}")
    print(f"  Reason: {judge_result['reason']}")

    # B. Task-based eval
    print("  Running task-based eval...")
    task_results = {"vanilla": [], "pipeline": []}

    for q in questions:
        print(f"    Q: {q[:50]}...")
        v_result = run_task_eval(vanilla_summary, q)
        p_result = run_task_eval(pipeline_summary, q)
        task_results["vanilla"].append(v_result)
        task_results["pipeline"].append(p_result)
        v_suf = "OK" if v_result["is_sufficient"] else "INSUFFICIENT"
        p_suf = "OK" if p_result["is_sufficient"] else "INSUFFICIENT"
        print(f"      vanilla: {v_suf} | pipeline: {p_suf}")

    # Compute task scores
    vanilla_answered = sum(1 for r in task_results["vanilla"] if r["is_sufficient"])
    pipeline_answered = sum(1 for r in task_results["pipeline"] if r["is_sufficient"])

    result = {
        "show": show_name,
        "judge": judge_result,
        "task_eval": {
            "vanilla": {
                "results": task_results["vanilla"],
                "answered": vanilla_answered,
                "total": len(questions),
            },
            "pipeline": {
                "results": task_results["pipeline"],
                "answered": pipeline_answered,
                "total": len(questions),
            },
        },
    }

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  Saved to {output_path}")
    return result


def print_summary(results: list[dict]):
    print(f"\n{'='*80}")
    print("SUMMARY TABLE")
    print(f"{'='*80}")

    header = f"{'Show':<12} {'Method':<10} {'Depth':>6} {'Structure':>10} {'Complete':>10} {'Useful':>8} {'Tasks':>7}"
    print(header)
    print("-" * len(header))

    for r in results:
        show = r["show"]
        j = r["judge"]
        for method in ["vanilla", "pipeline"]:
            scores = j[method]
            tasks = r["task_eval"][method]
            task_str = f"{tasks['answered']}/{tasks['total']}"
            marker = " *" if j["winner"] == method else ""
            print(
                f"{show:<12} {method:<10} {scores['depth']:>6} {scores['structure']:>10} "
                f"{scores['completeness']:>10} {scores['usefulness']:>8} {task_str:>7}{marker}"
            )
        print(f"  Winner: {j['winner']} — {j['reason']}")
        print()


def main():
    results = []

    # Mad Men
    r = run_show_eval(
        "Mad Men S01",
        str(BASE_DIR / "madmen_vanilla.json"),
        str(APP_RESULTS / "madmen_s01_result.json"),
        MADMEN_QUESTIONS,
        str(BASE_DIR / "eval_madmen.json"),
    )
    results.append(r)

    # Game of Thrones
    r = run_show_eval(
        "GoT S01",
        str(BASE_DIR / "got_vanilla.json"),
        str(APP_RESULTS / "got_s01_result.json"),
        GOT_QUESTIONS,
        str(BASE_DIR / "eval_got.json"),
    )
    results.append(r)

    print_summary(results)


if __name__ == "__main__":
    main()
