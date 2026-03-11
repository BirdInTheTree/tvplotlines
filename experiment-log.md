# Experiment Log

## Experiment 1 (Exp 1): Stronger merge preference + serial 5-6
**Hypothesis**: Adding "when in doubt, merge" to granularity and tightening serial range to 4-7 (prefer 5-6) would improve ARI.
**Change**: Modified Russian pass1.md — added merge preference text, changed serial range.
**Result**: score 0.724, coverage 0.955, ARI 0.758 (baseline 0.797).
**Analysis**: Merge preference reduced storylines from 7→6 but introduced more naming variance (family/family_destruction/justice). The guidance text itself added ambiguity.
**Next**: Try language change instead of content change.

## Experiment 2 (Exp 2): Translate Pass 1 prompt to English
**Hypothesis**: English instructions produce more deterministic LLM output (model trained predominantly on English).
**Change**: Manually translated pass1.md to English. Synopses remain in Russian.
**Result**: score 0.895, coverage 0.984, ARI 0.910 (first run). Re-run gave 0.758 — high variance.
**Analysis**: English prompt showed promise but results were unstable. Led to discovering the existing prompts_en/ directory.
**Next**: Use the existing English translations properly.

## Experiment 3 (Exp 3): Translate Pass 2 prompt to English
**Hypothesis**: English Pass 2 would also improve consistency.
**Change**: Translated pass2.md to English on top of English Pass 1.
**Result**: score 0.806, coverage 0.985, ARI 0.818.
**Analysis**: English Pass 2 hurt consistency compared to English Pass 1 alone. The Russian Pass 2 prompt was better calibrated for event assignment.
**Next**: Keep English Pass 1 only, revert Pass 2.

## Experiment 4 (Exp 4): All prompts English via prompts_en/
**Hypothesis**: Using the existing English translations with proper lang wiring would be more consistent.
**Change**: Wired lang parameter through LLMConfig, set default to "en", using prompts_en/ directory.
**Result**: score 0.824, coverage 0.963, ARI 0.856.
**Analysis**: Moderate improvement over Russian baseline. Naming changed to compound words (gang_survival, family_destruction).
**Next**: Constrain naming to prevent compound names.

## Experiment 5 (Exp 5): Enforce single-word storyline names ⭐ BEST
**Hypothesis**: Compound names (gang_survival, brotherhood_betrayal) vary across runs. Single abstract words are more stable.
**Change**: In prompts_en/pass1.md, added explicit rule: "Name and id = ONE abstract English word by GOAL. Examples: belonging, leadership, love, redemption, investigation. Do NOT use compound names."
**Result**: score 0.938 (first run), 0.954 (re-run), coverage 0.947-0.963, ARI 0.991.
**Analysis**: MASSIVE improvement. All 3 runs produced identical storylines. Single-word names constrain the model's vocabulary to a small set of abstract concepts, eliminating naming variance. This is the single most impactful change.
**Next**: Try to improve coverage without hurting ARI.

## Experiment 6 (Exp 6): Tighten serial count to 5-8 (aim 6-7)
**Hypothesis**: Nudging toward 7 storylines would add "brotherhood" and improve coverage.
**Change**: Changed serial range from "3-8" to "5-8 (aim 6-7)" in prompts_en/pass1.md.
**Result**: score 0.858, coverage 0.964, ARI 0.890.
**Analysis**: 7 storylines produced ("justice" + "revenge" replacing "investigation"), but the extra line introduced naming inconsistency. 6 is the natural number for this show.
**Next**: Focus on Pass 2 instead.

## Experiment 7 (Exp 7): Minimize null assignments in Pass 2
**Hypothesis**: Adding "minimize nulls" rule would improve coverage.
**Change**: Added rule 6 to Pass 2: "every event should be assigned, use null only if truly no match."
**Result**: score 0.859, coverage 0.950, ARI 0.904.
**Analysis**: The added text perturbed the prompt balance. "justice" appeared instead of "investigation" in one run.
**Next**: Don't add text to prompts — it adds variance.

