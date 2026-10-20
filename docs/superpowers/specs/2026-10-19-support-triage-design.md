# QueueSift (Project B) — Support Triage-and-Resolve: Design

- **Working name:** QueueSift (owner-confirmed 2026-10-19; search-checked, not trademark-checked)
- **Status:** Draft revision 2 for owner approval, after builder-check and critical review.
  No code is authorised by this document alone.
- **Date:** 2026-10-19 (revision 2 same day)
- **Owner / builder:** Jason (solo learner, targeting Forward Deployed Engineer roles)
- **Target queue:** `langchain-ai/langchain` GitHub Issues (owner-confirmed 2026-10-19)
- **Backup queue:** `astral-sh/uv`, only under the switch rule in §12
- **Evidence base:** `research/fde-hard-problems-moat-filter.md` §6 and §11 (Candidate B),
  `research/fde-hard-problems-20-more.md` (G01 comparison), `research/jev-ai.md` (Jev contract),
  `transcripts/clean/KpILHX2D-AA.txt` (moat definitions)

## 1. Intent and why

Build a complete, deployed semantic-triage system for one real GitHub Issues queue.
Deterministic code first extracts what the issue template already declares; typed AI
decisions then handle only the work templates cannot settle — declared-metadata mismatches,
duplicates, known issues, missing reproduction material, forum/security misroutes,
reproducibility, urgency, and evidence-backed first responses. An LLM drafts only narrow,
cited replies, and humans authorise every write. The primary purpose is FDE hiring evidence:
one embedded workflow, real data, and a measured operational result the builder can explain
end-to-end in an interview. Paid B2B inbox software is a possible later pivot to test, not a
v1 thesis; it would require fresh customer discovery and a budget holder's paid-pilot
commitment, because GitHub-queue success does not transfer automatically. The system must
prove the builder can build every essential layer of an AI product — data, retrieval,
decisions, drafting, safety, evaluation, product surface, deployment, and operations — in
staged vertical slices, without production-hardening theatre delaying the core quality proof.

One-line pitch: an AI triage nurse for GitHub Issues — it catches duplicates, missing
details, and misfiled reports before maintainers spend time on them, and humans keep the
final say.

### 1.1 Measured facts about the target queue (2026-10-19, GitHub API)

- New issues created in trailing 90 days: 651, about 50.6 per week (search count).
- Closed issues created in trailing 90 days: 405, with 100% carrying at least one label
  (search count minus `no:label` count).
- Open issues by search: 549. Repository `open_issues_count` is 664, which includes PRs.
- Default branch `master`; primary language Python; repository actively pushed.
- Blank issues are disabled. Templates: `bug-report.yml`, `feature-request.yml`,
  `privileged.yml`, `task.yml`. The template config routes community discussion to the
  LangChain Forum, documentation issues to `langchain-ai/docs`, and readers to
  docs.langchain.com and reference.langchain.com.
- **Template determinism (critical-review finding, verified 2026-10-19 by reading the
  template and workflow YAML):** issue templates set the GitHub issue `type` and initial
  intent labels (`bug`, `feature request`, `task`); bug/feature/privileged forms require
  the submitter to select one or more packages; and `auto-label-by-package.yml` parses
  that declared `Package` section on `opened`/`edited` and copies it to package labels.
  Predicting initial intent or package from the same body is therefore form parsing, not
  semantic triage, and cannot be a headline QueueSift accuracy claim. QueueSift treats
  declared type/package as deterministic input and scores only corrections, additions,
  and semantic judgments listed in §2 and §8. Maintainer-authored `task` and `privileged`
  issues are excluded from submitter-facing proposals by default because they are internal
  project-management items, not support requests.
- Label taxonomy snapshot (76 labels on page one) mixes type (`bug`, `feature`,
  `documentation`), packages and integrations (`core`, `langchain`, `openai`, `anthropic`,
  `text-splitters`, `mcp`), and workflow states (`waiting-on-author`,
  `unable-to-reproduce`, `reproduced`, `investigated` via `investigate`, `external`).
  The taxonomy is versioned at eval-freeze time (see §8); repos rename labels.
- Existing automation already present in `.github/workflows`, including
  `auto-label-by-package.yml`, `tag-external-issues.yml`, `close_unchecked_issues.yml`,
  `require_issue_link.yml`, `remove_waiting_on_author.yml`, `reopen_on_assignment.yml`,
  and `pr_labeler.yml`. The system must complement and be benchmarked against this
  installed rule base, not duplicate it blindly.
- No comments by the `dosubot` login were found (`commenter:dosubot` search returned 0).
  Other bots may still act under different logins; Day 1 includes a bot-actor inventory
  from issue timelines before any "no incumbent bot" claim is made.

Competitive honesty: Dosu already sells GitHub issue labelling, deduplication, and replies
with learning from corrections, and Intercom Fin already ships simulations, regression
tests, guardrailed procedures, and monitoring for helpdesks. Project B's value as a
learning artifact does not depend on beating them. Any later SaaS claim must come from
owned queue policy, accumulated correction history, or FDE-style deployment, never from
claiming these capabilities are unique.

## 2. Goals, non-goals, anti-goals

### 2.1 Goals

1. Ingest the real LangChain issue queue (history + live) with no synthetic substitute data,
   including template metadata and existing bot actions with provenance.
2. Preserve deterministic template metadata as given. For each eligible new issue, propose
   only the semantic work templates cannot settle: declared intent/package mismatch,
   additional workflow state, duplicate link, known-issue coverage, missing-information
   needs, reproducibility, forum/security misroute, urgency, and one route:
   auto-draft, assisted, or human. Package inference is scored only when the submitter
   selected `Other / not sure / general`, selected no usable package, or maintainers later
   corrected the declared package.
3. Draft only the three narrow reply classes in §7.2 from retrieved evidence, with
   citations and refusal when evidence is insufficient.
4. Beat the installed deterministic baseline and an LLM semantic-triage baseline on the
   semantic tasks in §8, with paired confidence intervals and accuracy per dollar. Exact
   agreement with template-derived labels is reported as a parser sanity check, never as
   the headline model result.
5. Run a live private shadow digest for at least 7 days to measure agreement with later
   maintainer actions; then, only with maintainer participation, run an assisted pilot
   that can measure maintainer time. Shadow agreement alone is never called time saved.
6. Ship a deployed, traced, cost-accounted service with CI-run evaluations, plus a README
   with eval tables and a 60-second demo. Production hardening is sequenced by §14 so it
   cannot consume the budget needed to prove or kill triage quality first.

### 2.2 Non-goals (v1)

- Multi-tenant SaaS, billing, marketing site, or additional channels (Slack, email, Forum).
- Auto-merging code, answering Forum/Discussions posts, or triaging pull requests.
- Any public comment, label, assignment, or close action before maintainer grant (§9).
- Replacing GitHub Issues as the system of record in v1. Queue-state ownership is an
  earned graduation, not a starting claim.
