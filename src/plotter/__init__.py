"""Plotter — extract storylines from TV series synopses using LLM."""

from plotter.callbacks import PipelineCallback
from plotter.models import (
    CastMember,
    EpisodeBreakdown,
    Event,
    Interaction,
    Patch,
    Plotline,
    PlotterResult,
    SeriesContext,
    Verdict,
)
from plotter.llm import UsageStats, usage
from plotter.pipeline import get_plotlines

__all__ = [
    "get_plotlines",
    "PipelineCallback",
    "CastMember",
    "EpisodeBreakdown",
    "Event",
    "Interaction",
    "Patch",
    "Plotline",
    "PlotterResult",
    "SeriesContext",
    "UsageStats",
    "usage",
    "Verdict",
]
