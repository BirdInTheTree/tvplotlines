"""Consistency test: run pipeline N times and compute ARI.

Requires ANTHROPIC_API_KEY in environment. Run manually:
    python -m pytest tests/test_consistency.py -v -s
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from plotter import get_plotlines
from plotter.metrics import compute_coverage, compute_consistency_ari, compute_score

FIXTURES = Path(__file__).parent / "fixtures"
N_RUNS = 3


def _load_episodes() -> list[str]:
    episodes = []
    for i in range(1, 9):
        path = FIXTURES / f"SP_S01E0{i}.txt"
        episodes.append(path.read_text(encoding="utf-8"))
    return episodes


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_consistency():
    """Run pipeline N times and measure consistency via ARI."""
    episodes_text = _load_episodes()

    runs_episodes = []
    runs_data = []
    cast_ids = None

    for run_idx in range(N_RUNS):
        print(f"\n--- Run {run_idx + 1}/{N_RUNS} ---")
        result = get_plotlines(
            show="Слово пацана. Кровь на асфальте",
            season=1,
            episodes=episodes_text,
            skip_review=True,
        )

        runs_episodes.append(result.episodes)

        if cast_ids is None:
            cast_ids = [c.id for c in result.cast]

        coverage = compute_coverage(result.episodes)
        print(f"  Plotlines: {len(result.plotlines)}")
        print(f"  Coverage: {coverage:.3f}")
        print(f"  Lines: {[p.id for p in result.plotlines]}")

        runs_data.append({
            "plotlines": [p.id for p in result.plotlines],
            "coverage": coverage,
            "cast": [c.id for c in result.cast],
        })

    # Compute consistency
    # Use union of all cast_ids across runs
    all_cast = set()
    for rd in runs_data:
        all_cast.update(rd["cast"])
    all_cast_ids = sorted(all_cast)

    consistency = compute_consistency_ari(runs_episodes, all_cast_ids)
    avg_coverage = sum(rd["coverage"] for rd in runs_data) / N_RUNS
    score = compute_score(avg_coverage, consistency)

    print(f"\n{'='*60}")
    print(f"Runs: {N_RUNS}")
    print(f"Avg coverage: {avg_coverage:.3f}")
    print(f"Consistency (ARI): {consistency:.3f}")
    print(f"Score: {score:.3f}")
    print(f"{'='*60}")

    # Save results
    results_path = FIXTURES / "slovo_patsana_s01_consistency.json"
    results_path.write_text(json.dumps({
        "n_runs": N_RUNS,
        "avg_coverage": round(avg_coverage, 4),
        "consistency_ari": round(consistency, 4),
        "score": round(score, 4),
        "runs": runs_data,
    }, ensure_ascii=False, indent=2))
    print(f"Results saved to {results_path}")

    # Sanity checks
    assert avg_coverage > 0.9, f"Coverage too low: {avg_coverage}"
    assert consistency > 0.0, f"Consistency should be positive: {consistency}"