- Fine-tuning or training models. All intelligence is API models plus code-owned policy.
- Supporting a second queue or a second ecosystem before the pass bar in §11 is met.

### 2.3 Anti-goals (failure even if it "works")

- A demo that only runs on the builder's laptop, with no evals, no deployment, no logs.
- Synthetic tickets, fake orders, or self-written help docs presented as validation.
- Auto-sent replies that spam submitters, hallucinate APIs, or damage maintainer trust.
- A generic "AI support chatbot" pitch indistinguishable from Fin or Dosu marketing.
- Optimising for more bot activity instead of maintainer minutes saved at equal quality.
- Collecting or retaining more personal data than triage requires.

## 3. Constraints

- **Real data only.** Public GitHub Issues history via official APIs; sandbox or generated
  data may be used only for unit tests and must be labelled as such, never as validation.
- **Python-first stack** (see §7 for picks and ownership boundaries).
- **Permission gradient:** public reads → private shadow digest → assisted pilot →
  maintainer-granted correction-label/comment writes → narrow single-class auto-actions.
  No step may be skipped.
- **API budgets:** GitHub REST authenticated limit 5,000 requests/hour; search endpoints
  are stricter and must be throttled, cached, and used sparingly after backfill.
- **Keys required on Day 1:** TypeSafe API key (`TYPESAFE_API_KEY`) and one LLM provider
  key, each with a hard spend cap. Signup openness for TypeSafe is unconfirmed; a Day 1
  spike call verifies both keys (see §13).
- **Willingness-to-pay gate:** multi-tenant build requires a written paid-pilot commitment
  from a budget holder. Portfolio-only success is an acceptable endpoint.
- **Solo builder.** Everything must be buildable and operable by one person in 2–6 weeks.

## 4. Users and daily workflow

### 4.1 Actors

- **Maintainer (approver):** LangChain maintainer or triage rota member. Reads the digest,
  accepts/edits/rejects proposals, and is the only actor who can authorise writes in v1.
- **Builder-operator (Jason):** runs QueueSift, reviews evals and traces, tunes thresholds
  only through versioned config changes evaluated in CI, and owns the kill switch.
- **Issue submitter:** unaffected in shadow mode. After maintainer grant, may receive
  approved bot comments (duplicate link, reproduction request) that are clearly attributed
  to the QueueSift GitHub App and can be ignored or disputed like any comment.
- **Future B2B support lead (out of v1 scope):** the paid-pilot persona the design must not
  foreclose. No v1 feature may assume GitHub-only concepts in its core queue model where a
  generic ticket concept would do.

### 4.2 Daily loop (shadow mode, the v1 default)

1. Ingest new and updated issues within one hour of creation (polling first; webhooks only
   after a maintainer installs the GitHub App — see §9).
2. For each eligible new issue, preserve its template-declared type/package and produce a
   semantic proposal: mismatch or additional-label candidates, duplicate candidate,
   known-issue and missing-information flags, reproducibility, misroute, urgency, route,
   and an evidence-cited draft reply where the route allows one. Maintainer task and
   privileged issues are counted for queue health but excluded from submitter-facing
   proposals unless a maintainer later opts them in.
3. Deliver one private digest per day to the builder-operator (and to the maintainer only
   with their consent): proposals grouped by route, each with probabilities, evidence
   links, and a one-line rationale. No public footprint.
4. Score each proposal against semantic outcomes that subsequently appear via the API,
   using §8 adjudication (label deltas with provenance, duplicate links, maintainer
   information requests/redirects, state and close reason, substantive-action timestamps).
5. Builder-operator timer-logs digest review minutes and files error-analysis notes as
   GitHub Issues on the QueueSift repo itself (see §14 tracking).

### 4.3 Daily loop (after maintainer grant; Phase 2, gated by §11)

Approved correction/additional-label writes first; duplicate-link and missing-info
comments second; single-class auto-actions last, each behind per-class confidence gates,
rate limits, and an opt-out label the maintainers control. QueueSift does not assign
individual maintainers in v1 because no public user-to-team mapping exists and assignment
has workload consequences a shadow study cannot validate. Any maintainer revert or
complaint freezes auto-actions for that class immediately (kill criterion KB3, §11).

## 5. System overview

```text
GitHub Issues API (poll; webhook later)
  -> ingestor (idempotent sync, checkpoints, ETags)
  -> template parser (declared type/package/fields preserved; no model call)
  -> redactor (secrets/PII minimisation before any model call)
  -> retriever (repo code + docs sources + closed-issue resolutions)
  -> Jev semantic battery (one parallel call; raw probabilities logged)
  -> code router (versioned thresholds/composites; owns dates & SLA maths)
  -> LLM drafter (cited draft; structured schema; context budget enforced)
  -> Jev gates (supported-by-evidence, policy-safe, needs-human)
  -> approval queue + daily digest (HTMX)
  -> guarded writer (GitHub App installation token; per-class allowlist)
  -> outcome scorer (maintainer actuals vs proposals)
Eval harness (offline): frozen cohort -> deterministic vs LLM semantic vs Jev+code -> report
Cross-cutting: tracing per issue, cost/latency panel, audit log, kill switch
```

Architecture rule: **code owns the workflow, Jev decides, the LLM writes, humans authorise.**
Jev probabilities inform routing; deterministic code plus human approval authorise writes.
No framework may hide retrieval, routing, the agent loop, or evaluation behind opaque calls;
provider SDKs, FastAPI, SQLAlchemy, and pgvector are used as libraries, not as black-box
"AI features." QueueSift is a Python monolith with background workers — no microservices,
no Kubernetes, no separate vector database service, no SPA frontend in v1.

### 5.1 Component responsibilities

| Component | Owns | Must never do |
| --- | --- | --- |
| Ingestor | Backfill, incremental sync, timeline parsing, first-action derivation | Call models; write to GitHub |
| Template parser | Issue type, declared packages, structured fields, template provenance | Infer semantics the form did not declare |
| Redactor | Secret patterns, email/PII minimisation, state-size caps | Silently alter quoted error output needed for triage |
| Retriever | Chunking, embeddings, hybrid rank, citation IDs, no-evidence signal | Fetch paywalled or off-licence content |
| Jev intake | Atomic Choice/Score/Noul battery, lean state assembly | Date/money maths, counting, free-text drafting |
| Code router | Composites, thresholds, SLA clocks, route selection | Learn thresholds without an eval run record |
| LLM drafter | Cited reply drafts, evidence summaries, LLM semantic-triage baseline | Act without retrieved evidence; exceed step/token budgets |
| Jev gates | Post-draft support/policy/needs-human checks | Serve as a security boundary (signals only) |
| Approval UI | Digest, accept/edit/reject, audit display, kill switch | Expose model keys; allow cross-installation access |
| Guarded writer | Correction/additional-label and comment writes under grant, rate limits | Merge code; assign people; close issues in v1 except approved duplicate-link flow |
| Outcome scorer | Maintainer-actual joins, accuracy/latency/cost aggregates | Tune on held-out frozen sets |

