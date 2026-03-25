# Quickstart

## Install

```bash
pip install tvplotlines
```

## Basic usage

```python
from tvplotlines import get_plotlines

result = get_plotlines(
    show="Breaking Bad",
    season=1,
    episodes={"S01E01": "Synopsis of S01E01...", "S01E02": "Synopsis of S01E02..."},
)

for plotline in result.plotlines:
    print(f"{plotline.rank} | {plotline.name} ({plotline.hero})")
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
