"""Compare three rank formulas on existing breakdowns.

Usage:
    python scripts/rank_experiment.py path/to/result.json [path2.json ...]

Shows a table for each file: plotline events (primary / also_affects)
and computed rank under three weighting schemes.
"""

import json
import sys
from collections import Counter
from pathlib import Path


def load_result(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def count_events(result: dict) -> dict[str, dict]:
    """Count primary events, also_affects, and span per plotline."""
    counts: dict[str, dict] = {}

    plotlines = {p["id"]: p for p in result.get("plotlines", [])}
    for pid in plotlines:
        counts[pid] = {
            "primary": 0, "also_affects": 0,
            "type": plotlines[pid].get("type", "serialized"),
            "episodes": set(),
        }

    for ep in result.get("episodes", []):
        ep_id = ep.get("episode", "")
        for event in ep.get("events", []):
            pid = event.get("plotline_id")
            if pid and pid in counts:
                counts[pid]["primary"] += 1
                counts[pid]["episodes"].add(ep_id)
            for aa in event.get("also_affects") or []:
                if aa in counts:
                    counts[aa]["also_affects"] += 1

    # Convert episode sets to span count
    for pid in counts:
        counts[pid]["span"] = len(counts[pid]["episodes"])
        del counts[pid]["episodes"]

    return counts


def assign_ranks(scores: dict[str, float], types: dict[str, str], context_format: str) -> dict[str, str | None]:
    """Assign A/B/C ranks based on scores, respecting format rules."""
    ranks: dict[str, str | None] = {}

    # Runners get null
    for pid, t in types.items():
        if t == "runner":
            ranks[pid] = None

    # Case of the week: fixed rank by format
    for pid, t in types.items():
        if t == "case_of_the_week":
            if context_format == "procedural":
                ranks[pid] = "A"
            elif context_format == "hybrid":
                ranks[pid] = "B"

    # Sort remaining by score descending
    remaining = [(pid, scores[pid]) for pid in scores if pid not in ranks]
    remaining.sort(key=lambda x: -x[1])

    # Check if A is already taken by case_of_the_week
    a_taken = any(r == "A" for r in ranks.values())

    rank_sequence = ["A", "B", "C"]
    rank_idx = 1 if a_taken else 0  # skip A if already assigned

    for pid, _ in remaining:
        if rank_idx < len(rank_sequence):
            ranks[pid] = rank_sequence[rank_idx]
            rank_idx += 1
        else:
            ranks[pid] = "C"

    return ranks


def run_experiment(path: Path) -> None:
    result = load_result(path)
    show = result.get("show", path.stem)
    context = result.get("context", {})
    fmt = context.get("format", "serial")

    counts = count_events(result)
    types = {pid: c["type"] for pid, c in counts.items()}

    # Three formulas
    scores_primary = {pid: c["primary"] for pid, c in counts.items()}
    scores_half = {pid: c["primary"] + c["also_affects"] * 0.5 for pid, c in counts.items()}
    scores_equal = {pid: c["primary"] + c["also_affects"] for pid, c in counts.items()}

    ranks_primary = assign_ranks(scores_primary, types, fmt)
    ranks_half = assign_ranks(scores_half, types, fmt)
    ranks_equal = assign_ranks(scores_equal, types, fmt)

    # Get LLM-assigned ranks for comparison
    llm_ranks = {}
    for p in result.get("plotlines", []):
        llm_ranks[p["id"]] = p.get("rank")

    # Print table
    print(f"\n{'=' * 80}")
    print(f"  {show} (format: {fmt}, ensemble: {context.get('is_ensemble', False)})")
    print(f"{'=' * 80}")
    n_episodes = len(result.get("episodes", []))
    print(f"  {'Plotline':<30} {'Span':>6} {'Primary':>7} {'AA':>4} {'LLM':>5} {'P-only':>7} {'P+½AA':>7} {'P+AA':>7}")
    print(f"  {'-' * 30} {'-' * 6} {'-' * 7} {'-' * 4} {'-' * 5} {'-' * 7} {'-' * 7} {'-' * 7}")

    # Sort by primary desc
    sorted_pids = sorted(counts.keys(), key=lambda pid: -counts[pid]["primary"])

    for pid in sorted_pids:
        c = counts[pid]
        name = pid
        for p in result.get("plotlines", []):
            if p["id"] == pid:
                name = p.get("name", pid)
                break
        # Truncate name
        if len(name) > 29:
            name = name[:26] + "..."

        llm_r = llm_ranks.get(pid, "-")
        r1 = ranks_primary.get(pid, "-")
        r2 = ranks_half.get(pid, "-")
        r3 = ranks_equal.get(pid, "-")

        # Format None as "-"
        llm_r = llm_r or "-"
        r1 = r1 or "-"
        r2 = r2 or "-"
        r3 = r3 or "-"

        span_str = f"{c['span']}/{n_episodes}"
        print(f"  {name:<30} {span_str:>6} {c['primary']:>7} {c['also_affects']:>4} {llm_r:>5} {r1:>7} {r2:>7} {r3:>7}")

    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/rank_experiment.py result.json [result2.json ...]")
        sys.exit(1)

    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            continue
        run_experiment(path)


if __name__ == "__main__":
    main()
