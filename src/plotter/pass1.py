"""Pass 1: Extract storylines and cast from all season synopses.

Input: show, season, franchise_type, story_engine, all synopses.
Output: list[CastMember], list[Plotline].
"""

from __future__ import annotations

import json
import logging
from collections import Counter

from plotter.llm import LLMConfig, call_llm, call_llm_parallel
from plotter.models import CastMember, Plotline, SeriesContext
from plotter.prompts import load_prompt

logger = logging.getLogger(__name__)

_VOTING_ROUNDS = 3

_VALID_TYPES = {"episodic", "serialized", "runner"}
_VALID_RANKS = {"A", "B", "C", "runner"}
_VALID_NATURES = {"plot-led", "character-led"}
_VALID_CONFIDENCE = {"solid", "partial", "inferred"}


def _build_user_message(
    show: str,
    season: int,
    context: SeriesContext,
    episodes: list[tuple[str, str]],
    *,
    prior_cast: list[CastMember] | None = None,
    prior_plotlines: list[Plotline] | None = None,
) -> str:
    """Build the JSON user message for Pass 1.

    Args:
        show: Series title.
        season: Season number.
        context: From Pass 0 or user-provided.
        episodes: List of (episode_id, synopsis_text) pairs.
        prior_cast: Cast from the previous season (for continuity).
        prior_plotlines: Storylines from the previous season (for continuity).

    Returns:
        JSON-encoded string ready to send as a user message.
    """
    data = {
        "show": show,
        "season": season,
        "franchise_type": context.franchise_type,
        "story_engine": context.story_engine,
        "synopses": [
            {"episode": eid, "text": text}
            for eid, text in episodes
        ],
    }
    if prior_cast and prior_plotlines:
        data["prior_season"] = {
            "cast": [
                {"id": c.id, "name": c.name, "aliases": c.aliases}
                for c in prior_cast
            ],
            "plotlines": [
                {
                    "id": p.id, "name": p.name, "driver": p.driver,
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
    """Warn if a new plotline shares a driver with a prior plotline that wasn't continued.

    Args:
        new_plotlines: Storylines extracted for the current season.
        prior_plotlines: Storylines from the previous season.
    """
    prior_by_driver: dict[str, list[Plotline]] = {}
    for p in prior_plotlines:
        prior_by_driver.setdefault(p.driver, []).append(p)

    new_ids = {p.id for p in new_plotlines}

    for driver, priors in prior_by_driver.items():
        for prior in priors:
            if prior.id in new_ids:
                continue  # Prior storyline was continued — no issue
            new_with_same_driver = [p for p in new_plotlines if p.driver == driver]
            for new_p in new_with_same_driver:
                logger.warning(
                    "Prior storyline %r (driver=%s) was not continued, "
                    "but new storyline %r has the same driver. "
                    "Possible duplicate?",
                    prior.id, driver, new_p.id,
                )


def extract_storylines(
    show: str,
    season: int,
    context: SeriesContext,
    episodes: list[tuple[str, str]],
    *,
    prior_cast: list[CastMember] | None = None,
    prior_plotlines: list[Plotline] | None = None,
    config: LLMConfig | None = None,
) -> tuple[list[CastMember], list[Plotline]]:
    """Extract cast and storylines from all season synopses.

    Args:
        show: Series title.
        season: Season number.
        context: From Pass 0 or user-provided.
        episodes: List of (episode_id, synopsis_text) pairs.
        prior_cast: Cast from the previous season (for continuity).
        prior_plotlines: Storylines from the previous season (for continuity).
        config: LLM settings.

    Returns:
        Tuple of (cast, storylines).
    """
    if config is None:
        config = LLMConfig()

    user_message = _build_user_message(
        show, season, context, episodes,
        prior_cast=prior_cast, prior_plotlines=prior_plotlines,
    )

    system_prompt = load_prompt("pass1", lang=config.lang)

    def _full_validate(data: dict) -> None:
        """Parse and validate in one step for retry support."""
        c = _parse_cast(data)
        s = _parse_storylines(data, c)
        _validate(s, c, context)

    # Majority voting: run Pass 1 multiple times, pick most common storyline set
    user_messages = [user_message] * _VOTING_ROUNDS
    validators = [_full_validate] * _VOTING_ROUNDS
    results = call_llm_parallel(
        system_prompt, user_messages, config, validators=validators,
    )

    # Pick the result whose storyline ID set appears most often
    id_sets = [
        tuple(sorted(s["id"] for s in r.get("storylines", [])))
        for r in results
    ]
    most_common_ids = Counter(id_sets).most_common(1)[0][0]
    # Use the first result that matches
    data = next(r for r, ids in zip(results, id_sets) if ids == most_common_ids)
    logger.info(
        "Pass 1 voting: %d/%d agreed on %s",
        id_sets.count(most_common_ids), _VOTING_ROUNDS, most_common_ids,
    )

    cast = _parse_cast(data)
    storylines = _parse_storylines(data, cast)

    if prior_plotlines:
        _check_prior_overlap(storylines, prior_plotlines)

    return cast, storylines


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


def _parse_storylines(data: dict, cast: list[CastMember]) -> list[Plotline]:
    cast_ids = {c.id for c in cast}
    storylines = []
    for s in data.get("storylines", []):
        try:
            driver = s["driver"]
        except KeyError as e:
            raise ValueError(f"Storyline missing required field: {e}") from e
        if driver not in cast_ids:
            raise ValueError(
                f"Storyline {s['id']!r} has driver {driver!r} not found in cast: {cast_ids}"
            )
        try:
            storylines.append(
                Plotline(
                    id=s["id"],
                    name=s["name"],
                    driver=driver,
                    goal=s["goal"],
                    obstacle=s["obstacle"],
                    stakes=s["stakes"],
                    type=s["type"],
                    rank=s["rank"],
                    nature=s["nature"],
                    confidence=s["confidence"],
                    devices=s.get("devices", []),
                )
            )
        except KeyError as e:
            raise ValueError(f"Storyline {s.get('id', '?')!r} missing field: {e}") from e
    return storylines


def _validate(
    storylines: list[Plotline],
    cast: list[CastMember],
    context: SeriesContext,
) -> None:
    """Validate Pass 1 output. Raises ValueError on problems."""
    if not storylines:
        raise ValueError("No storylines extracted")

    if not cast:
        raise ValueError("No cast members extracted")

    for s in storylines:
        if s.type not in _VALID_TYPES:
            raise ValueError(f"Storyline {s.id!r}: invalid type {s.type!r}")
        if s.rank not in _VALID_RANKS:
            raise ValueError(f"Storyline {s.id!r}: invalid rank {s.rank!r}")
        if s.nature not in _VALID_NATURES:
            raise ValueError(f"Storyline {s.id!r}: invalid nature {s.nature!r}")
        if s.confidence not in _VALID_CONFIDENCE:
            raise ValueError(f"Storyline {s.id!r}: invalid confidence {s.confidence!r}")

    # Procedural/hybrid must have exactly one episodic storyline
    if context.franchise_type in ("procedural", "hybrid"):
        episodic_count = sum(1 for s in storylines if s.type == "episodic")
        if episodic_count != 1:
            raise ValueError(
                f"franchise_type={context.franchise_type!r} expects exactly 1 episodic "
                f"storyline, got {episodic_count}"
            )

    # A-rank count must match franchise type
    a_count = sum(1 for s in storylines if s.rank == "A")
    if context.franchise_type in ("serial", "procedural", "hybrid"):
        if a_count != 1:
            raise ValueError(
                f"franchise_type={context.franchise_type!r} expects exactly 1 A-rank "
                f"storyline, got {a_count}"
            )
    elif context.franchise_type == "ensemble":
        if a_count < 2:
            raise ValueError(
                f"franchise_type='ensemble' expects 2+ A-rank storylines, got {a_count}"
            )
