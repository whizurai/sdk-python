"""
Tests for the Whizurai type definitions.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from whizurai import (CheckoutRequest, CheckoutResponse, ClientConfig,
                           ContentType, EnrichRequest, EnrichResponse,
                           FileInfo, GenerateRequest, GenerateResponse,
                           HealthResponse, JobInfo, JobStatus, ModelInfo,
                           ModerateRequest, ModerateResponse, Recommendation,
                           RecommendRequest, RecommendResponse, RouteRequest,
                           RouteResponse, SearchRequest, SearchResponse,
                           SearchResult, SentimentType, StatusResponse,
                           UploadRequest, UploadResponse, UsageStats)


class TestClientConfig:
    """Test cases for ClientConfig."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = ClientConfig(api_key="test_key")
        assert config.api_key == "test_key"
        assert config.base_url == "http://localhost:3000"
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = ClientConfig(
            api_key="test_key",
            base_url="https://api.example.com",
            timeout=60.0,
            max_retries=5,
            retry_delay=2.0,
        )
        assert config.api_key == "test_key"
        assert config.base_url == "https://api.example.com"
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.retry_delay == 2.0

    def test_invalid_timeout(self):
        """Test invalid timeout."""
        with pytest.raises(ValidationError):
            ClientConfig(api_key="test_key", timeout=-1)

    def test_invalid_max_retries(self):
        """Test invalid max retries."""
        with pytest.raises(ValidationError):
            ClientConfig(api_key="test_key", max_retries=-1)


class TestGenerateRequest:
    """Test cases for GenerateRequest."""

    def test_valid_request(self):
        """Test valid generation request."""
        request = GenerateRequest(prompt="Test prompt")
        assert request.prompt == "Test prompt"
        assert request.model is None
        assert request.max_tokens == 1000
        assert request.temperature == 0.7
        assert request.stream is False

    def test_custom_request(self):
        """Test custom generation request."""
        request = GenerateRequest(
            prompt="Test prompt",
            model="gpt-4",
            max_tokens=2000,
            temperature=0.5,
            top_p=0.9,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            stop=["END"],
            stream=True,
        )
        assert request.prompt == "Test prompt"
        assert request.model == "gpt-4"
        assert request.max_tokens == 2000
        assert request.temperature == 0.5
        assert request.top_p == 0.9
        assert request.frequency_penalty == 0.1
        assert request.presence_penalty == 0.1
        assert request.stop == ["END"]
        assert request.stream is True

    def test_invalid_temperature(self):
        """Test invalid temperature."""
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="Test", temperature=3.0)

        with pytest.raises(ValidationError):
            GenerateRequest(prompt="Test", temperature=-1.0)

    def test_invalid_max_tokens(self):
        """Test invalid max tokens."""
        with pytest.raises(ValidationError):
            GenerateRequest(prompt="Test", max_tokens=0)


class TestGenerateResponse:
    """Test cases for GenerateResponse."""

    def test_valid_response(self):
        """Test valid generation response."""
        response = GenerateResponse(
            content="Generated content",
            model="gpt-3.5-turbo",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )
        assert response.content == "Generated content"
        assert response.model == "gpt-3.5-turbo"
        assert response.usage["total_tokens"] == 30


class TestEnrichRequest:
    """Test cases for EnrichRequest."""

    def test_valid_request(self):
        """Test valid enrichment request."""
        request = EnrichRequest(content="Test content", type=ContentType.TEXT)
        assert request.content == "Test content"
        assert request.type == ContentType.TEXT
        assert request.include_summary is True
        assert request.include_tags is True
        assert request.include_sentiment is True
        assert request.include_entities is False

    def test_custom_request(self):
        """Test custom enrichment request."""
        request = EnrichRequest(
            content="Test content",
            type=ContentType.IMAGE,
            options={"quality": "high"},
            include_summary=False,
            include_tags=True,
            include_sentiment=False,
            include_entities=True,
        )
        assert request.content == "Test content"
        assert request.type == ContentType.IMAGE
        assert request.options == {"quality": "high"}
        assert request.include_summary is False
        assert request.include_tags is True
        assert request.include_sentiment is False
        assert request.include_entities is True


