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


def aggregate_patches(episodes: list[EpisodeBreakdown]) -> list[Patch]:
    """Collect all patches from all episodes into one list."""
    all_patches = []
    for ep in episodes:
        all_patches.extend(ep.patches)
    return all_patches
