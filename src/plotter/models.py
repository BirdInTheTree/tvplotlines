"""Data models for Plotter pipeline.

These dataclasses mirror the JSON output of Pass 0, Pass 1, and Pass 2 prompts.
Prompts are the source of truth — if they change, update models to match.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class SeriesContext:
    """Series metadata from Pass 0 (or provided manually)."""

    franchise_type: str  # "procedural" | "serial" | "hybrid" | "ensemble"
    story_engine: str  # one sentence — the mechanism that generates episodes
    genre: str  # "drama", "thriller", "comedy", etc.
    format: str | None = None  # "ongoing" | "limited" | "anthology"


@dataclass
class CastMember:
    """Main cast member identified by Pass 1."""

    id: str  # snake_case identifier: "walt", "jesse"
    name: str  # full name: "Walter White"
    aliases: list[str] = field(default_factory=list)  # ["Walt", "Heisenberg"]


@dataclass
class Plotline:
    """A storyline extracted by Pass 1."""

    id: str  # snake_case identifier: "empire", "family"
    name: str  # display name by goal: "Empire", "Investigation"
    driver: str  # CastMember.id
    goal: str
    obstacle: str
    stakes: str
    type: str  # "episodic" | "serialized" | "runner"
    rank: str  # "A" | "B" | "C" | "runner"
    nature: str  # "plot-led" | "character-led"
    confidence: str  # "solid" | "partial" | "inferred"
    span: list[str] = field(default_factory=list)  # computed from Pass 2


@dataclass
class Event:
    """A single event within an episode, assigned to a storyline by Pass 2."""

    event: str  # one sentence
    storyline: str | None  # Plotline.id, or None for unassigned (-> ADD_LINE patch)
    function: str  # "setup" | "escalation" | "turning_point" | "climax" | "resolution" | "cliffhanger" | "seed"
    characters: list[str]  # CastMember.id; guests use "guest:short_name"
    also_affects: list[str] | None = None  # Plotline.id list


@dataclass
class Interaction:
    """A relationship between storylines within an episode."""

    type: str  # "thematic_rhyme" | "dramatic_irony" | "convergence" | "meta"
    lines: list[str]  # Plotline.id list
    description: str  # one sentence
    subtype: str | None = None  # for meta: "twist-reveal", "wraparound", "time_jump"


@dataclass
class Patch:
    """A suggestion from Pass 2 to modify the Pass 1 storyline list."""

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
    """A structural decision from Pass 3 (narratologist review)."""

    action: str  # "MERGE" | "REASSIGN" | "PROMOTE" | "DEMOTE" | "CREATE" | "DROP"
    data: dict  # full verdict payload — structure depends on action


@dataclass
class PlotterResult:
    """Complete output of the Plotter pipeline."""

    context: SeriesContext
    cast: list[CastMember] = field(default_factory=list)
    plotlines: list[Plotline] = field(default_factory=list)
    episodes: list[EpisodeBreakdown] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to plain dict (for JSON export)."""
        return asdict(self)
