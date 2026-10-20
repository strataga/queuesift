# Spike: temporary local Ollama provider

Date: 2026-10-20. Hardware: Apple M4 Pro, about 24 GB RAM.

## Why

OpenAI billing is inactive (`429 billing_not_active`; see the OpenAI key
spike). To keep Slice 1 development moving without weakening the design,
QueueSift temporarily wires local models behind the provider configuration.
The approved evaluation/shadow target remains OpenAI. Local outputs are
always labelled `provider=ollama` with their actual model names and must
never be reported as OpenAI results.

## Configuration

- `LLM_PROVIDER=ollama` (any other value fails loudly in Slice 1 code)
- `DRAFT_MODEL=qwen2.5:7b` (4.7 GB, previously installed)
- `EMBED_MODEL=nomic-embed-text` (274 MB, pulled for this spike)
- `OLLAMA_BASE_URL=http://localhost:11434` on the host;
  `http://host.docker.internal:11434` inside Docker Compose
- Secrets stay in gitignored `.env.local`; no key values are logged.

## Through-QueueSift verification

Command: `uv run queuesift --check-providers`

Recorded evidence from the run on 2026-10-20:

- Embeddings: `nomic-embed-text`, 768 dimensions, unit-normalized in code for
  cosine search, 71 ms for two short evidence chunks.
- Draft: `qwen2.5:7b` returned schema-valid JSON with citations `A` and `B`
  validated against the supplied chunk IDs; 94 prompt tokens, 73 output
  tokens, 1,614 ms warm. An earlier cold/manual probe of the same task took
  about 6.5 seconds, so warm latency must not be quoted as cold latency.
- A separate manual batch probe embedded 20 short issue-like texts in about
  0.3 seconds. Full-corpus throughput remains a Slice 1 dry-run measurement,
  not a conclusion from this sample.

Unit tests use HTTP fakes at the Ollama boundary only; they cover batch
embedding normalization and dimension checks, empty-input rejection, draft
schema and unknown-citation retry, and evidence-required behaviour. Live model
calls are never part of CI.

## Embedding strategy notes

- One embedding model per index. Metadata must record provider, model,
  dimensions, normalization, source, and time-validity on every chunk.
- `nomic-embed-text` (768 dimensions) fits local English/code-adjacent
  retrieval development and is fast on this machine. It is not assumed equal
  to OpenAI `text-embedding-3-small` (1,536 dimensions) in quality.
- Switching to OpenAI later requires re-embedding the entire corpus into a
  new index/version; vectors from different models must never be mixed.
- Chunking remains semantic (headings/symbols), batched, and cached by content
  hash when Slice 2 builds the index; this spike does not choose final chunk
  sizes.

## Limits

Local drafting is a development substitute, not the evaluated baseline from
the approved design. Slice 2 go/no-go comparisons must either run after OpenAI
billing is active or be explicitly re-scoped and reported as local-model
results. Provider training/retention for any hosted model still requires the
design ADR before real issue text is sent at scale; local draft/embedding
calls keep that text on this machine, while Jev calls remain remote.
