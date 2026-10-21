# Slice 2 offline-eval plan: qualified backlog outcomes only

Status: **Plan only; paid scoring is blocked.** OpenAI is deferred until final
validation. No OpenAI call, embedding, draft, or scored run may start from this
plan. Paid provider scoring remains blocked until the nonzero-cap and pricing
conditions in §6 are satisfied. This update only records sequencing; it does
not start interim scoring.

Tracker: https://github.com/strataga/queuesift/issues/4  
Frozen cohort:
`evals/manifests/uv-backlog-sweep-2026-10-20.json`  
Gold:
`evals/adjudication/uv-backlog-gold-2026-10-20.json`  
Gold rules:
`docs/spikes/2026-10-20-uv-backlog-gold-rules.md`

## 1. Objective

Prepare—not run—an offline evaluation for the only qualified backlog tasks:

- Stale-triage classification: 145 positives, 5 negatives.
- Missing-reproduction secondary judgment: 55 positives and 30 adjudicated
  negatives.
- Duplicate retrieval/classification: no evaluation; the gold set has only 3
  positives against a 30-positive minimum.

This plan measures classification behavior with uncertainty, not BLEU, ROUGE,
BERTScore, LLM-as-judge scores, or provider-specific quality claims.

## 2. Frozen inputs and leakage controls

For every evaluated issue, use only:

- Creation-time title.
- Creation-time body/template sections.
- Parsed template fields.
- Author association available at creation/first ingestion.
- Repository taxonomy snapshot and code/version metadata frozen no later than
  the issue creation time.

Do not use:

- Current `updated_at`.
- Current labels.
- Later comments, label applications/removals, assignments, milestones,
  closures, duplicate marks, cross-references, or timeline outcomes.
- Edited bodies, if edit history becomes available.
- The gold outcome as a model input or retrieval query.
- Any chunk whose source timestamp is after the issue creation time.

For a future retrieval corpus:

- Backfill closed-issue resolutions as immutable closure snapshots.
- Version code/docs chunks with `valid_from` and, when superseded,
  `valid_to`.
- Enforce the design §7.2 timestamp filter for every evaluated issue.
- No website scraping as historical evidence.

## 3. Systems to compare

When unblocked, Slice 2 compares:

1. **Deterministic/code baseline.** Template parsing, parsed-field checks, and
   explicit queue rules. It may not claim semantic work and must not consume
   future timeline evidence.
2. **QueueSift decision method.** Deterministic code plus the approved Jev
   battery, retrieval, and versioned thresholds/weights.
3. **Named LLM semantic baseline.** Used only to test whether the Jev-based
   decision method adds value. OpenAI is reserved for final validation; before
   then, local Ollama may stand in for development-only checks. Local results
   must be labelled with the local model and must never be reported as OpenAI
   results.

All systems use the same frozen inputs. All prompts, model IDs, retrieval
limits, random seeds, thresholds, and weights are recorded for each run.
Changing thresholds or weights requires a new evaluation; do not tune them on
the frozen gold.

## 4. Metrics and denominators

Use only task-appropriate metrics.

### Stale triage

Because all 150 gold labels are known:

- Confusion matrix.
- Precision, recall, and F1 with Wilson 95% intervals.
- Precision-recall behavior under the 145/5 imbalance.
- Paired F1/accuracy differences with bootstrap 95% intervals.
- Decision latency.
- No retrieval metrics.

The severe imbalance must be stated alongside every number. Stale is primarily
a queue-utility outcome, not proof of semantic understanding.

### Missing reproduction

MRE reporting requires both:

- At least 30 adjudicated positives: 55 are present.
- At least 30 adjudicated true negatives: 30 are present.

Report:

- Confusion matrix.
- Precision, recall, and F1 with Wilson 95% intervals.
- Paired differences with bootstrap 95% intervals.
- Calibration/Brier score only for probabilistic outputs.
- Claim-level unsupported-rate audit only for generated drafts that pass all
  gates.

MRE remains a secondary operator judgment under design §8. It cannot support
a headline maintainer-accuracy claim.

### Duplicate

No model scoring. Report only the completed gold census:

- 3 positives.
- 14 direction-checked canonical hubs.
- 0 proposals eligible for the ≥90% precision rule.

### Cost and operational metrics

For every evaluated system:

- Total and per-eligible-issue model spend.
- Provider, model ID, embedding/model dimensions, and token counts.
- p50 decision latency.
- Failure/timeout/budget-exhaustion rate.
- Retrieval coverage, cost, and censored out-of-window misses.

The spend cap must be fixed before scoring and cannot be raised retroactively.
A scored nonzero cap requires measured unit pricing. No successful paid
provider work has occurred.

## 5. Human evaluation and regression controls

- Preserve the committed single-rater gold record.
- Needed maintainer time-saved claims remain prohibited; agreement is not
  acceptance.
- A future maintainer pilot needs its own pre-declared protocol and timer
  logs.
- CI should run fast deterministic unit checks and metric-library tests on
  synthetic fixtures.
- CI must not run provider-backed scoring or mutate the frozen gold.
- Full gold scoring is a deliberate local or workflow run with locked
  dependencies and recorded model/config versions.

## 6. Unblock conditions before paid implementation or scoring

Paid Slice 2 implementation and scoring remain blocked until all are true:

1. OpenAI is reserved for final validation; before that final stage, activate
   OpenAI billing/account and run a successful minimal cost/latency spike.
2. Updated provider training/retention ADR for real issue text.
3. Recorded nonzero pre-scoring spend cap with measured unit pricing.
4. Completed MRE denominators: 55 positives and 30 negatives.
5. A Slice 2 scope restricted to stale and secondary MRE evaluation.
6. Completed issue-level creation-time test and title/body provenance gates in
   `app/eval_inputs.py` and `tests/test_eval_inputs.py`.

No duplicate scoring, shadow deployment, outreach, maintainer pilot, or write
can be justified by this plan.
