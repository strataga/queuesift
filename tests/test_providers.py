import json
import math

import httpx
import pytest

from app.providers import EvidenceChunk, OllamaProvider, ProviderError


def _provider(handler) -> OllamaProvider:  # type: ignore[no-untyped-def]
    return OllamaProvider(
        base_url="http://ollama.test",
        draft_model="qwen2.5:7b",
        embed_model="nomic-embed-text",
        transport=httpx.MockTransport(handler),
    )


def test_embed_texts_normalizes_and_labels_provider() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        payload = json.loads(request.content)
        assert payload["model"] == "nomic-embed-text"
        assert payload["input"] == ["one", "two"]
        return httpx.Response(200, json={"embeddings": [[3.0, 4.0], [0.0, 2.0]]})

    result = _provider(handler).embed_texts(["one", "two"])
    assert result.provider == "ollama"
    assert result.model == "nomic-embed-text"
    assert result.dimensions == 2
    assert result.normalized is True
    assert math.isclose(math.sqrt(sum(v * v for v in result.vectors[0])), 1.0)
    assert result.vectors[0] == pytest.approx([0.6, 0.8])


def test_embed_texts_rejects_empty_input() -> None:
    provider = _provider(lambda request: httpx.Response(200, json={}))
    with pytest.raises(ProviderError):
        provider.embed_texts(["  "])


def test_draft_reply_validates_citations_and_retries() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        calls["count"] += 1
        if calls["count"] == 1:
            content = json.dumps({"reply": "bad", "citations": ["ZZZ"], "requested_info": []})
        else:
            content = json.dumps(
                {"reply": "Known issue; see evidence.", "citations": ["A"], "requested_info": []}
            )
        return httpx.Response(
            200,
            json={"message": {"content": content}, "prompt_eval_count": 99, "eval_count": 21},
        )

    result = _provider(handler).draft_reply(
        "Draft a reply.", [EvidenceChunk(chunk_id="A", text="evidence text")]
    )
    assert calls["count"] == 2
    assert result.provider == "ollama"
    assert result.model == "qwen2.5:7b"
    assert result.output.citations == ["A"]
    assert result.prompt_tokens == 99 and result.output_tokens == 21


def test_draft_reply_requires_evidence() -> None:
    provider = _provider(lambda request: httpx.Response(200, json={}))
    with pytest.raises(ProviderError):
        provider.draft_reply("Draft.", [])
