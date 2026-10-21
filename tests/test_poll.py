"""Slice 3b: incremental poll is read-only, bounded, and recorded."""

from __future__ import annotations

import httpx

from app.backfill import GitHubBackfillClient
from app.db import init_db, last_poll_at, make_engine, store_issue_with_events
from app.models import IssueSnapshot
from app.poll import run_poll

REPO = "astral-sh/uv"


def _payload(number: int, updated: str) -> dict:
    return {
        "id": 1000 + number,
        "number": number,
        "title": f"Poll probe {number}",
        "body": "### Description\nNeeds triage.",
        "state": "open",
        "state_reason": None,
        "labels": [],
        "type": None,
        "user": {"login": "reporter"},
        "author_association": "NONE",
        "created_at": "2026-10-01T00:00:00Z",
        "updated_at": updated,
        "closed_at": None,
        "html_url": f"https://example.invalid/{number}",
    }


class PollTransport(httpx.MockTransport):
    def __init__(self, listing: list[dict]) -> None:
        self.listing = listing
        self.paths: list[str] = []
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.paths.append(request.url.path)
        if request.url.path.endswith("/timeline"):
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/issues"):
            page = request.url.params.get("page", "1")
            return httpx.Response(200, json=self.listing if page == "1" else [])
        number = int(request.url.path.rsplit("/", 1)[-1])
        match = next(p for p in self.listing if p["number"] == number)
        return httpx.Response(200, json=match)


def _seed_known(engine) -> None:
    store_issue_with_events(
        engine,
        IssueSnapshot(
            repo=REPO,
            number=7,
            github_id=1007,
            title="Poll probe 7",
            body="### Description\nNeeds triage.",
        ),
        state_reason=None,
        author_association=None,
        closed_at=None,
        declared_packages=[],
        package_unsure=False,
        events=[],
    )


def test_poll_stores_new_and_refreshes_known() -> None:
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    _seed_known(engine)
    listing = [_payload(7, "2026-10-21T10:00:00Z"), _payload(8, "2026-10-21T11:00:00Z")]
    client = GitHubBackfillClient(REPO, token="test", transport=PollTransport(listing))
    result = run_poll(engine, client, since="2026-10-21T00:00:00Z", limit=10)
    assert (result.new_issues, result.refreshed_issues) == (1, 1)
    assert result.requests == 1 + 2 * 2  # listing + detail/timeline per issue
    assert last_poll_at(engine, REPO) == result.ran_at


def test_poll_skips_pull_requests_without_spending_limit() -> None:
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    pr = _payload(9, "2026-10-21T12:00:00Z")
    pr["pull_request"] = {"url": "https://example.invalid/pr/9"}
    listing = [pr, _payload(10, "2026-10-21T09:00:00Z")]
    client = GitHubBackfillClient(REPO, token="test", transport=PollTransport(listing))
    result = run_poll(engine, client, since="2026-10-21T00:00:00Z", limit=1)
    assert (result.new_issues, result.refreshed_issues) == (1, 0)


def test_poll_is_bounded_and_second_pass_is_quiet() -> None:
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    listing = [_payload(n, "2026-10-21T10:00:00Z") for n in (1, 2, 3)]
    client = GitHubBackfillClient(REPO, token="test", transport=PollTransport(listing))
    first = run_poll(engine, client, since="2026-10-21T00:00:00Z", limit=2)
    assert first.new_issues == 2
    quiet = PollTransport([])
    client2 = GitHubBackfillClient(REPO, token="test", transport=quiet)
    second = run_poll(engine, client2, limit=10)
    assert (second.new_issues, second.refreshed_issues) == (0, 0)
    assert second.since == first.ran_at
