"""Slice 0 deterministic triage: preserve declared metadata, flag exact gaps."""

from __future__ import annotations

from app.models import IssueSnapshot, Proposal
from app.template_parser import parse_template


def propose(issue: IssueSnapshot) -> Proposal:
    parsed = parse_template(issue.body)
    missing: list[str] = []
    rationale: list[str] = []

    if not parsed.declared_packages and not parsed.package_unsure:
        missing.append("package")
        rationale.append("No package checkbox selected in the template body.")
    if parsed.package_unsure:
        rationale.append("Submitter declared package as unsure; package inference is in scope.")
    issue_type = (issue.issue_type or "").lower()
    is_bug = issue_type == "bug" or "bug" in [label.lower() for label in issue.labels]
    if is_bug and not parsed.has_reproduction:
        missing.append("reproduction")
        rationale.append("Bug report has no usable reproduction section.")
    if is_bug and not parsed.has_error_text:
        rationale.append("No error text section content; may be a no-exception behaviour bug.")
    if not parsed.has_description and not parsed.has_reproduction:
        missing.append("description")
        rationale.append("Neither a description nor a reproduction section has usable content.")

    if missing:
        route = "assisted"
        rationale.append("Deterministic gaps found; a missing-information draft may apply in Slice 2.")
    else:
        route = "human"
        rationale.append("No deterministic gaps; semantic triage arrives in Slice 2.")

    return Proposal(
        repo=issue.repo,
        issue_number=issue.number,
        issue_type=issue.issue_type,
        declared_packages=parsed.declared_packages,
        package_unsure=parsed.package_unsure,
        missing_fields=missing,
        route=route,  # type: ignore[arg-type]
        rationale=rationale,
    )


def render_digest(proposals: list[Proposal]) -> str:
    lines = ["# QueueSift daily digest (shadow)", ""]
    for p in proposals:
        lines.append(f"## {p.repo}#{p.issue_number} — route: {p.route}")
        lines.append(f"- Declared type: {p.issue_type or 'unknown'}")
        lines.append(f"- Declared packages: {', '.join(p.declared_packages) or '(none)'}")
        if p.package_unsure:
            lines.append("- Package declared unsure: inference in scope")
        lines.append(f"- Missing fields: {', '.join(p.missing_fields) or '(none)'}")
        for reason in p.rationale:
            lines.append(f"- {reason}")
        lines.append("")
    return "\n".join(lines)
