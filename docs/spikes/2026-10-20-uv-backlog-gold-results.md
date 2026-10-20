# Slice 1b gold verdict: uv backlog sweep

Date: 2026-10-20. Cohort: `evals/manifests/uv-backlog-sweep-2026-10-20.json`
(150 issues). Adjudication:
`evals/adjudication/uv-backlog-gold-2026-10-20.json`. Rules:
`docs/spikes/2026-10-20-uv-backlog-gold-rules.md`. Actors:
`evals/actors/uv-actors-2026-10-20.json`.

## Verdicts under the unchanged 30-positive rule

- Duplicate: **3 positives / 30 required — FAIL**.
  Candidate census covered all 3 current duplicate labels and all 14
  pre-freeze `marked_as_duplicate` issues. Direction-checked GraphQL evidence
  showed the 14 marks nominated other issues as duplicates of the sampled
  issues; those sampled issues are canonical hubs, not duplicate positives.
  A cohort-wide Tier A duplicate-language scan found no additional positives.
- Missing reproduction: **50 positives / 30 required — PASS as a secondary
  operator judgment only**. All 50 current `needs-mre` members were reviewed.
  This does not authorize a headline missing-reproduction accuracy claim under
  design §8.
- Stale: **145 positives / 30 required — PASS**. The deterministic rule found
  145 members created before 2026-04-23 with no accepted-maintainer substantive
  action through the freeze. Five members had recent maintainer engagement:
  1235, 1442, 1566, 3271, and 3704.

## Slice 2 consequence

Slice 2 may use only the qualified stale and secondary missing-reproduction
outcomes. No duplicate pass/fail, retrieval, precision/recall, or headline
model claim may proceed on this gold set. OpenAI billing is also still
inactive, so no approved evaluation-arm scoring can run yet.
