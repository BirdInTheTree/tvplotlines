"""Pass 4: Assign arc functions (plot_fn) to every event.

Each event already has a `function` (its role within an episode).
Pass 4 assigns `plot_fn` — the event's role in the plotline's season-long arc.
"""

from __future__ import annotations

import json
import logging

from tvplotlines.llm import LLMConfig, call_llm
from tvplotlines.models import (
    CastMember,
    EpisodeBreakdown,
    Plotline,
    SeriesContext,
)
from tvplotlines.prompts_en import load_prompt

logger = logging.getLogger(__name__)

_VALID_FUNCTIONS = {
    "setup", "inciting_incident", "escalation", "turning_point",
    "crisis", "climax", "resolution",
}


def assign_arc_functions(
    show: str,
    season: int,
    context: SeriesContext,
    cast: list[CastMember],
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
    *,
    config: LLMConfig | None = None,
) -> int:
    """Assign arc functions (plot_fn) to all events. Returns count of assigned."""
    if config is None:
        config = LLMConfig()

    user_message = _build_user_message(show, season, plotlines, episodes)
    system_prompt = load_prompt("pass4", lang=config.lang)

    plotline_ids = {p.id for p in plotlines}
    # Map name → id for resilience (LLM may return name instead of id)
    name_to_id = {p.name: p.id for p in plotlines}
    name_to_id.update({p.id: p.id for p in plotlines})  # id maps to itself

    def _validate(data: dict) -> None:
        # Normalize plotline references before validation
        for af in data.get("arc_functions", []):
            pid = af.get("plotline", "")
            if pid not in plotline_ids and pid in name_to_id:
                af["plotline"] = name_to_id[pid]
        _parse_and_validate(data, plotline_ids, episodes)

    data = call_llm(system_prompt, user_message, config, validator=_validate)
    # Normalize again for apply (validator may have fixed during retry)
    for af in data.get("arc_functions", []):
        pid = af.get("plotline", "")
        if pid not in plotline_ids and pid in name_to_id:
            af["plotline"] = name_to_id[pid]
    return _apply_arc_functions(data, plotline_ids, episodes)


def _build_user_message(
    show: str,
    season: int,
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
) -> str:
    """Build user message grouping events by plotline in episode order."""
    # Index events by plotline_id
    events_by_plotline: dict[str, list[tuple[str, str, str]]] = {}
    for ep in episodes:
        for event in ep.events:
            pid = event.plotline_id
            if pid is None:
                continue
            events_by_plotline.setdefault(pid, []).append(
                (ep.episode, event.function, event.event)
            )

    lines = [f"Show: {show}, Season {season}", ""]
    for plotline in plotlines:
        lines.append(
            f"Plotline ID: {plotline.id} — {plotline.name} "
            f"(hero={plotline.hero}, goal={plotline.goal})"
        )
        lines.append("Events:")
        for ep_id, function, event_text in events_by_plotline.get(plotline.id, []):
            lines.append(f"  [{ep_id}] ({function}) {event_text}")
        lines.append("")

    return "\n".join(lines)


def _parse_and_validate(
    data: dict,
    plotline_ids: set[str],
    episodes: list[EpisodeBreakdown],
) -> None:
    """Validate arc_functions from LLM response. Raises ValueError on issues."""
    raw = data.get("arc_functions", [])
    if not raw:
        raise ValueError("arc_functions array is empty")

    # Build lookup of valid event texts per episode
    events_by_ep: dict[str, set[str]] = {}
    for ep in episodes:
        events_by_ep[ep.episode] = {e.event for e in ep.events}

    for af in raw:
        plot_fn = af.get("plot_fn")
        if plot_fn not in _VALID_FUNCTIONS:
            raise ValueError(f"Invalid plot_fn: {plot_fn!r}")

        plotline = af.get("plotline")
        if plotline not in plotline_ids:
            raise ValueError(f"Unknown plotline: {plotline!r}")

        ep_id = af.get("episode")
        if ep_id not in events_by_ep:
            raise ValueError(f"Unknown episode: {ep_id!r}")

        event_text = af.get("event")
        if event_text not in events_by_ep.get(ep_id, set()):
            raise ValueError(
                f"Event not found in {ep_id}: {str(event_text)[:60]!r}"
            )


def _apply_arc_functions(
    data: dict,
    plotline_ids: set[str],
    episodes: list[EpisodeBreakdown],
) -> int:
    """Apply arc functions to events in-place. Returns count of assigned.

    Skips invalid entries with a warning instead of crashing.
    """
    raw = data.get("arc_functions", [])

    # Build lookup of valid event texts per episode
    events_by_ep: dict[str, set[str]] = {}
    for ep in episodes:
        events_by_ep[ep.episode] = {e.event for e in ep.events}

    count = 0
    for af in raw:
        plot_fn = af.get("plot_fn")
        plotline = af.get("plotline")
        ep_id = af.get("episode")
        event_text = af.get("event")

        if plot_fn not in _VALID_FUNCTIONS:
            logger.warning("Skipping arc function with invalid plot_fn: %s", plot_fn)
            continue
        if plotline not in plotline_ids:
            logger.warning("Skipping arc function for unknown plotline: %s", plotline)
            continue
        if ep_id not in events_by_ep:
            logger.warning("Skipping arc function for unknown episode: %s", ep_id)
            continue
        if event_text not in events_by_ep.get(ep_id, set()):
            logger.warning(
                "Skipping arc function — event not found in %s: %s",
                ep_id, str(event_text)[:60],
            )
            continue

        for ep in episodes:
            if ep.episode == ep_id:
                for event in ep.events:
                    if event.event == event_text:
                        event.plot_fn = plot_fn
                        count += 1
                        break
                break

    return count
