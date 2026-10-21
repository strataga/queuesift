"""Narrow local-only drafter for missing-reproduction requests plus claim gates.

This module orchestrates evidence building and draft validation only. It never
selects which issues to score: callers pass already-qualified gold members.
All drafts are labelled with their actual provider and model.
"""

from __future__ import annotations

from pathlib import Path

from app.eval_inputs import CreationTimeIssueInput, load_creation_time_inputs
from app.providers import DraftResult, EvidenceChunk, ProviderError
from app.template_parser import parse_template

MAX_BODY_CHARS = 2000

DRAFT_INSTRUCTION = (
    "Draft a short maintainer reply for this GitHub issue that requests "
    "exactly the missing reproduction or diagnostic evidence. Cite only the "
    "evidence chunk IDs that support each request. Write each cited ID "
    "exactly as given, for example E-body: no brackets, quotes, prefixes, "
    "or extra characters around an ID. Do not invent facts that "
    "are not in the evidence."
)


def build_mre_evidence(item: CreationTimeIssueInput) -> list[EvidenceChunk]:
    """Build evidence chunks from creation-time fields only."""
    parsed = parse_template(item.body)
    findings = []
    if parsed.has_reproduction:
        findings.append("The report includes a reproduction section.")
    else:
        findings.append("The report has no reproduction section.")
    if parsed.has_error_text:
        findings.append("The report includes error text.")
    else:
        findings.append("The report has no error-text section.")
    return [
        EvidenceChunk(chunk_id="E-title", text=f"Issue title: {item.title}"),
        EvidenceChunk(chunk_id="E-body", text=item.body[:MAX_BODY_CHARS]),
        EvidenceChunk(chunk_id="E-signal", text=" ".join(findings)),
    ]


def check_draft_gates(
    result: DraftResult, allowed_chunk_ids: list[str]
) -> dict[str, bool]:
    """Verify a draft cites only supplied evidence and requests information."""
    allowed = set(allowed_chunk_ids)
    return {
        "citations_subset": all(
            citation in allowed for citation in result.output.citations
        ),
        "requested_info_nonempty": bool(result.output.requested_info),
        "reply_nonempty": bool(result.output.reply.strip()),
    }


def draft_mre_request(provider, item: CreationTimeIssueInput) -> DraftResult:
    """Draft a missing-evidence request for one qualified issue."""
    return provider.draft_reply(DRAFT_INSTRUCTION, build_mre_evidence(item))


def run_draft_spot_check(
    engine,
    *,
    repo: str,
    manifest_path: Path | str,
    gold_path: Path | str,
    titles_path: Path | str,
    report_path: Path | str,
    provider,
    limit: int = 5,
) -> dict:
    """Draft requests for the first `limit` MRE positives by issue number."""
    import json

    manifest = json.loads(Path(manifest_path).read_text())
    gold = json.loads(Path(gold_path).read_text())
    titles = json.loads(Path(titles_path).read_text())
    if manifest["repo"] != repo or gold["repo"] != repo or titles["repo"] != repo:
        raise ValueError("manifest, gold, and title provenance must match the repo")
    positives = sorted(item["number"] for item in gold["missing_reproduction"]["positives"])
    sample = positives[:limit]
    if len(sample) < limit:
        raise ValueError("not enough MRE positives for the spot-check sample")
    original_titles = {item["number"]: item["original_title"] for item in titles["issues"]}
    inputs = load_creation_time_inputs(
        engine, repo=repo, numbers=sample, original_titles=original_titles
    )
    by_number = {item.number: item for item in inputs}

    drafts = []
    for number in sample:
        chunks = build_mre_evidence(by_number[number])
        try:
            result = draft_mre_request(provider, by_number[number])
        except ProviderError as error:
            drafts.append(
                {
                    "number": number,
                    "provider": getattr(provider, "name", "unknown"),
                    "model": None,
                    "latency_ms": None,
                    "prompt_tokens": None,
                    "output_tokens": None,
                    "gates": {
                        "citations_subset": False,
                        "requested_info_nonempty": False,
                        "reply_nonempty": False,
                    },
                    "gates_pass": False,
                    "error": str(error)[:300],
                }
            )
            continue
        gates = check_draft_gates(
            result, [chunk.chunk_id for chunk in chunks]
        )
        drafts.append(
            {
                "number": number,
                "provider": result.provider,
                "model": result.model,
                "latency_ms": result.latency_ms,
                "prompt_tokens": result.prompt_tokens,
                "output_tokens": result.output_tokens,
                "gates": gates,
                "gates_pass": all(gates.values()),
                "citations": result.output.citations,
                "requested_info": result.output.requested_info,
                "reply_preview": result.output.reply[:300],
            }
        )
    report = {
        "repo": repo,
        "as_of": gold["as_of"],
        "sample": sample,
        "sample_basis": "first N MRE positives by issue number; spot-check only",
        "provider_gates": {
            "openai_used": False,
            "paid_provider_calls": 0,
            "paid_provider_spend_usd": 0.0,
        },
        "drafts": drafts,
        "pass_count": sum(1 for draft in drafts if draft["gates_pass"]),
    }
    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report
