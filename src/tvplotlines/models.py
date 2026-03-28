"""Data models for tvplotlines pipeline.

These dataclasses mirror the JSON output of Pass 0, Pass 1, and Pass 2 prompts.
Glossary (tvplotlines-glossary.md) is the source of truth for definitions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SeriesContext:
    """Series metadata from Pass 0 (or provided manually)."""

    format: str  # "procedural" | "serial" | "hybrid" | "ensemble"
    story_engine: str  # one sentence — the mechanism that generates episodes
    genre: str  # "drama", "thriller", "comedy", etc.
    is_anthology: bool = False  # seasons/episodes independent, no continuity

    @property
    def is_ensemble(self) -> bool:
        """Whether the show has 2+ co-equal A-rank plotlines, no single protagonist."""
        return self.format == "ensemble"


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
    nature: str  # "plot-led" | "character-led" | "theme-led"
    confidence: str  # "solid" | "partial" | "inferred"
    computed_rank: str | None = None  # "A" | "B" | "C" | None — set by compute_ranks()
    reviewed_rank: str | None = None  # "A" | "B" | "C" | None — set by Pass 3 CREATE
    span: list[str] = field(default_factory=list)  # computed from Pass 2

    @property
    def rank(self) -> str | None:
        """Effective rank: reviewed_rank takes precedence over computed_rank."""
        return self.reviewed_rank or self.computed_rank


@dataclass
class Event:
    """A single event within an episode, assigned to a plotline by Pass 2."""

    event: str  # one sentence
    plotline_id: str | None  # Plotline.id, or None for unassigned
    function: str  # "setup" | "inciting_incident" | "escalation" | "turning_point" | "crisis" | "climax" | "resolution"
    characters: list[str]  # CastMember.id; guests use "guest:short_name"
    also_affects: list[str] | None = None  # Plotline.id list
    plot_fn: str | None = None  # arc function — event's role in the season-long plotline arc


@dataclass
class Interaction:
    """A relationship between plotlines within an episode."""

    type: str  # "thematic_rhyme" | "dramatic_irony" | "convergence"
    lines: list[str]  # Plotline.id list
    description: str  # one sentence


@dataclass
class EpisodeBreakdown:
    """Pass 2 output for a single episode."""

    episode: str  # "S01E03"
    events: list[Event] = field(default_factory=list)
    theme: str = ""
    interactions: list[Interaction] = field(default_factory=list)


@dataclass
class Verdict:
    """A structural decision from Pass 3 (structural review)."""

    action: str  # "MERGE" | "REASSIGN" | "CREATE" | "DROP" | "REFUNCTION"
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
        """Serialize to plain dict (for JSON export).

        Adds the ``rank`` property to each plotline dict because
        dataclasses.asdict() only sees fields, not properties.
        """
        d: dict[str, Any] = asdict(self)
        for pd, plotline in zip(d["plotlines"], self.plotlines):
            pd["rank"] = plotline.rank
        return d
