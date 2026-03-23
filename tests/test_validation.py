"""Unit tests for validation logic in each pass (no LLM calls)."""

import pytest

from tvplotlines.models import (
    CastMember,
    EpisodeBreakdown,
    Event,
    Interaction,
    Plotline,
    SeriesContext,
)
from tvplotlines.pass0 import _validate as validate_pass0
from tvplotlines.pass1 import _validate as validate_pass1
from tvplotlines.pass2 import _validate as validate_pass2


# --- Pass 0 ---

class TestPass0Validation:
    def test_valid(self):
        validate_pass0({
            "format": "serial",
            "story_engine": "test engine",
            "genre": "drama",
            "is_ensemble": False,
            "is_anthology": False,
        })

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="format"):
            validate_pass0({
                "format": "miniseries",
                "story_engine": "x",
                "is_ensemble": False,
                "is_anthology": False,
            })

    def test_empty_story_engine(self):
        with pytest.raises(ValueError, match="story_engine"):
            validate_pass0({
                "format": "serial",
                "story_engine": "",
                "is_ensemble": False,
                "is_anthology": False,
            })

    def test_is_ensemble_must_be_bool(self):
        with pytest.raises(ValueError, match="is_ensemble"):
            validate_pass0({
                "format": "serial",
                "story_engine": "x",
                "is_ensemble": "yes",
                "is_anthology": False,
            })

    def test_is_anthology_must_be_bool(self):
        with pytest.raises(ValueError, match="is_anthology"):
            validate_pass0({
                "format": "serial",
                "story_engine": "x",
                "is_ensemble": False,
                "is_anthology": "yes",
            })


# --- Pass 1 ---

def _make_cast():
    return [
        CastMember(id="walt", name="Walter White"),
        CastMember(id="jesse", name="Jesse Pinkman"),
    ]


def _make_plotlines():
    return [
        Plotline(
            id="empire", name="Empire", hero="walt",
            goal="build empire", obstacle="morality", stakes="death",
            type="serialized", rank="A", nature="plot-led", confidence="solid",
        ),
        Plotline(
            id="partnership", name="Partnership", hero="jesse",
            goal="survive", obstacle="fear", stakes="prison",
            type="serialized", rank="B", nature="character-led", confidence="solid",
        ),
    ]


class TestPass1Validation:
    def test_valid(self):
        ctx = SeriesContext(format="serial", story_engine="x", genre="drama")
        validate_pass1(_make_plotlines(), _make_cast(), ctx)

    def test_no_plotlines(self):
        ctx = SeriesContext(format="serial", story_engine="x", genre="drama")
        with pytest.raises(ValueError, match="No plotlines"):
            validate_pass1([], _make_cast(), ctx)

    def test_no_cast(self):
        ctx = SeriesContext(format="serial", story_engine="x", genre="drama")
        with pytest.raises(ValueError, match="No cast"):
            validate_pass1(_make_plotlines(), [], ctx)

    def test_invalid_type(self):
        ctx = SeriesContext(format="serial", story_engine="x", genre="drama")
        lines = _make_plotlines()
        lines[0].type = "anthology"
        with pytest.raises(ValueError, match="invalid type"):
            validate_pass1(lines, _make_cast(), ctx)

    def test_procedural_needs_case_of_the_week(self):
        ctx = SeriesContext(format="procedural", story_engine="x", genre="drama")
        with pytest.raises(ValueError, match="case_of_the_week"):
            validate_pass1(_make_plotlines(), _make_cast(), ctx)

    def test_serial_rejects_multiple_a_rank(self):
        ctx = SeriesContext(format="serial", story_engine="x", genre="drama")
        lines = _make_plotlines()
        lines[1].rank = "A"  # now both are A
        with pytest.raises(ValueError, match="1 A-rank"):
            validate_pass1(lines, _make_cast(), ctx)

    def test_serial_accepts_one_a_rank(self):
        ctx = SeriesContext(format="serial", story_engine="x", genre="drama")
        validate_pass1(_make_plotlines(), _make_cast(), ctx)  # 1 A + 1 B

    def test_ensemble_needs_multiple_a_rank(self):
        ctx = SeriesContext(
            format="serial", story_engine="x", genre="drama", is_ensemble=True,
        )
        lines = _make_plotlines()  # 1 A + 1 B
        with pytest.raises(ValueError, match="2\\+ A-rank"):
            validate_pass1(lines, _make_cast(), ctx)

    def test_ensemble_accepts_multiple_a_rank(self):
        ctx = SeriesContext(
            format="serial", story_engine="x", genre="drama", is_ensemble=True,
        )
        lines = _make_plotlines()
        lines[1].rank = "A"  # both A
        validate_pass1(lines, _make_cast(), ctx)


# --- Pass 2 ---

def _make_breakdown():
    return EpisodeBreakdown(
        episode="S01E01",
        events=[
            Event(
                event="Walt cooks", plotline="empire",
                function="setup", characters=["walt", "jesse"],
            ),
            Event(
                event="Jesse runs", plotline="partnership",
                function="escalation", characters=["jesse"],
            ),
        ],
        theme="control",
        interactions=[
            Interaction(
                type="thematic_rhyme",
                lines=["empire", "partnership"],
                description="both about control",
            ),
        ],
    )


class TestPass2Validation:
    def test_valid(self):
        validate_pass2(_make_breakdown(), _make_plotlines(), _make_cast())

    def test_invalid_function(self):
        bd = _make_breakdown()
        bd.events[0].function = "explosion"
        with pytest.raises(ValueError, match="invalid function"):
            validate_pass2(bd, _make_plotlines(), _make_cast())

    def test_unknown_plotline(self):
        bd = _make_breakdown()
        bd.events[0].plotline = "nonexistent"
        with pytest.raises(ValueError, match="not found in plotlines"):
            validate_pass2(bd, _make_plotlines(), _make_cast())

    def test_unknown_character(self):
        bd = _make_breakdown()
        bd.events[0].characters = ["unknown_person"]
        with pytest.raises(ValueError, match="not in cast"):
            validate_pass2(bd, _make_plotlines(), _make_cast())

    def test_guest_character_ok(self):
        bd = _make_breakdown()
        bd.events[0].characters = ["walt", "guest:patient"]
        validate_pass2(bd, _make_plotlines(), _make_cast())

    def test_null_plotline_ok(self):
        """A few unassigned events (-> ADD_LINE patch) should pass validation."""
        bd = _make_breakdown()
        # Add enough events so that 1 null is under the 10% threshold
        for i in range(10):
            bd.events.append(Event(
                event=f"filler {i}", plotline="empire",
                function="escalation", characters=["walt"],
            ))
        bd.events[0].plotline = None
        validate_pass2(bd, _make_plotlines(), _make_cast())

    def test_invalid_interaction_type(self):
        bd = _make_breakdown()
        bd.interactions[0].type = "magic"
        with pytest.raises(ValueError, match="invalid type"):
            validate_pass2(bd, _make_plotlines(), _make_cast())
