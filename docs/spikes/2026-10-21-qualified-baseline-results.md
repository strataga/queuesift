# Qualified preliminary baselines: 2026-10-21 run

Command:

```sh
uv run queuesift \
  --repo astral-sh/uv \
  --uv-backlog-db queuesift-uv-backlog.db \
  --run-qualified-baselines \
  --eval-report evals/reports/uv-qualified-baselines-2026-10-21.json
```

Report:
`evals/reports/uv-qualified-baselines-2026-10-21.json`

## Scope and gates

- Stale: all 150 frozen members; 145 positive, 5 negative.
- Missing reproduction: 85 evaluated members; 55 positive, 30 negative; 65
  unknown members excluded.
- Duplicate: not scored; only the completed direction-checked census is used.
- No OpenAI use, paid calls, tuning, shadow deployment, outreach, pilot work,
  or writes.
- Local embeddings are labelled `ollama` / `nomic-embed-text` / 768
  dimensions; total local embedding latency was 8,896 ms across both tasks.

## Results

| Task | System | Accuracy [95% CI] | F1 | Paired F1 vs deterministic [95% CI] |
|---|---:|---:|---:|---:|
| Stale | Age rule | 0.9667 [0.9243, 0.9857] | 0.9831 | — |
| Stale | Local semantic | 0.6067 [0.5268, 0.6812] | 0.7511 | -0.2320 [-0.2980, -0.1733] |
| MRE secondary | Template rule | 0.6353 [0.5292, 0.7297] | 0.7770 | — |
| MRE secondary | Local semantic | 0.4471 [0.3459, 0.5528] | 0.2769 | -0.5001 [-0.6513, -0.3409] |

Paired accuracy differences were -0.3600 [-0.4467, -0.2800] for stale and
-0.1882 [-0.3765, 0.0118] for MRE. The stale age rule is strong because the
frozen cohort is overwhelmingly old; that score is a queue-utility baseline,
not evidence of semantic understanding. MRE remains a secondary operator
judgment, not headline maintainer accuracy.
