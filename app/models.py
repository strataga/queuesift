"""Typed snapshots and proposals for QueueSift Slice 0."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class IssueSnapshot(BaseModel):
    """Creation-time view of one GitHub issue (no later comments)."""

    repo: str
    number: int
    github_id: int
    title: str
    body: str = ""
    html_url: str = ""
    state: str = "open"
    labels: list[str] = Field(default_factory=list)
    issue_type: str | None = None
    author: str | None = None
    created_at: str | None = None


class ParsedTemplate(BaseModel):
    """Deterministic fields extracted from the rendered issue-form body."""

    declared_packages: list[str] = Field(default_factory=list)
    package_unsure: bool = False
    checklist_checked: int = 0
    checklist_total: int = 0
    sections: dict[str, str] = Field(default_factory=dict)
    has_reproduction: bool = False
    has_error_text: bool = False
    has_description: bool = False


Route = Literal["auto-draft", "assisted", "human"]


class Proposal(BaseModel):
    """Deterministic Slice 0 proposal. Semantic model fields arrive in Slice 2."""

    repo: str
    issue_number: int
    issue_type: str | None = None
    declared_packages: list[str] = Field(default_factory=list)
    package_unsure: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    route: Route = "human"
    rationale: list[str] = Field(default_factory=list)
    system: str = "deterministic-slice0"
