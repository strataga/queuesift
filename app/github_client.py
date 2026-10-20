"""GitHub reads for Slice 0. Shadow mode: this module never writes."""

from __future__ import annotations

import os

import httpx

API = "https://api.github.com"


def fetch_issue(repo: str, number: int, token: str | None = None) -> dict:
    token = token or os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(timeout=30, headers=headers) as client:
        response = client.get(f"{API}/repos/{repo}/issues/{number}")
        response.raise_for_status()
        payload = response.json()
    if "pull_request" in payload:
        raise ValueError(f"{repo}#{number} is a pull request, not an issue")
    return payload
