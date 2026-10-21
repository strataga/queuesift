"""Minimal persistence for Slice 0 (Postgres in Compose, SQLite in tests)."""

from __future__ import annotations

import json
import os

from sqlalchemy import Boolean, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.models import IssueSnapshot, Proposal

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+pysqlite:///./queuesift.db")


class Base(DeclarativeBase):
    pass


class IssueRow(Base):
    __tablename__ = "issues"

    repo: Mapped[str] = mapped_column(String, primary_key=True)
    github_id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int]
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, default="")
    issue_type: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, default="open")
    state_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    author_association: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
    closed_at: Mapped[str | None] = mapped_column(String, nullable=True)
    labels_json: Mapped[str] = mapped_column(Text, default="[]")
    declared_packages_json: Mapped[str] = mapped_column(Text, default="[]")
    package_unsure: Mapped[bool] = mapped_column(Boolean, default=False)
    body_hash: Mapped[str] = mapped_column(String, default="")


class IssueEventRow(Base):
    __tablename__ = "issue_events"

    repo: Mapped[str] = mapped_column(String, primary_key=True)
    issue_number: Mapped[int] = mapped_column(primary_key=True)
    event_key: Mapped[str] = mapped_column(String, primary_key=True)
    event: Mapped[str] = mapped_column(String)
    actor: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_association: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
    label_name: Mapped[str | None] = mapped_column(String, nullable=True)
    source_issue_number: Mapped[int | None] = mapped_column(nullable=True)


class ProposalRow(Base):
    __tablename__ = "proposals"

    repo: Mapped[str] = mapped_column(String, primary_key=True)
    issue_number: Mapped[int] = mapped_column(primary_key=True)
    system: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


class PollRunRow(Base):
    """One incremental poll pass per repo (read-only sync bookkeeping)."""

    __tablename__ = "poll_runs"

    repo: Mapped[str] = mapped_column(String, primary_key=True)
    ran_at: Mapped[str] = mapped_column(String, primary_key=True)
    since: Mapped[str | None] = mapped_column(String, nullable=True)
    new_issues: Mapped[int] = mapped_column(default=0)
    refreshed_issues: Mapped[int] = mapped_column(default=0)
    requests: Mapped[int] = mapped_column(default=0)


def record_poll_run(
    engine,
    *,
    repo: str,
    ran_at: str,
    since: str | None,
    new_issues: int,
    refreshed_issues: int,
    requests: int,
) -> None:
    with Session(engine) as session:
        session.add(
            PollRunRow(
                repo=repo,
                ran_at=ran_at,
                since=since,
                new_issues=new_issues,
                refreshed_issues=refreshed_issues,
                requests=requests,
            )
        )
        session.commit()


def last_poll_at(engine, repo: str) -> str | None:
    from sqlalchemy.exc import OperationalError

    try:
        with Session(engine) as session:
            row = (
                session.query(PollRunRow)
                .filter(PollRunRow.repo == repo)
                .order_by(PollRunRow.ran_at.desc())
                .first()
            )
            return row.ran_at if row else None
    except OperationalError:
        return None


def make_engine(database_url: str | None = None):
    # Read at call time so CLI-loaded .env.local values take effect.
    return create_engine(database_url or os.environ.get("DATABASE_URL") or DATABASE_URL)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def store_proposal(engine, issue: IssueSnapshot, proposal: Proposal) -> None:
    """Idempotent upsert keyed by (repo, github issue id / number, system)."""
    with Session(engine) as session:
        row = session.get(IssueRow, (issue.repo, issue.github_id))
        if row is None:
            session.add(
                IssueRow(
                    repo=issue.repo,
                    github_id=issue.github_id,
                    number=issue.number,
                    title=issue.title,
                    body=issue.body,
                    issue_type=issue.issue_type,
                )
            )
        else:
            row.title, row.body, row.issue_type = issue.title, issue.body, issue.issue_type
        prow = session.get(ProposalRow, (proposal.repo, proposal.issue_number, proposal.system))
        payload = proposal.model_dump_json()
        if prow is None:
            session.add(
                ProposalRow(
                    repo=proposal.repo,
                    issue_number=proposal.issue_number,
                    system=proposal.system,
                    payload=payload,
                )
            )
        else:
            prow.payload = payload
        session.commit()


def count_proposals(engine) -> int:
    from sqlalchemy.exc import OperationalError

    try:
        with Session(engine) as session:
            return session.query(ProposalRow).count()
    except OperationalError:
        return 0


def count_issues(engine) -> int:
    from sqlalchemy.exc import OperationalError

    try:
        with Session(engine) as session:
            return session.query(IssueRow).count()
    except OperationalError:
        return 0


def list_proposals(engine, limit: int = 200) -> list[Proposal]:
    from sqlalchemy.exc import OperationalError

    try:
        with Session(engine) as session:
            rows = session.query(ProposalRow).order_by(ProposalRow.issue_number).limit(limit).all()
            return [proposal_from_row(row) for row in rows]
    except OperationalError:
        return []


