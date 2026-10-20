# Spike: OpenAI key verification

Date: 2026-10-20. Throwaway probe (not kept in the application).

## Result

- Secrets are kept in repo-root `.env.local`, which is now gitignored
  (`.env` / `.env.*`, except `.env.example`) and verified untracked.
- The OpenAI key reached the API but the first embeddings call failed before
  drafting: `429 billing_not_active` — "Your account is not active, please
  check your billing details on our website."
- Therefore neither embeddings nor structured drafting is verified yet.
  This is an account/billing activation issue, not evidence of a bad key format.

## Required owner action

Activate API billing or credits for the OpenAI account/project that owns the
key, then re-run the spike: one `text-embedding-3-small` call and one small
JSON-mode draft from two cited chunks, recording model, tokens, latency, and
unit cost. The provider training/retention ADR is still required before real
issue text is sent at scale.
