# Prompt: Pass 2 — Event Assignment to Storylines

> **Self-contained document.** Compiled from `storyline-extraction-reference.md`, but fed to the LLM as-is. When reference is updated — recompile.

## Contract

- **Input**: Pass 1 output (`show`, `season`, `cast`, `storylines`) + one episode synopsis
- **Output**: JSON with episode events assigned to storylines

## Input

- **show**, **season**, **franchise_type**, **story_engine**, **format** (from Pass 0, forwarded by code)
- **cast**: character list with `id` (from Pass 1)
- **storylines**: storyline list with `id`, `driver`, `goal` (from Pass 1)
- **synopsis**: one episode synopsis (text)

## Task

### Step 1: Break the synopsis into events

One event = one action by one character (or group) that changes the situation. Two actions by different characters = two events. Two actions at the same moment where the second is an immediate consequence of the first = one event. Make sure every sentence of the synopsis is reflected in at least one event.

Write event descriptions that are specific and concrete. Include character names, what specifically happens, and the emotional or dramatic consequence. Bad: "The team works on the case." Good: "House orders a lumbar puncture over Cameron's objection, risking paralysis to test his sarcoidosis theory." Specificity helps distinguish events across storylines.

### Step 2: Assign each event to a storyline

### Step 3: Identify interactions between storylines

## Assignment rules

1. **By driver**: event → storyline of the character whose goal it advances.
2. **Guests → main cast**: the storyline belongs to the cast, not guests.
3. **By goal, not character**: multiple characters in a scene → storyline of the one whose GOAL the scene advances.
4. **Double bump — pick one**: event touches two storylines → assign to the primary goal, note the secondary in `also_affects`.
5. **Frequency as hint**: B-story = 1–2 scenes per act. If a storyline has more events than the A → re-check the hierarchy.

## Event functions

| function | what it does |
|----------|-------------|
| `setup` | Introduces the storyline |
| `escalation` | Raises the stakes |
| `turning_point` | Changes direction |
| `climax` | Peak of the conflict |
| `resolution` | Conflict resolved |
| `cliffhanger` | Cut at the peak |
| `seed` | Seeds a future storyline |

For **limited** series in the final episode: expect `resolution` or `climax` for each storyline, not `seed` or `cliffhanger`.

## Interactions between storylines

After assigning events, identify connections:

- **Thematic rhyme** — storylines explore the same theme from different angles. Determine the episode theme from the climax/resolution of storylines.
- **Dramatic irony** — the audience knows what a character in another storyline doesn't.
- **Convergence** — storylines merge (characters/conflicts intersect).
- **Meta** — structural device on top of storylines (subtype: twist-reveal, wraparound, time_jump, etc.). Test: doesn't advance a character's goal, but reframes what the audience has seen. If a meta-device has complete Story DNA — it's a storyline, not a device.

**Emotional counterpoint**: if all storylines are rising or all falling — something is missed or functions are wrong.

## Output format

Response — strictly JSON, no markdown wrapping, no comments outside JSON.

Weight (`primary` / `background` / `glimpse`) is computed by code from event counts — do NOT include in JSON.

