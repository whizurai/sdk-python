"""
Type definitions for the Whizurai Python SDK.

This module contains all the Pydantic models for request/response validation
and type safety across the SDK.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


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


class ContentType(str, Enum):
    """Content type enumeration."""

    TEXT = "text"
    IMAGE = "image"


class SentimentType(str, Enum):
    """Sentiment type enumeration."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# AI Services Types


class GenerateRequest(BaseModel):
    """Request for content generation."""

    prompt: str = Field(..., description="The prompt for content generation")
    model: Optional[str] = Field(None, description="Specific model to use")
    max_tokens: Optional[int] = Field(1000, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(0.7, description="Temperature for generation")
    top_p: Optional[float] = Field(None, description="Top-p sampling parameter")
    frequency_penalty: Optional[float] = Field(None, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(None, description="Presence penalty")
    stop: Optional[List[str]] = Field(None, description="Stop sequences")
    stream: Optional[bool] = Field(False, description="Whether to stream the response")

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        if v is not None and (v < 0 or v > 2):
            raise ValueError("Temperature must be between 0 and 2")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Max tokens must be positive")
        return v


class GenerateResponse(BaseModel):
    """Response from content generation."""

    content: str = Field(..., description="Generated content")
    model: str = Field(..., description="Model used for generation")
    usage: Dict[str, int] = Field(..., description="Token usage information")
    finish_reason: Optional[str] = Field(None, description="Reason for completion")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class EnrichRequest(BaseModel):
    """Request for content enrichment."""

    content: str = Field(..., description="Content to enrich")
    type: ContentType = Field(..., description="Type of content")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional options")
    include_summary: Optional[bool] = Field(True, description="Include summary")
    include_tags: Optional[bool] = Field(True, description="Include tags")
    include_sentiment: Optional[bool] = Field(
        True, description="Include sentiment analysis"
    )
    include_entities: Optional[bool] = Field(
        False, description="Include entity extraction"
    )


class EnrichResponse(BaseModel):
    """Response from content enrichment."""

    tags: List[str] = Field(default_factory=list, description="Extracted tags")
    summary: Optional[str] = Field(None, description="Content summary")
    sentiment: Optional[SentimentType] = Field(None, description="Sentiment analysis")
    confidence: Optional[float] = Field(None, description="Confidence score")
    entities: Optional[List[Dict[str, Any]]] = Field(
        None, description="Extracted entities"
    )
    quality_score: Optional[float] = Field(None, description="Content quality score")
    language: Optional[str] = Field(None, description="Detected language")
    created_at: Optional[datetime] = Field(None, description="Processing timestamp")


class SearchRequest(BaseModel):
    """Request for semantic search."""

    query: str = Field(..., description="Search query")
    limit: Optional[int] = Field(10, description="Maximum number of results")
    offset: Optional[int] = Field(0, description="Offset for pagination")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    include_metadata: Optional[bool] = Field(
        True, description="Include metadata in results"
    )
    min_score: Optional[float] = Field(None, description="Minimum similarity score")

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Limit must be positive")
        return v

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v):
        if v is not None and v < 0:
            raise ValueError("Offset must be non-negative")
        return v


class SearchResult(BaseModel):
    """Individual search result."""

    id: str = Field(..., description="Result ID")
    content: str = Field(..., description="Result content")
    score: float = Field(..., description="Similarity score")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Result metadata"
    )
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class SearchResponse(BaseModel):
    """Response from semantic search."""

    results: List[SearchResult] = Field(
        default_factory=list, description="Search results"
    )
    total: int = Field(0, description="Total number of results")
    query: str = Field(..., description="Original query")
    processing_time: Optional[float] = Field(
        None, description="Processing time in seconds"
    )
    created_at: Optional[datetime] = Field(None, description="Search timestamp")


class RecommendRequest(BaseModel):
    """Request for recommendations."""

    user_id: str = Field(..., description="User ID for personalization")
    item_id: Optional[str] = Field(None, description="Reference item ID")
    limit: Optional[int] = Field(10, description="Maximum number of recommendations")
    include_reasons: Optional[bool] = Field(
        True, description="Include recommendation reasons"
    )
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Recommendation filters"
    )
    algorithm: Optional[str] = Field(
        None, description="Recommendation algorithm to use"
    )

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Limit must be positive")
        return v


class Recommendation(BaseModel):
    """Individual recommendation."""

    id: str = Field(..., description="Item ID")
    score: float = Field(..., description="Recommendation score")
    reason: Optional[str] = Field(None, description="Reason for recommendation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Item metadata")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class RecommendResponse(BaseModel):
    """Response from recommendations."""

    recommendations: List[Recommendation] = Field(
        default_factory=list, description="Recommendations"
    )
    user_id: str = Field(..., description="User ID")
    algorithm: Optional[str] = Field(None, description="Algorithm used")
    processing_time: Optional[float] = Field(
        None, description="Processing time in seconds"
    )
    created_at: Optional[datetime] = Field(None, description="Recommendation timestamp")


