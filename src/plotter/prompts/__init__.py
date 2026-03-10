"""Prompt templates for each pipeline pass.

Prompts are stored as .md files and loaded at runtime as system prompts.
Source of truth: how2pitch/pitch_bible/md/prompt-pass*.md
These are copies — when source prompts change, update copies here.
"""

from importlib import resources


def load_prompt(pass_name: str) -> str:
    """Load a prompt template by pass name.

    Args:
        pass_name: "pass0", "pass1", or "pass2".

    Returns:
        Prompt text (markdown).
    """
    filename = f"{pass_name}.md"
    return resources.files(__package__).joinpath(filename).read_text(encoding="utf-8")
