# Slice 2 input gates: creation-time checks, spend cap, and retention

Date: 2026-10-20. No provider-backed scoring was performed.

## Creation-time leakage checks

Implementation: `app/eval_inputs.py`. Tests: `tests/test_eval_inputs.py`.

The loader proves the following by construction:

- It queries only these issue-table columns:
  `repo`, `number`, `github_id`, `title`, `body`, `author`,
  `author_association`, and `created_at`.
- It does not read `labels_json`, `state`, `state_reason`, `closed_at`, or any
  timeline/event table when building a model input.
- Its Pydantic input model forbids extra fields.
- Synthetic tests poison future labels, closure metadata, and later timeline
  signals and verify that none appears in the produced input.
- A missing or unknown issue number fails instead of returning a partial
  input.

Provenance repairs are kept outside the model input:

- The loader rejects any scored issue with an observed `edited` timeline
  event until its creation body is separately recovered.
- The loader rejects any scored issue with a pre-freeze `renamed` timeline
  event unless the committed original-title map supplies the earliest title.
- Original titles are in
  `evals/provenance/uv-backlog-original-titles-2026-10-20.json`.
- These timeline checks are provenance gates, not predictive features.

Observed frozen-cohort validation:

- 150/150 manifest members loaded.
- 27/27 renamed members covered by original-title provenance.
- 0 observed `edited` timeline events.
- The local stored bodies are therefore accepted as creation bodies only
  because no edit event is observed; this is not a cryptographic guarantee of
  an unrecorded text change.

## Pre-scoring spend cap

Cap record:
`evals/cost/uv-backlog-pre-scoring-spend-cap-2026-10-20.json`

- Paid provider spend is capped at `$0.00` per eligible issue and `$0.00` per
  day until billing activation and measured unit costs are recorded.
- This permits offline input, provenance, rule, metric-library, and synthetic
  test work.
- It prohibits paid provider scoring, including OpenAI and TypeSafe scoring
  calls.
- The cap cannot be raised retroactively to pass an evaluation.

## Provider retention update

Retention update is recorded in `docs/adr/0001-provider-data-retention.md`.
OpenAI billing remains the blocking account issue; no scored run, paid call,
draft, embedding, shadow deployment, outreach, pilot, or write may use this
input work as authorization.
