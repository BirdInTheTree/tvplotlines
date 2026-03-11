# Plotter autoresearch

Автономная оптимизация пайплайна извлечения сюжетных линий.

## Setup

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar11`). The branch `autoresearch/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current main.
3. **Read the in-scope files** — read ALL of these before starting, do not skip any:
   - `CLAUDE.md` — project context and conventions.
   - `md/architecture.md` — pipeline architecture.
   - `md/prompt-experiment-ideas.md` — experiment hypotheses (H1–H14).
   - `src/plotter/prompts/pass0.md` — Pass 0 prompt (context detection).
   - `src/plotter/prompts/pass1.md` — Pass 1 prompt (storyline extraction).
   - `src/plotter/prompts/pass2.md` — Pass 2 prompt (event assignment).
   - `src/plotter/prompts/pass3.md` — Pass 3 prompt (narratologist review).
   - `src/plotter/metrics.py` — metric computation (read-only).
   - `tests/fixtures/slovo_patsana_s01_consistency.json` — current baseline.
4. **Source environment**: `set -a && source .env && set +a` — this loads the API key. Ensure it's sourced before every run.
5. **Initialize results.tsv**: Create `results.tsv` with header row. Baseline will be the first entry.
6. **Confirm and go**.

## Experimentation

Each experiment = modify prompts and/or pipeline code → run N pipeline passes → compute score.

**What you CAN modify:**
- Prompt files: `src/plotter/prompts/pass{0,1,2,3}.md` — role formulations, step structure, strictness criteria, examples, wording.
- Pipeline code: `src/plotter/pass0.py`, `pass1.py`, `pass2.py`, `pass3.py` — parsing, validation, data preparation, what gets sent to LLM.
- Post-processing: `src/plotter/postprocess.py`, `verdicts.py` — span/weight computation, verdict application.
- Orchestration: `src/plotter/pipeline.py` — pass ordering, what data flows between passes.
- LLM settings: `src/plotter/llm.py` — model name, temperature, max_tokens. These are experiment parameters too.

**What you CANNOT modify** (fixed evaluation — otherwise optimization is meaningless):
- Metric code: `src/plotter/metrics.py` — the scoring function.
- Test harness: `tests/test_consistency.py` — how experiments are run.
- Test fixtures: `tests/fixtures/` — input data.

**Cost** is a soft constraint. Some increase is acceptable for meaningful score gains, but it should not blow up dramatically. A 10% score improvement that doubles cost? Worth considering. The same score at half the cost? Definitely keep. The `cost_usd` column in results.tsv tracks this — use it to compare experiments.

**The goal:** The pipeline takes TV series synopses and extracts storylines — narrative threads that span multiple episodes. A good result means:
- **High coverage** — every narrative event in a synopsis is assigned to a storyline (not left orphaned).
- **High consistency** — running the pipeline twice on the same input gives structurally the same storylines. Different wording is fine ("belonging" vs "acceptance"), but the same characters should end up grouped together.

Currently measured as `score = coverage × consistency(ARI)` — see `metrics.py` for details. This may not be the optimal way to measure quality; if you see problems with the metric, document them in `metric-concerns.md` but do not modify `metrics.py` during experiments.

Current baseline: score **0.581** (coverage 0.977, ARI 0.595). Run without Pass 3 review.

**Simplicity criterion**: All else being equal, simpler is better — shorter prompts, less code. If removing text or code gives equal or better results — keep. A 0.01 score improvement that adds 50 lines of complexity? Probably not worth it. A 0.01 improvement from simplifying? Definitely keep.

**The first run**: Establish baseline with current prompts (should match the stored baseline).

## Running an experiment

Each experiment requires N independent pipeline runs (N=3 minimum) to compute consistency.

```bash
python -m pytest tests/test_consistency.py -v -s > run.log 2>&1
```

Extract results:

```bash
grep -E "^(Avg coverage|Consistency|Score):" run.log
```

Expected output:

```
Avg coverage: 0.977
Consistency (ARI): 0.595
Score: 0.581
```

**Time budget**: Each experiment takes ~10 minutes (3 runs × ~3 minutes each). If a run exceeds 20 minutes, kill it (`kill %1` or `kill <PID>`) and treat it as a crash — log, revert, move on.

**Cost**: Each experiment costs ~$1–3 (API calls). Budget accordingly.

## Logging results

Log to `results.tsv` (tab-separated).

Header and columns:

```
commit	score	coverage	consistency	cost_usd	status	description
```

1. git commit hash (short, 7 chars)
2. score = coverage × consistency (e.g. 0.581)
3. coverage (e.g. 0.977)
4. consistency ARI (e.g. 0.595)
5. approximate cost in USD (e.g. 1.5)
6. status: `keep`, `discard`, or `crash`
7. short description of what changed

Example:

```
commit	score	coverage	consistency	cost_usd	status	description
a1b2c3d	0.581	0.977	0.595	1.5	keep	baseline
b2c3d4e	0.640	0.980	0.653	1.8	keep	H13: fewer theory quotes in pass1
c3d4e5f	0.550	0.990	0.556	1.5	discard	H7: free-form pass3 prompt
d4e5f6g	0.000	0.000	0.000	0.0	crash	H5: no role in pass3 (validation errors)
```

## The experiment loop

LOOP FOREVER:

1. Look at the git state and `results.tsv` — what's been tried, what worked.
2. Pick the next experiment. Use `md/prompt-experiment-ideas.md` as inspiration, but you can also try your own ideas. Prioritize:
   - Hypotheses that affect Pass 1–2 (larger impact on consistency).
   - Hypotheses that simplify prompts (cheaper per run).
   - Combining two previous near-wins.
3. Edit prompt(s) and/or pipeline code. One change per experiment — isolate variables.
4. `git commit` the change.
5. Run: `python -m pytest tests/test_consistency.py -v -s > run.log 2>&1`
6. Extract: `grep -E "^(Avg coverage|Consistency|Score):" run.log`
7. If grep is empty, the run crashed. Check `tail -n 50 run.log` and attempt a fix.
8. Record results in `results.tsv` (do NOT commit results.tsv — leave untracked).
9. If score improved → keep the commit, advance the branch.
10. If score is equal or worse → `git reset --hard HEAD~1` to revert.

**Crashes**: If validation errors consistently fail, the prompt change broke structural output. Revert and try a different approach.

**NEVER STOP**: Once the loop begins, do NOT pause to ask the human. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep or away and expects you to continue working *indefinitely* until manually stopped. Each experiment takes ~10 minutes, so you can run ~6 per hour, ~50 overnight. If you run out of hypotheses from the list, think harder — reread the prompts, try combining near-misses, try radical changes. The loop runs until the human interrupts you, period.

## Strategy notes

- **ARI is the bottleneck** (0.595). Coverage is already high (0.977). Focus on consistency.
- Consistency improves when the LLM makes the same *structural* decisions across runs — same grouping of characters into storylines.
- Things that help consistency: concrete rules > vague guidelines, examples > theory, constrained output > free-form.
- Things that hurt consistency: subjective criteria, open-ended instructions, ambiguous categories.
- Pass 3 currently runs with `skip_review=True` in the consistency test. To test Pass 3 prompt changes, update the test to include Pass 3. But note: Pass 3 adds another LLM call = more variance. Test it both ways.
- If you plateau on ARI, consider testing with a different show/season to verify generalization.