class ModerateRequest(BaseModel):
    """Request for content moderation."""

    content: str = Field(..., description="Content to moderate")
    type: ContentType = Field(..., description="Type of content")
    include_explanation: Optional[bool] = Field(True, description="Include explanation")
    include_categories: Optional[bool] = Field(
        True, description="Include category breakdown"
    )
    strict_mode: Optional[bool] = Field(False, description="Use strict moderation")


class ModerateResponse(BaseModel):
    """Response from content moderation."""

    safe: bool = Field(..., description="Whether content is safe")
    confidence: float = Field(..., description="Confidence score")
    categories: List[str] = Field(
        default_factory=list, description="Detected categories"
    )
    explanation: Optional[str] = Field(None, description="Moderation explanation")
    severity: Optional[str] = Field(None, description="Severity level")
    created_at: Optional[datetime] = Field(None, description="Moderation timestamp")


# File Management Types


class UploadRequest(BaseModel):
    """Request for file upload."""

    file_path: str = Field(..., description="Path to file to upload")
    options: Optional[Dict[str, Any]] = Field(None, description="Upload options")
    generate_variants: Optional[bool] = Field(
        False, description="Generate image variants"
    )
    compress: Optional[bool] = Field(True, description="Compress file")
    metadata: Optional[Dict[str, Any]] = Field(None, description="File metadata")


class UploadResponse(BaseModel):
    """Response from file upload."""

    id: str = Field(..., description="File ID")
    url: str = Field(..., description="File URL")
    size: int = Field(..., description="File size in bytes")
    type: str = Field(..., description="File MIME type")
    variants: Optional[List[Dict[str, Any]]] = Field(
        None, description="Generated variants"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="File metadata")
    created_at: Optional[datetime] = Field(None, description="Upload timestamp")


class FileInfo(BaseModel):
    """File information."""

    id: str = Field(..., description="File ID")
    url: str = Field(..., description="File URL")
    size: int = Field(..., description="File size in bytes")
    type: str = Field(..., description="File MIME type")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="File metadata")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


# Job Management Types


class JobInfo(BaseModel):
    """Job information."""

    id: str = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Job status")
    type: str = Field(..., description="Job type")
    progress: Optional[float] = Field(None, description="Job progress (0-100)")
    result: Optional[Dict[str, Any]] = Field(None, description="Job result")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class UsageStats(BaseModel):
    """Usage statistics."""

    total_requests: int = Field(0, description="Total API requests")
    total_tokens: int = Field(0, description="Total tokens used")
    total_cost: float = Field(0.0, description="Total cost in USD")
    requests_by_endpoint: Dict[str, int] = Field(
        default_factory=dict, description="Requests by endpoint"
    )
    tokens_by_model: Dict[str, int] = Field(
        default_factory=dict, description="Tokens by model"
    )
    period_start: Optional[datetime] = Field(None, description="Period start")
    period_end: Optional[datetime] = Field(None, description="Period end")


# Model Management Types


class ModelInfo(BaseModel):
    """Model information."""

    id: str = Field(..., description="Model ID")
    name: str = Field(..., description="Model name")
    provider: str = Field(..., description="Model provider")
    type: str = Field(..., description="Model type")
    capabilities: List[str] = Field(
        default_factory=list, description="Model capabilities"
    )
    cost_per_token: Optional[float] = Field(None, description="Cost per token")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens")
    available: bool = Field(True, description="Whether model is available")


class RouteRequest(BaseModel):
    """Request for model routing."""

    prompt: str = Field(..., description="Prompt for routing")
    type: str = Field(..., description="Request type")
    preferences: Optional[Dict[str, Any]] = Field(
        None, description="Routing preferences"
    )
    cost_limit: Optional[float] = Field(None, description="Cost limit")
    quality_requirement: Optional[str] = Field(None, description="Quality requirement")


class RouteResponse(BaseModel):
    """Response from model routing."""

    model: str = Field(..., description="Selected model")
    provider: str = Field(..., description="Model provider")
    reason: str = Field(..., description="Selection reason")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost")
    confidence: Optional[float] = Field(None, description="Selection confidence")


# Health and Status Types


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall status")
    timestamp: datetime = Field(..., description="Check timestamp")
    uptime: float = Field(..., description="Uptime in seconds")
    version: str = Field(..., description="API version")
    services: Dict[str, str] = Field(
        default_factory=dict, description="Service statuses"
    )
    memory_usage: Optional[Dict[str, Any]] = Field(None, description="Memory usage")
    cpu_usage: Optional[float] = Field(None, description="CPU usage percentage")


class StatusResponse(BaseModel):
    """API status response."""

    status: str = Field(..., description="API status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Status timestamp")
    features: List[str] = Field(default_factory=list, description="Available features")
    limits: Dict[str, Any] = Field(default_factory=dict, description="Rate limits")


# Error Types


class WhizuraiError(Exception):
    """Base exception for Whizurai SDK."""

    pass


class AuthenticationError(WhizuraiError):
    """Authentication error."""

    pass


class RateLimitError(WhizuraiError):
    """Rate limit exceeded error."""

    pass


class ValidationError(WhizuraiError):
    """Request validation error."""

    pass


class APIError(WhizuraiError):
    """General API error."""

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