## 6. Data design

Postgres is the system of storage for QueueSift's own records. GitHub remains the source
of truth for issues themselves; every local row must be rebuildable from the API except
QueueSift-generated proposals, eval runs, and audit events, which are append-only.

Core tables (names indicative; exact columns are builder detail within these contracts):

- `installations` — GitHub App installation ID (nullable until grant; shadow mode uses a
  single "public-poll" pseudo-installation for `langchain-ai/langchain`), repo full name,
  grant level (`poll`, `app-read`, `app-write`), opt-out label name, kill-switch state.
- `issues` — repo, GitHub issue ID and number, title, body, author login and association,
  GitHub issue `type`, template-declared packages and structured fields, template labels
  with provenance, state and state-reason, created/updated/closed timestamps, content
  hash, sync checkpoint data. Unique on (repo, github_issue_id). Pull requests are
  excluded at ingest. For live issues, the first ingested body is preserved as
  `body_at_first_seen`; for historical issues, `body_reconstruction` is one of
  `unedited`, `edited-after-first-maintainer-action`, or `edited-before-first-action`
  based on timeline `edited` events. Historical scoring uses the current body only with
  this reconstruction flag attached; it never pretends an edited body is a perfect
  creation-time snapshot.
- `issue_events` — timeline-derived maintainer actions used as ground truth: labelled,
  assigned, referenced/cross-referenced (duplicate signals), closed/reopened, first
  maintainer action timestamp and actor class (human vs bot login).
- `label_taxonomy_snapshots` — full label list with descriptions captured at freeze and
  at each taxonomy change; proposals and eval runs reference a snapshot ID.
- `documents` and `chunks` — retrievable corpus with source type (repo code, repo docs,
  external docs source, closed-issue resolution), source URL/path, commit or fetch date,
  licence note, chunk text, embedding model + version, vector, full-text index fields.
- `proposals` — issue FK, input snapshot timestamp and body-reconstruction flag, config
  version, Jev model version, LLM model, raw Jev answers (distributions, scores, nouls),
  composite route, mismatch/additional-label/duplicate/missing-info proposals, draft class
  and text hash plus cited chunk IDs, token and latency accounting per stage, state
  (`shadow`, `approved`, `edited`, `rejected`, `written`, `reverted`).
- `maintainer_actuals` — frozen join of what maintainers actually did, per issue, captured
  at scoring time so later label edits cannot rewrite history silently.
- `eval_sets`, `eval_runs`, `eval_results` — dataset version and membership, system under
  test (`rules`, `llm-router`, `jev-code`), per-issue predictions vs actuals, aggregate
  metrics, threshold config hash, cost totals, report artifact path.
- `audit_events` — actor (human login or system), action, target, before/after summary,
  request/trace ID, timestamp. Covers logins, approvals, writes, config changes, kills.
- `sessions` — server-side web sessions (hashed session ID, GitHub user ID, expiry).

Tenancy rule: every tenant-owned row carries the installation/repo scope, and every query
is scoped by it. Cross-installation access must be impossible by construction and covered
by tests, even though v1 runs a single queue.

Retention: raw issue bodies and comments are retained while the queue is active because
evals require them; author emails are never harvested; secrets matched by the redactor are
stored only as redacted placeholders plus a match-type count; digest exports inherit the
same retention. Deleting an installation deletes its proposals, sessions, and tokens;
aggregated eval metrics may be retained only in de-identified form.

Third-party processing is an explicit design surface, not an afterthought. Public issue
text may still contain accidentally pasted secrets or personal data, and redaction is
best-effort. Only redacted, size-capped text may leave the deployment. Before Slice 2,
the builder records each provider's current training/retention terms from its official
documentation, configures the strongest available no-training/shortest-retention settings,
and records those settings in an architecture decision record. Trace payloads sent to
Langfuse contain IDs, model/config versions, probabilities, token counts, and citation IDs
by default — not raw issue text or draft text — unless Langfuse is self-hosted inside the
deployment boundary. If an acceptable retention configuration cannot be verified for a
provider, that provider is not used for issue content.

## 7. AI design

### 7.1 Deterministic metadata and Jev semantic battery

The template parser runs before any model and extracts GitHub issue `type`, initial
template label, declared packages, checklist state, package/version fields, and error or
reproduction sections. Those values are inputs with provenance (`template`, `workflow`,
or `model`), never prediction targets in headline metrics. If the workflow label differs
from the parsed declaration, the discrepancy is logged as sync/template drift, not treated
as a model opportunity.

One parallel Jev call per eligible issue then uses a pinned versioned model ID and a lean
state consisting of the redacted creation/first-seen body, parsed template fields, the
scored-label criteria from the taxonomy snapshot, and top-k retrieved snippets — never
the whole repo and never later comments for a creation-time prediction.

- `Noul: declared_intent_mismatch` — content materially contradicts the selected template
  (for example, a usage question filed as a bug or a defect filed as a feature request).
- `Noul: declared_package_mismatch` — code, imports, stack trace, or named integration
  materially contradict the selected package set.
- `Choice: corrected_package` — asked in the same speculative call and consumed only when
  the declared package is `Other / not sure / general`, unusable, or the mismatch gate
  fires; full distribution retained for multi-package issues.
- `Noul: additional_package_relevant` — one question per shortlisted additional package,
  capped in code, rather than forcing the entire taxonomy into one label prediction.
- `Score: urgency` — three descriptive levels (routine; blocks a user workflow with a
  workaround; blocks with no workaround or signals a regression/security issue).
- `Score: reproducibility` — cannot attempt from the report; partial attempt possible but
  key detail missing; a maintainer could attempt reproduction from the report as written.
- `Noul: is_duplicate_of_retrieved` — one per top candidate returned by duplicate
  retrieval (cap candidates in code), not one vague "is duplicate" question.
- `Noul: known_issue_covered` — retrieved evidence already answers or tracks this issue.
- `Noul: missing_reproduction` and `Noul: missing_version_context` — required bug fields
  are absent or unusable; presence checks that code can settle exactly stay in code.
- `Noul: belongs_on_forum` — usage/design help rather than a repository defect or feature.
- `Noul: needs_human`, `Noul: injection_or_abuse`, and `Noul: security_sensitive`.
  Security-sensitive content routes to a human immediately and never receives a public draft.

Code-owned composites combine these with deterministic signals (template completeness,
author history counts computed in SQL, existing bot labels with provenance, SLA clocks).
Weights and per-route thresholds live in one versioned config file; changing them requires
an eval run. Because `Choice` can exhibit option-order sensitivity and Jev states have
token caps, corrected-package options are group-shortlisted in code and option order is
varied in the offline stability slice (§8); taxonomy text sent to Jev is limited to scored
families and candidate packages, not all 76 labels on every issue.

### 7.2 Retrieval and drafting

