import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db import IssueEventRow, IssueRow, init_db, make_engine
from app.eval_inputs import (
    RenameEvent,
    load_creation_time_inputs,
    original_title_from_chain,
)


def _engine_with_issue():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    with Session(engine) as session:
        session.add(
            IssueRow(
                repo="astral-sh/uv",
                github_id=1,
                number=7,
                title="Current edited title",
                body="Creation body with required version.",
                issue_type="bug",
                state="closed",
                state_reason="duplicate",
                author="reporter",
                author_association="NONE",
                created_at="2024-02-02T18:02:57Z",
                closed_at="2024-03-01T00:00:00Z",
                labels_json='["needs-mre", "duplicate"]',
                declared_packages_json="[]",
                package_unsure=False,
                body_hash="test",
            )
        )
        session.add(
            IssueEventRow(
                repo="astral-sh/uv",
                issue_number=7,
                event_key="comment-1",
                event="commented",
                actor="maintainer",
                actor_association="MEMBER",
                created_at="2024-02-03T00:00:00Z",
            )
        )
        session.add(
            IssueEventRow(
                repo="astral-sh/uv",
                issue_number=7,
                event_key="label-1",
                event="labeled",
                actor="maintainer",
                actor_association="MEMBER",
                created_at="2024-02-03T01:00:00Z",
                label_name="needs-mre",
            )
        )
        session.commit()
    return engine


def test_creation_time_loader_excludes_future_state_labels_and_timeline() -> None:
    engine = _engine_with_issue()
    (result,) = load_creation_time_inputs(engine, repo="astral-sh/uv", numbers=[7])

    assert result.model_dump() == {
        "repo": "astral-sh/uv",
        "number": 7,
        "github_id": 1,
        "title": "Current edited title",
        "body": "Creation body with required version.",
        "author": "reporter",
        "author_association": "NONE",
        "created_at": "2024-02-02T18:02:57Z",
        "as_of": "2026-10-20T00:00:00Z",
    }


def test_creation_time_loader_requires_title_provenance_for_renames() -> None:
    engine = _engine_with_issue()
    with Session(engine) as session:
        session.add(
            IssueRow(
                repo="astral-sh/uv",
                github_id=2,
                number=8,
                title="Later title",
                body="Body.",
                state="open",
                labels_json="[]",
                declared_packages_json="[]",
                package_unsure=False,
                body_hash="test",
            )
        )
        session.add(
            IssueEventRow(
                repo="astral-sh/uv",
                issue_number=8,
                event_key="rename-1",
                event="renamed",
                actor="maintainer",
                created_at="2024-02-04T00:00:00Z",
            )
        )
        session.commit()

    try:
        load_creation_time_inputs(engine, repo="astral-sh/uv", numbers=[7, 8])
    except ValueError as error:
        assert "missing original-title provenance for issues: [8]" in str(error)
    else:
        raise AssertionError("renamed issue without provenance must fail")

    seven, eight = load_creation_time_inputs(
        engine, repo="astral-sh/uv", numbers=[7, 8], original_titles={8: "Original title"}
    )
    assert (seven.number, seven.title) == (7, "Current edited title")
    assert (eight.number, eight.title) == (8, "Original title")


def test_creation_time_loader_rejects_observed_body_edits() -> None:
    engine = _engine_with_issue()
    with Session(engine) as session:
        session.add(
            IssueEventRow(
                repo="astral-sh/uv",
                issue_number=7,
                event_key="edit-1",
                event="edited",
                actor="reporter",
                created_at="2024-02-04T00:00:00Z",
            )
        )
        session.commit()

    try:
        load_creation_time_inputs(engine, repo="astral-sh/uv", numbers=[7])
    except ValueError as error:
        assert "observed body edits for issues: [7]" in str(error)
    else:
        raise AssertionError("observed body edits must fail")


def test_original_title_uses_earliest_rename() -> None:
    renames = [
        RenameEvent(created_at="2024-02-18T00:00:00Z", previous_title="Second title"),
        RenameEvent(created_at="2024-02-17T00:00:00Z", previous_title="Original title"),
    ]
    assert original_title_from_chain("Current title", renames) == "Original title"
    assert original_title_from_chain("Current title", []) == "Current title"


def test_title_provenance_file_covers_observed_renamed_members() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "provenance"
        / "uv-backlog-original-titles-2026-10-20.json"
    )
    provenance = json.loads(path.read_text())
    numbers = [item["number"] for item in provenance["issues"]]

    assert len(numbers) == 27
    assert numbers == sorted(set(numbers))
    assert all(
        item["earliest_rename"]["created_at"] < "2026-10-20T00:00:00Z"
        for item in provenance["issues"]
    )
