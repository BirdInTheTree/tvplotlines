# API Reference

## get_plotlines()

Main entry point. Extracts plotlines from a season of TV synopses.

```python
from plotter import get_plotlines

result = get_plotlines(
    show="House",
    season=1,
    episodes=synopses,
    prior=None,                  # PlotterResult from previous season
    llm_provider="anthropic",    # "anthropic" | "openai"
    model=None,                  # specific model or provider default
    pass2_mode="parallel",       # "parallel" | "batch" | "sequential"
    batch_id=None,               # resume batch by ID
    context=None,                # SeriesContext or auto-detect
    cast=None,                   # resume: skip Pass 1
    plotlines=None,              # resume: skip Pass 1
    breakdowns=None,             # resume: skip Pass 2
    callback=None,               # PipelineCallback subclass
)
```

### Multi-season processing

Pass the result of the previous season to maintain character and storyline ID continuity:

```python
r1 = get_plotlines("Breaking Bad", 1, episodes_s01)
r2 = get_plotlines("Breaking Bad", 2, episodes_s02, prior=r1)
r3 = get_plotlines("Breaking Bad", 3, episodes_s03, prior=r2)
```

When `prior` is provided:
- Pass 0 is skipped (reuses `prior.context`)
- Pass 1 receives prior cast and plotlines, reusing IDs for continuing characters and storylines
- Not supported for anthology format (raises `ValueError`)

## PlotterResult

Returned by `get_plotlines()`.

| Field | Type | Description |
|-------|------|-------------|
| `context` | `SeriesContext` | Detected series context |
| `cast` | `list[CastMember]` | Main cast members |
| `plotlines` | `list[Plotline]` | Discovered plotlines |
| `episodes` | `list[EpisodeBreakdown]` | Per-episode breakdowns |

## Data models

### Plotline

A narrative thread with Story DNA:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier |
| `name` | `str` | e.g. "Walt: Empire" |
| `driver` | `str` | Character who drives the plotline |
| `goal` | `str` | What the driver wants |
| `obstacle` | `str` | What stands in the way |
| `stakes` | `str` | What happens if the driver fails |
| `rank` | `str` | A (main), B (secondary), C (tertiary), runner |
| `type` | `str` | episodic, serialized, runner |
| `span` | `list[str]` | Which episodes it appears in (computed from events) |

### Event

A single narrative beat within an episode:

| Field | Type | Description |
|-------|------|-------------|
| `event` | `str` | What happens |
| `storyline` | `str` | Which plotline it belongs to |
| `function` | `str` | setup, escalation, turning_point, climax, resolution, cliffhanger, seed |
| `characters` | `list[str]` | Who is involved |
| `also_affects` | `str \| None` | Secondary plotline connection |

## Pass 2 modes

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

Plotter classifies shows into four structural types that determine how plotlines are extracted:

- **Procedural** — self-contained episode stories (House, CSI)
- **Serial** — continuous arcs across episodes (Breaking Bad, The Wire)
- **Hybrid** — case-of-week + serialized arcs (X-Files, Buffy)
- **Ensemble** — multiple equal-weight character arcs (Game of Thrones, This Is Us)
