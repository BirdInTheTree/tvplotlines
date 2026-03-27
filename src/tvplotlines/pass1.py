"""Pass 1: Extract plotlines and cast from all season synopses.

Input: show, season, format, story_engine, all synopses.
Output: list[CastMember], list[Plotline].
"""

from __future__ import annotations

import json
import logging
from collections import Counter

from tvplotlines.llm import LLMConfig, call_llm, call_llm_parallel
from tvplotlines.models import CastMember, Plotline, SeriesContext
from tvplotlines.prompts_en import load_prompt

logger = logging.getLogger(__name__)

_VOTING_ROUNDS = 3

_VALID_TYPES = {"case_of_the_week", "serialized", "runner"}
_VALID_NATURES = {"plot-led", "character-led", "theme-led"}
_VALID_CONFIDENCE = {"solid", "partial", "inferred"}


def _build_user_message(
    show: str,
    season: int,
    context: SeriesContext,
    episodes: list[tuple[str, str]],
    *,
    prior_cast: list[CastMember] | None = None,
    prior_plotlines: list[Plotline] | None = None,
    suggested_plotlines: list[dict] | None = None,
) -> str:
    """Build the JSON user message for Pass 1."""
    data = {
        "show": show,
        "season": season,
        "format": context.format,
        "is_ensemble": context.is_ensemble,
        "story_engine": context.story_engine,
        "synopses": [
            {"episode": eid, "text": text}
            for eid, text in episodes
        ],
    }
    if suggested_plotlines:
        data["suggested_plotlines"] = suggested_plotlines
    if prior_cast and prior_plotlines:
        data["prior_season"] = {
            "cast": [
                {"id": c.id, "name": c.name, "aliases": c.aliases}
                for c in prior_cast
            ],
            "plotlines": [
                {
                    "id": p.id, "name": p.name, "hero": p.hero,
                    "goal": p.goal, "obstacle": p.obstacle, "stakes": p.stakes,
                    "type": p.type, "rank": p.rank,
                }
                for p in prior_plotlines
            ],
        }
    return json.dumps(data, ensure_ascii=False)


def _check_prior_overlap(
    new_plotlines: list[Plotline],
    prior_plotlines: list[Plotline],
) -> None:
    """Warn if a new plotline shares a hero with a prior plotline that wasn't continued."""
    prior_by_hero: dict[str, list[Plotline]] = {}
    for p in prior_plotlines:
        prior_by_hero.setdefault(p.hero, []).append(p)

    new_ids = {p.id for p in new_plotlines}

    for hero, priors in prior_by_hero.items():
        for prior in priors:
            if prior.id in new_ids:
                continue
            new_with_same_hero = [p for p in new_plotlines if p.hero == hero]
            for new_p in new_with_same_hero:
                logger.warning(
                    "Prior plotline %r (hero=%s) was not continued, "
                    "but new plotline %r has the same hero. "
                    "Possible duplicate?",
                    prior.id, hero, new_p.id,
                )


