"""Prompt templates for each pipeline pass.

Prompts are stored as .md files in prompts_en/ and loaded at runtime as system prompts.
"""

from importlib import resources


def load_prompt(pass_name: str, *, lang: str = "en") -> str:
    """Load a prompt template by pass name.

    Args:
        pass_name: "pass0", "pass1", "pass2", or "pass3".
        lang: Currently only "en" is supported.

    Returns:
        Prompt text (markdown).
    """
    if lang != "en":
        raise ValueError(f"Unsupported language: {lang!r}. Only 'en' is currently supported.")
    filename = f"{pass_name}.md"
    pkg = __package__.rsplit(".", 1)[0] + ".prompts_en"
    return resources.files(pkg).joinpath(filename).read_text(encoding="utf-8")
