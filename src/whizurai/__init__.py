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
    SPEECH_SYNTHESIZE,
    VIDEO_MULTI_SHOT,
    APIError,
    Artifact,
    AudioTranscriptionResponse,
    AuthenticationError,
    Capability,
    CapabilityStatus,
    ClientConfig,
    DescribeImageResponse,
    DryRunResult,
    EmbeddingData,
    EmbeddingProvenance,
    EmbeddingSpaceError,
    EmbeddingsResponse,
    ExecuteCapabilityResponse,
    GenerateTextChoice,
    GenerateTextResponse,
    HealthResponse,
    InferenceProvenance,
    InferenceWorker,
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
    SpeechEngine,
    SpeechPriority,
    SpeechSynthesizeInput,
    SpeechSynthesizeResult,
    SpeechTimingProvenance,
    SpeechWarning,
    SpeechWordTiming,
    StatusResponse,
    SubjectReference,
    TimeoutError,
    TranscriptionPendingError,
    TranscriptionResponseFormat,
    TranscriptionSegment,
    Trigger,
    ValidationError,
    VideoMultiShotInput,
    VideoMultiShotOutput,
    VideoShot,
    WhizuraiError,
    assert_same_embedding_space,
    embedding_space_of,
    total_duration_seconds,
)

__version__ = "2.4.0"
__author__ = "Whizurai Labs"
__email__ = "dev@whizurai.com"

__all__ = [
    # Embeddings + rerank
    "EMBEDDINGS_MAX_INPUTS",
    "RECOMMENDED_EMBEDDING_MODEL",
    "RECOMMENDED_RERANK_MODEL",
    "RERANK_MAX_DOCUMENTS",
    "SPEECH_SYNTHESIZE",
    "VIDEO_MULTI_SHOT",
    "APIError",
    # Artifacts
    "Artifact",
    "ArtifactsResource",
    "AudioTranscriptionResponse",
    "AuthenticationError",
    "CapabilitiesResource",
    # Capabilities
    "Capability",
    "CapabilityStatus",
    # Configuration
    "ClientConfig",
    "DescribeImageResponse",
    "DryRunResult",
    "EmbeddingData",
    "EmbeddingProvenance",
    "EmbeddingSpaceError",
    "EmbeddingsResponse",
    "ExecuteCapabilityResponse",
    # Health and status
    "GenerateTextChoice",
    "GenerateTextResponse",
    "HealthResponse",
    "InferenceProvenance",
    "InferenceWorker",
    "ListArtifactsResponse",
    "ListCapabilitiesResponse",
    "ListRunsResponse",
    "ListTriggersResponse",
    "NetworkError",
    "NotFoundError",
    "RateLimitError",
    "RerankResponse",
    "RerankResult",
    # Runs
    "Run",
    "RunLogEntry",
    "RunStatus",
    "RunsResource",
    "SpeechEngine",
    "SpeechPriority",
    "SpeechSynthesizeInput",
    "SpeechSynthesizeResult",
    "SpeechTimingProvenance",
    "SpeechWarning",
    "SpeechWordTiming",
    "StatusResponse",
    "SubjectReference",
    "TimeoutError",
    "TranscriptionPendingError",
    "TranscriptionResponseFormat",
    "TranscriptionSegment",
    # Triggers
    "Trigger",
    "TriggersResource",
    "ValidationError",
    "VideoMultiShotInput",
    "VideoMultiShotOutput",
    "VideoShot",
    # Client + resources
    "WhizuraiClient",
    # Errors
    "WhizuraiError",
    "assert_same_embedding_space",
    "create_client",
    "create_client_from_env",
    "embedding_space_of",
    "total_duration_seconds",
]
