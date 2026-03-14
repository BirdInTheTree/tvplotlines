"""Post-processing: compute span, weight, aggregate patches.

These fields are derived from Pass 2 results, not from LLM.
"""

from __future__ import annotations

from collections import Counter

from plotter.models import EpisodeBreakdown, Patch, Plotline


def compute_span(
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
) -> None:
    """Fill Plotline.span from episode breakdowns (in-place).

    A storyline is present in an episode if it has at least one event there.
    """
    for plotline in plotlines:
        present_episodes = []
        for ep in episodes:
            has_event = any(
                e.storyline == plotline.id for e in ep.events
            )
            if has_event:
                present_episodes.append(ep.episode)
        plotline.span = present_episodes


def assign_orphan_events(
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
) -> None:
    """Assign null-storyline events to the most common storyline for their characters.

    For each unassigned event, find the storyline most frequently associated
    with its characters across the season. In-place modification.
    """
    # Build character → storyline frequency map from assigned events
    char_storyline_counts: dict[str, Counter[str]] = {}
    for ep in episodes:
        for event in ep.events:
            if event.storyline is None:
                continue
            for char in event.characters:
                if char not in char_storyline_counts:
                    char_storyline_counts[char] = Counter()
                char_storyline_counts[char][event.storyline] += 1

    plotline_ids = {p.id for p in plotlines}

    # Assign orphan events
    for ep in episodes:
        for event in ep.events:
            if event.storyline is not None:
                continue
            if not event.characters:
                continue

            # Aggregate storyline votes from all characters in this event
            votes: Counter[str] = Counter()
            for char in event.characters:
                if char in char_storyline_counts:
                    votes.update(char_storyline_counts[char])

            if not votes:
                # Fallback: use the most common storyline in this episode
                ep_counts: Counter[str] = Counter()
                for other in ep.events:
                    if other.storyline:
                        ep_counts[other.storyline] += 1
                if ep_counts:
                    votes = ep_counts

            if votes:
                best = votes.most_common(1)[0][0]
                if best in plotline_ids:
                    event.storyline = best


def compute_weight(
    plotlines: list[Plotline],
    episode: EpisodeBreakdown,
) -> dict[str, str]:
    """Compute storyline weight for an episode based on event count.

    Returns:
        Dict mapping storyline id to weight ("primary" / "background" / "glimpse").
    """
    counts: Counter[str] = Counter()
    for event in episode.events:
        if event.storyline:
            counts[event.storyline] += 1

    if not counts:
        return {}

    max_count = max(counts.values())

    weights = {}
    for storyline_id, count in counts.items():
        if count >= max_count * 0.5:
            weights[storyline_id] = "primary"
        elif count >= 2:
            weights[storyline_id] = "background"
        else:
            weights[storyline_id] = "glimpse"

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
            if event.storyline:
                counts[event.storyline] += 1

    flags = []

    for plotline in plotlines:
        span_len = len(plotline.span) if isinstance(plotline.span, list) else 0
        span_frac = span_len / n_episodes

        # Rule 1: A-rank + short span → demote
        if plotline.rank == "A" and span_frac < min_span_frac:
            plotline.rank = "B"
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

    return flags


def aggregate_patches(episodes: list[EpisodeBreakdown]) -> list[Patch]:
    """Collect all patches from all episodes into one list."""
    all_patches = []
    for ep in episodes:
        all_patches.extend(ep.patches)
    return all_patches
