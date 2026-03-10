"""Pass 0: Detect series context (franchise type + story engine).

Input: show name, season, first 2-3 synopses, optional description.
Output: SeriesContext.
"""

from __future__ import annotations

import json

from plotter.llm import LLMConfig, call_llm
from plotter.models import SeriesContext
from plotter.prompts import load_prompt

_VALID_FRANCHISE_TYPES = {"procedural", "serial", "hybrid", "ensemble"}
_VALID_FORMATS = {"ongoing", "limited", "anthology"}


def detect_context(
    show: str,
    season: int,
    episodes: list[str],
    *,
    description: str = "",
    config: LLMConfig | None = None,
) -> SeriesContext:
    """Auto-detect series context from first synopses.

    Args:
        show: Series title.
        season: Season number.
        episodes: All episode synopses (first 2-3 will be used).
        description: Show description / logline (optional).
        config: LLM settings.

    Returns:
        SeriesContext with franchise_type, story_engine, genre, format.
    """
    if config is None:
        config = LLMConfig()

    sample = episodes[:3]
    user_message = json.dumps(
        {
            "show": show,
            "season": season,
            "description": description,
            "sample_synopses": [
                {"episode": f"S{season:02d}E{i+1:02d}", "text": s}
                for i, s in enumerate(sample)
            ],
        },
        ensure_ascii=False,
    )

    system_prompt = load_prompt("pass0")
    data = call_llm(system_prompt, user_message, config, validator=_validate)

    return SeriesContext(
        franchise_type=data["franchise_type"],
        story_engine=data["story_engine"],
        genre=data.get("genre", ""),
        format=data.get("format"),
    )


def _validate(data: dict) -> None:
    """Validate Pass 0 output. Raises ValueError on problems."""
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
