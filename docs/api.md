# API Reference

## get_plotlines()

Main entry point. Extracts plotlines from a season of TV synopses using LLM.

```python
from tvplotlines import get_plotlines

result = get_plotlines(
    show="House",
    season=1,
    episodes={                       # dict[str, str]: episode_id → synopsis
        "S01E01": "Dr. House takes on a kindergarten teacher...",
        "S01E02": "A teenage swimmer collapses...",
        # ...
    },
    prior=None,                  # TVPlotlinesResult from previous season
    llm_provider="anthropic",    # "anthropic" | "openai" | "ollama" | "deepseek" | "groq" | any OpenAI-compatible
    model=None,                  # specific model or provider default
    pass2_mode="batch",          #  "batch" | "parallel" | "sequential"
    batch_id=None,               # resume batch by ID
    context=None,                # SeriesContext or auto-detect
    cast=None,                   # provide both cast + plotlines to skip Pass 1
    plotlines=None,              # provide both cast + plotlines to skip Pass 1
    breakdowns=None,             # resume: skip Pass 2
    callback=None,               # PipelineCallback subclass
)
```

### Multi-season processing

Pass the result of the previous season to maintain character and plotline ID continuity:

```python
r1 = get_plotlines("Breaking Bad", 1, {"S01E01": "...", "S01E02": "...", ...})
r2 = get_plotlines("Breaking Bad", 2, {"S02E01": "...", "S02E02": "...", ...}, prior=r1)
r3 = get_plotlines("Breaking Bad", 3, {"S03E01": "...", "S03E02": "...", ...}, prior=r2)
```

When `prior` is provided:
- Pass 0 is skipped (reuses `prior.context`)
- Pass 1 receives prior cast and plotlines, reusing IDs for continuing characters and plotlines
- Not supported for anthology format (raises `ValueError`)

## TVPlotlinesResult

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
| `hero` | `str` | Character who drives the plotline |
| `goal` | `str` | What the driver wants |
| `obstacle` | `str` | What stands in the way |
| `stakes` | `str` | What happens if the driver fails |
| `rank` | `str` | A (main), B (secondary), C (tertiary), runner |
| `type` | `str` | case_of_the_week, serialized, runner |
| `span` | `list[str]` | Which episodes it appears in (computed from events) |

### Event

A single narrative beat within an episode:

| Field | Type | Description |
|-------|------|-------------|
| `event` | `str` | What happens |
| `plotline_id` | `str` | Which plotline it belongs to |
| `function` | `str` | setup, inciting_incident, escalation, turning_point, crisis, climax, resolution |
| `characters` | `list[str]` | Who is involved |
| `also_affects` | `list[str] \| None` | Secondary plotline connections |

## Pass 2 modes

| Mode | Speed | Cost | Use case |
|------|-------|------|----------|
| `parallel` | Fast | Full price | All episodes at once via async |
| `batch` | Slow | 50% off | Default — Anthropic batch API, cheaper for large seasons |
| `sequential` | Slow | Full price | One episode at a time — for debugging |

## LLM providers

tvplotlines works with Anthropic (default) and any OpenAI-compatible API.

```bash
# Anthropic (default)
export ANTHROPIC_API_KEY=sk-ant-...
tvplotlines run house/

# OpenAI
export OPENAI_API_KEY=sk-...
tvplotlines run house/ --provider openai

# Ollama (local, free)
ollama pull qwen2.5:14b
tvplotlines run house/ --provider ollama

# DeepSeek
export DEEPSEEK_API_KEY=sk-...
tvplotlines run house/ --provider deepseek

# Any OpenAI-compatible endpoint
tvplotlines run house/ --provider openai \
    --base-url https://api.together.xyz/v1 \
    --model meta-llama/Llama-3-70b
```

In Python:

```python
result = get_plotlines(
    show="House", season=1,
    episodes={"S01E01": "synopsis...", "S01E02": "synopsis..."},
    llm_provider="ollama",           # or "deepseek", "groq", etc.
    model="qwen2.5:14b",             # optional, provider has defaults
    base_url="http://localhost:11434/v1",  # optional for known providers
)
```

## Format

tvplotlines classifies shows into four structural formats that determine how plotlines are extracted:

- **Procedural** — self-contained episode stories (House, CSI)
- **Serial** — continuous arcs across episodes (Breaking Bad, The Wire)
- **Hybrid** — case-of-week + serialized arcs (X-Files, Buffy)
- **Ensemble** — multiple equal-weight character arcs (Game of Thrones, This Is Us)
