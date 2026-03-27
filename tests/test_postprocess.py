"""Unit tests for post-processing (no LLM calls)."""

from tvplotlines.models import EpisodeBreakdown, Event, Plotline, SeriesContext
from tvplotlines.postprocess import compute_ranks, compute_span, compute_weight, validate_ranks


def _make_plotline(id: str) -> Plotline:
    return Plotline(
        id=id, name=id.title(), hero="x",
        goal="g", obstacle="o", stakes="s",
        type="serialized", nature="plot-led", confidence="solid",
        computed_rank="A",
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
        """A computed_rank line spanning 2/10 episodes should be demoted to B."""
        short = _make_plotline("short")
        short.computed_rank = "A"
        short.span = ["S01E01", "S01E02"]

        long = _make_plotline("long")
        long.computed_rank = "A"
        long.span = [f"S01E{i:02d}" for i in range(1, 9)]

        episodes = [
            _make_episode(f"S01E{i:02d}", ["short", "long"] if i <= 2 else ["long"])
            for i in range(1, 11)
        ]
        compute_span([short, long], episodes)
        flags = validate_ranks([short, long], episodes)

        assert short.computed_rank == "B"
        assert long.computed_rank == "A"
        assert any(f["flag"] == "demoted" for f in flags)

    def test_no_demotion_when_span_sufficient(self):
        """A computed_rank line spanning 4/10 episodes should keep rank A."""
        line = _make_plotline("mid")
        line.computed_rank = "A"
        line.span = [f"S01E{i:02d}" for i in range(1, 5)]

        episodes = [
            _make_episode(f"S01E{i:02d}", ["mid"] if i <= 4 else [])
            for i in range(1, 11)
        ]
        flags = validate_ranks([line], episodes)

        assert line.computed_rank == "A"
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
        """B computed_rank line with short span should not be demoted."""
        line = _make_plotline("minor")
        line.computed_rank = "B"
        line.span = ["S01E01"]

        episodes = [_make_episode(f"S01E{i:02d}", ["minor"] if i == 1 else []) for i in range(1, 11)]
        flags = validate_ranks([line], episodes)

        assert line.computed_rank == "B"
        assert not any(f["flag"] == "demoted" for f in flags)


def _make_plotline_no_rank(id: str, ptype: str = "serialized") -> Plotline:
    """Create a plotline without computed_rank (for compute_ranks tests)."""
    return Plotline(
        id=id, name=id.title(), hero="x",
        goal="g", obstacle="o", stakes="s",
        type=ptype, nature="plot-led", confidence="solid",
    )


class TestComputeRanks:
    def test_serial_assigns_a_b_c(self):
        """Most events → A, second → B, rest → C."""
        ctx = SeriesContext(format="serial", story_engine="x", genre="drama")
        lines = [_make_plotline_no_rank("big"), _make_plotline_no_rank("mid"), _make_plotline_no_rank("small")]
        episodes = [
            _make_episode("S01E01", ["big", "big", "big", "mid", "mid", "small"]),
        ]
        compute_ranks(lines, episodes, ctx)
        assert lines[0].computed_rank == "A"
        assert lines[1].computed_rank == "B"
        assert lines[2].computed_rank == "C"

    def test_runner_gets_no_rank(self):
        ctx = SeriesContext(format="serial", story_engine="x", genre="drama")
        runner = _make_plotline_no_rank("bg", ptype="runner")
        main = _make_plotline_no_rank("main")
        episodes = [_make_episode("S01E01", ["main", "main"])]
        compute_ranks([runner, main], episodes, ctx)
        assert runner.computed_rank is None
        assert main.computed_rank == "A"

    def test_procedural_case_of_week_gets_a(self):
        ctx = SeriesContext(format="procedural", story_engine="x", genre="drama")
        cotw = _make_plotline_no_rank("case", ptype="case_of_the_week")
        arc = _make_plotline_no_rank("arc")
        # arc has more events, but cotw is fixed at A for procedural
        episodes = [_make_episode("S01E01", ["arc", "arc", "arc", "case"])]
        compute_ranks([cotw, arc], episodes, ctx)
        assert cotw.computed_rank == "A"
        assert arc.computed_rank == "B"

    def test_hybrid_case_of_week_gets_b(self):
        ctx = SeriesContext(format="hybrid", story_engine="x", genre="drama")
        cotw = _make_plotline_no_rank("case", ptype="case_of_the_week")
        arc = _make_plotline_no_rank("arc")
        episodes = [_make_episode("S01E01", ["arc", "case", "case"])]
        compute_ranks([cotw, arc], episodes, ctx)
        assert cotw.computed_rank == "B"
        assert arc.computed_rank == "A"

    def test_also_affects_not_counted(self):
        """Only primary plotline_id counts, not also_affects."""
        ctx = SeriesContext(format="serial", story_engine="x", genre="drama")
        main = _make_plotline_no_rank("main")
        side = _make_plotline_no_rank("side")
        ep = EpisodeBreakdown(
            episode="S01E01",
            events=[
                Event(event="e1", plotline_id="main", function="setup",
                      characters=["x"], also_affects=["side"]),
                Event(event="e2", plotline_id="main", function="escalation",
                      characters=["x"], also_affects=["side"]),
                Event(event="e3", plotline_id="side", function="setup",
                      characters=["x"]),
            ],
            theme="t",
        )
        compute_ranks([main, side], [ep], ctx)
        assert main.computed_rank == "A"
        assert side.computed_rank == "B"


