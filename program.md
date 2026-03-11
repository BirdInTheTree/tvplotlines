# Plotter autoresearch

Автономная оптимизация промптов для пайплайна извлечения сюжетных линий.

## Setup

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar11`). The branch `autoresearch/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current main.
3. **Read the in-scope files**:
   - `CLAUDE.md` — project context and conventions.
   - `md/architecture.md` — pipeline architecture.
   - `md/prompt-experiment-ideas.md` — experiment hypotheses (H1–H14).
   - `src/plotter/prompts/pass0.md` — Pass 0 prompt (context detection).
   - `src/plotter/prompts/pass1.md` — Pass 1 prompt (storyline extraction).
   - `src/plotter/prompts/pass2.md` — Pass 2 prompt (event assignment).
   - `src/plotter/prompts/pass3.md` — Pass 3 prompt (narratologist review).
   - `src/plotter/metrics.py` — metric computation (read-only).
   - `tests/fixtures/slovo_patsana_s01_consistency.json` — current baseline.
4. **Verify API key**: Check that `ANTHROPIC_API_KEY` is set (`set -a && source .env && set +a`).
5. **Initialize results.tsv**: Create `results.tsv` with header row. Baseline will be the first entry.
6. **Confirm and go**.

## Experimentation

Each experiment = modify one or more prompt files → run N pipeline passes → compute score.

**What you CAN modify:**
- Prompt files: `src/plotter/prompts/pass{0,1,2,3}.md` — these are the only files you edit.
- Role formulations, step structure, strictness criteria, examples, wording.

**What you CANNOT modify:**
- Pipeline code (`pipeline.py`, `pass0.py`, `pass1.py`, `pass2.py`, `pass3.py`).
- Metric code (`metrics.py`).
- Validation code (`pass2.py:_validate`, `pass3.py:_parse_verdicts`).
- Model settings (model name, temperature, max_tokens).
- Test fixtures.

**The goal: get the highest score = coverage × consistency(ARI).**

Current baseline: score **0.581** (coverage 0.977, ARI 0.595). Run without Pass 3 review.

**Simplicity criterion**: All else being equal, shorter prompts are better. If removing text gives equal or better results — keep. A 0.01 score improvement that adds 50 lines of examples? Probably not worth it. A 0.01 improvement from simplifying instructions? Definitely keep.

**The first run**: Establish baseline with current prompts (should match the stored baseline).

## Running an experiment

Each experiment requires N independent pipeline runs (N=3 minimum) to compute consistency.

```bash
# Source API key
set -a && source .env && set +a

# Run the consistency test (3 pipeline runs, computes ARI)
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

**Time budget**: Each experiment takes ~10 minutes (3 runs × ~3 minutes each). If a run exceeds 20 minutes, kill it.

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
3. Edit the prompt file(s). One change per experiment — isolate variables.
4. `git commit` the prompt change.
5. Run: `set -a && source .env && set +a && python -m pytest tests/test_consistency.py -v -s > run.log 2>&1`
6. Extract: `grep -E "^(Avg coverage|Consistency|Score):" run.log`
7. If grep is empty, the run crashed. Check `tail -n 50 run.log` and attempt a fix.
8. Record results in `results.tsv` (do NOT commit results.tsv — leave untracked).
9. If score improved → keep the commit, advance the branch.
10. If score is equal or worse → `git reset --hard HEAD~1` to revert.

**Crashes**: If validation errors consistently fail, the prompt change broke structural output. Revert and try a different approach.

**NEVER STOP**: Do NOT pause to ask the human. Do NOT ask "should I keep going?". You are autonomous. If you run out of hypotheses from the list, try your own ideas: rephrase instructions, add/remove examples, change ordering, adjust strictness. The loop runs until the human interrupts you.

## Strategy notes

- **ARI is the bottleneck** (0.595). Coverage is already high (0.977). Focus on consistency.
- Consistency improves when the LLM makes the same *structural* decisions across runs — same grouping of characters into storylines.
- Things that help consistency: concrete rules > vague guidelines, examples > theory, constrained output > free-form.
- Things that hurt consistency: subjective criteria, open-ended instructions, ambiguous categories.
- Pass 3 currently runs with `skip_review=True` in the consistency test. To test Pass 3 prompt changes, update the test to include Pass 3. But note: Pass 3 adds another LLM call = more variance. Test it both ways.
- If you plateau on ARI, consider testing with a different show/season to verify generalization.