class TestEnrichResponse:
    """Test cases for EnrichResponse."""

    def test_valid_response(self):
        """Test valid enrichment response."""
        response = EnrichResponse(
            tags=["technology", "ai"],
            summary="Test summary",
            sentiment=SentimentType.POSITIVE,
            confidence=0.95,
            quality_score=0.8,
        )
        assert response.tags == ["technology", "ai"]
        assert response.summary == "Test summary"
        assert response.sentiment == SentimentType.POSITIVE
        assert response.confidence == 0.95
        assert response.quality_score == 0.8


class TestSearchRequest:
    """Test cases for SearchRequest."""

    def test_valid_request(self):
        """Test valid search request."""
        request = SearchRequest(query="test query")
        assert request.query == "test query"
        assert request.limit == 10
        assert request.offset == 0
        assert request.include_metadata is True

    def test_custom_request(self):
        """Test custom search request."""
        request = SearchRequest(
            query="test query",
            limit=20,
            offset=10,
            filters={"type": "document"},
            include_metadata=False,
            min_score=0.8,
        )
        assert request.query == "test query"
        assert request.limit == 20
        assert request.offset == 10
        assert request.filters == {"type": "document"}
        assert request.include_metadata is False
        assert request.min_score == 0.8

    def test_invalid_limit(self):
        """Test invalid limit."""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=0)

    def test_invalid_offset(self):
        """Test invalid offset."""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", offset=-1)


class TestSearchResponse:
    """Test cases for SearchResponse."""

    def test_valid_response(self):
        """Test valid search response."""
        result = SearchResult(
            id="1", content="Test content", score=0.95, metadata={"type": "document"}
        )
        response = SearchResponse(results=[result], total=1, query="test query")
        assert len(response.results) == 1
        assert response.results[0].id == "1"
        assert response.total == 1
        assert response.query == "test query"


class TestRecommendRequest:
    """Test cases for RecommendRequest."""

    def test_valid_request(self):
        """Test valid recommendation request."""
        request = RecommendRequest(user_id="user123")
        assert request.user_id == "user123"
        assert request.item_id is None
        assert request.limit == 10
        assert request.include_reasons is True

    def test_custom_request(self):
        """Test custom recommendation request."""
        request = RecommendRequest(
            user_id="user123",
            item_id="item456",
            limit=20,
            include_reasons=False,
            filters={"category": "books"},
            algorithm="collaborative",
        )
        assert request.user_id == "user123"
        assert request.item_id == "item456"
        assert request.limit == 20
        assert request.include_reasons is False
        assert request.filters == {"category": "books"}
        assert request.algorithm == "collaborative"

    def test_invalid_limit(self):
        """Test invalid limit."""
        with pytest.raises(ValidationError):
            RecommendRequest(user_id="user123", limit=0)


class TestRecommendResponse:
    """Test cases for RecommendResponse."""

    def test_valid_response(self):
        """Test valid recommendation response."""
        recommendation = Recommendation(
            id="item1", score=0.9, reason="Similar to your interests"
        )
        response = RecommendResponse(
            recommendations=[recommendation], user_id="user123"
        )
        assert len(response.recommendations) == 1
        assert response.recommendations[0].id == "item1"
        assert response.user_id == "user123"


class TestModerateRequest:
    """Test cases for ModerateRequest."""

    def test_valid_request(self):
        """Test valid moderation request."""
        request = ModerateRequest(content="Test content", type=ContentType.TEXT)
        assert request.content == "Test content"
        assert request.type == ContentType.TEXT
        assert request.include_explanation is True
        assert request.include_categories is True
        assert request.strict_mode is False

    def test_custom_request(self):
        """Test custom moderation request."""
        request = ModerateRequest(
            content="Test content",
            type=ContentType.IMAGE,
            include_explanation=False,
            include_categories=False,
            strict_mode=True,
        )
        assert request.content == "Test content"
        assert request.type == ContentType.IMAGE
        assert request.include_explanation is False
        assert request.include_categories is False
        assert request.strict_mode is True


