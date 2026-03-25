# tvplotlines

[![PyPI](https://img.shields.io/pypi/v/tvplotlines)](https://pypi.org/project/tvplotlines/)
[![License](https://img.shields.io/github/license/BirdInTheTree/tvplotlines)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/tvplotlines)](https://pypi.org/project/tvplotlines/)

LLM-powered narrative breakdown for TV series. Feed it episode synopses — get plotlines with Story DNA (hero, goal, obstacle, stakes), A/B/C ranking, and per-episode event tracking. Built for development executives and writers who need to analyze shows fast.

Works from synopses alone — no scripts or transcripts needed.
## Example output

Breaking Bad, Season 1 (truncated):

```json
{
  "context": {
    "franchise_type": "serial",
    "story_engine": "A high school teacher builds a drug empire, testing how far he'll go for family and control"
  },
  "plotlines": [
    {
      "name": "Walt: Empire",
      "hero": "walt",
      "goal": "build a profitable drug business to secure his family's financial future",
      "obstacle": "inexperience in criminal world, violent dealers, maintaining secrecy",
      "stakes": "death, imprisonment, family destruction",
      "rank": "A",
      "span": ["S01E01", "S01E02", "S01E03", "S01E04", "S01E05", "S01E06", "S01E07"]
    },
    {
      "name": "Jesse: Survival",
      "hero": "jesse",
      "goal": "survive as Walt's partner in the dangerous drug trade",
      "obstacle": "violent dealers like Tuco, lack of street credibility, Walt's reckless decisions",
      "stakes": "death, severe injury, imprisonment",
      "rank": "A",
      "span": ["S01E01", "S01E02", "S01E03", "S01E04", "S01E05", "S01E06", "S01E07"]
    }
  ],
  "episodes": [
    {
      "episode": "S01E01",
      "events": [
        {
          "event": "Hank shows off his gun at Walt's 50th birthday party and invites him on a DEA ride-along",
          "storyline": "investigation",
          "function": "setup",
          "characters": ["hank", "walt"]
        }
      ]
    }
  ]
}
```

## Installation

```bash
pip install tvplotlines
```

Requires an API key for at least one LLM provider:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...
```

Or put them in a `.env` file (requires `pip install tvplotlines[dotenv]`):

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Quick start

### CLI

```bash
tvplotlines run synopses/*.txt --show "Breaking Bad" --season 1 -o bb_s01.json
```

### Python

```python
from tvplotlines import get_plotlines

episodes = {
    "S01E01": "In the pilot, Walter White is diagnosed with cancer...",
    "S01E02": "Walt and Jesse attempt their first cook in the desert...",
    # ... all season synopses
}

result = get_plotlines("Breaking Bad", season=1, episodes=episodes)

for plotline in result.plotlines:
    print(f"[{plotline.rank}] {plotline.name} — {plotline.goal}")
    print(f"    Hero: {plotline.hero}, Span: {plotline.span}")

for ep in result.episodes:
    print(f"\n{ep.episode}: {ep.theme}")
    for event in ep.events:
        print(f"  [{event.function}] {event.event} -> {event.storyline}")
```

## Key concepts

- **Plotline** — a narrative thread running through one or more episodes (e.g. "Walt: Empire")
- **Story DNA** — the core conflict structure of a plotline: who drives it (*hero*), what they want (*goal*), what's in the way (*obstacle*), and what's at risk (*stakes*)
- **A/B/C ranking** — plotline weight within the season: A (main), B (secondary), C (tertiary), runner (minor recurring thread)
- **Franchise type** — structural classification of the show: procedural (House), serial (Breaking Bad), hybrid (X-Files), ensemble (Game of Thrones)
- **Story engine** — one-sentence description of the show's core dramatic mechanism

## How it works

The pipeline has four passes, each a separate LLM call with a specialized prompt:

| Pass       | Role                | Input                       | Output                                   |
| ---------- | ------------------- | --------------------------- | ---------------------------------------- |
| **Pass 0** | Context detection   | Show title + first synopses | Franchise type, story engine             |
| **Pass 1** | Plotline extraction | All synopses + context      | Cast + plotlines with Story DNA          |
| **Pass 2** | Event assignment    | One synopsis + plotlines    | Events assigned to plotlines             |
| **Pass 3** | Quality review      | Full result                 | Verdicts (merge, reassign, create, drop) |

Pass 2 runs in parallel for all episodes. Pass 3 reviews the full picture that no earlier pass could see and corrects the result (merge redundant plotlines, reassign misplaced events, etc.).

## LLM providers

tvplotlines works with Anthropic (default) and any OpenAI-compatible API:

```bash
tvplotlines run *.txt --show "House"                    # Anthropic (default)
tvplotlines run *.txt --show "House" --provider openai   # OpenAI
tvplotlines run *.txt --show "House" --provider ollama   # Ollama (local, free)
```

See [docs/api.md](docs/api.md) for full API reference, provider options, and pass modes.

## Citation

If you use tvplotlines in your research, please cite:

```bibtex
@software{tvplotlines2026,
  author = {Vashko, N.},
  title = {tvplotlines: Automated Narrative Breakdown for TV Series},
  year = {2026},
  url = {https://github.com/BirdInTheTree/tvplotlines}
}
```

## License

MIT
