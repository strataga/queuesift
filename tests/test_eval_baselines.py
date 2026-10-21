import pytest

from app.eval_baselines import (
    MRE_NEGATIVE_HYPOTHESIS,
    MRE_POSITIVE_HYPOTHESIS,
    issue_text_for_embedding,
    predict_mre_by_template,
    predict_stale_by_age,
    semantic_similarity_predictions,
)
from app.eval_inputs import CreationTimeIssueInput


def _item(**overrides) -> CreationTimeIssueInput:
    values = {
        "repo": "astral-sh/uv",
        "number": 7,
        "github_id": 1,
        "title": "Title",
        "body": "Body.",
        "author": "reporter",
        "author_association": "NONE",
        "created_at": "2024-02-02T18:02:57Z",
    }
    values.update(overrides)
    return CreationTimeIssueInput(**values)


def test_stale_age_baseline_uses_freeze_cutoff() -> None:
    assert predict_stale_by_age(_item()) == 1
    assert predict_stale_by_age(_item(created_at="2026-09-01T00:00:00Z")) == 0
    assert predict_stale_by_age(_item(created_at=None)) == 0
    assert predict_stale_by_age(_item(created_at="not-a-date")) == 0


def test_mre_template_baseline_flags_missing_reproduction() -> None:
    assert predict_mre_by_template(_item(body="No sections here.")) == 1
    assert (
        predict_mre_by_template(_item(body="### Reproduction\nRun this."))
        == 0
    )


def test_issue_text_for_embedding_is_bounded() -> None:
    item = _item(body="x" * 5000)
    assert len(issue_text_for_embedding(item)) == 4000
    assert issue_text_for_embedding(item).startswith("Title")


def _fake_embed(texts: list[str]) -> list[list[float]]:
    vectors = []
    for text in texts:
        if text == MRE_POSITIVE_HYPOTHESIS or "POS" in text:
            vectors.append([1.0, 0.0])
        elif text == MRE_NEGATIVE_HYPOTHESIS or "NEG" in text:
            vectors.append([0.0, 1.0])
        else:
            raise AssertionError(f"unexpected text: {text[:40]}")
    return vectors


def test_semantic_similarity_predictions_use_fixed_hypotheses() -> None:
    predictions = semantic_similarity_predictions(
        _fake_embed,
        ["POS issue", "NEG issue"],
        positive_hypothesis=MRE_POSITIVE_HYPOTHESIS,
        negative_hypothesis=MRE_NEGATIVE_HYPOTHESIS,
    )
    assert predictions == [1, 0]


def test_semantic_similarity_predictions_reject_empty_inputs() -> None:
    with pytest.raises(ValueError):
        semantic_similarity_predictions(
            _fake_embed,
            [],
            positive_hypothesis=MRE_POSITIVE_HYPOTHESIS,
            negative_hypothesis=MRE_NEGATIVE_HYPOTHESIS,
        )
