"""Tests for verdict application (Pass 3 results → data changes)."""

from __future__ import annotations

import pytest

from tvplotlines.models import (
    CastMember,
    EpisodeBreakdown,
    Event,
    Plotline,
    Verdict,
)
from tvplotlines.verdicts import apply_verdicts


def _make_plotlines() -> list[Plotline]:
    return [
        Plotline(
            id="belonging", name="Belonging", hero="andrey",
            goal="join the gang", obstacle="violence", stakes="family",
            type="serialized", rank="A", nature="character-led", confidence="solid",
        ),
        Plotline(
            id="brotherhood", name="Brotherhood", hero="marat",
            goal="balance love and gang", obstacle="conflict", stakes="loss",
            type="serialized", rank="A", nature="character-led", confidence="solid",
        ),
        Plotline(
            id="redemption", name="Redemption", hero="ira",
            goal="save Andrey", obstacle="distrust", stakes="failure",
            type="serialized", rank="C", nature="character-led", confidence="solid",
        ),
    ]


def _make_episodes() -> list[EpisodeBreakdown]:
    return [
        EpisodeBreakdown(
            episode="S01E01",
            events=[
                Event(event="Andrey joins the gang", plotline="belonging",
                      function="setup", characters=["andrey"]),
                Event(event="Marat fights for honor", plotline="brotherhood",
                      function="escalation", characters=["marat"]),
                Event(event="Ira visits the school", plotline="redemption",
                      function="setup", characters=["ira"]),
                Event(event="Unknown event", plotline=None,
                      function="setup", characters=["andrey"]),
            ],
            theme="belonging",
        ),
        EpisodeBreakdown(
            episode="S01E02",
            events=[
                Event(event="Andrey proves himself", plotline="belonging",
                      function="escalation", characters=["andrey"]),
                Event(event="Marat meets Aygul", plotline="brotherhood",
                      function="setup", characters=["marat"]),
            ],
            theme="loyalty",
        ),
    ]


class TestMerge:
    def test_merge_reassigns_events(self):
        plotlines = _make_plotlines()
        episodes = _make_episodes()

        verdicts = [Verdict(action="MERGE", data={
            "source": "redemption",
            "target": "belonging",
            "reason": "same driver concern",
        })]

        result = apply_verdicts(verdicts, plotlines, episodes)

        # Source plotline removed
        ids = [p.id for p in result]
        assert "redemption" not in ids
        assert "belonging" in ids

        # Events reassigned
        ep1_events = episodes[0].events
        ira_event = next(e for e in ep1_events if e.event == "Ira visits the school")
        assert ira_event.plotline == "belonging"

    def test_merge_updates_also_affects(self):
        plotlines = _make_plotlines()
        episodes = [EpisodeBreakdown(
            episode="S01E01",
            events=[
                Event(event="Cross event", plotline="belonging",
                      function="setup", characters=["andrey"],
                      also_affects=["redemption"]),
            ],
        )]

        verdicts = [Verdict(action="MERGE", data={
            "source": "redemption", "target": "brotherhood", "reason": "test",
        })]

        apply_verdicts(verdicts, plotlines, episodes)

        assert episodes[0].events[0].also_affects == ["brotherhood"]


class TestReassign:
    def test_reassign_changes_plotline(self):
        plotlines = _make_plotlines()
        episodes = _make_episodes()

        verdicts = [Verdict(action="REASSIGN", data={
            "event": "Unknown event",
            "episode": "S01E01",
            "from": None,
            "to": "belonging",
            "reason": "fits belonging arc",
        })]

        apply_verdicts(verdicts, plotlines, episodes)

        event = next(e for e in episodes[0].events if e.event == "Unknown event")
        assert event.plotline == "belonging"


