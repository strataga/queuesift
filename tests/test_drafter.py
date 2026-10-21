from app.drafter import (
    build_mre_evidence,
    check_draft_gates,
    draft_mre_request,
)
from app.eval_inputs import CreationTimeIssueInput
from app.providers import DraftOutput, DraftResult


def _item(**overrides) -> CreationTimeIssueInput:
    values = {
        "repo": "astral-sh/uv",
        "number": 7,
        "github_id": 1,
        "title": "Title",
        "body": "### Reproduction\nRun it.",
        "author": "reporter",
        "author_association": "NONE",
        "created_at": "2024-02-02T18:02:57Z",
    }
    values.update(overrides)
    return CreationTimeIssueInput(**values)


class _FakeProvider:
    name = "fake-local"

    def __init__(self, output: DraftOutput) -> None:
        self.output = output
        self.seen_chunks: list = []

    def draft_reply(self, instruction: str, chunks) -> DraftResult:
        assert "maintainer reply" in instruction
        self.seen_chunks = list(chunks)
        return DraftResult(
            provider=self.name,
            model="fake-draft",
            latency_ms=1,
            prompt_tokens=10,
            output_tokens=5,
            output=self.output,
        )


def test_build_mre_evidence_uses_creation_fields_only() -> None:
    chunks = build_mre_evidence(_item())
    assert [chunk.chunk_id for chunk in chunks] == ["E-title", "E-body", "E-signal"]
    assert "Title" in chunks[0].text
    assert "reproduction section" in chunks[2].text


def test_draft_mre_request_validates_gates() -> None:
    provider = _FakeProvider(
        DraftOutput(
            reply="Please share a minimal reproduction.",
            citations=["E-body", "E-signal"],
            requested_info=["minimal reproduction"],
        )
    )
    result = draft_mre_request(provider, _item())
    assert [chunk.chunk_id for chunk in provider.seen_chunks] == [
        "E-title",
        "E-body",
        "E-signal",
    ]
    gates = check_draft_gates(result, ["E-title", "E-body", "E-signal"])
    assert gates == {
        "citations_subset": True,
        "requested_info_nonempty": True,
        "reply_nonempty": True,
    }


def test_spot_check_records_provider_failures_without_aborting(tmp_path) -> None:
    from sqlalchemy.orm import Session

    from app.db import IssueRow, init_db, make_engine
    from app.drafter import run_draft_spot_check
    from app.providers import ProviderError

    class _FailingProvider:
        name = "fake-local"

        def draft_reply(self, instruction, chunks):
            raise ProviderError("draft failed schema/citation validation twice")

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    with Session(engine) as session:
        session.add(
            IssueRow(
                repo="test/repo",
                github_id=1,
                number=1,
                title="Title",
                body="No sections here.",
                state="open",
                labels_json="[]",
                declared_packages_json="[]",
                package_unsure=False,
                body_hash="test",
            )
        )
        session.commit()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"repo": "test/repo", "members": [{"number": 1, "title": "Title"}]}'
    )
    gold = tmp_path / "gold.json"
    gold.write_text(
        '{"repo": "test/repo", "as_of": "2026-10-20T00:00:00Z", '
        '"missing_reproduction": {"positives": [{"number": 1}], '
        '"negatives": [], "unknown_members": []}}'
    )
    titles = tmp_path / "titles.json"
    titles.write_text('{"repo": "test/repo", "issues": []}')
    report = run_draft_spot_check(
        engine,
        repo="test/repo",
        manifest_path=manifest,
        gold_path=gold,
        titles_path=titles,
        report_path=tmp_path / "report.json",
        provider=_FailingProvider(),
        limit=1,
    )
    assert report["pass_count"] == 0
    assert report["drafts"][0]["gates_pass"] is False
    assert "error" in report["drafts"][0]


def test_check_draft_gates_rejects_unknown_citations() -> None:
    provider = _FakeProvider(
        DraftOutput(reply="x", citations=["ZZZ"], requested_info=[])
    )
    result = draft_mre_request(provider, _item())
    gates = check_draft_gates(result, ["E-title", "E-body", "E-signal"])
    assert gates["citations_subset"] is False
    assert gates["requested_info_nonempty"] is False
