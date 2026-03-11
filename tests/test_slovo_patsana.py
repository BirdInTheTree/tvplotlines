"""Integration test: run full pipeline on Slovo Patsana S01.

Requires ANTHROPIC_API_KEY in environment. Run manually:
    python -m pytest tests/test_slovo_patsana.py -v -s
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from plotter import get_plotlines

FIXTURES = Path(__file__).parent / "fixtures"
SNAPSHOT_PATH = FIXTURES / "slovo_patsana_s01_result.json"


def _load_episodes() -> list[str]:
    """Load all 8 episode synopses from fixtures."""
    episodes = []
    for i in range(1, 9):
        path = FIXTURES / f"SP_S01E0{i}.txt"
        episodes.append(path.read_text(encoding="utf-8"))
    return episodes


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_full_pipeline():
    """Run full pipeline on Slovo Patsana and verify structure."""
    episodes = _load_episodes()

    result = get_plotlines(
        show="Слово пацана. Кровь на асфальте",
        season=1,
        episodes=episodes,
    )

    # Pass 0: context detected
    assert result.context.franchise_type in ("serial", "hybrid", "ensemble")
    assert result.context.story_engine

    # Pass 1: cast and storylines
    assert len(result.cast) >= 3
    assert len(result.plotlines) >= 2

    for line in result.plotlines:
        assert line.goal
        assert line.obstacle
        assert line.stakes
        assert line.driver

    # Pass 2: all 8 episodes processed
    assert len(result.episodes) == 8

    for ep in result.episodes:
        assert len(ep.events) >= 3
        assert ep.theme

    # Post-processing: span computed
    for line in result.plotlines:
        assert len(line.span) >= 1

    # Save snapshot for Pass 3 development
    SNAPSHOT_PATH.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSnapshot saved to {SNAPSHOT_PATH}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"Context: {result.context.franchise_type} | {result.context.story_engine}")
    print(f"Cast: {', '.join(c.name for c in result.cast)}")
    print(f"\nStorylines ({len(result.plotlines)}):")
    for s in result.plotlines:
        print(f"  [{s.rank}] {s.name} (driver={s.driver}) — {s.goal}")
        print(f"       span: {s.span}")
    print(f"\nEpisodes:")
    for ep in result.episodes:
        print(f"  {ep.episode}: {len(ep.events)} events, theme: {ep.theme}")
        if ep.patches:
            print(f"    patches: {[p.action for p in ep.patches]}")
    print(f"{'='*60}")
