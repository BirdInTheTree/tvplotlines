"""Tests for prior season continuity in pipeline."""

import pytest

from plotter.models import (
    CastMember,
    Plotline,
    PlotterResult,
    SeriesContext,
)


def _make_prior() -> PlotterResult:
    ctx = SeriesContext(
        franchise_type="serial",
        story_engine="A teacher builds a drug empire",
        genre="drama",
        format="ongoing",
    )
    cast = [
        CastMember(id="walt", name="Walter White", aliases=["Walt"]),
        CastMember(id="jesse", name="Jesse Pinkman", aliases=["Jesse"]),
    ]
    plotlines = [
        Plotline(
            id="empire", name="Walt: Empire", driver="walt",
            goal="build a drug business", obstacle="morality", stakes="death",
            type="serialized", rank="A", nature="plot-led", confidence="solid",
        ),
    ]
    return PlotterResult(context=ctx, cast=cast, plotlines=plotlines)


class TestPriorContextReuse:
    def test_prior_provides_context_when_context_is_none(self, monkeypatch):
        """If prior is given and context is not, pipeline should use prior.context
        and NOT call detect_context (Pass 0)."""
        from unittest.mock import MagicMock
        import plotter.pipeline as pipeline_mod

        prior = _make_prior()
        mock_detect = MagicMock(side_effect=AssertionError("Pass 0 should be skipped"))
        monkeypatch.setattr(pipeline_mod, "detect_context", mock_detect)
        mock_extract = MagicMock(return_value=(prior.cast, prior.plotlines))
        monkeypatch.setattr(pipeline_mod, "extract_storylines", mock_extract)

        try:
            pipeline_mod.get_plotlines("Breaking Bad", 2, ["synopsis"], prior=prior)
        except Exception:
            pass

        mock_detect.assert_not_called()
        mock_extract.assert_called_once()
        call_kwargs = mock_extract.call_args.kwargs
        assert call_kwargs["prior_cast"] == prior.cast
        assert call_kwargs["prior_plotlines"] == prior.plotlines

    def test_prior_ignored_when_cast_and_plotlines_provided(self, monkeypatch):
        """When cast+plotlines are provided (Pass 1 skip), prior only affects context."""
        from unittest.mock import MagicMock
        import plotter.pipeline as pipeline_mod

        prior = _make_prior()
        explicit_cast = [CastMember(id="custom", name="Custom")]
        explicit_plotlines = [
            Plotline(
                id="custom_line", name="Custom", driver="custom",
                goal="g", obstacle="o", stakes="s",
                type="serialized", rank="A", nature="plot-led", confidence="solid",
            ),
        ]
        mock_extract = MagicMock()
        monkeypatch.setattr(pipeline_mod, "extract_storylines", mock_extract)

        try:
            pipeline_mod.get_plotlines(
                "Breaking Bad", 2, ["synopsis"],
                prior=prior, cast=explicit_cast, plotlines=explicit_plotlines,
            )
        except Exception:
            pass

        mock_extract.assert_not_called()

    def test_anthology_raises_with_prior(self):
        """Anthology format + prior is contradictory."""
        from plotter.pipeline import get_plotlines

        prior = _make_prior()
        prior.context.format = "anthology"
        with pytest.raises(ValueError, match="anthology"):
            get_plotlines(
                "Test Show", 2, ["synopsis"],
                prior=prior,
            )
