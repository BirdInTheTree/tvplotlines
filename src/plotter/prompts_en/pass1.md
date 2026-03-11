# Prompt: Pass 1 — Storyline Extraction

> **Self-contained document.** Compiled from `storyline-extraction-reference.md`, but fed to the LLM as-is. When reference is updated — recompile.

## Contract

- **Input**: Pass 0 output (`show`, `season`, `franchise_type`, `story_engine`) + all season synopses
- **Output**: JSON with storyline list and cast → passed as input to Pass 2

## Input

- **show**: show title (from Pass 0)
- **season**: season number (from Pass 0)
- **franchise_type**: procedural / serial / hybrid / ensemble (from Pass 0)
- **story_engine**: one sentence (from Pass 0)
- **format**: ongoing / limited / anthology / null (from Pass 0)
- **synopses**: all season synopses (text)

## Task

Read ALL season synopses. Extract the list of storylines and the main cast.

## Rules

### Storyline = Story DNA

A storyline = hero + goal + obstacle + stakes. Missing any component — not a storyline, but an event within another storyline.

Additionally: a storyline has a three-act structure, conflict, and a causal chain of events. A storyline is tied to a main cast character (not a guest).

### Storyline types

- **Episodic** — resolves in each episode. For procedural/hybrid: create ONE episodic storyline for the franchise engine (case-of-week). Story DNA is templated (repeating goal/obstacle/stakes), specific content — in Pass 2.
- **Serialized** — spans multiple episodes or the entire season.
- **Runner** — no obstacle or resolution, logline is descriptive. Everything else — a full storyline.

### A/B/C hierarchy

Assign each storyline a rank — its typical role across the season:

- **A** — protagonist's storyline or franchise engine, most screen time, plot-led conflict
- **B** — second in importance, often character-led, carries the episode's theme
- **C** — third, lighter in tone, less screen time
- **runner** — incomplete Story DNA, no obstacle/resolution

For serial/ensemble, rank may shift episode to episode (a storyline is A in one, B in another). Here, indicate the typical rank across the season. Pass 2 may override per episode.

In procedural/hybrid: the episodic storyline (franchise engine) = always A.

### By conflict nature

- **Plot-led** — external goal vs antagonist.
- **Character-led** — internal conflict, protagonist = their own antagonist.

### Seed and wraparound — not storyline types

Seed — an event function in Pass 2. Wraparound — a meta-device in Pass 2. Do not create storylines of these types.

### Granularity

The key is GOAL, not character. One character can drive multiple storylines with different goals.

One storyline: one driver + one goal + causal connection.
Different storylines: different drivers, OR one driver with different goals, OR no causal connection.

Test: if you can't write a logline (hero + goal + obstacle) — it's not a storyline.

### What is NOT a storyline

| example | what it is |
|---------|-----------|
| "John has lunch" | Background — no goal/conflict |
| "Everyone goes to a party" | Setting — no driver/stakes |
| "John is sad" | State — no goal/obstacle |
| "John and Mike's friendship" | Context — no conflict |
| "Investigation" (procedural, ep.5) | Franchise engine — part of the episodic storyline |

When in doubt — do NOT create a storyline.

### Incomplete synopses

Story DNA is reconstructed from the aggregate of mentions across the season. Don't invent — mark confidence.

### Naming

Name = abstract word by GOAL, not by event. Ensemble: always `Driver: Theme` (e.g. "Jon: Honor", "Cersei: Power"). Others: add driver when one character drives multiple storylines.

### Series format and resolution

- **ongoing**: storylines may extend beyond the season, cliffhanger in the finale is acceptable.
- **limited**: all storylines must receive resolution within the season.
- **anthology**: each season is independent, don't reference other seasons.

### Quantity expectations

- Procedural: 2–3 storylines per episode (1 episodic + 1–2 serialized).
- Serial: 3–8 serialized storylines per season.
- Ensemble: 4–6 parallel storylines.

## Output format

Response — strictly JSON, no markdown wrapping, no comments outside JSON.

```json
{
  "show": "Breaking Bad",
  "season": 1,
  "cast": [
    {"id": "walt", "name": "Walter White", "aliases": ["Walt", "Heisenberg", "Mr. White"]},
    {"id": "jesse", "name": "Jesse Pinkman", "aliases": ["Jesse", "Cap'n Cook"]},
    {"id": "hank", "name": "Hank Schrader", "aliases": ["Hank"]},
    {"id": "skyler", "name": "Skyler White", "aliases": ["Skyler"]},
    {"id": "tuco", "name": "Tuco Salamanca", "aliases": ["Tuco"]}
  ],
  "storylines": [
    {
      "id": "empire",
      "name": "Empire",
      "driver": "walt",
      "goal": "build a drug business",
      "obstacle": "moral choices, escalating danger, unpredictable partners",
      "stakes": "death, loss of humanity",
      "rank": "A",
      "type": "serialized",
      "nature": "plot-led",
      "confidence": "solid"
    },
    {
      "id": "family",
      "name": "Family",
      "driver": "walt",
      "goal": "keep the family together and hide the truth",
      "obstacle": "cancer, family pressure for treatment, escalating lies",
      "stakes": "family breakdown, exposure",
      "rank": "B",
      "type": "serialized",
      "nature": "character-led",
      "confidence": "solid"
    },
    {
      "id": "investigation",
      "name": "Investigation",
      "driver": "hank",
      "goal": "find the new meth producer",
      "obstacle": "no direct evidence, only circumstantial traces",
      "stakes": "criminal at large, public threat",
      "rank": "C",
      "type": "serialized",
      "nature": "plot-led",
      "confidence": "solid"
    },
    {
      "id": "partnership",
      "name": "Partnership",
      "driver": "jesse",
      "goal": "survive as Walt's drug business partner",
      "obstacle": "incompetence, fear, conflict with Walt",
      "stakes": "prison or death",
      "rank": "B",
      "type": "serialized",
      "nature": "character-led",
      "confidence": "solid"
    }
  ]
}
```

### Field types

**cast[].**:
- `id`: string — unique snake_case identifier, used in `driver` and in Pass 2 `characters`
- `name`: string — full name as in credits
- `aliases`: array of strings — name variants found in synopses

**storylines[].**:
- `id`: string — unique snake_case identifier (stable, doesn't change on rename)
- `name`: string — display name (see naming convention)
- `driver`: string — `id` of a character from cast
- `goal`: string
- `obstacle`: string
- `stakes`: string
- `type`: enum — `"episodic"` | `"serialized"` | `"runner"`
- `rank`: enum — `"A"` | `"B"` | `"C"` | `"runner"` — typical role across the season
- `nature`: enum — `"plot-led"` | `"character-led"`
- `confidence`: enum — `"solid"` | `"partial"` | `"inferred"`

Language of `goal`, `obstacle`, `stakes` fields — in the language of the synopsis.

The `span` field (which episodes the storyline appears in) is computed by code from Pass 2 results — not included in Pass 1.

## Validation

Validation is performed by code, not LLM. Code checks:
- JSON schema: all required fields, enum values
- Each `driver` references an existing `id` in `cast`
- For procedural/hybrid: exactly one storyline with `type: "episodic"`
- Number of storylines within acceptable range for franchise type

If code detects an error — re-request from LLM with specific indication of what's wrong.