def extract_plotlines(
    show: str,
    season: int,
    context: SeriesContext,
    episodes: list[tuple[str, str]],
    *,
    prior_cast: list[CastMember] | None = None,
    prior_plotlines: list[Plotline] | None = None,
    suggested_plotlines: list[dict] | None = None,
    config: LLMConfig | None = None,
) -> tuple[list[CastMember], list[Plotline]]:
    """Extract cast and plotlines from all season synopses.

    Args:
        show: Series title.
        season: Season number.
        context: From Pass 0 or user-provided.
        episodes: List of (episode_id, synopsis_text) pairs.
        prior_cast: Cast from the previous season (for continuity).
        prior_plotlines: Plotlines from the previous season (for continuity).
        config: LLM settings.

    Returns:
        Tuple of (cast, plotlines).
    """
    if config is None:
        config = LLMConfig()

    user_message = _build_user_message(
        show, season, context, episodes,
        prior_cast=prior_cast, prior_plotlines=prior_plotlines,
        suggested_plotlines=suggested_plotlines,
    )

    system_prompt = load_prompt("pass1", lang=config.lang)

    def _full_validate(data: dict) -> None:
        """Parse and validate in one step for retry support."""
        c = _parse_cast(data)
        p = _parse_plotlines(data, c)
        _validate(p, c, context)

    # Majority voting: run Pass 1 multiple times, pick most common plotline set
    user_messages = [user_message] * _VOTING_ROUNDS
    validators = [_full_validate] * _VOTING_ROUNDS
    results = call_llm_parallel(
        system_prompt, user_messages, config, validators=validators,
    )

    # Pick the result whose plotline ID set appears most often
    id_sets = [
        tuple(sorted(s["id"] for s in r.get("plotlines", [])))
        for r in results
    ]
    most_common_ids = Counter(id_sets).most_common(1)[0][0]
    data = next(r for r, ids in zip(results, id_sets) if ids == most_common_ids)
    logger.info(
        "Pass 1 voting: %d/%d agreed on %s",
        id_sets.count(most_common_ids), _VOTING_ROUNDS, most_common_ids,
    )

    cast = _parse_cast(data)
    plotlines = _parse_plotlines(data, cast)

    if prior_plotlines:
        _check_prior_overlap(plotlines, prior_plotlines)

    return cast, plotlines


def _parse_cast(data: dict) -> list[CastMember]:
    cast = []
    for c in data.get("cast", []):
        try:
            cast.append(
                CastMember(
                    id=c["id"],
                    name=c["name"],
                    aliases=c.get("aliases", []),
                )
            )
        except KeyError as e:
            raise ValueError(f"Cast member missing required field: {e}") from e
    return cast


def _parse_plotlines(data: dict, cast: list[CastMember]) -> list[Plotline]:
    cast_ids = {c.id for c in cast}
    plotlines = []
    for s in data.get("plotlines", []):
        try:
            hero = s["hero"]
        except KeyError as e:
            raise ValueError(f"Plotline missing required field: {e}") from e
        if hero not in cast_ids:
            raise ValueError(
                f"Plotline {s['id']!r} has hero {hero!r} not found in cast: {cast_ids}"
            )
        try:
            plotlines.append(
                Plotline(
                    id=s["id"],
                    name=s["name"],
                    hero=hero,
                    goal=s["goal"],
                    obstacle=s["obstacle"],
                    stakes=s["stakes"],
                    type=s["type"],
                    nature=s["nature"],
                    confidence=s["confidence"],
                )
            )
        except KeyError as e:
            raise ValueError(f"Plotline {s.get('id', '?')!r} missing field: {e}") from e
    return plotlines


def _validate(
    plotlines: list[Plotline],
    cast: list[CastMember],
    context: SeriesContext,
) -> None:
    """Validate Pass 1 output. Raises ValueError on problems."""
    if not plotlines:
        raise ValueError("No plotlines extracted")

    if not cast:
        raise ValueError("No cast members extracted")

    for p in plotlines:
        if p.type not in _VALID_TYPES:
            raise ValueError(f"Plotline {p.id!r}: invalid type {p.type!r}")
        if p.nature not in _VALID_NATURES:
            raise ValueError(f"Plotline {p.id!r}: invalid nature {p.nature!r}")
        if p.confidence not in _VALID_CONFIDENCE:
            raise ValueError(f"Plotline {p.id!r}: invalid confidence {p.confidence!r}")

    # Procedural/hybrid must have exactly one case_of_the_week plotline
    if context.format in ("procedural", "hybrid"):
        cotw_count = sum(1 for p in plotlines if p.type == "case_of_the_week")
        if cotw_count != 1:
            raise ValueError(
                f"format={context.format!r} expects exactly 1 case_of_the_week "
                f"plotline, got {cotw_count}"
            )