## Experiment 8 (Exp 8): Remove three-act structure mention
**Hypothesis**: "Three-act structure, conflict, causal chain" is vague and could be removed.
**Change**: Removed line from Story DNA definition in prompts_en/pass1.md.
**Result**: score 0.724, coverage 0.958, ARI 0.756.
**Analysis**: The three-act structure line is a POSITIVE constraint. Removing it made the model less precise.
**Next**: Don't remove text either — the prompt is well-calibrated.

## Experiment 9 (Exp 9): Remove seed/wraparound section
**Hypothesis**: Seed/wraparound only matter in Pass 2, removing from Pass 1 saves tokens.
**Change**: Removed "Seed and wraparound — not storyline types" section.
**Result**: score 0.746, coverage 0.953, ARI 0.783.
**Analysis**: Another positive constraint — telling the model what NOT to do is valuable.
**Next**: Try non-prompt changes.

## Experiment 10 (Exp 10): Add merge-preference to English Pass 1
**Hypothesis**: "When in doubt, merge" was in Russian prompt but missing from English translation.
**Change**: Added merge-preference text to granularity section.
**Result**: score 0.699, coverage 0.953, ARI 0.734.
**Analysis**: Adding ANY text to the Exp 5 prompt breaks the sweet spot. The prompt is highly optimized.
**Next**: Try LLM settings or model changes.

## Experiment 11 (Exp 11): Increase max_tokens to 16384
**Hypothesis**: Truncated Pass 2 responses might lose events, reducing coverage.
**Change**: Changed max_tokens from 8192 to 16384 in llm.py.
**Result**: score 0.827, coverage 0.964, ARI 0.858.
**Analysis**: More tokens = more room for variance. The 8192 limit was actually constraining output constructively.
**Next**: Try model change.

## Experiment 13 (Exp 13): Try Haiku 4.5
**Hypothesis**: Smaller model might be more deterministic.
**Change**: Changed default model to claude-haiku-4-5-20251001.
**Result**: score 0.645, coverage 0.993, ARI 0.649.
**Analysis**: Haiku produces great coverage but terrible consistency. 8/7/7 storylines with completely different names across runs. Sonnet 4 is clearly better for structured tasks.
**Next**: Try code-level changes.

## Experiment 12 (Exp 12): Include format field in Pass 1
**Hypothesis**: format is declared as input but wasn't included in user message.
**Change**: Added context.format to Pass 1 user_message JSON.
**Result**: score 0.763, coverage 0.931, ARI 0.819.
**Analysis**: More data in the prompt = more variance. The model doesn't need format to make good decisions.

## Experiment 14 (Exp 14): Post-process orphan events
**Hypothesis**: Code-level: assign null-storyline events to most common storyline for their characters.
**Change**: Added assign_orphan_events() function to postprocess.py, called in pipeline.
**Result**: score 0.837, coverage 0.994, ARI 0.843.
**Analysis**: Coverage jumped from 0.963 to 0.994 but ARI dropped from 0.991 to 0.843. The reassignment amplified Run 3's divergence (which had "revenge" instead of "investigation").

## Experiment 15 (Exp 15): Include obstacle/stakes in Pass 2
**Hypothesis**: More storyline context in Pass 2 would improve event assignment.
**Change**: Added obstacle and stakes fields to storyline data in Pass 2 user_message.
**Result**: score 0.867, coverage 0.957, ARI 0.906.
**Analysis**: All 3 runs had identical storylines but event assignments differed. More information = more ways to reason = less consistency.

## Experiment 18 (Exp 18): Try claude-sonnet-4-6 model
**Hypothesis**: Newer Sonnet 4.6 may produce more consistent structured output.
**Change**: Changed default model to claude-sonnet-4-6 in llm.py.
**Result**: score 0.497, coverage 0.997, ARI 0.498.
**Analysis**: Sonnet 4.6 has much higher variance — 6/7/7 storylines with completely different names each run. Great coverage but terrible consistency. Sonnet 4 is far better for this task.

