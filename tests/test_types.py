"""Tests for the capability-first Pydantic types."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from whizurai import (
    Artifact,
    Capability,
    CapabilityStatus,
    ClientConfig,
    DryRunResult,
    ExecuteCapabilityResponse,
    HealthResponse,
    ListArtifactsResponse,
    ListCapabilitiesResponse,
    ListRunsResponse,
    ListTriggersResponse,
    Run,
    RunStatus,
    StatusResponse,
    Trigger,
)


class TestClientConfig:
    def test_defaults(self):
        cfg = ClientConfig(api_key="sk_test")
        assert cfg.base_url == "https://api.whizurai.com"
        assert cfg.timeout == 30.0
        assert cfg.max_retries == 3

    def test_custom(self):
        cfg = ClientConfig(api_key="k", base_url="http://localhost:3000/", timeout=5.0)
        assert cfg.base_url.endswith("3000/")
        assert cfg.timeout == 5.0

    def test_invalid_timeout(self):
        with pytest.raises(PydanticValidationError):
            ClientConfig(api_key="k", timeout=0)

    def test_invalid_max_retries(self):
        with pytest.raises(PydanticValidationError):
            ClientConfig(api_key="k", max_retries=-1)


class TestCapability:
    def test_minimal(self):
        cap = Capability(id="c1", slug="image.generate", name="Generate")
        assert cap.status == CapabilityStatus.PUBLISHED
        assert cap.tags == []

    def test_alias_fields_and_extra(self):
        cap = Capability(
            id="c1",
            slug="s",
            name="n",
            status="published",
            inputSchema={"properties": {}},
            somethingNew="ok",
        )
        assert cap.input_schema == {"properties": {}}

    def test_list_envelope(self):
        resp = ListCapabilitiesResponse(
            capabilities=[{"id": "c1", "slug": "s", "name": "n"}],
            total=1,
            nextCursor="abc",
        )
        assert resp.total == 1
        assert resp.next_cursor == "abc"
        assert resp.capabilities[0].id == "c1"


class TestRun:
    def test_status_enum(self):
        run = Run(id="r1", status="succeeded")
        assert run.status == RunStatus.SUCCEEDED

    def test_execute_wrapper(self):
        wrapper = ExecuteCapabilityResponse(run={"id": "r1", "status": "pending"})
        assert wrapper.run.id == "r1"
        assert wrapper.run.status == RunStatus.PENDING

    def test_list_runs(self):
        resp = ListRunsResponse(runs=[{"id": "r1", "status": "running"}], total=1)
        assert resp.runs[0].status == RunStatus.RUNNING


class TestArtifact:
    def test_aliases(self):
        art = Artifact(id="a1", type="image", mimeType="image/png", runId="r1")
        assert art.mime_type == "image/png"
        assert art.run_id == "r1"

    def test_list(self):
        resp = ListArtifactsResponse(artifacts=[{"id": "a1"}], count=1, total=1)
        assert resp.total == 1


class TestTrigger:
    def test_aliases(self):
        t = Trigger(
            id="t1",
            name="T",
            eventType="artifact.created",
            actionType="execute_capability",
            actionConfig={"capabilityId": "c1"},
        )
        assert t.event_type == "artifact.created"
        assert t.action_config == {"capabilityId": "c1"}

    def test_list(self):
        resp = ListTriggersResponse(triggers=[], count=0)
        assert resp.count == 0


class TestMisc:
    def test_dry_run(self):
        r = DryRunResult(valid=True, status="valid", estimatedCost=2.5)
        assert r.valid is True
        assert r.estimated_cost == 2.5

    def test_health_and_status(self):
        h = HealthResponse(status="healthy")
        assert h.status == "healthy"
        s = StatusResponse(status="operational", version="0.2.0")
        assert s.version == "0.2.0"
