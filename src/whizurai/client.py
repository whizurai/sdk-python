"""
Whizurai Python SDK Client

Capability-first async client for the Whizurai Platform. The client exposes four
resources — ``capabilities``, ``runs``, ``artifacts``, ``triggers`` — mirroring
the platform's public REST surface (``/v1/capabilities/:id/execute``,
``/v1/workflow-runs``, ``/v1/artifacts``, ``/v1/triggers``).
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from httpx import ConnectError, HTTPError, TimeoutException

from .types import (
    APIError,
    Artifact,
    AuthenticationError,
    Capability,
    ClientConfig,
    DryRunResult,
    ExecuteCapabilityResponse,
    HealthResponse,
    ListArtifactsResponse,
    ListCapabilitiesResponse,
    ListRunsResponse,
    ListTriggersResponse,
    NetworkError,
    NotFoundError,
    RateLimitError,
    Run,
    RunLogEntry,
    RunStatus,
    StatusResponse,
    TERMINAL_RUN_STATUSES,
    TimeoutError,
    Trigger,
    ValidationError,
    WhizuraiError,
)

logger = logging.getLogger(__name__)

SDK_VERSION = "2.0.0"


class WhizuraiClient:
    """
    Capability-first async client for the Whizurai Platform.

    Features:
    - Async/await support for all operations
    - Automatic retry with exponential backoff for transient failures
    - Typed error hierarchy (Authentication/NotFound/Validation/RateLimit/...)
    - Context manager support for resource cleanup
    """

    def __init__(self, config: ClientConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.api_key = config.api_key
        self.timeout = config.timeout
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay

        # The gateway accepts either header; send both so the same client works
        # for API-key auth regardless of which the deployment prefers.
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "X-API-Key": self.api_key,
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"whizurai-sdk-python/{SDK_VERSION}",
                "Accept": "application/json",
            },
        )

        # Resource accessors.
        self.capabilities = CapabilitiesResource(self)
        self.runs = RunsResource(self)
        self.artifacts = ArtifactsResource(self)
        self.triggers = TriggersResource(self)

        logger.info("Initialized Whizurai client for %s", self.base_url)

    async def __aenter__(self) -> "WhizuraiClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()
        logger.debug("Client closed")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retries: Optional[int] = None,
    ) -> Any:
        """
        Make an HTTP request with retry logic and typed error handling.

        Returns the decoded JSON body (dict or list).
        """
        if retries is None:
            retries = self.max_retries

        last_exception: Optional[Exception] = None

        for attempt in range(retries + 1):
            try:
                response = await self.client.request(
                    method=method,
                    url=endpoint,
                    json=data,
                    files=files,
                    params={k: v for k, v in (params or {}).items() if v is not None}
                    or None,
                    headers=headers,
                    timeout=self.timeout,
                )

                if 200 <= response.status_code < 300:
                    if not response.content:
                        return {}
                    return response.json()

                error_data = self._safe_json(response)
                message = self._error_message(error_data, response.reason_phrase)

                if response.status_code in (401, 403):
                    raise AuthenticationError(
                        message or "Authentication failed - check your API key"
                    )
                if response.status_code == 404:
                    raise NotFoundError(message or "Resource not found")
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    raise RateLimitError(
                        f"Rate limit exceeded. Retry after {retry_after} seconds"
                    )
                if response.status_code in (400, 422):
                    raise ValidationError(
                        f"Validation error: {message or 'invalid request data'}"
                    )
                if 400 <= response.status_code < 500:
                    raise APIError(
                        f"Client error {response.status_code}: {message}",
                        status_code=response.status_code,
                        response=error_data,
                    )
                # 5xx — retry with backoff.
                if attempt < retries:
                    logger.warning(
                        "Server error %s, retrying in %ss...",
                        response.status_code,
                        self.retry_delay,
                    )
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                raise APIError(
                    f"Server error {response.status_code}: {message}",
                    status_code=response.status_code,
                    response=error_data,
                )

            except TimeoutException as e:
                last_exception = TimeoutError(f"Request timeout: {e}")
            except ConnectError as e:
                last_exception = NetworkError(f"Connection error: {e}")
            except (
                AuthenticationError,
                NotFoundError,
                RateLimitError,
                ValidationError,
                APIError,
            ):
                # Already-typed, non-retryable errors propagate immediately.
                raise
            except HTTPError as e:
                last_exception = APIError(f"HTTP error: {e}")
            except Exception as e:  # noqa: BLE001 - normalize anything unexpected
                last_exception = WhizuraiError(f"Unexpected error: {e}")

            if attempt < retries:
                logger.warning("Request failed, retrying in %ss...", self.retry_delay)
                await asyncio.sleep(self.retry_delay * (2**attempt))
                continue
            raise last_exception

        raise last_exception or WhizuraiError("Request failed after all retries")

    @staticmethod
    def _safe_json(response: httpx.Response) -> Dict[str, Any]:
        try:
            return response.json() if response.content else {}
        except Exception:  # noqa: BLE001
            return {}

    @staticmethod
    def _error_message(error_data: Dict[str, Any], fallback: str) -> str:
        error = error_data.get("error")
        if isinstance(error, dict):
            return error.get("message") or error_data.get("message") or fallback
        if isinstance(error, str):
            return error
        return error_data.get("message") or fallback

    # ─── Health / status ────────────────────────────────────────────────────

    async def health_check(self) -> HealthResponse:
        """Unauthenticated gateway health check (``GET /health``)."""
        data = await self._make_request("GET", "/health")
        return HealthResponse(**data)

    async def get_status(self) -> StatusResponse:
        """Lightweight platform status (``GET /v1/status``)."""
        data = await self._make_request("GET", "/v1/status")
        return StatusResponse(**data)

    async def ping(self) -> bool:
        """Return ``True`` if the platform is reachable."""
        try:
            await self.health_check()
            return True
        except Exception:  # noqa: BLE001
            return False


class CapabilitiesResource:
    """List, inspect, dry-run, and execute capabilities."""

    def __init__(self, client: WhizuraiClient):
        self._client = client

    async def list(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> ListCapabilitiesResponse:
        """List capabilities, optionally filtered."""
        params = {
            "status": status,
            "category": category,
            "search": search,
            "limit": limit,
            "cursor": cursor,
        }
        data = await self._client._make_request("GET", "/v1/capabilities", params=params)
        return ListCapabilitiesResponse(**data)

    async def get(self, id_or_slug: str) -> Capability:
        """Fetch a single capability by id or slug."""
        data = await self._client._make_request(
            "GET", f"/v1/capabilities/{id_or_slug}"
        )
        if isinstance(data, dict) and "capability" in data:
            data = data["capability"]
        return Capability(**data)

    async def run(
        self,
        id_or_slug: str,
        input: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        webhook_url: Optional[str] = None,
        routing: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Run:
        """Execute a capability and return the created run."""
        body: Dict[str, Any] = {"input": input}
        if idempotency_key:
            body["idempotencyKey"] = idempotency_key
        if webhook_url:
            body["webhookUrl"] = webhook_url
        if routing:
            body["routing"] = routing
        if metadata:
            body["metadata"] = metadata

        headers = (
            {"x-idempotency-key": idempotency_key} if idempotency_key else None
        )
        data = await self._client._make_request(
            "POST",
            f"/v1/capabilities/{id_or_slug}/execute",
            data=body,
            headers=headers,
        )
        return ExecuteCapabilityResponse(**data).run

    async def dry_run(
        self, id_or_slug: str, input: Optional[Dict[str, Any]] = None
    ) -> DryRunResult:
        """Validate inputs and estimate cost without executing."""
        data = await self._client._make_request(
            "POST",
            f"/v1/capabilities/{id_or_slug}/dry-run",
            data={"input": input or {}},
        )
        valid = data.get("valid")
        if not isinstance(valid, bool):
            errors = data.get("errors") or []
            data["valid"] = data.get("status") == "valid" or (
                len(errors) == 0 and data.get("status") != "error"
            )
        return DryRunResult(**data)


class RunsResource:
    """Track capability runs, stream logs/artifacts, and poll to completion."""

    def __init__(self, client: WhizuraiClient):
        self._client = client

    async def get(self, run_id: str) -> Run:
        """Fetch a single run by id."""
        data = await self._client._make_request(
            "GET", f"/v1/workflow-runs/{run_id}"
        )
        return Run(**data)

    async def list(
        self,
        capability_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> ListRunsResponse:
        """List runs, optionally filtered by capability/status."""
        params = {
            "capabilityId": capability_id,
            "status": status,
            "limit": limit,
            "cursor": cursor,
        }
        data = await self._client._make_request(
            "GET", "/v1/workflow-runs", params=params
        )
        return ListRunsResponse(**data)

    async def logs(self, run_id: str) -> List[RunLogEntry]:
        """Structured logs for a run."""
        data = await self._client._make_request(
            "GET", f"/v1/workflow-runs/{run_id}/logs"
        )
        raw = data if isinstance(data, list) else data.get("logs", [])
        return [RunLogEntry(**entry) for entry in raw]

    async def artifacts(self, run_id: str) -> List[Artifact]:
        """Artifacts produced by a run."""
        data = await self._client._make_request(
            "GET", f"/v1/workflow-runs/{run_id}/artifacts", params={"grouped": "1"}
        )
        if isinstance(data, list):
            raw = data
        else:
            raw = data.get("artifacts")
            if raw is None:
                raw = [*data.get("outputs", []), *data.get("inputs", [])]
        return [Artifact(**a) for a in raw]

    async def poll_until_done(
        self,
        run_id: str,
        interval: float = 2.0,
        timeout: float = 600.0,
    ) -> Run:
        """Poll a run until it reaches a terminal status or ``timeout`` elapses."""
        loop = asyncio.get_event_loop()
        start = loop.time()
        while True:
            run = await self.get(run_id)
            if run.status in TERMINAL_RUN_STATUSES:
                return run
            if loop.time() - start >= timeout:
                raise TimeoutError(
                    f"Run {run_id} did not complete within {timeout}s"
                )
            await asyncio.sleep(interval)


class ArtifactsResource:
    """List and fetch artifacts produced by runs."""

    def __init__(self, client: WhizuraiClient):
        self._client = client

    async def list(
        self,
        run_id: Optional[str] = None,
        type: Optional[str] = None,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> ListArtifactsResponse:
        """List artifacts, optionally scoped to a run/type/query."""
        params = {
            "runId": run_id,
            "type": type,
            "query": query,
            "limit": limit,
            "offset": offset,
        }
        data = await self._client._make_request("GET", "/v1/artifacts", params=params)
        if isinstance(data, dict) and data.get("total") is None:
            data["total"] = data.get("count")
        return ListArtifactsResponse(**data)

    async def get(self, artifact_id: str) -> Artifact:
        """Fetch a single artifact by id."""
        data = await self._client._make_request(
            "GET", f"/v1/artifacts/{artifact_id}"
        )
        return Artifact(**data)


class TriggersResource:
    """Manage event-driven triggers that execute capabilities."""

    def __init__(self, client: WhizuraiClient):
        self._client = client

    async def list(
        self, app_id: Optional[str] = None, enabled: Optional[bool] = None
    ) -> ListTriggersResponse:
        """List triggers, optionally filtered by app/enabled state."""
        params: Dict[str, Any] = {"appId": app_id}
        if enabled is not None:
            params["enabled"] = "true" if enabled else "false"
        data = await self._client._make_request("GET", "/v1/triggers", params=params)
        return ListTriggersResponse(**data)

    async def get(self, trigger_id: str) -> Trigger:
        """Fetch a single trigger by id."""
        data = await self._client._make_request("GET", f"/v1/triggers/{trigger_id}")
        return Trigger(**data)

    async def create(
        self,
        name: str,
        event_type: str,
        action_type: str,
        action_config: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        description: Optional[str] = None,
    ) -> Trigger:
        """Create a new trigger."""
        body: Dict[str, Any] = {
            "name": name,
            "eventType": event_type,
            "actionType": action_type,
            "actionConfig": action_config,
            "enabled": enabled,
        }
        if filters is not None:
            body["filters"] = filters
        if description is not None:
            body["description"] = description
        data = await self._client._make_request("POST", "/v1/triggers", data=body)
        return Trigger(**data)

    async def update(self, trigger_id: str, **changes: Any) -> Trigger:
        """Update an existing trigger (partial). Accepts snake_case kwargs."""
        alias = {
            "event_type": "eventType",
            "action_type": "actionType",
            "action_config": "actionConfig",
        }
        body = {alias.get(k, k): v for k, v in changes.items() if v is not None}
        data = await self._client._make_request(
            "PUT", f"/v1/triggers/{trigger_id}", data=body
        )
        return Trigger(**data)

    async def delete(self, trigger_id: str) -> None:
        """Delete a trigger."""
        await self._client._make_request("DELETE", f"/v1/triggers/{trigger_id}")

    async def test(
        self, trigger_id: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fire a trigger against a sample event payload to validate it."""
        return await self._client._make_request(
            "POST", f"/v1/triggers/{trigger_id}/test", data=payload or {}
        )


def create_client(config: ClientConfig) -> WhizuraiClient:
    """Create a new Whizurai client from an explicit config."""
    return WhizuraiClient(config)


def create_client_from_env() -> WhizuraiClient:
    """
    Create a client using environment variables.

    Reads ``WHIZURAI_API_KEY`` (required) and ``WHIZURAI_BASE_URL`` (optional).
    """
    import os

    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("WHIZURAI_API_KEY")
    if not api_key:
        raise ValueError("WHIZURAI_API_KEY environment variable is required")

    base_url = os.getenv("WHIZURAI_BASE_URL", "https://api.whizurai.com")
    return create_client(ClientConfig(api_key=api_key, base_url=base_url))
