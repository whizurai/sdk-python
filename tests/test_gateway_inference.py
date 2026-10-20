"""Tests for client.generate_text() / client.describe_image() (mocked HTTP).

Both go to the gateway at base_url, never to model-router, and are sent once.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from whizurai import (
    APIError,
    ClientConfig,
    DescribeImageResponse,
    GenerateTextResponse,
    ValidationError,
    WhizuraiClient,
)


def fake_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.content = b'{"x":1}' if json_data is not None else b""
    resp.headers = {}
    resp.reason_phrase = "ERR"
    return resp


@pytest.fixture
def client():
    return WhizuraiClient(
        ClientConfig(
            api_key="k",
            base_url="http://localhost:3000",
            timeout=5.0,
            max_retries=2,
            retry_delay=0.0,
        )
    )


class TestGenerateText:
    async def test_posts_camelcase_body_to_gateway(self, client):
        client.client.request = AsyncMock(
            return_value=fake_response(
                200,
                {
                    "id": "gen_1",
                    "object": "text_completion",
                    "created": 1,
                    "model": "GLM-5.3-Flash-EXL3",
                    "provider": "ollama",
                    "choices": [{"text": "hello", "index": 0, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    "execution": {"execution": "fleet", "runtime": "vllm", "fleet_job_id": "j1"},
                },
            )
        )
        result = await client.generate_text(
            "Say hello",
            model="chat",
            max_tokens=50,
            reasoning_effort="none",
            metadata={"priority": "interactive", "timeoutMs": 30000},
            timeout=45.0,
        )
        assert isinstance(result, GenerateTextResponse)
        assert result.choices[0].text == "hello"
        assert result.model == "GLM-5.3-Flash-EXL3"
        assert result.execution == {"execution": "fleet", "runtime": "vllm", "fleet_job_id": "j1"}
        kwargs = client.client.request.call_args.kwargs
        assert kwargs["method"] == "POST"
        assert kwargs["url"] == "/v1/generate/text"
        assert kwargs["timeout"] == 45.0
        assert kwargs["json"] == {
            "prompt": "Say hello",
            "model": "chat",
            "maxTokens": 50,
            "reasoningEffort": "none",
            "metadata": {"priority": "interactive", "timeoutMs": 30000},
        }

    async def test_server_error_is_not_retried(self, client):
        client.client.request = AsyncMock(return_value=fake_response(503, {"error": {"message": "no_capacity"}}))
        with pytest.raises(APIError):
            await client.generate_text("x")
        assert client.client.request.call_count == 1

    async def test_empty_prompt_rejected_before_network(self, client):
        client.client.request = AsyncMock()
        with pytest.raises(ValidationError):
            await client.generate_text("  ")
        client.client.request.assert_not_called()


class TestDescribeImage:
    async def test_posts_bytes_and_parses_attribution(self, client):
        client.client.request = AsyncMock(
            return_value=fake_response(
                200,
                {
                    "description": '{"heroLabel":"dog"}',
                    "provider": "ollama",
                    "model": "qwen3-vl:30b-a3b-instruct",
                    "requestId": "r1",
                    "responseTime": 5.1,
                    "metadata": {"execution": "fleet"},
                },
            )
        )
        result = await client.describe_image(
            image="aGVsbG8=",
            prompt="Describe as JSON",
            model="qwen3-vl:30b-a3b-instruct",
            max_tokens=900,
            temperature=0,
            request_id="r1",
            metadata={"priority": "interactive"},
            timeout=330.0,
        )
        assert isinstance(result, DescribeImageResponse)
        assert result.model == "qwen3-vl:30b-a3b-instruct"
        assert result.request_id == "r1"
        assert result.response_time == 5.1
        kwargs = client.client.request.call_args.kwargs
        assert kwargs["url"] == "/v1/images/describe"
        assert kwargs["timeout"] == 330.0
        assert kwargs["json"] == {
            "image": "aGVsbG8=",
            "prompt": "Describe as JSON",
            "model": "qwen3-vl:30b-a3b-instruct",
            "maxTokens": 900,
            "temperature": 0,
            "requestId": "r1",
            "metadata": {"priority": "interactive"},
        }

    @pytest.mark.parametrize(
        "kwargs",
        [{}, {"image": "aGVsbG8=", "image_url": "https://example.test/a.png"}],
    )
    async def test_requires_exactly_one_source(self, client, kwargs):
        client.client.request = AsyncMock()
        with pytest.raises(ValidationError):
            await client.describe_image(**kwargs)
        client.client.request.assert_not_called()
