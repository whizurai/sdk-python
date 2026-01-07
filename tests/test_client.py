"""
Tests for the Whizurai client.
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ConnectError, TimeoutException

from whizurai import (APIError, AuthenticationError, CheckoutRequest,
                           CheckoutResponse, WhizuraiClient, ClientConfig,
                           ContentType, EnrichRequest, EnrichResponse,
                           FileInfo, GenerateRequest, GenerateResponse,
                           HealthResponse, JobInfo, JobStatus, ModelInfo,
                           ModerateRequest, ModerateResponse, NetworkError,
                           RateLimitError, RecommendRequest, RecommendResponse,
                           RouteRequest, RouteResponse, SearchRequest,
                           SearchResponse, SentimentType, StatusResponse,
                           TimeoutError, UploadResponse, UsageStats,
                           ValidationError, create_client,
                           create_client_from_env)


class TestWhizuraiClient:
    """Test cases for WhizuraiClient."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return ClientConfig(
            api_key="test_api_key",
            base_url="http://localhost:3000",
            timeout=30.0,
            max_retries=3,
            retry_delay=1.0,
        )

    @pytest.fixture
    def client(self, config):
        """Create a test client."""
        return WhizuraiClient(config)

    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""
        response = MagicMock()
        response.json.return_value = {"success": True, "data": {}}
        response.status_code = 200
        response.headers = {}
        return response

    @pytest.mark.asyncio
    async def test_client_initialization(self, config):
        """Test client initialization."""
        client = WhizuraiClient(config)
        assert client.config == config
        assert client.base_url == "http://localhost:3000"
        assert client.api_key == "test_api_key"
        assert client.timeout == 30.0
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        """Test client as context manager."""
        async with WhizuraiClient(config) as client:
            assert isinstance(client, WhizuraiClient)

    @pytest.mark.asyncio
    async def test_generate_success(self, client, mock_response):
        """Test successful content generation."""
        mock_response.json.return_value = {
            "content": "Generated content",
            "model": "gpt-3.5-turbo",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

        with patch.object(client.client, "request", return_value=mock_response):
            request = GenerateRequest(prompt="Test prompt")
            response = await client.generate(request)

            assert isinstance(response, GenerateResponse)
            assert response.content == "Generated content"
            assert response.model == "gpt-3.5-turbo"
            assert response.usage["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_generate_validation_error(self, client):
        """Test content generation with validation error."""
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"message": "Validation error"}
        mock_response.content = b'{"message": "Validation error"}'

        with patch.object(client.client, "request", return_value=mock_response):
            request = GenerateRequest(prompt="Test prompt")

            with pytest.raises(ValidationError, match="Validation error"):
                await client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_authentication_error(self, client):
        """Test content generation with authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid API key"}
        mock_response.content = b'{"message": "Invalid API key"}'

        with patch.object(client.client, "request", return_value=mock_response):
            request = GenerateRequest(prompt="Test prompt")

            with pytest.raises(AuthenticationError, match="Invalid API key"):
                await client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_rate_limit_error(self, client):
        """Test content generation with rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.json.return_value = {"message": "Rate limit exceeded"}
        mock_response.content = b'{"message": "Rate limit exceeded"}'

        with patch.object(client.client, "request", return_value=mock_response):
            request = GenerateRequest(prompt="Test prompt")

            with pytest.raises(RateLimitError, match="Rate limit exceeded"):
                await client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_retry_logic(self, client):
        """Test retry logic for server errors."""
        # First two calls fail with 500, third succeeds
        mock_responses = [
            MagicMock(
                status_code=500,
                json=MagicMock(return_value={"message": "Server error"}),
                content=b'{"message": "Server error"}',
            ),
            MagicMock(
                status_code=500,
                json=MagicMock(return_value={"message": "Server error"}),
                content=b'{"message": "Server error"}',
            ),
            MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "content": "Generated content",
                        "model": "gpt-3.5-turbo",
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 20,
                            "total_tokens": 30,
                        },
                    }
                ),
            ),
        ]

        with patch.object(client.client, "request", side_effect=mock_responses):
            request = GenerateRequest(prompt="Test prompt")
            response = await client.generate(request)

            assert response.content == "Generated content"

    @pytest.mark.asyncio
    async def test_generate_max_retries_exceeded(self, client):
        """Test that max retries are respected."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Server error"}
        mock_response.content = b'{"message": "Server error"}'

        with patch.object(client.client, "request", return_value=mock_response):
            request = GenerateRequest(prompt="Test prompt")

            with pytest.raises(APIError, match="Server error"):
                await client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_timeout_error(self, client):
        """Test timeout error handling."""
        with patch.object(
            client.client, "request", side_effect=TimeoutException("Request timeout")
        ):
            request = GenerateRequest(prompt="Test prompt")

            with pytest.raises(TimeoutError, match="Request timeout"):
                await client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_network_error(self, client):
        """Test network error handling."""
        with patch.object(
            client.client, "request", side_effect=ConnectError("Connection failed")
        ):
            request = GenerateRequest(prompt="Test prompt")

            with pytest.raises(NetworkError, match="Connection failed"):
                await client.generate(request)

    @pytest.mark.asyncio
    async def test_enrich_success(self, client, mock_response):
        """Test successful content enrichment."""
        mock_response.json.return_value = {
            "tags": ["technology", "ai"],
            "summary": "Test summary",
            "sentiment": "positive",
            "confidence": 0.95,
            "quality_score": 0.8,
        }

        with patch.object(client.client, "request", return_value=mock_response):
            request = EnrichRequest(content="Test content", type=ContentType.TEXT)
            response = await client.enrich(request)

            assert isinstance(response, EnrichResponse)
            assert response.tags == ["technology", "ai"]
            assert response.summary == "Test summary"
            assert response.sentiment == SentimentType.POSITIVE
            assert response.confidence == 0.95

    @pytest.mark.asyncio
    async def test_search_success(self, client, mock_response):
        """Test successful semantic search."""
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "1",
                    "content": "Test content",
                    "score": 0.95,
                    "metadata": {"type": "document"},
                }
            ],
            "total": 1,
            "query": "test query",
        }

        with patch.object(client.client, "request", return_value=mock_response):
            request = SearchRequest(query="test query")
            response = await client.search(request)

            assert isinstance(response, SearchResponse)
            assert len(response.results) == 1
            assert response.results[0].id == "1"
            assert response.results[0].score == 0.95
            assert response.total == 1

    @pytest.mark.asyncio
    async def test_recommend_success(self, client, mock_response):
        """Test successful recommendations."""
        mock_response.json.return_value = {
            "recommendations": [
                {"id": "item1", "score": 0.9, "reason": "Similar to your interests"}
            ],
            "user_id": "user123",
        }

        with patch.object(client.client, "request", return_value=mock_response):
            request = RecommendRequest(user_id="user123")
            response = await client.recommend(request)

            assert isinstance(response, RecommendResponse)
            assert len(response.recommendations) == 1
            assert response.recommendations[0].id == "item1"
            assert response.user_id == "user123"

    @pytest.mark.asyncio
    async def test_moderate_success(self, client, mock_response):
        """Test successful content moderation."""
        mock_response.json.return_value = {
            "safe": True,
            "confidence": 0.95,
            "categories": [],
            "explanation": "Content is safe",
        }

        with patch.object(client.client, "request", return_value=mock_response):
            request = ModerateRequest(content="Test content", type=ContentType.TEXT)
            response = await client.moderate(request)

            assert isinstance(response, ModerateResponse)
            assert response.safe is True
            assert response.confidence == 0.95
            assert response.explanation == "Content is safe"

    @pytest.mark.asyncio
    async def test_upload_file_success(self, client, mock_response, tmp_path):
        """Test successful file upload."""
        mock_response.json.return_value = {
            "id": "file123",
            "url": "https://example.com/file123",
            "size": 1024,
            "type": "image/jpeg",
        }

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        with patch.object(client.client, "request", return_value=mock_response):
            response = await client.upload_file(str(test_file))

            assert isinstance(response, UploadResponse)
            assert response.id == "file123"
            assert response.url == "https://example.com/file123"
            assert response.size == 1024

    @pytest.mark.asyncio
    async def test_upload_file_not_found(self, client):
        """Test file upload with non-existent file."""
        with pytest.raises(FileNotFoundError):
            await client.upload_file("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_get_file_success(self, client, mock_response):
        """Test successful file retrieval."""
        mock_response.json.return_value = {
            "id": "file123",
            "url": "https://example.com/file123",
            "size": 1024,
            "type": "image/jpeg",
            "metadata": {"name": "test.jpg"},
        }

        with patch.object(client.client, "request", return_value=mock_response):
            response = await client.get_file("file123")

            assert isinstance(response, FileInfo)
            assert response.id == "file123"
            assert response.size == 1024

    @pytest.mark.asyncio
    async def test_get_job_success(self, client, mock_response):
        """Test successful job retrieval."""
        mock_response.json.return_value = {
            "id": "job123",
            "status": "completed",
            "type": "generation",
            "progress": 100.0,
            "result": {"content": "Generated content"},
        }

        with patch.object(client.client, "request", return_value=mock_response):
            response = await client.get_job("job123")

            assert isinstance(response, JobInfo)
            assert response.id == "job123"
            assert response.status == JobStatus.COMPLETED
            assert response.progress == 100.0

    @pytest.mark.asyncio
    async def test_checkout_success(self, client, mock_response):
        """Test successful checkout creation."""
        mock_response.json.return_value = {
            "session_id": "cs_test_123",
            "url": "https://checkout.stripe.com/c/pay/cs_test_123",
            "amount": 2000,
            "currency": "usd",
        }

        with patch.object(client.client, "request", return_value=mock_response):
            request = CheckoutRequest(items=[{"id": "item1", "price": 2000}])
            response = await client.checkout(request)

            assert isinstance(response, CheckoutResponse)
            assert response.session_id == "cs_test_123"
            assert response.amount == 2000

    @pytest.mark.asyncio
    async def test_get_usage_success(self, client, mock_response):
        """Test successful usage retrieval."""
        mock_response.json.return_value = {
            "total_requests": 1000,
            "total_tokens": 50000,
            "total_cost": 10.50,
            "requests_by_endpoint": {"generate": 500, "enrich": 300},
            "tokens_by_model": {"gpt-3.5-turbo": 30000, "gpt-4": 20000},
        }

        with patch.object(client.client, "request", return_value=mock_response):
            response = await client.get_usage()

            assert isinstance(response, UsageStats)
            assert response.total_requests == 1000
            assert response.total_cost == 10.50

    @pytest.mark.asyncio
    async def test_get_models_success(self, client, mock_response):
        """Test successful model retrieval."""
        mock_response.json.return_value = {
            "models": [
                {
                    "id": "gpt-3.5-turbo",
                    "name": "GPT-3.5 Turbo",
                    "provider": "openai",
                    "type": "text",
                    "capabilities": ["generation", "completion"],
                    "cost_per_token": 0.000002,
                    "max_tokens": 4096,
                    "available": True,
                }
            ]
        }

        with patch.object(client.client, "request", return_value=mock_response):
            response = await client.get_models()

            assert len(response) == 1
            assert isinstance(response[0], ModelInfo)
            assert response[0].id == "gpt-3.5-turbo"
            assert response[0].provider == "openai"

    @pytest.mark.asyncio
    async def test_route_model_success(self, client, mock_response):
        """Test successful model routing."""
        mock_response.json.return_value = {
            "model": "gpt-3.5-turbo",
            "provider": "openai",
            "reason": "Best cost-performance ratio",
            "estimated_cost": 0.01,
            "confidence": 0.9,
        }

        with patch.object(client.client, "request", return_value=mock_response):
            request = RouteRequest(prompt="Test prompt", type="generation")
            response = await client.route_model(request)

            assert isinstance(response, RouteResponse)
            assert response.model == "gpt-3.5-turbo"
            assert response.provider == "openai"

    @pytest.mark.asyncio
    async def test_health_check_success(self, client, mock_response):
        """Test successful health check."""
        mock_response.json.return_value = {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "uptime": 3600.0,
            "version": "0.2.0",
            "services": {"api": "healthy", "db": "healthy"},
        }

        with patch.object(client.client, "request", return_value=mock_response):
            response = await client.health_check()

            assert isinstance(response, HealthResponse)
            assert response.status == "healthy"
            assert response.version == "0.2.0"

    @pytest.mark.asyncio
    async def test_get_status_success(self, client, mock_response):
        """Test successful status retrieval."""
        mock_response.json.return_value = {
            "status": "operational",
            "version": "0.2.0",
            "timestamp": "2024-01-01T00:00:00Z",
            "features": ["generation", "enrichment", "search"],
            "limits": {"requests_per_minute": 100},
        }

        with patch.object(client.client, "request", return_value=mock_response):
            response = await client.get_status()

            assert isinstance(response, StatusResponse)
            assert response.status == "operational"
            assert "generation" in response.features

    @pytest.mark.asyncio
    async def test_ping_success(self, client):
        """Test successful ping."""
        with patch.object(client, "health_check", return_value=MagicMock()):
            result = await client.ping()
            assert result is True

    @pytest.mark.asyncio
    async def test_ping_failure(self, client):
        """Test failed ping."""
        with patch.object(
            client, "health_check", side_effect=Exception("Connection failed")
        ):
            result = await client.ping()
            assert result is False


class TestClientFactories:
    """Test cases for client factory functions."""

    def test_create_client(self):
        """Test create_client function."""
        config = ClientConfig(api_key="test_key")
        client = create_client(config)
        assert isinstance(client, WhizuraiClient)
        assert client.config == config

    @patch.dict("os.environ", {"CHEDDARWHIZZY_API_KEY": "test_key"})
    def test_create_client_from_env(self):
        """Test create_client_from_env function."""
        client = create_client_from_env()
        assert isinstance(client, WhizuraiClient)
        assert client.api_key == "test_key"

    @patch.dict("os.environ", {}, clear=True)
    def test_create_client_from_env_missing_key(self):
        """Test create_client_from_env with missing API key."""
        with pytest.raises(
            ValueError, match="CHEDDARWHIZZY_API_KEY environment variable is required"
        ):
            create_client_from_env()

    @patch.dict(
        "os.environ",
        {
            "CHEDDARWHIZZY_API_KEY": "test_key",
            "CHEDDARWHIZZY_BASE_URL": "https://api.example.com",
        },
    )
    def test_create_client_from_env_with_custom_url(self):
        """Test create_client_from_env with custom base URL."""
        client = create_client_from_env()
        assert isinstance(client, WhizuraiClient)
        assert client.api_key == "test_key"
        assert client.base_url == "https://api.example.com"
