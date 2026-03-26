# Quickstart

## Install

```bash
pip install tvplotlines
export ANTHROPIC_API_KEY=sk-ant-...  # or OPENAI_API_KEY
```

## Prepare synopses

Write one `.txt` file per episode. Include the episode code (`S01E01`) in the filename. Put all files in a folder named after the show:

```
breaking-bad/
├── S01E01.txt
├── S01E02.txt
└── ...
```

## CLI

```bash
tvplotlines run breaking-bad/
```

The show name is taken from the folder name. Override with `--show` if needed:

```bash
tvplotlines run got/ --show "Game of Thrones"
```

## Python

```python
from tvplotlines import load_synopses_dir, get_plotlines

show, season, episodes = load_synopses_dir("breaking-bad/")
result = get_plotlines(show, season, episodes)

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
