# Rules and Formulas

Every rule, formula, and threshold in tvplotlines — whether executed by the LLM or by code. Ordered by pipeline stage. Each entry is marked:

- **LLM** — the LLM follows this rule based on the prompt
- **Code** — deterministic computation, no LLM involved

Code paths are relative to `src/tvplotlines/`.

---

## Pass 0: Format Detection

**LLM** classifies the show based on the first 3 synopses.

### Format classification

| Format | Diagnostic |
|--------|-----------|
| procedural | Each episode has a standalone case that opens and closes within the episode |
| hybrid | Each episode has case-of-the-week AND serialized arcs, and they intertwine |
| serial | Episodes continue each other; conflicts don't close within an episode |
| limited | Same as serial, but the story is designed to end this season |

Quick test: if E01 and E02 have different cases → procedural or hybrid. If E02 continues E01's conflict without closing it → serial.

### Ensemble and anthology flags

- **is_ensemble:** if you can't name THE main character → ensemble. Independent of format.
- **is_anthology:** seasons/episodes independent, new cast, no continuity. Independent of format.
- Both flags can combine with any format (e.g. limited + anthology = True Detective S1).

### Story engine templates

| Format | Template |
|--------|----------|
| procedural | "Every week [profession] [verb] [challenge type], testing [hero's quality]" |
| hybrid | "Every week [profession] [verb] [case] while [ongoing character plotline]" |
| serial | "[Hero] [transformation], testing how far they'll go for [goal]" |
| limited | "[Characters] [verb] [one problem] over one season" |

### Constraints

- Classify from the synopses, not from prior knowledge of the show. The same show can change format between seasons.
- Don't default to serial just because character arcs are present. Hybrid means both case-of-the-week and serialized arcs are significant.

---

## Pass 1: Plotline Extraction

**LLM** extracts cast and plotlines. **Code** validates and votes.

### Story DNA

Every plotline has four parts: **hero** (who drives it), **goal** (what they want), **obstacle** (what blocks them), **stakes** (what happens if they fail). Missing any component → not a plotline, just an event within another.

For theme-led plotlines (problem comes from an institution or system), there may be no obvious single hero. Assign the most fitting character — the one most affected, driving the dynamic, or whose POV dominates.

### Granularity

The key is GOAL, not character. One character can drive multiple plotlines with different goals. One plotline = one hero + one goal + causal connection between events.

**Logline test:** "[hero] wants [goal], but [obstacle], and if they fail [stakes]." For theme-led: "[institution/system] creates [problem], [hero] is caught in it, stakes: [stakes]."

Can't write the logline → not a plotline.

### What is not a plotline

| Example | Why not |
|---------|---------|
| "John has lunch" | Background — no goal/conflict |
| "Everyone goes to a party" | Setting — no hero/stakes |
| "John is sad" | State — no goal/obstacle |
| "John and Mike's friendship" | Context — no conflict |
| "Investigation" (procedural, ep. 5) | Part of case_of_the_week, not separate |

### Plotline types

| Type | Duration | Story DNA |
|------|----------|-----------|
| case_of_the_week | Opens and closes within one episode | Templated (repeating goal/obstacle/stakes) |
| serialized | Spans multiple episodes or the season | Full |
| runner | Minor recurring thread, 3+ episodes | Incomplete — no obstacle or resolution |

### Rank

How central the plotline is to what the show is about. Resonance, not event count.

| Rank | Meaning |
|------|---------|
| A | The plotline the series is about |
| B | Second in importance, often character-led |
| C | Third, lighter in tone |
| null | Runner only |

**Assignment by format:**
- Procedural: case_of_the_week = A
- Hybrid: character plotline = A, case = B (case may have more events, but character story matters more)
- Serial/ensemble: rank may shift episode to episode; report typical rank across the season

### Nature

Where the problem comes from:

