"""Data models for tvplotlines pipeline.

These dataclasses mirror the JSON output of Pass 0, Pass 1, and Pass 2 prompts.
Glossary (tvplotlines-glossary.md) is the source of truth for definitions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class SeriesContext:
    """Series metadata from Pass 0 (or provided manually)."""

    format: str  # "procedural" | "serial" | "hybrid" | "limited"
    story_engine: str  # one sentence — the mechanism that generates episodes
    genre: str  # "drama", "thriller", "comedy", etc.
    is_ensemble: bool = False  # 2+ co-equal A-rank plotlines, no single protagonist
    is_anthology: bool = False  # seasons/episodes independent, no continuity


@dataclass
class CastMember:
    """Main cast member identified by Pass 1."""

    id: str  # snake_case identifier: "walt", "jesse"
    name: str  # full name: "Walter White"
    aliases: list[str] = field(default_factory=list)  # ["Walt", "Heisenberg"]


@dataclass
class Plotline:
    """A plotline extracted by Pass 1."""

    id: str  # snake_case identifier: "empire", "family"
    name: str  # "Hero: Theme" format: "Walt: Empire"
    hero: str  # CastMember.id
    goal: str
    obstacle: str
    stakes: str
    type: str  # "case_of_the_week" | "serialized" | "runner"
    rank: str | None  # "A" | "B" | "C" | None (None for type=runner)
    nature: str  # "plot-led" | "character-led" | "theme-led"
    confidence: str  # "solid" | "partial" | "inferred"
    span: list[str] = field(default_factory=list)  # computed from Pass 2


@dataclass
class Event:
    """A single event within an episode, assigned to a plotline by Pass 2."""

    event: str  # one sentence
    plotline: str | None  # Plotline.id, or None for unassigned (-> ADD_LINE patch)
    function: str  # "setup" | "inciting_incident" | "escalation" | "turning_point" | "crisis" | "climax" | "resolution"
    characters: list[str]  # CastMember.id; guests use "guest:short_name"
    also_affects: list[str] | None = None  # Plotline.id list


@dataclass
class Interaction:
    """A relationship between plotlines within an episode."""

    type: str  # "thematic_rhyme" | "dramatic_irony" | "convergence"
    lines: list[str]  # Plotline.id list
    description: str  # one sentence


@dataclass
class Patch:
    """A suggestion from Pass 2 to modify the Pass 1 plotline list."""

    action: str  # "ADD_LINE" | "CHECK_LINE" | "SPLIT_LINE" | "RERANK"
    target: str  # Plotline.id (or proposed new id)
    reason: str
    episodes: list[str] = field(default_factory=list)


@dataclass
class EpisodeBreakdown:
    """Pass 2 output for a single episode."""

    episode: str  # "S01E03"
    events: list[Event] = field(default_factory=list)
    theme: str = ""
    interactions: list[Interaction] = field(default_factory=list)
    patches: list[Patch] = field(default_factory=list)


@dataclass
class Verdict:
    """A structural decision from Pass 3 (structural review)."""

    action: str  # "MERGE" | "REASSIGN" | "PROMOTE" | "DEMOTE" | "CREATE" | "DROP" | "REFUNCTION"
    data: dict  # full verdict payload — structure depends on action


@dataclass
class TVPlotlinesResult:
    """Complete output of the tvplotlines pipeline."""

    context: SeriesContext
    cast: list[CastMember] = field(default_factory=list)
    plotlines: list[Plotline] = field(default_factory=list)
    episodes: list[EpisodeBreakdown] = field(default_factory=list)
    usage: str = ""

    def to_dict(self) -> dict:
        """Serialize to plain dict (for JSON export)."""
        return asdict(self)
