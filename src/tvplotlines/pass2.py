"""Pass 2: Assign events to plotlines for a single episode.

Input: one episode synopsis + cast + plotlines from Pass 1.
Output: EpisodeBreakdown.
"""

from __future__ import annotations

import json

from tvplotlines.llm import LLMConfig, call_llm, call_llm_batch, call_llm_parallel
from tvplotlines.models import (
    CastMember,
    EpisodeBreakdown,
    Event,
    Interaction,
    Patch,
    Plotline,
    SeriesContext,
)
from tvplotlines.prompts import load_prompt

_VALID_FUNCTIONS = {
    "setup", "inciting_incident", "escalation", "turning_point",
    "crisis", "climax", "resolution",
}
_VALID_INTERACTION_TYPES = {
    "thematic_rhyme", "dramatic_irony", "convergence",
}
_VALID_PATCH_ACTIONS = {"ADD_LINE", "CHECK_LINE", "SPLIT_LINE", "RERANK"}


def assign_events(
    show: str,
    season: int,
    episode_id: str,
    synopsis: str,
    context: SeriesContext,
    cast: list[CastMember],
    plotlines: list[Plotline],
    *,
    config: LLMConfig | None = None,
) -> EpisodeBreakdown:
    """Assign events from one episode to plotlines.

    Args:
        show: Series title.
        season: Season number.
        episode_id: Episode identifier (e.g. "S01E01").
        synopsis: Synopsis text for this episode.
        context: Series context from Pass 0.
        cast: Cast from Pass 1.
        plotlines: Plotlines from Pass 1.
        config: LLM settings.

    Returns:
        EpisodeBreakdown for this episode.
    """
    if config is None:
        config = LLMConfig()

    user_message = json.dumps(
        {
            "show": show,
            "season": season,
            "episode": episode_id,
            "format": context.format,
            "story_engine": context.story_engine,
            "cast": [
                {"id": c.id, "name": c.name, "aliases": c.aliases}
                for c in cast
            ],
            "plotlines": [
                {
                    "id": p.id,
                    "name": p.name,
                    "hero": p.hero,
                    "goal": p.goal,
                    "type": p.type,
                    "rank": p.rank,
                }
                for p in plotlines
            ],
            "synopsis": synopsis,
        },
        ensure_ascii=False,
    )

    system_prompt = load_prompt("pass2", lang=config.lang)

    def _full_validate(data: dict) -> None:
        bd = _parse_breakdown(data, episode_id)
        _validate(bd, plotlines, cast)

    data = call_llm(
        system_prompt, user_message, config,
        cache_system=True, validator=_full_validate,
    )

    return _parse_breakdown(data, episode_id)


def _prepare_bulk(
    show: str,
    season: int,
    episodes: list[tuple[str, str]],
    context: SeriesContext,
    cast: list[CastMember],
    plotlines: list[Plotline],
    config: LLMConfig,
) -> tuple[str, list[str], list[str], list]:
    """Prepare shared data for parallel/batch Pass 2 calls."""
    system_prompt = load_prompt("pass2", lang=config.lang)

    user_messages = []
    episode_ids = []
    for episode_id, synopsis in episodes:
        episode_ids.append(episode_id)
        user_messages.append(json.dumps(
            {
                "show": show,
                "season": season,
                "episode": episode_id,
                "format": context.format,
                "story_engine": context.story_engine,
                "cast": [
                    {"id": c.id, "name": c.name, "aliases": c.aliases}
                    for c in cast
                ],
                "plotlines": [
                    {
                        "id": p.id, "name": p.name, "hero": p.hero,
                        "goal": p.goal, "type": p.type, "rank": p.rank,
                    }
                    for p in plotlines
                ],
                "synopsis": synopsis,
            },
            ensure_ascii=False,
        ))

    def _make_validator(ep_id: str):
        def _validate_ep(data: dict) -> None:
            bd = _parse_breakdown(data, ep_id)
            _validate(bd, plotlines, cast)
        return _validate_ep

    validators = [_make_validator(ep_id) for ep_id in episode_ids]

    return system_prompt, user_messages, episode_ids, validators