| Nature | Source of problem | Examples |
|--------|------------------|----------|
| plot-led | Outside the hero — external goal vs antagonist | Stranger Things, CSI |
| character-led | Inside the hero — hero IS the problem | Breaking Bad, Fleabag |
| theme-led | From society — systemic, no single solution | The Wire, Succession |

Nature of a plotline and nature of individual events can differ — plot-led action serving a character-led plotline is normal.

### Confidence

| Level | Meaning |
|-------|---------|
| solid | Hero, goal, obstacle, stakes all clear |
| partial | Hero and goal clear, obstacle or stakes unclear |
| inferred | Plotline implied, structure incomplete |

Inferred plotlines won't be flagged for missing functions or low event count. Solid plotlines will.

### Naming rules

- ID = one abstract word by GOAL: "belonging", "leadership", "love". No compounds ("gang_survival" → "survival").
- Name format: `Hero: Theme` (e.g. "House: Authority", "Walt: Empire").
- Case_of_the_week: name by franchise formula ("Case of the Week", "Crime of the Week", "Mission").
- Theme-led: name by the dynamic ("MI5 vs Slough House", "Lab Politics", "Professional Life at Sterling Cooper").
- Goal language matches synopsis language.

### Quantity expectations

| Format | Composition | Max total |
|--------|------------|-----------|
| Procedural | 1 case_of_the_week + 1–3 serialized | 5 |
| Hybrid | 1 case_of_the_week + 2–4 serialized | 5 |
| Serial | 1 A, 1–2 B, 1–2 C. Runners must span 3+ episodes | 5 |
| Ensemble | 2–4 A, 1–2 B | 5–6 |

When in doubt — do NOT create a plotline.

### Prior season continuity

For each prior plotline, decide based on new synopses:

| Decision | Action |
|----------|--------|
| CONTINUES | Keep `id`, update goal/obstacle/stakes |
| TRANSFORMED | Keep `id`, rewrite Story DNA |
| ENDED | Don't include |

Reuse character `id` and `name` if the character appears. Process all prior plotlines before identifying new ones.

### Other constraints

- Do not create plotlines of type seed or wraparound — those are event functions, not plotlines.
- Serial: plotlines may extend beyond the season; cliffhanger is acceptable.
- Limited: all plotlines must resolve within the season.
- Anthology: each season is independent; don't reference other seasons.
- Procedural/hybrid: exactly 1 case_of_the_week plotline.
- Don't invent missing Story DNA — mark confidence as partial or inferred.

### Code: majority voting

`pass1.py:extract_plotlines`

Pass 1 runs three times with identical input. Code keeps the result whose plotline ID set the majority agrees on. When all three disagree, the first result wins.

**Why:** a single LLM run may miss or hallucinate a plotline. Three runs with voting reduce variance.

`_VOTING_ROUNDS = 3`

### Code: rank count warnings

`pipeline.py:_warn_rank_limits`

Logs a warning (no auto-fix) when counts exceed:

| Format | Max A | Max B | Max C | Max total |
|--------|-------|-------|-------|-----------|
| Non-ensemble | 1 | 2 | 2 | 5 |
| Ensemble | 4 | 2 | 2 | 6 |

### Code: validation

`pass1.py:_validate`

Rejects LLM output that violates structural rules (LLM retries automatically):

- Cast and plotlines non-empty
- `type` ∈ {case_of_the_week, serialized, runner}
- Runner → rank null; others → rank ∈ {A, B, C}
- `nature` ∈ {plot-led, character-led, theme-led}
- `confidence` ∈ {solid, partial, inferred}
- Procedural/hybrid: exactly 1 case_of_the_week
- Non-ensemble: exactly 1 A-rank. Ensemble: 2+ A-rank

---

## Pass 2: Event Assignment

**LLM** breaks each episode into events and assigns them to plotlines. **Code** validates.

### Event definition

One action by one character (or group) that changes the situation. Two actions by different characters = two events. Two actions at the same moment where the second is an immediate consequence of the first = one event.

