"""English prompt templates for each pipeline pass.

Prompts are stored as .md files and loaded at runtime as system prompts.
"""

from importlib import resources


def load_prompt(pass_name: str) -> str:
    """Load an English prompt template by pass name.

    Args:
        pass_name: "pass0", "pass1", "pass2", or "pass3".

    Returns:
        Prompt text (markdown).
    """
    filename = f"{pass_name}.md"
    return resources.files(__package__).joinpath(filename).read_text(encoding="utf-8")
