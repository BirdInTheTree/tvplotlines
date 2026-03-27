"""Apply Pass 3 verdicts to plotlines and episode breakdowns.

Each verdict type maps to a mechanical transformation on the data.
No LLM calls — pure code.
"""

from __future__ import annotations

import logging

from tvplotlines.models import EpisodeBreakdown, Plotline, Verdict

logger = logging.getLogger(__name__)

def _validate_targets(
    action: str, d: dict, index: dict[str, Plotline], create_ids: set[str],
) -> bool:
    """Check that verdict references valid plotline IDs. Return False to skip."""
    valid_ids = set(index.keys()) | create_ids

    if action == "MERGE":
        target = d.get("target")
        if target not in valid_ids:
            logger.warning("Skipping MERGE: target %r not in plotlines", target)
            return False
        source = d.get("source")
        if source not in valid_ids:
            logger.warning("Skipping MERGE: source %r not in plotlines", source)
            return False
    if action == "REASSIGN":
        to = d.get("to")
        if to not in valid_ids:
            logger.warning("Skipping REASSIGN: target %r not in plotlines", to)
            return False
    if action == "DROP":
        target = d.get("target")
        if target not in valid_ids:
            logger.warning("Skipping DROP: target %r not in plotlines", target)
            return False
        for re_item in d.get("redistribute", []):
            if re_item.get("to") not in valid_ids:
                logger.warning(
                    "Skipping DROP %s: redistribute target %r not in plotlines",
                    target, re_item.get("to"),
                )
                return False

    return True


_VALID_FUNCTIONS = {
    "setup", "inciting_incident", "escalation", "turning_point",
    "crisis", "climax", "resolution",
}


def apply_verdicts(
    verdicts: list[Verdict],
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
    *,
    series_format: str = "serial",
) -> list[Plotline]:
    """Apply verdicts to plotlines and episodes (in-place for episodes).

    Args:
        verdicts: From Pass 3.
        plotlines: Current plotlines (will be copied, not mutated).
        episodes: Episode breakdowns (events mutated in-place).
        series_format: Series format for rank validation.

    Returns:
        Updated list of plotlines.
    """
    plotlines = list(plotlines)
    plotline_index = {p.id: p for p in plotlines}

    # Collect CREATE ids so REASSIGN can reference not-yet-created plotlines
    create_ids = {
        v.data["plotline"]["id"]
        for v in verdicts
        if v.action == "CREATE" and "plotline" in v.data
    }

    for verdict in verdicts:
        action = verdict.action
        d = verdict.data

        if not _validate_targets(action, d, plotline_index, create_ids):
            continue

        if action == "MERGE":
            _apply_merge(d, plotlines, plotline_index, episodes)
        elif action == "REASSIGN":
            _apply_reassign(d, episodes)
        elif action == "CREATE":
            _apply_create(d, plotlines, plotline_index, episodes)
        elif action == "DROP":
            _apply_drop(d, plotlines, plotline_index, episodes)
        elif action == "REFUNCTION":
            _apply_refunction(d, episodes)
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

    for ep in episodes:
        for event in ep.events:
            if event.plotline_id == source_id:
                event.plotline_id = target_id
            if event.also_affects:
                event.also_affects = [
                    target_id if sid == source_id else sid
                    for sid in event.also_affects
                ]

    source = index.pop(source_id, None)
    if source and source in plotlines:
        plotlines.remove(source)

    logger.info("MERGE %s → %s: %s", source_id, target_id, d.get("reason", ""))


def _apply_reassign(d: dict, episodes: list[EpisodeBreakdown]) -> None:
    """REASSIGN: change one event's plotline."""
    event_text = d["event"]
    episode_id = d["episode"]
    new_line = d["to"]

    for ep in episodes:
        if ep.episode == episode_id:
            for event in ep.events:
                if event.event == event_text:
                    event.plotline_id = new_line
                    logger.info("REASSIGN '%s' → %s", event_text[:50], new_line)
                    return

    logger.warning("REASSIGN: event not found in %s: '%s'", episode_id, event_text[:50])


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
        hero=pl_data["hero"],
        goal=pl_data["goal"],
        obstacle=pl_data["obstacle"],
        stakes=pl_data["stakes"],
        type=pl_data["type"],
        nature=pl_data["nature"],
        confidence="inferred",
        # Pass 3 assigns rank to created plotlines via reviewed_rank
        reviewed_rank=pl_data.get("rank"),
    )

    plotlines.append(new_plotline)
    index[new_plotline.id] = new_plotline

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
    """DROP: redistribute events, then remove plotline only if all events moved."""
    target_id = d["target"]

    for re in d.get("redistribute", []):
        _apply_reassign(
            {"event": re["event"], "episode": re["episode"], "to": re["to"]},
            episodes,
        )

    # Check if any events still belong to this plotline
    remaining = sum(
        1 for ep in episodes for event in ep.events
        if event.plotline_id == target_id
    )
    if remaining > 0:
        logger.warning(
            "DROP %s aborted: %d events not redistributed, keeping plotline",
            target_id, remaining,
        )
        return

    dropped = index.pop(target_id, None)
    if dropped and dropped in plotlines:
        plotlines.remove(dropped)

    logger.info("DROP %s: %s", target_id, d.get("reason", ""))


def _apply_refunction(d: dict, episodes: list[EpisodeBreakdown]) -> None:
    """REFUNCTION: change an event's function."""
    event_text = d["event"]
    episode_id = d["episode"]
    new_function = d["new_function"]

    if new_function not in _VALID_FUNCTIONS:
        logger.warning("REFUNCTION: invalid function %r", new_function)
        return

    for ep in episodes:
        if ep.episode == episode_id:
            for event in ep.events:
                if event.event == event_text:
                    old = event.function
                    event.function = new_function
                    logger.info("REFUNCTION '%s': %s → %s", event_text[:50], old, new_function)
                    return

    logger.warning("REFUNCTION: event not found in %s: '%s'", episode_id, event_text[:50])