def list_issue_snapshots(engine, repo: str | None = None) -> list[IssueSnapshot]:
    from sqlalchemy.exc import OperationalError

    try:
        with Session(engine) as session:
            query = session.query(IssueRow).order_by(IssueRow.number)
            if repo is not None:
                query = query.filter(IssueRow.repo == repo)
            snapshots: list[IssueSnapshot] = []
            for row in query.all():
                try:
                    labels = json.loads(row.labels_json or "[]")
                except ValueError:
                    labels = []
                snapshots.append(
                    IssueSnapshot(
                        repo=row.repo,
                        number=row.number,
                        github_id=row.github_id,
                        title=row.title or "",
                        body=row.body or "",
                        state=row.state or "open",
                        labels=[str(label) for label in labels],
                        issue_type=row.issue_type,
                        author=row.author,
                        created_at=row.created_at,
                    )
                )
            return snapshots
    except OperationalError:
        return []


def seed_deterministic_proposals(engine, repo: str | None = None) -> int:
    """Run the Slice 0 deterministic proposer over stored issues (local only).

    Idempotent: re-running overwrites the same (repo, number, system) rows.
    Returns the number of issues seeded.
    """
    from app.triage import propose

    snapshots = list_issue_snapshots(engine, repo)
    for snapshot in snapshots:
        store_proposal(engine, snapshot, propose(snapshot))
    return len(snapshots)


def get_proposal(engine, issue_number: int) -> Proposal | None:
    from sqlalchemy.exc import OperationalError

    try:
        with Session(engine) as session:
            rows = (
                session.query(ProposalRow)
                .filter(ProposalRow.issue_number == issue_number)
                .order_by(ProposalRow.system)
                .all()
            )
            if not rows:
                return None
            return proposal_from_row(rows[0])
    except OperationalError:
        return None


def snapshot_from_github(repo: str, payload: dict) -> IssueSnapshot:
    issue_type = payload.get("type")
    return IssueSnapshot(
        repo=repo,
        number=payload["number"],
        github_id=payload["id"],
        title=payload.get("title", ""),
        body=payload.get("body") or "",
        html_url=payload.get("html_url", ""),
        state=payload.get("state", "open"),
        labels=[label["name"] for label in payload.get("labels", []) if isinstance(label, dict)],
        issue_type=issue_type.get("name") if isinstance(issue_type, dict) else None,
        author=(payload.get("user") or {}).get("login"),
        created_at=payload.get("created_at"),
    )


def proposal_from_row(row: ProposalRow) -> Proposal:
    return Proposal(**json.loads(row.payload))


def store_issue_with_events(
    engine,
    issue: IssueSnapshot,
    *,
    state_reason: str | None,
    author_association: str | None,
    closed_at: str | None,
    declared_packages: list[str],
    package_unsure: bool,
    events: list[dict],
) -> None:
    """Idempotent backfill upsert for one issue and its timeline events."""
    import hashlib

    with Session(engine) as session:
        row = session.get(IssueRow, (issue.repo, issue.github_id))
        values = {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body,
            "issue_type": issue.issue_type,
            "state": issue.state,
            "state_reason": state_reason,
            "author": issue.author,
            "author_association": author_association,
            "created_at": issue.created_at,
            "closed_at": closed_at,
            "labels_json": json.dumps(issue.labels),
            "declared_packages_json": json.dumps(declared_packages),
            "package_unsure": package_unsure,
            "body_hash": hashlib.sha256(issue.body.encode()).hexdigest(),
        }
        if row is None:
            session.add(IssueRow(repo=issue.repo, github_id=issue.github_id, **values))
        else:
            for key, value in values.items():
                setattr(row, key, value)
        for index, event in enumerate(events):
            event_key = str(event.get("id") or f"idx-{index}-{event.get('event')}-{event.get('created_at')}")
            actor = (event.get("actor") or event.get("user") or {}).get("login")
            label = event.get("label") or {}
            source = event.get("source")
            if isinstance(source, dict):
                source_issue = (source.get("issue") or {}).get("number")
            else:
                source_issue = source if isinstance(source, int) else None
            existing = session.get(IssueEventRow, (issue.repo, issue.number, event_key))
            event_values = {
                "event": str(event.get("event") or "unknown"),
                "actor": actor,
                "actor_association": event.get("author_association"),
                "created_at": event.get("created_at"),
                "label_name": label.get("name") if isinstance(label, dict) else None,
                "source_issue_number": source_issue,
            }
            if existing is None:
                session.add(
                    IssueEventRow(
                        repo=issue.repo,
                        issue_number=issue.number,
                        event_key=event_key,
                        **event_values,
                    )
                )
            else:
                for key, value in event_values.items():
                    setattr(existing, key, value)
        session.commit()
