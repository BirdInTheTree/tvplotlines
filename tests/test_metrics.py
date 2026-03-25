"""Tests for quality metrics."""

from __future__ import annotations

from tvplotlines.metrics import compute_coverage, compute_consistency_ari, compute_score
from tvplotlines.models import EpisodeBreakdown, Event


def _ep(events_data: list[tuple[str, str | None]]) -> EpisodeBreakdown:
    """Helper: create episode from (event_text, plotline) pairs."""
    return EpisodeBreakdown(
        episode="S01E01",
        events=[
            Event(event=text, plotline=line, function="setup", characters=["a"])
            for text, line in events_data
        ],
    )


class TestCoverage:
    def test_all_assigned(self):
        ep = _ep([("e1", "line_a"), ("e2", "line_b")])
        assert compute_coverage([ep]) == 1.0

    def test_some_null(self):
        ep = _ep([("e1", "line_a"), ("e2", None), ("e3", "line_b"), ("e4", None)])
        assert compute_coverage([ep]) == 0.5

    def test_all_null(self):
        ep = _ep([("e1", None), ("e2", None)])
        assert compute_coverage([ep]) == 0.0

    def test_empty(self):
        ep = EpisodeBreakdown(episode="S01E01")
        assert compute_coverage([ep]) == 1.0

    def test_multiple_episodes(self):
        ep1 = _ep([("e1", "a"), ("e2", "b")])
        ep2 = _ep([("e3", None), ("e4", None)])
        assert compute_coverage([ep1, ep2]) == 0.5


class TestConsistencyARI:
    def test_identical_runs(self):
        ep = EpisodeBreakdown(
            episode="S01E01",
            events=[
                Event(event="e1", plotline="line_a", function="setup", characters=["char1"]),
                Event(event="e2", plotline="line_b", function="setup", characters=["char2"]),
            ],
        )
        # Same data twice = perfect consistency
        ari = compute_consistency_ari([[ep], [ep]], cast_ids=["char1", "char2"])
        assert ari == 1.0

    def test_different_names_same_structure(self):
        """Runs with different plotline names but same grouping = high ARI."""
        ep_run1 = EpisodeBreakdown(
            episode="S01E01",
            events=[
                Event(event="e1", plotline="belonging", function="setup", characters=["char1"]),
                Event(event="e2", plotline="belonging", function="setup", characters=["char2"]),
                Event(event="e3", plotline="leadership", function="setup", characters=["char3"]),
            ],
        )
        ep_run2 = EpisodeBreakdown(
            episode="S01E01",
            events=[
                Event(event="e1", plotline="acceptance", function="setup", characters=["char1"]),
                Event(event="e2", plotline="acceptance", function="setup", characters=["char2"]),
                Event(event="e3", plotline="power", function="setup", characters=["char3"]),
            ],
        )
        ari = compute_consistency_ari(
            [[ep_run1], [ep_run2]],
            cast_ids=["char1", "char2", "char3"],
        )
        assert ari == 1.0

    def test_completely_different(self):
        """Opposite groupings = low ARI."""
        ep_run1 = EpisodeBreakdown(
            episode="S01E01",
            events=[
                Event(event="e1", plotline="A", function="setup", characters=["c1"]),
                Event(event="e2", plotline="A", function="setup", characters=["c2"]),
                Event(event="e3", plotline="B", function="setup", characters=["c3"]),
                Event(event="e4", plotline="B", function="setup", characters=["c4"]),
            ],
        )
        ep_run2 = EpisodeBreakdown(
            episode="S01E01",
            events=[
                Event(event="e1", plotline="X", function="setup", characters=["c1"]),
                Event(event="e2", plotline="Y", function="setup", characters=["c2"]),
                Event(event="e3", plotline="X", function="setup", characters=["c3"]),
                Event(event="e4", plotline="Y", function="setup", characters=["c4"]),
            ],
        )
        ari = compute_consistency_ari(
            [[ep_run1], [ep_run2]],
            cast_ids=["c1", "c2", "c3", "c4"],
        )
        assert ari < 0.0  # worse than random

    def test_single_run(self):
        """One run = perfect consistency by definition."""
        ep = EpisodeBreakdown(episode="S01E01", events=[])
        assert compute_consistency_ari([[ep]], cast_ids=["c1"]) == 1.0


class TestScore:
    def test_perfect(self):
        assert compute_score(1.0, 1.0) == 1.0

    def test_zero_coverage(self):
        assert compute_score(0.0, 1.0) == 0.0

    def test_zero_consistency(self):
        assert compute_score(1.0, 0.0) == 0.0

    def test_multiplicative(self):
        assert compute_score(0.8, 0.5) == 0.4
