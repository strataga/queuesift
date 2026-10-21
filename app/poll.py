"""Incremental shadow polling for Slice 3b. Reads only; never writes to GitHub."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.backfill import GitHubBackfillClient
from app.db import (
    IssueRow,
    last_poll_at,
    record_poll_run,
    snapshot_from_github,
    store_issue_with_events,
)
from app.template_parser import parse_template
from app.triage import propose

DEFAULT_LIMIT = 30
DEFAULT_LOOKBACK_DAYS = 7


@dataclass
class PollResult:
    new_issues: int
    refreshed_issues: int
    requests: int
    since: str
    ran_at: str


def _stored_numbers(engine, repo: str) -> set[int]:
    with Session(engine) as session:
        return {
            row[0]
            for row in session.query(IssueRow.number).filter_by(repo=repo).all()
        }


def run_poll(
    engine,
    client: GitHubBackfillClient,
    *,
    since: str | None = None,
    limit: int = DEFAULT_LIMIT,
    now: str | None = None,
) -> PollResult:
    """Poll issues updated since `since` (default: last poll, else 7 days).

    New numbers get full detail+timeline; already-stored numbers in the window
    get a full refresh so timelines stay current. Bounded by limit; each issue
    costs 1 detail request plus its timeline pages. Proposals are deterministic
    only — no model calls.
    """
    ran_at = now or datetime.now(UTC).isoformat()
    if since is None:
        since = last_poll_at(engine, client.repo) or (
            datetime.now(UTC) - timedelta(days=DEFAULT_LOOKBACK_DAYS)
        ).isoformat()
    stored = _stored_numbers(engine, client.repo)
    before = client.requests
    new_issues = 0
    refreshed_issues = 0
    for payload in client.iter_updated_since(since, limit):
        if "pull_request" in payload:
            continue
        number = payload["number"]
        is_new = number not in stored
        detail = client.fetch_issue_detail(number)
        full = detail.payload
        snapshot = snapshot_from_github(client.repo, full)
        parsed = parse_template(snapshot.body)
        store_issue_with_events(
            engine,
            snapshot,
            state_reason=full.get("state_reason"),
            author_association=full.get("author_association"),
            closed_at=full.get("closed_at"),
            declared_packages=parsed.declared_packages,
            package_unsure=parsed.package_unsure,
            events=detail.timeline,
        )
        from app.db import store_proposal

        store_proposal(engine, snapshot, propose(snapshot))
        stored.add(number)
        if is_new:
            new_issues += 1
        else:
            refreshed_issues += 1
    result = PollResult(
        new_issues=new_issues,
        refreshed_issues=refreshed_issues,
        requests=client.requests - before,
        since=since,
        ran_at=ran_at,
    )
    record_poll_run(
        engine,
        repo=client.repo,
        ran_at=ran_at,
        since=since,
        new_issues=new_issues,
        refreshed_issues=refreshed_issues,
        requests=result.requests,
    )
    return result