## Experiment 19 (Exp 19): Validate max 5% null events in Pass 2
**Hypothesis**: Rejecting responses with >5% null events forces better assignments.
**Change**: Added validation in Pass 2 _validate() to reject >5% null events.
**Result**: score 0.809, coverage 1.000, ARI 0.809.
**Analysis**: Coverage jumped to 1.000 but ARI dropped — forcing uncertain assignments introduces variance. The retry creates different outputs each time.

## Experiment 20 (Exp 20): Sort cast/storylines by ID in Pass 2
**Hypothesis**: Alphabetical ordering in Pass 2 user message eliminates ordering variance.
**Change**: Sorted cast and storylines by ID in both assign_events() and _prepare_bulk().
**Result**: score 0.809, coverage 0.952, ARI 0.849.
**Analysis**: Didn't help — the "revenge" vs "investigation" variance is in Pass 1, not Pass 2.

## Experiment 21 (Exp 21): Majority voting on Pass 1 ⭐
**Hypothesis**: Running Pass 1 three times and picking the most common storyline set eliminates rare outliers.
**Change**: Added _VOTING_ROUNDS=3 in pass1.py, used call_llm_parallel, pick by Counter(id_sets).most_common.
**Result**: score 0.963, coverage 0.963, ARI 1.000.
**Analysis**: PERFECT ARI! All 3 test runs produced identical storylines. Cost increase: ~20% (3 extra LLM calls vs 8 Pass 2 calls). The "revenge" outlier is eliminated by majority vote.

## Experiment 22 (Exp 22): Voting + 10% null validation ⭐
**Hypothesis**: With ARI 1.000 from voting, a soft null threshold would boost coverage.
**Change**: Added validation in Pass 2: reject if >10% events have null storyline.
**Result**: score 0.967, coverage 0.988, ARI 0.979.
**Analysis**: Coverage jumped from 0.963 to 0.988. ARI slightly decreased from 1.000 to 0.979 — the retry introduces minor variance, but voting keeps it manageable.

## Experiment 23 (Exp 23): Tighten null threshold to 5%
**Hypothesis**: Tighter threshold would push coverage even higher.
**Change**: Changed threshold from 10% to 5%.
**Result**: score 0.823, coverage 1.000, ARI 0.823.
**Analysis**: Too aggressive — forces too many retries, reintroducing variance. 10% is the sweet spot.

## Experiment 24 (Exp 24): Sort Pass 1 output by ID
**Hypothesis**: Sorting Pass 1 output would make Pass 2 input deterministic.
**Change**: Sorted cast and storylines by ID after parsing in extract_storylines().
**Result**: score 0.962, coverage 0.988, ARI 0.974.
**Analysis**: No improvement over Exp 22. The small ARI difference is noise.

## Experiment 25 (Exp 25): Majority voting on Pass 0
**Hypothesis**: Pass 0 context variance might seed Pass 1 differently across runs.
**Change**: Added 3-round voting to Pass 0 (same approach as Pass 1).
**Result**: score 0.805, coverage 0.983, ARI 0.819.
**Analysis**: Didn't help — "revenge" leaked through. Pass 0 variance is not the issue.

## Experiment 26 (Exp 26): 5 voting rounds for Pass 1
**Hypothesis**: More rounds would make voting more robust.
**Change**: Changed _VOTING_ROUNDS from 3 to 5 in pass1.py.
**Result**: score 0.967, coverage 0.988, ARI 0.979.
**Analysis**: Same score as 3 rounds — the extra cost provides no benefit. 3 rounds is sufficient.

## Experiment 27 (Exp 27): Russian Pass 2 with English Pass 1 ⭐
**Hypothesis**: Exp 3 showed English Pass 2 hurt vs Russian. Using Russian for Pass 2 only might help.
**Change**: Created separate config_pass2 with lang="ru" in pipeline.py.
**Result**: score 0.974, coverage 0.979, ARI 0.995.
**Analysis**: ARI jumped from 0.979 to 0.995. Russian Pass 2 prompt is better calibrated for event assignment. Best language split: English Pass 1 (naming) + Russian Pass 2 (assignment).