class TestPromoteDemote:
    def test_promote(self):
        plotlines = _make_plotlines()
        episodes = _make_episodes()

        verdicts = [Verdict(action="PROMOTE", data={
            "target": "redemption",
            "new_rank": "B",
            "reason": "more weight than expected",
        })]

        result = apply_verdicts(verdicts, plotlines, episodes)

        redemption = next(p for p in result if p.id == "redemption")
        assert redemption.rank == "B"

    def test_demote(self):
        plotlines = _make_plotlines()
        episodes = _make_episodes()

        verdicts = [Verdict(action="DEMOTE", data={
            "target": "brotherhood",
            "new_rank": "B",
            "reason": "less weight than A",
        })]

        result = apply_verdicts(verdicts, plotlines, episodes)

        brotherhood = next(p for p in result if p.id == "brotherhood")
        assert brotherhood.rank == "B"


class TestCreate:
    def test_create_adds_plotline_and_reassigns(self):
        plotlines = _make_plotlines()
        episodes = _make_episodes()

        verdicts = [Verdict(action="CREATE", data={
            "plotline": {
                "id": "investigation",
                "name": "Investigation",
                "hero": "ildar",
                "goal": "catch the gang",
                "obstacle": "no evidence",
                "stakes": "criminals go free",
                "type": "serialized",
                "rank": "C",
                "nature": "plot-led",
            },
            "reassign_events": [
                {"event": "Unknown event", "episode": "S01E01"},
            ],
            "reason": "orphaned events form a pattern",
        })]

        result = apply_verdicts(verdicts, plotlines, episodes)

        # New plotline added
        ids = [p.id for p in result]
        assert "investigation" in ids

        # Event reassigned
        event = next(e for e in episodes[0].events if e.event == "Unknown event")
        assert event.plotline == "investigation"

        # New plotline has inferred confidence
        investigation = next(p for p in result if p.id == "investigation")
        assert investigation.confidence == "inferred"


class TestDrop:
    def test_drop_removes_and_redistributes(self):
        plotlines = _make_plotlines()
        episodes = _make_episodes()

        verdicts = [Verdict(action="DROP", data={
            "target": "redemption",
            "redistribute": [
                {"event": "Ira visits the school", "episode": "S01E01", "to": "belonging"},
            ],
            "reason": "not a real plotline",
        })]

        result = apply_verdicts(verdicts, plotlines, episodes)

        # Plotline removed
        ids = [p.id for p in result]
        assert "redemption" not in ids

        # Event redistributed
        event = next(e for e in episodes[0].events if e.event == "Ira visits the school")
        assert event.plotline == "belonging"


class TestOriginalNotMutated:
    def test_original_plotlines_not_mutated(self):
        """apply_verdicts should not mutate the original plotlines list."""
        plotlines = _make_plotlines()
        original_ids = [p.id for p in plotlines]
        episodes = _make_episodes()

        verdicts = [Verdict(action="DROP", data={
            "target": "redemption",
            "redistribute": [
                {"event": "Ira visits the school", "episode": "S01E01", "to": "belonging"},
            ],
            "reason": "test",
        })]

        result = apply_verdicts(verdicts, plotlines, episodes)

        # Original list unchanged
        assert [p.id for p in plotlines] == original_ids
        # Result is different
        assert len(result) == len(plotlines) - 1


class TestMultipleVerdicts:
    def test_create_then_reassign_to_new(self):
        """CREATE a line, then REASSIGN an event to it in the same batch."""
        plotlines = _make_plotlines()
        episodes = _make_episodes()

        verdicts = [
            Verdict(action="CREATE", data={
                "plotline": {
                    "id": "new_line",
                    "name": "New",
                    "hero": "andrey",
                    "goal": "new goal",
                    "obstacle": "new obstacle",
                    "stakes": "new stakes",
                    "type": "serialized",
                    "rank": "B",
                    "nature": "character-led",
                },
                "reassign_events": [],
                "reason": "test",
            }),
            Verdict(action="REASSIGN", data={
                "event": "Unknown event",
                "episode": "S01E01",
                "from": None,
                "to": "new_line",
                "reason": "test",
            }),
        ]

        result = apply_verdicts(verdicts, plotlines, episodes)

        assert "new_line" in [p.id for p in result]
        event = next(e for e in episodes[0].events if e.event == "Unknown event")
        assert event.plotline == "new_line"