```json
{
  "show": "Breaking Bad",
  "season": 1,
  "episode": "S01E03",
  "events": [
    {
      "event": "Walt and Jesse clean up Emilio's remains",
      "storyline": "empire",
      "function": "escalation",
      "characters": ["walt", "jesse"],
      "also_affects": null
    },
    {
      "event": "Krazy-8 talks about his childhood, Walt about cancer",
      "storyline": "empire",
      "function": "escalation",
      "characters": ["walt"],
      "also_affects": ["family"]
    },
    {
      "event": "Walt makes a pros and cons list for killing",
      "storyline": "empire",
      "function": "turning_point",
      "characters": ["walt"],
      "also_affects": null
    },
    {
      "event": "Skyler organizes a family intervention",
      "storyline": "family",
      "function": "setup",
      "characters": ["skyler", "walt"],
      "also_affects": null
    },
    {
      "event": "Family votes for chemo, Walt wants to refuse",
      "storyline": "family",
      "function": "escalation",
      "characters": ["walt", "skyler"],
      "also_affects": null
    },
    {
      "event": "Hank finds the desert cooking site",
      "storyline": "investigation",
      "function": "escalation",
      "characters": ["hank"],
      "also_affects": null
    },
    {
      "event": "DEA finds Krazy-8's car with meth",
      "storyline": "investigation",
      "function": "escalation",
      "characters": ["hank"],
      "also_affects": null
    },
    {
      "event": "Native girl brings a mask",
      "storyline": "investigation",
      "function": "seed",
      "characters": ["guest:native_girl"],
      "also_affects": null
    },
    {
      "event": "Walt decides to release Krazy-8",
      "storyline": "empire",
      "function": "turning_point",
      "characters": ["walt"],
      "also_affects": null
    },
    {
      "event": "Walt notices the missing plate shard",
      "storyline": "empire",
      "function": "turning_point",
      "characters": ["walt"],
      "also_affects": null
    },
    {
      "event": "Walt strangles Krazy-8",
      "storyline": "empire",
      "function": "climax",
      "characters": ["walt"],
      "also_affects": null
    },
    {
      "event": "Walt decides to tell Skyler about the cancer",
      "storyline": "family",
      "function": "turning_point",
      "characters": ["walt"],
      "also_affects": null
    }
  ],
  "summary": {
    "theme": "the illusion of control",
    "interactions": [
      {
        "type": "thematic_rhyme",
        "lines": ["empire", "family", "investigation"],
        "description": "all three storylines are about control — over another's life, one's own death, the law"
      },
      {
        "type": "dramatic_irony",
        "lines": ["empire", "investigation"],
        "description": "the audience knows Walt = Heisenberg, Hank doesn't"
      }
    ],
    "patches": []
  }
}
```

### Field types

**events[].**:
- `event`: string — one sentence
- `storyline`: string | null — `id` of a storyline from Pass 1, or `null` if the event can't be assigned to any storyline (→ `ADD_LINE` patch)
- `function`: enum — `"setup"` | `"escalation"` | `"turning_point"` | `"climax"` | `"resolution"` | `"cliffhanger"` | `"seed"`
- `characters`: array of strings — `id` of characters from cast. For guest characters use the format `"guest:short_name"` (e.g. `"guest:native_girl"`)
- `also_affects`: array of strings | null — `id` of secondarily affected storylines

**summary.interactions[].**:
- `type`: enum — `"thematic_rhyme"` | `"dramatic_irony"` | `"convergence"` | `"meta"`
- `lines`: array of strings — storyline `id`s
- `description`: string
- `subtype`: string | null — only for `"meta"`: `"twist-reveal"`, `"wraparound"`, `"time_jump"`, etc.

**summary.patches[].**:
- `action`: enum — `"ADD_LINE"` | `"CHECK_LINE"` | `"SPLIT_LINE"` | `"RERANK"`
- `target`: string — storyline `id` (or proposed new `id`)
- `reason`: string
- `episodes`: array of strings

## Validation

Validation is performed by code, not LLM. Code checks:
- JSON schema: all required fields, enum values
- Each `storyline` references an existing `id` from Pass 1 or is `null`
- Each `characters` element references an existing `id` from cast or has the `guest:` prefix
- Balance: A-story > B > C by event count
- `theme` is not empty

If code detects an error — re-request from LLM with specific indication of what's wrong.

## Patches to Pass 1

Pass 2 does not re-run Pass 1. It collects patches — suggestions for changing the storyline list. Patches are applied by code after processing all episodes.

| problem | what to do in the episode | patch |
|---------|--------------------------|-------|
| Event doesn't attach | `storyline: null` | `ADD_LINE` |
| Storyline with no events | Nothing | `CHECK_LINE` |
| Storyline covers disparate things | Assign to current | `SPLIT_LINE` |
| C is heavier than A | Note it | `RERANK` |
