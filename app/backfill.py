"""Issue/timeline backfill for Slice 1 feasibility. Reads only; never writes to GitHub."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from app.db import IssueRow, snapshot_from_github, store_issue_with_events
from app.template_parser import parse_template

API = "https://api.github.com"


@dataclass
class BackfillResult:
    issues_stored: int
    events_stored: int
    requests: int
    since: str


@dataclass
class IssueDetail:
    payload: dict
    timeline: list


class GitHubBackfillClient:
    def __init__(
        self,
        repo: str,
        token: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.repo = repo
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.transport = transport
        self.timeout = timeout
        self.requests = 0
        self._stored_issue_numbers: set[int] | None = None

    def _get(self, client: httpx.Client, path: str, params: dict) -> list:
        for attempt in range(4):
            self.requests += 1
            response = client.get(path, params=params)
            if response.status_code in (403, 429) and attempt < 3:
                retry_after = response.headers.get("retry-after")
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                raise TypeError(f"expected list from {path}, got {type(data).__name__}")
            return data
        raise RuntimeError(f"rate limited repeatedly at {path}")

    def _new_client(self) -> httpx.Client:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return httpx.Client(
            base_url=API, headers=headers, timeout=self.timeout, transport=self.transport
        )

    def _fetch_all_timeline(self, client: httpx.Client, number: int) -> list:
        timeline: list = []
        timeline_page = 1
        while True:
            events = self._get(
                client,
                f"/repos/{self.repo}/issues/{number}/timeline",
                {"per_page": 100, "page": timeline_page},
            )
            timeline.extend(events)
            if len(events) < 100:
                break
            timeline_page += 1
        return timeline

    def iter_open_issues(
        self,
        *,
        labels: str | None = None,
        sort: str = "created",
        direction: str = "asc",
    ):
        """Yield open backlog issues oldest-first by default without timelines."""
        with self._new_client() as client:
            page = 1
            while True:
                params = {
                    "state": "open",
                    "per_page": 100,
                    "page": page,
                    "sort": sort,
                    "direction": direction,
                }
                if labels:
                    params["labels"] = labels
                batch = self._get(client, f"/repos/{self.repo}/issues", params)
                if not batch:
                    return
                for payload in batch:
                    if "pull_request" in payload:
                        continue
                    yield payload
                if len(batch) < 100:
                    return
                page += 1

    def iter_updated_since(self, since_iso: str, limit: int):
        """Yield issue payloads updated since an ISO timestamp, newest first.

        Pull requests are skipped without counting toward limit, so a queue
        with heavy PR traffic cannot eat the poll budget. Read-only; timeline
        fetches happen per issue in the poll step, not here.
        """
        with self._new_client() as client:
            page = 1
            yielded = 0
            while yielded < limit:
                batch = self._get(
                    client,
                    f"/repos/{self.repo}/issues",
                    {
                        "state": "all",
                        "per_page": 100,
                        "page": page,
                        "sort": "updated",
                        "direction": "desc",
                        "since": since_iso,
                    },
                )
                if not batch:
                    return
                for payload in batch:
                    if "pull_request" in payload:
                        continue
                    yield payload
                    yielded += 1
                    if yielded >= limit:
                        return
                if len(batch) < 100:
                    return
                page += 1

    def fetch_issue_detail(self, number: int) -> IssueDetail:
        """Fetch one issue payload and its complete timeline."""
        with self._new_client() as client:
            response_path = f"/repos/{self.repo}/issues/{number}"
            self.requests += 1
            response = client.get(response_path)
            response.raise_for_status()
            payload = response.json()
            if "pull_request" in payload:
                raise ValueError(f"{self.repo}#{number} is a pull request, not an issue")
            return IssueDetail(payload=payload, timeline=self._fetch_all_timeline(client, number))

    def iter_issues_since(self, since: date, limit: int | None = None):
        yielded = 0
        with self._new_client() as client:
            page = 1
            while True:
                batch = self._get(
                    client,
                    f"/repos/{self.repo}/issues",
                    {
                        "state": "all",
                        "per_page": 100,
                        "page": page,
                        "sort": "created",
                        "direction": "desc",
                    },
                )
                if not batch:
                    return
                stop = False
                stored_numbers = self._stored_issue_numbers or set()
                for payload in batch:
                    created = str(payload.get("created_at") or "")[:10]
                    try:
                        created_date = date.fromisoformat(created)
                    except ValueError:
                        continue
                    if created_date < since:
                        stop = True
                        continue
                    if "pull_request" in payload:
                        continue
                    if payload["number"] in stored_numbers:
                        # Campaign resume: metadata refresh only; timeline
                        # fetched on an earlier pass and left stored.
                        yield payload, []
                        continue
                    timeline = self._fetch_all_timeline(client, payload["number"])
                    yielded += 1
                    yield payload, timeline
                    if limit is not None and yielded >= limit:
                        return
                if stop and batch and str(batch[-1].get("created_at") or "")[:10] < since.isoformat():
                    return
                page += 1


def run_backfill(
    engine,
    client: GitHubBackfillClient,
    *,
    days: int = 90,
    today: str | None = None,
    limit: int | None = None,
    reuse_stored: bool = False,
) -> BackfillResult:
    """Resume semantics: with reuse_stored, previously stored issues contribute
    metadata refreshes only; their timeline fetches are skipped and previously
    stored events are left untouched. Use only within one backfill campaign;
    do not rely on it across days of live queue movement, since new events on
    already-stored issues would be missed.
    """
    end = date.fromisoformat(today) if today else datetime.now(UTC).date()
    since = end - timedelta(days=days)
    if reuse_stored:
        with Session(engine) as session:
            client._stored_issue_numbers = {
                row[0]
                for row in session.query(IssueRow.number)
                .filter_by(repo=client.repo)
                .all()
            }
    issues_stored = 0
    events_stored = 0
    for payload, timeline in client.iter_issues_since(since, limit=limit):
        snapshot = snapshot_from_github(client.repo, payload)
        parsed = parse_template(snapshot.body)
        store_issue_with_events(
            engine,
            snapshot,
            state_reason=payload.get("state_reason"),
            author_association=payload.get("author_association"),
            closed_at=payload.get("closed_at"),
            declared_packages=parsed.declared_packages,
            package_unsure=parsed.package_unsure,
            events=timeline,
        )
        issues_stored += 1
        events_stored += len(timeline)
    return BackfillResult(
        issues_stored=issues_stored,
        events_stored=events_stored,
        requests=client.requests,
        since=since.isoformat(),
    )
