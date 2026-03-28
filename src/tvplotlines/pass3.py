"""Pass 3: Structural review of full pipeline results.

Input: complete TVPlotlinesResult (plotlines + events + span + weight).
Output: list of Verdict objects to apply.
"""

from __future__ import annotations

import json

from tvplotlines.llm import LLMConfig, call_llm
from tvplotlines.models import (
    CastMember,
    EpisodeBreakdown,
    Plotline,
    SeriesContext,
    Verdict,
)
from tvplotlines.postprocess import compute_weight
from tvplotlines.prompts_en import load_prompt

_VALID_ACTIONS = {"MERGE", "REASSIGN", "CREATE", "DROP", "REFUNCTION"}
_VALID_FUNCTIONS = {
    "setup", "inciting_incident", "escalation", "turning_point",
    "crisis", "climax", "resolution",
}


def review_plotlines(
    show: str,
    season: int,
    context: SeriesContext,
    cast: list[CastMember],
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
    *,
    diagnostics: list[dict] | None = None,
    config: LLMConfig | None = None,
) -> list[Verdict]:
    """Run structural review on pipeline results.

    Args:
        show: Series title.
        season: Season number.
        context: From Pass 0 or user-provided.
        cast: Cast from Pass 1.
        plotlines: Plotlines from Pass 1 (with span computed).
        episodes: Episode breakdowns from Pass 2.
        diagnostics: Automated flags from postprocess (arc_completeness, monotonicity, ranks).
        config: LLM settings.

    Returns:
        Dict with "verdicts" (list of Verdict) and "arc_functions" (list of dicts).
    """
    if config is None:
        config = LLMConfig()

    # Compute weight per episode for each plotline
    weight_data = {}
    for ep in episodes:
        weights = compute_weight(plotlines, ep)
        weight_data[ep.episode] = weights

    payload = {
        "show": show,
        "season": season,
        "format": context.format,
        "is_ensemble": context.is_ensemble,
        "story_engine": context.story_engine,
        "cast": [
            {"id": c.id, "name": c.name}
            for c in cast
        ],
        "plotlines": [
            {
                "id": p.id,
                "name": p.name,
                "hero": p.hero,
                "goal": p.goal,
                "obstacle": p.obstacle,
                "stakes": p.stakes,
                "type": p.type,
                "rank": p.rank,
                "nature": p.nature,
                "confidence": p.confidence,
                "span": p.span,
                "weight_per_episode": {
                    ep_id: w.get(p.id, "absent")
                    for ep_id, w in weight_data.items()
                },
            }
            for p in plotlines
        ],
        "episodes": [
            {
                "episode": ep.episode,
                "theme": ep.theme,
                "events": [
                    {
                        "event": e.event,
                        "plotline_id": e.plotline_id,
                        "function": e.function,
                        "characters": e.characters,
                        "also_affects": e.also_affects,
                    }
                    for e in ep.events
                ],
            }
            for ep in episodes
        ],
    }

    if diagnostics:
        payload["diagnostics"] = diagnostics

    user_message = json.dumps(payload, ensure_ascii=False)

    system_prompt = load_prompt("pass3", lang=config.lang)

    def _full_validate(data: dict) -> None:
        _parse_verdicts(data, plotlines, episodes)

    data = call_llm(system_prompt, user_message, config, validator=_full_validate)
    verdicts = _parse_verdicts(data, plotlines, episodes)
    arc_functions = _parse_arc_functions(data, episodes)
    return {"verdicts": verdicts, "arc_functions": arc_functions}


