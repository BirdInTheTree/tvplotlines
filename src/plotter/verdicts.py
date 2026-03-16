"""Apply Pass 3 verdicts to plotlines and episode breakdowns.

Each verdict type maps to a mechanical transformation on the data.
No LLM calls — pure code.
"""

from __future__ import annotations

import logging

from plotter.models import EpisodeBreakdown, Plotline, Verdict

logger = logging.getLogger(__name__)


def apply_verdicts(
    verdicts: list[Verdict],
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
    *,
    franchise_type: str = "serial",
) -> list[Plotline]:
    """Apply verdicts to plotlines and episodes (in-place for episodes).

    Args:
        verdicts: From Pass 3.
        plotlines: Current plotlines (will be copied, not mutated).
        episodes: Episode breakdowns (events mutated in-place).

    Returns:
        Updated list of plotlines.
    """
    # Work on a mutable copy of plotlines
    plotlines = list(plotlines)
    plotline_index = {p.id: p for p in plotlines}

    for verdict in verdicts:
        action = verdict.action
        d = verdict.data

        if action == "MERGE":
            _apply_merge(d, plotlines, plotline_index, episodes)
        elif action == "REASSIGN":
            _apply_reassign(d, episodes)
        elif action == "PROMOTE":
            _apply_rank_change(d, plotline_index, plotlines, franchise_type)
        elif action == "DEMOTE":
            _apply_rank_change(d, plotline_index, plotlines, franchise_type)
        elif action == "CREATE":
            _apply_create(d, plotlines, plotline_index, episodes)
        elif action == "DROP":
            _apply_drop(d, plotlines, plotline_index, episodes)
        else:
            logger.warning("Unknown verdict action: %s", action)

    return plotlines


def _apply_merge(
    d: dict,
    plotlines: list[Plotline],
    index: dict[str, Plotline],
    episodes: list[EpisodeBreakdown],
) -> None:
    """MERGE: move all events from source to target, remove source."""
    source_id = d["source"]
    target_id = d["target"]

    # Reassign events
    for ep in episodes:
        for event in ep.events:
            if event.storyline == source_id:
                event.storyline = target_id
            if event.also_affects:
                event.also_affects = [
                    target_id if sid == source_id else sid
                    for sid in event.also_affects
                ]

    # Remove source plotline
    source = index.pop(source_id, None)
    if source and source in plotlines:
        plotlines.remove(source)

    logger.info("MERGE %s → %s: %s", source_id, target_id, d.get("reason", ""))


def _apply_reassign(d: dict, episodes: list[EpisodeBreakdown]) -> None:
    """REASSIGN: change one event's storyline."""
    event_text = d["event"]
    episode_id = d["episode"]
    new_line = d["to"]

    for ep in episodes:
        if ep.episode == episode_id:
            for event in ep.events:
                if event.event == event_text:
                    event.storyline = new_line
                    logger.info("REASSIGN '%s' → %s", event_text[:50], new_line)
                    return

    logger.warning("REASSIGN: event not found in %s: '%s'", episode_id, event_text[:50])


def _apply_rank_change(
    d: dict,
    index: dict[str, Plotline],
    all_plotlines: list[Plotline],
    franchise_type: str,
) -> None:
    """PROMOTE or DEMOTE: change plotline rank."""
    target_id = d["target"]
    new_rank = d["new_rank"]

    # Block PROMOTE to A if there's already an A-rank storyline (non-ensemble)
    if new_rank == "A" and franchise_type != "ensemble":
        has_a = any(p.rank == "A" for p in all_plotlines)
        if has_a:
            logger.warning(
                "Blocked PROMOTE %s to A: franchise_type=%r already has an A-rank storyline",
                target_id, franchise_type,
            )
            return

    plotline = index.get(target_id)
    if plotline:
        old_rank = plotline.rank
        plotline.rank = new_rank
        logger.info("RANK %s: %s → %s", target_id, old_rank, new_rank)


def _apply_create(
    d: dict,
    plotlines: list[Plotline],
    index: dict[str, Plotline],
    episodes: list[EpisodeBreakdown],
) -> None:
    """CREATE: add new plotline and reassign specified events to it."""
    pl_data = d["plotline"]
    new_plotline = Plotline(
        id=pl_data["id"],
        name=pl_data["name"],
        driver=pl_data["driver"],
        goal=pl_data["goal"],
        obstacle=pl_data["obstacle"],
        stakes=pl_data["stakes"],
        type=pl_data["type"],
        rank=pl_data["rank"],
        nature=pl_data["nature"],
        confidence="inferred",
    )

    plotlines.append(new_plotline)
    index[new_plotline.id] = new_plotline

    # Reassign events
    for re in d.get("reassign_events", []):
        _apply_reassign(
            {"event": re["event"], "episode": re["episode"], "to": new_plotline.id},
            episodes,
        )

    logger.info("CREATE %s: %s", new_plotline.id, d.get("reason", ""))


def _apply_drop(
    d: dict,
    plotlines: list[Plotline],
    index: dict[str, Plotline],
    episodes: list[EpisodeBreakdown],
) -> None:
    """DROP: redistribute events and remove plotline."""
    target_id = d["target"]

    # Redistribute specified events
    for re in d.get("redistribute", []):
        _apply_reassign(
            {"event": re["event"], "episode": re["episode"], "to": re["to"]},
            episodes,
        )

    # Any remaining events of this plotline become unassigned
    for ep in episodes:
        for event in ep.events:
            if event.storyline == target_id:
                logger.warning(
                    "DROP %s: event '%s' not redistributed, setting to null",
                    target_id, event.event[:50],
                )
                event.storyline = None

    # Remove plotline
    dropped = index.pop(target_id, None)
    if dropped and dropped in plotlines:
        plotlines.remove(dropped)

    logger.info("DROP %s: %s", target_id, d.get("reason", ""))
