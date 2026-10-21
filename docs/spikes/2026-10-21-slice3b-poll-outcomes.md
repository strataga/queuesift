# Slice 3b — live poll, outcome snapshots, digest artifact (done 2026-10-21)

## What was built

- `GET /issues?state=all&sort=updated&since=` incremental listing, newest
  first, pull requests skipped without spending the poll budget
  (`app/backfill.py::iter_updated_since`).
- `app/poll.py::run_poll`: new numbers get full detail+timeline; stored
  numbers in the window get a full refresh; deterministic proposals stored
  for both; every pass recorded in `poll_runs` (repo, ran_at, since, counts,
  requests). Default bound 30 issues per pass.
- `app/outcomes.py::score_outcomes`: descriptive snapshot per stored issue —
  current state/labels plus maintainer-activity flag from stored timelines
  (TIER-A login or OWNER/MEMBER/COLLABORATOR, substantive event, not a bot).
  Reports what maintainers did, never whether the proposal was right.
- `app/outcomes.py::write_digest_artifact`: daily Markdown digest grouped by
  route with `[state, maintainer-active|no-maintainer-action-yet]` flags.
- CLI: `--poll [--poll-since] [--poll-limit]`, `--score-outcomes
  [--outcomes-report]`, `--write-digest [--digest-date] [--digest-path]`,
  all on `--shadow-db` (default `queuesift-shadow-poll.db`, gitignored).
  The frozen uv-backlog cohort DB is never the poll target.

## Live evidence (read-only, 2026-10-21)

`--poll --poll-limit 2` on `astral-sh/uv`: 2 new issues, 5 requests, both
joined to maintainer-active outcomes, digest artifact rendered with real
titles and links. No writes to GitHub, no model calls.

## What 3b deliberately leaves out

- No agreement scoring vs proposals (that is the §11.2 7-day analysis, not a
  per-pass claim); no auto-class claims; no outreach packet.
- No scheduler/daemon: each pass is one CLI invocation; 7-day cadence is
  manual until 3c deploy.
- No GitHub OAuth yet (single local operator; auth arrives with approval
  actions in Slice 4).
