"""QueueSift CLI: process one real issue into a shadow digest (Slice 0)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.analysis import analyze_backfill
from app.backfill import GitHubBackfillClient, run_backfill
from app.config import load_local_env
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
    source.add_argument("--backfill-days", type=int, help="Backfill issues/timelines created in last N days")
    source.add_argument(
        "--analyze-backfill", action="store_true", help="Print feasibility analysis JSON"
    )
    parser.add_argument("--repo", default="langchain-ai/langchain")
    parser.add_argument("--database-url", default=None, help="Override DATABASE_URL")
    parser.add_argument("--limit", type=int, default=None, help="Backfill issue limit (smoke runs)")
    args = parser.parse_args(argv)

    load_local_env()
    if args.check_providers:
        sys.stdout.write(check_providers().model_dump_json(indent=2) + "\n")
        return 0
    if args.backfill_days is not None:
        engine = make_engine(args.database_url)
        init_db(engine)
        result = run_backfill(
            engine, GitHubBackfillClient(args.repo), days=args.backfill_days, limit=args.limit
        )
        sys.stdout.write(json.dumps(result.__dict__, indent=2) + "\n")
        return 0
    if args.analyze_backfill:
        engine = make_engine(args.database_url)
        init_db(engine)
        sys.stdout.write(json.dumps(analyze_backfill(engine, repo=args.repo), indent=2) + "\n")
        return 0
    if args.issue_json is None and args.issue is None:
        parser.error(
            "one of --issue-json, --issue, --check-providers, --backfill-days, "
            "or --analyze-backfill is required"
        )

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
