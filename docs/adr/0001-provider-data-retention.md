# ADR-0001: Provider data handling and retention

Date: 2026-10-20. Status: accepted for Slice 1 development; revisit before
Slice 3 shadow deployment and before any paid pilot.

## Context

QueueSift processes public GitHub issue text that can still contain pasted
secrets or personal data. Three model paths exist: local Ollama (temporary),
OpenAI (approved evaluation target, billing inactive), and TypeSafe Jev
(remote decision API).

## Verified provider positions (official sources, checked 2026-10-20)

- OpenAI API data is not used to train or improve models unless the customer
  explicitly opts in. Abuse-monitoring logs may contain prompts/responses and
  are retained up to 30 days by default; Zero Data Retention and Modified
  Abuse Monitoring require prior approval. Sources:
  https://developers.openai.com/api/docs/guides/your-data and
  https://openai.com/policies/how-your-data-is-used-to-improve-model-performance/
- TypeSafe states it will not train or fine tune models on prompts or other
  Input. Its DPA limits processing to documented instructions and prohibits
  sale/share of customer personal data. Its privacy policy retains personal
  data "for as long as reasonably necessary" (no fixed default period found);
  zero data retention is an enterprise option via sales, not an account
  default assumed here. Sources: https://typesafe.ai/legal/privacy-policy,
  https://typesafe.ai/legal/data-processing, https://docs.typesafe.ai/legal
- Ollama local inference sends no issue text to a third party from QueueSift
  code. Jev calls remain remote even when drafting/embeddings are local.

## Decision

1. Only redacted, size-capped text may leave the deployment to any provider.
   Redaction is best-effort and is never described as a guarantee.
2. While OpenAI billing is inactive, local Ollama is the development provider.
   Local results are labelled with actual provider/model in every record and
   report; they are not OpenAI evidence.
3. Jev may receive lean creation-time state for feasibility work because its
   no-training commitment is verified, but API keys, secrets, email addresses,
   and unrelated comment threads are excluded by the redactor and state caps.
   Because no fixed default retention period is published, scaled or customer
   use requires either enterprise zero-retention confirmation or an explicit
   owner acceptance recorded in a superseding ADR.
4. OpenAI may be used once billing is active under the default API no-training
   posture above; `store=false` style stateless calls are preferred where the
   endpoint supports them, and ZDR eligibility is not assumed.
5. Hosted tracing, if enabled later, receives IDs, versions, probabilities,
   token counts, and citation IDs only — not raw issue or draft text — unless
   self-hosted inside the deployment boundary.
6. Secrets live only in environment/secret-manager storage or gitignored
   `.env.local`; never in Git, issues, logs, traces, or evaluation artifacts.

## Consequences

Slice 1 feasibility can proceed (local drafting/embeddings, lean Jev spikes).
Slice 2 evaluated comparisons must state exactly which provider produced each
arm. Any customer pilot needs a fresh review of retention terms as they exist
at that date; this ADR records only what was verified on 2026-10-20.

## Slice 2 input-gate update — 2026-10-20

Status: accepted for no-provider Slice 2 input, provenance, rule, metric, and
synthetic-test work. It does not authorize provider-backed scoring, shadow
deployment, outreach, a maintainer pilot, or writes.

- OpenAI billing remained inactive in the 2026-10-20 check and was
  re-verified inactive on 2026-10-21 with one synthetic billing probe.
  Billing activation is the remaining blocker for any scored evaluation run.
- Paid provider spend is capped at `$0.00` per eligible issue and `$0.00` per
  day in
  `evals/cost/uv-backlog-pre-scoring-spend-cap-2026-10-20.json`.
- No new provider call, draft, embedding, trace payload, or paid evaluation
  was made in this update.
- The OpenAI no-training default, TypeSafe processing limits, local-Ollama
  boundary, secret-handling rules, and hosted-tracing limits above remain
  unchanged.
