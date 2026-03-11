"""Run Pass 3 (narratologist review) on saved snapshot.

Requires ANTHROPIC_API_KEY in environment. Run manually:
    python -m pytest tests/test_pass3_snapshot.py -v -s
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from plotter.llm import LLMConfig
from plotter.models import (
    CastMember,
    EpisodeBreakdown,
    Event,
    Interaction,
    Patch,
    Plotline,
    SeriesContext,
)
from plotter.pass3 import review_storylines

FIXTURES = Path(__file__).parent / "fixtures"
SNAPSHOT_PATH = FIXTURES / "slovo_patsana_s01_result.json"


def _load_snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def _rebuild_from_snapshot(data: dict):
    """Reconstruct typed objects from snapshot dict."""
    context = SeriesContext(**data["context"])

    cast = [CastMember(**c) for c in data["cast"]]

    plotlines = [Plotline(**p) for p in data["plotlines"]]

    episodes = []
    for ep in data["episodes"]:
        events = [Event(**e) for e in ep.get("events", [])]
        interactions = [Interaction(**i) for i in ep.get("interactions", [])]
        patches = [Patch(**p) for p in ep.get("patches", [])]
        episodes.append(EpisodeBreakdown(
            episode=ep["episode"],
            events=events,
            theme=ep.get("theme", ""),
            interactions=interactions,
            patches=patches,
        ))

    return context, cast, plotlines, episodes


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_pass3_on_snapshot():
    """Run Pass 3 on saved snapshot and display verdicts."""
    data = _load_snapshot()
    context, cast, plotlines, episodes = _rebuild_from_snapshot(data)

    verdicts = review_storylines(
        show="Слово пацана. Кровь на асфальте",
        season=1,
        context=context,
        cast=cast,
        plotlines=plotlines,
        episodes=episodes,
    )

    # Save verdicts
    verdicts_path = FIXTURES / "slovo_patsana_s01_verdicts.json"
    verdicts_data = [{"action": v.action, **v.data} for v in verdicts]
    verdicts_path.write_text(
        json.dumps(verdicts_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nVerdicts saved to {verdicts_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"Verdicts: {len(verdicts)}")
    for v in verdicts:
        print(f"\n  [{v.action}]")
        for k, val in v.data.items():
            if k == "action":
                continue
            if isinstance(val, str) and len(val) > 100:
                val = val[:100] + "..."
            print(f"    {k}: {val}")
    print(f"{'='*60}")
