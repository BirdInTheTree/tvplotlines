# Changelog

## Unreleased

### Fixed
- Verdicts with invalid plotline IDs are now skipped instead of applied
- DROP aborts if any events remain unredistributed — events are never set to null
- CLI callback inherits PipelineCallback to prevent AttributeError on batch mode

### Added
- CLI progress output: prints status after each pipeline pass
- `write-synopses` creates folder named after show (`mad-men/`) instead of generic `synopses/`
- Synopsis generation from Wikipedia: `tvplotlines write-synopses "Show Name"`
- Per-episode theme in output JSON

### Changed
- Plotline count limits in prompts: max 5 (non-ensemble), 5–6 (ensemble)
- Auto-demote replaced with warnings — code no longer overrides LLM rank decisions
- Output filename uses dashes: `mad-men_s01.json`
- Pass 2 CLI default changed from parallel to batch

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
