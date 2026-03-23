"""Pipeline progress callbacks.

Subclass PipelineCallback and override methods to receive notifications
at each pipeline stage. The library never writes files — persistence
is the caller's choice via these hooks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tvplotlines.models import (
        CastMember,
        EpisodeBreakdown,
        Plotline,
        SeriesContext,
        Verdict,
    )


class PipelineCallback:
    """Override any method to receive progress notifications.

    All methods are no-ops by default. Subclass and override what you need.
    The pipeline wraps every call in try/except so a buggy callback
    never kills the run.
    """

    def on_pass0_complete(self, context: SeriesContext) -> None:
        """Called after context detection (Pass 0)."""

    def on_pass1_complete(
        self, cast: list[CastMember], plotlines: list[Plotline],
    ) -> None:
        """Called after storyline extraction (Pass 1)."""

    def on_episode_complete(
        self, index: int, breakdown: EpisodeBreakdown,
    ) -> None:
        """Called after each episode is processed.

        Only fires in sequential mode (pass2_mode="sequential").
        In parallel and batch modes, use on_pass2_complete instead.
        """

    def on_pass2_complete(self, breakdowns: list[EpisodeBreakdown]) -> None:
        """Called after all episodes are processed (Pass 2)."""

    def on_batch_submitted(self, batch_id: str) -> None:
        """Called with batch ID immediately after batch creation."""

    def on_pass3_complete(self, verdicts: list[Verdict]) -> None:
        """Called after structural review (Pass 3)."""