Corpus v1, in priority order: (1) closed-issue resolutions and linked PR discussions from
the target repo; (2) LangChain repository README, `AGENTS.md`, contributing docs, and
package-level docs/docstrings under `libs/`; (3) the `langchain-ai/docs` repository that
publishes the official documentation. The published website may be linked for human
citation targets, but **website scraping is not the historical corpus mechanism**: both
repositories are cloned so every code/docs chunk carries a real git commit timestamp and
commit SHA. Duplicate metadata and timelines are backfilled for 24 months, but embedding
is staged to control unverified corpus cost: Slice 2 embeds all open issues plus closed
issues from the latest 12 months first, measures duplicate-target coverage and unit cost,
and expands embeddings to months 13–24 only if missed duplicate/known-issue targets older
than 12 months are material in error analysis. Out-of-window duplicate targets are reported
as censored retrieval misses, never silently counted as semantic-model errors. The
duplicate-candidate pool is all open issues plus the currently embedded closed window.
**As-of rule (eval validity):** when scoring an issue created at time T, only chunks whose
source timestamp is at or before T are retrievable (closed-issue chunk timestamp = its
`closed_at`; code/docs chunk timestamp = its git commit date; the scored issue itself,
later comments, and current-body edits are excluded from its model input). Document chunks
store `valid_from` and, where a later commit modifies or deletes them, `valid_to`; every
eval query filters `valid_from <= issue.created_at AND (valid_to IS NULL OR
issue.created_at < valid_to)`. Closed-issue resolution chunks are immutable snapshots at
closure and need no `valid_to` in v1. Live shadow mode uses cutoff = issue first-seen time, effectively now. This
prevents the leak where the answer that resolved an issue is retrieved while "predicting"
that same issue, while making the remaining edited-body limitation explicit in §8.
Code and prose are chunked differently (symbol/section-aware for code, heading-aware for
prose). Ranking is hybrid (vector plus full-text with reciprocal-rank fusion in code).
Every draft sentence that asserts a fact must cite a chunk ID that resolves to a source
URL or repo path; uncited factual drafts fail the gate by construction.

LLM use is limited to: drafting replies from evidence, summarising long threads for the
digest, and serving as the named LLM semantic-triage baseline in evals. Drafts use a structured
output schema (reply text, citations, requested-info checklist, internal summary). Step,
token, and latency budgets are enforced in code; budget exhaustion routes to human.

**Draft scope (settled after builder check, my call).** The v1 drafter produces exactly
three submitter-ready reply classes: (A) missing-information request (version, minimal
reproduction, error text) mirroring the repo templates; (B) duplicate pointer naming the
canonical issue with a one-line why; (C) known-issue answer or workaround strictly from
cited retrieved evidence. Bug diagnosis, code-fix advice, and design opinions are never
drafted as submitter replies; where useful they appear only as an internal evidence brief
for maintainers. Route meanings: `auto-draft` = a class A/B/C draft passes all gates and
would be sendable unchanged (in shadow mode it is still never sent; the label exists so
shadow scoring measures the future auto class honestly); `assisted` = no submitter draft,
maintainer receives labels plus an internal evidence brief; `human` = labels only or
escalation with reason. This sizes Slice 2 as a triage system, not a general answer engine.

### 7.3 Post-draft gates

Second Jev battery over (draft + cited evidence + issue): `supported_by_evidence`,
`policy_safe`, `leaks_private_data`. Middle-band probabilities route to human. These
gates are evaluated signals, never security boundaries; deterministic checks (allowlisted
actions, amount-free v1, account/repo scope, opt-out label, kill switch) always run in code.

## 8. Evaluation design

### 8.1 Frozen cohort, creation-time inputs, and gold construction

"Freeze" means a fixed snapshot scored repeatedly without tuning on it — it does not stop
the live queue. Revision 2 changes F1 from a convenient closed-issue sample to a
prevalence-preserving creation cohort, because sampling closed issues over-represents easy
resolutions and leaks future information.

**Cohort definition.** After a 90-day backfill and taxonomy snapshot, F1 is *every eligible
issue created in a pre-declared 28-day window ending 30 days before the freeze/scoring
date*, so each issue has had the same 30-day outcome-observation window. Eligible means
created through the bug-report or feature-request template; maintainer `task`/`privileged`
issues, pull requests, deleted/converted items, and security reports are excluded from the
headline cohort and reported separately. The exact issue count is recorded before any
system output is viewed. Tuning uses only issues created before the F1 window. If a
headline semantic class has fewer than 30 adjudicated positives in F1, that class receives
descriptive results only; the cohort may be enlarged once to the preceding 28 days under a
rule recorded before system scores are inspected. Enriched challenge slices drawn from the
tuning period may stress rare classes, but they never replace prevalence-cohort results.

**Creation-time input rule.** A system may see title, parsed template fields, declared
type/package, author association, and the body as first ingested or, historically, the
current body only when `body_reconstruction = unedited` or
`edited-after-first-maintainer-action`. Issues edited before the first maintainer action
are excluded from headline metrics and reported in a sensitivity slice, because GitHub
does not provide a reliable original-body version for every edit. Comments, final labels,
linked fixes, and later submitter clarifications are outcome evidence, never model input
for creation-time scoring. Live proposals use `body_at_first_seen` captured by the poller.

**Taxonomy and label provenance.** The snapshot maps every label into `intent`,
`package`, `workflow`, or `unscored`. Template-applied initial labels and
`auto-label-by-package.yml` labels are recorded as `declared` provenance, not maintainer
gold. Headline label scoring is a **delta task**: starting from declared intent/package,
did the system predict label additions/removals that a maintainer later made. Exact
agreement with declared labels is a parser sanity metric only. Package inference is
headline-scored only for `Other / not sure / general`, unusable declarations, and later
maintainer corrections.

**Outcome lock and adjudication.** Maintainer actuals lock at creation-plus-30-days for
every F1 issue, closed or still open. A maintainer actor is identified from comment/timeline
association where GitHub exposes OWNER/MEMBER/COLLABORATOR, supplemented by a
snapshot-recorded maintainer/bot allowlist built during the Day 1 inventory; unknown actors
never create gold automatically. Semantic outcomes are adjudicated from timeline evidence
under written rules: duplicate (maintainer duplicate close/link or explicit canonical
reference), missing information (maintainer request, `waiting-on-author`, or
unable-to-reproduce closure), forum/security misroute (explicit redirect), and known-issue
coverage (maintainer link to tracking issue/docs). Absence of such evidence is `unknown`
for recall denominators unless a human adjudicator marks a true negative from the full
thread. Urgency and reproducibility have no dependable maintainer gold; they are reported
as operator-adjudicated secondary judgments with their rubric, not as maintainer accuracy.
Assignee agreement is informational only and is not in the pass bar.

Set F1 is scored only in recorded eval runs; tuning exposure retires it to F2. Live shadow
proposals form rolling Set L; L measures agreement over time but never replaces F1 for
offline go/no-go decisions, and never by itself proves time saved (§11).

