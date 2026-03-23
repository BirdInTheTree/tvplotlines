"""Prompt templates for each pipeline pass.

Prompts are stored as .md files and loaded at runtime as system prompts.
Two language versions: Russian (default, this package) and English (prompts_en).
"""

from importlib import resources


def load_prompt(pass_name: str, *, lang: str = "ru") -> str:
    """Load a prompt template by pass name and language.

    Args:
        pass_name: "pass0", "pass1", "pass2", or "pass3".
        lang: "ru" (default) or "en".

    Returns:
        Prompt text (markdown).
    """
    filename = f"{pass_name}.md"
    if lang == "en":
        pkg = __package__.rsplit(".", 1)[0] + ".prompts_en"
    else:
        pkg = __package__
    return resources.files(pkg).joinpath(filename).read_text(encoding="utf-8")
