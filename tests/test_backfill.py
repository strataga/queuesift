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


def _client() -> GitHubBackfillClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/timeline"):
            return httpx.Response(200, json=TIMELINE)
        page = request.url.params.get("page")
        return httpx.Response(200, json=[ISSUE] if page == "1" else [])

    return GitHubBackfillClient(
        "langchain-ai/langchain", token="test", transport=httpx.MockTransport(handler)
    )


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
