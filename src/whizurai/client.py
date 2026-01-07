"""
Whizurai Python SDK Client

Main client class for interacting with the Whizurai Platform.
Provides comprehensive API access with retry logic, error handling, and validation.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
from httpx import ConnectError, HTTPError, TimeoutException

from .types import (APIError, AuthenticationError, WhizuraiError, ClientConfig,
                    EnrichRequest, EnrichResponse, FileInfo, GenerateRequest,
                    GenerateResponse, HealthResponse, JobInfo, ModelInfo,
                    ModerateRequest, ModerateResponse, NetworkError,
                    RateLimitError, RecommendRequest, RecommendResponse,
                    RouteRequest, RouteResponse, SearchRequest, SearchResponse,
                    StatusResponse, TimeoutError, UploadResponse, UsageStats,
                    ValidationError)

# Configure logging
logger = logging.getLogger(__name__)


class WhizuraiClient:
    """
    Main client for interacting with the Whizurai Platform.

    This client provides comprehensive access to all platform services including
    AI generation, enrichment, search, recommendations, moderation, file management,
    job tracking, and system health monitoring.

    Features:
    - Async/await support for all operations
    - Automatic retry logic with exponential backoff
    - Comprehensive error handling and validation
    - Request/response logging and monitoring
    - Type safety with Pydantic models
    - Context manager support for resource cleanup
    """

    def __init__(self, config: ClientConfig):
        """
        Initialize the client with configuration.

        Args:
            config: Client configuration including API key, base URL, and settings
        """
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.api_key = config.api_key
        self.timeout = config.timeout
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay

        # Create HTTP client with default headers
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "whizurai-sdk-python/0.2.0",
                "Accept": "application/json",
            },
        )

        # Setup request/response interceptors
        self._setup_interceptors()

        logger.info(f"Initialized Whizurai client for {self.base_url}")

    def _setup_interceptors(self):
        """Setup request and response interceptors for logging and error handling."""

        # Request interceptor
        async def request_interceptor(request):
            logger.debug(f"Making request: {request.method} {request.url}")
            return request

        # Response interceptor
        async def response_interceptor(response):
            logger.debug(
                f"Received response: {response.status_code} {response.reason_phrase}"
            )
            return response

        # Add interceptors
        self.client.event_hooks["request"] = [request_interceptor]
        self.client.event_hooks["response"] = [response_interceptor]

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client and cleanup resources."""
        await self.client.aclose()
        logger.debug("Client closed")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            files: File upload data
            params: Query parameters
            retries: Number of retries (uses config default if None)

        Returns:
            Response data as dictionary

        Raises:
            APIError: For API-related errors
            NetworkError: For network connectivity issues
            TimeoutError: For request timeouts
            AuthenticationError: For authentication failures
            RateLimitError: For rate limit exceeded
        """
        if retries is None:
            retries = self.max_retries

        last_exception: Optional[Exception] = None

        for attempt in range(retries + 1):
            try:
                # Prepare request kwargs
                kwargs: Dict[str, Any] = {
                    "method": method,
                    "url": endpoint,
                    "timeout": self.timeout,
                }

                if data is not None:
                    kwargs["json"] = data
                if files is not None:
                    kwargs["files"] = files
                if params is not None:
                    kwargs["params"] = params

                # Make the request
                response = await self.client.request(
                    method=kwargs["method"],
                    url=kwargs["url"],
                    timeout=kwargs["timeout"],
                    json=kwargs.get("json"),
                    files=kwargs.get("files"),
                    params=kwargs.get("params"),
                )

                # Handle different status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 201:
                    return response.json()
                elif response.status_code == 401:
                    raise AuthenticationError(
                        "Invalid API key or authentication failed"
                    )
                elif response.status_code == 403:
                    raise AuthenticationError(
                        "Access forbidden - check API key permissions"
                    )
                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    raise RateLimitError(
                        f"Rate limit exceeded. Retry after {retry_after} seconds"
                    )
                elif response.status_code == 422:
                    error_data = response.json() if response.content else {}
                    raise ValidationError(
                        f"Validation error: {error_data.get('message', 'Invalid request data')}"
                    )
                elif 400 <= response.status_code < 500:
                    error_data = response.json() if response.content else {}
                    raise APIError(
                        f"Client error {response.status_code}: {error_data.get('message', response.reason_phrase)}",
                        status_code=response.status_code,
                        response=error_data,
                    )
                elif 500 <= response.status_code < 600:
                    if attempt < retries:
                        logger.warning(
                            f"Server error {response.status_code}, retrying in {self.retry_delay}s..."
                        )
                        await asyncio.sleep(
                            self.retry_delay * (2**attempt)
                        )  # Exponential backoff
                        continue
                    else:
                        error_data = response.json() if response.content else {}
                        raise APIError(
                            f"Server error {response.status_code}: {error_data.get('message', response.reason_phrase)}",
                            status_code=response.status_code,
                            response=error_data,
                        )
                else:
                    raise APIError(f"Unexpected status code: {response.status_code}")

            except TimeoutException as e:
                last_exception = TimeoutError(f"Request timeout: {e}")
                if attempt < retries:
                    logger.warning(f"Timeout, retrying in {self.retry_delay}s...")
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                else:
                    raise last_exception

            except ConnectError as e:
                last_exception = NetworkError(f"Connection error: {e}")
                if attempt < retries:
                    logger.warning(
                        f"Connection error, retrying in {self.retry_delay}s..."
                    )
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                else:
                    raise last_exception

            except (
                AuthenticationError,
                RateLimitError,
                ValidationError,
                APIError,
            ) as e:
                # These errors should not be retried
                raise e

            except HTTPError as e:
                last_exception = APIError(f"HTTP error: {e}")
                if attempt < retries:
                    logger.warning(f"HTTP error, retrying in {self.retry_delay}s...")
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                else:
                    raise last_exception

            except Exception as e:
                last_exception = WhizuraiError(f"Unexpected error: {e}")
                if attempt < retries:
                    logger.warning(
                        f"Unexpected error, retrying in {self.retry_delay}s..."
                    )
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                else:
                    raise last_exception

        # If we get here, all retries failed
        raise last_exception or WhizuraiError("Request failed after all retries")

    # AI Services Methods

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """
        Generate content using AI models.

        Args:
            request: Generation request with prompt and parameters

        Returns:
            Generated content response

        Raises:
            APIError: For API-related errors
            ValidationError: For invalid request data
        """
        logger.info("Generating content with AI models")
        response_data = await self._make_request(
            "POST", "/v1/generate", data=request.model_dump()
        )
        return GenerateResponse(**response_data)

    async def enrich(self, request: EnrichRequest) -> EnrichResponse:
        """
        Enrich content with AI capabilities.

        Args:
            request: Enrichment request with content and options

        Returns:
            Enriched content response with tags, summary, sentiment, etc.
        """
        logger.info("Enriching content with AI capabilities")
        response_data = await self._make_request(
            "POST", "/v1/enrich", data=request.model_dump()
        )
        return EnrichResponse(**response_data)

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Perform semantic search over content.

        Args:
            request: Search request with query and filters

        Returns:
            Search results with similarity scores
        """
        logger.info("Performing semantic search")
        response_data = await self._make_request(
            "POST", "/v1/search", data=request.model_dump()
        )
        return SearchResponse(**response_data)

    async def recommend(self, request: RecommendRequest) -> RecommendResponse:
        """
        Get personalized recommendations.

        Args:
            request: Recommendation request with user ID and preferences

        Returns:
            Personalized recommendations with scores and reasons
        """
        logger.info("Getting personalized recommendations")
        response_data = await self._make_request(
            "POST", "/v1/recommend", data=request.model_dump()
        )
        return RecommendResponse(**response_data)

    async def moderate(self, request: ModerateRequest) -> ModerateResponse:
        """
        Moderate content for safety and compliance.

        Args:
            request: Moderation request with content to check

        Returns:
            Moderation results with safety assessment
        """
        logger.info("Moderating content for safety")
        response_data = await self._make_request(
            "POST", "/v1/moderate", data=request.model_dump()
        )
        return ModerateResponse(**response_data)

    async def ingest(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest content into the platform for processing.

        Args:
            content: Content to ingest
            metadata: Optional metadata for the content

        Returns:
            Ingestion result with content ID
        """
        logger.info("Ingesting content into platform")
        request_data: Dict[str, Any] = {"content": content}
        if metadata:
            request_data["metadata"] = metadata
        return await self._make_request("POST", "/v1/ingest", data=request_data)

    # File Management Methods

    async def upload_file(
        self, file_path: Union[str, Path], options: Optional[Dict[str, Any]] = None
    ) -> UploadResponse:
        """
        Upload a file to the platform.

        Args:
            file_path: Path to file to upload
            options: Optional upload options

        Returns:
            Upload response with file ID and URL
        """
        logger.info(f"Uploading file: {file_path}")

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            form_data = options or {}

            response_data = await self._make_request(
                "POST", "/v1/files/upload", files=files, data=form_data
            )

        return UploadResponse(**response_data)

    async def get_file(self, file_id: str) -> FileInfo:
        """
        Get file information and metadata.

        Args:
            file_id: File ID to retrieve

        Returns:
            File information and metadata
        """
        logger.info(f"Getting file info: {file_id}")
        response_data = await self._make_request("GET", f"/v1/files/{file_id}")
        return FileInfo(**response_data)

    async def process_file(
        self, file_id: str, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a file (e.g., generate variants, extract metadata).

        Args:
            file_id: File ID to process
            options: Processing options

        Returns:
            Processing result
        """
        logger.info(f"Processing file: {file_id}")
        data = options or {}
        return await self._make_request(
            "POST", f"/v1/files/{file_id}/process", data=data
        )

    # Job Management Methods

    async def get_job(self, job_id: str) -> JobInfo:
        """
        Get job status and results.

        Args:
            job_id: Job ID to check

        Returns:
            Job information and status
        """
        logger.info(f"Getting job status: {job_id}")
        response_data = await self._make_request("GET", f"/v1/jobs/{job_id}")
        return JobInfo(**response_data)

    async def get_usage(self, period: Optional[str] = None) -> UsageStats:
        """
        Get usage statistics and billing information.

        Args:
            period: Time period for usage stats (e.g., 'month', 'year')

        Returns:
            Usage statistics and costs
        """
        logger.info("Getting usage statistics")
        params = {"period": period} if period else None
        response_data = await self._make_request("GET", "/v1/usage", params=params)
        return UsageStats(**response_data)

    # Model Management Methods

    async def get_models(self) -> List[ModelInfo]:
        """
        Get available AI models.

        Returns:
            List of available models with capabilities
        """
        logger.info("Getting available models")
        response_data = await self._make_request("GET", "/v1/models")
        return [ModelInfo(**model) for model in response_data.get("models", [])]

    async def route_model(self, request: RouteRequest) -> RouteResponse:
        """
        Get model routing recommendation.

        Args:
            request: Routing request with prompt and preferences

        Returns:
            Recommended model and provider
        """
        logger.info("Getting model routing recommendation")
        response_data = await self._make_request(
            "POST", "/v1/models/route", data=request.model_dump()
        )
        return RouteResponse(**response_data)

    # Health and Status Methods

    async def health_check(self) -> HealthResponse:
        """
        Check platform health status.

        Returns:
            Health status with service information
        """
        logger.info("Checking platform health")
        response_data = await self._make_request("GET", "/health")
        return HealthResponse(**response_data)

    async def get_status(self) -> StatusResponse:
        """
        Get API status and version information.

        Returns:
            API status and available features
        """
        logger.info("Getting API status")
        response_data = await self._make_request("GET", "/v1/status")
        return StatusResponse(**response_data)

    # Utility Methods

    async def ping(self) -> bool:
        """
        Simple ping to check connectivity.

        Returns:
            True if platform is reachable, False otherwise
        """
        try:
            await self.health_check()
            return True
        except Exception:
            return False


def create_client(config: ClientConfig) -> WhizuraiClient:
    """
    Create a new Whizurai client.

    Args:
        config: Client configuration

    Returns:
        Configured client instance
    """
    return WhizuraiClient(config)


# Convenience function for quick setup
def create_client_from_env() -> WhizuraiClient:
    """
    Create a client using environment variables.

    Expected environment variables:
    - WHIZURAI_API_KEY: Your API key
    - WHIZURAI_BASE_URL: Base URL (optional, defaults to localhost)

    Returns:
        Configured client instance
    """
    import os

    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("WHIZURAI_API_KEY")
    if not api_key:
        raise ValueError("WHIZURAI_API_KEY environment variable is required")

    base_url = os.getenv("WHIZURAI_BASE_URL", "https://api.whizurai.com")

    config = ClientConfig(api_key=api_key, base_url=base_url)
    return create_client(config)
