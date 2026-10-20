# Switch verdict: KB4 invoked — LangChain to uv backlog triage

Date: 2026-10-20. The one permitted design switch (§12) is invoked on the
semantic-sparsity variant of KB4: LangChain's headline semantic classes could
not support the design's minimum-30 pass/fail rule, even after thread-level
adjudication. LangChain results remain reported as a completed
negative/mixed result; nothing is deleted or lowered.

## uv re-measurement (this probe)

- Templates: bug reports require Summary, Platform, Version; feature requests
  require Summary; questions are a separate template; blank issues remain
  allowed. Template labels are applied (bug/enhancement/question), but GitHub
  issue types are effectively unused (249 of 250 backfilled issues had none).
  QueueSift's parser must read uv forms, not LangChain Package checkboxes.
- Issue triage automation already exists and is sophisticated:
  `issue-triage.yml` classifies type (including duplicate precedence rules),
  builds a related-issues README handoff in uv-dev, and drafts maintainer
  replies; operator-owned only, no public writes were observed from this
  probe. Public write and internal-triage duplication remain out of scope.
- 90-day backfill (2026-07-22 to 2026-10-20, separate database file
  `queuesift-uv.db`, gitignored): 250 issues, 2,087 timeline events, 108
  requests with resume-skipping.
  - Closed duplicate state_reason: 13 (vs 4 on LangChain in 90 days).
    `marked_as_duplicate` events: 7 distinct issues.
  - `needs-mre` currently on 10 recent issues; open backlog holds 82.
  - Active human maintainers visible with associations (zanieb, charliermarsh,
    woodruffw, konstin, zsol and others); automation bots present
    (astral-automations-bot, zaniebot) but do not dominate the queue the way
    LangChain's policy bot dominates no-type traffic.
- Open backlog: 2,359 open issues, median age 531 days (p90 792), 1,812 not
  updated in 180 days, 1,497 distinct authors. Currently open labelled:
  enhancement 693, question 422, bug 401, needs-decision 150, wish 112,
  needs-mre 82, needs-design 79.
- Taxonomy snapshot: `evals/taxonomy/uv-labels-2026-10-20.json` (87 labels).

## Decision

Switch the build target to `astral-sh/uv` in **backlog scope only**: stale and
duplicate sweep over the 2,359-issue open backlog, where duplicates and
unresolved needs would actually be evaluable. New-issue type/duplicate
classification is already occupied by the repo's own triage workflow and is
not the battleground. Frozen cohorts, thresholds, taxonomy, gold rules, and
corpus windows restart on uv before any evaluated claim; LangChain's negative
result stands as reported.

## Remaining switches

None. This was the one permitted switch. A second switch is not allowed;
failure on uv ends Project B and returns the builder to Candidate A.

## Immediate next work

1. Update §12 status and the board to name uv backlog as the target;
   LangChain issues stay referenced as completed investigation.
2. Define the uv backlog evaluation cohort (aged-open sample plus closed
   duplicate anchors), its gold rules, and its taxonomy freeze; F1's
   creation-cohort method does not transfer unchanged to a sweep over
   pre-existing backlog.
3. Extend the template parser to uv forms; treat the uv internal triage
   workflow’s README handoffs as knowledge to complement, not gold to copy.
4. No LangChain results may be blended into uv scores.
