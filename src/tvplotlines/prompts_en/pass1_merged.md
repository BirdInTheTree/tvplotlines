# Prompt: Pass 1 Merged — Context Detection + Storyline Extraction

> **Self-contained document.** Combines Pass 0 (context detection) and Pass 1 (storyline extraction) into a single LLM call.

## Contract

- **Input**: show title, season number, all season synopses
- **Output**: JSON with franchise_type, story_engine, cast, and storylines

## Input

- **show**: show title
- **season**: season number
- **synopses**: all season synopses (text)

## Task

Read ALL season synopses. Complete two tasks in sequence:

### Task 1: Determine series context

Determine the franchise type and story engine from the synopses.

#### Franchise type

Determine the episode structure from the pattern of the synopses:

| type | indicator | example |
|------|-----------|---------|
| `procedural` | Each episode contains a self-contained story (case, patient, mission) that opens and closes within the episode | House, CSI, Law & Order |
| `serial` | Episodes continue each other, conflicts don't resolve within an episode | Breaking Bad, The Americans, The Wire |
| `hybrid` | Self-contained episode story (case-of-week) + serialized arcs across episodes | X-Files, Buffy, Castle |
| `ensemble` | Multiple equal-weight characters, each with their own arc, no single protagonist | Game of Thrones, This Is Us, The Crown |

#### Story engine

Choose the closest template for the determined franchise type and fill in the slots:

- **Procedural**: "Every week [profession] solves [type of challenge], testing [hero's quality]"
- **Serial**: "[Hero] [transformation], testing how far they'll go for [goal]"
- **Hybrid**: "Every week [challenge], against the backdrop of [serialized conflict]"
- **Ensemble**: "[Group] [shared situation], each experiencing [their aspect of the theme]"

### Task 2: Extract storylines and cast

Using the franchise type you just determined, extract the list of storylines and the main cast.

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
  "franchise_type": "serial",
  "story_engine": "A high school teacher builds a drug empire, testing how far he'll go for family and control",
  "genre": "drama",
  "format": "ongoing",
  "cast": [
    {"id": "walt", "name": "Walter White", "aliases": ["Walt", "Heisenberg", "Mr. White"]},
    {"id": "jesse", "name": "Jesse Pinkman", "aliases": ["Jesse", "Cap'n Cook"]}
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
    }
  ]
}
```

### Field types

- `franchise_type`: enum — `"procedural"` | `"serial"` | `"hybrid"` | `"ensemble"`
- `story_engine`: string — filled template (one sentence)
- `genre`: string — `"drama"`, `"thriller"`, `"comedy"`, etc.
- `format`: enum — `"ongoing"` | `"limited"` | `"anthology"` | null (if unclear)

**cast[].**:
- `id`: string — unique snake_case identifier
- `name`: string — full name as in credits
- `aliases`: array of strings — name variants found in synopses

**storylines[].**:
- `id`: string — unique snake_case identifier
- `name`: string — display name (see naming convention)
- `driver`: string — `id` of a character from cast
- `goal`: string
- `obstacle`: string
- `stakes`: string
- `type`: enum — `"episodic"` | `"serialized"` | `"runner"`
- `rank`: enum — `"A"` | `"B"` | `"C"` | `"runner"` — typical role across the season
- `nature`: enum — `"plot-led"` | `"character-led"`
- `confidence`: enum — `"solid"` | `"partial"` | `"inferred"`
- `devices`: array of strings — narrative devices. Empty if none.

Language of `goal`, `obstacle`, `stakes` fields — in the language of the synopsis.

## Validation

Validation is performed by code, not LLM. Code checks:
- JSON schema: all required fields, enum values
- `franchise_type` — one of four values
- `story_engine` — non-empty string
- Each `driver` references an existing `id` in `cast`
- For procedural/hybrid: exactly one storyline with `type: "episodic"`
- Number of storylines within acceptable range for franchise type

If code detects an error — re-request from LLM with specific indication of what's wrong.
