"""Creation-time evaluation inputs without provider calls.

The loader intentionally projects only creation-time columns from the issue
table. It never reads labels, state, closure metadata, or the timeline table.
Title/body edits are handled by two separate provenance requirements:

- no observed ``edited`` timeline event may exist for a scored issue; and
- every issue with a pre-freeze ``renamed`` event must supply a recovered
  original title.

Those checks use timeline metadata as provenance repair/gating. They are not
model inputs and must not become predictive features.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import IssueEventRow, IssueRow

AS_OF = "2026-10-20T00:00:00Z"
ALLOWED_ISSUE_FIELDS = (
    "repo",
    "number",
    "github_id",
    "title",
    "body",
    "author",
    "author_association",
    "created_at",
)


class CreationTimeIssueInput(BaseModel):
    """Exactly the creation-time fields a scored system may receive."""

    model_config = ConfigDict(extra="forbid")

    repo: str
    number: int
    github_id: int
    title: str
    body: str = ""
    author: str | None = None
    author_association: str | None = None
    created_at: str | None = None
    as_of: str = Field(default=AS_OF)


@dataclass(frozen=True)
class RenameEvent:
    created_at: str
    previous_title: str


def original_title_from_chain(current_title: str, renames: list[RenameEvent]) -> str:
    """Recover the earliest title from a rename chain.

    The timeline API records each rename as ``previous_title`` to
    ``current_title``. The scored input must use the first ``previous_title``,
    not the freeze-time title.
    """
    if not renames:
        return current_title
    earliest = min(renames, key=lambda event: event.created_at)
    return earliest.previous_title


def assert_no_observed_body_edits(engine, *, repo: str, numbers: list[int]) -> None:
    """Fail if the stored timeline contains an observed body edit.

    This is an observed-edit guard, not proof that an unrecorded edit is
    impossible. A scored run must not proceed when this guard fails.
    """
    with Session(engine) as session:
        edited = (
            session.query(IssueEventRow.issue_number)
            .filter(
                IssueEventRow.repo == repo,
                IssueEventRow.issue_number.in_(numbers),
                IssueEventRow.event == "edited",
            )
            .all()
        )
    if edited:
        offenders = sorted({row[0] for row in edited})
        raise ValueError(f"observed body edits for issues: {offenders}")


def missing_title_provenance(
    engine, *, repo: str, numbers: list[int], original_titles: dict[int, str]
) -> list[int]:
    """Return renamed issues lacking recovered original titles."""
    with Session(engine) as session:
        renamed = {
            row[0]
            for row in session.query(IssueEventRow.issue_number)
            .filter(
                IssueEventRow.repo == repo,
                IssueEventRow.issue_number.in_(numbers),
                IssueEventRow.event == "renamed",
            )
            .all()
        }
    return sorted(number for number in renamed if number not in original_titles)


def load_creation_time_inputs(
    engine,
    *,
    repo: str,
    numbers: list[int],
    original_titles: dict[int, str] | None = None,
) -> list[CreationTimeIssueInput]:
    """Load creation-time inputs with forbidden current/outcome state excluded."""
    original_titles = original_titles or {}
    missing = missing_title_provenance(
        engine, repo=repo, numbers=numbers, original_titles=original_titles
    )
    if missing:
        raise ValueError(f"missing original-title provenance for issues: {missing}")
    assert_no_observed_body_edits(engine, repo=repo, numbers=numbers)

    statement = (
        select(
            IssueRow.repo,
            IssueRow.number,
            IssueRow.github_id,
            IssueRow.title,
            IssueRow.body,
            IssueRow.author,
            IssueRow.author_association,
            IssueRow.created_at,
        )
        .where(IssueRow.repo == repo, IssueRow.number.in_(numbers))
        .order_by(IssueRow.number)
    )
    with Session(engine) as session:
        rows = session.execute(statement).mappings().all()
    by_number = {row["number"]: row for row in rows}
    absent = sorted(set(numbers) - set(by_number))
    if absent:
        raise ValueError(f"missing issues in evaluation store: {absent}")

    inputs: list[CreationTimeIssueInput] = []
    for number in sorted(by_number):
        row = by_number[number]
        inputs.append(
            CreationTimeIssueInput(
                repo=row["repo"],
                number=row["number"],
                github_id=row["github_id"],
                title=original_titles.get(number, row["title"] or ""),
                body=row["body"] or "",
                author=row["author"],
                author_association=row["author_association"],
                created_at=row["created_at"],
            )
        )
    return inputs
