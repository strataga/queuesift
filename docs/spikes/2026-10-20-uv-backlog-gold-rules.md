# uv backlog gold rules (Slice 1b)

Cohort: `evals/manifests/uv-backlog-sweep-2026-10-20.json` (150 issues).
Evidence freeze: `2026-10-20T00:00:00Z`.
Actor allowlist: `evals/actors/uv-actors-2026-10-20.json`.
Implemented checks: `app/gold.py`; behavior tests: `tests/test_gold.py`.

These rules adapt design §8.1 to the backlog-only sweep authorized by design
§12. They do not lower the 30-adjudicated-positive bar.

## Actor rule

- Tier A and Tier B are accepted automatically.
- A non-bot actor with an `OWNER`, `MEMBER`, or `COLLABORATOR` association in
  the same event/comment is also accepted.
- Automation accounts and `[bot]` actors are never accepted.
- Tier C contributors are candidates only. They need both an explicitly worded
  request/link and operator review; their labels or marks alone are not gold.
- Unknown actors never create gold automatically.

## Duplicate positive

An issue is duplicate-positive when both conditions hold before the freeze:

1. Either:
   - a Tier A/B maintainer marked this issue as the duplicate in a
     direction-checked GitHub duplicate event;
   - a Tier A/B maintainer explicitly identified another issue as canonical for
     this issue in text; or
   - a current `duplicate` label was applied by a Tier A maintainer.
2. The operator verified that the identified canonical issue is the same
   underlying problem or request, rather than merely related work.

A mark is not enough when its target is missing, deleted, ambiguous, or only
adjacent. Direction matters: an event in which another issue was marked as a
duplicate of the sampled issue makes the sampled issue a canonical hub, not a
duplicate-positive. Multiple canonical targets are retained when maintainers marked the
same issue more than once.

## Missing-reproduction positive

An issue is missing-reproduction-positive when both conditions hold before the
freeze:

1. Either:
   - it carries `needs-mre` at the freeze after Tier A/B triage;
   - a Tier A/B maintainer explicitly requested a reproduction, logs,
     environment details, configuration, setup steps, or another missing
     diagnostic artifact; or
   - a Tier C contributor made that explicit request and also applied
     `needs-mre` during triage.
2. The operator reviewed the surrounding thread and found no reason to reject
   the maintainer judgment.

A fulfilled follow-up does not erase the positive: the gold question is whether
maintainer triage needed more evidence, not whether the reporter eventually
supplied it.

Under design §8.1, these are operator-adjudicated secondary judgments, not
headline maintainer-accuracy gold. A 30-positive MRE count therefore permits a
secondary Slice 2 judgment only; it does not authorize a headline
missing-reproduction accuracy claim.

## Stale positive

An issue is stale-positive when both conditions hold:

1. It was created before `2026-04-23T00:00:00Z`, exactly 180 days before the
   freeze.
2. No accepted maintainer performed a substantive action from that cutoff
   through the freeze.

Substantive actions are direct comments, labels, assignments, milestones,
closures, reopenings, and renames. Subscriptions, references, mentions, and
cross-issue chatter do not interrupt staleness. Non-maintainer comments do not
interrupt staleness.

## Verdict

Each class passes only with at least 30 adjudicated positives. A class below
30 is descriptive only and cannot support an offline Slice 2 pass/fail claim
for that headline task.
