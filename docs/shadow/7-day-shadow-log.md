# 7-day shadow run log (`astral-sh/uv`, §11.2)

Pass bar reminder: 7 consecutive days of proposals within 1 hour of
creation/first-seen, ≥70% agreement with later maintainer actuals on sampled
decisions with known outcomes (agreement, not acceptance, never time saved),
zero operator-judged harmful/spammy proposals in the final week, zero public
writes attempted. Sync gaps and model failures are reported, not hidden.

Daily recipe (each day, until a long-lived host takes over):

```bash
docker compose up -d  # or the cloud host when it exists
docker compose exec -T app sh -c \
  'queuesift --repo astral-sh/uv --poll --poll-limit 30 --database-url "$DATABASE_URL"'
docker compose exec -T app sh -c \
  'queuesift --repo astral-sh/uv --score-outcomes --database-url "$DATABASE_URL" \
   --outcomes-report evals/reports/uv-outcome-snapshot.json'
docker compose exec -T app sh -c \
  'queuesift --repo astral-sh/uv --write-digest --database-url "$DATABASE_URL"'
```

## Day 1 — 2026-10-21 (local Compose Postgres)

- Deploy: `docker compose up --build` green; `/healthz`, `/`, `/digest`,
  `/evals`, and one frozen report all 200, report served from inside the image.
- Poll (limit 2, read-only): 2 new issues, 0 refreshed, 5 requests.
- Stored: issues=2, proposals=2, poll_runs=1 (verified in Postgres; digest
  serves both issue links).
- Backup rehearsal: `pg_dump` to `/tmp/qs-backup-2026-10-21.sql`; restored
  into `queuesift_restore`; counts matched 2/2/1; scratch database dropped.
- No writes to GitHub, no model calls, no outreach. Clock started; day 2 due
  2026-10-22.
