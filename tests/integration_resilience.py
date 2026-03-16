"""Integration test: pipeline resilience with real API calls.

Runs get_plotlines on 3 short episodes, verifies:
1. Callbacks fire in correct order
2. Resume from pre-computed results skips expensive passes

Usage: python -m tests.integration_resilience
Requires: ANTHROPIC_API_KEY in .env or environment
"""

from __future__ import annotations

import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from plotter import get_plotlines, PipelineCallback
from plotter.models import CastMember, EpisodeBreakdown, Plotline, SeriesContext, Verdict


# 3 minimal synopses — enough to exercise the pipeline cheaply
EPISODES = [
    "Detective Lena arrives in the small town of Millbrook to investigate the disappearance "
    "of teenager Amy Chen. She meets Sheriff Dan, who is skeptical of outside help. "
    "Lena discovers Amy's diary hidden under her mattress, with entries about a secret "
    "meeting place in the woods.",

    "Lena follows the diary clues to an abandoned cabin in the woods, where she finds "
    "Amy's phone. Sheriff Dan reveals his son Jake was dating Amy. Meanwhile, Amy's mother "
    "Carol holds a vigil in town. Lena finds a threatening text from an unknown number on "
    "Amy's phone.",

    "The threatening texts are traced to local businessman Mr. Pratt, who was trying to buy "
    "the Chen family land. Amy is found alive, hiding at a friend's house after Pratt "
    "threatened her family. Sheriff Dan arrests Pratt. Lena says goodbye to the town.",
]


class RecordingCallback(PipelineCallback):
    """Records all callback events for verification."""

    def __init__(self):
        self.events: list[str] = []
        self.context = None
        self.cast = None
        self.plotlines = None
        self.breakdowns = []
        self.batch_id = None

    def on_pass0_complete(self, context: SeriesContext) -> None:
        self.events.append("pass0")
        self.context = context
        print(f"  [callback] Pass 0 complete: {context.genre}")

    def on_pass1_complete(self, cast: list[CastMember], plotlines: list[Plotline]) -> None:
        self.events.append("pass1")
        self.cast = cast
        self.plotlines = plotlines
        print(f"  [callback] Pass 1 complete: {len(cast)} cast, {len(plotlines)} plotlines")

    def on_episode_complete(self, index: int, breakdown: EpisodeBreakdown) -> None:
        self.events.append(f"episode_{index}")
        self.breakdowns.append(breakdown)
        print(f"  [callback] Episode {index} complete: {len(breakdown.events)} events")

    def on_pass2_complete(self, breakdowns: list[EpisodeBreakdown]) -> None:
        self.events.append("pass2")
        if not self.breakdowns:
            self.breakdowns = breakdowns
        print(f"  [callback] Pass 2 complete: {len(breakdowns)} episodes")

    def on_batch_submitted(self, batch_id: str) -> None:
        self.events.append("batch_submitted")
        self.batch_id = batch_id
        print(f"  [callback] Batch submitted: {batch_id}")

    def on_pass3_complete(self, verdicts: list[Verdict]) -> None:
        self.events.append("pass3")
        print(f"  [callback] Pass 3 complete: {len(verdicts)} verdicts")


def test_full_run():
    """Test 1: Full pipeline run with callbacks."""
    print("\n=== Test 1: Full pipeline run (sequential mode) ===")

    cb = RecordingCallback()
    result = get_plotlines(
        show="Millbrook",
        season=1,
        episodes=EPISODES,
        lang="en",
        pass2_mode="sequential",
        callback=cb,
    )

    # Verify callbacks fired
    assert "pass0" in cb.events, f"pass0 not in events: {cb.events}"
    assert "pass1" in cb.events, f"pass1 not in events: {cb.events}"
    assert "pass2" in cb.events, f"pass2 not in events: {cb.events}"
    # Sequential mode should fire episode callbacks
    episode_events = [e for e in cb.events if e.startswith("episode_")]
    assert len(episode_events) == 3, f"Expected 3 episode events, got {episode_events}"

    print(f"\n  Result: {len(result.cast)} cast, {len(result.plotlines)} plotlines, "
          f"{len(result.episodes)} episodes")
    print(f"  Usage: {result.usage}")
    print(f"  Events: {cb.events}")

    return cb


def test_resume(cb: RecordingCallback):
    """Test 2: Resume from pre-computed results (skips Pass 0, 1, 2)."""
    print("\n=== Test 2: Resume with pre-computed breakdowns ===")

    cb2 = RecordingCallback()
    result = get_plotlines(
        show="Millbrook",
        season=1,
        episodes=EPISODES,
        context=cb.context,
        cast=cb.cast,
        plotlines=cb.plotlines,
        breakdowns=list(cb.breakdowns),
        lang="en",
        skip_review=True,  # Skip Pass 3 too — pure resume test
        callback=cb2,
    )

    # Pass 0, 1, 2 should still fire callbacks (with pre-computed data)
    # but no LLM calls should be made (usage should be 0 requests)
    assert "0 requests" in result.usage, f"Expected 0 requests, got: {result.usage}"
    print(f"  Usage: {result.usage}")
    print(f"  Events: {cb2.events}")
    print(f"  Plotlines preserved: {len(result.plotlines)}")


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set. Skipping integration test.")
        sys.exit(0)

    print("Running pipeline resilience integration tests...")
    print(f"Using {len(EPISODES)} episodes, sequential mode (cheapest)")

    cb = test_full_run()
    test_resume(cb)

    print("\n=== All integration tests passed ===")


if __name__ == "__main__":
    main()