Event descriptions must be specific: include character names, what happens, dramatic consequence. Not "The team works on the case" but "House orders a lumbar puncture over Cameron's objection, risking paralysis to test his sarcoidosis theory."

### Event functions

| Function | Meaning | Repeats? |
|----------|---------|----------|
| setup | Introduces the plotline, status quo | No |
| inciting_incident | The event that starts the plotline | No — one per plotline |
| escalation | Raises the stakes | Yes |
| turning_point | Changes direction; false peak or collapse | Yes |
| crisis | Lowest point; hero faces what they feared | No |
| climax | Peak of conflict; outcome irreversible | No |
| resolution | Conflict resolved; aftermath | No |

Functions are checked downstream for arc completeness and monotonicity.

### Assignment rules

1. **By hero:** event → plotline of the character whose goal it advances
2. **Guests → cast:** guest in a scene → plotline belongs to the cast member
3. **By goal, not character:** multiple characters → whose GOAL does this scene advance?
4. **Double bump:** event touches two plotlines → assign to primary goal, note secondary in `also_affects`
5. **Frequency hint:** B-story = 1–2 scenes per act. More events than the A → re-check hierarchy
6. **Emotional counterpoint:** if all plotlines are rising or all falling → something is missed
7. **Complete coverage:** every synopsis sentence must map to at least one event
8. **Limited, final episode:** expect resolution/climax, not setup/escalation

### Interactions between plotlines

| Type | Meaning |
|------|---------|
| thematic_rhyme | Plotlines explore the same theme from different angles |
| dramatic_irony | Audience knows what a character in another plotline doesn't |
| convergence | Plotlines merge — characters or conflicts intersect |

### Patches

Hints from episode breakdowns that something in Pass 1 may need fixing:

| Patch | When |
|-------|------|
| ADD_LINE | Event doesn't attach to any plotline (plotline_id: null) |
| CHECK_LINE | Plotline has no events in this episode |
| SPLIT_LINE | Plotline covers disparate things |
| RERANK | C-plotline is heavier than A in this episode |

### Code: validation

`pass2.py:_validate`

- `function` ∈ {setup, inciting_incident, escalation, turning_point, crisis, climax, resolution}
- `plotline_id` references existing plotline or is null
- Characters are cast IDs or `guest:*`
- Every `also_affects` ID exists in plotlines
- `interaction.type` ∈ {thematic_rhyme, dramatic_irony, convergence}
- `patch.action` ∈ {ADD_LINE, CHECK_LINE, SPLIT_LINE, RERANK}

---

## Post-processing (between Pass 2 and Pass 3)

All steps are **Code** — deterministic, no LLM.

### Orphan event assignment

`postprocess.py:assign_orphan_events`

Events with `plotline_id = null` get resolved by character voting:

1. For each character across the season, count which plotline they appear in most
2. For each orphan, aggregate votes from its characters
3. Assign to the plotline with most votes
4. **Fallback:** if no character data, use most common plotline in the same episode
5. Events with empty character list stay null

**Why:** orphan events are rare but create gaps in span and weight calculations.

### Span

`postprocess.py:compute_span`

A plotline's span = list of episodes where it has ≥1 event. Recomputed after Pass 3 verdicts.

**Why:** span drives the A-rank demotion rule and helps Pass 3 judge whether a plotline is real.

### Weight per episode

`postprocess.py:compute_weight`

Each plotline gets a weight label per episode:

| Weight | Rule |
|--------|------|
| primary | event count ≥ 50% of max in this episode |
| background | event count ≥ 2, but < 50% of max |
| glimpse | event count = 1 |

`threshold = 0.5`

**Why:** Pass 3 needs a quick read of plotline presence without counting raw events.

### Diagnostic flags

`postprocess.py:validate_ranks`

**A-rank span check:** A-rank plotline in fewer than 25% of episodes → auto-demote to B.
`min_span_frac = 0.25`

