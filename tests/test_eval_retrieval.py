import pytest

from app.eval_inputs import CreationTimeIssueInput
from app.eval_retrieval import (
    build_corpus,
    eligible_chunks,
    retrieve_top_k,
)


def _item(number: int, created_at: str | None) -> CreationTimeIssueInput:
    return CreationTimeIssueInput(
        repo="test/repo",
        number=number,
        github_id=number,
        title=f"Title {number}",
        body="Body.",
        author="reporter",
        author_association="NONE",
        created_at=created_at,
    )


def test_build_corpus_uses_creation_time_validity() -> None:
    corpus = build_corpus([_item(1, "2024-02-02T18:02:57Z")])
    assert corpus[0].issue_number == 1
    assert corpus[0].valid_from == "2024-02-02T18:02:57Z"
    assert corpus[0].title == "Title 1"


def test_eligible_chunks_excludes_future_and_unparseable() -> None:
    corpus = build_corpus(
        [
            _item(1, "2024-02-02T18:02:57Z"),
            _item(2, "2025-01-01T00:00:00Z"),
            _item(3, None),
            _item(4, "not-a-date"),
        ]
    )
    eligible = eligible_chunks("2024-06-01T00:00:00Z", corpus)
    assert [chunk.issue_number for chunk in eligible] == [1]
    assert eligible_chunks(None, corpus) == []
    assert eligible_chunks("not-a-date", corpus) == []


def test_retrieve_top_k_excludes_query_issue_and_ranks() -> None:
    corpus = build_corpus(
        [
            _item(1, "2024-01-01T00:00:00Z"),
            _item(2, "2024-02-01T00:00:00Z"),
            _item(3, "2024-03-01T00:00:00Z"),
        ]
    )
    vectors = [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]]
    ranked = retrieve_top_k(1, vectors[0], corpus, vectors, top_k=2)
    assert [entry["issue_number"] for entry in ranked] == [2, 3]
    assert ranked[0]["similarity"] > ranked[1]["similarity"]


def test_retrieve_top_k_validates_inputs() -> None:
    corpus = build_corpus([_item(1, "2024-01-01T00:00:00Z")])
    with pytest.raises(ValueError):
        retrieve_top_k(1, [1.0], corpus, [], top_k=2)
    with pytest.raises(ValueError):
        retrieve_top_k(1, [1.0, 0.0], corpus, [[1.0, 0.0]], top_k=0)
