# Changelog

## Unreleased

### Added
- **Pass 4: arc functions** (`plot_fn`) — each event gets a season-arc role alongside its episode function. Pass 4 runs per-plotline, sees episode functions as context.
- **Reviewed rank**: Pass 3 assigns its own ranks. When they differ from `computed_rank`, stored as `reviewed_rank` — user sees both.
- **Fandom wiki** as second synopsis source — 15-20× more detailed than Wikipedia. Fetched automatically alongside Wikipedia.
- **DuckDuckGo fallback** — searches web for episodes with sparse Wikipedia + Fandom descriptions. Works for any language.
- **Suggested plotlines** from synopsis writer passed to Pass 0 and Pass 1 as context.
- **Russian prompts** (`prompts_ru/`) — all passes + glossary translated.
- **Rank refactor**: rank split into `computed_rank` (code, from event counts) and `reviewed_rank` (Pass 3, when it disagrees). LLM no longer assigns rank in Pass 1.
- **Theme-led plotlines**: glossary, logline test, naming rules for institutional/systemic plotlines (e.g. "MI5 vs Slough House", "Sterling Cooper: Business")
- **Shared glossary**: all prompt definitions in one file (`glossary.md`), injected into all passes via `{GLOSSARY}`
- **CLI**: `--stop-after pass1` saves intermediate JSON, `--resume-from` resumes from it
- **CLI**: `--output-dir` saves timestamped copy of results
- **CLI**: `--no-glossary`, `--no-fandom`, `--fandom-wiki` flags for write-synopses
- **Environment variables**: `TVPLOTLINES_OUTPUT_DIR`, `TVPLOTLINES_SYNOPSES_DIR` — default output locations
- **Rules and formulas reference**: `docs/formulas.md`
- Chain-of-thought nudge in all prompts before OUTPUT section

### Changed
- **5-pass pipeline**: Pass 4 (arc functions) added after Pass 3
- **Synopses writer auto-mode**: parallel for procedural/hybrid (preserves B-stories), single for serial/ensemble (season context)
- **Synopses writer**: Wikipedia + Fandom + DuckDuckGo, self-check for plotline balance
- **Rank formula**: equal weight for primary and also_affects events. Span requirements: A ≥ 75%, B ≥ 50%, C ≥ 25%.
- **Quantity limits** scale with season length: serial ≤8 eps max 5, 9+ max 7; ensemble ≤8 max 7, 9+ max 9
- **Ensemble is now a format** (`format: "ensemble"`), not a boolean flag. Ensemble = always serial.
- **Pass 2 functions are episode-scoped**: clarified as role within the episode, not the season arc
- **Pass 2**: plotline distribution check — warns if all events in one plotline
- Wikipedia `write-synopses`: Search API instead of URL guessing
- `max_tokens` scales by episode count (synopses) and event count (Pass 4)

### Removed
- **`limited` format** — not useful for analysis
- **Patches** (ADD_LINE, CHECK_LINE, SPLIT_LINE) — dead feature
- **PROMOTE/DEMOTE verdicts** — replaced by reviewed_rank

### Fixed
- Verdicts with invalid plotline IDs skipped instead of applied
- DROP aborts if events remain unredistributed
- CLI callback inherits PipelineCallback
- Arc function parsing: warn on mismatched event text instead of crash
- Pass 4 plotline ID normalization (name → id mapping)
- Single mode chunking for seasons >13 episodes
- Timeout scaling for large plotlines in Pass 4

## 0.1.0 — 2026-03-25

Initial open-source release.

- 4-pass LLM pipeline: context detection, plotline extraction, event assignment, structural review
- Story DNA extraction: hero, goal, obstacle, stakes for each plotline
- A/B/C ranking and format classification (procedural, serial, hybrid, ensemble), genre, is_ensemble, is_anthology
- Per-episode theme extraction
- Multi-season continuity via `prior` parameter
- Providers: Anthropic (default), OpenAI, Ollama, DeepSeek, Groq, any OpenAI-compatible API
- Pass 2 modes: parallel, batch (50% cheaper), sequential
- CLI: `tvplotlines run`
