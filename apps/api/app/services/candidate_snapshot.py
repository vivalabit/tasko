from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.models.profile import CandidateMatchSnapshotRecord, ProfilePayload
from app.services.ai_match import (
    MATCHER_VERSION,
    build_candidate_snapshot,
    build_candidate_snapshot_hash,
    normalize_list,
    parse_number,
)
from app.services.resume_import import (
    extract_json_object,
    extract_json_objects,
    extract_openclaw_text_payloads,
    extract_resume_text,
    summarize_openclaw_error,
)


class CandidateSnapshotError(RuntimeError):
    pass


@dataclass(frozen=True)
class CandidateMatchSnapshot:
    profile_input_hash: str
    profile_hash: str
    source: str
    data: dict[str, Any]
    openclaw_error: str | None = None


LIST_FIELDS = {
    "roles",
    "skills",
    "domains",
    "locations",
    "work_formats",
    "employment_types",
    "industries",
    "seniority",
    "languages",
    "company_sizes",
    "priorities",
    "no_preference",
    "dealbreakers",
}

SUMMARY_LIST_FIELDS = {"experience", "education"}
STRING_FIELDS = {
    "current_role",
    "desired_role",
    "headline",
    "salary_currency",
    "work_authorization",
    "preference_notes",
    "additional_notes",
}


def get_candidate_match_snapshot(
    db: Session,
    *,
    profile: ProfilePayload,
    settings: Settings | None = None,
    allow_openclaw: bool = False,
    strict_openclaw: bool = False,
) -> CandidateMatchSnapshot:
    profile_input_hash = build_profile_input_hash(profile)
    existing_record = latest_snapshot_record(db, profile_input_hash=profile_input_hash)
    if existing_record and (not strict_openclaw or existing_record.source == "openclaw"):
        return record_to_snapshot(existing_record)

    fallback_snapshot = empty_candidate_snapshot() if strict_openclaw else build_candidate_snapshot(profile)
    if allow_openclaw and settings and settings.openclaw_ai_match_enabled:
        try:
            snapshot_data = build_snapshot_with_openclaw(
                profile=profile,
                fallback_snapshot=fallback_snapshot,
                settings=settings,
            )
            source = "openclaw"
            openclaw_error = None
        except CandidateSnapshotError as exc:
            if strict_openclaw:
                raise
            snapshot_data = fallback_snapshot
            source = "local"
            openclaw_error = str(exc)[:240]
    elif strict_openclaw:
        raise CandidateSnapshotError("OpenClaw candidate snapshot is required but disabled")
    else:
        snapshot_data = fallback_snapshot
        source = "local"
        openclaw_error = None

    snapshot_data = normalize_candidate_snapshot(snapshot_data, fallback_snapshot)
    profile_hash = build_candidate_snapshot_hash(snapshot_data)
    snapshot = CandidateMatchSnapshot(
        profile_input_hash=profile_input_hash,
        profile_hash=profile_hash,
        source=source,
        data=snapshot_data,
        openclaw_error=openclaw_error,
    )

    if allow_openclaw:
        db.add(snapshot_to_record(snapshot))

    return snapshot


def empty_candidate_snapshot() -> dict[str, Any]:
    return {
        "roles": [],
        "current_role": "",
        "desired_role": "",
        "headline": "",
        "skills": [],
        "domains": [],
        "experience": [],
        "education": [],
        "locations": [],
        "work_formats": [],
        "employment_types": [],
        "industries": [],
        "seniority": [],
        "salary_min": 0,
        "salary_currency": "",
        "work_authorization": "",
        "languages": [],
        "company_sizes": [],
        "priorities": [],
        "preference_notes": "",
        "no_preference": [],
        "dealbreakers": [],
        "additional_notes": "",
        "evidence": {
            "resume": False,
            "resume_file_name": "",
            "linkedin": False,
            "github": False,
            "portfolio": False,
            "documents": 0,
        },
    }


def latest_snapshot_record(
    db: Session,
    *,
    profile_input_hash: str,
) -> CandidateMatchSnapshotRecord | None:
    return (
        db.query(CandidateMatchSnapshotRecord)
        .filter(
            CandidateMatchSnapshotRecord.profile_input_hash == profile_input_hash,
            CandidateMatchSnapshotRecord.matcher_version == MATCHER_VERSION,
        )
        .order_by(CandidateMatchSnapshotRecord.created_at.desc(), CandidateMatchSnapshotRecord.id.desc())
        .first()
    )


def snapshot_to_record(snapshot: CandidateMatchSnapshot) -> CandidateMatchSnapshotRecord:
    return CandidateMatchSnapshotRecord(
        id=uuid4().hex,
        profile_input_hash=snapshot.profile_input_hash,
        profile_hash=snapshot.profile_hash,
        matcher_version=MATCHER_VERSION,
        source=snapshot.source,
        data=snapshot.data,
        openclaw_error=snapshot.openclaw_error,
        created_at=datetime.now(UTC),
    )


def record_to_snapshot(record: CandidateMatchSnapshotRecord) -> CandidateMatchSnapshot:
    return CandidateMatchSnapshot(
        profile_input_hash=record.profile_input_hash,
        profile_hash=record.profile_hash,
        source=record.source,
        data=record.data,
        openclaw_error=record.openclaw_error,
    )


