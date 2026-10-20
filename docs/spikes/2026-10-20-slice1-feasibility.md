# Slice 1 feasibility findings (partial gate)

Date: 2026-10-20. Source: live 90-day backfill of `langchain-ai/langchain`
(created on/after 2026-07-22) via QueueSift's own backfill tooling, plus the
Jev, OpenAI, and Ollama spikes. Raw issue text stays in the local gitignored
database only; committed artifacts are counts, manifests, and hashes.

## Backfill result

- 661 issues and 6,408 timeline events stored in 683 GitHub requests.
- Wall time 6m40s serial (one timeline request per issue dominates). A
  checkpointed/concurrent production sync is still Slice 1 work; this run is
  the feasibility corpus, not the final ingestor.
- Eligible template issues (GitHub type Bug/Feature): 412 of 661
  (337 Bug, 75 Feature), about 32 per week. Total creation volume is about
  51 per week, consistent with earlier search measurement.

## Actor inventory (important incumbent finding)

- Bot actors: `github-actions[bot]` (1,303 events),
  `langchain-oss-automated-triage[bot]` (541 events on 271 issues),
  `open-swe[bot]`, `coderabbitai[bot]`, `cursor[bot]`, `langsmith-fleet[bot]`.
- The automated-triage bot's observed role is narrow: it comments and closes
  issues that have no GitHub issue type as programmatic submissions, pointing
  reporters to the web templates. Of 249 no-type issues, 239 are closed
  `not_planned`. QueueSift correctly excludes this population; it is already
  handled deterministically by the incumbent.
- Maintainer association is only present on a minority of timeline rows
  (66 COLLABORATOR and 4 MEMBER events exposed an association; most timeline
  events expose none). Four maintainer logins were identified that way.
  Maintainer attribution for gold construction therefore needs a curated
  allowlist (for example from repository collaborators/CODEOWNERS and manual
  review) before Slice 2 adjudication; association alone undercounts humans.

## Semantic-class prevalence (the hard finding)

Across the full 90 days, and inside the declared F1 creation cohort
(145 eligible issues created 2026-08-24..2026-09-20):

- Closed with `state_reason=duplicate`: 4 in 90 days; 2 inside F1.
  `marked_as_duplicate` events likewise cover 2 F1 issues.
- Deterministically missing reproduction (Slice 0 rule): 5 of 337 Bug issues
  in 90 days. The required template fields are doing their job.
- Final workflow labels are effectively unused by humans in this window:
  `external` appears on 653 issues (workflow-applied), `investigate` on 1,
  and `waiting-on-author` / `unable-to-reproduce` / `reproduced` on 0.
- Package declared "unsure": 19 eligible issues in 90 days (9 inside F1);
  eligible with no declared package: 11 (2 inside F1).
- Declared package label missing from final labels: 18 issues in 90 days.
  Only 1 issue shows a recognised-maintainer label change more than five
  minutes after creation under the current actor-identification method.
- First substantive recognised-maintainer action: median 29.0 hours across
  151 issues where the actor could be identified. Treat as a lower-bound
  sample, not a queue-wide baseline.
- No `edited` timeline events were returned for these issues. That supports,
  but does not prove, creation-body stability; live `body_at_first_seen`
  capture remains the trustworthy path.

Consequence: several headline semantic classes are too sparse for the
design's minimum-30-positives rule on F1 — duplicates, missing information,
and label corrections included. Under §8/§11 they are descriptive only unless
manual adjudication of full threads uncovers materially more positives than
label/event proxies show. Enlarging F1 by the one permitted preceding 28 days
would still leave duplicates in single digits at the observed rate.

## Corpus and cost dry run

- 90 days of titles+bodies: 2,900,693 characters, about 725k tokens by the
  chars/4 planning estimate. At OpenAI `text-embedding-3-small` ($0.02/1M,
  verified 2026-10-20) embedding that text would cost about $0.015; a
  12-month issue corpus at the same rate is only a few cents. Dollar cost is
  not the corpus constraint; request count, chunk quality, and evaluation
  denominators are.
- Local `nomic-embed-text` embedded 100 real backfilled texts (truncated to
  2,000 characters) in 4.7 seconds; naive extrapolation to all 661 issues is
  about 31 seconds. Full-body/chunked timing must be re-measured when the
  indexer exists.
- Repository sizes reported by GitHub (whole git repositories, not text
  volume): langchain about 614 MB, docs about 1.17 GB. Code/docs text-token
  volume is still UNCONFIRMED until the clones are chunked; do not quote a
  code-corpus cost from repository size.

## Artifacts produced

- Taxonomy snapshot: `evals/taxonomy/langchain-labels-2026-10-20.json`
  (75 labels with family mapping).
- F1 cohort manifest: `evals/manifests/f1-cohort-2026-10-20.json`
  (145 members, IDs and body hashes only, declared before any system output).
- Retention decision: `docs/adr/0001-provider-data-retention.md`.
- Domain language: `GLOSSARY.md`.

## Gate assessment (Slice 1 feasibility gate, design §14)

**PASS parts:** working Jev inference; working local draft/embedding
provider; 90-day backfill and actor inventory completed; taxonomy and F1
cohort declared; provider-retention ADR recorded; embedding dollar cost is
negligible under either provider.

**BLOCKERS / re-scope triggers:**

1. OpenAI billing remains inactive, so the approved OpenAI evaluation arm
   cannot run. Local results cannot substitute for it in reporting.
2. Duplicate, missing-information, and label-correction positives are too
   sparse on F1 for pass/fail verdicts under the minimum-30 rule. Slice 2
   needs either thread-level manual adjudication showing materially more
   positives, an enlarged/re-scoped evaluation centred on denser outcomes
   (for example evidence-brief usefulness, package-unsure routing, and
   shadow agreement on maintainer comment/close behaviour), or the KB4
   stop/switch decision. Do not lower the bar silently.
3. Maintainer attribution needs a curated allowlist before gold is built;
   timeline associations alone miss most human actions.
4. Outreach must respect the incumbent policy visible in the bot's comments:
   programmatic issue submission is not allowed. Any genuine contribution
   preceding outreach must be human-submitted through the web templates.

Next concrete step: finish the actor allowlist and manually adjudicate a
bounded F1 sample to test whether thread-level positives change blocker 2,
before building Slice 2 model plumbing.