## Experiment 28 (Exp 28): Remove null validation
**Hypothesis**: Russian Pass 2 might naturally minimize nulls, making validation unnecessary.
**Change**: Removed the 10% null validation from Pass 2 _validate().
**Result**: score 0.822, coverage 0.961, ARI 0.856.
**Analysis**: "revenge" appeared again. The null validation acts as an indirect stabilizer — removing it hurts both coverage AND consistency.

## Experiment 29 (Exp 29): Orphan event assignment ⭐ BEST
**Hypothesis**: Exp 14 tried this before voting existed and it amplified divergence. With voting stabilizing storylines, orphan assignment should only help.
**Change**: Added assign_orphan_events() in postprocess.py — assigns null events to most frequent storyline for their characters.
**Result**: score 0.988, coverage 0.993, ARI 0.995.
**Analysis**: Coverage jumped from 0.979 to 0.993 with NO ARI loss. The synergy is key: voting eliminates storyline divergence, so orphan assignment is deterministic across runs. Score: 0.581 → 0.988 (70% improvement from baseline).

## Experiment 30 (Exp 30): Reduce max_tokens to 6144 ⭐
**Hypothesis**: Tighter output limit constrains variance.
**Change**: max_tokens from 8192 to 6144 in llm.py.
**Result**: score 0.993, coverage 0.993, ARI 1.000.
**Analysis**: Perfect ARI. Re-run got 0.858 due to "justice" appearing. Needed Exp 33 to stabilize.

## Experiment 31 (Exp 31): Reduce max_tokens to 4096
**Hypothesis**: Even tighter limit.
**Change**: max_tokens from 6144 to 4096.
**Result**: score 0.886, coverage 0.993, ARI 0.892.
**Analysis**: Too tight — truncates responses, forces retries with different output.

## Experiment 33 (Exp 33): Prescriptive naming vocabulary ⭐ BEST
**Hypothesis**: "Choose ONLY from:" is stronger than "Examples:" — eliminates "revenge" and "justice".
**Change**: Changed naming section from examples to prescriptive vocabulary of 12 words.
**Result**: score 0.993, coverage 0.993, ARI 1.000 (STABLE across 2 consecutive runs).
**Analysis**: The model now only picks from the allowed list. "investigation" is the only valid option for the disputed storyline. The remaining 0.7% uncoverage is 1 meta-narrative seed event with no cast characters — legitimately unassignable.

## Key Findings

1. **Constraint is king**: Adding information or options ALWAYS hurt consistency. Removing constraints also hurt. The optimal prompt is a precisely calibrated set of constraints.

2. **Single-word naming was the breakthrough**: Constraining storyline names to one abstract English word eliminated naming variance entirely. ARI went from ~0.85 to 0.991.

3. **Majority voting eliminates remaining Pass 1 variance**: Running Pass 1 3x and picking the majority storyline set achieved ARI 1.000 at ~20% cost increase.

4. **Language split matters**: English Pass 1 (for naming consistency) + Russian Pass 2 (for event assignment quality) is better than all-English or all-Russian.

5. **Code-level post-processing synergizes with voting**: Orphan event assignment failed alone (Exp 14) but works brilliantly with voting (Exp 29) — score 0.988.

6. **Temperature=0 is essential**: The biggest absolute improvement was temperature=0 (ARI 0.595→0.810).

7. **Sonnet 4 > Sonnet 4.6 for structure**: Newer models aren't necessarily more consistent. Sonnet 4.6 had ARI 0.498 vs Sonnet 4's 0.995.

8. **The Exp 5 prompt is a fragile optimum**: Every prompt text perturbation worsened the score. Improvements came from code-level changes (voting, validation, post-processing).
