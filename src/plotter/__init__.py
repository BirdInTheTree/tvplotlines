"""Plotter — extract storylines from TV series synopses using LLM."""

from plotter.models import (
    CastMember,
    EpisodeBreakdown,
    Event,
    Interaction,
    Patch,
    Plotline,
    PlotterResult,
    SeriesContext,
)
from plotter.pipeline import get_plotlines

__all__ = [
    "get_plotlines",
    "CastMember",
    "EpisodeBreakdown",
    "Event",
    "Interaction",
    "Patch",
    "Plotline",
    "PlotterResult",
    "SeriesContext",
]
