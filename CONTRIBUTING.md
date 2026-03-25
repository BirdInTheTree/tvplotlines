# Contributing

## Setup

```bash
git clone https://github.com/BirdInTheTree/tvplotlines.git
cd tvplotlines
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

Tests use mocked LLM responses — no API key needed.

## Code style

- Python 3.11+
- Type hints on public functions
- `verb_noun` naming: `extract_plotlines`, `detect_context`
- Prompts live in `src/tvplotlines/prompts_en/` as markdown files

## Pull requests

1. Fork the repo
2. Create a branch (`git checkout -b feature/your-feature`)
3. Make your changes and add tests
4. Run `pytest` to verify
5. Open a PR with a clear description of what and why
