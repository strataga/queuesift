"""Temporary local model provider for Slice 1 development (Ollama).

Approved target remains OpenAI for evaluated/shadow runs. Every result records
its actual provider and model so local outputs can never be reported as OpenAI
outputs. Switching embedding providers later requires re-embedding the corpus:
vector spaces and dimensions are not interchangeable.
"""

from __future__ import annotations

import json
import math
import os
import time

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.config import load_local_env

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_DRAFT_MODEL = "qwen2.5:7b"
DEFAULT_EMBED_MODEL = "nomic-embed-text"


class EvidenceChunk(BaseModel):
    chunk_id: str
    text: str


class DraftOutput(BaseModel):
    reply: str
    citations: list[str] = Field(default_factory=list)
    requested_info: list[str] = Field(default_factory=list)


class ProviderEvidence(BaseModel):
    provider: str
    draft_model: str
    embed_model: str
    embed_dimensions: int
    embed_latency_ms: int
    draft_latency_ms: int
    draft_prompt_tokens: int | None = None
    draft_output_tokens: int | None = None
    draft_reply_preview: str = ""
    citations: list[str] = Field(default_factory=list)


class DraftResult(BaseModel):
    provider: str
    model: str
    latency_ms: int
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    output: DraftOutput


class EmbeddingResult(BaseModel):
    provider: str
    model: str
    latency_ms: int
    dimensions: int
    normalized: bool = True
    vectors: list[list[float]]


class ProviderError(RuntimeError):
    pass


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        raise ProviderError("embedding model returned a zero vector")
    return [v / norm for v in vector]


class OllamaProvider:
    """Ollama drafting + embeddings over plain HTTP (no extra SDK)."""

    name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        draft_model: str | None = None,
        embed_model: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 180.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.draft_model = draft_model or os.environ.get("DRAFT_MODEL") or DEFAULT_DRAFT_MODEL
        self.embed_model = embed_model or os.environ.get("EMBED_MODEL") or DEFAULT_EMBED_MODEL
        self._transport = transport
        self._timeout = timeout

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=self._timeout, transport=self._transport)

    def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        if not texts or any(not t.strip() for t in texts):
            raise ProviderError("embed_texts requires at least one non-empty text")
        started = time.perf_counter()
        with self._client() as client:
            response = client.post("/api/embed", json={"model": self.embed_model, "input": texts})
            response.raise_for_status()
            payload = response.json()
        latency_ms = int((time.perf_counter() - started) * 1000)
        raw = payload.get("embeddings") or []
        if len(raw) != len(texts):
            raise ProviderError(f"expected {len(texts)} embeddings, got {len(raw)}")
        vectors = [_normalize([float(v) for v in vector]) for vector in raw]
        dimensions = len(vectors[0])
        if any(len(v) != dimensions for v in vectors):
            raise ProviderError("embedding dimensions are inconsistent within the batch")
        return EmbeddingResult(
            provider=self.name,
            model=self.embed_model,
            latency_ms=latency_ms,
            dimensions=dimensions,
            vectors=vectors,
        )

    def draft_reply(self, instruction: str, chunks: list[EvidenceChunk]) -> DraftResult:
        if not chunks:
            raise ProviderError("draft_reply requires at least one evidence chunk")
        evidence = "\n".join(f"[{c.chunk_id}] {c.text}" for c in chunks)
        allowed = {c.chunk_id for c in chunks}
        last_error: Exception | None = None
        for _attempt in range(2):
            started = time.perf_counter()
            with self._client() as client:
                response = client.post(
                    "/api/chat",
                    json={
                        "model": self.draft_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You draft GitHub triage replies only from supplied evidence. "
                                    "Reply with JSON only."
                                ),
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"{instruction}\n\nEvidence:\n{evidence}\n\n"
                                    'Return JSON {"reply": string, "citations": [chunk IDs], '
                                    '"requested_info": [string]}.'
                                ),
                            },
                        ],
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.2, "num_predict": 320},
                    },
                )
                response.raise_for_status()
                payload = response.json()
            latency_ms = int((time.perf_counter() - started) * 1000)
            content = ((payload.get("message") or {}).get("content")) or ""
            try:
                output = DraftOutput(**json.loads(content))
            except (json.JSONDecodeError, ValidationError) as error:
                last_error = error
                continue
            unknown = [c for c in output.citations if c not in allowed]
            if unknown:
                last_error = ProviderError(f"draft cited unknown chunks: {unknown}")
                continue
            return DraftResult(
                provider=self.name,
                model=self.draft_model,
                latency_ms=latency_ms,
                prompt_tokens=payload.get("prompt_eval_count"),
                output_tokens=payload.get("eval_count"),
                output=output,
            )
        raise ProviderError(f"draft failed schema/citation validation twice: {last_error}")


def get_provider() -> OllamaProvider:
    """Return the configured Slice 1 provider.

    Only Ollama is wired while OpenAI billing is inactive. Selecting another
    provider fails loudly instead of silently substituting models.
    """
    load_local_env()
    provider = (os.environ.get("LLM_PROVIDER") or "ollama").strip().lower()
    if provider != "ollama":
        raise ProviderError(
            f"provider {provider!r} is not wired in Slice 1; use LLM_PROVIDER=ollama locally. "
            "Local results must never be reported as OpenAI results."
        )
    return OllamaProvider()


def check_providers() -> ProviderEvidence:
    provider = get_provider()
    chunks = [
        EvidenceChunk(
            chunk_id="A",
            text="Known issue: responses omit search_results; workaround is to read the native SDK response.",
        ),
        EvidenceChunk(
            chunk_id="B",
            text="Bug reports require a minimal reproduction and package version.",
        ),
    ]
    embeddings = provider.embed_texts([c.text for c in chunks])
    draft = provider.draft_reply("Draft a known-issue reply citing the evidence.", chunks)
    return ProviderEvidence(
        provider=provider.name,
        draft_model=draft.model,
        embed_model=embeddings.model,
        embed_dimensions=embeddings.dimensions,
        embed_latency_ms=embeddings.latency_ms,
        draft_latency_ms=draft.latency_ms,
        draft_prompt_tokens=draft.prompt_tokens,
        draft_output_tokens=draft.output_tokens,
        draft_reply_preview=draft.output.reply[:200],
        citations=draft.output.citations,
    )
