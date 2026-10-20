# QueueSift

Measured first-pass triage for GitHub Issues. Deterministic code preserves
template-declared metadata; typed decisions handle semantic triage; humans
authorise every write. Design: `docs/superpowers/specs/2026-10-19-support-triage-design.md`.
Tracker spec: https://github.com/strataga/queuesift/issues/1

## Status

Slice 0 walking skeleton: template parser, deterministic proposal, persistence,
static digest, and health endpoint. Shadow mode only — no GitHub writes anywhere.

## Run locally (uv, project-local environment)

```sh
uv sync --dev
uv run pytest
uv run queuesift --repo langchain-ai/langchain --issue 41348
uv run uvicorn app.main:app --port 8000
curl http://localhost:8000/healthz
```

Or with Postgres via Docker Compose:

```sh
docker compose up --build
curl http://localhost:8000/healthz
```

## Configuration

Copy `.env.example` to `.env` for local overrides. Never commit real keys.
Slice 0 needs no model keys; `GITHUB_TOKEN` only raises read rate limits.
