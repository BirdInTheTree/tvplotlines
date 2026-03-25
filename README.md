# tvplotlines

[![PyPI](https://img.shields.io/pypi/v/tvplotlines)](https://pypi.org/project/tvplotlines/)
[![License](https://img.shields.io/github/license/BirdInTheTree/tvplotlines)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/tvplotlines)](https://pypi.org/project/tvplotlines/)

Extract plotlines from TV synopses using LLM.

One function call turns episode synopses into structured data: plotlines with cast, Story DNA (hero, goal, obstacle, stakes), A/B/C ranking, and per-episode events.

## Input

Write one .txt file per episode. Include S01E01 in the filename — any prefix is fine:

```
S01E01.txt
S01E02.txt
BB_S01E01.txt        ← also works
my_show_S01E03.txt     ← also works
```

Put all files in a folder named after the show:

```
breaking-bad/
    S01E01.txt
    S01E02.txt
    ...
    S01E07.txt
```

Install, set your API key, and run:

```bash
pip install tvplotlines
export ANTHROPIC_API_KEY=sk-ant-...

tvplotlines run breaking-bad/
```

## Output

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
- **Format** — procedural (House), serial (Breaking Bad), hybrid (X-Files), ensemble (Game of Thrones)
- **Story engine** — one sentence capturing the show's core dramatic mechanism

Full definitions are in the [prompts](src/tvplotlines/prompts_en/).

## Quick start

The repo includes synopses for Breaking Bad and Game of Thrones in [`examples/synopses/`](examples/synopses/) and pre-computed results in [`examples/results/`](examples/results/).

```bash
tvplotlines run examples/synopses/breaking-bad/
```

Or in Python:

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
tvplotlines run house/                                   # Anthropic (default)
tvplotlines run house/ --provider openai                 # OpenAI
tvplotlines run house/ --provider ollama                 # Ollama (local, free)
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
