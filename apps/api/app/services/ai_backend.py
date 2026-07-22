from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx


AIBackendMode = Literal["openclaw_codex", "openai_api"]
PromptTransport = Literal["argument", "file"]


class AIBackendError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "backend_error",
        retryable: bool = False,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.status_code = status_code


@dataclass(frozen=True)
class AIUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    source: str = "unavailable"

    def as_dict(self) -> dict[str, int | str]:
        return {
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "totalTokens": self.total_tokens or self.input_tokens + self.output_tokens,
            "tokenCountSource": self.source,
        }


@dataclass(frozen=True)
class AIRequest:
    prompt: str
    model: str = ""
    agent_id: str = ""
    thinking: str = "off"
    timeout_seconds: int = 120
    session_id: str = ""
    structured: bool = False


@dataclass(frozen=True)
class AIResult:
    text: str
    structured_data: Any | None
    model: str
    backend: AIBackendMode
    usage: AIUsage
    latency_ms: int
    session_id: str
    raw_response: str = field(default="", repr=False)


class AIBackend(Protocol):
    name: AIBackendMode

    def generate(self, request: AIRequest) -> AIResult: ...

    async def agenerate(self, request: AIRequest) -> AIResult: ...


SyncRunner = Callable[..., subprocess.CompletedProcess[str]]
AsyncProcessFactory = Callable[..., Any]