### 8.2 Systems compared on identical creation-time inputs

1. **Installed/deterministic baseline:** the exact template parser plus a line-faithful
   re-implementation of `auto-label-by-package.yml` (verified from YAML: extract the
   declared `Package` section on opened/edited and sync package labels), exact missing-field
   checks for structured template slots that code can settle, and a lexical duplicate
   candidate ranker. This baseline is near-perfect at declared metadata by construction;
   QueueSift must add value only on semantic deltas, candidates, and drafts.
2. **LLM semantic-triage baseline:** same creation-time lean state and same retrieved
   duplicate/evidence candidates as QueueSift, returning the same semantic fields as
   structured JSON. Sharing retrieval isolates the decision method instead of confusing
   it with corpus quality.
3. **QueueSift:** deterministic parser plus Jev battery and code composites (§7), drafting
   scored separately.

### 8.3 Metrics and statistical honesty

Headline metrics are semantic, per task, never one aggregate accuracy:

- **Delta labels:** micro/macro precision, recall, and F1 for maintainer additions/removals
  after creation, split by intent-correction, package-correction/addition, and workflow
  state. Parser agreement with declared intent/package is a sanity check reported apart.
- **Duplicates:** candidate-retrieval Recall@5 among adjudicated duplicate positives,
  end-to-end proposal precision after gates, and end-to-end recall. Every proposed
  positive in F1 is human-audited; retrieved negatives are sampled for false-negative checks.
- **Missing information, forum/security misroute, known-issue coverage:** precision/recall
  only over adjudicated positive/negative outcomes, with `unknown` counts shown and not
  folded into either denominator.
- **Calibration:** Brier score and reliability bins for binary semantic probabilities, so
  threshold claims rest on observed calibration rather than vendor positioning.
