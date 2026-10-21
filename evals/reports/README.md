# QueueSift evaluation reports

Machine-readable outputs of the non-paid Slice 2 offline evaluation on the
frozen 150-issue `astral-sh/uv` backlog cohort. All runs used creation-time
inputs only, local Ollama models labelled as such, and zero paid provider
calls. Duplicate scoring was prohibited throughout.

| Report | Contents |
|---|---|
| `uv-qualified-baselines-2026-10-21.json` | Deterministic age/template baselines vs local `nomic-embed-text` semantic baselines on stale (150) and secondary MRE (85); Wilson 95% intervals and paired bootstrap differences. |
| `uv-threshold-sweep-2026-10-21.json` | Descriptive 7-point F1 sweep over the fixed semantic margin, with Wilson and paired bootstrap intervals, plus staged-retrieval timestamp validation. No threshold adopted. |
| `uv-draft-spot-check-2026-10-21.json` | Narrow local `qwen2.5:7b` missing-evidence drafts for the first 5 MRE positives with citation/request/reply gates; 5/5 passed. No draft was sent anywhere. |

Headline numbers and verdicts live in
`docs/spikes/2026-10-21-slice2-offline-eval-complete.md`. Frozen inputs:
`evals/manifests/`, `evals/adjudication/`, `evals/provenance/`.
