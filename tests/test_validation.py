"""Unit tests for validation logic in each pass (no LLM calls)."""

import pytest

from plotter.models import (
    CastMember,
    EpisodeBreakdown,
    Event,
    Interaction,
    Plotline,
    SeriesContext,
)
from plotter.pass0 import _validate as validate_pass0
from plotter.pass1 import _validate as validate_pass1
from plotter.pass2 import _validate as validate_pass2


# --- Pass 0 ---

class TestPass0Validation:
    def test_valid(self):
        validate_pass0({
            "franchise_type": "serial",
            "story_engine": "test engine",
            "genre": "drama",
            "format": "ongoing",
        })

    def test_invalid_franchise_type(self):
        with pytest.raises(ValueError, match="franchise_type"):
            validate_pass0({"franchise_type": "soap", "story_engine": "x"})

    def test_empty_story_engine(self):
        with pytest.raises(ValueError, match="story_engine"):
            validate_pass0({"franchise_type": "serial", "story_engine": ""})

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="format"):
            validate_pass0({
                "franchise_type": "serial",
                "story_engine": "x",
                "format": "miniseries",
            })

    def test_null_format_ok(self):
        validate_pass0({
            "franchise_type": "serial",
            "story_engine": "x",
            "format": None,
        })


# --- Pass 1 ---

def _make_cast():
    return [
        CastMember(id="walt", name="Walter White"),
        CastMember(id="jesse", name="Jesse Pinkman"),
    ]


def _make_storylines():
    return [
        Plotline(
            id="empire", name="Empire", driver="walt",
            goal="build empire", obstacle="morality", stakes="death",
            type="serialized", rank="A", nature="plot-led", confidence="solid",
        ),
        Plotline(
            id="partnership", name="Partnership", driver="jesse",
            goal="survive", obstacle="fear", stakes="prison",
            type="serialized", rank="B", nature="character-led", confidence="solid",
        ),
    ]


class TestPass1Validation:
    def test_valid(self):
        ctx = SeriesContext(franchise_type="serial", story_engine="x", genre="drama")
        validate_pass1(_make_storylines(), _make_cast(), ctx)

    def test_no_storylines(self):
        ctx = SeriesContext(franchise_type="serial", story_engine="x", genre="drama")
        with pytest.raises(ValueError, match="No storylines"):
            validate_pass1([], _make_cast(), ctx)

    def test_no_cast(self):
        ctx = SeriesContext(franchise_type="serial", story_engine="x", genre="drama")
        with pytest.raises(ValueError, match="No cast"):
            validate_pass1(_make_storylines(), [], ctx)

    def test_invalid_type(self):
        ctx = SeriesContext(franchise_type="serial", story_engine="x", genre="drama")
        lines = _make_storylines()
        lines[0].type = "anthology"
        with pytest.raises(ValueError, match="invalid type"):
            validate_pass1(lines, _make_cast(), ctx)

    def test_procedural_needs_episodic(self):
        ctx = SeriesContext(franchise_type="procedural", story_engine="x", genre="drama")
        with pytest.raises(ValueError, match="episodic"):
            validate_pass1(_make_storylines(), _make_cast(), ctx)

    def test_serial_rejects_multiple_a_rank(self):
        ctx = SeriesContext(franchise_type="serial", story_engine="x", genre="drama")
        lines = _make_storylines()
        lines[1].rank = "A"  # now both are A
        with pytest.raises(ValueError, match="1 A-rank"):
            validate_pass1(lines, _make_cast(), ctx)

    def test_serial_accepts_one_a_rank(self):
        ctx = SeriesContext(franchise_type="serial", story_engine="x", genre="drama")
        validate_pass1(_make_storylines(), _make_cast(), ctx)  # 1 A + 1 B

    def test_ensemble_needs_multiple_a_rank(self):
        ctx = SeriesContext(franchise_type="ensemble", story_engine="x", genre="drama")
        lines = _make_storylines()  # 1 A + 1 B
        with pytest.raises(ValueError, match="2\\+ A-rank"):
            validate_pass1(lines, _make_cast(), ctx)

    def test_ensemble_accepts_multiple_a_rank(self):
        ctx = SeriesContext(franchise_type="ensemble", story_engine="x", genre="drama")
        lines = _make_storylines()
        lines[1].rank = "A"  # both A
        validate_pass1(lines, _make_cast(), ctx)


# --- Pass 2 ---

def _make_breakdown():
    return EpisodeBreakdown(
        episode="S01E01",
        events=[
            Event(
                event="Walt cooks", storyline="empire",
                function="setup", characters=["walt", "jesse"],
            ),
            Event(
                event="Jesse runs", storyline="partnership",
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
        validate_pass2(_make_breakdown(), _make_storylines(), _make_cast())

    def test_invalid_function(self):
        bd = _make_breakdown()
        bd.events[0].function = "explosion"
        with pytest.raises(ValueError, match="invalid function"):
            validate_pass2(bd, _make_storylines(), _make_cast())

    def test_unknown_storyline(self):
        bd = _make_breakdown()
        bd.events[0].storyline = "nonexistent"
        with pytest.raises(ValueError, match="not found in Pass 1"):
            validate_pass2(bd, _make_storylines(), _make_cast())

    def test_unknown_character(self):
        bd = _make_breakdown()
        bd.events[0].characters = ["unknown_person"]
        with pytest.raises(ValueError, match="not in cast"):
            validate_pass2(bd, _make_storylines(), _make_cast())

    def test_guest_character_ok(self):
        bd = _make_breakdown()
        bd.events[0].characters = ["walt", "guest:patient"]
        validate_pass2(bd, _make_storylines(), _make_cast())

    def test_null_storyline_ok(self):
        """A few unassigned events (-> ADD_LINE patch) should pass validation."""
        bd = _make_breakdown()
        # Add enough events so that 1 null is under the 10% threshold
        for i in range(10):
            bd.events.append(Event(
                event=f"filler {i}", storyline="empire",
                function="escalation", characters=["walt"],
            ))
        bd.events[0].storyline = None
        validate_pass2(bd, _make_storylines(), _make_cast())

    def test_invalid_interaction_type(self):
        bd = _make_breakdown()
        bd.interactions[0].type = "magic"
        with pytest.raises(ValueError, match="invalid type"):
            validate_pass2(bd, _make_storylines(), _make_cast())