def build_profile_input_hash(profile: ProfilePayload) -> str:
    payload = json.dumps(
        {"version": MATCHER_VERSION, "profile": profile.model_dump()},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_snapshot_with_openclaw(
    *,
    profile: ProfilePayload,
    fallback_snapshot: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    executable = shutil.which(settings.openclaw_command) or settings.openclaw_command
    prompt = build_openclaw_candidate_snapshot_prompt(profile, fallback_snapshot)
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt") as prompt_file:
            prompt_file.write(prompt)
            prompt_file.flush()
            result = subprocess.run(
                [
                    executable,
                    "agent",
                    "--local",
                    "--agent",
                    settings.openclaw_agent_id,
                    "--message-file",
                    prompt_file.name,
                    "--thinking",
                    settings.openclaw_ai_match_thinking,
                    "--json",
                ],
                capture_output=True,
                check=True,
                text=True,
                timeout=settings.openclaw_ai_match_timeout_seconds,
            )
    except FileNotFoundError as exc:
        raise CandidateSnapshotError(
            f"OpenClaw command was not found: {settings.openclaw_command}. Install OpenClaw or "
            "set OPENCLAW_COMMAND to the executable path."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise CandidateSnapshotError("OpenClaw candidate snapshot timed out") from exc
    except subprocess.CalledProcessError as exc:
        error_output = (exc.stderr or exc.stdout or "OpenClaw command failed").strip()
        raise CandidateSnapshotError(summarize_openclaw_error(error_output)) from exc
    except OSError as exc:
        raise CandidateSnapshotError(f"OpenClaw command could not start: {exc}") from exc

    snapshot = extract_openclaw_candidate_snapshot_payload(result.stdout)
    if not snapshot:
        raise CandidateSnapshotError("OpenClaw did not return a candidate snapshot")
    return snapshot


def build_openclaw_candidate_snapshot_prompt(
    profile: ProfilePayload,
    fallback_snapshot: dict[str, Any],
) -> str:
    resume_text = ""
    if profile.resume_file_name and profile.resume_data_url:
        try:
            resume_text = extract_resume_text(profile.resume_file_name, profile.resume_data_url)[:50000]
        except Exception:
            resume_text = ""

    profile_payload = profile.model_dump()
    profile_payload["avatar_url"] = "[attached]" if profile.avatar_url.startswith("data:") else profile.avatar_url
    profile_payload["documents"] = summarize_profile_documents(profile.documents)
    profile_payload["resume_data_url"] = "[attached]" if profile.resume_data_url else ""
    payload = json.dumps(
        {
            "profile": profile_payload,
            "resume_text": resume_text,
            "fallback_snapshot": fallback_snapshot,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return (
        "Normalize this candidate for deterministic job matching.\n"
        "Return ONLY one valid JSON object, no markdown and no prose.\n"
        "Use the resume/profile evidence; do not invent facts.\n"
        "Return shape: {\"candidate\":{...}} where candidate has the same keys as fallback_snapshot.\n"
        "Keep arrays concise and deduplicated. Normalize aliases, seniority, locations, work formats, "
        "salary currency, skills, domains, priorities, dealbreakers, and evidence.\n"
        f"Input JSON:\n{payload}"
    )


def summarize_profile_documents(value: str) -> list[dict[str, Any]] | str:
    if not value:
        return ""
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return "[attached documents omitted]"
    if not isinstance(parsed, list):
        return "[attached documents omitted]"

    metadata_fields = (
        "id",
        "title",
        "category",
        "language",
        "file_name",
        "file_size",
        "file_type",
        "uploaded_at",
    )
    return [
        {
            field: document[field]
            for field in metadata_fields
            if field in document and isinstance(document[field], (str, int, float, bool))
        }
        for document in parsed
        if isinstance(document, dict)
    ]


def extract_openclaw_candidate_snapshot_payload(value: str) -> dict[str, Any]:
    for payload in extract_json_objects(value):
        candidate = payload.get("candidate")
        if isinstance(candidate, dict):
            return candidate

        if looks_like_candidate_snapshot(payload):
            return payload

        for text in extract_openclaw_text_payloads(payload):
            final_payload = extract_json_object(text)
            candidate = final_payload.get("candidate")
            if isinstance(candidate, dict):
                return candidate
            if looks_like_candidate_snapshot(final_payload):
                return final_payload

        result = payload.get("result")
        if not isinstance(result, dict):
            continue

        for key in ("finalAssistantVisibleText", "finalAssistantRawText"):
            final_text = result.get(key)
            if isinstance(final_text, str):
                final_payload = extract_json_object(final_text)
                candidate = final_payload.get("candidate")
                if isinstance(candidate, dict):
                    return candidate
                if looks_like_candidate_snapshot(final_payload):
                    return final_payload

    return {}


def looks_like_candidate_snapshot(value: dict[str, Any]) -> bool:
    return isinstance(value.get("roles"), list) and isinstance(value.get("skills"), list)


def normalize_candidate_snapshot(
    snapshot: dict[str, Any],
    fallback_snapshot: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(fallback_snapshot)

    for field in LIST_FIELDS:
        if field in snapshot:
            normalized[field] = normalize_list(snapshot[field])

    for field in SUMMARY_LIST_FIELDS:
        if isinstance(snapshot.get(field), list):
            normalized[field] = [
                item
                for item in snapshot[field]
                if isinstance(item, dict)
            ][:12]

    for field in STRING_FIELDS:
        if field in snapshot:
            normalized[field] = str(snapshot.get(field) or "").strip()[:500]

    if "salary_min" in snapshot:
        normalized["salary_min"] = parse_number(snapshot.get("salary_min"))

    evidence = snapshot.get("evidence")
    if isinstance(evidence, dict):
        normalized_evidence = dict(fallback_snapshot.get("evidence") or {})
        normalized_evidence.update(
            {
                key: value
                for key, value in evidence.items()
                if isinstance(key, str) and isinstance(value, (bool, int, str))
            }
        )
        normalized["evidence"] = normalized_evidence

    return normalized
