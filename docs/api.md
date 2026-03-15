# API Reference

## get_plotlines()

Main entry point. Extracts storylines from a season of TV synopses.

```python
from plotter import get_plotlines

result = get_plotlines(
    show="House",
    season=1,
    episodes=synopses,
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

## PlotterResult

Returned by `get_plotlines()`.

| Field | Type | Description |
|-------|------|-------------|
| `context` | `SeriesContext` | Detected series context |
| `cast` | `list[CastMember]` | Main cast members |
| `plotlines` | `list[Plotline]` | Discovered storylines |
| `episodes` | `list[EpisodeBreakdown]` | Per-episode breakdowns |

## Data models

See source: `src/plotter/models.py`

*Full auto-generated reference coming soon.*
