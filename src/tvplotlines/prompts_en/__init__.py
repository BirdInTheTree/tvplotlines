"""English prompt templates for each pipeline pass.

Prompts are stored as .md files and loaded at runtime as system prompts.
"""

from importlib import resources


_glossary_cache: str | None = None


def _load_glossary() -> str:
    """Load shared glossary (cached)."""
    global _glossary_cache
    if _glossary_cache is None:
        _glossary_cache = resources.files(__package__).joinpath("glossary.md").read_text(encoding="utf-8")
    return _glossary_cache


def load_prompt(pass_name: str, lang: str = "en") -> str:
    """Load a prompt template by pass name.

    If the prompt contains {GLOSSARY}, it is replaced with the shared
    glossary from glossary.md.

    Args:
        pass_name: "pass0", "pass1", "pass2", or "pass3".
        lang: Language code. Only "en" is supported currently.

    Returns:
        Prompt text (markdown).
    """
    filename = f"{pass_name}.md"
    text = resources.files(__package__).joinpath(filename).read_text(encoding="utf-8")
    if "{GLOSSARY}" in text:
        text = text.replace("{GLOSSARY}", _load_glossary())
    return text
