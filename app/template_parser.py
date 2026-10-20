"""Deterministic parser for rendered GitHub issue-form bodies.

Mirrors the observable contract of LangChain's issue templates: sections are
``### Heading`` blocks and the package is declared with checked boxes in the
``Package (Required)`` section. No model calls happen here.
"""

from __future__ import annotations

import re

from app.models import ParsedTemplate

_HEADING = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
_CHECKED = re.compile(r"^-\s+\[x\]\s+(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
_ANY_CHECKBOX = re.compile(r"^-\s+\[( |x)\]\s+", re.MULTILINE | re.IGNORECASE)
_UNSURE = "other / not sure / general"
_NO_RESPONSE = {"", "_no response_", "none", "n/a"}


def _split_sections(body: str) -> dict[str, str]:
    matches = list(_HEADING.finditer(body))
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[match.group(1).strip().lower()] = body[start:end].strip()
    return sections


def _nonempty(text: str | None) -> bool:
    return text is not None and text.strip().lower() not in _NO_RESPONSE and len(text.strip()) > 3


def parse_template(body: str) -> ParsedTemplate:
    sections = _split_sections(body or "")
    package_text = ""
    checklist_text = ""
    for heading, text in sections.items():
        if heading.startswith("package"):
            package_text = text
        if "checklist" in heading:
            checklist_text = text

    checked_packages = [m.group(1).strip() for m in _CHECKED.finditer(package_text)]
    package_unsure = any(p.lower() == _UNSURE for p in checked_packages)
    declared = [p for p in checked_packages if p.lower() != _UNSURE]

    checklist_total = len(_ANY_CHECKBOX.findall(checklist_text)) if checklist_text else 0
    checklist_checked = len(_CHECKED.findall(checklist_text)) if checklist_text else 0

    def section_containing(fragment: str) -> str:
        for heading, text in sections.items():
            if fragment in heading:
                return text
        return ""

    return ParsedTemplate(
        declared_packages=declared,
        package_unsure=package_unsure,
        checklist_checked=checklist_checked,
        checklist_total=checklist_total,
        sections={k: v for k, v in sections.items()},
        has_reproduction=_nonempty(section_containing("reproduction")),
        has_error_text=_nonempty(section_containing("error message")),
        has_description=_nonempty(section_containing("description")),
    )
