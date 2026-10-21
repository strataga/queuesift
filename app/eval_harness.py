"""Qualified non-paid preliminary scoring for stale and secondary-MRE baselines.

Duplicate scoring is prohibited and is never executed by this module. Paid
provider calls are prohibited. Local Ollama results are labelled with their
actual provider and model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from app.eval_baselines import (
    MRE_NEGATIVE_HYPOTHESIS,
    MRE_POSITIVE_HYPOTHESIS,
    STALE_NEGATIVE_HYPOTHESIS,
    STALE_POSITIVE_HYPOTHESIS,
    issue_text_for_embedding,
    predict_mre_by_template,
    predict_stale_by_age,
    semantic_similarity_predictions,
)
from app.eval_inputs import CreationTimeIssueInput, load_creation_time_inputs
from app.eval_metrics import (
    confusion_matrix,
    paired_bootstrap_difference,
    precision_recall_f1,
    wilson_interval,
)
from app.providers import EmbeddingResult

BOOTSTRAP_SAMPLES = 2000
BOOTSTRAP_SEED = 20261020


class Embedder(Protocol):
    def embed_texts(self, texts: list[str]) -> EmbeddingResult: ...


def _read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def _wilson_or_none(successes: int, trials: int) -> dict[str, float] | None:
    return wilson_interval(successes, trials) if trials else None


def _score_binary(
    name: str,
    y_true: list[int],
    y_pred: list[int],
    *,
    bootstrap_samples: int,
    bootstrap_seed: int,
    baseline_pred: list[int] | None = None,
) -> dict:
    matrix = confusion_matrix(y_true, y_pred)
    scores = precision_recall_f1(matrix)
    result: dict = {
        "name": name,
        "n": matrix.total,
        "positives": sum(y_true),
        "negatives": matrix.total - sum(y_true),
        "confusion": {
            "true_positives": matrix.true_positives,
            "true_negatives": matrix.true_negatives,
            "false_positives": matrix.false_positives,
            "false_negatives": matrix.false_negatives,
        },
        "accuracy": scores["accuracy"],
        "accuracy_ci95": _wilson_or_none(
            matrix.true_positives + matrix.true_negatives, matrix.total
        ),
        "precision": scores["precision"],
        "precision_ci95": _wilson_or_none(
            matrix.true_positives,
            matrix.true_positives + matrix.false_positives,
        ),
        "recall": scores["recall"],
        "recall_ci95": _wilson_or_none(
            matrix.true_positives,
            matrix.true_positives + matrix.false_negatives,
        ),
        "f1": scores["f1"],
    }
    if baseline_pred is not None:
        result["paired_difference_vs_baseline"] = {
            "f1": paired_bootstrap_difference(
                y_true,
                y_pred,
                baseline_pred,
                metric="f1",
                samples=bootstrap_samples,
                seed=bootstrap_seed,
            ),
            "accuracy": paired_bootstrap_difference(
                y_true,
                y_pred,
                baseline_pred,
                metric="accuracy",
                samples=bootstrap_samples,
                seed=bootstrap_seed,
            ),
        }
    return result


def _embed_issue_texts(
    embedder: Embedder, texts: list[str]
) -> tuple[list[list[float]], dict]:
    started_vectors = 0
    total_latency_ms = 0
    provider = model = None
    dimensions = 0
    vectors: list[list[float]] = []
    for start in range(0, len(texts), 50):
        batch = texts[start : start + 50]
        result = embedder.embed_texts(batch)
        if provider is None:
            provider = result.provider
            model = result.model
            dimensions = result.dimensions
        if (
            result.provider != provider
            or result.model != model
            or result.dimensions != dimensions
        ):
            raise ValueError("embedding batches must use one provider/model/shape")
        if len(result.vectors) != len(batch):
            raise ValueError("embedding batch returned the wrong number of vectors")
        vectors.extend([[float(value) for value in vector] for vector in result.vectors])
        total_latency_ms += result.latency_ms
        started_vectors += len(batch)
    metadata = {
        "provider": provider,
        "model": model,
        "dimensions": dimensions,
        "vectors": started_vectors,
        "latency_ms": total_latency_ms,
        "paid_spend_usd": 0.0,
    }
    return vectors, metadata


def _semantic_predictions(
    embedder: Embedder,
    items: list[CreationTimeIssueInput],
    *,
    positive_hypothesis: str,
    negative_hypothesis: str,
) -> tuple[list[int], dict]:
    texts = [issue_text_for_embedding(item) for item in items]
    vectors, metadata = _embed_issue_texts(
        embedder, [*texts, positive_hypothesis, negative_hypothesis]
    )
    issue_vectors = vectors[:-2]
    positive_vector = vectors[-2]
    negative_vector = vectors[-1]
    predictions = semantic_similarity_predictions(
        lambda batch: _vectors_for_batch(issue_vectors, positive_vector, negative_vector, batch, texts, positive_hypothesis, negative_hypothesis),
        texts,
        positive_hypothesis=positive_hypothesis,
        negative_hypothesis=negative_hypothesis,
    )
    return predictions, metadata


def _vectors_for_batch(
    issue_vectors: list[list[float]],
    positive_vector: list[float],
    negative_vector: list[float],
    batch: list[str],
    texts: list[str],
    positive_hypothesis: str,
    negative_hypothesis: str,
) -> list[list[float]]:
    """Map the already-embedded batch back to vectors without another model call."""
    ordered = [*texts, positive_hypothesis, negative_hypothesis]
    lookup = {
        text: vector
        for text, vector in zip(
            ordered, [*issue_vectors, positive_vector, negative_vector]
        )
    }
    return [lookup[text] for text in batch]


def run_qualified_baselines(
    engine,
    *,
    repo: str,
    manifest_path: Path | str,
    gold_path: Path | str,
    titles_path: Path | str,
    report_path: Path | str,
    embedder: Embedder,
    bootstrap_samples: int = BOOTSTRAP_SAMPLES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> dict:
    """Score deterministic and local-embedding baselines on qualified gold only."""
    manifest = _read_json(Path(manifest_path))
    gold = _read_json(Path(gold_path))
    titles = _read_json(Path(titles_path))
    if manifest["repo"] != repo or gold["repo"] != repo or titles["repo"] != repo:
        raise ValueError("manifest, gold, and title provenance must match the repo")

    manifest_numbers = [item["number"] for item in manifest["members"]]
    original_titles = {
        item["number"]: item["original_title"] for item in titles["issues"]
    }
    inputs = load_creation_time_inputs(
        engine, repo=repo, numbers=manifest_numbers, original_titles=original_titles
    )
    by_number = {item.number: item for item in inputs}

    stale_gold = gold["stale"]
    stale_numbers = sorted(
        set(stale_gold["positive_members"]) | set(stale_gold["non_positive_members"])
    )
    if set(stale_numbers) != set(manifest_numbers):
        raise ValueError("stale gold must cover exactly the frozen manifest")
    stale_items = [by_number[number] for number in manifest_numbers]
    stale_truth = [1 if number in set(stale_gold["positive_members"]) else 0 for number in manifest_numbers]
    stale_deterministic = [predict_stale_by_age(item) for item in stale_items]
    stale_local, stale_embed_metadata = _semantic_predictions(
        embedder,
        stale_items,
        positive_hypothesis=STALE_POSITIVE_HYPOTHESIS,
        negative_hypothesis=STALE_NEGATIVE_HYPOTHESIS,
    )

    mre_gold = gold["missing_reproduction"]
    mre_positives = {item["number"] for item in mre_gold["positives"]}
    mre_negatives = {item["number"] for item in mre_gold["negatives"]}
    if not mre_positives.isdisjoint(mre_negatives):
        raise ValueError("MRE positives and negatives must be disjoint")
    if len(mre_positives) < 30 or len(mre_negatives) < 30:
        raise ValueError("MRE evaluation requires at least 30 positives and 30 negatives")
    mre_numbers = [number for number in manifest_numbers if number in mre_positives | mre_negatives]
    mre_items = [by_number[number] for number in mre_numbers]
    mre_truth = [1 if number in mre_positives else 0 for number in mre_numbers]
    mre_deterministic = [predict_mre_by_template(item) for item in mre_items]
    mre_local, mre_embed_metadata = _semantic_predictions(
        embedder,
        mre_items,
        positive_hypothesis=MRE_POSITIVE_HYPOTHESIS,
        negative_hypothesis=MRE_NEGATIVE_HYPOTHESIS,
    )

    report = {
        "repo": repo,
        "as_of": gold["as_of"],
        "cohort_manifest": str(manifest_path),
        "gold_file": str(gold_path),
        "title_provenance": str(titles_path),
        "inputs": {
            "members": len(manifest_numbers),
            "renamed_title_overrides": len(original_titles),
            "unknown_mre_members_excluded": len(mre_gold.get("unknown_members", [])),
        },
        "provider_gates": {
            "openai_used": False,
            "paid_provider_calls": 0,
            "paid_provider_spend_usd": 0.0,
            "duplicate_scoring": "prohibited; duplicate census only",
        },
        "local_embeddings": {
            "stale": stale_embed_metadata,
            "missing_reproduction": mre_embed_metadata,
        },
        "stale": {
            "deterministic_age": _score_binary(
                "deterministic_age",
                stale_truth,
                stale_deterministic,
                bootstrap_samples=bootstrap_samples,
                bootstrap_seed=bootstrap_seed,
            ),
            "local_semantic": _score_binary(
                "local_semantic",
                stale_truth,
                stale_local,
                bootstrap_samples=bootstrap_samples,
                bootstrap_seed=bootstrap_seed,
                baseline_pred=stale_deterministic,
            ),
        },
        "missing_reproduction": {
            "note": "Secondary operator judgment only; not headline maintainer accuracy.",
            "deterministic_template": _score_binary(
                "deterministic_template",
                mre_truth,
                mre_deterministic,
                bootstrap_samples=bootstrap_samples,
                bootstrap_seed=bootstrap_seed,
            ),
            "local_semantic": _score_binary(
                "local_semantic",
                mre_truth,
                mre_local,
                bootstrap_samples=bootstrap_samples,
                bootstrap_seed=bootstrap_seed,
                baseline_pred=mre_deterministic,
            ),
        },
        "bootstrap": {"samples": bootstrap_samples, "seed": bootstrap_seed},
    }

    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report
