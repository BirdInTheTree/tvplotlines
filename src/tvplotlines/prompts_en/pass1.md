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

## Prior season (if provided)

If `prior_season` is present in the input, it contains cast and storylines from the previous season.

**Process prior data BEFORE analyzing new synopses:**

For each storyline in `prior_season.plotlines`, decide based on the NEW season's synopses:
- **CONTINUES** — the storyline is present this season. Keep the same `id`, update goal/obstacle/stakes to reflect the new season's material.
- **TRANSFORMED** — same driver, but goal fundamentally changed. Keep the `id`, rewrite Story DNA.
- **ENDED** — the storyline resolved or disappeared. Don't include it.

For each character in `prior_season.cast`:
- If the character appears in this season's synopses — reuse the same `id` and `name`.
- If the character does not appear — don't include them.

Only after processing all prior storylines, identify NEW storylines not present before.

## Task
Read ALL season synopses. If `prior_season` data is provided, first process prior storylines (see Prior season section), then identify new storylines. Extract the list of storylines and the main cast.

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

| example                            | what it is                                        |
| ---------------------------------- | ------------------------------------------------- |
| "John has lunch"                   | Background — no goal/conflict                     |
| "Everyone goes to a party"         | Setting — no driver/stakes                        |
| "John is sad"                      | State — no goal/obstacle                          |
| "John and Mike's friendship"       | Context — no conflict                             |
| "Investigation" (procedural, ep.5) | Franchise engine — part of the episodic storyline |

When in doubt — do NOT create a storyline.

### Incomplete synopses

Story DNA is reconstructed from the aggregate of mentions across the season. Don't invent — mark confidence.

### Naming

Name and id = ONE abstract word by GOAL, not by event or outcome. Examples: "belonging", "leadership", "love", "redemption". Do NOT use compound names like "gang_survival" or "family_destruction" — use "survival" or "family". The `id` must be a single snake_case word matching the `name`.

Episodic storyline (franchise engine): name it by the franchise formula — "Case of the Week", "Crime of the Week", "Mission", etc. — so it is immediately clear this is a recurring structure.

Always use `Driver: Theme` format for storyline names (e.g. "House: Authority", "Cameron: Ethics", "Jon: Honor"). This makes it clear who drives each storyline and prevents confusion during event assignment.

### Narrative devices

While reading synopses, note if a storyline employs recurring narrative devices. List them in the `devices` field. Most storylines have none — leave the list empty.

| device | what it means |
|--------|--------------|
| `dramatic_irony` | audience knows something the characters in this storyline do not |
| `flashback` | events in this storyline are shown out of chronological order (past) |
| `flashforward` | events in this storyline are shown out of chronological order (future) |
| `callback` | this storyline pays off something established earlier |
| `twist` | this storyline contains a reveal that reframes the audience's understanding |
| `unreliable` | events in this storyline are distorted by narrator or point-of-view |

Only list devices that are **characteristic** of the storyline across the season, not one-off occurrences.

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
      "name": "Walt: Empire",
      "driver": "walt",
      "goal": "build a drug business",
      "obstacle": "moral choices, escalating danger, unpredictable partners",
      "stakes": "death, loss of humanity",
      "rank": "A",
      "type": "serialized",
      "nature": "plot-led",
      "confidence": "solid",
      "devices": ["dramatic_irony"]
    },
    {
      "id": "family",
      "name": "Walt: Family",
      "driver": "walt",
      "goal": "keep the family together and hide the truth",
      "obstacle": "cancer, family pressure for treatment, escalating lies",
      "stakes": "family breakdown, exposure",
      "rank": "B",
      "type": "serialized",
      "nature": "character-led",
      "confidence": "solid",
      "devices": ["dramatic_irony"]
    },
    {
      "id": "investigation",
      "name": "Hank: Investigation",
      "driver": "hank",
      "goal": "find the new meth producer",
      "obstacle": "no direct evidence, only circumstantial traces",
      "stakes": "criminal at large, public threat",
      "rank": "C",
      "type": "serialized",
      "nature": "plot-led",
      "confidence": "solid",
      "devices": ["dramatic_irony"]
    },
    {
      "id": "partnership",
      "name": "Jesse: Partnership",
      "driver": "jesse",
      "goal": "survive as Walt's drug business partner",
      "obstacle": "incompetence, fear, conflict with Walt",
      "stakes": "prison or death",
      "rank": "B",
      "type": "serialized",
      "nature": "character-led",
      "confidence": "solid",
      "devices": []
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
- `devices`: array of strings — narrative devices characteristic of this storyline: `"dramatic_irony"`, `"flashback"`, `"flashforward"`, `"callback"`, `"twist"`, `"unreliable"`. Empty if none.

Language of `goal`, `obstacle`, `stakes` fields — in the language of the synopsis.

The `span` field (which episodes the storyline appears in) is computed by code from Pass 2 results — not included in Pass 1.

## Validation

Validation is performed by code, not LLM. Code checks:
- JSON schema: all required fields, enum values
- Each `driver` references an existing `id` in `cast`
- For procedural/hybrid: exactly one storyline with `type: "episodic"`
- Number of storylines within acceptable range for franchise type

If code detects an error — re-request from LLM with specific indication of what's wrong.
