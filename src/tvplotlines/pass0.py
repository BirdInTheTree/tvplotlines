"""Pass 0: Detect series context (format + story engine).

Input: show name, season, first 3 synopses.
Output: SeriesContext.
"""

from __future__ import annotations

import json

from tvplotlines.llm import LLMConfig, call_llm
from tvplotlines.models import SeriesContext
from tvplotlines.prompts_en import load_prompt

_VALID_FORMATS = {"procedural", "serial", "hybrid", "ensemble"}


def detect_context(
    show: str,
    season: int,
    episodes: list[tuple[str, str]],
    *,
    config: LLMConfig | None = None,
    suggested_plotlines: list[dict] | None = None,
) -> SeriesContext:
    """Auto-detect series context from first synopses.

    Args:
        show: Series title.
        season: Season number.
        episodes: List of (episode_id, synopsis_text) pairs (first 3 used).
        config: LLM settings.

    Returns:
        SeriesContext with format, is_anthology, story_engine, genre.
    """
    if config is None:
        config = LLMConfig()

    sample = episodes[:3]
    data = {
        "show": show,
        "season": season,
        "sample_synopses": [
            {"episode": eid, "text": text}
            for eid, text in sample
        ],
    }
    if suggested_plotlines:
        data["suggested_plotlines"] = suggested_plotlines
    user_message = json.dumps(data, ensure_ascii=False)

    system_prompt = load_prompt("pass0", lang=config.lang)
    data = call_llm(system_prompt, user_message, config, validator=_validate)

    # Backward compat: old LLM output may have is_ensemble as separate flag
    fmt = data["format"]
    if fmt != "ensemble" and data.get("is_ensemble"):
        fmt = "ensemble"

    return SeriesContext(
        format=fmt,
        story_engine=data["story_engine"],
        genre=data.get("genre", ""),
        is_anthology=bool(data.get("is_anthology", False)),
    )


def _validate(data: dict) -> None:
    """Validate Pass 0 output. Raises ValueError on problems."""
    fmt = data.get("format")
    if fmt not in _VALID_FORMATS:
        raise ValueError(
            f"Invalid format: {fmt!r}. Expected one of {_VALID_FORMATS}"
        )

    if not data.get("story_engine"):
        raise ValueError("story_engine is empty")

    if not isinstance(data.get("is_anthology"), bool):
        raise ValueError("is_anthology must be a boolean")