def _parse_verdicts(
    data: dict,
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
) -> list[Verdict]:
    """Parse and validate verdicts from LLM response."""
    plotline_ids = {p.id for p in plotlines}

    # Collect new ids from CREATE verdicts for cross-referencing
    created_ids: set[str] = set()
    for v in data.get("verdicts", []):
        if v.get("action") == "CREATE" and "plotline" in v:
            created_ids.add(v["plotline"]["id"])

    all_ids = plotline_ids | created_ids

    # Collect all event texts for validation
    all_events: set[str] = set()
    for ep in episodes:
        for e in ep.events:
            all_events.add(e.event)

    verdicts = []
    for v in data.get("verdicts", []):
        try:
            action = v["action"]
        except KeyError as e:
            raise ValueError(f"Verdict missing required field: {e}") from e
        if action not in _VALID_ACTIONS:
            raise ValueError(f"Invalid verdict action: {action!r}")

        if action == "MERGE":
            _require_keys(v, ["source", "target", "reason"])
            if v["source"] not in plotline_ids:
                raise ValueError(f"MERGE source {v['source']!r} not in plotlines")
            if v["target"] not in plotline_ids:
                raise ValueError(f"MERGE target {v['target']!r} not in plotlines")

        elif action == "REASSIGN":
            _require_keys(v, ["event", "episode", "to", "reason"])
            if v["event"] not in all_events:
                raise ValueError(f"REASSIGN event not found: {v['event']!r}")
            if v["to"] not in all_ids:
                raise ValueError(f"REASSIGN target {v['to']!r} not in plotlines")

        elif action == "CREATE":
            _require_keys(v, ["plotline", "reassign_events", "reason"])
            pl = v["plotline"]
            _require_keys(pl, ["id", "name", "hero", "goal", "obstacle", "stakes", "type", "rank", "nature"])
            for re in v["reassign_events"]:
                if re["event"] not in all_events:
                    raise ValueError(f"CREATE reassign event not found: {re['event']!r}")

        elif action == "DROP":
            _require_keys(v, ["target", "redistribute", "reason"])
            if v["target"] not in plotline_ids:
                raise ValueError(f"DROP target {v['target']!r} not in plotlines")
            for re in v["redistribute"]:
                if re["event"] not in all_events:
                    raise ValueError(f"DROP redistribute event not found: {re['event']!r}")
                if re["to"] not in all_ids:
                    raise ValueError(f"DROP redistribute target {re['to']!r} not in plotlines")

        elif action == "REFUNCTION":
            _require_keys(v, ["event", "episode", "old_function", "new_function", "reason"])
            if v["event"] not in all_events:
                raise ValueError(f"REFUNCTION event not found: {v['event']!r}")
            if v["new_function"] not in _VALID_FUNCTIONS:
                raise ValueError(f"REFUNCTION invalid function: {v['new_function']!r}")

        verdicts.append(Verdict(action=action, data=v))

    return verdicts


def _parse_arc_functions(
    data: dict,
    episodes: list[EpisodeBreakdown],
) -> list[dict]:
    """Parse and validate arc_functions from LLM response.

    Returns:
        List of dicts with episode, event, plot_fn.
    """
    raw = data.get("arc_functions", [])

    # Build lookup of valid event texts per episode
    events_by_ep: dict[str, set[str]] = {}
    for ep in episodes:
        events_by_ep[ep.episode] = {e.event for e in ep.events}

    result = []
    for af in raw:
        ep_id = af.get("episode")
        event_text = af.get("event")
        plot_fn = af.get("plot_fn")

        if plot_fn not in _VALID_FUNCTIONS:
            raise ValueError(f"Invalid arc function: {plot_fn!r}")
        if ep_id not in events_by_ep:
            raise ValueError(f"Arc function references unknown episode: {ep_id!r}")
        if event_text not in events_by_ep.get(ep_id, set()):
            raise ValueError(f"Arc function event not found in {ep_id}: {event_text!r}")

        result.append({"episode": ep_id, "event": event_text, "plot_fn": plot_fn})
    return result


def apply_arc_functions(
    arc_functions: list[dict],
    episodes: list[EpisodeBreakdown],
) -> None:
    """Apply arc functions to events in-place.

    Args:
        arc_functions: List of dicts with episode, event, plot_fn.
        episodes: Episode breakdowns to mutate.
    """
    for af in arc_functions:
        ep_id = af["episode"]
        event_text = af["event"]
        plot_fn = af["plot_fn"]
        for ep in episodes:
            if ep.episode == ep_id:
                for event in ep.events:
                    if event.event == event_text:
                        event.plot_fn = plot_fn
                        break


def _require_keys(d: dict, keys: list[str]) -> None:
    """Raise ValueError if any required key is missing."""
    for key in keys:
        if key not in d:
            raise ValueError(f"Missing required key {key!r} in verdict: {d}")