class TestModerateResponse:
    """Test cases for ModerateResponse."""

    def test_valid_response(self):
        """Test valid moderation response."""
        response = ModerateResponse(
            safe=True, confidence=0.95, categories=[], explanation="Content is safe"
        )
        assert response.safe is True
        assert response.confidence == 0.95
        assert response.categories == []
        assert response.explanation == "Content is safe"


class TestUploadRequest:
    """Test cases for UploadRequest."""

    def test_valid_request(self):
        """Test valid upload request."""
        request = UploadRequest(file_path="/path/to/file.jpg")
        assert request.file_path == "/path/to/file.jpg"
        assert request.options is None
        assert request.generate_variants is False
        assert request.compress is True

    def test_custom_request(self):
        """Test custom upload request."""
        request = UploadRequest(
            file_path="/path/to/file.jpg",
            options={"quality": "high"},
            generate_variants=True,
            compress=False,
            metadata={"name": "test.jpg"},
        )
        assert request.file_path == "/path/to/file.jpg"
        assert request.options == {"quality": "high"}
        assert request.generate_variants is True
        assert request.compress is False
        assert request.metadata == {"name": "test.jpg"}


class TestUploadResponse:
    """Test cases for UploadResponse."""

    def test_valid_response(self):
        """Test valid upload response."""
        response = UploadResponse(
            id="file123",
            url="https://example.com/file123",
            size=1024,
            type="image/jpeg",
        )
        assert response.id == "file123"
        assert response.url == "https://example.com/file123"
        assert response.size == 1024
        assert response.type == "image/jpeg"


class TestFileInfo:
    """Test cases for FileInfo."""

    def test_valid_file_info(self):
        """Test valid file info."""
        file_info = FileInfo(
            id="file123",
            url="https://example.com/file123",
            size=1024,
            type="image/jpeg",
            metadata={"name": "test.jpg"},
        )
        assert file_info.id == "file123"
        assert file_info.url == "https://example.com/file123"
        assert file_info.size == 1024
        assert file_info.type == "image/jpeg"
        assert file_info.metadata == {"name": "test.jpg"}


class TestJobInfo:
    """Test cases for JobInfo."""

    def test_valid_job_info(self):
        """Test valid job info."""
        job_info = JobInfo(
            id="job123",
            status=JobStatus.COMPLETED,
            type="generation",
            progress=100.0,
            result={"content": "Generated content"},
        )
        assert job_info.id == "job123"
        assert job_info.status == JobStatus.COMPLETED
        assert job_info.type == "generation"
        assert job_info.progress == 100.0
        assert job_info.result == {"content": "Generated content"}


class TestCheckoutRequest:
    """Test cases for CheckoutRequest."""

    def test_valid_request(self):
        """Test valid checkout request."""
        request = CheckoutRequest(items=[{"id": "item1", "price": 2000}])
        assert request.items == [{"id": "item1", "price": 2000}]
        assert request.currency == "usd"
        assert request.success_url is None
        assert request.cancel_url is None

    def test_custom_request(self):
        """Test custom checkout request."""
        request = CheckoutRequest(
            items=[{"id": "item1", "price": 2000}],
            currency="eur",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            metadata={"order_id": "12345"},
        )
        assert request.items == [{"id": "item1", "price": 2000}]
        assert request.currency == "eur"
        assert request.success_url == "https://example.com/success"
        assert request.cancel_url == "https://example.com/cancel"
        assert request.metadata == {"order_id": "12345"}


class TestCheckoutResponse:
    """Test cases for CheckoutResponse."""

    def test_valid_response(self):
        """Test valid checkout response."""
        response = CheckoutResponse(
            session_id="cs_test_123",
            url="https://checkout.stripe.com/c/pay/cs_test_123",
            amount=2000,
            currency="usd",
        )
        assert response.session_id == "cs_test_123"
        assert response.url == "https://checkout.stripe.com/c/pay/cs_test_123"
        assert response.amount == 2000
        assert response.currency == "usd"