- **Route quality:** offline, only class-conditional actionability can be scored (would the
  proposed draft/action have matched the maintainer's eventual action class). No offline
  "auto-resolve accuracy" is claimed without an assisted pilot.
- **Draft quality:** claim-level supported/unsupported audit over every auto-draft proposal
  up to the first 50 in F1, then a stratified sample. Drafts are shuffled and stripped of
  system identity before audit; the builder is the default single rater and every report
  labels that limitation. A second rater (maintainer preferred) audits at least 20 drafts
  when available; disagreement rate is reported. Deterministic citation checks verify that
  cited chunks exist, predate the issue under §7.2, and resolve to the claimed source.
- **Safety/cost/operations:** injection-suite pass rate (at least 20 cases), dollars per
  eligible issue by provider/stage, p50/p95 latency, model-call failure rate, corrected-
  package option-order stability, and threshold sweeps of proposed-action rate versus error.

All proportions carry Wilson 95% intervals; paired system differences on the same issues
use issue-level bootstrap intervals. A task has no pass/fail verdict with fewer than 30
adjudicated positives (or draft audits for draft claims); it is reported descriptively and
handled through the enlargement/live-shadow rule in §8.1. Maintainer labels are treated as
noisy operational truth with an unknown agreement ceiling, not as infallible annotation.

### 8.4 Eval execution

Offline harness in `pytest`-driven CLI, run in CI as a smoke subset on every PR (recorded
model responses, no live spend) and in full live mode on demand or nightly with a spend
cap. Every run writes an immutable report artifact (JSON plus Markdown summary) linked
from the PR that changed prompts, criteria, models, or thresholds. Git stores dataset
manifests (repo, issue IDs/numbers, input/as-of timestamps, body hashes, adjudication
labels, and config hashes), not bulk raw issue/comment text; the harness hydrates text
from the local database or GitHub at run time. Public reports quote only short redacted
snippets necessary for error analysis. This keeps a public portfolio repo possible without
republishing the queue corpus or accidentally committing pasted secrets.

## 9. Authentication, authorisation, and permission gradient

Four trust planes are kept separate:

1. **Human → QueueSift (who is approving):** Sign in with GitHub (OAuth authorisation-code
   flow via the GitHub App's user authorisation). No local passwords. Browser holds only an
   `HttpOnly`, `Secure`, `SameSite` cookie referencing a server-side session; state-changing
   requests require CSRF tokens. Authorisation is re-checked per request against the user's
   live GitHub permission on the target repo: `viewer` (digest read), `approver`
   (maintain/admin on repo; approve/edit/reject), `operator` (builder; config, kill switch).
   In pre-grant shadow mode the operator is the only human user, but the checks are built
   and tested from the start.
2. **QueueSift → GitHub (system access):** All product writes use the GitHub App — never a
   personal access token. Server signs a short-lived App JWT (RS256 with the App private
   key) and exchanges it for one-hour installation tokens minted on demand and cached in
   memory. **Credential sequence (settled after builder check, my call):** the GitHub App
   is registered in Slice 0 so its identity, permissions, and webhook configuration are
   testable early, but it cannot read LangChain data until a maintainer installs it. Before
   installation, deployed shadow polling — including the Slice 3 cloud deploy — uses one
   explicit exception: a builder-owned fine-grained personal access token, public-repo
   read-only scope, 90-day expiry, stored only in the deploy secret manager, used solely
   for reads of public LangChain data, and recorded in every sync audit event as
   `credential=builder-pat-readonly`. This exception exists because unauthenticated reads
   (60/hour) cannot sustain hourly incremental sync plus timelines, and delaying all
   deployment until maintainer installation would make the shadow evidence needed to earn
   that installation impossible. The token is deleted the day the App is installed;
   security tests assert it can perform no write. Human sign-in during pre-install slices
   uses the App's user-authorisation flow restricted to an operator allowlist containing
   only the builder's GitHub account — it grants no LangChain access and implies none.
   Grant phases after invitation: `app-read` (issues read, metadata read), then
   `app-write` (issues write) only after §11 shadow pass bars and maintainer invitation.
3. **GitHub → QueueSift (event trust):** Webhooks are enabled only in app phases. Every
   delivery is verified with HMAC-SHA256 over the raw body (`X-Hub-Signature-256`) and
   deduplicated by delivery ID. Unverified payloads are rejected and logged.
4. **QueueSift → models (spend authority):** Jev and LLM keys exist only server-side in
   environment/secret-manager storage, with per-provider hard spend caps and per-issue
   token budgets enforced in code. Keys never reach the browser, logs, or traces.

Secrets and failures: the App private key, webhook secret, session secret, and model keys
live outside Git; rotation is documented in the runbook (§15). Required negative tests:
unauthenticated request rejected, wrong-repo user forbidden, forged webhook rejected,
expired installation token refreshed, revoked installation stops all writes, cross-repo
(session bound to one installation, target issue in another) access denied. Audit events
record the GitHub user ID behind every approval and write.

## 10. Product surface

v1 surface is deliberately small and server-rendered (FastAPI + Jinja2 + HTMX + Tailwind):

- `GET /` — operator overview: queue health, last sync, spend today, kill-switch state.
- `GET /digest/{date}` — daily digest grouped by route; each proposal shows issue link,
  declared metadata, semantic correction/duplicate/missing-info proposals, probabilities,
  evidence citations, draft preview, and the maintainer actual once known (score
  afterwards, visibly labelled as hindsight).
- `GET /proposals/{id}` — full audit view: raw Jev answers, retrieved chunks, draft,
  gate values, token/latency breakdown, trace link.
- `POST /proposals/{id}/approve|edit|reject` — approver actions (write phase only for
  approve-to-GitHub; in shadow these record judgments used as eval labels).
- `GET /evals` and `GET /evals/{run_id}` — frozen-set and live metrics, threshold sweeps,
  cost panel (dollars per issue by stage; p50 latency by stage).
- `POST /admin/kill` and `POST /admin/resume` — operator only; kill stops all writes and
  digests within one worker cycle.
- `GET /healthz` — liveness only, no data. No public JSON API is promised in v1; internal
  endpoints return JSON where HTMX needs it, versioned under `/internal/v1/`.

Digest delivery in shadow mode is in-app plus a Markdown file artifact per day (suitable
to attach to maintainer outreach). Email/Slack delivery is deferred until a maintainer
asks for it — an explicit non-goal to build pre-emptively.

## 11. Metrics, pass bars, time proof, and kill criteria

Queue baselines are computed from the F1 cohort and trailing 30 days before live shadow:
eligible issue volume, class prevalence and adjudicated-positive counts, declared-label
correction rate, duplicate-link rate, missing-info request rate, reopen rate, and time to
first **substantive human maintainer action**. The last term means a human comment,
human label correction, assignment, close, or linked fix — never template labels,
`github-actions` package sync, or other bot events. It is a queue-health baseline only;
shadow software that maintainers do not use cannot causally improve it.

### 11.1 Offline pass bar — proceed to live shadow

All applicable conditions on F1, each with the intervals required in §8.3:

1. **Semantic value over deterministic code:** on tasks the installed baseline cannot
   settle (mismatch/additional labels, duplicates, missing-info, misroute, known issue),
   QueueSift improves the relevant precision/recall or F1 over the deterministic baseline
   with a paired interval excluding zero where denominators permit a verdict. It need not
   beat template parsing at declared metadata, and must not claim to.
2. **Decision-method value:** QueueSift is not dominated by the LLM semantic baseline:
   at comparable or better task quality it has lower dollars per eligible issue or lower
   p50 latency, or it has materially better calibration (lower Brier score) at comparable
   cost. If the LLM baseline wins on quality, cost, latency, and calibration, Jev has no
   demonstrated role and bar 2 fails even if absolute quality looks attractive.
3. **Duplicate trust:** end-to-end duplicate proposal precision ≥90% among adjudicated
   proposals when at least 30 proposals exist; retrieval Recall@5 and end-to-end recall
   are reported with intervals and positive counts.
4. **Draft trust:** claim-level unsupported rate ≤2% among audited auto-drafts, with the
   audit denominator shown; injection suite 100% refused/escalated.
5. **Cost:** total model spend per eligible issue is at or below a cap fixed after the
   Day 1 measured-cost spike and recorded before F1 scoring; the cap may not be raised
   retroactively to pass.

### 11.2 Shadow pass bar — proceed to maintainer outreach

1. Seven consecutive days of proposals within 1 hour of creation/first-seen for eligible
   issues, with sync gaps and model failures reported rather than hidden.
2. On sampled semantic decisions with known later outcomes, at least 70% agreement with
   maintainer actuals, reported by task with denominators and intervals. This is
   **agreement**, not acceptance and not time saved.
3. Zero proposals the operator judges harmful/spammy in the final shadow week under a
   written rubric, and no public writes attempted.

### 11.3 Assisted pilot — the only time-saving claim

Time saved can be claimed only if a maintainer agrees to actually use QueueSift output in
an assisted pilot. Minimum protocol: a pre-declared sample of at least 30 eligible issues
handled with QueueSift proposals and a comparable baseline sample from the same maintainer
or rota handled without them (alternating days or matched issue classes where randomisation
is impractical); the maintainer or operator timer-logs triage minutes per issue and records
accept/edit/reject per proposal. The time-value bar is ≥30% lower median maintainer triage
minutes per eligible issue with no increase in reverts, reopen rate, or maintainer-rated
harmful proposals. Self-timed builder review may be reported as operator-time evidence, but
must never be relabelled maintainer time saved. If no maintainer will run the pilot, the
project can still succeed as an evaluated shadow system; its FDE claim becomes measured
agreement and system quality, explicitly without a customer time-saving result.

### 11.4 Guarded writes and kill criteria

Guarded writes require §§11.1–11.2, explicit App installation with issues-write,
allowlisted action classes and opt-out agreed with maintainers, and two approval-gated
weeks with zero reverts. Kill criteria:

- KB1 No semantic value: §11.1 bars 1–2 fail after one documented tuning iteration.
- KB2 No demonstrated time value: no assisted pilot can be recruited, or the pilot misses
  the §11.3 bar → remove all time-saved claims; assisted-writes thesis stops.
- KB3 Trust failure: any approved/auto output reverted or complained about, or audited
  unsupported-claim rate above 2% after one tightening iteration → approval-only or stop.
- KB4 No usable queue/feedback: fewer than 30 eligible new issues in a shadow week with no
  viable backlog re-scope, too few adjudicated positives to judge headline tasks after the
  one permitted cohort enlargement, or no maintainer feedback on 50 shadow proposals within
  7 days of outreach → invoke §12 once, then stop rather than lowering the bar.
- KB5 No payer: technical and pilot metrics pass but no budget holder signs a paid pilot
  → portfolio/OSS endpoint only; do not build multi-tenancy or a B2B clone on spec.

## 12. Queue switch rule

The target is `langchain-ai/langchain`. Exactly one switch is permitted, to
`astral-sh/uv`, if KB4 fires on LangChain (maintainer silence after good-faith outreach
including one genuine contribution, queue volume collapses, or the semantic classes prove
too sparse to evaluate). Before reusing this design on uv, the builder must re-measure
uv's templates, existing label automation, bot actors, eligible-issue definition, and
semantic-class prevalence; LangChain template assumptions do not transfer by assertion.
On switch, scope becomes backlog triage (stale/duplicate sweep over the roughly
2,356-issue open backlog measured 2026-10-19, with 84% of recently closed issues labelled)
because uv creates about 19 new issues per week, below the 30/week new-issue bar. Frozen
cohorts, thresholds, taxonomy snapshots, gold rules, and corpus windows restart under the
same creation-time and leakage rules. LangChain results remain reported as a completed
negative/mixed result, never silently dropped. A second switch is not permitted inside
this design; failure on both queues ends Project B and returns the builder to Candidate A.

## 13. Stack, dependencies, and Day 1 spikes

| Layer | Pick (my call — see §16) | Notes |
| --- | --- | --- |
| Language/tooling | Python 3.12, uv, Ruff, Pyright | Typed, tested with pytest |
| API/UI | FastAPI, Pydantic v2, Uvicorn, Jinja2 + HTMX + Tailwind | Server-rendered approval queue |
| Storage | Postgres + SQLAlchemy + Alembic + pgvector + full-text search | One database for records and retrieval |
| Jobs | Redis + ARQ workers | Polling, indexing, digests, retries with backoff |
| GitHub | GitHub App (`httpx` + JWT via PyJWT/cryptography) | Direct REST; no framework wrapper hiding pagination/limits |
| Decisions | `typesafe-sdk`, pinned versioned Jev model ID | Log `response.model` and `usage.input_tokens` per call |
| Drafting/baseline | OpenAI SDK (owner pick, 2026-10-19) | Structured outputs; small model drafts, strong model routed |
| Embeddings | OpenAI embeddings (same key as drafting) | Model + version stored per chunk; switching provider re-embeds corpus |
| Evals | pytest + custom JSONL harness, scikit-learn metrics only | No hosted eval SaaS in v1 |
| Observability | Structured logs + local trace records first; Langfuse after §6 retention ADR; Sentry at first cloud deploy | Trace ID per issue; hosted traces carry redacted metadata only |
| Delivery | Docker Compose, GitHub Actions CI, one cloud target from Slice 3 (§16) | Migrations run as release step; backup restore rehearsed before shadow |

Day 1 feasibility spikes (throwaway code, results kept in the repo `docs/spikes/` notes):
(1) Jev key works from the builder's region; `Choice`/`Score`/`Noul` calls on real issues
with latency, tokens, and failure behaviour recorded. (2) OpenAI key works for structured
drafting and embeddings from two cited chunks. (3) Provider-data ADR: official training
and retention settings for Jev, OpenAI, and any hosted tracing are recorded and configured
before real issue text is sent in Slice 2. (4) GitHub sample of at least 100 consecutive
eligible issues with timelines: request count and wall time, bot/maintainer actor inventory,
template-label provenance, body-edit reconstruction rates, semantic-class candidates, and
declared-label correction rate. (5) Corpus dry run on a bounded sample: cloned-repo sizes,
chunk counts, embedding tokens/dollars per 100 issues, projected 12-month corpus cost, and
duplicate-target window coverage. (6) `auto-label-by-package.yml` and all issue templates
re-read at build start; deterministic baseline fixtures written from the actual YAML.
Slice 1 does not exit until these six notes exist and the §11 cost cap is set from measured
unit costs — this is the feasibility gate that prevents spending the solo budget on an
unmeasurable queue or an unbounded corpus.
If the Jev key is waitlisted, week 1 proceeds with the LLM semantic-triage baseline behind the same
decision interface, and Jev joins as the challenger when the key arrives — the eval design
already supports either order. **Branch deadline (settled after builder check, my call):**
if no working Jev key exists by the end of Slice 1, Slice 2 builds only the rules and
LLM semantic-triage systems and the Schedule Checkpoint fires at Slice 2 exit: the owner chooses
(a) pause for at most 14 calendar days awaiting the key, doing Slice 3 shadow plumbing
without any Jev pass-bar claims, or (b) approve a design revision that removes Jev from
the product and re-states §11 around the LLM semantic baseline (with the FDE story
explicitly downgraded from typed decisions to structured-output triage). Silently continuing
LLM-only past the checkpoint while keeping Jev pass bars is prohibited, because §11
bar 1 is defined for the Jev-plus-code system.

## 14. Delivery plan and tracking

Build in vertical slices with **core proof before production hardening**. Each slice ends
runnable in Docker with tests and a named artifact; public/cloud deployment begins at
Slice 3, not Slice 0. Calendar estimates are deliberately not promised per slice: exit is
by gate evidence, while the fixed calendar elements are the F1 30-day outcome window,
7 shadow days, and pilot/write durations in §11.

- **Slice 0 — Walking skeleton (local):** one real historical issue flows template parser
  → Postgres → deterministic proposal → static digest; GitHub App registered (not
  installed); Docker Compose and CI green; no cloud, Langfuse, Sentry, or write path yet.
- **Slice 1 — Feasibility and data foundation:** six §13 spikes; 90-day idempotent
  metadata/timeline backfill; taxonomy and gold rules implemented; baselines and class
  prevalence measured; F1 creation cohort declared before outputs are viewed; GitHub
  Projects board live. **Feasibility gate:** working keys or the §13 branch decision,
  acceptable provider-retention settings, projected corpus/eval cost inside the recorded
  cap, and enough projected adjudicated positives for at least the duplicate and
  missing-info tasks (else enlarge/re-scope/stop under KB4 before model work).
- **Slice 2 — Offline intelligence:** staged retriever, deterministic parser, Jev battery,
  router, narrow drafter, gates; F1 three-system semantic eval + calibration + threshold
  sweep + injection suite; go/no-go against §11.1. Only structured logs/local traces are
  required here.
- **Slice 3 — Shadow product:** minimal approval UI and operator auth, daily digest, live
  polling, outcome scoring, one-cloud Docker deploy, backup/restore rehearsal, redacted
  tracing and error reporting; 7-day shadow run against §11.2; maintainer outreach packet
  (10 worked examples + one-page summary) sent only after a genuine contribution and only
  if outreach bars pass.
- **Slice 4 — Assisted pilot then guarded writes (both gated):** maintainer uses proposals
  under the §11.3 time protocol, initially without automated writes if installation is not
  yet granted; then GitHub App install flow, full auth negative-test suite,
  approval-gated correction-label/comment writes, allowlisted auto-actions, kill-switch drill.
- **Slice 5 — Hardening and proof packaging:** failure drills, runbooks, retention/deletion
  rehearsal, week of live logs, README with architecture + eval tables, 60-second demo,
  resume bullets using only measured numbers and claim levels earned in §§11.1–11.3.

Deferred until the slice that needs them: webhooks (Slice 4), Langfuse/Sentry (Slice 3,
after the retention ADR), multi-repo support, email/Slack delivery, assignment, and any
billing/multi-tenancy (KB5). Building them earlier is scope failure, not extra credit.

**Tracking: GitHub Projects** on the QueueSift repo (owner decision). Columns:
Backlog → Ready → In Progress → Review/Eval → Done; Blocked is a label. Fields:
Priority, Size (S/M/L), Layer (data, retrieval, decisions, evals, product, ops).
Rules: WIP limit 2; Ready requires acceptance criteria; Done requires test or eval
evidence linked in the closing PR; one milestone per slice; every threshold/prompt change
is a PR that links its eval artifact. Cards are GitHub Issues on the QueueSift repo —
never cards filed on the LangChain repo.

Indicative repo layout (builder may refine names, not boundaries):

```text
app/{main,api,github,triage,retrieval,drafting,writers,db,jobs}/
evals/{datasets,adversarial,run_eval.py}
tests/{unit,integration,contracts}
docs/{spikes,runbooks,adr}/
docker-compose.yml  pyproject.toml
```

## 15. Risks, operations, and mitigations

- **Template determinism / no semantic headroom:** LangChain templates and workflows
  already settle initial intent/package, and maintainers may rarely correct them. Mitigation:
  Slice 1 measures semantic-class prevalence and correction rates before model work; if
  duplicate/missing-info/misroute positives cannot support evaluation, KB4 stops or switches
  scope instead of manufacturing a label-prediction win.
- **Maintainer access:** LangChain is a company-run queue with existing internal processes;
  shadow agreement may be the ceiling. Mitigation: claim levels are separated in §11,
  outreach requires contribution plus private evidence, and no time outcome is
  promised without the assisted pilot. There is no design workaround for a maintainer who
  simply does not want the system.
- **Platform absorption:** GitHub, LangChain's own workflows, Dosu, or Fin ship equivalent
  triage. Mitigation: compete on embedded queue policy and published per-queue evals as a
  learning artifact; never claim feature uniqueness (see §1.1 honesty note). The GitHub
  result does not by itself validate a B2B inbox product, different support data, or SaaS moats.
- **Maintainer harm or spam:** the fastest way to destroy the FDE story. Mitigation:
  shadow-first gradient (§9), private digest, rate limits, opt-out label, kill switch,
  contribution-before-outreach rule, zero tolerance in KB3.
- **Adversarial issue text:** injected instructions can move model verdicts. Mitigation:
  issue text is data, never instructions; redaction; Jev gates as signals; deterministic
  allowlists; injection suite in CI; security-sensitive route never drafts publicly.
- **PII, secrets, and third-party retention:** minimisation before model calls (§6),
  no email harvesting, secrets stored redacted only, official provider no-training/retention
  settings recorded in the Slice 1 ADR, hosted traces limited to redacted metadata, and a
  sampled redaction-failure audit. Redaction is treated as lossy and imperfect, so sensitive
  routes stay human and raw issue text is never sent merely to improve a trace view.
- **Corpus/API cost surprise:** 24 months of timelines/comments plus two cloned repos can
  exceed a solo budget before quality is known. Mitigation: metadata-first backfill, staged
  12-month embedding, Slice 1 measured unit-cost projection, hard caps, and expansion only
  on demonstrated retrieval headroom.
- **Rate limits and sync gaps:** conditional requests (ETags), `since` checkpoints,
  search API avoided in steady state, backoff with jitter, sync-gap alarms on the
  operator overview.
- **Label taxonomy and docs drift:** taxonomy snapshots per eval run (§8.1); corpus
  re-index on default-branch change detection; stale-evidence drafts fail gates rather
  than citing superseded text silently.
- **Model/provider drift:** pinned Jev model ID with `response.model` logged; LLM model
  IDs pinned in config; any model change is a config PR requiring a fresh F1 run.
- **Cost runaway:** per-issue and daily spend caps enforced in code; digest halts rather
  than exceeding cap; cost panel reviewed daily during shadow.
- **Single-operator burden (M8 in practice):** runbooks for key rotation, re-freezing an
  eval set, taxonomy change, incident (bad proposal wave), rollback, and queue switch.
  Failure drills before Slice 4: forged webhook, GitHub outage, model timeout storm,
  duplicate webhook flood, poisoned issue batch.

Operational definition of healthy during shadow: sync lag under 1 hour, digest produced
daily without manual intervention, zero writes attempted, spend within cap, and every
proposal traceable from ingest timestamp to maintainer actual.

## 16. Decisions record and approval gate

### 16.1 Decided by the owner (do not re-litigate in planning)

- Career target: Forward Deployed Engineer; the project is judged on embedded delivery
  plus measured operational evidence at the claim level actually earned (§11).
- Candidate B (support triage-and-resolve) as the build, on `langchain-ai/langchain`,
  with the single permitted switch to `astral-sh/uv` backlog scope (§12).
- Working name: QueueSift.
- LLM and embeddings provider: OpenAI (single key for drafting, LLM semantic-triage baseline, and
  embeddings; key itself is obtained and verified in the Day 1 spike — this document
  records the pick, not possession of a working key).
- Python-based stack; the system must demonstrate end-to-end building competence
  (every layer owned, per §5 architecture rule).
- Implementation tracking: GitHub Projects on the QueueSift repo (§14).
- Real data only; willingness to pay validated with a design partner before any
  multi-tenant SaaS build.

### 16.2 My calls (sensible defaults, marked as mine; owner may override at approval)

- Monolith + Postgres/pgvector + Redis/ARQ; HTMX server-rendered UI; no LangGraph unless
  a genuine multi-step drafting loop emerges in Slice 2 error analysis.
- Shadow-first polling before webhooks; GitHub App registered in Slice 0, installed only
  at Slice 4, with the read-only builder-token exception for deployed shadow (§9).
- Builder-check settlements: draft classes and route meanings (§7.2), staged corpus
  window with the as-of leakage rule (§7.2), gold-label provenance and lock rules (§8.1),
  pre-install credential sequence (§9), and the Jev-waitlist Schedule Checkpoint (§13).
- Critical-review revision 2 settlements: deterministic template metadata excluded from
  headline model scores; prevalence-preserving creation cohort with 30-day outcomes,
  creation-time inputs, edited-body censoring, confidence intervals, and minimum-positive
  rules (§8); separate offline/shadow/assisted-pilot claim levels (§11); Slice 1
  feasibility gate and deferred production hardening (§§13–14); provider-retention ADR and
  dataset-manifest-only Git artifacts (§§6, 8.4).
- Digest as in-app page plus Markdown artifact; no email/Slack delivery in v1.
- Local structured tracing first; redacted Langfuse metadata after the retention ADR;
  Sentry from first cloud deploy; scikit-learn only for metric arithmetic.
- Deployment starts as Docker Compose on one small host the owner controls; the named
  long-lived cloud is chosen at Slice 3 kickoff, not before, because it does not change
  Slices 0–2.

### 16.3 Left to the builder (explicitly builder's choice during planning/build)

- Exact table columns, index choices, chunk sizes, embedding dimensions, top-k values,
  ARQ queue names, HTMX interaction details, CSS, log field names, Dockerfile layering,
  test fixture shapes, and runbook wording — within the contracts in §§5–10.
- Which small/strong OpenAI model pair to use, tuned only through §8 evals with recorded
  cost/latency.
- Nightly versus on-demand full eval scheduling, within the spend cap.

### 16.4 What approval means

Owner approval of this document authorises: (a) writing the implementation plan,
(b) creating the QueueSift GitHub repository and GitHub Projects board seeded from §14,
and (c) beginning Slice 0. It does not authorise maintainer outreach, any write to the
LangChain repository beyond the owner's own genuine contribution, or multi-tenant work.
Those remain gated by §§4, 9, and 11.
