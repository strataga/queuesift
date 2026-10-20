"""Feasibility analysis over a backfilled queue. Descriptive only, no model calls."""

from __future__ import annotations

import json
import statistics
from collections import Counter
from datetime import datetime

from sqlalchemy.orm import Session

from app.db import IssueEventRow, IssueRow
from app.template_parser import parse_template

WORKFLOW_LABELS = {
    "waiting-on-author",
    "unable-to-reproduce",
    "reproduced",
    "investigate",
    "external",
}
INTENT_LABELS = {"bug", "feature", "feature request", "documentation"}
UNSCORED_LABELS = {
    "size: XS", "size: S", "size: M", "size: L", "size: XL", "release",
    "dependencies", "docker", "ci-ignore", "linting", "tests", "typing",
    "refactor", "breaking", "performance", "infra",
}
# Declared checkbox -> the package-family label the installed workflow applies.
PACKAGE_LABEL_MAP = {
    "langchain": "langchain",
    "langchain-core": "core",
    "langchain-classic": "langchain-classic",
    "langchain-mcp-adapters": "langchain-mcp-adapters",
    "langchain-model-profiles": "model-profiles",
    "langchain-tests": "langchain-tests",
    "langchain-text-splitters": "text-splitters",
}
MAINTAINER_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}
SUBSTANTIVE_EVENTS = {"commented", "labeled", "unlabeled", "assigned", "closed", "cross-referenced"}


def _is_bot(login: str | None) -> bool:
    return bool(login) and (login.endswith("[bot]") or login == "github-actions")


def _expected_package_label(declared: str) -> str:
    if declared in PACKAGE_LABEL_MAP:
        return PACKAGE_LABEL_MAP[declared]
    return declared.removeprefix("langchain-")


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def analyze_backfill(engine, *, repo: str) -> dict:
    with Session(engine) as session:
        issues = session.query(IssueRow).filter_by(repo=repo).all()
        events = session.query(IssueEventRow).filter_by(repo=repo).all()

    events_by_issue: dict[int, list[IssueEventRow]] = {}
    for event in events:
        events_by_issue.setdefault(event.issue_number, []).append(event)
    for rows in events_by_issue.values():
        rows.sort(key=lambda e: e.created_at or "")

    bots = sorted({str(e.actor) for e in events if e.actor is not None and _is_bot(e.actor)})
    maintainers = sorted(
        {
            str(e.actor)
            for e in events
            if e.actor is not None
            and e.actor_association in MAINTAINER_ASSOCIATIONS
            and not _is_bot(e.actor)
        }
    )
    maintainer_set = set(maintainers)

    type_counts = Counter(i.issue_type or "(none)" for i in issues)
    eligible = [i for i in issues if (i.issue_type or "").lower() in {"bug", "feature"}]
    states = Counter(i.state for i in issues)
    state_reasons = Counter(i.state_reason or "(open/none)" for i in issues)

    workflow_counts: Counter = Counter()
    unsure = 0
    no_package = 0
    diverged = 0
    missing_repro = 0
    cross_ref = 0
    duplicate_reason = 0
    edited_any = 0
    label_events_after_5min_by_maintainer = 0
    first_action_hours: list[float] = []
    weekly: Counter = Counter()
    token_chars = 0

    for issue in issues:
        labels = json.loads(issue.labels_json or "[]")
        workflow_counts.update(label for label in labels if label in WORKFLOW_LABELS)
        declared = json.loads(issue.declared_packages_json or "[]")
        if issue.package_unsure:
            unsure += 1
        if not declared and not issue.package_unsure:
            no_package += 1
        final_package_labels = {
            label
            for label in labels
            if label not in INTENT_LABELS | WORKFLOW_LABELS | UNSCORED_LABELS
        }
        expected = {_expected_package_label(d) for d in declared}
        if declared and not expected.issubset(final_package_labels):
            diverged += 1
        parsed = parse_template(issue.body)
        if (issue.issue_type or "").lower() == "bug" and not parsed.has_reproduction:
            missing_repro += 1
        token_chars += len(issue.title) + len(issue.body)
        created = _parse_ts(issue.created_at)
        if created:
            iso = created.isocalendar()
            weekly[f"{iso.year}-W{iso.week:02d}"] += 1

        rows = events_by_issue.get(issue.number, [])
        if any(e.event == "cross-referenced" for e in rows):
            cross_ref += 1
        if (issue.state_reason or "") == "duplicate":
            duplicate_reason += 1
        if any(e.event == "edited" for e in rows):
            edited_any += 1
        for event in rows:
            if (
                event.event in {"labeled", "unlabeled"}
                and event.actor in maintainer_set
                and created
                and (event_ts := _parse_ts(event.created_at))
                and (event_ts - created).total_seconds() > 300
            ):
                label_events_after_5min_by_maintainer += 1
                break
        if created:
            for event in rows:
                if (
                    event.event in SUBSTANTIVE_EVENTS
                    and event.actor in maintainer_set
                    and event.actor != issue.author
                    and (event_ts := _parse_ts(event.created_at))
                    and event_ts >= created
                ):
                    first_action_hours.append((event_ts - created).total_seconds() / 3600)
                    break

    return {
        "repo": repo,
        "issues_total": len(issues),
        "events_total": len(events),
        "eligible_bug_feature": len(eligible),
        "by_type": dict(type_counts),
        "by_state": dict(states),
        "by_state_reason": dict(state_reasons),
        "issues_per_iso_week": dict(sorted(weekly.items())),
        "bot_actors": bots,
        "maintainer_actors": maintainers,
        "workflow_label_counts": dict(workflow_counts),
        "package_unsure": unsure,
        "package_undeclared": no_package,
        "declared_package_not_in_final_labels": diverged,
        "issues_with_maintainer_label_change_after_5min": label_events_after_5min_by_maintainer,
        "bug_missing_reproduction_deterministic": missing_repro,
        "issues_with_cross_reference": cross_ref,
        "closed_state_reason_duplicate": duplicate_reason,
        "issues_with_edited_event": edited_any,
        "body_title_chars_total": token_chars,
        "body_title_tokens_estimate_chars_div_4": round(token_chars / 4),
        "first_substantive_human_action_hours": {
            "count": len(first_action_hours),
            "median": round(statistics.median(first_action_hours), 2) if first_action_hours else None,
        },
    }
