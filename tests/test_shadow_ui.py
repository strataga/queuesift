"""Slice 3a: read-only shadow digest pages over stored proposals."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import (
    init_db,
    make_engine,
    seed_deterministic_proposals,
    store_issue_with_events,
    store_proposal,
)
from app.main import app
from app.models import IssueSnapshot, Proposal


def _seeded_engine(tmp_path):
    engine = make_engine(f"sqlite+pysqlite:///{tmp_path}/shadow.db")
    init_db(engine)
    issue = IssueSnapshot(
        repo="astral-sh/uv",
        number=1,
        github_id=101,
        title="Stale triage probe",
        body="x",
    )
    store_proposal(
        engine,
        issue,
        Proposal(
            repo="astral-sh/uv",
            issue_number=1,
            issue_type="bug",
            declared_packages=["core"],
            missing_fields=["reproduction"],
            route="assisted",
            rationale=["Bug report has no usable reproduction section."],
        ),
    )
    return engine


def test_overview_digest_detail_evals_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{tmp_path}/empty.db")
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert "shadow mode" in client.get("/").text
    digest = client.get("/digest")
    assert digest.status_code == 200
    assert "No stored proposals" in digest.text
    assert client.get("/proposals/1").status_code == 404
    evals = client.get("/evals")
    assert evals.status_code == 200
    assert "uv-qualified-baselines" in evals.text
    assert client.get("/evals/unknown.json").status_code == 404


def test_seed_deterministic_proposals_is_idempotent(tmp_path):
    engine = make_engine(f"sqlite+pysqlite:///{tmp_path}/seed.db")
    init_db(engine)
    for number in (11, 12):
        store_issue_with_events(
            engine,
            IssueSnapshot(
                repo="astral-sh/uv",
                number=number,
                github_id=1000 + number,
                title=f"Seed probe {number}",
                body="### Description\nNeeds triage.",
            ),
            state_reason=None,
            author_association=None,
            closed_at=None,
            declared_packages=[],
            package_unsure=False,
            events=[],
        )
    assert seed_deterministic_proposals(engine, "astral-sh/uv") == 2
    assert seed_deterministic_proposals(engine, "astral-sh/uv") == 2


def test_digest_lists_seeded_proposal(tmp_path, monkeypatch):
    engine = _seeded_engine(tmp_path)
    monkeypatch.setenv("DATABASE_URL", str(engine.url))
    client = TestClient(app)
    overview = client.get("/")
    assert "Stored proposals: <strong>1</strong>" in overview.text
    digest = client.get("/digest")
    assert digest.status_code == 200
    assert "astral-sh/uv#1" in digest.text
    assert "reproduction" in digest.text
    assert "open; no-maintainer-action-yet" in digest.text
    detail = client.get("/proposals/1")
    assert detail.status_code == 200
    assert "no usable reproduction" in detail.text
    assert "github.com/astral-sh/uv/issues/1" in detail.text


def test_digest_html_renders_outcome_flags() -> None:
    from app.shadow_ui import digest_html

    proposal = Proposal(
        repo="astral-sh/uv",
        issue_number=9,
        missing_fields=[],
        route="human",
        rationale=[],
    )
    text = digest_html(
        [proposal],
        {9: {"number": 9, "state": "closed", "has_maintainer_action": True}},
    )
    assert "closed; maintainer-active" in text
    assert "—" in digest_html([proposal])
    assert "—" in digest_html([proposal], {})
