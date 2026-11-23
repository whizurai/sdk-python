"""capabilities.run_events: the SSE follower for a capability run's live events."""
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from whizurai import ClientConfig, NotFoundError, WhizuraiClient
from whizurai.types import NetworkError


def chunk(seq, chunks):
    return f"id: {seq}\nevent: chunk\ndata: {json.dumps({'seq': seq, 'chunks': chunks})}\n\n"


def end(status):
    return f"event: end\ndata: {json.dumps({'status': status})}\n\n"


def make_client(responses):
    """responses: list of (status, body) served in order; records each request."""
    seen = []

    def handler(request):
        seen.append(request)
        status, body = responses[min(len(seen) - 1, len(responses) - 1)]
        return httpx.Response(status, content=body.encode(), headers={"content-type": "text/event-stream"})

    client = WhizuraiClient(ClientConfig(api_key="k", base_url="http://localhost:3000"))
    client.client = httpx.AsyncClient(base_url="http://localhost:3000", transport=httpx.MockTransport(handler))
    return client, seen


async def collect(it):
    return [e async for e in it]


async def test_streams_chunks_in_order_then_end():
    client, seen = make_client([(200, ": keep-alive\n\n" + chunk(0, [{"type": "coding_progress", "text": "hi"}]) + chunk(1, ["b"]) + end("succeeded"))])
    events = await collect(client.capabilities.run_events("cr1"))
    assert events == [
        {"type": "chunk", "seq": 0, "chunks": [{"type": "coding_progress", "text": "hi"}]},
        {"type": "chunk", "seq": 1, "chunks": ["b"]},
        {"type": "end", "status": "succeeded"},
    ]
    assert seen[0].url.path == "/v1/capabilities/capability-runs/cr1/events"
    assert "last-event-id" not in seen[0].headers


async def test_resumes_after_a_dropped_connection_without_duplicates():
    client, seen = make_client([(200, chunk(0, ["a"]) + chunk(1, ["b"])), (200, chunk(1, ["b"]) + chunk(2, ["c"]) + end("succeeded"))])
    with patch("whizurai.client.asyncio.sleep", new=AsyncMock()):
        events = await collect(client.capabilities.run_events("cr1"))
    assert [e.get("seq", e.get("status")) for e in events] == [0, 1, 2, "succeeded"]
    assert seen[1].headers["last-event-id"] == "1"
    assert seen[1].url.params["after"] == "1"


async def test_a_refusal_is_not_retried():
    client, seen = make_client([(404, "")])
    with pytest.raises(NotFoundError):
        await collect(client.capabilities.run_events("nope"))
    assert len(seen) == 1


async def test_gives_up_after_max_reconnects():
    client, seen = make_client([(502, "")])
    with patch("whizurai.client.asyncio.sleep", new=AsyncMock()):
        with pytest.raises(NetworkError):
            await collect(client.capabilities.run_events("cr1", max_reconnects=2))
    assert len(seen) == 3
