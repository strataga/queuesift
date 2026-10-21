# Narrow drafter spot-check: 2026-10-21 run

Command:

```sh
uv run queuesift \
  --repo astral-sh/uv \
  --uv-backlog-db queuesift-uv-backlog.db \
  --draft-spot-check 5 \
  --draft-report evals/reports/uv-draft-spot-check-2026-10-21.json
```

Report:
`evals/reports/uv-draft-spot-check-2026-10-21.json`

## Scope and gates

- Sample: first 5 MRE positives by issue number (2059, 2138, 2253, 2670,
  2828). Spot-check only; not an evaluation claim.
- Evidence per draft: creation title, bounded creation body, and one
  deterministic template finding. No future state, labels, or timeline.
- Gates: citations cite only supplied chunk IDs; `requested_info` nonempty;
  reply nonempty.
- Provider: local Ollama `qwen2.5:7b`, labelled as such. No OpenAI use, paid
  calls, tuning on gold, shadow deployment, outreach, pilot work, or writes.

## Iteration note

The first instruction produced citations wrapped in brackets (`[E-body]`),
which the citation gate rejects; all 5 drafts failed validation. The
instruction was tightened to require bare IDs exactly as given. This is a
prompt-format fix, not tuning on gold outcomes: the gate definition did not
change.

## Results

- 5 of 5 drafts passed all gates after the format fix.
- Total draft latency: 13,159 ms across 5 drafts (1,864–3,659 ms each).
- Every passing draft requested a minimal reproduction plus the relevant
  diagnostic artifact (error text, command, or logs).
- Replies are maintainer-request drafts only; none were sent anywhere.
