"""
Type definitions for the Whizurai Python SDK.

The platform's public surface is capability-first: you list/execute
capabilities, track their runs, and read the resulting artifacts. These
Pydantic models cover that surface plus client configuration and the typed
error hierarchy.

Response models allow extra fields (``extra="allow"``) so forward-compatible
additions from the platform never break deserialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── Client configuration ───────────────────────────────────────────────────


class ClientConfig(BaseModel):
    """Configuration for the Whizurai client."""

    api_key: str = Field(..., description="API key for authentication")
    base_url: str = Field(
        default="https://api.whizurai.com", description="Base URL for the API"
    )
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    max_retries: int = Field(
        default=3, description="Maximum number of retries for failed requests"
    )
    retry_delay: float = Field(
        default=1.0, description="Delay between retries in seconds"
    )

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, v):
        if v < 0:
            raise ValueError("Max retries must be non-negative")
        return v


# ─── Enums ──────────────────────────────────────────────────────────────────


class CapabilityStatus(str, Enum):
    """Lifecycle status of a capability."""

    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class RunStatus(str, Enum):
    """Lifecycle status of a capability/workflow run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


#: Statuses at which a run is finished and will not change further.
TERMINAL_RUN_STATUSES = frozenset(
    {RunStatus.SUCCEEDED, RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
)


# ─── Capabilities ───────────────────────────────────────────────────────────


class Capability(BaseModel):
    """A productized, executable AI capability."""

    model_config = ConfigDict(extra="allow")

    id: str
    slug: str
    name: str
    status: CapabilityStatus = CapabilityStatus.PUBLISHED
    version: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    input_contract: Optional[List[Dict[str, Any]]] = Field(
        default=None, alias="inputContract"
    )
    input_schema: Optional[Dict[str, Any]] = Field(default=None, alias="inputSchema")
    output_schema: Optional[Dict[str, Any]] = Field(default=None, alias="outputSchema")


class ListCapabilitiesResponse(BaseModel):
    """Paginated list of capabilities."""

    model_config = ConfigDict(extra="allow")

    capabilities: List[Capability] = Field(default_factory=list)
    total: Optional[int] = None
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")


class DryRunResult(BaseModel):
    """Result of validating a capability's inputs without executing."""

    model_config = ConfigDict(extra="allow")

    valid: bool = False
    status: Optional[str] = None
    resolved_inputs: Optional[Dict[str, Any]] = Field(
        default=None, alias="resolvedInputs"
    )
    resolved_artifacts: Optional[Dict[str, Any]] = Field(
        default=None, alias="resolvedArtifacts"
    )
    estimated_cost: Optional[float] = Field(default=None, alias="estimatedCost")
    warnings: List[Any] = Field(default_factory=list)
    errors: List[Any] = Field(default_factory=list)


# ─── Artifacts ──────────────────────────────────────────────────────────────


class Artifact(BaseModel):
    """An artifact produced by a run."""

    model_config = ConfigDict(extra="allow")

    id: str
    type: Optional[str] = None
    name: Optional[str] = None
    filename: Optional[str] = None
    url: Optional[str] = None
    preview_url: Optional[str] = Field(default=None, alias="previewUrl")
    mime_type: Optional[str] = Field(default=None, alias="mimeType")
    size_bytes: Optional[int] = Field(default=None, alias="sizeBytes")
    run_id: Optional[str] = Field(default=None, alias="runId")
    step_id: Optional[str] = Field(default=None, alias="stepId")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")


class ListArtifactsResponse(BaseModel):
    """List of artifacts."""

    model_config = ConfigDict(extra="allow")

    artifacts: List[Artifact] = Field(default_factory=list)
    count: Optional[int] = None
    total: Optional[int] = None


# ─── Runs ───────────────────────────────────────────────────────────────────


# ─── Run presentation ───────────────────────────────────────────────────────


class PresentedOutput(BaseModel):
    """One presentable value from a run's result.

    ``semantic_type`` is intentionally a plain string, not an enum: an
    unrecognised value must degrade gracefully rather than fail validation.
    Known values: text, markdown, object, collection, image, video, audio,
    file, unknown.
    """

    model_config = ConfigDict(extra="allow")

    key: str
    label: str
    semantic_type: str = Field(alias="semanticType")
    value: Optional[Any] = None
    truncated: Optional[bool] = None
    href: Optional[str] = None
    mime_type: Optional[str] = Field(default=None, alias="mimeType")
    size_bytes: Optional[int] = Field(default=None, alias="sizeBytes")
    artifact_id: Optional[str] = Field(default=None, alias="artifactId")
    item_type: Optional[str] = Field(default=None, alias="itemType")
    item_count: Optional[int] = Field(default=None, alias="itemCount")
    items: Optional[List["PresentedOutput"]] = None
    schema_: Optional[Dict[str, Any]] = Field(default=None, alias="schema")


class PresentedInput(BaseModel):
    """An input echoed alongside the result that it produced."""

    model_config = ConfigDict(extra="allow")

    key: str
    label: str
    semantic_type: Optional[str] = Field(default=None, alias="semanticType")
    value: Optional[Any] = None
    href: Optional[str] = None
    mime_type: Optional[str] = Field(default=None, alias="mimeType")


class PresentedAction(BaseModel):
    """An affordance for a result.

    ``id`` is one of copy | download | open | play | view_raw | save_as_asset |
    reuse, or ``continuation`` for a capability that can consume this result.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    output_key: Optional[str] = Field(default=None, alias="outputKey")
    primary: Optional[bool] = None
    capability_slug: Optional[str] = Field(default=None, alias="capabilitySlug")


class RunPresentation(BaseModel):
    """Derived read model for a run's result.

    Present only when the platform has the feature enabled and the run
    succeeded. Never persisted; recomputed per request from the run's canonical
    ``result`` plus its capability's output declarations.

    ``source`` is the honesty field: ``declared`` means the values came from the
    workflow's declared outputs; ``inferred`` means a compatibility adapter
    reconstructed them for a run predating the canonical-result contract.
    """

    model_config = ConfigDict(extra="allow")

    contract_version: int = Field(alias="contractVersion")
    source: str
    primary: Optional[PresentedOutput] = None
    secondary: List[PresentedOutput] = Field(default_factory=list)
    debug: List[PresentedOutput] = Field(default_factory=list)
    inputs: List[PresentedInput] = Field(default_factory=list)
    actions: List[PresentedAction] = Field(default_factory=list)


class Run(BaseModel):
    """A single execution of a capability."""

    model_config = ConfigDict(extra="allow")

    id: str
    status: RunStatus = RunStatus.PENDING
    capability_id: Optional[str] = Field(default=None, alias="capabilityId")
    workflow_run_id: Optional[str] = Field(default=None, alias="workflowRunId")
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    presentation: Optional[RunPresentation] = None
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    progress: Optional[float] = None
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    started_at: Optional[datetime] = Field(default=None, alias="startedAt")
    completed_at: Optional[datetime] = Field(default=None, alias="completedAt")


class ExecuteCapabilityResponse(BaseModel):
    """Wrapper returned by ``POST /v1/capabilities/:id/execute``."""

    model_config = ConfigDict(extra="allow")

    run: Run


class ListRunsResponse(BaseModel):
    """List of runs."""

    model_config = ConfigDict(extra="allow")

    runs: List[Run] = Field(default_factory=list)
    total: Optional[int] = None
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")


class RunLogEntry(BaseModel):
    """A single structured log line for a run."""

    model_config = ConfigDict(extra="allow")

    level: Optional[str] = None
    message: str = ""
    timestamp: Optional[str] = None
    step_id: Optional[str] = Field(default=None, alias="stepId")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ─── Triggers ───────────────────────────────────────────────────────────────


class Trigger(BaseModel):
    """An event-driven automation that executes a capability."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    enabled: bool = True
    event_type: str = Field(alias="eventType")
    action_type: str = Field(alias="actionType")
    action_config: Dict[str, Any] = Field(default_factory=dict, alias="actionConfig")
    filters: Dict[str, Any] = Field(default_factory=dict)
    app_id: Optional[str] = Field(default=None, alias="appId")
    description: Optional[str] = None
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")


class ListTriggersResponse(BaseModel):
    """List of triggers."""

    model_config = ConfigDict(extra="allow")

    triggers: List[Trigger] = Field(default_factory=list)
    count: int = 0


# ─── Health and status ──────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Gateway health check response."""

    model_config = ConfigDict(extra="allow")

    status: str
    timestamp: Optional[datetime] = None
    uptime: Optional[float] = None
    version: Optional[str] = None
    checks: Dict[str, Any] = Field(default_factory=dict)


class StatusResponse(BaseModel):
    """Lightweight platform status response."""

    model_config = ConfigDict(extra="allow")

    status: str
    version: str
    timestamp: Optional[datetime] = None


# ─── Error hierarchy ────────────────────────────────────────────────────────


class WhizuraiError(Exception):
    """Base exception for the Whizurai SDK."""

    pass


class AuthenticationError(WhizuraiError):
    """Authentication or authorization failure (401/403)."""

    pass


class NotFoundError(WhizuraiError):
    """Requested resource was not found (404)."""

    pass


class RateLimitError(WhizuraiError):
    """Rate limit exceeded (429)."""

    pass


class ValidationError(WhizuraiError):
    """Request validation error (400/422)."""

    pass


class APIError(WhizuraiError):
    """General API error carrying status code and response body."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class NetworkError(WhizuraiError):
    """Network connectivity error."""

    pass


class TimeoutError(WhizuraiError):
    """Request timeout error."""

    pass
