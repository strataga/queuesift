"""Read-only shadow digest pages (Slice 3a).

Plain server-rendered HTML over stored proposals and frozen eval reports.
No writes, no model calls, no GitHub fetches at request time.
"""

from __future__ import annotations

import html

from app.models import Proposal

EVAL_REPORTS: list[tuple[str, str]] = [
    (
        "uv-qualified-baselines-2026-10-21.json",
        "Deterministic age/template baselines vs local semantic baselines (stale 150, MRE 85).",
    ),
    (
        "uv-threshold-sweep-2026-10-21.json",
        "Descriptive 7-point F1 sweep over the fixed semantic margin; no threshold adopted.",
    ),
    (
        "uv-draft-spot-check-2026-10-21.json",
        "Narrow local missing-evidence drafts for the first 5 MRE positives; 5/5 gated.",
    ),
]

PAGE_CSS = (
    "body{font-family:system-ui,-apple-system,sans-serif;max-width:56rem;"
    "margin:2rem auto;padding:0 1rem;line-height:1.5;color:#1a1a1a}"
    "nav a{margin-right:1rem}"
    "table{border-collapse:collapse;width:100%}"
    "th,td{border:1px solid #ccc;padding:0.4rem 0.6rem;text-align:left;vertical-align:top}"
    ".meta{color:#444;font-size:0.9rem}"
)


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        f"<style>{PAGE_CSS}</style></head><body>"
        "<nav><a href='/'>Overview</a><a href='/digest'>Digest</a>"
        "<a href='/evals'>Evals</a></nav>"
        f"<h1>{html.escape(title)}</h1>{body}</body></html>"
    )


def overview_html(issue_count: int, proposal_count: int, scope: str) -> str:
    body = (
        f"<p class='meta'>Scope: {html.escape(scope)} · shadow mode · "
        "read-only · no GitHub writes · no paid calls</p>"
        f"<p>Stored issues: <strong>{issue_count}</strong><br>"
        f"Stored proposals: <strong>{proposal_count}</strong></p>"
        "<p>Start with the <a href='/digest'>daily digest</a>, then open a "
        "proposal, then check <a href='/evals'> eval reports</a>.</p>"
    )
    return _page("QueueSift shadow overview", body)


def digest_html(proposals: list[Proposal]) -> str:
    if not proposals:
        return _page(
            "QueueSift digest",
            "<p>No stored proposals in this database. Point "
            "<code>DATABASE_URL</code> at the uv-backlog SQLite file and reload.</p>",
        )
    groups: dict[str, list[Proposal]] = {}
    for proposal in proposals:
        groups.setdefault(proposal.route, []).append(proposal)
    parts = [f"<p class='meta'>{len(proposals)} stored proposals grouped by route.</p>"]
    for route in sorted(groups):
        parts.append(f"<h2>Route: {html.escape(route)} ({len(groups[route])})</h2>")
        parts.append("<table><tr><th>Issue</th><th>Declared</th><th>Missing</th></tr>")
        for proposal in groups[route]:
            declared = ", ".join(proposal.declared_packages) or "(none)"
            missing = ", ".join(proposal.missing_fields) or "(none)"
            parts.append(
                "<tr><td><a href='/proposals/"
                f"{proposal.issue_number}'>{html.escape(proposal.repo)}"
                f"#{proposal.issue_number}</a></td>"
                f"<td>{html.escape(proposal.issue_type or 'unknown')}; "
                f"{html.escape(declared)}</td>"
                f"<td>{html.escape(missing)}</td></tr>"
            )
        parts.append("</table>")
    return _page("QueueSift digest", "".join(parts))


def proposal_html(proposal: Proposal) -> str:
    lines = "".join(f"<li>{html.escape(reason)}</li>" for reason in proposal.rationale)
    external = f"https://github.com/{proposal.repo}/issues/{proposal.issue_number}"
    body = (
        f"<p><a href='{html.escape(external)}'>{html.escape(external)}</a> "
        "(external link; opened by you, never fetched by this page)</p>"
        f"<p>Route: <strong>{html.escape(proposal.route)}</strong> · "
        f"system: {html.escape(proposal.system)}</p>"
        f"<p>Declared type: {html.escape(proposal.issue_type or 'unknown')}<br>"
        f"Declared packages: {html.escape(', '.join(proposal.declared_packages) or '(none)')}<br>"
        f"Missing fields: {html.escape(', '.join(proposal.missing_fields) or '(none)')}</p>"
        f"<h2>Rationale</h2><ul>{lines}</ul>"
    )
    return _page(f"Proposal {proposal.repo}#{proposal.issue_number}", body)


def evals_html() -> str:
    items = "".join(
        f"<li><a href='/evals/{html.escape(name)}'>{html.escape(name)}</a> — "
        f"{html.escape(description)}</li>"
        for name, description in EVAL_REPORTS
    )
    return _page(
        "QueueSift eval reports",
        f"<ul>{items}</ul><p class='meta'>Frozen non-paid Slice 2 outputs; "
        "descriptive only where denominators are small.</p>",
    )
