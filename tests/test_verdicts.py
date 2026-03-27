"""Tests for verdict validation and safe DROP logic."""

from tvplotlines.models import EpisodeBreakdown, Event, Plotline, Verdict
from tvplotlines.verdicts import apply_verdicts


def _make_plotline(id: str, computed_rank: str = "A") -> Plotline:
    return Plotline(
        id=id, name=f"Test: {id}", hero="hero",
        goal="goal", obstacle="obstacle", stakes="stakes",
        type="serialized", nature="character-led",
        confidence="solid", computed_rank=computed_rank,
    )


def _make_episode(episode: str, events: list[dict]) -> EpisodeBreakdown:
    return EpisodeBreakdown(
        episode=episode,
        theme="test",
        events=[
            Event(
                event=e["event"],
                plotline_id=e["plotline_id"],
                function="escalation",
                characters=["hero"],
            )
            for e in events
        ],
    )


class TestVerdictTargetValidation:
    """Verdicts with invalid targets should be skipped, not applied."""

    def test_reassign_to_nonexistent_plotline_skipped(self):
        plotlines = [_make_plotline("real")]
        episodes = [_make_episode("S01E01", [
            {"event": "something happens", "plotline_id": "real"},
        ])]
        verdicts = [Verdict(action="REASSIGN", data={
            "event": "something happens",
            "episode": "S01E01",
            "from": "real",
            "to": "nonexistent",
            "reason": "test",
        })]

        apply_verdicts(verdicts, plotlines, episodes)

        assert episodes[0].events[0].plotline_id == "real"

    def test_merge_with_nonexistent_target_skipped(self):
        plotlines = [_make_plotline("source")]
        episodes = [_make_episode("S01E01", [
            {"event": "event one", "plotline_id": "source"},
        ])]
        verdicts = [Verdict(action="MERGE", data={
            "source": "source",
            "target": "nonexistent",
            "reason": "test",
        })]

        result = apply_verdicts(verdicts, plotlines, episodes)

        assert len(result) == 1
        assert result[0].id == "source"

    def test_drop_with_nonexistent_redistribute_target_skipped(self):
        plotlines = [_make_plotline("victim"), _make_plotline("other", computed_rank="B")]
        episodes = [_make_episode("S01E01", [
            {"event": "important event", "plotline_id": "victim"},
        ])]
        verdicts = [Verdict(action="DROP", data={
            "target": "victim",
            "redistribute": [
                {"event": "important event", "episode": "S01E01", "to": "nonexistent"},
            ],
            "reason": "test",
        })]

        result = apply_verdicts(verdicts, plotlines, episodes)

        assert any(p.id == "victim" for p in result)
        assert episodes[0].events[0].plotline_id == "victim"


class TestSafeDrop:
    """DROP should abort if any events remain unredistributed."""

    def test_drop_aborts_when_events_not_redistributed(self):
        plotlines = [_make_plotline("target"), _make_plotline("other", computed_rank="B")]
        episodes = [_make_episode("S01E01", [
            {"event": "event one", "plotline_id": "target"},
            {"event": "event two", "plotline_id": "target"},
            {"event": "event three", "plotline_id": "other"},
        ])]
        verdicts = [Verdict(action="DROP", data={
            "target": "target",
            "redistribute": [
                {"event": "event one", "episode": "S01E01", "to": "other"},
            ],
            "reason": "test",
        })]

        result = apply_verdicts(verdicts, plotlines, episodes)

        assert any(p.id == "target" for p in result)
        event_two = [e for e in episodes[0].events if e.event == "event two"][0]
        assert event_two.plotline_id == "target"

    def test_drop_succeeds_when_all_events_redistributed(self):
        plotlines = [_make_plotline("target"), _make_plotline("other", computed_rank="B")]
        episodes = [_make_episode("S01E01", [
            {"event": "event one", "plotline_id": "target"},
            {"event": "event three", "plotline_id": "other"},
        ])]
        verdicts = [Verdict(action="DROP", data={
            "target": "target",
            "redistribute": [
                {"event": "event one", "episode": "S01E01", "to": "other"},
            ],
            "reason": "test",
        })]

        result = apply_verdicts(verdicts, plotlines, episodes)

        assert not any(p.id == "target" for p in result)
        assert episodes[0].events[0].plotline_id == "other"

    def test_no_events_set_to_null(self):
        """Events must never have plotline_id set to null by DROP."""
        plotlines = [_make_plotline("target"), _make_plotline("other", computed_rank="B")]
        episodes = [_make_episode("S01E01", [
            {"event": f"event {i}", "plotline_id": "target"}
            for i in range(5)
        ])]
        verdicts = [Verdict(action="DROP", data={
            "target": "target",
            "redistribute": [],
            "reason": "test",
        })]

        apply_verdicts(verdicts, plotlines, episodes)

        for ep in episodes:
            for event in ep.events:
                assert event.plotline_id is not None
