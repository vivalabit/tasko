import asyncio
import base64
import hashlib
import json
import re
import shutil
from typing import Any

from pydantic import ValidationError

from app.models.assistant import (
    AddApplicationNoteProposal,
    AssistantActionFieldPreview,
    AssistantActionPreview,
    AssistantApplicationContext,
    AssistantJobContext,
    CreateInterviewEventProposal,
    SaveDocumentProposal,
    UpdateApplicationNextStepProposal,
    UpdateProfileFieldProposal,
)
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


ACTION_BLOCK_PATTERN = re.compile(
    r"(?:```(?:json)?\s*)?<TASKO_ACTIONS_JSON>\s*(.*?)\s*</TASKO_ACTIONS_JSON>(?:\s*```)?",
    re.DOTALL | re.IGNORECASE,
)
ACTION_PROPOSAL_MODELS = {
    "add_application_note": AddApplicationNoteProposal,
    "update_application_next_step": UpdateApplicationNextStepProposal,
    "create_interview_event": CreateInterviewEventProposal,
    "save_document": SaveDocumentProposal,
    "update_profile_field": UpdateProfileFieldProposal,
}


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
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        raise
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

    return response, session_key


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
    profile_context["resume_attached"] = bool(profile.resume_file_name and profile.resume_data_url)
    structured_profile = "".join((profile.experience, profile.skills, profile.education)).strip()

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


def extract_assistant_action_previews(
    text: str,
    *,
    request_id: str,
    context_kind: str,
    context_id: str,
    profile: ProfilePayload,
    job: AssistantJobContext | None,
    application: AssistantApplicationContext | None,
) -> tuple[str, list[AssistantActionPreview]]:
    raw_actions: list[dict[str, Any]] = []
    for match in ACTION_BLOCK_PATTERN.finditer(text):
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(value, list):
            raw_actions.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            raw_actions.append(value)

    visible_text = ACTION_BLOCK_PATTERN.sub("", text).strip()
    previews: list[AssistantActionPreview] = []
    for index, raw_action in enumerate(raw_actions[:5]):
        preview = build_action_preview(
            raw_action,
            request_id=request_id,
            index=index,
            context_kind=context_kind,
            context_id=context_id,
            profile=profile,
            job=job,
            application=application,
        )
        if preview:
            previews.append(preview)
    return visible_text, previews


def build_action_preview(
    raw_action: dict[str, Any],
    *,
    request_id: str,
    index: int,
    context_kind: str,
    context_id: str,
    profile: ProfilePayload,
    job: AssistantJobContext | None,
    application: AssistantApplicationContext | None,
) -> AssistantActionPreview | None:
    action_type = raw_action.get("type")
    proposal_model = ACTION_PROPOSAL_MODELS.get(action_type)
    if not proposal_model:
        return None
    try:
        proposal = proposal_model.model_validate(raw_action)
    except ValidationError:
        return None

    canonical = json.dumps(raw_action, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{request_id}:{index}:{canonical}".encode()).hexdigest()[:32]
    action_id = f"assistant-action-{digest}"

    if isinstance(proposal, AddApplicationNoteProposal):
        if context_kind != "application" or not application or not application.id:
            return None
        payload = {
            "applicationId": application.id,
            "note": proposal.note.strip(),
        }
        return AssistantActionPreview(
            id=action_id,
            type=proposal.type,
            title="Add application note",
            description=f"Add a note to {application.job.title} at {application.job.company}.",
            contextKind=context_kind,
            contextId=context_id,
            fields=[AssistantActionFieldPreview(label="New note", after=proposal.note.strip())],
            payload=payload,
        )

    if isinstance(proposal, UpdateApplicationNextStepProposal):
        if context_kind != "application" or not application or not application.id:
            return None
        next_step = proposal.next_step.strip()
        payload = {
            "applicationId": application.id,
            "nextStep": next_step,
            "expectedValue": application.next_step,
        }
        return AssistantActionPreview(
            id=action_id,
            type=proposal.type,
            title="Update next step",
            description=f"Change the next step for {application.job.title} at {application.job.company}.",
            contextKind=context_kind,
            contextId=context_id,
            fields=[
                AssistantActionFieldPreview(
                    label="Next step",
                    before=application.next_step,
                    after=next_step,
                )
            ],
            payload=payload,
        )

    if isinstance(proposal, CreateInterviewEventProposal):
        if context_kind != "application" or not application or not application.id:
            return None
        if proposal.starts_at.tzinfo is None:
            return None
        starts_at = proposal.starts_at.isoformat()
        payload = {
            "applicationId": application.id,
            "title": proposal.title.strip(),
            "startsAt": starts_at,
            "durationMinutes": proposal.duration_minutes,
            "timezone": proposal.timezone.strip(),
            "location": proposal.location.strip(),
            "notes": proposal.notes.strip(),
        }
        return AssistantActionPreview(
            id=action_id,
            type=proposal.type,
            title="Create interview event",
            description=f"Schedule an interview for {application.job.title} at {application.job.company}.",
            contextKind=context_kind,
            contextId=context_id,
            fields=[
                AssistantActionFieldPreview(label="Interview", after=proposal.title.strip()),
                AssistantActionFieldPreview(label="Starts", after=starts_at),
                AssistantActionFieldPreview(
                    label="Duration",
                    after=f"{proposal.duration_minutes} minutes",
                ),
                AssistantActionFieldPreview(label="Location", after=proposal.location.strip()),
            ],
            payload=payload,
        )

    if isinstance(proposal, SaveDocumentProposal):
        application_id = application.id if context_kind == "application" and application else ""
        job_id = job.id if job else ""
        payload = {
            "documentType": proposal.document_type,
            "title": proposal.title.strip(),
            "content": proposal.content.strip(),
            "jobId": job_id,
            "applicationId": application_id,
        }
        return AssistantActionPreview(
            id=action_id,
            type=proposal.type,
            title="Save document",
            description=(
                "Create a document and attach it to the selected application."
                if application_id
                else "Create a saved document in Tasko."
            ),
            contextKind=context_kind,
            contextId=context_id,
            fields=[
                AssistantActionFieldPreview(
                    label="Type",
                    after=(
                        "Cover letter"
                        if proposal.document_type == "cover_letter"
                        else "Tailored resume"
                    ),
                ),
                AssistantActionFieldPreview(label="Title", after=proposal.title.strip()),
                AssistantActionFieldPreview(label="Content", after=proposal.content.strip()),
            ],
            payload=payload,
        )

    if isinstance(proposal, UpdateProfileFieldProposal):
        current_value = str(getattr(profile, proposal.field, ""))
        payload = {
            "field": proposal.field,
            "value": proposal.value.strip(),
            "expectedValue": current_value,
        }
        return AssistantActionPreview(
            id=action_id,
            type=proposal.type,
            title="Update profile field",
            description=f"Change only the profile field “{proposal.field.replace('_', ' ')}”.",
            contextKind=context_kind,
            contextId=context_id,
            fields=[
                AssistantActionFieldPreview(
                    label=proposal.field.replace("_", " ").title(),
                    before=current_value,
                    after=proposal.value.strip(),
                )
            ],
            payload=payload,
        )

    return None


def encode_message_actions(text: str, actions: list[AssistantActionPreview]) -> str:
    if not actions:
        return text
    payload = json.dumps(
        [action.model_dump(by_alias=True, mode="json") for action in actions],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(payload).decode()
    return f"{text.rstrip()}\n\n<!--TASKO_ACTIONS:{encoded}-->"
