# tvplotlines autoresearch v3

Автономная оптимизация пайплайна извлечения сюжетных линий.

## Setup

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar23`). The branch `autoresearch/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current main.
3. **Read the in-scope files** — read ALL of these before starting, do not skip any:
   - `CLAUDE.md` — project context and conventions.
   - `src/tvplotlines/prompts_en/pass0.md` — Pass 0 prompt (context detection).
   - `src/tvplotlines/prompts_en/pass1.md` — Pass 1 prompt (plotline extraction).
   - `src/tvplotlines/prompts_en/pass2.md` — Pass 2 prompt (event assignment).
   - `src/tvplotlines/prompts_en/pass3.md` — Pass 3 prompt (structural review).
   - `src/tvplotlines/metrics.py` — metric computation (read-only).
4. **Source environment**: `set -a && source .env && set +a` — loads ANTHROPIC_API_KEY and OPENAI_API_KEY.
5. **Initialize results.tsv**: Create `results.tsv` with header row. Baseline will be the first entry.
6. **Confirm and go**.

## Metric

**Quality score** = mean across fast set shows of:

```
show_score = coverage × max(coh_sep, 0)
```

Where:
- **coverage** = fraction of events with non-null plotline assignment.
- **coh_sep** = within-plotline coherence minus between-plotline separation, computed from OpenAI `text-embedding-3-small` embeddings. Higher = plotlines are more semantically distinct.

**Constraint**: min(show_score) ≥ 0.01 — no show may collapse to zero. A change that improves the mean but kills one show is rejected.

**Why not ARI**: ARI measures run-to-run consistency, not quality. A pipeline that consistently produces bad results scores high on ARI. Coh-Sep measures whether extracted plotlines are semantically distinct — closer to actual extraction quality. One run per experiment instead of three.

**Embeddings**: OpenAI `text-embedding-3-small`. Cost: ~$0.002 per show (negligible).

## Fast set

4 shows for rapid iteration:

| Show | Code | Eps | Type | Lang |
|------|------|-----|------|------|
| Breaking Bad S01 | BB | 7 | serial | en |
| Слово пацана S01 | SP | 8 | serial | ru |
| House S01 | HOUSE | 22 | procedural | en |
| GoT S01 | GOT | 10 | ensemble | en |

Synopses: `/Users/nvashko/Projects/1-projects/tvplotlines-app/data/synopses/{CODE}_S01E*.txt`
Results: `/Users/nvashko/Projects/1-projects/tvplotlines-app/data/results/`

## Experimentation

Each experiment = modify prompts and/or pipeline code → run pipeline on fast set → compute coh-sep → keep/discard.

**What you CAN modify:**
- Prompt files: `src/tvplotlines/prompts_en/pass{0,1,2,3}.md` — role formulations, step structure, strictness criteria, examples, wording.
- Pipeline code: `src/tvplotlines/pass0.py`, `pass1.py`, `pass2.py`, `pass3.py` — parsing, validation, data preparation, what gets sent to LLM.
- Post-processing: `src/tvplotlines/postprocess.py`, `verdicts.py` — span/weight computation, verdict application.
- Orchestration: `src/tvplotlines/pipeline.py` — pass ordering, what data flows between passes.
- LLM settings: `src/tvplotlines/llm.py` — model name, temperature, max_tokens. These are experiment parameters too.

**What you CANNOT modify** (fixed evaluation — otherwise optimization is meaningless):
- Embedding metrics script: `/Users/nvashko/Projects/1-projects/tvplotlines-app/data/compute_embedding_metrics.py`
- Synopsis files
- The scoring formula defined in this document

**Cost** is a soft constraint. Some increase is acceptable for meaningful score gains, but it should not blow up dramatically. The `cost_usd` column in results.tsv tracks this.

**Simplicity criterion**: All else being equal, simpler is better — shorter prompts, less code. If removing text or code gives equal or better results — keep.

**The first run**: Establish baseline with current prompts. This is a new baseline (prompts were rewritten).

## Running an experiment

### Step 1: Run pipeline on fast set

```bash
set -a && source .env && set +a

tvplotlines run /Users/nvashko/Projects/1-projects/tvplotlines-app/data/synopses/BB_S01E*.txt \
  --show "Breaking Bad" --season 1 --pass2-mode batch \
  -o /Users/nvashko/Projects/1-projects/tvplotlines-app/data/results/bb_s01_result.json

tvplotlines run /Users/nvashko/Projects/1-projects/tvplotlines-app/data/synopses/SP_S01E*.txt \
  --show "Слово пацана" --season 1 --pass2-mode batch \
  -o /Users/nvashko/Projects/1-projects/tvplotlines-app/data/results/slovo_patsana_s01_result.json

tvplotlines run /Users/nvashko/Projects/1-projects/tvplotlines-app/data/synopses/HOUSE_S01E*.txt \
  --show "House" --season 1 --pass2-mode batch \
  -o /Users/nvashko/Projects/1-projects/tvplotlines-app/data/results/house_s01_result_v3.json

tvplotlines run /Users/nvashko/Projects/1-projects/tvplotlines-app/data/synopses/GOT_S01E*.txt \
  --show "Game of Thrones" --season 1 --pass2-mode batch \
  -o /Users/nvashko/Projects/1-projects/tvplotlines-app/data/results/got_s01_result.json
```

