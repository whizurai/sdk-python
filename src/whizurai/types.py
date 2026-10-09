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
from typing import Any, Dict, List, Literal, Optional

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
    inference_base_url: Optional[str] = Field(
        default=None,
        description=(
            "Base URL of model-router, which serves POST /v1/embeddings and "
            "POST /v1/rerank (e.g. https://model-router.staging.whizur.ai). The "
            "gateway at base_url does not serve them. Required for embed()/rerank(); "
            "create_client_from_env() reads WHIZAI_INFERENCE_URL."
        ),
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
    #: The run's customer-facing name, taken verbatim from the capability's
    #: ``name``. ``None`` when the run has no capability — a workflow-only run
    #: has no human name anywhere, and formatting ``workflow_slug`` would
    #: substitute a guess for a fact. Fall back to the slug instead.
    title: Optional[str] = None
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


# ─── video:multi-shot@v1 ────────────────────────────────────────────────────
#
# One continuous video generated from an ordered list of shots, optionally
# holding named subjects consistent across every shot. It is not several clips
# stitched together, and it is billed as one task.
#
# These models are provider-neutral. Nothing here names a model or a provider's
# field vocabulary — a caller that writes provider reference syntax into a shot
# prompt has leaked the provider into product code, and will break the first
# time routing picks a different one.

#: Capability slug, for ``client.capabilities.run(...)``.
VIDEO_MULTI_SHOT = "video:multi-shot"


class VideoShot(BaseModel):
    """One shot of a multi-shot generation.

    List order IS shot order, all the way to the provider. Nothing re-sorts it.
    """

    prompt: str = Field(
        ...,
        description=(
            "What happens in this shot. May address a registered subject by its "
            "bare token (e.g. 'hero_pet'); the platform applies provider syntax."
        ),
    )
    duration_seconds: float = Field(
        ..., alias="durationSeconds", description="Length of this shot in seconds"
    )

    model_config = ConfigDict(populate_by_name=True)


class SubjectReference(BaseModel):
    """A named subject whose identity must survive the whole generation."""

    token: str = Field(
        ..., description="How shot prompts address this subject, e.g. 'hero_pet'"
    )
    description: Optional[str] = Field(
        default=None, description="Short factual description of the subject"
    )
    image_urls: List[str] = Field(
        ...,
        alias="imageUrls",
        description=(
            "Images establishing this subject's appearance. The routed model "
            "declares how many it needs (Kling 3.0 requires 2-4) and the platform "
            "refuses an out-of-range set before the task is billed."
        ),
    )

    model_config = ConfigDict(populate_by_name=True)


class VideoMultiShotInput(BaseModel):
    """Input for ``video:multi-shot@v1``."""

    start_image_url: Optional[str] = Field(
        default=None,
        alias="startImageUrl",
        description="The frame the sequence opens on",
    )
    shots: List[VideoShot] = Field(
        ..., description="Ordered shots; the routed model declares the maximum"
    )
    subject_references: Optional[List[SubjectReference]] = Field(
        default=None,
        alias="subjectReferences",
        description="Named subjects to keep consistent across shots",
    )
    aspect_ratio: Optional[str] = Field(default=None, alias="aspectRatio")
    resolution: Optional[str] = Field(default=None)
    audio: Optional[bool] = Field(
        default=None, description="Generate audio with the video; defaults to false"
    )

    model_config = ConfigDict(populate_by_name=True)


class VideoMultiShotOutput(BaseModel):
    """Output of ``video:multi-shot@v1``."""

    video: str = Field(..., description="The single sequenced video")

    model_config = ConfigDict(extra="allow")


def total_duration_seconds(shots: List[VideoShot]) -> float:
    """Seconds the request will bill for: the sum of the shot durations.

    Providers bill per second of generated output, so this is the number that
    decides cost — not the shot count.
    """
    return sum(shot.duration_seconds for shot in shots)


# ─── speech:synthesize ───────────────────────────────────────────────────────
#
# Text to speech on the local fleet. Asynchronous: ``capabilities.run`` returns
# a run and the audio is an artifact. No new endpoint. The capability is
# flag-gated on the platform (``ENABLE_SPEECH_SYNTHESIS``) and ships as draft.
# Shapes are flat and camelCase on the wire; the platform rejects unknown
# fields, so serialize with ``model_dump(by_alias=True, exclude_none=True)``.

#: Capability slug, for ``client.capabilities.run(...)``.
SPEECH_SYNTHESIZE = "speech:synthesize"

SpeechEngine = Literal["kokoro", "chatterbox"]

#: ``interactive`` is deliberately absent: a call over this capability is never
#: one a person is waiting on inside a request.
SpeechPriority = Literal["production", "batch", "backfill"]


class SpeechSynthesizeInput(BaseModel):
    """Input for ``speech:synthesize@v1``."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description=(
            "Plain UTF-8 text, no SSML. Each engine has a tighter cap (see the "
            "capability's experienceMeta); over the cap is refused, never truncated."
        ),
    )
    engine: SpeechEngine
    voice: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="kokoro: REQUIRED preset id, e.g. 'af_heart'. chatterbox: not accepted.",
    )
    reference_audio_artifact_id: Optional[str] = Field(
        default=None,
        alias="referenceAudioArtifactId",
        min_length=1,
        max_length=64,
        description=(
            "chatterbox: optional reference voice, an artifact owned by the calling "
            "app. kokoro: not accepted."
        ),
    )
    speed: Optional[float] = Field(
        default=None, ge=0.5, le=2, description="kokoro only"
    )
    exaggeration: Optional[float] = Field(
        default=None, ge=0.25, le=2, description="chatterbox only"
    )
    cfg_weight: Optional[float] = Field(
        default=None, alias="cfgWeight", ge=0, le=1, description="chatterbox only"
    )
    seed: Optional[int] = Field(
        default=None,
        ge=0,
        le=2_147_483_647,
        description="Best effort; the result reports seedApplied",
    )
    priority: Optional[SpeechPriority] = Field(
        default=None, description="Fleet class; the platform default is 'batch'"
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class SpeechWarning(BaseModel):
    """A non-fatal note on a successful synthesis. Never changes success."""

    code: str
    message: str

    model_config = ConfigDict(extra="allow")


class SpeechSynthesizeResult(BaseModel):
    """Output of ``speech:synthesize@v1`` (the audio artifact's metadata).

    Everything under "what actually served" comes from the executing worker,
    never from the request or the alias. There is no worker name and no echo of
    the text.
    """

    url: str = Field(
        ..., description="Storage URL; a bearer capability, do not forward credentials"
    )
    storage_key: str = Field(..., alias="storageKey")
    content_type: Literal["audio/wav"] = Field(..., alias="contentType")
    size_bytes: int = Field(..., alias="sizeBytes")
    sha256: str

    duration_ms: int = Field(..., alias="durationMs")
    sample_rate: int = Field(
        ..., alias="sampleRate", description="Reported, not promised: read it"
    )
    channels: Literal[1]
    bit_depth: Literal[16] = Field(..., alias="bitDepth")

    served_engine: SpeechEngine = Field(..., alias="servedEngine")
    served_voice: str = Field(..., alias="servedVoice")
    served_model: str = Field(..., alias="servedModel")
    model_revision: Optional[str] = Field(default=None, alias="modelRevision")
    runtime: str
    device_observed: Optional[str] = Field(default=None, alias="deviceObserved")
    watermark: Optional[Literal["perth"]] = None
    seed_applied: Optional[int] = Field(default=None, alias="seedApplied")
    attributable: bool

    job_id: str = Field(..., alias="jobId")
    input_chars: int = Field(..., alias="inputChars")
    wall_ms: Optional[int] = Field(default=None, alias="wallMs")
    warnings: List[SpeechWarning] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="allow")


# ─── Direct inference: embeddings + rerank ──────────────────────────────────
#
# Wire shapes for ``POST /v1/embeddings`` and ``POST /v1/rerank``; field names
# match the wire (snake_case) and mirror ``@whizurai/types/inference``.
#
# Provenance (``whizai``) is optional everywhere: older, non-fleet embedding
# models (e.g. ``nomic-embed-text``) answer without it. Treat a missing
# ``embedding_space`` as "comparable with nothing", never as a wildcard.

#: Pinned alias for the recommended fleet embedding model.
RECOMMENDED_EMBEDDING_MODEL = "embedding-qwen3-0.6b-v1"
#: Pinned alias for the recommended fleet rerank model.
RECOMMENDED_RERANK_MODEL = "rerank-qwen3-0.6b-v1"
#: Maximum inputs per ``POST /v1/embeddings`` call.
EMBEDDINGS_MAX_INPUTS = 128
#: Maximum documents per ``POST /v1/rerank`` call.
RERANK_MAX_DOCUMENTS = 64


class InferenceWorker(BaseModel):
    """The worker that executed a request, when attributable."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str


class InferenceProvenance(BaseModel):
    """Execution attribution shared by embeddings and rerank responses."""

    model_config = ConfigDict(extra="allow", protected_namespaces=())

    provider: Optional[str] = None
    runtime: Optional[str] = None
    execution: Optional[str] = None
    worker: Optional[InferenceWorker] = None
    model: Optional[str] = None
    model_revision: Optional[str] = None
    prompt_contract: Optional[str] = None
    #: ``False`` when the gateway could not establish which worker/model served it.
    attributable: Optional[bool] = None


class EmbeddingProvenance(InferenceProvenance):
    """Embedding provenance; ``embedding_space`` identifies the vector space."""

    dimensions: Optional[int] = None
    normalized: Optional[bool] = None
    #: ``model:revision:dimensions:normalization:prompt_contract``. Vectors are
    #: comparable only when these strings are identical.
    embedding_space: Optional[str] = None


class EmbeddingData(BaseModel):
    model_config = ConfigDict(extra="allow")

    object: str = "embedding"
    index: int
    embedding: List[float]


class EmbeddingsResponse(BaseModel):
    """Response of ``POST /v1/embeddings``."""

    model_config = ConfigDict(extra="allow")

    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: Optional[Dict[str, Any]] = None
    whizai: Optional[EmbeddingProvenance] = None

    @property
    def embedding_space(self) -> Optional[str]:
        """Shortcut for ``whizai.embedding_space`` (``None`` when absent)."""
        return self.whizai.embedding_space if self.whizai else None


class RerankResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    index: int
    #: ``None`` only in a degraded (fallback) response.
    relevance_score: Optional[float] = None


class RerankResponse(BaseModel):
    """Response of ``POST /v1/rerank``, or a degraded fallback.

    ``degraded`` is ``True`` only when ``fallback="original-order"`` was used
    and the reranker was unavailable; then ``results`` are in original order
    with ``relevance_score=None`` and ``reason``/``error`` explain why.
    """

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    id: Optional[str] = None
    model: str
    results: List[RerankResult]
    usage: Optional[Dict[str, Any]] = None
    whizai: Optional[InferenceProvenance] = None
    degraded: bool = False
    #: ``timeout``, ``network_error`` or ``http_<status>`` when degraded.
    reason: Optional[str] = None
    #: The underlying exception when degraded (excluded from serialization).
    error: Optional[Exception] = Field(default=None, exclude=True)


class EmbeddingSpaceError(WhizuraiError):
    """Two embedding spaces differ, or one is missing/not fully attributed."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def embedding_space_of(source: Any) -> Optional[str]:
    """Extract ``embedding_space`` from a string, provenance, response or dict."""
    if source is None:
        return None
    if isinstance(source, str):
        return source
    if isinstance(source, EmbeddingsResponse):
        return source.embedding_space
    if isinstance(source, EmbeddingProvenance):
        return source.embedding_space
    if isinstance(source, dict):
        if "whizai" in source:
            whizai = source.get("whizai") or {}
            return whizai.get("embedding_space") if isinstance(whizai, dict) else None
        return source.get("embedding_space")
    return None


def _known_space(space: Optional[str], label: str) -> str:
    if not isinstance(space, str) or not space.strip():
        raise EmbeddingSpaceError(
            f"Embedding space {label} is missing; refusing to compare vectors of unknown origin.",
            "EMBEDDING_SPACE_UNKNOWN",
        )
    if "unknown" in space.lower():
        raise EmbeddingSpaceError(
            f"Embedding space {label} is not fully attributed ({space}); refusing to compare.",
            "EMBEDDING_SPACE_UNKNOWN",
        )
    return space


def assert_same_embedding_space(a: Any, b: Any) -> str:
    """Raise :class:`EmbeddingSpaceError` unless ``a`` and ``b`` name the same,
    fully-known embedding space. Returns the shared space string.

    Never compare vectors across ``embedding_space`` values.
    """
    left = _known_space(embedding_space_of(a), "A")
    right = _known_space(embedding_space_of(b), "B")
    if left != right:
        raise EmbeddingSpaceError(
            f"Embedding spaces differ: {left!r} vs {right!r}. "
            "Vectors from different spaces are not comparable.",
            "EMBEDDING_SPACE_MISMATCH",
        )
    return left
