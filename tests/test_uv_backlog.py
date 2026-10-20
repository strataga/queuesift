import httpx

from app.backfill import GitHubBackfillClient
from app.uv_backlog import eligible_backlog_payload, select_uv_backlog_sample


def listing(number: int, labels: list[str], created: str = "2024-01-01T00:00:00Z") -> dict:
    return {
        "number": number,
        "title": f"issue {number}",
        "created_at": created,
        "updated_at": created,
        "labels": [{"name": name} for name in labels],
    }


def test_uv_backlog_selection_prefers_labels_then_oldest_and_excludes_internal() -> None:
    payloads = [
        listing(10, ["duplicate"], "2025-01-01T00:00:00Z"),
        listing(11, ["needs-mre"], "2024-02-01T00:00:00Z"),
        listing(12, ["needs-mre"], "2024-03-01T00:00:00Z"),
        listing(1, ["bug"], "2023-01-01T00:00:00Z"),
        listing(2, ["bug"], "2023-02-01T00:00:00Z"),
        listing(3, ["internal"], "2022-01-01T00:00:00Z"),
        listing(4, ["security"], "2022-02-01T00:00:00Z"),
    ]
    eligible = [payload for payload in payloads if eligible_backlog_payload(payload)]
    assert {payload["number"] for payload in eligible} == {1, 2, 10, 11, 12}

    selected = select_uv_backlog_sample(payloads, size=4, mre_cap=1)
    assert [selection.number for selection in selected] == [10, 11, 1, 2]
    assert selected[0].source == "current-duplicate-label"
    assert selected[1].source == "current-missing-reproduction-label"
    assert selected[2].source == "oldest-eligible-open-issue"


def test_backfill_client_supports_open_issues_and_single_issue_detail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/issues/7"):
            return httpx.Response(200, json={"id": 1, "number": 7, "title": "t"})
        if request.url.path.endswith("/issues/7/timeline"):
            return httpx.Response(200, json=[])
        if request.url.path == "/repos/astral-sh/uv/issues":
            page = request.url.params.get("page")
            if request.url.params.get("labels") == "needs-mre":
                return httpx.Response(200, json=[])
            return httpx.Response(200, json=[{"number": 7, "labels": []}]) if page == "1" else httpx.Response(200, json=[])
        raise AssertionError(f"unexpected {request.url.path}")

    client = GitHubBackfillClient(
        "astral-sh/uv", token="test", transport=httpx.MockTransport(handler)
    )
    assert [payload["number"] for payload in client.iter_open_issues()] == [7]
    detail = client.fetch_issue_detail(7)
    assert detail.payload["number"] == 7 and detail.timeline == []
