# Quickstart

## Install

```bash
pip install plotter
```

## Basic usage

```python
from plotter import get_plotlines

result = get_plotlines(
    show="Breaking Bad",
    season=1,
    episodes=["Synopsis of S01E01...", "Synopsis of S01E02...", ...],
)

for storyline in result.plotlines:
    print(f"{storyline.rank} | {storyline.name} ({storyline.driver})")
```

## Configuration

```python
result = get_plotlines(
    show="Breaking Bad",
    season=1,
    episodes=synopses,
    llm_provider="openai",       # or "anthropic" (default)
    pass2_mode="batch",          # "parallel" | "batch" | "sequential"
)
```

See [API Reference](api.md) for all options.
