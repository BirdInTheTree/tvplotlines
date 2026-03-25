"""Unit tests for post-processing (no LLM calls)."""

from tvplotlines.models import EpisodeBreakdown, Event, Plotline
from tvplotlines.postprocess import aggregate_patches, compute_span, compute_weight, validate_ranks


def _make_plotline(id: str) -> Plotline:
    return Plotline(
        id=id, name=id.title(), hero="x",
        goal="g", obstacle="o", stakes="s",
        type="serialized", rank="A", nature="plot-led", confidence="solid",
    )


def _make_episode(episode: str, plotline_ids: list[str]) -> EpisodeBreakdown:
    return EpisodeBreakdown(
        episode=episode,
        events=[
            Event(event=f"event for {sid}", plotline_id=sid,
                  function="escalation", characters=["x"])
            for sid in plotline_ids
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
                Event(event="e1", plotline_id="a", function="setup", characters=["x"]),
                Event(event="e2", plotline_id="a", function="escalation", characters=["x"]),
                Event(event="e3", plotline_id="a", function="climax", characters=["x"]),
                Event(event="e4", plotline_id="a", function="resolution", characters=["x"]),
                Event(event="e5", plotline_id="b", function="setup", characters=["x"]),
            ],
            theme="test",
        )
        weights = compute_weight([line_a, line_b], ep)
        assert weights["a"] == "primary"
        assert weights["b"] == "glimpse"


class TestValidateRanks:
    def test_demotes_a_rank_short_span(self):
        """A-rank line spanning 2/10 episodes should be demoted to B."""
        short = _make_plotline("short")
        short.rank = "A"
        short.span = ["S01E01", "S01E02"]

        long = _make_plotline("long")
        long.rank = "A"
        long.span = [f"S01E{i:02d}" for i in range(1, 9)]

        episodes = [
            _make_episode(f"S01E{i:02d}", ["short", "long"] if i <= 2 else ["long"])
            for i in range(1, 11)
        ]
        compute_span([short, long], episodes)
        flags = validate_ranks([short, long], episodes)

        assert short.rank == "B"
        assert long.rank == "A"
        assert any(f["flag"] == "demoted" for f in flags)

    def test_no_demotion_when_span_sufficient(self):
        """A-rank line spanning 4/10 episodes should keep rank A."""
        line = _make_plotline("mid")
        line.rank = "A"
        line.span = [f"S01E{i:02d}" for i in range(1, 5)]

        episodes = [
            _make_episode(f"S01E{i:02d}", ["mid"] if i <= 4 else [])
            for i in range(1, 11)
        ]
        flags = validate_ranks([line], episodes)

        assert line.rank == "A"
        assert not any(f["flag"] == "demoted" for f in flags)

    def test_flags_dominant_line(self):
        """Line with >50% events should be flagged."""
        big = _make_plotline("big")
        small = _make_plotline("small")
        big.span = [f"S01E{i:02d}" for i in range(1, 11)]
        small.span = ["S01E01", "S01E02"]

        # 8 events for big, 2 for small → big = 80%
        events_big = [
            Event(event=f"e{i}", plotline_id="big", function="escalation", characters=["x"])
            for i in range(8)
        ]
        events_small = [
            Event(event=f"e{i}", plotline_id="small", function="setup", characters=["x"])
            for i in range(2)
        ]
        episodes = [
            EpisodeBreakdown(episode="S01E01", events=events_big + events_small, theme="t"),
        ]
        flags = validate_ranks([big, small], episodes)

        assert any(f["flag"] == "dominant" and f["plotline"] == "big" for f in flags)

    def test_b_rank_not_demoted(self):
        """B-rank line with short span should not be demoted."""
        line = _make_plotline("minor")
        line.rank = "B"
        line.span = ["S01E01"]

        episodes = [_make_episode(f"S01E{i:02d}", ["minor"] if i == 1 else []) for i in range(1, 11)]
        flags = validate_ranks([line], episodes)

        assert line.rank == "B"
        assert not any(f["flag"] == "demoted" for f in flags)


class TestAggregatePatches:
    def test_collects_from_all_episodes(self):
        from tvplotlines.models import Patch
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
