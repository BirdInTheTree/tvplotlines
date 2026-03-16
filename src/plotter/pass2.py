"""Pass 2: Assign events to storylines for a single episode.

Input: one episode synopsis + cast + storylines from Pass 1.
Output: EpisodeBreakdown.
"""

from __future__ import annotations

import json

from plotter.llm import LLMConfig, call_llm, call_llm_batch, call_llm_parallel
from plotter.models import (
    CastMember,
    EpisodeBreakdown,
    Event,
    Interaction,
    Patch,
    Plotline,
    SeriesContext,
)
from plotter.prompts import load_prompt

_VALID_FUNCTIONS = {
    "setup", "escalation", "turning_point", "climax",
    "resolution", "cliffhanger", "seed",
}
_VALID_INTERACTION_TYPES = {
    "thematic_rhyme", "dramatic_irony", "convergence", "meta",
}
_VALID_PATCH_ACTIONS = {"ADD_LINE", "CHECK_LINE", "SPLIT_LINE", "RERANK"}


def assign_events(
    show: str,
    season: int,
    episode_number: int,
    synopsis: str,
    context: SeriesContext,
    cast: list[CastMember],
    storylines: list[Plotline],
    *,
    config: LLMConfig | None = None,
) -> EpisodeBreakdown:
    """Assign events from one episode to storylines.

    Args:
        show: Series title.
        season: Season number.
        episode_number: Episode number (1-based).
        synopsis: Synopsis text for this episode.
        context: Series context from Pass 0.
        cast: Cast from Pass 1.
        storylines: Storylines from Pass 1.
        config: LLM settings.

    Returns:
        EpisodeBreakdown for this episode.
    """
    if config is None:
        config = LLMConfig()

    episode_id = f"S{season:02d}E{episode_number:02d}"

    user_message = json.dumps(
        {
            "show": show,
            "season": season,
            "episode": episode_id,
            "franchise_type": context.franchise_type,
            "story_engine": context.story_engine,
            "cast": [
                {"id": c.id, "name": c.name, "aliases": c.aliases}
                for c in cast
            ],
            "storylines": [
                {
                    "id": s.id,
                    "name": s.name,
                    "driver": s.driver,
                    "goal": s.goal,
                    "type": s.type,
                    "rank": s.rank,
                    "devices": s.devices,
                }
                for s in storylines
            ],
            "synopsis": synopsis,
        },
        ensure_ascii=False,
    )

    system_prompt = load_prompt("pass2", lang=config.lang)
    # Cache system prompt — same for all episodes
    def _full_validate(data: dict) -> None:
        bd = _parse_breakdown(data, episode_id)
        _validate(bd, storylines, cast)

    data = call_llm(
        system_prompt, user_message, config,
        cache_system=True, validator=_full_validate,
    )

    return _parse_breakdown(data, episode_id)


def _prepare_bulk(
    show: str,
    season: int,
    synopses: list[str],
    context: SeriesContext,
    cast: list[CastMember],
    storylines: list[Plotline],
    config: LLMConfig,
) -> tuple[str, list[str], list[str], list]:
    """Prepare shared data for parallel/batch Pass 2 calls.

    Returns:
        (system_prompt, user_messages, episode_ids, validators)
    """
    system_prompt = load_prompt("pass2", lang=config.lang)

    user_messages = []
    episode_ids = []
    for i, synopsis in enumerate(synopses):
        episode_id = f"S{season:02d}E{i + 1:02d}"
        episode_ids.append(episode_id)
        user_messages.append(json.dumps(
            {
                "show": show,
                "season": season,
                "episode": episode_id,
                "franchise_type": context.franchise_type,
                "story_engine": context.story_engine,
                "cast": [
                    {"id": c.id, "name": c.name, "aliases": c.aliases}
                    for c in cast
                ],
                "storylines": [
                    {
                        "id": s.id, "name": s.name, "driver": s.driver,
                        "goal": s.goal, "type": s.type, "rank": s.rank,
                        "devices": s.devices,
                    }
                    for s in storylines
                ],
                "synopsis": synopsis,
            },
            ensure_ascii=False,
        ))

    def _make_validator(ep_id: str):
        def _validate_ep(data: dict) -> None:
            bd = _parse_breakdown(data, ep_id)
            _validate(bd, storylines, cast)
        return _validate_ep

    validators = [_make_validator(ep_id) for ep_id in episode_ids]

    return system_prompt, user_messages, episode_ids, validators


