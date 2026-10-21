"""Binary evaluation metrics with uncertainty for qualified Slice 2 baselines.

Only task-appropriate classification metrics are implemented. There are no
text-generation scores, no LLM-as-judge scores, and no provider-specific
quality claims here.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfusionMatrix:
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int

    @property
    def total(self) -> int:
        return (
            self.true_positives
            + self.true_negatives
            + self.false_positives
            + self.false_negatives
        )


def _check_binary(values: list[int], name: str) -> None:
    if any(value not in (0, 1) for value in values):
        raise ValueError(f"{name} must contain only 0/1 labels")


def confusion_matrix(y_true: list[int], y_pred: list[int]) -> ConfusionMatrix:
    """Count issue-level binary outcomes in input order."""
    if len(y_true) != len(y_pred):
        raise ValueError("truth and prediction lists must have the same length")
    if not y_true:
        raise ValueError("truth and prediction lists must not be empty")
    _check_binary(y_true, "y_true")
    _check_binary(y_pred, "y_pred")

    true_positives = sum(1 for actual, predicted in zip(y_true, y_pred) if actual == 1 and predicted == 1)
    true_negatives = sum(1 for actual, predicted in zip(y_true, y_pred) if actual == 0 and predicted == 0)
    false_positives = sum(1 for actual, predicted in zip(y_true, y_pred) if actual == 0 and predicted == 1)
    false_negatives = sum(1 for actual, predicted in zip(y_true, y_pred) if actual == 1 and predicted == 0)
    return ConfusionMatrix(
        true_positives=true_positives,
        true_negatives=true_negatives,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def precision_recall_f1(matrix: ConfusionMatrix) -> dict[str, float]:
    """Precision/recall/F1 with zero-denominator outcomes defined as 0.0."""
    precision = _safe_ratio(
        matrix.true_positives, matrix.true_positives + matrix.false_positives
    )
    recall = _safe_ratio(
        matrix.true_positives, matrix.true_positives + matrix.false_negatives
    )
    f1 = _safe_ratio(
        2 * precision * recall, precision + recall
    )
    accuracy = _safe_ratio(
        matrix.true_positives + matrix.true_negatives, matrix.total
    )
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> dict[str, float]:
    """Two-sided Wilson score interval for a binomial proportion at 95% by default."""
    if trials <= 0:
        raise ValueError("Wilson interval requires at least one trial")
    if not 0 <= successes <= trials:
        raise ValueError("successes must be between 0 and trials")
    if z <= 0:
        raise ValueError("z must be positive")

    center = (successes + z * z / 2) / (trials + z * z)
    half_width = (
        z
        * math.sqrt(
            successes * (trials - successes) / trials + z * z / 4
        )
        / (trials + z * z)
    )
    return {
        "lower": max(0.0, center - half_width),
        "estimate": successes / trials,
        "upper": min(1.0, center + half_width),
    }


def _metric_value(
    y_true: list[int], y_pred: list[int], metric: str
) -> float:
    matrix = confusion_matrix(y_true, y_pred)
    scores = precision_recall_f1(matrix)
    if metric not in ("accuracy", "f1"):
        raise ValueError("paired bootstrap supports only accuracy and f1")
    return scores[metric]


def paired_bootstrap_difference(
    y_true: list[int],
    pred_a: list[int],
    pred_b: list[int],
    *,
    metric: str = "f1",
    samples: int = 2000,
    seed: int = 20261020,
) -> dict[str, float]:
    """Paired bootstrap CI for metric(A) minus metric(B), resampling issues.

    The pairing is by issue: each bootstrap replicate draws issue indices with
    replacement and scores both systems on exactly the same replicate.
    """
    if len(y_true) != len(pred_a) or len(y_true) != len(pred_b):
        raise ValueError("truth and prediction lists must have the same length")
    if not y_true:
        raise ValueError("truth and prediction lists must not be empty")
    if samples < 100:
        raise ValueError("bootstrap samples must be at least 100")

    rng = random.Random(seed)
    count = len(y_true)
    differences: list[float] = []
    for _ in range(samples):
        indices = [rng.randrange(count) for _ in range(count)]
        differences.append(
            _metric_value(
                [y_true[i] for i in indices],
                [pred_a[i] for i in indices],
                metric,
            )
            - _metric_value(
                [y_true[i] for i in indices],
                [pred_b[i] for i in indices],
                metric,
            )
        )

    differences.sort()
    lower_index = int(0.025 * samples)
    upper_index = min(samples - 1, int(0.975 * samples))
    return {
        "observed": _metric_value(y_true, pred_a, metric)
        - _metric_value(y_true, pred_b, metric),
        "lower": differences[lower_index],
        "upper": differences[upper_index],
        "samples": float(samples),
        "seed": float(seed),
    }
