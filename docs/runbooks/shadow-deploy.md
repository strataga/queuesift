# Shadow deploy runbook (Slice 3c)

Local Compose deploy plus backup/restore. Last rehearsed 2026-10-21 against
the Compose Postgres with 2 polled issues, 2 proposals, 1 poll run; restore
matched the source on all three counts.

## Deploy (local)

```bash
docker compose up --build -d
curl localhost:8000/healthz   # {"status":"ok","service":"queuesift"}
curl localhost:8000/digest    # proposals grouped by route
```

The image bakes `app/` plus the frozen `evals/reports/` so `/evals` works
without a volume. No secrets are baked in: `.dockerignore` excludes `.env*`
and `*.db`. The app creates its schema at startup (lifespan `init_db`), so a
fresh volume serves an honest empty state.

Poll from inside the compose network (Mac note below):

```bash
docker compose exec -T app sh -c \
  'queuesift --repo astral-sh/uv --poll --poll-limit 30 --database-url "$DATABASE_URL"'
```

## Backup

```bash
docker compose exec -T db pg_dump -U queuesift -d queuesift -F p \
  > /tmp/qs-backup-$(date +%F).sql
```

Record the counts alongside the dump:

```bash
docker compose exec -T db psql -U queuesift -d queuesift \
  -t -c "SELECT 'issues=' || count(*) FROM issues;" \
  -t -c "SELECT 'proposals=' || count(*) FROM proposals;" \
  -t -c "SELECT 'poll_runs=' || count(*) FROM poll_runs;"
```

## Restore rehearsal

Restore into a scratch database and compare counts before trusting the dump:

```bash
docker compose exec -T db psql -U queuesift -d postgres \
  -c "CREATE DATABASE queuesift_restore;"
cat /tmp/qs-backup-<date>.sql | docker compose exec -T db \
  psql -U queuesift -d queuesift_restore -q
# re-run the three count queries against queuesift_restore and compare
docker compose exec -T db psql -U queuesift -d postgres \
  -c "DROP DATABASE queuesift_restore;"
```

## Mac local-portgres conflict

If a Mac-local Postgres already holds port 5432, the laptop cannot reach the
compose database over `localhost:5432` (connections land on the Mac server,
which has no `queuesift` role). Do not change the compose mapping for this;
reach the database from inside the compose network as above. Container IPs
are not routable from macOS, so `docker inspect` IPs will time out.

## Cloud move (not done yet)

The long-lived host is an owner decision, still open. When chosen: one small
host, this same Compose file, secrets (`GITHUB_TOKEN`, model keys when they
exist) in the host secret manager only, nightly `pg_dump` to object storage,
and the 7-day shadow log continues there. No code change is expected for the
move; this runbook is the migration plan until it happens.