def assign_events_parallel(
    show: str,
    season: int,
    synopses: list[str],
    context: SeriesContext,
    cast: list[CastMember],
    storylines: list[Plotline],
    *,
    config: LLMConfig | None = None,
) -> list[EpisodeBreakdown]:
    """Assign events for all episodes in parallel (fast, full price).

    Args:
        show: Series title.
        season: Season number.
        synopses: Synopsis text for each episode (full season).
        context: Series context from Pass 0.
        cast: Cast from Pass 1.
        storylines: Storylines from Pass 1.
        config: LLM settings.

    Returns:
        List of EpisodeBreakdown, one per episode.
    """
    if config is None:
        config = LLMConfig()

    system_prompt, user_messages, episode_ids, validators = _prepare_bulk(
        show, season, synopses, context, cast, storylines, config,
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
    synopses: list[str],
    context: SeriesContext,
    cast: list[CastMember],
    storylines: list[Plotline],
    *,
    config: LLMConfig | None = None,
    batch_id: str | None = None,
    on_batch_submitted=None,
) -> list[EpisodeBreakdown]:
    """Assign events for all episodes in a single batch (50% cheaper, slower).

    Falls back to parallel calls for non-Anthropic providers.

    Args:
        show: Series title.
        season: Season number.
        synopses: Synopsis text for each episode (full season).
        context: Series context from Pass 0.
        cast: Cast from Pass 1.
        storylines: Storylines from Pass 1.
        config: LLM settings.

    Returns:
        List of EpisodeBreakdown, one per episode.
    """
    if config is None:
        config = LLMConfig()

    system_prompt, user_messages, episode_ids, validators = _prepare_bulk(
        show, season, synopses, context, cast, storylines, config,
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
                    storyline=e.get("storyline"),
                    function=e["function"],
                    characters=e.get("characters", []),
                    also_affects=e.get("also_affects"),
                    devices=e.get("devices", []),
                )
            )
        except KeyError as exc:
            raise ValueError(f"Event missing required field: {exc}") from exc

    summary = data.get("summary", {})

    interactions = []
    for i in summary.get("interactions", []):
        try:
            interactions.append(
                Interaction(
                    type=i["type"],
                    lines=i["lines"],
                    description=i["description"],
                    subtype=i.get("subtype"),
                )
            )
        except KeyError as exc:
            raise ValueError(f"Interaction missing required field: {exc}") from exc

    patches = []
    for p in summary.get("patches", []):
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
        theme=summary.get("theme", ""),
        interactions=interactions,
        patches=patches,
    )


def _validate(
    breakdown: EpisodeBreakdown,
    storylines: list[Plotline],
    cast: list[CastMember],
) -> None:
    """Validate Pass 2 output. Raises ValueError on problems."""
    storyline_ids = {s.id for s in storylines}
    cast_ids = {c.id for c in cast}

    for event in breakdown.events:
        if event.function not in _VALID_FUNCTIONS:
            raise ValueError(
                f"Event {event.event!r}: invalid function {event.function!r}"
            )

        # storyline must reference Pass 1 or be null (-> patch)
        if event.storyline is not None and event.storyline not in storyline_ids:
            raise ValueError(
                f"Event {event.event!r}: storyline {event.storyline!r} "
                f"not found in Pass 1 storylines: {storyline_ids}"
            )

        # characters must reference cast or use guest: prefix
        for char in event.characters:
            if not char.startswith("guest:") and char not in cast_ids:
                raise ValueError(
                    f"Event {event.event!r}: character {char!r} "
                    f"not in cast and not a guest"
                )

        # also_affects must reference valid storyline ids
        if event.also_affects:
            for sid in event.also_affects:
                if sid not in storyline_ids:
                    raise ValueError(
                        f"Event {event.event!r}: also_affects {sid!r} "
                        f"not found in storylines"
                    )

    # Unassigned events are handled by postprocess.assign_orphan_events()
    # after all episodes are processed — no rejection here.

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
