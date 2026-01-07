"""
Whizurai Python SDK

Unified API client for the Whizurai Platform providing easy access
to all platform services and capabilities.

This SDK provides comprehensive access to:
- AI content generation and enrichment
- Semantic search and recommendations
- Content moderation and safety
- File upload and management
- Job tracking and monitoring
- Model management and routing
- Health monitoring and status

Features:
- Full async/await support
- Comprehensive type safety with Pydantic
- Automatic retry logic with exponential backoff
- Detailed error handling and validation
- Request/response logging and monitoring
- Context manager support for resource cleanup
"""

from .client import WhizuraiClient, create_client, create_client_from_env
from .types import (  # Configuration; AI Services; File Management; Job Management; Model Management; Health and Status; Enums; Error Types
    APIError, AuthenticationError, WhizuraiError, ClientConfig, ContentType, EnrichRequest,
    EnrichResponse, FileInfo, GenerateRequest, GenerateResponse,
    HealthResponse, JobInfo, JobStatus, ModelInfo, ModerateRequest,
    ModerateResponse, NetworkError, RateLimitError, Recommendation,
    RecommendRequest, RecommendResponse, RouteRequest, RouteResponse,
    SearchRequest, SearchResponse, SearchResult, SentimentType, StatusResponse,
    TimeoutError, UploadRequest, UploadResponse, UsageStats, ValidationError)

__version__ = "0.2.0"
__author__ = "Whizurai Labs"
__email__ = "dev@whizurai.com"

__all__ = [
    # Client classes and factories
    "WhizuraiClient",
    "create_client",
    "create_client_from_env",
    # Configuration
    "ClientConfig",
    # AI Services
    "GenerateRequest",
    "GenerateResponse",
    "EnrichRequest",
    "EnrichResponse",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "RecommendRequest",
    "RecommendResponse",
    "Recommendation",
    "ModerateRequest",
    "ModerateResponse",
    # File Management
    "UploadRequest",
    "UploadResponse",
    "FileInfo",
    # Job Management
    "JobInfo",
    "JobStatus",
    # Usage
    "UsageStats",
    # Model Management
    "ModelInfo",
    "RouteRequest",
    "RouteResponse",
    # Health and Status
    "HealthResponse",
    "StatusResponse",
    # Enums
    "ContentType",
    "SentimentType",
    # Error Types
    "WhizuraiError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "APIError",
    "NetworkError",
    "TimeoutError",
]