class OpenClawCodexBackend:
    name: AIBackendMode = "openclaw_codex"

    def __init__(
        self,
        *,
        command: str = "openclaw",
        sync_runner: SyncRunner = subprocess.run,
        async_process_factory: AsyncProcessFactory = asyncio.create_subprocess_exec,
        prompt_transport: PromptTransport = "argument",
        include_cli_timeout: bool = False,
        model_after_timeout: bool = False,
    ) -> None:
        self.command = command
        self.executable = shutil.which(command) or command
        self.sync_runner = sync_runner
        self.async_process_factory = async_process_factory
        self.prompt_transport = prompt_transport
        self.include_cli_timeout = include_cli_timeout
        self.model_after_timeout = model_after_timeout

    def generate(self, request: AIRequest) -> AIResult:
        started_at = time.perf_counter()
        try:
            if self.prompt_transport == "file":
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", suffix=".txt"
                ) as prompt_file:
                    prompt_file.write(request.prompt)
                    prompt_file.flush()
                    result = self.sync_runner(
                        self._arguments(request, prompt_file=Path(prompt_file.name)),
                        capture_output=True,
                        check=True,
                        text=True,
                        timeout=request.timeout_seconds,
                    )
            else:
                result = self.sync_runner(
                    self._arguments(request),
                    capture_output=True,
                    check=True,
                    text=True,
                    timeout=request.timeout_seconds,
                )
        except FileNotFoundError as exc:
            raise AIBackendError(
                f"AI backend command was not found: {self.command}",
                code="runtime_missing",
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise AIBackendError(
                "AI backend request timed out",
                code="timeout",
                retryable=True,
            ) from exc
        except subprocess.CalledProcessError as exc:
            raw_error = (exc.stderr or exc.stdout or "OpenClaw command failed").strip()
            raise AIBackendError(
                raw_error,
                code="execution_failed",
                retryable=True,
            ) from exc
        except OSError as exc:
            raise AIBackendError(
                f"AI backend command could not start: {exc}",
                code="runtime_unavailable",
            ) from exc

        return build_ai_result(
            raw_response=result.stdout,
            fallback_model=request.model,
            backend=self.name,
            session_id=request.session_id,
            latency_ms=round((time.perf_counter() - started_at) * 1000),
        )

    async def agenerate(self, request: AIRequest) -> AIResult:
        started_at = time.perf_counter()
        try:
            process = await self.async_process_factory(
                *self._arguments(request),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise AIBackendError(
                f"AI backend command was not found: {self.command}",
                code="runtime_missing",
            ) from exc

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=request.timeout_seconds + 5,
            )
        except asyncio.CancelledError:
            process.kill()
            await process.wait()
            raise
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise AIBackendError(
                "AI backend request timed out",
                code="timeout",
                retryable=True,
            ) from exc

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        if process.returncode != 0:
            raise AIBackendError(
                (stderr or stdout or "OpenClaw command failed").strip(),
                code="execution_failed",
                retryable=True,
            )
        return build_ai_result(
            raw_response=stdout,
            fallback_model=request.model,
            backend=self.name,
            session_id=request.session_id,
            latency_ms=round((time.perf_counter() - started_at) * 1000),
        )

    def _arguments(self, request: AIRequest, *, prompt_file: Path | None = None) -> list[str]:
        arguments = [self.executable, "agent", "--local"]
        if request.agent_id:
            arguments.extend(["--agent", request.agent_id])
        if request.session_id:
            arguments.extend(["--session-key", request.session_id])
        if prompt_file is not None:
            arguments.extend(["--message-file", str(prompt_file)])
        else:
            arguments.extend(["--message", request.prompt])
        if request.model and not self.model_after_timeout:
            arguments.extend(["--model", request.model])
        if request.thinking:
            arguments.extend(["--thinking", request.thinking])
        if self.include_cli_timeout:
            arguments.extend(["--timeout", str(request.timeout_seconds)])
        if request.model and self.model_after_timeout:
            arguments.extend(["--model", request.model])
        arguments.append("--json")
        return arguments


class OpenAIAPIBackend:
    name: AIBackendMode = "openai_api"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        default_model: str = "",
        client: httpx.Client | None = None,
        async_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.client = client
        self.async_client = async_client

    def generate(self, request: AIRequest) -> AIResult:
        started_at = time.perf_counter()
        client = self.client or httpx.Client(timeout=request.timeout_seconds)
        should_close = self.client is None
        try:
            response = client.post(
                f"{self.base_url}/responses",
                headers=self._headers(),
                json=self._payload(request),
            )
            return self._result(response, request, started_at)
        except httpx.TimeoutException as exc:
            raise AIBackendError("AI backend request timed out", code="timeout", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise AIBackendError(
                "AI backend could not reach the provider",
                code="provider_unreachable",
                retryable=True,
            ) from exc
        finally:
            if should_close:
                client.close()

    async def agenerate(self, request: AIRequest) -> AIResult:
        started_at = time.perf_counter()
        client = self.async_client or httpx.AsyncClient(timeout=request.timeout_seconds)
        should_close = self.async_client is None
        try:
            response = await client.post(
                f"{self.base_url}/responses",
                headers=self._headers(),
                json=self._payload(request),
            )
            return self._result(response, request, started_at)
        except httpx.TimeoutException as exc:
            raise AIBackendError("AI backend request timed out", code="timeout", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise AIBackendError(
                "AI backend could not reach the provider",
                code="provider_unreachable",
                retryable=True,
            ) from exc
        finally:
            if should_close:
                await client.aclose()

    def _headers(self) -> dict[str, str]:
        if not self.api_key.strip():
            raise AIBackendError(
                "OPENAI_API_KEY is required for openai_api mode",
                code="authentication",
            )
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _payload(self, request: AIRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": normalize_openai_model(request.model or self.default_model),
            "input": request.prompt,
        }
        if request.thinking and request.thinking != "off":
            payload["reasoning"] = {"effort": request.thinking}
        if request.structured:
            payload["text"] = {"format": {"type": "json_object"}}
        return payload

    def _result(
        self,
        response: httpx.Response,
        request: AIRequest,
        started_at: float,
    ) -> AIResult:
        if response.is_error:
            raise openai_response_error(response)
        raw_response = response.text
        return build_ai_result(
            raw_response=raw_response,
            fallback_model=normalize_openai_model(request.model or self.default_model),
            backend=self.name,
            session_id="",
            latency_ms=round((time.perf_counter() - started_at) * 1000),
        )


def build_ai_result(
    *,
    raw_response: str,
    fallback_model: str,
    backend: AIBackendMode,
    session_id: str,
    latency_ms: int,
) -> AIResult:
    payloads = extract_json_values(raw_response)
    text = extract_ai_text(payloads)
    structured_data = extract_structured_data(text, payloads)
    model = find_string_field(payloads, {"model", "modelid"}) or fallback_model
    usage = extract_ai_usage(payloads)
    response_id = extract_response_id(payloads) if backend == "openai_api" else ""
    return AIResult(
        text=text,
        structured_data=structured_data,
        model=model or "configured-agent-model",
        backend=backend,
        usage=usage,
        latency_ms=latency_ms,
        session_id=session_id or response_id,
        raw_response=raw_response,
    )


def extract_json_values(value: str) -> list[Any]:
    decoder = json.JSONDecoder()
    values: list[Any] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character not in "[{":
            index += 1
            continue
        try:
            payload, end = decoder.raw_decode(value[index:])
        except json.JSONDecodeError:
            index += 1
            continue
        values.append(payload)
        index += max(1, end)
    return values


def extract_ai_text(payloads: list[Any]) -> str:
    texts: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = key.replace("_", "").lower()
                if normalized in {
                    "outputtext",
                    "finalassistantvisibletext",
                    "finalassistantrawtext",
                } and isinstance(item, str):
                    texts.append(item)
                elif key == "text" and isinstance(item, str):
                    texts.append(item)
                else:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for payload in payloads:
        visit(payload)
    return next((text.strip() for text in reversed(texts) if text.strip()), "")


def extract_structured_data(text: str, payloads: list[Any]) -> Any | None:
    candidates = [text.strip()]
    if text.strip().startswith("```"):
        candidates.append(re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip()))
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except (TypeError, json.JSONDecodeError):
            pass
    for payload in reversed(payloads):
        if isinstance(payload, dict) and not any(
            key in payload for key in ("status", "result", "response", "output", "payloads")
        ):
            return payload
    return None


def extract_ai_usage(payloads: list[Any]) -> AIUsage:
    usage_values: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key.replace("_", "").lower() in {"usage", "tokenusage", "tokens"} and isinstance(item, dict):
                    usage_values.append(item)
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for payload in payloads:
        visit(payload)
    best = AIUsage()
    for usage in usage_values:
        input_tokens = usage_int(usage, "input_tokens", "inputTokens", "prompt_tokens", "promptTokens", "input")
        output_tokens = usage_int(usage, "output_tokens", "outputTokens", "completion_tokens", "completionTokens", "output")
        total_tokens = usage_int(usage, "total_tokens", "totalTokens", "total") or input_tokens + output_tokens
        if total_tokens >= best.total_tokens:
            best = AIUsage(input_tokens, output_tokens, total_tokens, source="provider")
    return best


def usage_int(value: dict[str, Any], *keys: str) -> int:
    for key in keys:
        item = value.get(key)
        if isinstance(item, (int, float)) and not isinstance(item, bool) and item >= 0:
            return int(item)
    return 0


def find_string_field(payloads: list[Any], names: set[str]) -> str:
    result = ""

    def visit(value: Any) -> None:
        nonlocal result
        if isinstance(value, dict):
            for key, item in value.items():
                if key.replace("_", "").lower() in names and isinstance(item, str) and item:
                    result = item
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for payload in payloads:
        visit(payload)
    return result


def extract_response_id(payloads: list[Any]) -> str:
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        response_id = payload.get("id")
        if isinstance(response_id, str) and response_id:
            return response_id
    return ""


def normalize_openai_model(model: str) -> str:
    return model.removeprefix("openai/")


def openai_response_error(response: httpx.Response) -> AIBackendError:
    status_code = response.status_code
    try:
        payload = response.json()
        detail = payload.get("error", {}).get("message", "") if isinstance(payload, dict) else ""
    except (TypeError, ValueError):
        detail = ""
    if status_code in {401, 403}:
        return AIBackendError(detail or "AI backend authentication failed", code="authentication", status_code=status_code)
    if status_code == 429:
        return AIBackendError(detail or "AI backend is rate-limited", code="rate_limited", retryable=True, status_code=status_code)
    if status_code >= 500:
        return AIBackendError(detail or "AI provider failed", code="provider_error", retryable=True, status_code=status_code)
    return AIBackendError(detail or "AI request was rejected", code="invalid_request", status_code=status_code)


def create_ai_backend(
    *,
    mode: AIBackendMode,
    openclaw_command: str = "openclaw",
    openai_api_key: str = "",
    openai_api_base_url: str = "https://api.openai.com/v1",
    openai_api_model: str = "",
    sync_runner: SyncRunner = subprocess.run,
    async_process_factory: AsyncProcessFactory = asyncio.create_subprocess_exec,
    openclaw_prompt_transport: PromptTransport = "argument",
    openclaw_include_cli_timeout: bool = False,
    openclaw_model_after_timeout: bool = False,
) -> AIBackend:
    if mode == "openclaw_codex":
        return OpenClawCodexBackend(
            command=openclaw_command,
            sync_runner=sync_runner,
            async_process_factory=async_process_factory,
            prompt_transport=openclaw_prompt_transport,
            include_cli_timeout=openclaw_include_cli_timeout,
            model_after_timeout=openclaw_model_after_timeout,
        )
    if mode == "openai_api":
        return OpenAIAPIBackend(
            api_key=openai_api_key,
            base_url=openai_api_base_url,
            default_model=openai_api_model,
        )
    raise AIBackendError(f"Unsupported AI backend mode: {mode}", code="unsupported_backend")


def create_configured_ai_backend(
    settings: Any,
    *,
    sync_runner: SyncRunner = subprocess.run,
    async_process_factory: AsyncProcessFactory = asyncio.create_subprocess_exec,
    openclaw_prompt_transport: PromptTransport = "argument",
    openclaw_include_cli_timeout: bool = False,
    openclaw_model_after_timeout: bool = False,
) -> AIBackend:
    return create_ai_backend(
        mode=settings.ai_backend_mode,
        openclaw_command=settings.openclaw_command,
        openai_api_key=settings.openai_api_key,
        openai_api_base_url=settings.openai_api_base_url,
        openai_api_model=settings.openai_api_model,
        sync_runner=sync_runner,
        async_process_factory=async_process_factory,
        openclaw_prompt_transport=openclaw_prompt_transport,
        openclaw_include_cli_timeout=openclaw_include_cli_timeout,
        openclaw_model_after_timeout=openclaw_model_after_timeout,
    )
