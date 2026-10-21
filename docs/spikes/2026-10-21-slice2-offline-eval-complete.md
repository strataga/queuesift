# Slice 2 offline evaluation: completion record (non-paid phase)

Date: 2026-10-21. This record closes the non-paid Slice 2 offline-evaluation
work. Everything below ran with zero paid provider calls and zero writes to
any upstream repository. OpenAI is postponed until final validation.

## Frozen inputs and gold (unchanged)

- Cohort: `evals/manifests/uv-backlog-sweep-2026-10-20.json` (150 issues).
- Gold: `evals/adjudication/uv-backlog-gold-2026-10-20.json`.
- Duplicate: 3 positives / 30 required — FAIL; 14 direction-checked canonical
  hubs, not duplicate positives.
- Missing reproduction: 55 positives and 30 adjudicated negatives —
  secondary-judgment PASS only; no headline maintainer-accuracy claim.
- Stale: 145 positives of 150 — PASS.
- Creation-time leakage test passes: 150/150 inputs load, 27 renamed titles
  recovered from provenance, 0 observed body edits.

## Qualified preliminary scoring

Report:
`evals/reports/uv-qualified-baselines-2026-10-21.json`

| Task | System | Accuracy [95% CI] | F1 | Paired F1 vs deterministic [95% CI] |
|---|---:|---:|---:|---:|
| Stale (150) | Age rule | 0.9667 [0.9243, 0.9857] | 0.9831 | — |
| Stale (150) | Local semantic | 0.6067 [0.5268, 0.6812] | 0.7511 | -0.2320 [-0.2980, -0.1733] |
| MRE secondary (85) | Template rule | 0.6353 [0.5292, 0.7297] | 0.7770 | — |
| MRE secondary (85) | Local semantic | 0.4471 [0.3459, 0.5528] | 0.2769 | -0.5001 [-0.6513, -0.3409] |

The stale age rule is strong because the cohort is overwhelmingly old; it is
a queue-utility baseline, not evidence of semantic understanding.

## Threshold sweep (descriptive)

Report:
`evals/reports/uv-threshold-sweep-2026-10-21.json`.
Full 7-point grid table lives in
`docs/spikes/2026-10-21-threshold-sweep-results.md`. No threshold was adopted
and no system was changed. Staged retrieval validation: 149/150 queries have
older corpus available at top-3, with 0 timestamp violations.

## Drafter spot-check

Report:
`evals/reports/uv-draft-spot-check-2026-10-21.json`.
5/5 local `qwen2.5:7b` drafts for the first 5 MRE positives passed
citation/request/reply gates (13,159 ms total). No draft was sent anywhere.

## Scaffolding completed without live calls

- Jev battery adapter (`app/jev.py`, typesafe-sdk 0.7.5 pinned): fixed
  stale/MRE questions, creation-time state, injected-runner tests; live
  runner refuses to run while paid scoring is blocked.
- Injection suite: hostile citations fail the claim gates; persistent
  citation violations raise after two attempts.
- Brier score implemented for future probabilistic outputs only.

## Explicitly not done / still blocked

- No OpenAI use of any kind (postponed until final validation).
- No paid provider scoring ($0.00 cap in force).
- No duplicate scoring (gold failed the 30-positive minimum).
- No threshold, weight, or prompt tuning on gold.
- No shadow deployment, maintainer outreach, pilot, or writes.
- Second-rater adjudication and maintainer-accepted time-saved claims remain
  out of scope for this phase.
