"""Pipeline quality metrics: coverage and consistency.

Coverage: fraction of events assigned to a plotline.
Consistency: stability of plotline assignments across multiple runs (ARI).

Combined score = coverage × consistency.
"""

from __future__ import annotations

from collections import Counter

from tvplotlines.models import EpisodeBreakdown


def compute_coverage(episodes: list[EpisodeBreakdown]) -> float:
    """Fraction of events with a non-null plotline assignment.

    Returns:
        Float in [0.0, 1.0]. 1.0 = every event assigned.
    """
    total = 0
    assigned = 0
    for ep in episodes:
        for event in ep.events:
            total += 1
            if event.plotline is not None:
                assigned += 1

    if total == 0:
        return 1.0

    return assigned / total


def compute_consistency_ari(
    runs: list[list[EpisodeBreakdown]],
    cast_ids: list[str],
) -> float:
    """Measure consistency across multiple runs using ARI on (episode, character) grid.

    Each run assigns characters to plotlines per episode. ARI compares
    these clusterings without caring about plotline names.

    Args:
        runs: List of runs, each run is a list of EpisodeBreakdown.
        cast_ids: Fixed list of character ids to build the grid.

    Returns:
        Mean ARI across all pairs of runs. Range: [-0.5, 1.0], 1.0 = identical.
    """
    from sklearn.metrics import adjusted_rand_score

    if len(runs) < 2:
        return 1.0

    # Build label vectors: for each (episode, character) → plotline label
    vectors = []
    for run in runs:
        labels = []
        for ep in run:
            # Map character → most frequent plotline in this episode
            char_counts: dict[str, Counter[str]] = {}
            for event in ep.events:
                if not event.plotline:
                    continue
                for char in event.characters:
                    if char in cast_ids:
                        if char not in char_counts:
                            char_counts[char] = Counter()
                        char_counts[char][event.plotline] += 1
            char_plotlines: dict[str, str] = {
                char: counts.most_common(1)[0][0]
                for char, counts in char_counts.items()
            }

            for char_id in cast_ids:
                labels.append(char_plotlines.get(char_id, "__absent__"))
        vectors.append(labels)

    # Compute ARI for all pairs
    scores = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            score = adjusted_rand_score(vectors[i], vectors[j])
            scores.append(score)

    return sum(scores) / len(scores)


def compute_score(
    coverage: float,
    consistency: float,
) -> float:
    """Combined quality score = coverage × consistency."""
    return coverage * consistency
