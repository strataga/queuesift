"""Minimal persistence for Slice 0 (Postgres in Compose, SQLite in tests)."""

from __future__ import annotations

import json
import os

from sqlalchemy import String, Text, create_engine
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


class ProposalRow(Base):
    __tablename__ = "proposals"

    repo: Mapped[str] = mapped_column(String, primary_key=True)
    issue_number: Mapped[int] = mapped_column(primary_key=True)
    system: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


def make_engine(database_url: str | None = None):
    return create_engine(database_url or DATABASE_URL)


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
    with Session(engine) as session:
        return session.query(ProposalRow).count()


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
