# How does `also_affects` count toward ABC rank

**Date:** 2026-03-26

## Question

When computing rank from number of events in a plotline, should `also_affects` mentions count? Three formulas tested:

1. **Primary only** — count `plotline_id` assignments
2. **Primary + ½AA** — primary = 1, also_affects = 0.5
3. **Equal weight** — both = 1

All three: runners → null, case-of-the-week → A (procedural) or B (hybrid), rest sorted by count.

## Reproduce

```bash
python scripts/rank_experiment.py \
  examples/results/bb_s01.json \
  examples/results/got_s01.json
```

Mad Men S01 tested separately (not in repo).

## Results

### Breaking Bad S01 (serial, non-ensemble, 7 episodes)

| Plotline | Span | Primary | AA | LLM | P-only | P+½AA | P+AA |
|----------|-----:|--------:|---:|-----|--------|-------|------|
| Walt: Empire | 7/7 | 80 | 40 | A | A | A | A |
| Walt: Family | 7/7 | 36 | 8 | B | B | B | B |
| Walt: Treatment | 3/7 | 13 | 4 | C | C | C | C |
| Hank: Investigation | 6/7 | 12 | 1 | C | C | C | C |

### Game of Thrones S01 (serial, ensemble, 10 episodes)

| Plotline | Span | Primary | AA | LLM | P-only | P+½AA | P+AA |
|----------|-----:|--------:|---:|-----|--------|-------|------|
| Ned: Honor | 10/10 | 62 | 16 | A | A | A | A |
| Daenerys: Transformation | 9/10 | 41 | 2 | A | B | B | C |
| Arya: Independence | 7/10 | 20 | 5 | C | C | C | C |
| Jon: Belonging | 7/10 | 19 | 0 | B | C | C | C |
| Catelyn: Protection | 6/10 | 19 | 8 | B | C | C | C |
| Tyrion: Survival | 5/10 | 14 | 7 | B | C | C | C |
| Cersei: Power | 6/10 | 13 | 31 | B | C | C | B |
| Robb: War | 3/10 | 9 | 4 | A | C | C | C |
| Night's Watch | 3/10 | 7 | 0 | C | C | C | C |

### Mad Men S01 (serial, non-ensemble, 13 episodes)

| Plotline | Span | Primary | AA | LLM | P-only | P+½AA | P+AA |
|----------|-----:|--------:|---:|-----|--------|-------|------|
| Don: Identity | 13/13 | 60 | 14 | A | A | A | A |
| Pete: Advancement | 11/13 | 34 | 14 | C | B | B | B |
| Don: Marriage | 11/13 | 32 | 12 | B | C | C | C |
| Peggy: Creativity | 10/13 | 29 | 5 | C | C | C | C |
| Betty: Liberation | 7/13 | 25 | 9 | B | C | C | C |
| Roger: Joan Affair | 4/13 | 10 | 0 | C | C | C | C |
| Joan: Personal Life | 2/13 | 5 | 0 | C | C | C | C |


## Decision

**Equal weight** (primary + also_affects, both = 1) for `computed_rank`.

Pass 3 sees event counts and can PROMOTE/DEMOTE (→ `reviewed_rank`). User sees both ranks when they diverge.

Script: `scripts/rank_experiment.py`.
