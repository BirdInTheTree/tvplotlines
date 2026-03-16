"""Main pipeline: get_plotlines() orchestrates Pass 0 → Pass 1 → Pass 2 → Pass 3 → post-processing."""

from __future__ import annotations

import logging
import re

from plotter.callbacks import PipelineCallback
from plotter.llm import LLMConfig, UsageStats, usage
from plotter.models import CastMember, EpisodeBreakdown, Plotline, PlotterResult, SeriesContext
from plotter.pass0 import detect_context
from plotter.pass1 import extract_storylines
from plotter.pass2 import assign_events, assign_events_batch, assign_events_parallel
from plotter.pass3 import review_storylines
from plotter.postprocess import assign_orphan_events, compute_span, validate_ranks
from plotter.verdicts import apply_verdicts

logger = logging.getLogger(__name__)

_EPISODE_ID_RE = re.compile(r"^S\d{2}E\d{2}$")


def _fire(callback: PipelineCallback | None, method: str, *args) -> None:
    """Call a callback method, swallowing exceptions."""
    if callback is None:
        return
    try:
        getattr(callback, method)(*args)
    except Exception:
        logger.exception("Callback %s raised", method)


def get_plotlines(
    show: str,
    season: int,
    episodes: dict[str, str],
    *,
    prior: PlotterResult | None = None,
    context: SeriesContext | None = None,
    cast: list[CastMember] | None = None,
    plotlines: list[Plotline] | None = None,
    breakdowns: list[EpisodeBreakdown] | None = None,
    llm_provider: str = "anthropic",
    model: str | None = None,
    base_url: str | None = None,
    lang: str = "en",
    skip_review: bool = False,
    pass2_mode: str = "parallel",
    batch_id: str | None = None,
    callback: PipelineCallback | None = None,
) -> PlotterResult:
    """Extract storylines from TV series synopses.

    Args:
        show: Series title.
        season: Season number.
        episodes: Dict mapping episode IDs (e.g. "S01E01") to synopsis texts.
            Keys must match S{dd}E{dd} format and the season number must match
            the ``season`` parameter.
        prior: PlotterResult from the previous season. When provided and
            context is None, reuses prior.context to skip Pass 0. Also
            passes prior cast and plotlines to Pass 1 for continuity.
            Incompatible with anthology format (anthology seasons are
            independent by definition).
        context: If provided, skip Pass 0 (auto-detection).
        cast: If provided with plotlines, skip Pass 1.
        plotlines: If provided with cast, skip Pass 1.
        breakdowns: If provided, skip Pass 2.
        llm_provider: "anthropic" or "openai".
        model: Specific model name, or provider default.
        skip_review: If True, skip Pass 3 (narratologist review).
        pass2_mode: How to run Pass 2:
            "parallel" — all episodes at once via async (fast, default)
            "batch" — Anthropic batch API (50% cheaper, slower)
            "sequential" — one episode at a time (simple, for debugging)
        batch_id: Resume a batch by ID (only with pass2_mode="batch").
        callback: PipelineCallback subclass for progress notifications.

    Returns:
        PlotterResult with context, cast, plotlines, and episode breakdowns.
    """
    config = LLMConfig(provider=llm_provider, model=model, base_url=base_url, lang=lang)

    # Validate episode keys and convert to sorted (id, text) pairs
    season_prefix = f"S{season:02d}"
    for key in episodes:
        if not _EPISODE_ID_RE.match(key):
            raise ValueError(
                f"Episode key {key!r} must match S{{dd}}E{{dd}} format (e.g. 'S01E01')"
            )
        if not key.startswith(season_prefix):
            raise ValueError(
                f"Episode key {key!r} does not match season={season} "
                f"(expected prefix {season_prefix!r})"
            )
    episode_pairs = [(eid, episodes[eid]) for eid in sorted(episodes)]
    episode_ids = [eid for eid, _ in episode_pairs]
    episode_texts = [text for _, text in episode_pairs]

    # Validate resume parameters
    if (cast is None) != (plotlines is None):
        raise ValueError("cast and plotlines must be provided together (or both omitted)")

    if breakdowns is not None and len(breakdowns) != len(episode_ids):
        raise ValueError(
            f"breakdowns length ({len(breakdowns)}) != episodes length ({len(episode_ids)})"
        )

    if batch_id is not None and pass2_mode != "batch":
        raise ValueError(f"batch_id requires pass2_mode='batch', got {pass2_mode!r}")

    # Validate prior parameter
    if prior is not None:
        prior_context = context or prior.context
        if prior_context.format == "anthology":
            raise ValueError(
                "prior is not supported for anthology format "
                "(anthology seasons are independent by definition)"
            )
        if context is None:
            context = prior.context

    # Reset usage tracker for this run
    global usage
    usage.__init__()

    # Pass 0: detect context (skip if provided)
    if context is None:
        context = detect_context(show, season, episode_pairs[:3], config=config)
    _fire(callback, "on_pass0_complete", context)

    # Pass 1: extract cast and plotlines from all synopses
    if cast is None:
        cast, plotlines = extract_storylines(
            show, season, context, episode_pairs,
            prior_cast=prior.cast if prior else None,
            prior_plotlines=prior.plotlines if prior else None,
            config=config,
        )
    _fire(callback, "on_pass1_complete", cast, plotlines)

    # Pass 2: assign events for each episode
    if breakdowns is None:
        if pass2_mode == "parallel":
            breakdowns = assign_events_parallel(
                show, season, episode_pairs, context, cast, plotlines,
                config=config,
            )
        elif pass2_mode == "batch":
            breakdowns = assign_events_batch(
                show, season, episode_pairs, context, cast, plotlines,
                config=config,
                batch_id=batch_id,
                on_batch_submitted=lambda bid: _fire(callback, "on_batch_submitted", bid),
            )
        elif pass2_mode == "sequential":
            breakdowns = []
            for i, (episode_id, synopsis) in enumerate(episode_pairs):
                breakdown = assign_events(
                    show, season, episode_id, synopsis, context, cast, plotlines,
                    config=config,
                )
                breakdowns.append(breakdown)
                _fire(callback, "on_episode_complete", i, breakdown)
        else:
            raise ValueError(f"Unknown pass2_mode: {pass2_mode!r}")

    _fire(callback, "on_pass2_complete", breakdowns)

    # Post-processing: assign orphan events, compute span, validate ranks
    assign_orphan_events(plotlines, breakdowns)
    compute_span(plotlines, breakdowns)
    flags = validate_ranks(plotlines, breakdowns)

    # Pass 3: narratologist review (with diagnostic flags as context)
    if not skip_review:
        verdicts = review_storylines(
            show, season, context, cast, plotlines, breakdowns,
            diagnostics=flags or None,
            config=config,
        )
        _fire(callback, "on_pass3_complete", verdicts)
        if verdicts:
            plotlines = apply_verdicts(verdicts, plotlines, breakdowns)
            # Recompute span and re-validate after verdicts
            compute_span(plotlines, breakdowns)
            validate_ranks(plotlines, breakdowns)

    result = PlotterResult(
        context=context,
        cast=cast,
        plotlines=plotlines,
        episodes=breakdowns,
    )
    result.usage = usage.summary(config.resolved_model)
    return result
