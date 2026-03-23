"""Pass 1 Merged: Context detection + storyline extraction in one LLM call.

Used in ablation study to test whether separating Pass 0 from Pass 1 improves quality.
Input: show name, season, all synopses.
Output: SeriesContext, list[CastMember], list[Plotline].
"""

from __future__ import annotations

import json
import logging
from collections import Counter

from tvplotlines.llm import LLMConfig, call_llm_parallel
from tvplotlines.models import CastMember, Plotline, SeriesContext
from tvplotlines.pass0 import _VALID_FRANCHISE_TYPES, _VALID_FORMATS
from tvplotlines.pass1 import _parse_cast, _parse_storylines, _validate, _VOTING_ROUNDS
from tvplotlines.prompts import load_prompt

logger = logging.getLogger(__name__)


def extract_storylines_merged(
    show: str,
    season: int,
    episodes: list[tuple[str, str]],
    *,
    config: LLMConfig | None = None,
) -> tuple[SeriesContext, list[CastMember], list[Plotline]]:
    """Extract context, cast, and storylines in a single LLM call.

    Args:
        show: Series title.
        season: Season number.
        episodes: List of (episode_id, synopsis_text) pairs.
        config: LLM settings.

    Returns:
        Tuple of (context, cast, storylines).
    """
    if config is None:
        config = LLMConfig()

    user_message = json.dumps(
        {
            "show": show,
            "season": season,
            "synopses": [
                {"episode": eid, "text": text}
                for eid, text in episodes
            ],
        },
        ensure_ascii=False,
    )

    system_prompt = load_prompt("pass1_merged", lang=config.lang)

    def _full_validate(data: dict) -> None:
        """Validate both context and storyline fields."""
        _validate_context(data)
        context = SeriesContext(
            franchise_type=data["franchise_type"],
            story_engine=data["story_engine"],
            genre=data.get("genre", ""),
            format=data.get("format"),
        )
        c = _parse_cast(data)
        s = _parse_storylines(data, c)
        _validate(s, c, context)

    # Majority voting — same as pass1.py
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
    data = next(r for r, ids in zip(results, id_sets) if ids == most_common_ids)
    logger.info(
        "Pass 1 merged voting: %d/%d agreed on %s",
        id_sets.count(most_common_ids), _VOTING_ROUNDS, most_common_ids,
    )

    context = SeriesContext(
        franchise_type=data["franchise_type"],
        story_engine=data["story_engine"],
        genre=data.get("genre", ""),
        format=data.get("format"),
    )
    cast = _parse_cast(data)
    storylines = _parse_storylines(data, cast)
    return context, cast, storylines


def _validate_context(data: dict) -> None:
    """Validate context fields in merged output."""
    ft = data.get("franchise_type")
    if ft not in _VALID_FRANCHISE_TYPES:
        raise ValueError(
            f"Invalid franchise_type: {ft!r}. Expected one of {_VALID_FRANCHISE_TYPES}"
        )
    if not data.get("story_engine"):
        raise ValueError("story_engine is empty")
    fmt = data.get("format")
    if fmt is not None and fmt not in _VALID_FORMATS:
        raise ValueError(
            f"Invalid format: {fmt!r}. Expected one of {_VALID_FORMATS} or null"
        )
