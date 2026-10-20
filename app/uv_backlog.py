"""uv backlog cohort selection and storage for Slice 1b.

The backlog target is different from the 90-day creation cohort: these are
already-open issues selected for a stale/duplicate sweep. Current public
labels are selection signals, not ground truth; the accompanying gold rules
require comment/timeline evidence or adjudication before any evaluated claim.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from app.backfill import GitHubBackfillClient, store_issue_with_events
from app.config import load_local_env
from app.db import init_db, make_engine, snapshot_from_github
from app.template_parser import parse_template

EXCLUDED_BACKLOG_LABELS = {
    "internal",
    "internal:automations",
    "internal:ci",
    "internal:ci-flake",
    "internal:releases",
    "internal:testing",
    "project:maintainer-followups",
    "tracking",
    "ep-2026-sprints",
    "security",
    "bot:ai-policy-close",
    "bot:ai-policy-comment",
    "bot:needs-mre-comment",
    "bot:promote",
    "bot:rebase",
}
DUPLICATE_LABEL = "duplicate"
MRE_LABEL = "needs-mre"


class BacklogSelection(BaseModel):
    number: int
    title: str
    created_at: str | None = None
    updated_at: str | None = None
    labels: list[str]
    source: str


class BacklogManifest(BaseModel):
    name: str
    cohort_date: str
    repo: str
    database_filename: str
    sample_size: int
    duplicate_labeled_count: int
    mre_labeled_count: int
    oldest_created_at: str | None = None
    members: list[BacklogSelection]


def _labels(payload: dict) -> list[str]:
    return [label["name"] for label in payload.get("labels", []) if isinstance(label, dict)]


def eligible_backlog_payload(payload: dict) -> bool:
    """Exclude internal, policy, tracking, and security items from the sweep."""
    return not (set(_labels(payload)) & EXCLUDED_BACKLOG_LABELS)


def select_uv_backlog_sample(
    listings: list[dict], *, size: int = 150, mre_cap: int = 50
) -> list[BacklogSelection]:
    """Deterministically prefer anchors, then MRE signals, then oldest stale issues."""
    considered = [payload for payload in listings if eligible_backlog_payload(payload)]
    in_order = sorted(
        considered,
        key=lambda payload: (payload.get("created_at") or "", payload["number"]),
    )

    selected: list[BacklogSelection] = []
    seen: set[int] = set()

    def add(payload: dict, source: str) -> None:
        if payload["number"] in seen:
            return
        seen.add(payload["number"])
        selected.append(
            BacklogSelection(
                number=payload["number"],
                title=payload.get("title", ""),
                created_at=payload.get("created_at"),
                updated_at=payload.get("updated_at"),
                labels=_labels(payload),
                source=source,
            )
        )

    for payload in in_order:
        if len(selected) >= size:
            break
        if DUPLICATE_LABEL in _labels(payload):
            add(payload, "current-duplicate-label")
    mre = [payload for payload in in_order if MRE_LABEL in _labels(payload)]
    for payload in mre[:mre_cap]:
        if len(selected) >= size:
            break
        add(payload, "current-missing-reproduction-label")
    for payload in in_order:
        if len(selected) >= size:
            break
        add(payload, "oldest-eligible-open-issue")
    assert len(selected) <= size
    assert len({s.number for s in selected}) == len(selected)
    return selected


def run_uv_backlog_cohort(
    *,
    client: GitHubBackfillClient,
    database_path: str,
    manifest_path: Path,
    sample_size: int = 150,
    mre_cap: int = 50,
    cohort_date: str,
) -> BacklogManifest:
    """Fetch, store, and manifest one deterministic backlog sample."""
    load_local_env()
    engine = make_engine(f"sqlite+pysqlite:///{database_path}")
    init_db(engine)
    listings = list(client.iter_open_issues(direction="asc"))
    selected = select_uv_backlog_sample(listings, size=sample_size, mre_cap=mre_cap)
    if not selected:
        raise ValueError("no eligible uv backlog issues were listed")

    for selection in selected:
        detail = client.fetch_issue_detail(selection.number)
        snapshot = snapshot_from_github(client.repo, detail.payload)
        parsed = parse_template(snapshot.body)
        store_issue_with_events(
            engine,
            snapshot,
            state_reason=detail.payload.get("state_reason"),
            author_association=detail.payload.get("author_association"),
            closed_at=detail.payload.get("closed_at"),
            declared_packages=parsed.declared_packages,
            package_unsure=parsed.package_unsure,
            events=detail.timeline,
        )
    manifest = BacklogManifest(
        name="uv-backlog-sweep",
        cohort_date=cohort_date,
        repo=client.repo,
        database_filename=Path(database_path).name,
        sample_size=len(selected),
        duplicate_labeled_count=sum(
            1 for selection in selected if DUPLICATE_LABEL in selection.labels
        ),
        mre_labeled_count=sum(1 for selection in selected if MRE_LABEL in selection.labels),
        oldest_created_at=min(
            (selection.created_at or "" for selection in selected), default=None
        ),
        members=selected,
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n")
    return manifest


__all__ = [
    "EXCLUDED_BACKLOG_LABELS",
    "BacklogManifest",
    "BacklogSelection",
    "eligible_backlog_payload",
    "run_uv_backlog_cohort",
    "select_uv_backlog_sample",
]
