# tvplotlines

[![PyPI](https://img.shields.io/pypi/v/tvplotlines)](https://pypi.org/project/tvplotlines/)
[![License](https://img.shields.io/github/license/BirdInTheTree/tvplotlines)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/tvplotlines)](https://pypi.org/project/tvplotlines/)

Extract plotlines from TV synopses using LLM.

One function call turns episode synopses into structured data: plotlines with cast, Story DNA (hero, goal,  obstacle, stakes), A/B/C ranking, and per-episode events.

## Example output

Breaking Bad, Season 1 (truncated):

```json
{
  "context": {
    "format": "serial",
    "story_engine": "A high school teacher builds a drug empire, testing how far he'll go for family and survival"
  },
  "cast": [
    {"id": "walt", "name": "Walter White", "aliases": ["Walt", "Heisenberg", "Mr. White"]},
    {"id": "jesse", "name": "Jesse Pinkman", "aliases": ["Jesse"]}
  ],
  "plotlines": [
    {
      "id": "empire",
      "name": "Walt: Empire",
      "hero": "walt",
      "goal": "build a drug business to secure his family's financial future",
      "obstacle": "inexperience with criminal world, violent dealers like Tuco, moral boundaries",
      "stakes": "death, loss of family, imprisonment",
      "rank": "A",
      "span": ["S01E01", "S01E02", "...", "S01E07"]
    }
  ],
  "episodes": [
    {
      "episode": "S01E01",
      "events": [
        {
          "event": "During the meth lab raid, Walt spots his former student Jesse escaping through a window",
          "plotline_id": "empire",
          "function": "inciting_incident",
          "characters": ["walt", "jesse"]
        }
      ]
    }
  ]
}
```

## Key concepts

- **Plotline** — a narrative thread running through one or more episodes (e.g. "Walt: Empire")
- **Story DNA** — who drives the plotline (*hero*), what they want (*goal*), what's in the way (*obstacle*), and what's at risk (*stakes*)
- **A/B/C ranking** — plotline weight: A (main), B (secondary), C (tertiary), runner (minor recurring thread)
- **Format**— procedural (House), serial (Breaking Bad), hybrid (X-Files), ensemble (Game of Thrones)
- **Story engine** — one sentence capturing the show's core dramatic mechanism

Full definitions are in the [prompts](src/tvplotlines/prompts_en/).

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

## Quick start

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
```

Or from the command line:

```bash
tvplotlines run examples/synopses/BB_S01E*.txt --show "Breaking Bad" --season 1 -o bb.json
```

The repo includes pre-computed results in [`examples/results/`](examples/results/) and synopses for Breaking Bad S01 and Game of Thrones S01 in [`examples/synopses/`](examples/synopses/).

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
