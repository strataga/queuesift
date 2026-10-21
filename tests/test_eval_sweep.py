from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.db import IssueRow, init_db, make_engine
from app.eval_baselines import (
    MRE_NEGATIVE_HYPOTHESIS,
    MRE_POSITIVE_HYPOTHESIS,
    STALE_NEGATIVE_HYPOTHESIS,
    STALE_POSITIVE_HYPOTHESIS,
)
from app.eval_sweep import THRESHOLD_GRID, run_threshold_sweep
from app.providers import EmbeddingResult


class FakeEmbedder:
    def embed_texts(self, texts: list[str]) -> EmbeddingResult:
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


def test_run_threshold_sweep_reports_grid_and_validates_retrieval(tmp_path: Path) -> None:
    repo = "test/repo"
    old = "2024-02-02T18:02:57Z"
    new = "2026-09-01T00:00:00Z"
    stale_positive = [1, 2, 3]
    stale_negative = [4, 5, 6]
    mre_positive = [1, 2]
    mre_negative = [3, 4]
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
                    labels_json="[]",
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
                "unknown_members": [5, 6],
            },
        },
    )
    _write_json(titles_path, {"repo": repo, "issues": []})

    report = run_threshold_sweep(
        engine,
        repo=repo,
        manifest_path=manifest_path,
        gold_path=gold_path,
        titles_path=titles_path,
        report_path=report_path,
        embedder=FakeEmbedder(),
    )

    assert report["threshold_grid"] == THRESHOLD_GRID
    assert len(report["stale"]["thresholds"]) == len(THRESHOLD_GRID)
    assert len(report["missing_reproduction"]["thresholds"]) == len(THRESHOLD_GRID)
    zero_stale = next(t for t in report["stale"]["thresholds"] if t["threshold"] == 0.0)
    assert zero_stale["f1"] == pytest.approx(0.8)
    zero_mre = next(
        t for t in report["missing_reproduction"]["thresholds"] if t["threshold"] == 0.0
    )
    assert zero_mre["f1"] == 1.0
    assert report["staged_retrieval_validation"]["timestamp_violations"] == 0
    assert report["staged_retrieval_validation"]["queries"] == 6
    assert report["provider_gates"]["paid_provider_spend_usd"] == 0.0
    assert "duplicate" not in report["stale"]
    assert report_path.exists()
