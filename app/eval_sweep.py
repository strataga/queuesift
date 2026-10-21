"""Threshold-sweep F1 scoring for qualified stale and secondary-MRE baselines.

The sweep is descriptive: it reports how the fixed local-semantic margin rule
behaves across a predeclared threshold grid. No threshold is adopted from this
sweep and no system is changed by it. Duplicate scoring is prohibited and is
never executed by this module. All embeddings are local and non-paid.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.eval_baselines import (
    MRE_NEGATIVE_HYPOTHESIS,
    MRE_POSITIVE_HYPOTHESIS,
    STALE_NEGATIVE_HYPOTHESIS,
    STALE_POSITIVE_HYPOTHESIS,
    cosine_similarity,
    issue_text_for_embedding,
    predict_mre_by_template,
    predict_stale_by_age,
)
from app.eval_harness import Embedder, embed_in_batches
from app.eval_inputs import CreationTimeIssueInput, load_creation_time_inputs
from app.eval_metrics import (
    confusion_matrix,
    paired_bootstrap_difference,
    precision_recall_f1,
    wilson_interval,
)
from app.eval_retrieval import build_corpus, eligible_chunks, retrieve_top_k

THRESHOLD_GRID = [-0.10, -0.05, -0.02, 0.0, 0.02, 0.05, 0.10]
BOOTSTRAP_SAMPLES = 2000
BOOTSTRAP_SEED = 20261020
RETRIEVAL_TOP_K = 3


def _wilson_or_none(successes: int, trials: int) -> dict[str, float] | None:
    return wilson_interval(successes, trials) if trials else None


def _margins(
    vectors: list[list[float]],
    positive_vector: list[float],
    negative_vector: list[float],
) -> list[float]:
    return [
        cosine_similarity(vector, positive_vector)
        - cosine_similarity(vector, negative_vector)
        for vector in vectors
    ]


def _sweep_task(
    name: str,
    y_true: list[int],
    margins: list[float],
    deterministic_pred: list[int],
    note: str | None = None,
) -> dict:
    results = []
    for threshold in THRESHOLD_GRID:
        y_pred = [1 if margin >= threshold else 0 for margin in margins]
        matrix = confusion_matrix(y_true, y_pred)
        scores = precision_recall_f1(matrix)
        results.append(
            {
                "threshold": threshold,
                "n": matrix.total,
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
                "paired_difference_vs_deterministic": {
                    "f1": paired_bootstrap_difference(
                        y_true,
                        y_pred,
                        deterministic_pred,
                        metric="f1",
                        samples=BOOTSTRAP_SAMPLES,
                        seed=BOOTSTRAP_SEED,
                    ),
                    "accuracy": paired_bootstrap_difference(
                        y_true,
                        y_pred,
                        deterministic_pred,
                        metric="accuracy",
                        samples=BOOTSTRAP_SAMPLES,
                        seed=BOOTSTRAP_SEED,
                    ),
                },
            }
        )
    task: dict[str, object] = {"name": name, "thresholds": results}
    if note is not None:
        task["note"] = note
    return task


def _validate_retrieval(
    numbers: list[int],
    created: dict[int, str | None],
    issue_vectors: list[list[float]],
) -> dict:
    """Check timestamp filtering across the frozen cohort without scoring."""
    chunks = build_corpus(
        [
            CreationTimeIssueInput(
                repo="",
                number=number,
                github_id=0,
                title="",
                body="",
                created_at=created[number],
            )
            for number in numbers
        ]
    )
    per_query = []
    violations = 0
    for index, number in enumerate(numbers):
        eligible = eligible_chunks(created[number], chunks)
        eligible_numbers = {chunk.issue_number for chunk in eligible}
        ranked = retrieve_top_k(
            number,
            issue_vectors[index],
            eligible,
            [
                issue_vectors[numbers.index(chunk.issue_number)]
                for chunk in eligible
            ],
            top_k=RETRIEVAL_TOP_K,
        )
        bad = [
            entry
            for entry in ranked
            if entry["issue_number"] == number
            or entry["issue_number"] not in eligible_numbers
        ]
        violations += len(bad)
        per_query.append(
            {
                "number": number,
                "eligible_others": len(eligible_numbers - {number}),
                "retrieved": len(ranked),
            }
        )
    covered = sum(1 for entry in per_query if entry["eligible_others"] > 0)
    return {
        "queries": len(numbers),
        "top_k": RETRIEVAL_TOP_K,
        "queries_with_older_corpus": covered,
        "timestamp_violations": violations,
        "per_query": per_query,
    }


def run_threshold_sweep(
    engine,
    *,
    repo: str,
    manifest_path: Path | str,
    gold_path: Path | str,
    titles_path: Path | str,
    report_path: Path | str,
    embedder: Embedder,
) -> dict:
    """Score the semantic-margin sweep and validate staged retrieval inputs."""
    manifest = json.loads(Path(manifest_path).read_text())
    gold = json.loads(Path(gold_path).read_text())
    titles = json.loads(Path(titles_path).read_text())
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
    stale_positives = set(stale_gold["positive_members"])
    stale_truth = [1 if number in stale_positives else 0 for number in manifest_numbers]
    stale_det = [predict_stale_by_age(by_number[number]) for number in manifest_numbers]

    mre_gold = gold["missing_reproduction"]
    mre_positives = {item["number"] for item in mre_gold["positives"]}
    mre_negatives = {item["number"] for item in mre_gold["negatives"]}
    if not mre_positives.isdisjoint(mre_negatives):
        raise ValueError("MRE positives and negatives must be disjoint")
    mre_numbers = [
        number
        for number in manifest_numbers
        if number in mre_positives | mre_negatives
    ]
    mre_truth = [1 if number in mre_positives else 0 for number in mre_numbers]
    mre_det = [predict_mre_by_template(by_number[number]) for number in mre_numbers]

    stale_texts = [issue_text_for_embedding(by_number[n]) for n in manifest_numbers]
    stale_vectors, stale_meta = embed_in_batches(
        embedder,
        [*stale_texts, STALE_POSITIVE_HYPOTHESIS, STALE_NEGATIVE_HYPOTHESIS],
    )
    stale_margins = _margins(stale_vectors[:-2], stale_vectors[-2], stale_vectors[-1])

    mre_texts = [issue_text_for_embedding(by_number[n]) for n in mre_numbers]
    mre_vectors, mre_meta = embed_in_batches(
        embedder,
        [*mre_texts, MRE_POSITIVE_HYPOTHESIS, MRE_NEGATIVE_HYPOTHESIS],
    )
    mre_margins = _margins(mre_vectors[:-2], mre_vectors[-2], mre_vectors[-1])

    created = {number: by_number[number].created_at for number in manifest_numbers}
    retrieval = _validate_retrieval(manifest_numbers, created, stale_vectors[:-2])

    report = {
        "repo": repo,
        "as_of": gold["as_of"],
        "cohort_manifest": str(manifest_path),
        "gold_file": str(gold_path),
        "title_provenance": str(titles_path),
        "method": (
            "Descriptive threshold sweep over the fixed local-semantic margin "
            "(positive-hypothesis similarity minus negative-hypothesis "
            "similarity). No threshold is adopted and no system is changed."
        ),
        "threshold_grid": THRESHOLD_GRID,
        "inputs": {
            "members": len(manifest_numbers),
            "renamed_title_overrides": len(original_titles),
        },
        "provider_gates": {
            "openai_used": False,
            "paid_provider_calls": 0,
            "paid_provider_spend_usd": 0.0,
            "duplicate_scoring": "prohibited; duplicate census only",
        },
        "local_embeddings": {"stale": stale_meta, "missing_reproduction": mre_meta},
        "stale": _sweep_task("stale", stale_truth, stale_margins, stale_det),
        "missing_reproduction": _sweep_task(
            "missing_reproduction",
            mre_truth,
            mre_margins,
            mre_det,
            note="Secondary operator judgment only; not headline maintainer accuracy.",
        ),
        "staged_retrieval_validation": retrieval,
        "bootstrap": {"samples": BOOTSTRAP_SAMPLES, "seed": BOOTSTRAP_SEED},
    }
    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report
