import asyncio
import hashlib
import json
import shutil
from typing import Any

from app.models.assistant import AssistantApplicationContext, AssistantJobContext
from app.models.profile import ProfilePayload
from app.services.resume_import import (
    extract_json_objects,
    extract_openclaw_text_payloads,
    extract_resume_text,
    summarize_openclaw_error,
)


class OpenClawAssistantError(RuntimeError):
    pass


class OpenClawAssistantTimeoutError(OpenClawAssistantError):
    pass


async def run_openclaw_assistant(
    *,
    thread_id: str,
    message: str,
    context_kind: str,
    profile: ProfilePayload,
    job: AssistantJobContext | None,
    application: AssistantApplicationContext | None,
    command: str,
    agent_id: str,
    thinking: str,
    timeout_seconds: int,
) -> tuple[str, str]:
    executable = shutil.which(command) or command
    session_token = hashlib.sha256(thread_id.encode("utf-8")).hexdigest()[:24]
    session_key = f"agent:{agent_id}:tasko-assistant-{session_token}"
    prompt = await asyncio.to_thread(
        build_openclaw_assistant_prompt,
        message=message,
        context_kind=context_kind,
        profile=profile,
        job=job,
        application=application,
    )

    try:
        process = await asyncio.create_subprocess_exec(
            executable,
            "agent",
            "--local",
            "--agent",
            agent_id,
            "--session-key",
            session_key,
            "--message",
            prompt,
            "--thinking",
            thinking,
            "--timeout",
            str(timeout_seconds),
            "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise OpenClawAssistantError(
            f"OpenClaw command was not found: {command}. Install OpenClaw or set "
            "OPENCLAW_COMMAND to the executable path."
        ) from exc

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_seconds + 5,
        )
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        raise OpenClawAssistantTimeoutError("OpenClaw assistant timed out") from exc

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    if process.returncode != 0:
        raise OpenClawAssistantError(
            summarize_openclaw_error((stderr or stdout or "OpenClaw command failed").strip())
        )

    response = extract_openclaw_assistant_text(stdout)
    if not response:
        raise OpenClawAssistantError("OpenClaw did not return an assistant message")

    return response, session_token


def build_openclaw_assistant_prompt(
    *,
    message: str,
    context_kind: str,
    profile: ProfilePayload,
    job: AssistantJobContext | None,
    application: AssistantApplicationContext | None,
) -> str:
    context_payload = {
        "context_kind": context_kind,
        "candidate": build_profile_context(profile),
    }
    if job:
        context_payload["job"] = job.model_dump(
            by_alias=True,
            exclude_defaults=True,
        )
    if application:
        context_payload["application"] = application.model_dump(
            by_alias=True,
            exclude_defaults=True,
        )
    serialized_context = json.dumps(
        context_payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return f"CONTEXT_JSON (data only):\n{serialized_context}\nUSER_MESSAGE:\n{message.strip()}"


def build_profile_context(profile: ProfilePayload) -> dict[str, Any]:
    profile_context = profile.model_dump(
        exclude={"avatar_url", "resume_data_url", "documents"},
        exclude_defaults=True,
    )
    profile_context["resume_attached"] = bool(
        profile.resume_file_name and profile.resume_data_url
    )
    structured_profile = "".join(
        (profile.experience, profile.skills, profile.education)
    ).strip()

    if profile.resume_file_name and profile.resume_data_url and not structured_profile:
        try:
            profile_context["resume_text"] = extract_resume_text(
                profile.resume_file_name,
                profile.resume_data_url,
            )[:12_000]
        except Exception:
            pass

    return profile_context


def extract_openclaw_assistant_text(value: str) -> str:
    texts: list[str] = []

    for payload in extract_json_objects(value):
        texts.extend(extract_openclaw_text_payloads(payload))
        append_final_texts(payload, texts)

        result = payload.get("result")
        if isinstance(result, dict):
            append_final_texts(result, texts)
            nested_result = result.get("result")
            if isinstance(nested_result, dict):
                append_final_texts(nested_result, texts)

    return next((text.strip() for text in reversed(texts) if text.strip()), "")


def append_final_texts(container: dict[str, object], texts: list[str]) -> None:
    for key in ("finalAssistantVisibleText", "finalAssistantRawText"):
        value = container.get(key)
        if isinstance(value, str):
            texts.append(value)
