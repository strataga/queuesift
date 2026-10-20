"""QueueSift CLI: process one real issue into a shadow digest (Slice 0)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.db import init_db, make_engine, snapshot_from_github, store_proposal
from app.github_client import fetch_issue
from app.providers import check_providers
from app.triage import propose, render_digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="queuesift", description=__doc__)
    source = parser.add_mutually_exclusive_group(required=False)
    source.add_argument("--issue-json", type=Path, help="Saved GitHub issue JSON file")
    source.add_argument("--issue", type=int, help="Issue number to fetch live from GitHub")
    source.add_argument(
        "--check-providers",
        action="store_true",
        help="Verify configured draft/embedding models and print JSON evidence",
    )
    parser.add_argument("--repo", default="langchain-ai/langchain")
    parser.add_argument("--database-url", default=None, help="Override DATABASE_URL")
    args = parser.parse_args(argv)

    if args.check_providers:
        sys.stdout.write(check_providers().model_dump_json(indent=2) + "\n")
        return 0
    if args.issue_json is None and args.issue is None:
        parser.error("one of --issue-json, --issue, or --check-providers is required")

    payload = (
        json.loads(args.issue_json.read_text())
        if args.issue_json
        else fetch_issue(args.repo, args.issue)
    )
    snapshot = snapshot_from_github(args.repo, payload)
    proposal = propose(snapshot)
    engine = make_engine(args.database_url)
    init_db(engine)
    store_proposal(engine, snapshot, proposal)
    sys.stdout.write(render_digest([proposal]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
