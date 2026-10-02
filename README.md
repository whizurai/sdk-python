# whizurai-sdk

Official Python SDK for the Whizurai Platform.

## Installation

```bash
pip install whizurai-sdk
```

## Quick Start

The SDK is **capability-first**: you execute published capabilities, track their
runs, and read the resulting artifacts.

```python
import asyncio
from whizurai import WhizuraiClient, ClientConfig

async def main():
    config = ClientConfig(
        api_key='your-api-key',
        base_url='https://api.whizurai.com',  # Optional
    )

    async with WhizuraiClient(config) as client:
        # 1. List published capabilities
        caps = await client.capabilities.list(status='published')

        # 2. Execute a capability
        run = await client.capabilities.run(
            'image.generate',
            {'prompt': 'a red bicycle'},
            idempotency_key='req-123',
        )

        # 3. Poll the run to completion
        done = await client.runs.poll_until_done(run.id)

        # 4. Read the produced artifacts
        artifacts = await client.runs.artifacts(done.id)
        for art in artifacts:
            print(art.url)

asyncio.run(main())
```

## Resources

| Resource | Methods |
|---|---|
| `client.capabilities` | `list`, `get`, `run`, `dry_run` |
| `client.runs` | `get`, `list`, `logs`, `artifacts`, `poll_until_done` |
| `client.artifacts` | `list`, `get` |
| `client.triggers` | `list`, `get`, `create`, `update`, `delete`, `test` |

Plus `client.health_check()`, `client.get_status()`, `client.ping()`, and the
direct-inference methods `client.embed()` / `client.rerank()` below.

## Embeddings and Rerank

Direct inference against `POST /v1/embeddings` and `POST /v1/rerank`. Field
names match the wire (snake_case), including the optional `whizai` provenance.

These endpoints are served by **model-router**, not the api-gateway at
`base_url`, so set `inference_base_url` (or env `WHIZAI_INFERENCE_URL` with
`create_client_from_env()`). The same API key authenticates there (sent as
`X-API-Key` and `Authorization: Bearer`; model-router verifies it with the
gateway). Without it, `embed()`/`rerank()` raise `WhizuraiError`.

```python
client = WhizuraiClient(ClientConfig(
    api_key=os.environ["WHIZURAI_API_KEY"],
    inference_base_url="https://model-router.staging.whizur.ai",
))
```

### Embed

`model` is **required** — there is no default, because the model fixes the
vector space. Use a pinned alias such as `embedding-qwen3-0.6b-v1`.

**Set `input_type` correctly.** Retrieval queries must pass `input_type="query"`;
passages being indexed use `"document"` (the default). Qwen3-Embedding applies
its retrieval instruction only to query inputs — a query embedded as a document
gets no instruction and retrieves worse, with no error.

```python
res = await client.embed(
    "embedding-qwen3-0.6b-v1",
    ["first passage", "second passage"],  # str or up to 128 strings
    input_type="document",                # or "query" (server default "document")
    instruction=None,                     # optional task instruction
)
res.data[0].embedding            # List[float]
res.embedding_space              # shortcut for res.whizai.embedding_space (None if absent)
res.whizai.model_revision        # str | None
res.whizai.worker                # InferenceWorker(id, name) when attributable
```

**Never compare vectors across `embedding_space` values.** Store the space next
to every vector and check it before computing similarity:

```python
from whizurai import assert_same_embedding_space

# Raises EmbeddingSpaceError if the spaces differ, or if either is missing or
# contains "unknown". Accepts strings, EmbeddingsResponse, provenance or dicts.
assert_same_embedding_space(stored_space, res)
```

Older non-fleet models (e.g. `nomic-embed-text`) return no `embedding_space`;
the guard treats that as non-comparable, not as a wildcard.

### Rerank

```python
ranked = await client.rerank(
    "rerank-qwen3-0.6b-v1",
    "live music tonight",
    ["doc a", "doc b", "doc c"],   # 1..64
    top_n=2,
)
ranked.results  # [RerankResult(index, relevance_score)] sorted by score, descending
```

Without `fallback`, `rerank()` raises on any failure (the platform fails fast
with 503/504 when no worker is available or the call times out).

### Rerank fallback mode

A reranker should never be a correctness dependency. With
`fallback="original-order"`, a timeout, network error, 408, 429 or 5xx returns
instead of raising. Fallback mode makes a single attempt (no retries), so
`timeout` (seconds) bounds the call:

```python
out = await client.rerank(model, query, documents, fallback="original-order", timeout=1.5)
if out.degraded:
    # out.results: index 0..n-1 in original order (truncated to top_n), relevance_score=None
    log.warning("rerank degraded: %s (%r)", out.reason, out.error)  # "timeout" | "network_error" | "http_503" | ...
```

Validation and auth errors (400, 401, 403, 404, 422) **always raise**, even in
fallback mode — they are caller bugs, not outages. A 401/403/404 message ends
with `(check inference_base_url: …)`, since pointing at the wrong host (e.g.
the gateway) produces exactly those. A missing `inference_base_url` also raises
in fallback mode.

Error messages are read from any body shape the platform returns:
`{"error": {"code", "message"}}`, `{"error", "message"}`, or FastAPI's
`{"detail": ...}` (string, `{"error", "message"}` object, or validation list).

## Error Handling

All errors extend `WhizuraiError`:

```python
from whizurai import NotFoundError, AuthenticationError, WhizuraiError

try:
    await client.capabilities.run('invalid-id', {})
except NotFoundError:
    print('Capability not found')
except AuthenticationError:
    print('Check your API key')
except WhizuraiError as e:
    print('Platform error:', e)
```

## Documentation

- [Full Documentation](https://github.com/whizurai/docs)
- [API Reference](https://github.com/whizurai/docs/blob/main/api/README.md)
- [Examples](https://github.com/whizurai/examples)

## License

MIT
