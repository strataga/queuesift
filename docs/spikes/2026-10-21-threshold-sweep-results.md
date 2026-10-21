# Threshold-sweep scoring: 2026-10-21 run

Command:

```sh
uv run queuesift \
  --repo astral-sh/uv \
  --uv-backlog-db queuesift-uv-backlog.db \
  --run-threshold-sweep \
  --sweep-report evals/reports/uv-threshold-sweep-2026-10-21.json
```

Report:
`evals/reports/uv-threshold-sweep-2026-10-21.json`

## Scope and gates

- Descriptive sweep only over the fixed local-semantic margin
  (positive-hypothesis similarity minus negative-hypothesis similarity).
- No threshold is adopted from this sweep and no system was changed by it.
- Stale: all 150 frozen members. MRE: 85 evaluated members, 65 unknown
  excluded. Duplicate: not scored.
- No OpenAI use, paid calls, tuning, shadow deployment, outreach, pilot
  work, or writes. Local embeddings labelled `ollama` / `nomic-embed-text`.
- Staged retrieval inputs were validated across the cohort: 149 of 150
  queries have older corpus available at top-3, with 0 timestamp violations.

## Sweep results (F1)

| Threshold | Stale F1 | Stale paired dF1 [95% CI] | MRE F1 | MRE paired dF1 [95% CI] |
|---|---:|---:|---:|---:|
| -0.10 | 0.9831 | +0.0000 [+0.0000, +0.0000] | 0.7857 | +0.0087 [+0.0000, +0.0286] |
| -0.05 | 0.9831 | +0.0000 [+0.0000, +0.0000] | 0.7941 | +0.0171 [-0.0115, +0.0518] |
| -0.02 | 0.9541 | -0.0290 [-0.0538, -0.0073] | 0.6316 | -0.1454 [-0.2684, -0.0271] |
| +0.00 | 0.7511 | -0.2320 [-0.2980, -0.1733] | 0.2769 | -0.5001 [-0.6513, -0.3409] |
| +0.02 | 0.3778 | -0.6053 [-0.7025, -0.5123] | 0.0357 | -0.7413 [-0.8356, -0.6275] |
| +0.05 | 0.0137 | -0.9694 [-0.9933, -0.9312] | 0.0000 | -0.7770 [-0.8435, -0.6923] |
| +0.10 | 0.0000 | -0.9831 [-0.9967, -0.9655] | 0.0000 | -0.7770 [-0.8435, -0.6923] |

Deterministic references: stale age rule F1 0.9831; MRE template rule F1
0.7770. At the most lenient thresholds the semantic margin rule converges
toward the deterministic rules; no operating threshold was selected. MRE
remains a secondary operator judgment, not headline maintainer accuracy.
