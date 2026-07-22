import asyncio
import json
import subprocess

import httpx
import pytest

from app.services.ai_backend import (
    AIBackendError,
    AIRequest,
    AIResult,
    OpenAIAPIBackend,
    OpenClawCodexBackend,
    create_ai_backend,
)


def test_openclaw_adapter_preserves_cli_and_returns_neutral_result() -> None:
    captured: list[str] = []

    def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        captured.extend(args)
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps(
                {
                    "result": {"payloads": [{"text": '{"answer":"ready"}'}]},
                    "meta": {
                        "model": "openai/gpt-5.6-terra",
                        "usage": {"input": 20, "output": 5, "total": 25},
                    },
                }
            ),
            stderr="",
        )

    result = OpenClawCodexBackend(
        command="/custom/openclaw",
        sync_runner=fake_run,
    ).generate(
        AIRequest(
            prompt="Return JSON",
            model="openai/gpt-5.6-terra",
            agent_id="tasko-assistant",
            thinking="low",
            timeout_seconds=30,
            session_id="agent:tasko-assistant:test-session",
            structured=True,
        )
    )

    assert captured[:5] == [
        "/custom/openclaw",
        "agent",
        "--local",
        "--agent",
        "tasko-assistant",
    ]
    assert captured[captured.index("--session-key") + 1] == (
        "agent:tasko-assistant:test-session"
    )
    assert captured[captured.index("--message") + 1] == "Return JSON"
    assert captured[-1] == "--json"
    assert result.text == '{"answer":"ready"}'
    assert result.structured_data == {"answer": "ready"}
    assert result.model == "openai/gpt-5.6-terra"
    assert result.backend == "openclaw_codex"
    assert result.usage.input_tokens == 20
    assert result.usage.output_tokens == 5
    assert result.usage.total_tokens == 25
    assert result.latency_ms >= 0
    assert result.session_id == "agent:tasko-assistant:test-session"


def test_openai_api_adapter_uses_responses_api_and_returns_same_contract() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "resp_tasko_123",
                "model": "gpt-5.6-terra",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": '{"answer":"ready"}'}
                        ],
                    }
                ],
                "usage": {"input_tokens": 18, "output_tokens": 4, "total_tokens": 22},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = OpenAIAPIBackend(
        api_key="test-key",
        base_url="https://api.openai.test/v1/",
        client=client,
    ).generate(
        AIRequest(
            prompt="Return JSON",
            model="openai/gpt-5.6-terra",
            thinking="low",
            structured=True,
        )
    )

    assert captured == {
        "url": "https://api.openai.test/v1/responses",
        "authorization": "Bearer test-key",
        "payload": {
            "model": "gpt-5.6-terra",
            "input": "Return JSON",
            "reasoning": {"effort": "low"},
            "text": {"format": {"type": "json_object"}},
        },
    }
    assert result.text == '{"answer":"ready"}'
    assert result.structured_data == {"answer": "ready"}
    assert result.model == "gpt-5.6-terra"
    assert result.backend == "openai_api"
    assert result.usage.total_tokens == 22
    assert result.session_id == "resp_tasko_123"


def test_openai_api_adapter_supports_async_chat_calls() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "resp_async_123",
                "model": "gpt-5.6-terra",
                "output": [
                    {
                        "id": "msg_nested_id",
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Async response"}],
                    }
                ],
                "usage": {"input_tokens": 7, "output_tokens": 2, "total_tokens": 9},
            },
        )

    async def invoke() -> AIResult:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            backend = OpenAIAPIBackend(api_key="test-key", async_client=client)
            return await backend.agenerate(
                AIRequest(prompt="Answer", model="gpt-5.6-terra")
            )

    result = asyncio.run(invoke())

    assert result.text == "Async response"
    assert result.session_id == "resp_async_123"
    assert result.usage.total_tokens == 9


def test_backend_factory_supports_both_modes_and_requires_direct_api_credentials() -> None:
    assert create_ai_backend(mode="openclaw_codex").name == "openclaw_codex"
    assert create_ai_backend(mode="openai_api", openai_api_key="key").name == "openai_api"

    backend = create_ai_backend(mode="openai_api")
    with pytest.raises(AIBackendError, match="OPENAI_API_KEY"):
        backend.generate(AIRequest(prompt="test", model="gpt-5.6-terra"))
