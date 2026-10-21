"""Qualified preliminary baselines for stale and secondary-MRE evaluation.

Deterministic rules use only creation-time inputs. The local semantic baseline
uses fixed natural-language hypotheses and local embeddings; the hypotheses
were written before scoring and are not tuned on the frozen gold.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from datetime import datetime

from app.eval_inputs import AS_OF, CreationTimeIssueInput
from app.template_parser import parse_template

MAX_ISSUE_CHARS = 4000
STALE_OBSERVATION_CUTOFF = "2026-04-23T00:00:00Z"

MRE_POSITIVE_HYPOTHESIS = (
    "This GitHub issue report is missing a reproduction, log, environment, "
    "configuration, setup steps, or another diagnostic artifact needed to "
    "reproduce the reported problem."
)
MRE_NEGATIVE_HYPOTHESIS = (
    "This GitHub issue report includes enough reproduction, logs, environment, "
    "configuration, and setup detail to reproduce the reported problem."
)
STALE_POSITIVE_HYPOTHESIS = (
    "This GitHub issue will remain without accepted-maintainer action for at "
    "least 180 days."
)
STALE_NEGATIVE_HYPOTHESIS = (
    "This GitHub issue will receive accepted-maintainer action within 180 days."
)


def issue_text_for_embedding(item: CreationTimeIssueInput) -> str:
    """Bounded creation-time text for local embedding baselines."""
    return f"{item.title}\n\n{item.body}"[:MAX_ISSUE_CHARS]


def predict_stale_by_age(item: CreationTimeIssueInput) -> int:
    """Predict stale when creation is at least 180 days before the freeze."""
    if not item.created_at:
        return 0
    try:
        created = datetime.fromisoformat(item.created_at)
        cutoff = datetime.fromisoformat(STALE_OBSERVATION_CUTOFF)
        freeze = datetime.fromisoformat(AS_OF)
    except ValueError:
        return 0
    if created.tzinfo is None or cutoff.tzinfo is None or freeze.tzinfo is None:
        return 0
    return 1 if created < cutoff <= freeze else 0


def predict_mre_by_template(item: CreationTimeIssueInput) -> int:
    """Predict missing reproduction when the creation body has no reproduction section."""
    return 0 if parse_template(item.body).has_reproduction else 1


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("similarity vectors must have the same nonzero length")
    left_norm = math.sqrt(math.fsum(v * v for v in left))
    right_norm = math.sqrt(math.fsum(v * v for v in right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("similarity vectors must not be zero vectors")
    return math.fsum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _batched_vectors(
    embed_texts: Callable[[list[str]], list[list[float]]],
    texts: list[str],
    batch_size: int = 50,
) -> list[list[float]]:
    if batch_size <= 0:
        raise ValueError("batch size must be positive")
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = embed_texts(texts[start : start + batch_size])
        if len(batch) != len(texts[start : start + batch_size]):
            raise ValueError("embedding batch returned the wrong number of vectors")
        vectors.extend([[float(value) for value in vector] for vector in batch])
    return vectors


def semantic_similarity_predictions(
    embed_texts: Callable[[list[str]], list[list[float]]],
    issue_texts: list[str],
    *,
    positive_hypothesis: str,
    negative_hypothesis: str,
) -> list[int]:
    """Classify each issue text by nearer fixed hypothesis embedding.

    Ties favor positive so the rule is fully predeclared. Hypotheses are fixed
    inputs to this function, not learned from gold.
    """
    if not issue_texts:
        raise ValueError("issue texts must not be empty")
    vectors = _batched_vectors(
        embed_texts, [*issue_texts, positive_hypothesis, negative_hypothesis]
    )
    positive_vector = vectors[-2]
    negative_vector = vectors[-1]
    return [
        1
        if _cosine(vector, positive_vector) >= _cosine(vector, negative_vector)
        else 0
        for vector in vectors[:-2]
    ]
