"""tvplotlines — extract plotlines from TV series synopses using LLM."""

from tvplotlines.callbacks import PipelineCallback
from tvplotlines.models import (
    CastMember,
    EpisodeBreakdown,
    Event,
    Interaction,
    Patch,
    Plotline,
    TVPlotlinesResult,
    SeriesContext,
    Verdict,
)
from tvplotlines.llm import UsageStats, usage
from tvplotlines.pipeline import get_plotlines

__all__ = [
    "get_plotlines",
    "PipelineCallback",
    "CastMember",
    "EpisodeBreakdown",
    "Event",
    "Interaction",
    "Patch",
    "Plotline",
    "TVPlotlinesResult",
    "SeriesContext",
    "UsageStats",
    "usage",
    "Verdict",
]
