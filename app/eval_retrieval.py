"""Staged retrieval inputs over frozen creation-time issue texts.

The corpus is built only from creation-time titles and bodies. A query may
retrieve only chunks whose validity timestamp is at or before the query
issue's creation time, and never the query issue itself. Gold outcomes,
labels, and timeline signals are never stored in the corpus.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.eval_baselines import cosine_similarity
from app.eval_inputs import CreationTimeIssueInput


@dataclass(frozen=True)
class CorpusChunk:
    issue_number: int
    title: str
    body: str
    valid_from: str


def build_corpus(items: list[CreationTimeIssueInput]) -> list[CorpusChunk]:
    """Build retrieval chunks with validity starting at each issue's creation."""
    return [
        CorpusChunk(
            issue_number=item.number,
            title=item.title,
            body=item.body,
            valid_from=item.created_at or "",
        )
        for item in items
    ]


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def eligible_chunks(
    query_created_at: str | None, chunks: list[CorpusChunk]
) -> list[CorpusChunk]:
    """Return chunks valid at or before the query's creation time.

    Chunks with missing or unparseable timestamps are excluded rather than
    guessed at.
    """
    query_time = _parse_timestamp(query_created_at)
    if query_time is None:
        return []
    eligible = []
    for chunk in chunks:
        chunk_time = _parse_timestamp(chunk.valid_from)
        if chunk_time is not None and chunk_time <= query_time:
            eligible.append(chunk)
    return eligible


def retrieve_top_k(
    query_number: int,
    query_vector: list[float],
    chunks: list[CorpusChunk],
    vectors: list[list[float]],
    top_k: int = 3,
) -> list[dict]:
    """Rank eligible chunks by cosine similarity, excluding the query issue."""
    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors must have the same length")
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    scored = [
        (chunk.issue_number, cosine_similarity(query_vector, vector))
        for chunk, vector in zip(chunks, vectors)
        if chunk.issue_number != query_number
    ]
    scored.sort(key=lambda entry: entry[1], reverse=True)
    return [
        {"issue_number": number, "similarity": similarity}
        for number, similarity in scored[:top_k]
    ]
