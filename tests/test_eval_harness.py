from pathlib import Path

from sqlalchemy.orm import Session

from app.db import IssueRow, init_db, make_engine
from app.eval_baselines import (
    MRE_NEGATIVE_HYPOTHESIS,
    MRE_POSITIVE_HYPOTHESIS,
    STALE_NEGATIVE_HYPOTHESIS,
    STALE_POSITIVE_HYPOTHESIS,
)
from app.eval_harness import run_qualified_baselines
from app.providers import EmbeddingResult


class FakeEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        self.calls += 1
        vectors = []
        for text in texts:
            if text in (MRE_POSITIVE_HYPOTHESIS, STALE_POSITIVE_HYPOTHESIS) or "MARK-POS" in text:
                vectors.append([1.0, 0.0])
            elif text in (MRE_NEGATIVE_HYPOTHESIS, STALE_NEGATIVE_HYPOTHESIS) or "MARK-NEG" in text:
                vectors.append([0.0, 1.0])
            else:
                raise AssertionError(f"unexpected text: {text[:40]}")
        return EmbeddingResult(
            provider="fake-local",
            model="fake-embed",
            latency_ms=0,
            dimensions=2,
            normalized=True,
            vectors=vectors,
        )


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(__import__("json").dumps(payload))


def test_run_qualified_baselines_scores_only_qualified_gold(tmp_path: Path) -> None:
    repo = "test/repo"
    old = "2024-02-02T18:02:57Z"
    new = "2026-09-01T00:00:00Z"
    stale_positive = list(range(1, 56))
    stale_negative = list(range(56, 61))
    mre_positive = list(range(1, 31))
    mre_negative = list(range(31, 61))
    manifest_numbers = stale_positive + stale_negative

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    with Session(engine) as session:
        for number in manifest_numbers:
            marker = "MARK-POS" if number in mre_positive else "MARK-NEG"
            body = "No sections here." if number in mre_positive else "### Reproduction\nRun it."
            session.add(
                IssueRow(
                    repo=repo,
                    github_id=number,
                    number=number,
                    title=f"{marker} title {number}",
                    body=body,
                    state="open",
                    labels_json='["needs-mre"]' if number in mre_positive else "[]",
                    declared_packages_json="[]",
                    package_unsure=False,
                    body_hash="test",
                    author="reporter",
                    author_association="NONE",
                    created_at=old if number in stale_positive else new,
                )
            )
        session.commit()

    manifest_path = tmp_path / "manifest.json"
    gold_path = tmp_path / "gold.json"
    titles_path = tmp_path / "titles.json"
    report_path = tmp_path / "report.json"
    _write_json(
        manifest_path,
        {
            "repo": repo,
            "members": [{"number": n, "title": f"title {n}"} for n in manifest_numbers],
        },
    )
    _write_json(
        gold_path,
        {
            "repo": repo,
            "as_of": "2026-10-20T00:00:00Z",
            "stale": {
                "positive_members": stale_positive,
                "non_positive_members": stale_negative,
            },
            "missing_reproduction": {
                "positives": [{"number": n} for n in mre_positive],
                "negatives": [{"number": n} for n in mre_negative],
                "unknown_members": [],
            },
        },
    )
    _write_json(titles_path, {"repo": repo, "issues": []})

    embedder = FakeEmbedder()
    report = run_qualified_baselines(
        engine,
        repo=repo,
        manifest_path=manifest_path,
        gold_path=gold_path,
        titles_path=titles_path,
        report_path=report_path,
        embedder=embedder,
        bootstrap_samples=100,
        bootstrap_seed=20261020,
    )

    assert report["inputs"]["members"] == 60
    assert report["provider_gates"]["paid_provider_spend_usd"] == 0.0
    assert report["stale"]["deterministic_age"]["f1"] == 1.0
    assert report["missing_reproduction"]["deterministic_template"]["n"] == 60
    assert report["missing_reproduction"]["local_semantic"]["n"] == 60
    assert report["local_embeddings"]["stale"]["provider"] == "fake-local"
    assert report_path.exists()
    assert "duplicate" not in report["stale"]
