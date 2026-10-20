# Slice 1b evidence: uv backlog cohort build

Date: 2026-10-20. Cohort file:
`evals/manifests/uv-backlog-sweep-2026-10-20.json`; local event database is
the gitignored `queuesift-uv-backlog.db`.

## Completed sample

Command:

```sh
export GITHUB_TOKEN="$(gh auth token)"
uv run queuesift \
  --repo astral-sh/uv \
  --uv-backlog-sample 150 \
  --uv-backlog-db queuesift-uv-backlog.db \
  --uv-backlog-manifest evals/manifests/uv-backlog-sweep-2026-10-20.json
```

Observed corpus:

- 150 stored backlog members.
- 150 stored issues and 4,196 stored timeline events.
- 3 current-`duplicate`-label anchors.
- 50 current-`needs-mre`-label signals.
- 97 additional oldest eligible open issues.
- Oldest member creation date: `2023-11-02T19:12:01Z`.
- Top timeline categories: 1,466 comments, 1,283 subscriptions, 470
  cross-references, 269 mentions, and 22 explicit `marked_as_duplicate`
  events.

Selection order was deterministic:

1. Current duplicate labels, oldest first.
2. Current `needs-mre` labels, oldest first, capped at 50.
3. Oldest eligible open issues.
4. Excluded internal, bot-policy, tracking/epic, security, and
   maintainer-follow-up labels.

## Gold follow-up

Gold adjudication is now complete in
`evals/adjudication/uv-backlog-gold-2026-10-20.json` and summarized in
`docs/spikes/2026-10-20-uv-backlog-gold-results.md`: duplicate 3/30 (fail),
missing reproduction 54/30 (secondary judgment only), and stale 145/150
(pass).
