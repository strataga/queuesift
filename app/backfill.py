"""Issue/timeline backfill for Slice 1 feasibility. Reads only; never writes to GitHub."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import httpx

from app.db import snapshot_from_github, store_issue_with_events
from app.template_parser import parse_template

API = "https://api.github.com"


@dataclass
class BackfillResult:
    issues_stored: int
    events_stored: int
    requests: int
    since: str


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

    def iter_issues_since(self, since: date, limit: int | None = None):
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        yielded = 0
        with httpx.Client(
            base_url=API, headers=headers, timeout=self.timeout, transport=self.transport
        ) as client:
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
                    timeline: list = []
                    timeline_page = 1
                    while True:
                        events = self._get(
                            client,
                            f"/repos/{self.repo}/issues/{payload['number']}/timeline",
                            {"per_page": 100, "page": timeline_page},
                        )
                        timeline.extend(events)
                        if len(events) < 100:
                            break
                        timeline_page += 1
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
) -> BackfillResult:
    end = date.fromisoformat(today) if today else datetime.now(UTC).date()
    since = end - timedelta(days=days)
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
