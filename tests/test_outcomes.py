"""Slice 3b: outcome snapshots describe stored maintainer activity only."""

from __future__ import annotations

from app.db import init_db, make_engine, store_issue_with_events, store_proposal
from app.models import IssueSnapshot, Proposal
from app.outcomes import score_outcomes, write_digest_artifact

REPO = "astral-sh/uv"


def _seed(engine, number: int, events: list[dict]) -> None:
    snapshot = IssueSnapshot(
        repo=REPO,
        number=number,
        github_id=2000 + number,
        title=f"Outcome probe {number}",
        body="### Description\nNeeds triage.",
    )
    store_issue_with_events(
        engine,
        snapshot,
        state_reason=None,
        author_association=None,
        closed_at=None,
        declared_packages=[],
        package_unsure=False,
        events=events,
    )
    store_proposal(
        engine,
        snapshot,
        Proposal(
            repo=REPO,
            issue_number=number,
            missing_fields=["reproduction"],
            route="assisted",
            rationale=["Bug report has no usable reproduction section."],
        ),
    )


MAINTAINER_COMMENT = {
    "id": 1,
    "event": "commented",
    "actor": {"login": "charliermarsh"},
    "author_association": "MEMBER",
    "created_at": "2026-10-21T01:00:00Z",
}
BOT_LABEL = {
    "id": 2,
    "event": "labeled",
    "actor": {"login": "github-actions[bot]"},
    "created_at": "2026-10-21T02:00:00Z",
    "label": {"name": "needs-mre"},
}


def test_score_outcomes_flags_maintainer_action_only(tmp_path) -> None:
    engine = make_engine(f"sqlite+pysqlite:///{tmp_path}/out.db")
    init_db(engine)
    _seed(engine, 21, [MAINTAINER_COMMENT])
    _seed(engine, 22, [BOT_LABEL])
    report = score_outcomes(engine, REPO)
    by_number = {row["number"]: row for row in report["issues"]}
    assert by_number[21]["has_maintainer_action"] is True
    assert by_number[21]["maintainer_event_count"] == 1
    assert by_number[22]["has_maintainer_action"] is False


def test_write_digest_artifact_groups_routes_with_outcomes(tmp_path) -> None:
    engine = make_engine(f"sqlite+pysqlite:///{tmp_path}/out.db")
    init_db(engine)
    _seed(engine, 21, [MAINTAINER_COMMENT])
    report = score_outcomes(engine, REPO)
    path = tmp_path / "digests" / "2026-10-21.md"
    write_digest_artifact(engine, REPO, report, path, "2026-10-21")
    text = path.read_text()
    assert "Route: assisted (1)" in text
    assert "#21 Outcome probe 21 [open, maintainer-active]" in text
    assert "no GitHub writes" in text