def assign_events_parallel(
    show: str,
    season: int,
    episodes: list[tuple[str, str]],
    context: SeriesContext,
    cast: list[CastMember],
    plotlines: list[Plotline],
    *,
    config: LLMConfig | None = None,
) -> list[EpisodeBreakdown]:
    """Assign events for all episodes in parallel (fast, full price)."""
    if config is None:
        config = LLMConfig()

    system_prompt, user_messages, episode_ids, validators = _prepare_bulk(
        show, season, episodes, context, cast, plotlines, config,
    )

    results = call_llm_parallel(
        system_prompt, user_messages, config,
        cache_system=True, validators=validators,
    )

    return [
        _parse_breakdown(data, ep_id)
        for data, ep_id in zip(results, episode_ids)
    ]


def assign_events_batch(
    show: str,
    season: int,
    episodes: list[tuple[str, str]],
    context: SeriesContext,
    cast: list[CastMember],
    plotlines: list[Plotline],
    *,
    config: LLMConfig | None = None,
    batch_id: str | None = None,
    on_batch_submitted=None,
) -> list[EpisodeBreakdown]:
    """Assign events for all episodes in a single batch (50% cheaper, slower)."""
    if config is None:
        config = LLMConfig()

    system_prompt, user_messages, episode_ids, validators = _prepare_bulk(
        show, season, episodes, context, cast, plotlines, config,
    )

    results = call_llm_batch(
        system_prompt, user_messages, config,
        cache_system=True, validators=validators,
        batch_id=batch_id, on_batch_submitted=on_batch_submitted,
    )

    return [
        _parse_breakdown(data, ep_id)
        for data, ep_id in zip(results, episode_ids)
    ]


def _parse_breakdown(data: dict, episode_id: str) -> EpisodeBreakdown:
    events = []
    for e in data.get("events", []):
        try:
            events.append(
                Event(
                    event=e["event"],
                    plotline=e.get("plotline"),
                    function=e["function"],
                    characters=e.get("characters", []),
                    also_affects=e.get("also_affects"),
                )
            )
        except KeyError as exc:
            raise ValueError(f"Event missing required field: {exc}") from exc

    interactions = []
    for i in data.get("interactions", []):
        try:
            interactions.append(
                Interaction(
                    type=i["type"],
                    lines=i["lines"],
                    description=i["description"],
                )
            )
        except KeyError as exc:
            raise ValueError(f"Interaction missing required field: {exc}") from exc

    patches = []
    for p in data.get("patches", []):
        try:
            patches.append(
                Patch(
                    action=p["action"],
                    target=p["target"],
                    reason=p["reason"],
                    episodes=p.get("episodes", []),
                )
            )
        except KeyError as exc:
            raise ValueError(f"Patch missing required field: {exc}") from exc

    return EpisodeBreakdown(
        episode=data.get("episode", episode_id),
        events=events,
        theme=data.get("theme", ""),
        interactions=interactions,
        patches=patches,
    )


def _validate(
    breakdown: EpisodeBreakdown,
    plotlines: list[Plotline],
    cast: list[CastMember],
) -> None:
    """Validate Pass 2 output. Raises ValueError on problems."""
    plotline_ids = {p.id for p in plotlines}
    cast_ids = {c.id for c in cast}

    for event in breakdown.events:
        if event.function not in _VALID_FUNCTIONS:
            raise ValueError(
                f"Event {event.event!r}: invalid function {event.function!r}"
            )

        if event.plotline is not None and event.plotline not in plotline_ids:
            raise ValueError(
                f"Event {event.event!r}: plotline {event.plotline!r} "
                f"not found in plotlines: {plotline_ids}"
            )

        for char in event.characters:
            if not char.startswith("guest:") and char not in cast_ids:
                raise ValueError(
                    f"Event {event.event!r}: character {char!r} "
                    f"not in cast and not a guest"
                )

        if event.also_affects:
            for pid in event.also_affects:
                if pid not in plotline_ids:
                    raise ValueError(
                        f"Event {event.event!r}: also_affects {pid!r} "
                        f"not found in plotlines"
                    )

    for interaction in breakdown.interactions:
        if interaction.type not in _VALID_INTERACTION_TYPES:
            raise ValueError(
                f"Interaction: invalid type {interaction.type!r}"
            )

    for patch in breakdown.patches:
        if patch.action not in _VALID_PATCH_ACTIONS:
            raise ValueError(
                f"Patch: invalid action {patch.action!r}"
            )