Run shows sequentially (batch mode polls for results).

### Step 2: Compute metrics

```bash
cd /Users/nvashko/Projects/1-projects/tvplotlines-app/data
python3 compute_embedding_metrics.py
```

Read the Coh-Sep column for each fast set show.

### Step 3: Compute score

```
mean_score = mean of [coverage × max(coh_sep, 0)] across fast set
min_score = min of [coverage × max(coh_sep, 0)] across fast set
```

**Time budget**: Each experiment takes ~5-10 minutes (4 shows × 1-3 minutes each). If a run exceeds 20 minutes, kill it and treat it as a crash.

**Cost**: Each experiment costs ~$1.5-2 (API calls + negligible embedding cost). Budget accordingly.

**HARD LIMIT: $30 total.** Track cumulative cost in results.tsv. When cumulative cost approaches $28, stop and summarize findings.

## Logging results

Log to `results.tsv` (tab-separated).

Header and columns:

```
commit	mean_score	min_score	bb	sp	house	got	cost_usd	status	description
```

1. git commit hash (short, 7 chars)
2. mean_score across fast set
3. min_score across fast set
4-7. per-show coh_sep values
8. approximate cost in USD
9. status: `keep`, `discard`, or `crash`
10. short description of what changed

Example:

```
commit	mean_score	min_score	bb	sp	house	got	cost_usd	status	description
a1b2c3d	0.043	0.002	0.083	0.077	0.002	0.077	1.5	keep	baseline (new prompts)
b2c3d4e	0.055	0.015	0.090	0.082	0.015	0.085	1.8	keep	add season-length scaling to pass1
c3d4e5f	0.038	0.000	0.085	0.080	-0.003	0.070	1.5	discard	remove rank rules (house collapsed)
```

## The experiment loop

LOOP FOREVER:

1. Look at the git state and `results.tsv` — what's been tried, what worked.
2. Pick the next experiment. Prioritize:
   - Changes that affect Pass 1–2 (larger impact on plotline quality).
   - Changes that improve weak shows (House, procedurals) without hurting strong ones.
   - Changes that simplify prompts (cheaper per run).
   - Combining two previous near-wins.
3. Edit prompt(s) and/or pipeline code. One change per experiment — isolate variables.
4. `git commit` the change.
5. Run fast set (Step 1 above).
6. Compute metrics (Step 2 above).
7. If mean_score improved AND min_score ≥ 0.01 → keep the commit.
8. If mean_score did not improve OR min_score < 0.01 → `git reset --hard HEAD~1` to revert.
9. Record results in `results.tsv` (do NOT commit results.tsv — leave untracked).

**Crashes**: If validation errors consistently fail, the prompt change broke structural output. Revert and try a different approach.

**NEVER STOP**: Once the loop begins, do NOT pause to ask the human. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep or away and expects you to continue working *indefinitely* until manually stopped. Each experiment takes ~5-10 minutes, so you can run ~6-12 per hour, ~50-100 overnight. If you run out of ideas, think harder — reread the prompts, try combining near-misses, try radical changes. The loop runs until the human interrupts you, period.

## Strategy notes

- **Coh-Sep is the bottleneck for long shows.** Coverage is already high everywhere.
- Long seasons produce too few plotlines → all events blend together → low coherence, no separation.
- Focus on Pass 1 instructions that scale plotline count with season length.
- Be careful not to over-generate plotlines for short shows — verify on fast set.
- If a change helps House but hurts BB/SP/GOT, it's rejected (min constraint).
- Pass 3 runs by default. To disable it, add `--skip-review`. But note: Pass 3 adds another LLM call = more variance. Test both ways.
- Theoretical grounding matters: changes should be defensible from narrative theory, not ad-hoc rules.

## v2 baseline reference

| Show | Eps | Lines | Coh-Sep | Coverage |
|------|-----|-------|---------|----------|
| Breaking Bad S01 | 7 | 4 | 0.083 | 0.97 |
| Slovo Patsana S01 | 8 | 7 | 0.077 | 0.97 |
| GoT S01 | 10 | 8 | 0.077 | 1.00 |
| House S01 | 22 | 4 | 0.002 | 0.98 |

The gap between short shows (~0.08) and long procedurals (~0.00) is the primary optimization target.
