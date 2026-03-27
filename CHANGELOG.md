# Changelog

## Unreleased

### Added
- **Rank refactor**: rank split into `computed_rank` (code, from event counts) and `reviewed_rank` (Pass 3, when it disagrees). LLM no longer assigns rank in Pass 1.
- **Theme-led plotlines**: glossary, logline test, naming rules for institutional/systemic plotlines (e.g. "MI5 vs Slough House", "Lab Politics")
- **Shared glossary**: all prompt definitions in one file (`glossary.md`), injected into all passes
- **CLI**: `--stop-after pass1` saves intermediate JSON, `--resume-from` resumes from it
- **CLI**: `--output-dir` saves timestamped copy of results
- **Rank experiment**: `scripts/rank_experiment.py` + `docs/experiments/counting-events-for-ABC-rank.md`
- **Rules and formulas reference**: `docs/formulas.md` — all computed values, thresholds, and rules in one place
- Chain-of-thought nudge in all prompts before OUTPUT section

### Changed
- **Ensemble is now a format** (`format: "ensemble"`), not a boolean flag (`is_ensemble`). Ensemble shows are always serial by nature.
- **Pass 2 functions are episode-scoped**: function assignment clarified as role within the episode, not the season arc
- **Pass 2 event assignment**: rules rewritten as prose instead of jargon shorthand
- Wikipedia `write-synopses`: uses Search API instead of URL guessing — works for shows without dedicated season pages
- Plotline quantity limits: ensemble max raised to 8

### Removed
- **`limited` format** — not useful for analysis, hard to distinguish from serial
- **Patches** (ADD_LINE, CHECK_LINE, SPLIT_LINE) — dead feature, events with `plotline_id: null` are sufficient signal
- **RERANK patch** — rank is now computed by code after Pass 2
- **PROMOTE/DEMOTE verdicts** — rank computed by code, Pass 3 no longer changes ranks

### Fixed
- Verdicts with invalid plotline IDs are now skipped instead of applied
- DROP aborts if any events remain unredistributed — events are never set to null
- CLI callback inherits PipelineCallback to prevent AttributeError on batch mode

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