class TestUsageStats:
    """Test cases for UsageStats."""

    def test_valid_usage_stats(self):
        """Test valid usage stats."""
        stats = UsageStats(
            total_requests=1000,
            total_tokens=50000,
            total_cost=10.50,
            requests_by_endpoint={"generate": 500, "enrich": 300},
            tokens_by_model={"gpt-3.5-turbo": 30000, "gpt-4": 20000},
        )
        assert stats.total_requests == 1000
        assert stats.total_tokens == 50000
        assert stats.total_cost == 10.50
        assert stats.requests_by_endpoint == {"generate": 500, "enrich": 300}
        assert stats.tokens_by_model == {"gpt-3.5-turbo": 30000, "gpt-4": 20000}


class TestModelInfo:
    """Test cases for ModelInfo."""

    def test_valid_model_info(self):
        """Test valid model info."""
        model = ModelInfo(
            id="gpt-3.5-turbo",
            name="GPT-3.5 Turbo",
            provider="openai",
            type="text",
            capabilities=["generation", "completion"],
            cost_per_token=0.000002,
            max_tokens=4096,
            available=True,
        )
        assert model.id == "gpt-3.5-turbo"
        assert model.name == "GPT-3.5 Turbo"
        assert model.provider == "openai"
        assert model.type == "text"
        assert model.capabilities == ["generation", "completion"]
        assert model.cost_per_token == 0.000002
        assert model.max_tokens == 4096
        assert model.available is True


class TestRouteRequest:
    """Test cases for RouteRequest."""

    def test_valid_request(self):
        """Test valid route request."""
        request = RouteRequest(prompt="Test prompt", type="generation")
        assert request.prompt == "Test prompt"
        assert request.type == "generation"
        assert request.preferences is None
        assert request.cost_limit is None
        assert request.quality_requirement is None

    def test_custom_request(self):
        """Test custom route request."""
        request = RouteRequest(
            prompt="Test prompt",
            type="generation",
            preferences={"provider": "openai"},
            cost_limit=0.01,
            quality_requirement="high",
        )
        assert request.prompt == "Test prompt"
        assert request.type == "generation"
        assert request.preferences == {"provider": "openai"}
        assert request.cost_limit == 0.01
        assert request.quality_requirement == "high"


class TestRouteResponse:
    """Test cases for RouteResponse."""

    def test_valid_response(self):
        """Test valid route response."""
        response = RouteResponse(
            model="gpt-3.5-turbo",
            provider="openai",
            reason="Best cost-performance ratio",
            estimated_cost=0.01,
            confidence=0.9,
        )
        assert response.model == "gpt-3.5-turbo"
        assert response.provider == "openai"
        assert response.reason == "Best cost-performance ratio"
        assert response.estimated_cost == 0.01
        assert response.confidence == 0.9


class TestHealthResponse:
    """Test cases for HealthResponse."""

    def test_valid_response(self):
        """Test valid health response."""
        response = HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            uptime=3600.0,
            version="0.2.0",
            services={"api": "healthy", "db": "healthy"},
        )
        assert response.status == "healthy"
        assert response.uptime == 3600.0
        assert response.version == "0.2.0"
        assert response.services == {"api": "healthy", "db": "healthy"}


class TestStatusResponse:
    """Test cases for StatusResponse."""

    def test_valid_response(self):
        """Test valid status response."""
        response = StatusResponse(
            status="operational",
            version="0.2.0",
            timestamp=datetime.now(),
            features=["generation", "enrichment", "search"],
            limits={"requests_per_minute": 100},
        )
        assert response.status == "operational"
        assert response.version == "0.2.0"
        assert "generation" in response.features
        assert response.limits == {"requests_per_minute": 100}


class TestEnums:
    """Test cases for enums."""

    def test_content_type_enum(self):
        """Test ContentType enum."""
        assert ContentType.TEXT == "text"
        assert ContentType.IMAGE == "image"

    def test_sentiment_type_enum(self):
        """Test SentimentType enum."""
        assert SentimentType.POSITIVE == "positive"
        assert SentimentType.NEGATIVE == "negative"
        assert SentimentType.NEUTRAL == "neutral"

    def test_job_status_enum(self):
        """Test JobStatus enum."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"
