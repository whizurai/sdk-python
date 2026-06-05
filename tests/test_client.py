"""Tests for the capability-first WhizuraiClient (mocked HTTP)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ConnectError, TimeoutException

from whizurai import (
    APIError,
    AuthenticationError,
    ClientConfig,
    NetworkError,
    NotFoundError,
    RateLimitError,
    Run,
    RunStatus,
    TimeoutError,
    ValidationError,
    WhizuraiClient,
    create_client,
)


def make_config(**overrides):
    base = dict(
        api_key="test_api_key",
        base_url="http://localhost:3000",
        timeout=5.0,
        max_retries=2,
        retry_delay=0.0,
    )
    base.update(overrides)
    return ClientConfig(**base)


def fake_response(status_code=200, json_data=None, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.content = b"{}" if json_data is None else b'{"x":1}'
    resp.headers = headers or {}
    resp.reason_phrase = "OK"
    return resp


@pytest.fixture
def client():
    return WhizuraiClient(make_config())


class TestInitialization:
    async def test_init(self):
        c = WhizuraiClient(make_config())
        assert c.base_url == "http://localhost:3000"
        assert c.api_key == "test_api_key"
        assert c.capabilities and c.runs and c.artifacts and c.triggers
        await c.close()

    def test_create_client(self):
        assert isinstance(create_client(make_config()), WhizuraiClient)

    async def test_context_manager(self):
        async with WhizuraiClient(make_config()) as c:
            assert isinstance(c, WhizuraiClient)


class TestMakeRequest:
    async def test_success(self, client):
        client.client.request = AsyncMock(return_value=fake_response(200, {"ok": True}))
        data = await client._make_request("GET", "/v1/x")
        assert data == {"ok": True}

    async def test_empty_body(self, client):
        client.client.request = AsyncMock(return_value=fake_response(204, None))
        assert await client._make_request("DELETE", "/v1/x") == {}

    async def test_401(self, client):
        client.client.request = AsyncMock(return_value=fake_response(401))
        with pytest.raises(AuthenticationError):
            await client._make_request("GET", "/v1/x")

    async def test_404(self, client):
        client.client.request = AsyncMock(return_value=fake_response(404))
        with pytest.raises(NotFoundError):
            await client._make_request("GET", "/v1/x")

    async def test_429(self, client):
        client.client.request = AsyncMock(
            return_value=fake_response(429, headers={"Retry-After": "1"})
        )
        with pytest.raises(RateLimitError):
            await client._make_request("GET", "/v1/x")

    async def test_422(self, client):
        client.client.request = AsyncMock(
            return_value=fake_response(422, {"error": {"message": "bad"}})
        )
        with pytest.raises(ValidationError):
            await client._make_request("POST", "/v1/x", data={})

    async def test_400_api_error(self, client):
        client.client.request = AsyncMock(
            return_value=fake_response(409, {"message": "conflict"})
        )
        with pytest.raises(APIError) as exc:
            await client._make_request("POST", "/v1/x", data={})
        assert exc.value.status_code == 409

    async def test_500_retries_then_raises(self, client):
        client.client.request = AsyncMock(return_value=fake_response(500))
        with pytest.raises(APIError):
            await client._make_request("GET", "/v1/x")
        # initial + max_retries(2) = 3 attempts
        assert client.client.request.await_count == 3

    async def test_500_then_success(self, client):
        client.client.request = AsyncMock(
            side_effect=[fake_response(503), fake_response(200, {"ok": 1})]
        )
        assert await client._make_request("GET", "/v1/x") == {"ok": 1}

    async def test_timeout_retries(self, client):
        client.client.request = AsyncMock(side_effect=TimeoutException("slow"))
        with pytest.raises(TimeoutError):
            await client._make_request("GET", "/v1/x")

    async def test_connect_error(self, client):
        client.client.request = AsyncMock(side_effect=ConnectError("down"))
        with pytest.raises(NetworkError):
            await client._make_request("GET", "/v1/x")


class TestCapabilities:
    async def test_list(self, client):
        client._make_request = AsyncMock(
            return_value={"capabilities": [{"id": "c1", "slug": "s", "name": "n"}], "total": 1}
        )
        resp = await client.capabilities.list(status="published", limit=5)
        client._make_request.assert_awaited_once()
        args, kwargs = client._make_request.call_args
        assert args[1] == "/v1/capabilities"
        assert kwargs["params"]["status"] == "published"
        assert resp.capabilities[0].id == "c1"

    async def test_get_unwraps_capability(self, client):
        client._make_request = AsyncMock(
            return_value={"capability": {"id": "c1", "slug": "s", "name": "n"}}
        )
        cap = await client.capabilities.get("image.generate")
        assert cap.id == "c1"
        assert client._make_request.call_args[0][1] == "/v1/capabilities/image.generate"

    async def test_run(self, client):
        client._make_request = AsyncMock(
            return_value={"run": {"id": "r1", "status": "pending"}}
        )
        run = await client.capabilities.run("c1", {"prompt": "hi"}, idempotency_key="k1")
        assert isinstance(run, Run)
        args, kwargs = client._make_request.call_args
        assert args[1] == "/v1/capabilities/c1/execute"
        assert kwargs["data"]["idempotencyKey"] == "k1"
        assert kwargs["headers"]["x-idempotency-key"] == "k1"

    async def test_dry_run_derives_valid(self, client):
        client._make_request = AsyncMock(return_value={"status": "valid", "estimatedCost": 1})
        res = await client.capabilities.dry_run("c1", {"a": 1})
        assert res.valid is True


class TestRuns:
    async def test_get(self, client):
        client._make_request = AsyncMock(return_value={"id": "r1", "status": "succeeded"})
        run = await client.runs.get("r1")
        assert run.status == RunStatus.SUCCEEDED
        assert client._make_request.call_args[0][1] == "/v1/workflow-runs/r1"

    async def test_list(self, client):
        client._make_request = AsyncMock(return_value={"runs": [{"id": "r1", "status": "running"}]})
        resp = await client.runs.list(limit=3)
        assert resp.runs[0].id == "r1"

    async def test_logs(self, client):
        client._make_request = AsyncMock(return_value={"logs": [{"message": "hi"}]})
        logs = await client.runs.logs("r1")
        assert logs[0].message == "hi"

    async def test_artifacts_flatten(self, client):
        client._make_request = AsyncMock(
            return_value={"outputs": [{"id": "a1"}], "inputs": [{"id": "a2"}]}
        )
        arts = await client.runs.artifacts("r1")
        assert [a.id for a in arts] == ["a1", "a2"]

    async def test_poll_until_done(self, client):
        client.runs.get = AsyncMock(
            side_effect=[
                Run(id="r1", status="running"),
                Run(id="r1", status="succeeded"),
            ]
        )
        run = await client.runs.poll_until_done("r1", interval=0, timeout=5)
        assert run.status == RunStatus.SUCCEEDED

    async def test_poll_timeout(self, client):
        client.runs.get = AsyncMock(return_value=Run(id="r1", status="running"))
        with pytest.raises(TimeoutError):
            await client.runs.poll_until_done("r1", interval=0, timeout=-1)


class TestArtifacts:
    async def test_list_maps_count(self, client):
        client._make_request = AsyncMock(return_value={"artifacts": [{"id": "a1"}], "count": 1})
        resp = await client.artifacts.list(run_id="r1")
        assert resp.total == 1

    async def test_get(self, client):
        client._make_request = AsyncMock(return_value={"id": "a1", "type": "image"})
        art = await client.artifacts.get("a1")
        assert art.type == "image"


class TestTriggers:
    async def test_list(self, client):
        client._make_request = AsyncMock(return_value={"triggers": [{"id": "t1", "name": "T", "eventType": "e", "actionType": "a"}], "count": 1})
        resp = await client.triggers.list()
        assert resp.count == 1

    async def test_create(self, client):
        client._make_request = AsyncMock(
            return_value={"id": "t1", "name": "T", "eventType": "e", "actionType": "a"}
        )
        t = await client.triggers.create(
            name="T", event_type="e", action_type="a", action_config={"capabilityId": "c1"}
        )
        assert t.id == "t1"
        body = client._make_request.call_args.kwargs["data"]
        assert body["eventType"] == "e"

    async def test_update(self, client):
        client._make_request = AsyncMock(
            return_value={"id": "t1", "name": "T", "eventType": "e", "actionType": "a", "enabled": False}
        )
        t = await client.triggers.update("t1", enabled=False)
        assert t.enabled is False

    async def test_delete(self, client):
        client._make_request = AsyncMock(return_value={"message": "ok"})
        assert await client.triggers.delete("t1") is None

    async def test_test(self, client):
        client._make_request = AsyncMock(return_value={"success": True})
        res = await client.triggers.test("t1", {"artifact": {"id": "x"}})
        assert res["success"] is True


class TestHealth:
    async def test_health_status_ping(self, client):
        client._make_request = AsyncMock(
            side_effect=[
                {"status": "healthy"},
                {"status": "operational", "version": "0.2.0"},
                {"status": "healthy"},
            ]
        )
        assert (await client.health_check()).status == "healthy"
        assert (await client.get_status()).version == "0.2.0"
        assert await client.ping() is True

    async def test_ping_false_on_error(self, client):
        client._make_request = AsyncMock(side_effect=NetworkError("down"))
        assert await client.ping() is False
