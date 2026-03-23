"""Smoke tests for data models."""

from tvplotlines.models import CastMember, Plotline, TVPlotlinesResult, SeriesContext


def test_plotline_creation():
    line = Plotline(
        id="empire",
        name="Empire",
        driver="walt",
        goal="построить наркобизнес",
        obstacle="моральный выбор",
        stakes="смерть",
        type="serialized",
        rank="A",
        nature="plot-led",
        confidence="solid",
    )
    assert line.id == "empire"
    assert line.span == []


def test_tvplotlines_result_creation():
    ctx = SeriesContext(
        franchise_type="serial",
        story_engine="test engine",
        genre="drama",
    )
    result = TVPlotlinesResult(context=ctx)
    assert result.cast == []
    assert result.plotlines == []
    assert result.episodes == []
