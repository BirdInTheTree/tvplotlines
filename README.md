# Plotter

Extract storylines from TV series synopses using LLM.

Given episode synopses for a season, Plotter identifies narrative threads (storylines), assigns events to them, and produces a structured breakdown of the season's narrative architecture.

## Installation

```bash
pip install plotter
```

Requires an API key for at least one LLM provider:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...
```

Or put them in a `.env` file (requires `pip install plotter[dotenv]`):

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Quick start

### CLI

```bash
plotter run synopses/*.txt --show "Breaking Bad" --season 1 -o bb_s01.json
```

### Python

```python
from plotter import get_plotlines

episodes = [
    "In the pilot, Walter White is diagnosed with cancer...",
    "Walt and Jesse attempt their first cook in the desert...",
    # ... all season synopses
]

result = get_plotlines("Breaking Bad", season=1, episodes=episodes)

for plotline in result.plotlines:
    print(f"[{plotline.rank}] {plotline.name} — {plotline.goal}")
    print(f"    Driver: {plotline.driver}, Span: {plotline.span}")

for ep in result.episodes:
    print(f"\n{ep.episode}: {ep.theme}")
    for event in ep.events:
        print(f"  [{event.function}] {event.event} -> {event.storyline}")
```

## How it works

The pipeline has four passes, each a separate LLM call with a specialized prompt:

| Pass | Role | Input | Output |
|------|------|-------|--------|
| **Pass 0** | Context detection | Show title + first synopses | Franchise type, story engine |
| **Pass 1** | Storyline extraction | All synopses + context | Cast + storylines with Story DNA |
| **Pass 2** | Event assignment | One synopsis + storylines | Events assigned to storylines |
| **Pass 3** | Narratologist review | Full result | Verdicts (merge, reassign, create, drop) |

Pass 2 runs in parallel for all episodes. Pass 3 is optional — it provides a "second opinion" on the full picture that no earlier pass could see.

## API

### `get_plotlines()`

```python
result = get_plotlines(
    show="Breaking Bad",
    season=1,
    episodes=["synopsis 1", "synopsis 2", ...],
    # Optional:
    context=None,          # Skip Pass 0, provide SeriesContext directly
    llm_provider="anthropic",  # "anthropic" or "openai"
    model=None,            # Provider default (claude-sonnet-4, gpt-4o)
    lang="en",             # Prompt language: "en" or "ru"
    skip_review=False,     # Skip Pass 3
    pass2_mode="parallel", # "parallel", "batch", or "sequential"
)
```

Returns a `PlotterResult`:

```python
result.context     # SeriesContext — franchise type, story engine, genre
result.cast        # list[CastMember] — id, name, aliases
result.plotlines   # list[Plotline] — id, name, driver, goal, rank, span, ...
result.episodes    # list[EpisodeBreakdown] — events, theme, interactions
result.to_dict()   # Serialize to plain dict for JSON export
```

### Key types

**Plotline** — a narrative thread with Story DNA:
- `driver` — character who drives the storyline
- `goal`, `obstacle`, `stakes` — the conflict
- `rank` — A (main), B (secondary), C (tertiary), runner
- `type` — episodic, serialized, runner
- `span` — which episodes it appears in (computed from events)

**Event** — a single narrative beat within an episode:
- `storyline` — which plotline it belongs to
- `function` — setup, escalation, turning_point, climax, resolution, cliffhanger, seed
- `characters` — who is involved
- `also_affects` — secondary storyline connections

### Pass 2 modes

| Mode | Speed | Cost | Use case |
|------|-------|------|----------|
| `parallel` | Fast | Full price | Default — all episodes at once via async |
| `batch` | Slow | 50% off | Anthropic batch API — cheaper for large seasons |
| `sequential` | Slow | Full price | One episode at a time — for debugging |

## LLM providers

Plotter works with Anthropic (default) and any OpenAI-compatible API.

```bash
# Anthropic (default)
export ANTHROPIC_API_KEY=sk-ant-...
plotter run *.txt --show "House"

# OpenAI
export OPENAI_API_KEY=sk-...
plotter run *.txt --show "House" --provider openai

# Ollama (local, free)
ollama pull qwen2.5:14b
plotter run *.txt --show "House" --provider ollama

# DeepSeek
export DEEPSEEK_API_KEY=sk-...
plotter run *.txt --show "House" --provider deepseek

# Any OpenAI-compatible endpoint
plotter run *.txt --show "House" --provider openai \
    --base-url https://api.together.xyz/v1 \
    --model meta-llama/Llama-3-70b
```

In Python:

```python
result = get_plotlines(
    show="House", season=1, episodes=episodes,
    llm_provider="ollama",           # or "deepseek", "groq", etc.
    model="qwen2.5:14b",             # optional, provider has defaults
    base_url="http://localhost:11434/v1",  # optional for known providers
)
```

## Franchise types

Plotter classifies shows into four structural types that determine how storylines are extracted:

- **Procedural** — self-contained episode stories (House, CSI)
- **Serial** — continuous arcs across episodes (Breaking Bad, The Wire)
- **Hybrid** — case-of-week + serialized arcs (X-Files, Buffy)
- **Ensemble** — multiple equal-weight character arcs (Game of Thrones, This Is Us)

## License

MIT
