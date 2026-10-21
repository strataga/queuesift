"""Outcome snapshots and Markdown digest artifacts (Slice 3b).

Descriptive only: joins stored deterministic proposals with the maintainer
actuals currently stored locally (labels, state, timeline events). No model
calls, no GitHub writes. Agreement claims stay out: this reports what
maintainers have done since, not whether the proposal was right.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.db import IssueEventRow, IssueRow, list_proposals
from app.gold import BOTS, MAINTAINER_ASSOCIATIONS, SUBSTANTIVE_STALE_EVENTS, TIER_A_MAINTAINERS


def _is_maintainer(actor: str | None, association: str | None) -> bool:
    if actor in TIER_A_MAINTAINERS:
        return True
    return bool(association) and association in MAINTAINER_ASSOCIATIONS


def _is_bot(actor: str | None) -> bool:
    return bool(actor) and (actor.endswith("[bot]") or actor in BOTS)


def score_outcomes(engine, repo: str) -> dict:
    """Snapshot one row per stored issue: current state plus maintainer activity."""
    with Session(engine) as session:
        issues = (
            session.query(IssueRow).filter_by(repo=repo).order_by(IssueRow.number).all()
        )
        events = session.query(IssueEventRow).filter_by(repo=repo).all()
    by_issue: dict[int, list] = {}
    for event in events:
        by_issue.setdefault(event.issue_number, []).append(event)
    rows: list[dict] = []
    for issue in issues:
        labels = json.loads(issue.labels_json or "[]")
        maintainer_events = [
            event
            for event in by_issue.get(issue.number, [])
            if event.event in SUBSTANTIVE_STALE_EVENTS
            and _is_maintainer(event.actor, event.actor_association)
            and not _is_bot(event.actor)
        ]
        rows.append(
            {
                "number": issue.number,
                "title": issue.title,
                "state": issue.state,
                "labels": labels,
                "has_maintainer_action": bool(maintainer_events),
                "maintainer_event_count": len(maintainer_events),
            }
        )
    return {
        "repo": repo,
        "generated_at": datetime.now(UTC).isoformat(),
        "issues": rows,
    }


def write_digest_artifact(
    engine, repo: str, report: dict, path: Path, date_str: str
) -> Path:
    """Write the daily Markdown digest: proposals grouped by route with outcomes."""
    proposals = list_proposals(engine)
    proposals = [p for p in proposals if p.repo == repo]
    by_number = {row["number"]: row for row in report["issues"]}
    groups: dict[str, list] = {}
    for proposal in proposals:
        groups.setdefault(proposal.route, []).append(proposal)
    lines = [
        f"# QueueSift shadow digest — {repo} — {date_str}",
        "",
        (
            f"{len(proposals)} stored deterministic proposals (shadow mode; "
            "no GitHub writes, no paid calls)."
        ),
        "",
    ]
    for route in sorted(groups):
        lines.append(f"## Route: {route} ({len(groups[route])})")
        lines.append("")
        for proposal in sorted(groups[route], key=lambda p: p.issue_number):
            outcome = by_number.get(proposal.issue_number, {})
            state = outcome.get("state", "unknown")
            title = outcome.get("title", "")
            acted = outcome.get("has_maintainer_action")
            flag = "maintainer-active" if acted else "no-maintainer-action-yet"
            missing = ", ".join(proposal.missing_fields) or "(none)"
            lines.append(
                f"- #{proposal.issue_number} {title} [{state}, {flag}] "
                f"missing: {missing} "
                f"(https://github.com/{repo}/issues/{proposal.issue_number})"
            )
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path
