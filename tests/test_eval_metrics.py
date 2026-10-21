import math

import pytest

from app.eval_metrics import (
    confusion_matrix,
    paired_bootstrap_difference,
    precision_recall_f1,
    wilson_interval,
)


def test_confusion_matrix_counts_issue_outcomes() -> None:
    matrix = confusion_matrix([1, 1, 0, 0, 1, 0], [1, 0, 0, 1, 1, 0])
    assert (matrix.true_positives, matrix.true_negatives) == (2, 2)
    assert (matrix.false_positives, matrix.false_negatives) == (1, 1)
    assert matrix.total == 6


def test_precision_recall_f1_handles_zero_denominators() -> None:
    matrix = confusion_matrix([0, 0], [0, 0])
    scores = precision_recall_f1(matrix)
    assert scores == {"accuracy": 1.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}


def test_wilson_interval_contains_estimate_within_bounds() -> None:
    interval = wilson_interval(145, 150)
    assert 0.0 <= interval["lower"] <= interval["estimate"] <= interval["upper"] <= 1.0
    assert math.isclose(interval["estimate"], 145 / 150)
    assert interval["lower"] > 0.9


def test_wilson_interval_rejects_empty_or_invalid_counts() -> None:
    with pytest.raises(ValueError):
        wilson_interval(0, 0)
    with pytest.raises(ValueError):
        wilson_interval(3, 2)


def test_paired_bootstrap_difference_is_deterministic() -> None:
    y_true = [1, 1, 1, 0, 0, 0, 1, 0]
    pred_a = [1, 1, 0, 0, 0, 1, 1, 0]
    pred_b = [1, 0, 0, 0, 1, 1, 0, 0]
    first = paired_bootstrap_difference(
        y_true, pred_a, pred_b, metric="f1", samples=200, seed=20261020
    )
    second = paired_bootstrap_difference(
        y_true, pred_a, pred_b, metric="f1", samples=200, seed=20261020
    )
    assert first == second
    assert first["lower"] <= first["observed"] <= first["upper"]
