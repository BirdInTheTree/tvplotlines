# Vanilla Prompt (Condition A)

Model: `claude-sonnet-4-20250514`, temperature=0, max_tokens=16384

```
Here are synopses for {show} Season {season} ({n_eps} episodes):

{all synopses, separated by ---}

Extract the main plotlines from this season. For each plotline, list name and main character.
Then assign each event from the synopses to its plotline, and for each event indicate its narrative function from this list: setup, inciting_incident, escalation, turning_point, crisis, climax, resolution.

Return as JSON inside a ```json code block:
{
  "plotlines": [{"id": "...", "name": "...", "hero": "..."}],
  "episodes": [{"episode": "S01E01", "events": [{"event": "...", "plotline": "...", "function": "..."}]}]
}
```

No Story DNA (goal/obstacle/stakes), no format detection, no cast list, no interactions, no patches, no rank, no type, no confidence. Single LLM call.
