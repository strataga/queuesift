import json

import httpx

from app.analysis import analyze_backfill
from app.backfill import GitHubBackfillClient, run_backfill
from app.db import init_db, make_engine

ISSUE = {
    "id": 101,
    "number": 7,
    "title": "Bug example",
    "body": "### Package (Required)\n\n- [x] langchain-perplexity\n\n### Reproduction Steps\n\nrun it\n",
    "state": "closed",
    "state_reason": "completed",
    "labels": [{"name": "bug"}, {"name": "perplexity"}, {"name": "waiting-on-author"}],
    "type": {"name": "Bug"},
    "user": {"login": "reporter"},
    "author_association": "NONE",
    "created_at": "2026-09-01T00:00:00Z",
    "closed_at": "2026-09-03T00:00:00Z",
    "html_url": "https://example.invalid/issues/7",
}
TIMELINE = [
    {
        "id": 1,
        "event": "labeled",
        "actor": {"login": "github-actions[bot]"},
        "created_at": "2026-09-01T00:01:00Z",
        "label": {"name": "perplexity"},
    },
    {
        "id": 2,
        "event": "commented",
        "actor": {"login": "maintainer1"},
        "author_association": "MEMBER",
        "created_at": "2026-09-01T02:00:00Z",
    },
    {
        "id": 3,
        "event": "cross-referenced",
        "actor": {"login": "maintainer1"},
        "created_at": "2026-09-01T03:00:00Z",
        "source": {"issue": {"number": 99}},
    },
]


class TrackingTransport(httpx.MockTransport):
    def __init__(self) -> None:
        self.paths: list[str] = []
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.paths.append(request.url.path)
        if request.url.path.endswith("/timeline"):
            return httpx.Response(200, json=TIMELINE)
        page = request.url.params.get("page")
        return httpx.Response(200, json=[ISSUE] if page == "1" else [])


def _client() -> GitHubBackfillClient:
    return GitHubBackfillClient(
        "langchain-ai/langchain", token="test", transport=TrackingTransport()
    )


def test_resume_skips_stored_timelines_but_refreshes_metadata() -> None:
    transport = TrackingTransport()
    client = GitHubBackfillClient(
        "langchain-ai/langchain", token="test", transport=transport
    )
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    first = run_backfill(engine, client, days=90, today="2026-10-20", reuse_stored=True)
    issue_calls = {c for c in transport.paths if c.endswith("/timeline")}
    assert first.issues_stored == 1 and first.events_stored == 3 and issue_calls
    # Second run: one timeline fetch total would mean a full re-read of the
    # only stored issue; with reuse_stored it must be skipped.
    transport.paths.clear()
    second = run_backfill(engine, client, days=90, today="2026-10-20", reuse_stored=True)
    assert not [c for c in transport.paths if c.endswith("/timeline")]
    assert second.issues_stored == 1 and second.events_stored == 0


def test_backfill_is_idempotent_and_analysis_measures_actors() -> None:
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    client = _client()
    first = run_backfill(engine, client, days=90, today="2026-10-20")
    second = run_backfill(engine, client, days=90, today="2026-10-20")
    assert first.issues_stored == 1 and second.issues_stored == 1

    report = analyze_backfill(engine, repo="langchain-ai/langchain")
    assert report["issues_total"] == 1
    assert report["events_total"] == 3
    assert report["bot_actors"] == ["github-actions[bot]"]
    assert report["maintainer_actors"] == ["maintainer1"]
    assert report["eligible_bug_feature"] == 1
    assert report["workflow_label_counts"]["waiting-on-author"] == 1
    assert report["first_substantive_human_action_hours"]["median"] == 2.0
    assert json.dumps(report)
