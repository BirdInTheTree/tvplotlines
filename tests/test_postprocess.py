"""Unit tests for post-processing (no LLM calls)."""

from plotter.models import EpisodeBreakdown, Event, Plotline
from plotter.postprocess import aggregate_patches, compute_span, compute_weight


def _make_plotline(id: str) -> Plotline:
    return Plotline(
        id=id, name=id.title(), driver="x",
        goal="g", obstacle="o", stakes="s",
        type="serialized", rank="A", nature="plot-led", confidence="solid",
    )


def _make_episode(episode: str, storyline_ids: list[str]) -> EpisodeBreakdown:
    return EpisodeBreakdown(
        episode=episode,
        events=[
            Event(event=f"event for {sid}", storyline=sid,
                  function="escalation", characters=["x"])
            for sid in storyline_ids
        ],
        theme="test",
    )


class TestComputeSpan:
    def test_basic(self):
        lines = [_make_plotline("a"), _make_plotline("b")]
        episodes = [
            _make_episode("S01E01", ["a", "b"]),
            _make_episode("S01E02", ["a"]),
            _make_episode("S01E03", ["b"]),
        ]
        compute_span(lines, episodes)
        assert lines[0].span == ["S01E01", "S01E02"]
        assert lines[1].span == ["S01E01", "S01E03"]

    def test_empty(self):
        lines = [_make_plotline("a")]
        compute_span(lines, [])
        assert lines[0].span == []


class TestComputeWeight:
    def test_primary_and_glimpse(self):
        line_a = _make_plotline("a")
        line_b = _make_plotline("b")
        ep = EpisodeBreakdown(
            episode="S01E01",
            events=[
                Event(event="e1", storyline="a", function="setup", characters=["x"]),
                Event(event="e2", storyline="a", function="escalation", characters=["x"]),
                Event(event="e3", storyline="a", function="climax", characters=["x"]),
                Event(event="e4", storyline="a", function="resolution", characters=["x"]),
                Event(event="e5", storyline="b", function="setup", characters=["x"]),
            ],
            theme="test",
        )
        weights = compute_weight([line_a, line_b], ep)
        assert weights["a"] == "primary"
        assert weights["b"] == "glimpse"


class TestAggregatePatches:
    def test_collects_from_all_episodes(self):
        from plotter.models import Patch
        ep1 = EpisodeBreakdown(
            episode="S01E01", theme="t",
            patches=[Patch(action="ADD_LINE", target="x", reason="r")],
        )
        ep2 = EpisodeBreakdown(
            episode="S01E02", theme="t",
            patches=[Patch(action="RERANK", target="y", reason="r")],
        )
        ep3 = EpisodeBreakdown(episode="S01E03", theme="t")
        patches = aggregate_patches([ep1, ep2, ep3])
        assert len(patches) == 2
        assert patches[0].action == "ADD_LINE"
        assert patches[1].action == "RERANK"
