# QueueSift

Measured first-pass triage for GitHub Issues. Deterministic code preserves
template-declared metadata; typed decisions handle semantic triage; humans
authorise every write. Design: `docs/superpowers/specs/2026-10-19-support-triage-design.md`.
Tracker spec: https://github.com/strataga/queuesift/issues/1

## Status

Non-paid Slice 2 offline evaluation is complete on the frozen 150-issue
`astral-sh/uv` backlog cohort; see
`docs/spikes/2026-10-21-slice2-offline-eval-complete.md` and
`evals/reports/README.md`. Shadow mode only — no GitHub writes anywhere.
Local Ollama models are used behind the provider interface while OpenAI is
postponed until final validation; local results are always labelled with
their actual provider/model and are never reported as OpenAI results.

## Run locally (uv, project-local environment)

```sh
uv sync --dev
uv run pytest
uv run queuesift --repo langchain-ai/langchain --issue 41348
uv run queuesift --check-providers   # requires local Ollama serving both models
uv run uvicorn app.main:app --port 8000
curl http://localhost:8000/healthz
```

Or with Postgres via Docker Compose:

```sh
docker compose up --build
curl http://localhost:8000/healthz
```

## Configuration

Copy `.env.example` to `.env.local` for local overrides. Never commit real keys;
`.env.local` is gitignored. Slice 0 needs no model keys. Local provider defaults
are `LLM_PROVIDER=ollama`, `DRAFT_MODEL=qwen2.5:7b`, and
`EMBED_MODEL=nomic-embed-text` (768 dimensions, normalized for cosine search).
Switching to OpenAI embeddings later requires re-embedding the corpus: vector
spaces from different models must never be mixed in one index.
