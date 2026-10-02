"""Tests for client.embed() / client.rerank() and the embedding-space guard (mocked HTTP)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ConnectError, TimeoutException

from whizurai import (
    AuthenticationError,
    ClientConfig,
    NotFoundError,
    WhizuraiError,
    create_client_from_env,
    EmbeddingSpaceError,
    RECOMMENDED_EMBEDDING_MODEL,
    ValidationError,
    WhizuraiClient,
    assert_same_embedding_space,
)

SPACE = (
    "qwen3-embedding-0.6b:97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3:1024:"
    "normalized:qwen3-embed-instruct-v1"
)
DOCS = ["alpha", "beta", "gamma"]


def fake_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.content = b'{"x":1}' if json_data is not None else b""
    resp.headers = {}
    resp.reason_phrase = "ERR"
    return resp


@pytest.fixture
def client():
    return WhizuraiClient(
        ClientConfig(
            api_key="k",
            base_url="http://localhost:3000",
            inference_base_url="http://model-router.test/",
            timeout=5.0,
            max_retries=2,
            retry_delay=0.0,
        )
    )


class TestEmbed:
    async def test_posts_wire_body_and_parses_provenance(self, client):
        client.client.request = AsyncMock(
            return_value=fake_response(
                200,
                {
                    "object": "list",
                    "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}],
                    "model": RECOMMENDED_EMBEDDING_MODEL,
                    "whizai": {
                        "provider": "spark",
                        "runtime": "vllm",
                        "execution": "local",
                        "worker": {"id": "w1", "name": "spark02"},
                        "model": "qwen3-embedding-0.6b",
                        "model_revision": "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3",
                        "dimensions": 1024,
                        "normalized": True,
                        "prompt_contract": "qwen3-embed-instruct-v1",
                        "embedding_space": SPACE,
                        "attributable": True,
                    },
                },
            )
        )
        res = await client.embed(
            RECOMMENDED_EMBEDDING_MODEL, ["hello"], input_type="query", instruction="find"
        )
        kwargs = client.client.request.call_args.kwargs
        assert kwargs["url"] == "http://model-router.test/v1/embeddings"
        assert kwargs["json"] == {
            "model": "embedding-qwen3-0.6b-v1",
            "input": ["hello"],
            "input_type": "query",
            "instruction": "find",
        }
        assert res.embedding_space == SPACE
        assert res.whizai.model_revision == "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
        assert res.whizai.worker.name == "spark02"
        assert res.whizai.dimensions == 1024 and res.whizai.normalized is True
        assert res.data[0].embedding == [0.1, 0.2]

    async def test_no_provenance(self, client):
        client.client.request = AsyncMock(
            return_value=fake_response(
                200,
                {"object": "list", "data": [{"object": "embedding", "index": 0, "embedding": [1.0]}], "model": "nomic-embed-text"},
            )
        )
        res = await client.embed("nomic-embed-text", "x")
        assert res.whizai is None and res.embedding_space is None

    async def test_model_required(self, client):
        client.client.request = AsyncMock()
        with pytest.raises(ValidationError):
            await client.embed("", "x")
        client.client.request.assert_not_called()


class TestRerank:
    async def test_happy_path(self, client):
        client.client.request = AsyncMock(
            return_value=fake_response(
                200,
                {
                    "id": "rr_1",
                    "model": "rerank-qwen3-0.6b-v1",
                    "results": [{"index": 2, "relevance_score": 0.9}, {"index": 0, "relevance_score": 0.4}],
                    "whizai": {"provider": "spark", "runtime": "vllm", "model_revision": None, "prompt_contract": "qwen3-rerank-v1"},
                },
            )
        )
        res = await client.rerank("rerank-qwen3-0.6b-v1", "q", DOCS, top_n=2)
        assert client.client.request.call_args.kwargs["url"] == "http://model-router.test/v1/rerank"
        assert client.client.request.call_args.kwargs["json"] == {
            "model": "rerank-qwen3-0.6b-v1",
            "query": "q",
            "documents": DOCS,
            "top_n": 2,
        }
        assert res.degraded is False
        assert [r.index for r in res.results] == [2, 0]
        assert res.results[0].relevance_score == 0.9
        assert res.whizai.prompt_contract == "qwen3-rerank-v1"

    async def test_503_raises_without_fallback(self, client):
        client.client.request = AsyncMock(return_value=fake_response(503, {"error": "no worker"}))
        with pytest.raises(Exception) as exc:
            await client.rerank("m", "q", DOCS)
        assert getattr(exc.value, "status_code", None) == 503

    @pytest.mark.parametrize(
        "side_effect,reason",
        [
            ({"return_value": fake_response(503, {"error": "no worker"})}, "http_503"),
            ({"return_value": fake_response(504)}, "http_504"),
            ({"side_effect": TimeoutException("read timeout")}, "timeout"),
            ({"side_effect": ConnectError("refused")}, "network_error"),
        ],
    )
    async def test_fallback_degrades(self, client, side_effect, reason):
        client.client.request = AsyncMock(**side_effect)
        res = await client.rerank("m", "q", DOCS, fallback="original-order", timeout=0.5)
        # Fallback mode makes exactly one attempt and passes the per-call timeout.
        assert client.client.request.call_count == 1
        assert client.client.request.call_args.kwargs["timeout"] == 0.5
        assert res.degraded is True
        assert res.reason == reason
        assert isinstance(res.error, Exception)
        assert [(r.index, r.relevance_score) for r in res.results] == [(0, None), (1, None), (2, None)]

    async def test_fallback_honours_top_n(self, client):
        client.client.request = AsyncMock(return_value=fake_response(503))
        res = await client.rerank("m", "q", DOCS, top_n=2, fallback="original-order")
        assert [r.index for r in res.results] == [0, 1]

    async def test_400_raises_even_with_fallback(self, client):
        client.client.request = AsyncMock(
            return_value=fake_response(400, {"error": {"message": "documents must be 1..64"}})
        )
        with pytest.raises(ValidationError):
            await client.rerank("m", "q", [], fallback="original-order")

    async def test_401_raises_even_with_fallback(self, client):
        client.client.request = AsyncMock(return_value=fake_response(401))
        with pytest.raises(AuthenticationError):
            await client.rerank("m", "q", DOCS, fallback="original-order")

    async def test_invalid_fallback_value(self, client):
        with pytest.raises(ValueError):
            await client.rerank("m", "q", DOCS, fallback="drop")


class TestEmbeddingSpaceGuard:
    def test_same(self):
        assert assert_same_embedding_space(SPACE, SPACE) == SPACE

    def test_accepts_dicts(self):
        assert assert_same_embedding_space({"whizai": {"embedding_space": SPACE}}, {"embedding_space": SPACE}) == SPACE

    def test_mismatch(self):
        with pytest.raises(EmbeddingSpaceError) as exc:
            assert_same_embedding_space(SPACE, SPACE.replace(":1024:", ":768:"))
        assert exc.value.code == "EMBEDDING_SPACE_MISMATCH"

    @pytest.mark.parametrize(
        "bad",
        [None, "", {"whizai": None}, "qwen3-embedding-0.6b:unknown:1024:normalized:qwen3-embed-instruct-v1"],
    )
    def test_missing_or_unknown(self, bad):
        with pytest.raises(EmbeddingSpaceError) as exc:
            assert_same_embedding_space(SPACE, bad)
        assert exc.value.code == "EMBEDDING_SPACE_UNKNOWN"
        with pytest.raises(EmbeddingSpaceError):
            assert_same_embedding_space(bad, SPACE)


class TestInferenceHost:
    async def test_missing_inference_base_url_raises_even_with_fallback(self):
        c = WhizuraiClient(ClientConfig(api_key="k", base_url="http://localhost:3000"))
        c.client.request = AsyncMock()
        with pytest.raises(WhizuraiError, match="inference_base_url"):
            await c.embed("m", "x")
        with pytest.raises(WhizuraiError, match="inference_base_url"):
            await c.rerank("m", "q", DOCS, fallback="original-order")
        c.client.request.assert_not_called()

    async def test_sends_api_key_headers(self, client):
        assert client.client.headers["X-API-Key"] == "k"
        assert client.client.headers["Authorization"] == "Bearer k"

    @pytest.mark.parametrize("status,exc", [(401, AuthenticationError), (404, NotFoundError)])
    async def test_wrong_host_raises_with_hint_even_with_fallback(self, client, status, exc):
        client.client.request = AsyncMock(return_value=fake_response(status, {"detail": "Not Found"}))
        with pytest.raises(exc, match=r"check inference_base_url: http://model-router\.test"):
            await client.rerank("m", "q", DOCS, fallback="original-order")

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("WHIZURAI_API_KEY", "k")
        monkeypatch.setenv("WHIZAI_INFERENCE_URL", "http://mr.env")
        assert create_client_from_env().inference_base_url == "http://mr.env"


class TestErrorBodyParsing:
    @pytest.mark.parametrize(
        "body,expected",
        [
            ({"error": {"code": "no_worker_claimed", "message": "no worker"}}, "no worker"),
            ({"detail": {"error": "no_worker_claimed", "message": "no worker"}}, "no worker"),
            ({"detail": "Model not allowed"}, "Model not allowed"),
            ({"detail": [{"loc": ["body", "documents"], "msg": "too long"}]}, "body.documents: too long"),
            ({"error": "invalid_request", "message": "bad"}, "bad"),
            ({"error": "plain sentence"}, "plain sentence"),
            ({}, "fallback"),
        ],
    )
    def test_parse(self, body, expected):
        assert WhizuraiClient._error_message(body, "fallback") == expected

    async def test_server_message_survives_on_400(self, client):
        client.client.request = AsyncMock(
            return_value=fake_response(400, {"detail": {"error": "input_rejected", "message": "too many docs"}})
        )
        with pytest.raises(ValidationError, match="too many docs"):
            await client.rerank("m", "q", DOCS)
