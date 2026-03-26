# tvplotlines

[![PyPI](https://img.shields.io/pypi/v/tvplotlines)](https://pypi.org/project/tvplotlines/)
[![License](https://img.shields.io/github/license/BirdInTheTree/tvplotlines)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/tvplotlines)](https://pypi.org/project/tvplotlines/)

a Python library to extract plotlines from a season of TV synopses using LLMs.


In our benchmarks, a naive LLM prompt extracts 12% usable narrative structure from a TV season. tvplotlines reaches 87% — by separating what the model looks for (narrative theory in prompts) from how the result is organized (code).

One function call takes a season of episode synopses and returns structured data: plotlines with cast, Story DNA (hero, goal, obstacle, stakes), A/B/C ranking, and per-episode events.

## Input

One `.txt` file per episode. Include the season and episode number in the filename as `S01E01`, `S01E02`, etc. — any prefix works. 

Each file is a plain-text synopsis of one episode — a few paragraphs covering the main events. See `examples/synopses/breaking-bad/` for  reference.

Put all files in one folder. The folder name becomes the show title (`breaking-bad` → "Breaking Bad"):
```
breaking-bad/
├── S01E01.txt
├── S01E02.txt
├── ...
└── S01E07.txt
```

Install, set your API key, and run:
```bash
pip install tvplotlines
export ANTHROPIC_API_KEY=sk-ant-…

tvplotlines run breaking-bad/
```

Use `--show` to set the title manually:

```bash
tvplotlines run got/ --show "Game of Thrones"
```
## Output

The result is a single JSON file per season. Breaking Bad, Season 1 (truncated):

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
      "theme": "transformation through desperation",
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

The output is structured JSON — plug it into your own tools, scripts, or visualizations.

## Key concepts

- **Plotline** — a narrative thread running through one or more episodes (e.g. "Walt: Empire")
- **Story DNA** — who drives the plotline (*hero*), what they want (*goal*), what's in the way (*obstacle*), and what's at risk (*stakes*)
- **A/B/C ranking** — plotline weight: A (main), B (secondary), C (tertiary), runner (minor recurring thread)
- **Format** — procedural (House), serial (Breaking Bad), hybrid (X-Files), ensemble (Game of Thrones)
- **Story engine** — one sentence capturing the show's core dramatic mechanism

More detail in the [prompts](src/tvplotlines/prompts_en/).

## How it works

Four passes, each a separate LLM call with a specialized prompt:

| Pass       | Role                | Input                       | Output                                   |
| ---------- | ------------------- | --------------------------- | ---------------------------------------- |
| **Pass 0** | Context detection   | Show title + first synopses | Format, story engine                     |
| **Pass 1** | Plotline extraction | All synopses + context      | Cast + plotlines with Story DNA          |
| **Pass 2** | Event assignment    | One synopsis + plotlines    | Events assigned to plotlines             |
| **Pass 3** | Quality review      | Full result                 | Verdicts (merge, reassign, create, drop) |

Pass 1 uses majority voting (3 calls). Pass 2 adds one call per episode. Total: 5 fixed calls + one per episode.

Pass 3 reviews the full picture that no earlier pass could see and corrects the result (merge redundant plotlines, reassign misplaced events, etc.).

Tested with Claude Sonnet (default). OpenAI and Ollama are supported but less tested.

## Quick start

```bash
pip install tvplotlines
export ANTHROPIC_API_KEY=sk-ant-...  # or OPENAI_API_KEY for any OpenAI-compatible provider
```

The repo includes example synopses for Breaking Bad and Game of Thrones:

```bash
git clone https://github.com/BirdInTheTree/tvplotlines.git
cd tvplotlines
tvplotlines run examples/synopses/breaking-bad/
```

Pre-computed results are in [`examples/results/`](examples/results/) if you want to explore the output without spending API credits.

### Python API

Seasons can be chained — pass the previous result as `prior` so the model tracks plotline continuity:

```python
from tvplotlines import get_plotlines

s01 = get_plotlines("Breaking Bad", season=1, episodes=season_1_synopses)
s02 = get_plotlines("Breaking Bad", season=2, episodes=season_2_synopses, prior=s01)
```

## LLM providers

Anthropic (default) and any OpenAI-compatible API:

```bash
tvplotlines run breaking-bad/                            # Anthropic (default)
tvplotlines run breaking-bad/ --provider openai          # OpenAI
tvplotlines run breaking-bad/ --provider ollama          # Ollama (local, free)
```

See [docs/api.md](docs/api.md) for full API reference, provider options, and pass modes.

## Citation

If you use tvplotlines in your research, please cite:

```bibtex
@software{tvplotlines2026,
  author = {Vashko, N.},
  title = {tvplotlines: LLM-Driven Plotline Extraction from Episode Synopses},
  year = {2026},
  url = {https://github.com/BirdInTheTree/tvplotlines}
}
```

## License

MIT
