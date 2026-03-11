"""Pass 1: Extract storylines and cast from all season synopses.

Input: show, season, franchise_type, story_engine, all synopses.
Output: list[CastMember], list[Plotline].
"""

from __future__ import annotations

import json

from plotter.llm import LLMConfig, call_llm
from plotter.models import CastMember, Plotline, SeriesContext
from plotter.prompts import load_prompt

_VALID_TYPES = {"episodic", "serialized", "runner"}
_VALID_RANKS = {"A", "B", "C", "runner"}
_VALID_NATURES = {"plot-led", "character-led"}
_VALID_CONFIDENCE = {"solid", "partial", "inferred"}


def extract_storylines(
    show: str,
    season: int,
    context: SeriesContext,
    episodes: list[str],
    *,
    config: LLMConfig | None = None,
) -> tuple[list[CastMember], list[Plotline]]:
    """Extract cast and storylines from all season synopses.

    Args:
        show: Series title.
        season: Season number.
        context: From Pass 0 or user-provided.
        episodes: All episode synopses.
        config: LLM settings.

    Returns:
        Tuple of (cast, storylines).
    """
    if config is None:
        config = LLMConfig()

    user_message = json.dumps(
        {
            "show": show,
            "season": season,
            "franchise_type": context.franchise_type,
            "story_engine": context.story_engine,
            "synopses": [
                {"episode": f"S{season:02d}E{i+1:02d}", "text": s}
                for i, s in enumerate(episodes)
            ],
        },
        ensure_ascii=False,
    )

    system_prompt = load_prompt("pass1", lang=config.lang)

    def _full_validate(data: dict) -> None:
        """Parse and validate in one step for retry support."""
        c = _parse_cast(data)
        s = _parse_storylines(data, c)
        _validate(s, c, context)

    data = call_llm(system_prompt, user_message, config, validator=_full_validate)

    cast = _parse_cast(data)
    storylines = _parse_storylines(data, cast)
    return cast, storylines


def _parse_cast(data: dict) -> list[CastMember]:
    cast = []
    for c in data.get("cast", []):
        cast.append(
            CastMember(
                id=c["id"],
                name=c["name"],
                aliases=c.get("aliases", []),
            )
        )
    return cast


def _parse_storylines(data: dict, cast: list[CastMember]) -> list[Plotline]:
    cast_ids = {c.id for c in cast}
    storylines = []
    for s in data.get("storylines", []):
        driver = s["driver"]
        if driver not in cast_ids:
            raise ValueError(
                f"Storyline {s['id']!r} has driver {driver!r} not found in cast: {cast_ids}"
            )
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
            )
        )
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
