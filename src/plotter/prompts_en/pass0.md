# Prompt: Pass 0 — Series Context Detection

> **Self-contained document.** Fed to the LLM as-is. The cheapest prompt in the pipeline — few input tokens, fast response.

## Contract

- **Input**: show title, season number, 2–3 first synopses (+ show description if available)
- **Output**: JSON with franchise_type, story_engine, genre, format → passed as input to Pass 1 and Pass 2

## Input

- **show**: show title
- **season**: season number
- **description**: show description / logline / premise (if available, otherwise empty string)
- **sample_synopses**: 2–3 first synopses of the season (text)

## Task

Determine two parameters: franchise type and story engine. These define how the pipeline will extract storylines.

### Step 1: Franchise type

Determine the episode structure from the pattern of the first synopses:

| type | indicator | example |
|------|-----------|---------|
| `procedural` | Each episode contains a self-contained story (case, patient, mission) that opens and closes within the episode | House, CSI, Law & Order |
| `serial` | Episodes continue each other, conflicts don't resolve within an episode | Breaking Bad, The Americans, The Wire |
| `hybrid` | Self-contained episode story (case-of-week) + serialized arcs across episodes | X-Files, Buffy, Castle |
| `ensemble` | Multiple equal-weight characters, each with their own arc, no single protagonist | Game of Thrones, This Is Us, The Crown |

If E01 and E02 have different "cases of the week" — procedural or hybrid. If E02 continues E01's conflict without closure — serial. If each episode has its own focal character — ensemble.

### Step 2: Story engine

Choose the closest template for the determined franchise type and fill in the slots:

**Procedural:**
> Every week [profession] solves [type of challenge], testing [hero's quality]

Examples: "Every week a diagnostician solves a medical mystery, testing the limits of ethics" (House). "Every week detectives solve a murder, testing how far the justice system will go" (Law & Order).

**Serial:**
> [Hero] [transformation], testing how far they'll go for [goal]

Examples: "A high school teacher builds a drug empire, testing how far he'll go for family and control" (Breaking Bad). "A pair of spies lead double lives, testing how far they'll go for ideology" (The Americans).

**Hybrid:**
> Every week [challenge], against the backdrop of [serialized conflict]

Examples: "Every week a new paranormal case, against the backdrop of a government conspiracy" (X-Files). "Every week demons and vampires, against the backdrop of growing up and relationships" (Buffy).

**Ensemble:**
> [Group] [shared situation], each experiencing [their aspect of the theme]

Examples: "A family across three generations, each experiencing their aspect of identity and loss" (This Is Us). "Noble houses fight for the throne, each experiencing their aspect of power and honor" (Game of Thrones).

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
  "reasoning": "Episodes continue each other: E01's conflict (first cook) flows into E02 (consequences), no self-contained stories within episodes"
}
```

### Field types

- `show`: string
- `season`: integer
- `franchise_type`: enum — `"procedural"` | `"serial"` | `"hybrid"` | `"ensemble"`
- `story_engine`: string — filled template (one sentence)
- `genre`: string — `"drama"`, `"thriller"`, `"comedy"`, `"sci-fi"`, etc.
- `format`: enum — `"ongoing"` | `"limited"` | `"anthology"` | null (if unclear)
- `reasoning`: string — brief justification for franchise_type choice (1–2 sentences)

## Validation

Validation is performed by code, not LLM:
- JSON schema: all required fields, enum values
- `franchise_type` — one of four values
- `story_engine` — non-empty string

After validation, the result is shown to the human for confirmation or editing.
