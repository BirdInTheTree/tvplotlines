"""Main pipeline: get_plotlines() orchestrates Pass 0 → Pass 1 → Pass 2 → Pass 3 → post-processing."""

from __future__ import annotations

from plotter.llm import LLMConfig, UsageStats, usage
from plotter.models import PlotterResult, SeriesContext
from plotter.pass0 import detect_context
from plotter.pass1 import extract_storylines
from plotter.pass2 import assign_events, assign_events_batch, assign_events_parallel
from plotter.pass3 import review_storylines
from plotter.postprocess import assign_orphan_events, compute_span
from plotter.verdicts import apply_verdicts


def get_plotlines(
    show: str,
    season: int,
    episodes: list[str],
    *,
    context: SeriesContext | None = None,
    llm_provider: str = "anthropic",
    model: str | None = None,
    lang: str = "en",
    skip_review: bool = False,
    pass2_mode: str = "parallel",
) -> PlotterResult:
    """Extract storylines from TV series synopses.

    Runs the full pipeline: Pass 0 (context) → Pass 1 (storylines) →
    Pass 2 (events per episode) → Pass 3 (narratologist review) →
    post-processing (span).

    Args:
        show: Series title.
        season: Season number.
        episodes: Synopsis text for each episode (full season).
        context: If provided, skip Pass 0 (auto-detection).
        llm_provider: "anthropic" or "openai".
        model: Specific model name, or provider default.
        skip_review: If True, skip Pass 3 (narratologist review).
        pass2_mode: How to run Pass 2:
            "parallel" — all episodes at once via async (fast, default)
            "batch" — Anthropic batch API (50% cheaper, slower)
            "sequential" — one episode at a time (simple, for debugging)

    Returns:
        PlotterResult with context, cast, plotlines, and episode breakdowns.
    """
    config = LLMConfig(provider=llm_provider, model=model, lang=lang)

    # Reset usage tracker for this run
    global usage
    usage.__init__()

    # Pass 0: detect context (skip if provided)
    if context is None:
        context = detect_context(show, season, episodes, config=config)

    # Pass 1: extract cast and storylines from all synopses
    cast, storylines = extract_storylines(
        show, season, context, episodes, config=config,
    )

    # Pass 2: assign events for each episode
    if pass2_mode == "parallel":
        breakdowns = assign_events_parallel(
            show, season, episodes, context, cast, storylines,
            config=config,
        )
    elif pass2_mode == "batch":
        breakdowns = assign_events_batch(
            show, season, episodes, context, cast, storylines,
            config=config,
        )
    else:
        breakdowns = []
        for i, synopsis in enumerate(episodes):
            breakdown = assign_events(
                show, season, i + 1, synopsis, context, cast, storylines,
                config=config,
            )
            breakdowns.append(breakdown)

    # Post-processing: assign orphan events, then compute span
    assign_orphan_events(storylines, breakdowns)
    compute_span(storylines, breakdowns)

    # Pass 3: narratologist review
    if not skip_review:
        verdicts = review_storylines(
            show, season, context, cast, storylines, breakdowns,
            config=config,
        )
        if verdicts:
            storylines = apply_verdicts(verdicts, storylines, breakdowns)
            # Recompute span after verdicts changed assignments
            compute_span(storylines, breakdowns)

    result = PlotterResult(
        context=context,
        cast=cast,
        plotlines=storylines,
        episodes=breakdowns,
    )
    result.usage = usage.summary(config.resolved_model)
    return result
