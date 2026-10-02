"""
Whizurai Python SDK

Capability-first async client for the Whizurai Platform. Execute published
capabilities, track their runs, read the resulting artifacts, and manage
event-driven triggers.

Example::

    import asyncio
    from whizurai import WhizuraiClient, ClientConfig

    async def main():
        async with WhizuraiClient(ClientConfig(api_key="sk_live_...")) as client:
            run = await client.capabilities.run("image.generate", {"prompt": "a red bike"})
            done = await client.runs.poll_until_done(run.id)
            artifacts = await client.runs.artifacts(done.id)

    asyncio.run(main())

Features:
- Full async/await support
- Pydantic-typed requests/responses
- Automatic retry with exponential backoff
- Typed error hierarchy and context-manager cleanup
"""

from .client import (
    ArtifactsResource,
    CapabilitiesResource,
    RunsResource,
    TriggersResource,
    WhizuraiClient,
    create_client,
    create_client_from_env,
)
from .types import (
    EMBEDDINGS_MAX_INPUTS,
    RECOMMENDED_EMBEDDING_MODEL,
    RECOMMENDED_RERANK_MODEL,
    RERANK_MAX_DOCUMENTS,
    EmbeddingData,
    EmbeddingProvenance,
    EmbeddingSpaceError,
    EmbeddingsResponse,
    InferenceProvenance,
    InferenceWorker,
    RerankResponse,
    RerankResult,
    assert_same_embedding_space,
    embedding_space_of,
    VIDEO_MULTI_SHOT,
    SubjectReference,
    VideoMultiShotInput,
    VideoMultiShotOutput,
    VideoShot,
    total_duration_seconds,
    APIError,
    Artifact,
    AuthenticationError,
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
    NetworkError,
    NotFoundError,
    RateLimitError,
    Run,
    RunLogEntry,
    RunStatus,
    StatusResponse,
    TimeoutError,
    Trigger,
    ValidationError,
    WhizuraiError,
)

__version__ = "2.1.0"
__author__ = "Whizurai Labs"
__email__ = "dev@whizurai.com"

__all__ = [
    # Embeddings + rerank
    "EMBEDDINGS_MAX_INPUTS",
    "RECOMMENDED_EMBEDDING_MODEL",
    "RECOMMENDED_RERANK_MODEL",
    "RERANK_MAX_DOCUMENTS",
    "EmbeddingData",
    "EmbeddingProvenance",
    "EmbeddingSpaceError",
    "EmbeddingsResponse",
    "InferenceProvenance",
    "InferenceWorker",
    "RerankResponse",
    "RerankResult",
    "assert_same_embedding_space",
    "embedding_space_of",
    "VIDEO_MULTI_SHOT",
    "SubjectReference",
    "VideoMultiShotInput",
    "VideoMultiShotOutput",
    "VideoShot",
    "total_duration_seconds",
    # Client + resources
    "WhizuraiClient",
    "CapabilitiesResource",
    "RunsResource",
    "ArtifactsResource",
    "TriggersResource",
    "create_client",
    "create_client_from_env",
    # Configuration
    "ClientConfig",
    # Capabilities
    "Capability",
    "CapabilityStatus",
    "ListCapabilitiesResponse",
    "DryRunResult",
    # Runs
    "Run",
    "RunStatus",
    "ListRunsResponse",
    "RunLogEntry",
    "ExecuteCapabilityResponse",
    # Artifacts
    "Artifact",
    "ListArtifactsResponse",
    # Triggers
    "Trigger",
    "ListTriggersResponse",
    # Health and status
    "HealthResponse",
    "StatusResponse",
    # Errors
    "WhizuraiError",
    "AuthenticationError",
    "NotFoundError",
    "RateLimitError",
    "ValidationError",
    "APIError",
    "NetworkError",
    "TimeoutError",
]
