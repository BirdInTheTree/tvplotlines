"""Tests for data model serialization."""

import json

from tvplotlines.models import (
    CastMember,
    EpisodeBreakdown,
    Event,
    Plotline,
    SeriesContext,
    TVPlotlinesResult,
)


def _make_result() -> TVPlotlinesResult:
    return TVPlotlinesResult(
        context=SeriesContext(
            format="serial",
            story_engine="A teacher builds a drug empire",
            genre="drama",
        ),
        cast=[CastMember(id="walt", name="Walter White", aliases=["Walt"])],
        plotlines=[
            Plotline(
                id="empire", name="Walt: Empire", hero="walt",
                goal="build a drug business", obstacle="violent dealers",
                stakes="death", type="serialized",
                nature="plot-led", confidence="solid",
                computed_rank="A", span=["S01E01"],
            ),
        ],
        episodes=[
            EpisodeBreakdown(
                episode="S01E01",
                events=[
                    Event(
                        event="Walt meets Jesse",
                        plotline_id="empire",
                        function="inciting_incident",
                        characters=["walt", "jesse"],
                    ),
                ],
                theme="transformation",
            ),
        ],
    )


def test_to_dict_is_json_serializable():
    """to_dict() output must be valid for json.dumps."""
    result = _make_result()
    d = result.to_dict()
    text = json.dumps(d, ensure_ascii=False)
    parsed = json.loads(text)
    assert parsed["context"]["format"] == "serial"
    assert parsed["plotlines"][0]["id"] == "empire"
    assert parsed["episodes"][0]["events"][0]["plotline_id"] == "empire"


def test_to_dict_preserves_structure():
    """All fields present in serialized output."""
    result = _make_result()
    d = result.to_dict()
    assert "context" in d
    assert "cast" in d
    assert "plotlines" in d
    assert "episodes" in d
    assert d["cast"][0]["aliases"] == ["Walt"]
    assert d["plotlines"][0]["span"] == ["S01E01"]
    assert d["episodes"][0]["theme"] == "transformation"


def test_to_dict_event_fields():
    """Event serialization uses plotline_id, not plotline."""
    result = _make_result()
    event = result.to_dict()["episodes"][0]["events"][0]
    assert "plotline_id" in event
    assert "plotline" not in event
    assert event["characters"] == ["walt", "jesse"]
