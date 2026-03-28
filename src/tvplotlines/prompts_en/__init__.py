"""Prompt templates for each pipeline pass.

Prompts are stored as .md files and loaded at runtime as system prompts.
Supports English (default) and Russian prompt sets.
"""

from importlib import resources

_LANG_PACKAGES = {
    "en": "tvplotlines.prompts_en",
    "ru": "tvplotlines.prompts_ru",
}

_glossary_cache: dict[str, str] = {}


def _load_glossary(lang: str) -> str:
    """Load shared glossary for a language (cached)."""
    if lang not in _glossary_cache:
        package = _LANG_PACKAGES[lang]
        _glossary_cache[lang] = (
            resources.files(package).joinpath("glossary.md").read_text(encoding="utf-8")
        )
    return _glossary_cache[lang]


def load_prompt(pass_name: str, lang: str = "en") -> str:
    """Load a prompt template by pass name and language.

    If the prompt contains {GLOSSARY}, it is replaced with the shared
    glossary from the same language package.

    Args:
        pass_name: "pass0", "pass1", "pass2", "pass3", "pass4", or "synopses_writer".
        lang: Language code — "en" or "ru".

    Returns:
        Prompt text (markdown).
    """
    if lang not in _LANG_PACKAGES:
        raise ValueError(f"Unsupported language: {lang!r}. Expected one of {list(_LANG_PACKAGES)}")
    package = _LANG_PACKAGES[lang]
    filename = f"{pass_name}.md"
    text = resources.files(package).joinpath(filename).read_text(encoding="utf-8")
    if "{GLOSSARY}" in text:
        text = text.replace("{GLOSSARY}", _load_glossary(lang))
    return text
