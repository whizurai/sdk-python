"""
Whizurai Python SDK Client

Capability-first async client for the Whizurai Platform. The client exposes four
resources — ``capabilities``, ``runs``, ``artifacts``, ``triggers`` — mirroring
the platform's public REST surface (``/v1/capabilities/:id/execute``,
``/v1/workflow-runs``, ``/v1/artifacts``, ``/v1/triggers``).
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

import httpx
from httpx import ConnectError, HTTPError, TimeoutException

from .types import (
    APIError,
    Artifact,
    AuthenticationError,
    Capability,
    ClientConfig,
    DryRunResult,
    EmbeddingsResponse,
    ExecuteCapabilityResponse,
    HealthResponse,
    ListArtifactsResponse,
    ListCapabilitiesResponse,
    ListRunsResponse,
    ListTriggersResponse,
    NetworkError,
    NotFoundError,
    RateLimitError,
    RerankResponse,
    RerankResult,
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

SDK_VERSION = "2.1.0"


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
        self.inference_base_url = (
            config.inference_base_url.rstrip("/") if config.inference_base_url else None
        )

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
        timeout: Optional[float] = None,
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
                    timeout=timeout if timeout is not None else self.timeout,
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
    def _error_message(error_data: Any, fallback: str) -> str:
        """Server message from any platform error body.

        Handles ``{"error": {"code", "message"}}``, ``{"error": "...", "message"}``,
        ``{"message"}`` and FastAPI's ``{"detail": "..."}``,
        ``{"detail": {"error", "message"}}`` and ``{"detail": [{"loc", "msg"}]}``.
        """
        if isinstance(error_data, str):
            return error_data or fallback
        if not isinstance(error_data, dict):
            return fallback
        error = error_data.get("error")
        if isinstance(error, dict) and error.get("message"):
            return error["message"]
        if error_data.get("message"):
            return error_data["message"]
        detail = error_data.get("detail")
        if isinstance(detail, str) and detail:
            return detail
        if isinstance(detail, dict):
            nested = detail.get("error")
            if detail.get("message"):
                return detail["message"]
            if isinstance(nested, dict) and nested.get("message"):
                return nested["message"]
            if isinstance(nested, str) and nested:
                return nested
        if isinstance(detail, list):
            parts = []
            for item in detail:
                if isinstance(item, dict) and (item.get("msg") or item.get("message")):
                    loc = item.get("loc")
                    msg = item.get("msg") or item.get("message")
                    parts.append(f"{'.'.join(str(x) for x in loc)}: {msg}" if loc else msg)
            if parts:
                return "; ".join(parts)
        if isinstance(error, str) and error:
            return error
        return fallback

    # ─── Direct inference: embeddings + rerank ─────────────────────────────

    def _inference_url(self, path: str) -> str:
        """Absolute model-router URL; embed/rerank are not served by the gateway."""
        if not self.inference_base_url:
            raise WhizuraiError(
                "embed()/rerank() require inference_base_url (the model-router URL, e.g. "
                "'https://model-router.staging.whizur.ai'; env WHIZAI_INFERENCE_URL with "
                "create_client_from_env). The gateway base_url does not serve "
                "/v1/embeddings or /v1/rerank."
            )
        return f"{self.inference_base_url}{path}"

    async def _inference_request(self, path: str, body: Dict[str, Any], **kwargs: Any) -> Any:
        """POST to model-router. 401/403/404 there usually mean a wrong host."""
        url = self._inference_url(path)
        try:
            return await self._make_request("POST", url, data=body, **kwargs)
        except (AuthenticationError, NotFoundError) as exc:
            raise type(exc)(
                f"{exc} (check inference_base_url: {self.inference_base_url})"
            ) from exc

    @staticmethod
    def _require_model(model: Any, method: str) -> str:
        if not isinstance(model, str) or not model.strip():
            raise ValidationError(
                f"{method} requires an explicit model (e.g. 'embedding-qwen3-0.6b-v1'). "
                "There is no default: the vector space must be a deliberate choice."
            )
        return model

    async def embed(
        self,
        model: str,
        input: Union[str, List[str]],
        input_type: Optional[str] = None,
        instruction: Optional[str] = None,
    ) -> EmbeddingsResponse:
        """Embed text (``POST /v1/embeddings``).

        ``model`` is required — there is no default, because the model fixes
        the vector space. ``input_type`` is ``"query"`` or ``"document"``
        (server default ``"document"``) — retrieval queries MUST pass
        ``"query"``: Qwen3-Embedding applies its instruction only to queries.
        Served by model-router: requires ``inference_base_url``. The response carries
        ``whizai.embedding_space``; never compare vectors across spaces (see
        :func:`assert_same_embedding_space`).
        """
        body: Dict[str, Any] = {
            "model": self._require_model(model, "embed()"),
            "input": input,
        }
        if input_type:
            body["input_type"] = input_type
        if instruction:
            body["instruction"] = instruction
        data = await self._inference_request("/v1/embeddings", body)
        return EmbeddingsResponse(**data)

    async def rerank(
        self,
        model: str,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None,
        instruction: Optional[str] = None,
        fallback: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> RerankResponse:
        """Rerank ``documents`` against ``query`` (``POST /v1/rerank``).

        With ``fallback="original-order"`` this never raises on timeout,
        network error, 408, 429 or 5xx: it returns ``degraded=True`` with the
        documents in their original order (``relevance_score=None``,
        truncated to ``top_n``) and makes a single attempt (no retries) so
        ``timeout`` (seconds) bounds the call. Other 4xx errors always raise
        (401/403/404 messages name ``inference_base_url``).

        Served by model-router: requires ``inference_base_url``.
        """
        if fallback not in (None, "original-order"):
            raise ValueError("fallback must be None or 'original-order'")
        body: Dict[str, Any] = {
            "model": self._require_model(model, "rerank()"),
            "query": query,
            "documents": documents,
        }
        if top_n is not None:
            body["top_n"] = top_n
        if instruction:
            body["instruction"] = instruction

        # A missing inference_base_url is a config bug: raise even in fallback mode.
        self._inference_url("/v1/rerank")
        try:
            data = await self._inference_request(
                "/v1/rerank",
                body,
                timeout=timeout,
                retries=0 if fallback else None,
            )
        except WhizuraiError as exc:
            reason = _rerank_degrade_reason(exc) if fallback else None
            if reason is None:
                raise
            n = len(documents or [])
            if top_n is not None and top_n >= 0:
                n = min(n, top_n)
            logger.warning("rerank degraded to original order: %s (%s)", reason, exc)
            return RerankResponse(
                model=model,
                results=[RerankResult(index=i, relevance_score=None) for i in range(n)],
                degraded=True,
                reason=reason,
                error=exc,
            )
        return RerankResponse(**data)

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


def _rerank_degrade_reason(exc: Exception) -> Optional[str]:
    """Reason string if a rerank failure may degrade, else ``None`` (raise)."""
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, NetworkError):
        return "network_error"
    if isinstance(exc, RateLimitError):
        return "http_429"
    if isinstance(exc, APIError):
        status = exc.status_code
        if status is None:
            return "network_error"
        if status >= 500 or status == 408:
            return f"http_{status}"
    # ValidationError / AuthenticationError / NotFoundError / other 4xx: caller bugs.
    return None


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

    Reads ``WHIZURAI_API_KEY`` (required), ``WHIZURAI_BASE_URL`` (optional) and
    ``WHIZAI_INFERENCE_URL`` (optional; model-router URL for embed/rerank).
    """
    import os

    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("WHIZURAI_API_KEY")
    if not api_key:
        raise ValueError("WHIZURAI_API_KEY environment variable is required")

    base_url = os.getenv("WHIZURAI_BASE_URL", "https://api.whizurai.com")
    inference_base_url = os.getenv("WHIZAI_INFERENCE_URL") or None
    return create_client(
        ClientConfig(api_key=api_key, base_url=base_url, inference_base_url=inference_base_url)
    )
