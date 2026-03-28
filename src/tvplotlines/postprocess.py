"""Post-processing: compute span, weight, rank.

These fields are derived from Pass 2 results, not from LLM.
"""

from __future__ import annotations

import logging
from collections import Counter

logger = logging.getLogger(__name__)

from tvplotlines.models import EpisodeBreakdown, Plotline, SeriesContext


def compute_span(
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
) -> None:
    """Fill Plotline.span from episode breakdowns (in-place).

    A plotline is present in an episode if it has at least one event there.
    """
    for plotline in plotlines:
        present_episodes = []
        for ep in episodes:
            has_event = any(
                e.plotline_id == plotline.id for e in ep.events
            )
            if has_event:
                present_episodes.append(ep.episode)
        plotline.span = present_episodes


def assign_orphan_events(
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
) -> None:
    """Assign null-plotline events to the most common plotline for their characters.

    For each unassigned event, find the plotline most frequently associated
    with its characters across the season. In-place modification.
    """
    # Build character → plotline frequency map from assigned events
    char_plotline_counts: dict[str, Counter[str]] = {}
    for ep in episodes:
        for event in ep.events:
            if event.plotline_id is None:
                continue
            for char in event.characters:
                if char not in char_plotline_counts:
                    char_plotline_counts[char] = Counter()
                char_plotline_counts[char][event.plotline_id] += 1

    plotline_ids = {p.id for p in plotlines}

    # Assign orphan events
    for ep in episodes:
        for event in ep.events:
            if event.plotline_id is not None:
                continue
            if not event.characters:
                continue

            # Aggregate plotline votes from all characters in this event
            votes: Counter[str] = Counter()
            for char in event.characters:
                if char in char_plotline_counts:
                    votes.update(char_plotline_counts[char])

            if not votes:
                # Fallback: use the most common plotline in this episode
                ep_counts: Counter[str] = Counter()
                for other in ep.events:
                    if other.plotline_id:
                        ep_counts[other.plotline_id] += 1
                if ep_counts:
                    votes = ep_counts

            if votes:
                best = votes.most_common(1)[0][0]
                if best in plotline_ids:
                    event.plotline_id = best


def compute_weight(
    plotlines: list[Plotline],
    episode: EpisodeBreakdown,
) -> dict[str, str]:
    """Compute plotline weight for an episode based on event count.

    Returns:
        Dict mapping plotline id to weight ("primary" / "background" / "glimpse").
    """
    counts: Counter[str] = Counter()
    for event in episode.events:
        if event.plotline_id:
            counts[event.plotline_id] += 1

    if not counts:
        return {}

    max_count = max(counts.values())

    weights = {}
    for plotline_id, count in counts.items():
        if count >= max_count * 0.5:
            weights[plotline_id] = "primary"
        elif count >= 2:
            weights[plotline_id] = "background"
        else:
            weights[plotline_id] = "glimpse"

    return weights


def compute_ranks(
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
    context: SeriesContext,
) -> None:
    """Assign computed_rank to each plotline based on event counts (in-place).

    Counts both primary events (plotline_id) and also_affects mentions equally.
    The LLM's choice of primary vs also_affects is often arbitrary — the event
    advances both plotlines. Equal weight avoids amplifying that arbitrariness.

    Rules:
    1. Runners get no rank (None).
    2. Procedural format: case_of_the_week → A.
    3. Hybrid format: case_of_the_week → B.
    4. Remaining plotlines sorted by descending event count:
       first → highest available rank, second → next, rest → C.
    """
    # Count events per plotline: primary + also_affects, equal weight
    event_counts: Counter[str] = Counter()
    for ep in episodes:
        for event in ep.events:
            if event.plotline_id:
                event_counts[event.plotline_id] += 1
            for aa in event.also_affects or []:
                event_counts[aa] += 1

    # Phase 1: fixed assignments
    fixed_ids: set[str] = set()
    is_a_taken = False

    for plotline in plotlines:
        if plotline.type == "runner":
            plotline.computed_rank = None
            fixed_ids.add(plotline.id)
        elif plotline.type == "case_of_the_week":
            if context.format == "procedural":
                plotline.computed_rank = "A"
                is_a_taken = True
            elif context.format == "hybrid":
                plotline.computed_rank = "B"
            fixed_ids.add(plotline.id)

    # Phase 2: remaining plotlines sorted by event count, filtered by span
    n_episodes = len(episodes)
    remaining = [p for p in plotlines if p.id not in fixed_ids]
    remaining.sort(key=lambda p: (-event_counts.get(p.id, 0), p.id))

    logger.info(
        "Rank assignment order: %s",
        [(p.id, event_counts.get(p.id, 0), len(p.span)) for p in remaining],
    )

    # Span requirements: A ≥ 75%, B ≥ 50%, C ≥ 25%
    for i, plotline in enumerate(remaining):
        span_frac = len(plotline.span) / n_episodes if n_episodes else 0
        if i == 0 and not is_a_taken and span_frac >= 0.75:
            plotline.computed_rank = "A"
            is_a_taken = True
        elif i <= 1 and span_frac >= 0.50:
            plotline.computed_rank = "B" if is_a_taken else "A"
            if plotline.computed_rank == "A":
                is_a_taken = True
        elif span_frac >= 0.25:
            plotline.computed_rank = "C"
        else:
            plotline.computed_rank = "C"  # low span but still serialized, not runner
        logger.info(
            "  %s → %s (events=%d, span=%d/%d=%.0f%%)",
            plotline.id, plotline.computed_rank, event_counts.get(plotline.id, 0),
            len(plotline.span), n_episodes, span_frac * 100,
        )


def validate_ranks(
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
    *,
    min_span_frac: float = 0.25,
    dominance_threshold: float = 0.50,
) -> list[dict]:
    """Check rank-span consistency and event dominance. In-place fixes.

    Rules:
    1. A-rank line with span < 25% of season → demote to B.
    2. Any line with > 50% of all events → flag for Pass 3 context.

    Returns list of flags (dicts with line id, flag type, details).
    """
    n_episodes = len(episodes)
    if n_episodes == 0:
        return []

    # Count events per line
    total_events = 0
    counts: Counter[str] = Counter()
    for ep in episodes:
        for event in ep.events:
            total_events += 1
            if event.plotline_id:
                counts[event.plotline_id] += 1

    # Collect all flags first, then apply mutations — avoids Rule 1 demotions
    # affecting Rule 2 dominance checks on the same pass
    flags = []
    demotions: list[Plotline] = []

    for plotline in plotlines:
        span_len = len(plotline.span) if isinstance(plotline.span, list) else 0
        span_frac = span_len / n_episodes

        # Rule 1: A computed_rank + short span → demote to B
        if plotline.computed_rank == "A" and span_frac < min_span_frac:
            demotions.append(plotline)
            flags.append({
                "plotline": plotline.id,
                "flag": "demoted",
                "reason": f"computed_rank A but span {span_len}/{n_episodes} ({span_frac:.0%})",
            })

        # Rule 2: dominates event share → flag
        if total_events > 0:
            share = counts.get(plotline.id, 0) / total_events
            if share > dominance_threshold:
                flags.append({
                    "plotline": plotline.id,
                    "flag": "dominant",
                    "reason": f"{share:.0%} of events ({counts[plotline.id]}/{total_events})",
                })

    # Apply demotions after all rules evaluated
    for plotline in demotions:
        plotline.computed_rank = "B"

    return flags
