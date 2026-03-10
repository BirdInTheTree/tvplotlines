"""Main pipeline: get_plotlines() orchestrates Pass 0 → Pass 1 → Pass 2 → post-processing."""

from __future__ import annotations

from plotter.llm import LLMConfig
from plotter.models import PlotterResult, SeriesContext
from plotter.pass0 import detect_context
from plotter.pass1 import extract_storylines
from plotter.pass2 import assign_events
from plotter.postprocess import aggregate_patches, compute_span


def get_plotlines(
    show: str,
    season: int,
    episodes: list[str],
    *,
    context: SeriesContext | None = None,
    llm_provider: str = "anthropic",
    model: str | None = None,
) -> PlotterResult:
    """Extract storylines from TV series synopses.

    Runs the full pipeline: Pass 0 (context) → Pass 1 (storylines) →
    Pass 2 (events per episode) → post-processing (span, patches).

    Args:
        show: Series title.
        season: Season number.
        episodes: Synopsis text for each episode (full season).
        context: If provided, skip Pass 0 (auto-detection).
        llm_provider: "anthropic" or "openai".
        model: Specific model name, or provider default.

    Returns:
        PlotterResult with context, cast, plotlines, and episode breakdowns.
    """
    config = LLMConfig(provider=llm_provider, model=model)

    # Pass 0: detect context (skip if provided)
    if context is None:
        context = detect_context(show, season, episodes, config=config)

    # Pass 1: extract cast and storylines from all synopses
    cast, storylines = extract_storylines(
        show, season, context, episodes, config=config,
    )

    # Pass 2: assign events for each episode
    breakdowns = []
    for i, synopsis in enumerate(episodes):
        breakdown = assign_events(
            show, season, i + 1, synopsis, context, cast, storylines,
            config=config,
        )
        breakdowns.append(breakdown)

    # Post-processing: compute span from Pass 2 results
    compute_span(storylines, breakdowns)

    # Collect patches for review
    patches = aggregate_patches(breakdowns)
    if patches:
        # TODO: apply patches — rerun Pass 1 if needed
        # For now, patches are available in each EpisodeBreakdown
        pass

    return PlotterResult(
        context=context,
        cast=cast,
        plotlines=storylines,
        episodes=breakdowns,
    )
