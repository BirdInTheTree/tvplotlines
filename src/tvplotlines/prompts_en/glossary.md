## story DNA

Every plotline has four parts: **hero** (who drives it), **goal** (what they want), **obstacle** (what blocks them), **stakes** (what happens if they fail). Missing any component—not a plotline, but an event within another plotline.

Some plotlines have no obvious single hero—typically theme-led ones (see plotline:nature), where the problem comes from an institution or system rather than a character. Examples: "MI5 vs Slough House" in Slow Horses, "Professional life at Sterling Cooper" in Mad Men. In such cases, use your judgment to assign the most fitting character as hero—the one most affected, or driving the dynamic, or whose POV dominates.

## plotline

A story with complete Story DNA. Has a three-act structure, conflict, and a causal chain of events. A plotline is tied to a main cast character or an institution, not a guest.

TV episodes typically feature two or more parallel plotlines, denoted by letters A, B, C: a main A plot that dominates screen time and secondary B plots that may offer thematic parallels or counterpoint.

### granularity

The key is GOAL, not character.
Different plotlines: different heroes, OR one hero with different goals and obstacles and stakes.

Test: if you can't write a logline—"[hero] wants [goal], but [obstacle], and if they fail [stakes]"—it's not a plotline.

For theme-led plotlines, the logline test becomes: "[institution/system] [problem]; [hero] [role in it], stakes: [stakes]." Example: "MI5 covers up its role in the kidnapping; Taverner drives the cover-up, stakes: exposure and careers."

### what is not a plotline

| example                            | what it is                                             |
| ---------------------------------- | ------------------------------------------------------ |
| "John has lunch"                   | Background—no goal/conflict                            |
| "Everyone goes to a party"         | Setting—no hero/stakes                                 |
| "John is sad"                      | State—no goal/obstacle                                 |
| "John and Mike's friendship"       | Context—no conflict                                    |
| "Investigation" (procedural, ep.5) | Part of the case_of_the_week plotline, not a separate one |

## plotline:type

How long does this plotline last?

- **case_of_the_week**—opens and closes within one episode. The show's story engine describes the repeating formula. Story DNA is templated (repeating goal/obstacle/stakes), specific content—filled in per episode.
- **serialized**—spans multiple episodes or the entire season. Conflicts carry over.
- **runner**—minor recurring thread. Incomplete Story DNA—no obstacle or resolution, logline is descriptive. Everything else—a full plotline.

## plotline:nature

Where does the main problem come from? This matters because nature tells you what kind of obstacle to look for: an outside enemy (plot-led), the hero's own flaw (character-led), or a system nobody can fix alone (theme-led).

- **plot-led**—from outside the hero. External goal vs antagonist. Stranger Things, CSI.
- **character-led**—from inside the hero. Internal conflict, the hero IS the problem. Breaking Bad, Fleabag.
- **theme-led**—from society. Systemic, no single solution. The Wire, Succession.

## plotline:confidence

How complete is the conflict structure?

- **solid**—hero, goal, obstacle, stakes all clear.
- **partial**—hero and goal clear, obstacle or stakes unclear.
- **inferred**—plotline implied, conflict structure incomplete.

This matters because inferred plotlines are expected to have incomplete structure—they won't be flagged for missing functions or low event count. Solid plotlines will be.

## format

- **procedural**—each episode has a standalone story (case, patient, mission) that opens and closes within the episode. Even though each episode's case is different, we treat them as one recurring plotline called "Case of the Week"—same structural slot, different content each time. Other plotlines are secondary. CSI, House, Law & Order.
- **hybrid**—each episode has a case-of-the-week AND serialized plotlines, and they actively intertwine. Both matter. X-Files, Buffy, Good Wife, Grey's Anatomy.
- **serial**—episodes continue each other. Conflicts don't close within an episode. No case-of-the-week. One clear protagonist. Breaking Bad, Sopranos.
- **ensemble**—like serial, but no single protagonist. Multiple characters drive their own plotlines with roughly equal screen time. Diagnostic: can you name THE main character? If not—ensemble. Game of Thrones, Succession, The Wire, The Crown.

Base classification on the synopses, not on prior knowledge of the show. The same show can change format between seasons.

Don't default to serial just because character plotlines are present—hybrid means BOTH case-of-the-week AND serialized arcs are significant.

Diagnostic:
- if E01 and E02 have different cases—procedural or hybrid
- if E02 continues E01's conflict without closing it—serial or ensemble
- serial vs ensemble: can you name THE main character? If not—ensemble

## is_anthology

Seasons are independent—new cast, new story, no continuity between seasons. Within a single season, an anthology show has normal structure (serial, procedural, etc.). This matters because prior season data is not passed forward. True Detective, Fargo.

## story_engine

The show's repeating dramatic mechanism in one sentence. Focus on the verbs—what are characters doing each week?

Write the story engine as a one-sentence logline. Two common structures:
- "[Who] [does what] in order to [goal], but [obstacle]."
- "When [situation], [who] must [do what], or else [stakes]."

Use whichever fits the show.

Examples from real shows (none follow the formulas exactly—that's fine, the formulas are a starting point):
- "A high school chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing and selling methamphetamine in order to secure his family's future." (Breaking Bad)
- "Nine noble families fight for control over the lands of Westeros, while an ancient enemy returns after being dormant for millennia." (Game of Thrones)
- "An antisocial maverick doctor does whatever it takes to solve puzzling cases that come his way." (House)

## genre

Free text—drama, thriller, comedy, sci-fi, etc.

## event

One action by one character (or group) that changes the situation. Two actions by different characters = two events. Two actions at the same moment where the second is an immediate consequence of the first = one event.

Write event descriptions that are specific and concrete. Include character names, what specifically happens, and the dramatic consequence. Bad: "The team works on the case." Good: "House orders a lumbar puncture over Cameron's objection, risking paralysis to test his sarcoidosis theory."

## function

Each event carries a function—its position in the dramatic structure:

| function | what it does |
|----------|-------------|
| `setup` | Introduces the plotline. Status quo. |
| `inciting_incident` | The event that starts the plotline. One per plotline, does not repeat. |
| `escalation` | Raises the stakes. Can repeat. |
| `turning_point` | Changes direction. False peak or false collapse. |
| `crisis` | Lowest point. Hero faces what they feared most. True dilemma. |
| `climax` | Peak of the conflict. Outcome is irreversible. |
| `resolution` | Conflict resolved. Aftermath. |

Functions are checked downstream for arc completeness and monotonicity—if a plotline has only setup and escalation across the whole season, that's a flag.

## interaction

How plotlines connect within an episode:

- **thematic_rhyme**—plotlines explore the same theme from different angles.
- **dramatic_irony**—the audience knows what a character in another plotline doesn't.
- **convergence**—plotlines merge (characters/conflicts intersect).

## verdict

A structural correction applied after reviewing the full season:

| action | what it does |
|--------|-------------|
| `MERGE` | Merge two plotlines into one |
| `REASSIGN` | Move an event to a different plotline |
| `CREATE` | Create a new plotline from orphaned events |
| `DROP` | Remove a plotline, redistribute its events |
| `REFUNCTION` | Change an event's function (e.g. escalation → crisis) |
