"""Tests for client.outcomes (mocked HTTP)."""

import re
from unittest.mock import AsyncMock

import pytest

from whizurai import APIError, ClientConfig, OutcomeRunEvent, WhizuraiClient
from whizurai.client import SDK_VERSION

import whizurai


@pytest.fixture
def client():
    return WhizuraiClient(
        ClientConfig(api_key="k", base_url="http://localhost:3000", max_retries=0, retry_delay=0.0)
    )


def test_version_in_lockstep():
    assert SDK_VERSION == whizurai.__version__


async def test_run_sends_execution_policy(client):
    client._make_request = AsyncMock(
        return_value={"outcomeRun": {"id": "or_1", "status": "PENDING", "statusUrl": "/v1/outcomes/runs/or_1"}}
    )
    handle = await client.outcomes.run("five shot", {"idea": "a fox"}, execution_policy="review")
    method, path = client._make_request.call_args[0]
    assert (method, path) == ("POST", "/v1/outcomes/five%20shot/runs")
    assert client._make_request.call_args.kwargs["data"] == {
        "inputs": {"idea": "a fox"},
        "executionPolicy": "review",
    }
    assert handle.id == "or_1" and handle.status_url == "/v1/outcomes/runs/or_1"


async def test_get_run_reads_interactive(client):
    client._make_request = AsyncMock(
        return_value={"outcomeRun": {"id": "or_1", "status": "RUNNING", "interactive": True, "acuConsumed": None}}
    )
    run = await client.outcomes.get_run("or_1")
    assert run.interactive is True
    assert client._make_request.call_args[0] == ("GET", "/v1/outcomes/runs/or_1")


async def test_workspace(client):
    client._make_request = AsyncMock(return_value={"runId": "or_1", "controlRevision": 3})
    ws = await client.outcomes.workspace("or/1")
    assert ws["controlRevision"] == 3
    assert client._make_request.call_args[0] == ("GET", "/v1/outcomes/runs/or%2F1/workspace")


async def test_command_with_client_action_id(client):
    client._make_request = AsyncMock(return_value={"result": {"dispatch": True}, "workspace": {}})
    command = {"action": "generate", "operation": "image", "targets": [{"itemId": "it_1"}]}
    out = await client.outcomes.command("or_1", command, client_action_id="action-0001")
    assert out["result"]["dispatch"] is True
    assert client._make_request.call_args[0] == ("POST", "/v1/outcomes/runs/or_1/commands")
    assert client._make_request.call_args.kwargs["data"] == {
        "command": command,
        "clientActionId": "action-0001",
    }


async def test_command_generates_uuid(client):
    client._make_request = AsyncMock(return_value={"result": {}, "workspace": {}})
    await client.outcomes.command("or_1", {"action": "pause", "expectedControlRevision": 3})
    sent = client._make_request.call_args.kwargs["data"]["clientActionId"]
    assert re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", sent)


async def test_preview_sends_no_client_action_id(client):
    client._make_request = AsyncMock(return_value={"result": {"preview": {}}, "workspace": {}})
    command = {"action": "finish_remaining", "expectedControlRevision": 3, "preview": True}
    await client.outcomes.command("or_1", command)
    assert client._make_request.call_args.kwargs["data"] == {"command": command}


async def test_state_changed_carries_workspace(client, monkeypatch):
    class Resp:
        status_code = 409
        content = b"{}"
        headers = {}
        reason_phrase = "Conflict"

        def json(self):
            return {"error": "STATE_CHANGED", "message": "Refresh.", "workspace": {"controlRevision": 4}}

    client.client.request = AsyncMock(return_value=Resp())
    with pytest.raises(APIError) as info:
        await client.outcomes.command("or_1", {"action": "retry", "invocationId": "inv_1"})
    assert info.value.status_code == 409
    assert info.value.response["workspace"]["controlRevision"] == 4


async def test_invocation(client):
    client._make_request = AsyncMock(return_value={"acceptance": "submitted"})
    detail = await client.outcomes.invocation("or_1", "inv_1")
    assert detail["acceptance"] == "submitted"
    assert client._make_request.call_args[0] == ("GET", "/v1/outcomes/runs/or_1/invocations/inv_1")


async def test_events(client):
    client._make_request = AsyncMock(
        return_value={
            "events": [
                {
                    "id": "ev_1",
                    "outcomeRunId": "or_1",
                    "type": "edit_applied",
                    "actorType": "api_key",
                    "actorId": "k1",
                    "itemId": None,
                    "data": None,
                    "createdAt": "2026-11-11T00:00:00.000Z",
                }
            ]
        }
    )
    events = await client.outcomes.events("or_1")
    assert isinstance(events[0], OutcomeRunEvent)
    assert events[0].actor_type == "api_key"
    client._make_request = AsyncMock(return_value={})
    assert await client.outcomes.events("or_1") == []
