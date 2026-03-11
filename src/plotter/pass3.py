"""Pass 3: Narratologist review of full pipeline results.

Input: complete PlotterResult (lines + events + span + weight).
Output: list of Verdict objects to apply.
"""

from __future__ import annotations

import json

from plotter.llm import LLMConfig, call_llm
from plotter.models import (
    CastMember,
    EpisodeBreakdown,
    Plotline,
    SeriesContext,
    Verdict,
)
from plotter.postprocess import compute_weight
from plotter.prompts import load_prompt

_VALID_ACTIONS = {"MERGE", "REASSIGN", "PROMOTE", "DEMOTE", "CREATE", "DROP"}
_VALID_RANKS = {"A", "B", "C", "runner"}


def review_storylines(
    show: str,
    season: int,
    context: SeriesContext,
    cast: list[CastMember],
    plotlines: list[Plotline],
    episodes: list[EpisodeBreakdown],
    *,
    config: LLMConfig | None = None,
) -> list[Verdict]:
    """Run narratologist review on pipeline results.

    Args:
        show: Series title.
        season: Season number.
        context: From Pass 0 or user-provided.
        cast: Cast from Pass 1.
        plotlines: Storylines from Pass 1 (with span computed).
        episodes: Episode breakdowns from Pass 2.
        config: LLM settings.

    Returns:
        List of verdicts to apply.
    """
    if config is None:
        config = LLMConfig()

    # Compute weight per episode for each plotline
    weight_data = {}
    for ep in episodes:
        weights = compute_weight(plotlines, ep)
        weight_data[ep.episode] = weights

    user_message = json.dumps(
        {
            "show": show,
            "season": season,
            "franchise_type": context.franchise_type,
            "story_engine": context.story_engine,
            "format": context.format,
            "cast": [
                {"id": c.id, "name": c.name}
                for c in cast
            ],
            "plotlines": [
                {
                    "id": p.id,
                    "name": p.name,
                    "driver": p.driver,
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
                            "storyline": e.storyline,
                            "function": e.function,
                            "characters": e.characters,
                            "also_affects": e.also_affects,
                        }
                        for e in ep.events
                    ],
                    "patches": [
                        {
                            "action": p.action,
                            "target": p.target,
                            "reason": p.reason,
                        }
                        for p in ep.patches
                    ],
                }
                for ep in episodes
            ],
        },
        ensure_ascii=False,
    )

    system_prompt = load_prompt("pass3")

    def _full_validate(data: dict) -> None:
        _parse_verdicts(data, plotlines, episodes)

    data = call_llm(system_prompt, user_message, config, validator=_full_validate)
    return _parse_verdicts(data, plotlines, episodes)


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
        action = v["action"]
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

        elif action in ("PROMOTE", "DEMOTE"):
            _require_keys(v, ["target", "new_rank", "reason"])
            if v["target"] not in plotline_ids:
                raise ValueError(f"{action} target {v['target']!r} not in plotlines")
            if v["new_rank"] not in _VALID_RANKS:
                raise ValueError(f"{action} invalid rank: {v['new_rank']!r}")

        elif action == "CREATE":
            _require_keys(v, ["plotline", "reassign_events", "reason"])
            pl = v["plotline"]
            _require_keys(pl, ["id", "name", "driver", "goal", "obstacle", "stakes", "type", "rank", "nature"])
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

        verdicts.append(Verdict(action=action, data=v))

    return verdicts


def _require_keys(d: dict, keys: list[str]) -> None:
    """Raise ValueError if any required key is missing."""
    for key in keys:
        if key not in d:
            raise ValueError(f"Missing required key {key!r} in verdict: {d}")
