"""Post-processing: compute span, weight, aggregate patches.

These fields are derived from Pass 2 results, not from LLM.
"""

from __future__ import annotations

from collections import Counter

from tvplotlines.models import EpisodeBreakdown, Patch, Plotline


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
                e.plotline == plotline.id for e in ep.events
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
            if event.plotline is None:
                continue
            for char in event.characters:
                if char not in char_plotline_counts:
                    char_plotline_counts[char] = Counter()
                char_plotline_counts[char][event.plotline] += 1

    plotline_ids = {p.id for p in plotlines}

    # Assign orphan events
    for ep in episodes:
        for event in ep.events:
            if event.plotline is not None:
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
                    if other.plotline:
                        ep_counts[other.plotline] += 1
                if ep_counts:
                    votes = ep_counts

            if votes:
                best = votes.most_common(1)[0][0]
                if best in plotline_ids:
                    event.plotline = best


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
        if event.plotline:
            counts[event.plotline] += 1

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
            if event.plotline:
                counts[event.plotline] += 1

    # Collect all flags first, then apply mutations — avoids Rule 1 demotions
    # affecting Rule 2 dominance checks on the same pass
    flags = []
    demotions: list[Plotline] = []

    for plotline in plotlines:
        span_len = len(plotline.span) if isinstance(plotline.span, list) else 0
        span_frac = span_len / n_episodes

        # Rule 1: A-rank + short span → mark for demotion
        if plotline.rank == "A" and span_frac < min_span_frac:
            demotions.append(plotline)
            flags.append({
                "plotline": plotline.id,
                "flag": "demoted",
                "reason": f"rank A but span {span_len}/{n_episodes} ({span_frac:.0%})",
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
        plotline.rank = "B"

    return flags


def aggregate_patches(episodes: list[EpisodeBreakdown]) -> list[Patch]:
    """Collect all patches from all episodes into one list."""
    all_patches = []
    for ep in episodes:
        all_patches.extend(ep.patches)
    return all_patches