**Dominance check:** plotline with > 50% of all season events → flag `dominant` (no auto-fix).
`dominance_threshold = 0.50`

---

## Pass 3: Structural Review

**LLM** reviews the full season structure and issues verdicts. **Code** applies them.

### What Pass 3 checks

**Story DNA:** does every solid plotline have a logline with hero → goal → obstacle → stakes?

**Event assignment spot-check:** does each event advance the plotline it's assigned to? Common errors:
- Event assigned to hero's A-plotline but advances B-plotline (wrong goal)
- Event describes reaction to another plotline's conflict (should be `also_affects`)
- Multiple events in a row with same plotline but describing different conflicts

**Arc progression:** healthy arc goes setup → inciting_incident → escalation → turning_point → crisis → climax → resolution. Problems:
- Only setup → stillborn plotline
- Only escalation → plotline is stuck
- No climax/resolution in final episode (limited format) → unclosed plotline
- Function goes backwards past a milestone (crisis after climax) → monotonicity violation

**Duplication detection:** two plotlines with same hero and adjacent goals → likely one plotline with phases. Signs: goals causally linked, events alternate in same episodes, no conflict between the two plotlines.

**Rank vs data:** rank=C but weight=primary in most episodes → PROMOTE. Rank=A but weight=glimpse in half the season → DEMOTE. Two A-rank plotlines with equal weight in non-ensemble → DEMOTE one.

**Orphaned events:** plotline_id null after post-processing. If they belong to an existing plotline → REASSIGN. If they form a pattern → CREATE new plotline.

### Verdict constraints

- If everything is fine → empty verdicts array. Don't invent problems.
- Each verdict justified by theory (Story DNA, format, arc) or data (weight, span, diagnostics).
- REASSIGN references exact event text — do not rephrase.
- MERGE moves all events automatically — no need to list each one.
- DROP must specify where ALL events go. Code rejects DROP if events remain unredistributed.
- CREATE requires complete Story DNA and a list of events to reassign to it.
- Don't flag inferred plotlines for missing functions — incomplete structure is expected.
- DROP only phantoms (plotlines with no events), not weak plotlines in bad scripts.
- Never PROMOTE to A if A-rank already exists in non-ensemble format.

### Code: verdict application

`verdicts.py:apply_verdicts`

| Action | Effect |
|--------|--------|
| MERGE | Moves all events from source to target; removes source |
| REASSIGN | Moves one event (exact text match) to different plotline |
| PROMOTE | Raises rank. Blocked when non-ensemble and A exists |
| DEMOTE | Lowers rank |
| CREATE | Adds plotline with `confidence: "inferred"`; reassigns specified events |
| DROP | Redistributes events; removes plotline only when zero events remain |
| REFUNCTION | Changes an event's function |

### Code: post-verdict recomputation

Span and rank validation run again after verdicts — the plotline list may have changed.

---

## Pipeline orchestration

All **Code**.

### Pass skip logic

`pipeline.py:get_plotlines`

| Parameter provided | Effect |
|-------------------|--------|
| `context` | Skip Pass 0 |
| `cast` + `plotlines` | Skip Pass 1 |
| `breakdowns` | Skip Pass 2 |
| `skip_review=True` | Skip Pass 3 |
| `prior` | Reuse prior.context (unless explicit context given); pass prior cast/plotlines to Pass 1 |

`prior` raises ValueError for anthology format.

### Episode ID validation

- Must match `S{dd}E{dd}` (regex `^S\d{2}E\d{2}$`)
- Season prefix must match `season` parameter
- Sorted alphabetically before processing

### Pass 2 execution modes

| Mode | Mechanism | Cost | Speed |
|------|-----------|------|-------|
| parallel | Async, all episodes at once | Full | Fast |
| batch | Anthropic batch API | 50% discount | Slow |
| sequential | One episode at a time | Full | Slowest |

`batch_id` resumes a previously submitted batch (batch mode only).
