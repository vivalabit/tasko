from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
from datetime import UTC, datetime
from typing import Any

from app.models.profile import ProfilePayload
from app.services.resume_import import (
    extract_json_object,
    extract_json_objects,
    extract_openclaw_text_payloads,
    summarize_openclaw_error,
)

MATCHER_VERSION = "ai-match-v1"
MAX_REASON_COUNT = 3
MAX_GAP_COUNT = 3
JOB_ADDED_AT_FIELDS = ("addedAt", "importedAt", "createdAt", "created_at")

WEIGHTS = {
    "role_fit": 20,
    "skills_fit": 30,
    "experience_fit": 15,
    "preferences_fit": 15,
    "constraints_fit": 10,
    "industry_fit": 5,
    "evidence_fit": 5,
}

SKILL_ALIASES = {
    "ai": "artificial intelligence",
    "ar": "augmented reality",
    "backend": "back end",
    "back-end": "back end",
    "computer vision": "computer vision",
    "ci cd": "ci/cd",
    "cv": "computer vision",
    "devops": "development operations",
    "front-end": "front end",
    "frontend": "front end",
    "gen ai": "generative artificial intelligence",
    "gen-ai": "generative artificial intelligence",
    "genai": "generative artificial intelligence",
    "generative ai": "generative artificial intelligence",
    "gpt": "large language model",
    "js": "javascript",
    "large language models": "large language model",
    "llms": "large language model",
    "llm": "large language model",
    "ml": "machine learning",
    "ml ops": "machine learning operations",
    "ml-ops": "machine learning operations",
    "mlops": "machine learning operations",
    "nlp": "natural language processing",
    "node": "node",
    "node.js": "node",
    "nodejs": "node",
    "react.js": "react",
    "reactjs": "react",
    "ts": "typescript",
    "vr": "virtual reality",
    "xr": "extended reality",
}

CURRENCY_ALIASES = {
    "CHF": {"chf", "fr", "sfr", "swiss franc", "swiss francs"},
    "EUR": {"eur", "euro", "euros", "€"},
    "GBP": {"gbp", "pound", "pounds", "£"},
    "USD": {"usd", "dollar", "dollars", "$"},
}
SENIORITY_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("lead", ("principal", "staff", "lead", "manager", "head", "director", "vp", "chief", "architect")),
    ("senior", ("senior", "sr", "experienced", "expert", "advanced")),
    ("mid", ("mid", "mid level", "mid-level", "intermediate", "regular", "professional")),
    ("junior", ("junior", "jr", "entry", "entry level", "graduate", "new grad", "associate")),
    ("intern", ("intern", "internship", "trainee", "apprentice", "working student", "student")),
)


class OpenClawAiMatchError(RuntimeError):
    pass


def calculate_ai_matches(
    profile: ProfilePayload,
    jobs: list[dict[str, Any]],
    *,
    command: str,
    agent_id: str,
    thinking: str,
    timeout_seconds: int,
    openclaw_enabled: bool,
    openclaw_max_jobs: int,
    force: bool = False,
    candidate_snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not openclaw_enabled:
        raise OpenClawAiMatchError("OpenClaw AI match is required but disabled")
    if openclaw_max_jobs <= 0:
        raise OpenClawAiMatchError("OpenClaw AI match requires a positive job batch size")

    profile_snapshot = candidate_snapshot or build_candidate_snapshot(profile)
    ordered_jobs: list[dict[str, Any] | tuple[dict[str, Any], dict[str, Any], str]] = []
    now = datetime.now(UTC).isoformat()
    jobs_to_score: list[tuple[dict[str, Any], dict[str, Any], str]] = []

    for job in jobs:
        if not isinstance(job, dict):
            continue

        job_snapshot = build_job_snapshot(job)
        cache_key = build_cache_key(profile_snapshot, job_snapshot)
        cached_match = job.get("aiMatch")
        if not force and is_cached_match_valid(cached_match, cache_key) and cached_match.get("source") == "openclaw":
            ordered_jobs.append(job)
            continue

        scored_job = (job, job_snapshot, cache_key)
        jobs_to_score.append(scored_job)
        ordered_jobs.append(scored_job)

    if not jobs_to_score:
        return [item for item in ordered_jobs if isinstance(item, dict)]

    by_id: dict[str, dict[str, Any]] = {}
    for start in range(0, len(jobs_to_score), openclaw_max_jobs):
        chunk = jobs_to_score[start : start + openclaw_max_jobs]
        openclaw_results = score_with_openclaw(
            profile_snapshot=profile_snapshot,
            jobs=[job_snapshot for _, job_snapshot, _ in chunk],
            command=command,
            agent_id=agent_id,
            thinking=thinking,
            timeout_seconds=timeout_seconds,
        )
        by_id.update(
            {
                result["id"]: result
                for result in openclaw_results
                if isinstance(result.get("id"), str)
            }
        )

    scored_ids = {job_snapshot["id"] for _, job_snapshot, _ in jobs_to_score}
    missing_ids = sorted(scored_ids - set(by_id))
    if missing_ids:
        raise OpenClawAiMatchError(f"OpenClaw did not return matches for: {', '.join(missing_ids[:8])}")

    return [
        item
        if isinstance(item, dict)
        else apply_match_result(
            item[0],
            normalize_openclaw_result(by_id[item[1]["id"]], item[0]),
            item[2],
            now,
        )
        for item in ordered_jobs
    ]


def build_candidate_snapshot(profile: ProfilePayload) -> dict[str, Any]:
    preferences = parse_json_object(profile.job_preferences)
    experience_entries = parse_json_list(profile.experience)
    education_entries = parse_json_list(profile.education)
    documents = parse_json_list(profile.documents)
    skills = normalize_list(parse_lines(profile.skills))
    roles = normalize_list(
        [
            profile.current_role,
            profile.desired_role,
            *normalize_list(preferences.get("desired_roles", [])),
            *[entry.get("title", "") for entry in experience_entries if isinstance(entry, dict)],
        ]
    )
    domains = extract_keywords(
        " ".join(
            [
                profile.headline,
                profile.additional_notes,
                *skills,
                *[
                    str(entry.get("description", ""))
                    for entry in experience_entries
                    if isinstance(entry, dict)
                ],
            ]
        )
    )[:20]

    return {
        "roles": roles[:12],
        "current_role": profile.current_role.strip(),
        "desired_role": profile.desired_role.strip(),
        "headline": profile.headline.strip()[:500],
        "skills": skills[:80],
        "domains": domains,
        "experience": summarize_experience(experience_entries),
        "education": summarize_education(education_entries),
        "locations": normalize_list([profile.location, *normalize_list(preferences.get("locations", []))]),
        "work_formats": normalize_list([profile.work_format, *normalize_list(preferences.get("work_formats", []))]),
        "employment_types": normalize_list(preferences.get("employment_types", [])),
        "industries": normalize_list(preferences.get("industries", [])),
        "seniority": normalize_list(preferences.get("seniority", [])),
        "salary_min": parse_number(preferences.get("salary_min", "")),
        "salary_currency": normalize_currency(preferences.get("salary_currency") or "CHF") or "CHF",
        "work_authorization": str(preferences.get("work_authorization") or "").strip(),
        "languages": normalize_list(preferences.get("languages", [])),
        "company_sizes": normalize_list(preferences.get("company_sizes", [])),
        "priorities": normalize_list(preferences.get("priorities", [])),
        "preference_notes": str(preferences.get("notes") or "").strip()[:500],
        "no_preference": normalize_list(preferences.get("no_preference", [])),
        "dealbreakers": normalize_list(parse_lines(profile.dealbreakers)),
        "additional_notes": profile.additional_notes.strip()[:500],
        "evidence": {
            "resume": bool(profile.resume_file_name and profile.resume_data_url),
            "resume_file_name": profile.resume_file_name,
            "linkedin": bool(profile.linkedin),
            "github": bool(profile.github),
            "portfolio": bool(profile.portfolio or profile.personal_site),
            "documents": len(documents),
        },
    }


def build_job_snapshot(job: dict[str, Any]) -> dict[str, Any]:
    requirements = normalize_list(job.get("requirements", []))
    responsibilities = normalize_list(job.get("responsibilities", []))
    skills = normalize_list(job.get("skills", []))
    overview = str(job.get("overview") or "")
    title = str(job.get("title") or "")
    company = str(job.get("company") or "")
    location = str(job.get("location") or "")
    employment_type = str(job.get("type") or "")
    experience = str(job.get("experience") or "")
    text = " ".join([title, company, location, employment_type, experience, overview, *requirements, *responsibilities, *skills])

    return {
        "id": str(job.get("id") or ""),
        "title": title.strip(),
        "company": company.strip(),
        "location": location.strip(),
        "employment_type": employment_type.strip(),
        "salary": str(job.get("salary") or "").strip(),
        "salary_amount": parse_job_salary(job),
        "salary_currency": parse_job_salary_currency(job),
        "experience": experience.strip(),
        "department": str(job.get("department") or "").strip(),
        "overview": overview.strip()[:1200],
        "requirements": requirements[:16],
        "responsibilities": responsibilities[:12],
        "skills": skills[:40],
        "keywords": extract_keywords(text)[:40],
        "source_url": str(job.get("sourceUrl") or job.get("applyUrl") or "").strip(),
    }


def score_with_openclaw(
    *,
    profile_snapshot: dict[str, Any],
    jobs: list[dict[str, Any]],
    command: str,
    agent_id: str,
    thinking: str,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    if not jobs:
        return []

    executable = shutil.which(command) or command
    prompt = build_openclaw_ai_match_prompt(profile_snapshot, jobs)
    try:
        result = subprocess.run(
            [executable, "agent", "--agent", agent_id, "--message", prompt, "--thinking", thinking, "--json"],
            capture_output=True,
            check=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise OpenClawAiMatchError(
            f"OpenClaw command was not found: {command}. Install OpenClaw or set "
            "OPENCLAW_COMMAND to the executable path."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise OpenClawAiMatchError("OpenClaw AI match timed out") from exc
    except subprocess.CalledProcessError as exc:
        error_output = (exc.stderr or exc.stdout or "OpenClaw command failed").strip()
        raise OpenClawAiMatchError(summarize_openclaw_error(error_output)) from exc

    payload = extract_openclaw_ai_match_payload(result.stdout)
    matches = payload.get("matches", [])
    if not isinstance(matches, list):
        return []

    return [match for match in matches if isinstance(match, dict)]


def build_openclaw_ai_match_prompt(profile_snapshot: dict[str, Any], jobs: list[dict[str, Any]]) -> str:
    compact_jobs = [
        {
            "id": job["id"],
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "employment_type": job["employment_type"],
            "salary": job["salary"],
            "experience": job["experience"],
            "department": job["department"],
            "overview": job["overview"],
            "requirements": job["requirements"],
            "responsibilities": job["responsibilities"],
            "skills": job["skills"],
            "keywords": job["keywords"],
            "source_url": job["source_url"],
        }
        for job in jobs
    ]
    payload = json.dumps(
        {"candidate": profile_snapshot, "jobs": compact_jobs, "breakdownMaxScores": WEIGHTS},
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return (
        "You score job fit for a personal job search app.\n"
        "Return ONLY one valid JSON object, no markdown and no prose.\n"
        "Use only the provided snapshots. Do not invent missing evidence.\n"
        "For every job, set score as your expert judgment from 0 to 100.\n"
        "Score is the final AI assessment, not an arithmetic sum of breakdown values.\n"
        "Breakdown is a structured explanation with category scores capped by breakdownMaxScores; "
        "it must be internally consistent, but it is not the formula for score.\n"
        "Apply caps: hard dealbreaker max 30, salary below candidate minimum max 50, "
        "work authorization mismatch max 35, major seniority mismatch max 45.\n"
        "JSON shape:\n"
        '{"matches":[{"id":"job id","score":0,"confidence":"low|medium|high",'
        '"breakdown":{"role_fit":0,"skills_fit":0,"experience_fit":0,"preferences_fit":0,'
        '"constraints_fit":0,"industry_fit":0,"evidence_fit":0},'
        '"reasons":["max 3 short reasons"],"gaps":["max 3 short gaps"]}]}\n'
        f"Input JSON:\n{payload}"
    )


def extract_openclaw_ai_match_payload(value: str) -> dict[str, object]:
    for payload in extract_json_objects(value):
        if isinstance(payload.get("matches"), list):
            return payload

        for text in extract_openclaw_text_payloads(payload):
            final_payload = extract_json_object(text)
            if isinstance(final_payload.get("matches"), list):
                return final_payload

        result = payload.get("result")
        if not isinstance(result, dict):
            continue

        for key in ("finalAssistantVisibleText", "finalAssistantRawText"):
            final_text = result.get(key)
            if isinstance(final_text, str):
                final_payload = extract_json_object(final_text)
                if isinstance(final_payload.get("matches"), list):
                    return final_payload

        nested_result = result.get("result")
        if isinstance(nested_result, dict):
            for key in ("finalAssistantVisibleText", "finalAssistantRawText"):
                final_text = nested_result.get(key)
                if isinstance(final_text, str):
                    final_payload = extract_json_object(final_text)
                    if isinstance(final_payload.get("matches"), list):
                        return final_payload

    return {}


def normalize_openclaw_result(result: dict[str, Any], current_job: dict[str, Any]) -> dict[str, Any]:
    fallback = current_job.get("aiMatch", {}) if isinstance(current_job.get("aiMatch"), dict) else {}
    validate_openclaw_result(result, current_job)
    breakdown = result["breakdown"]
    normalized_breakdown = {key: clamp_round(breakdown[key]) for key in WEIGHTS}

    return {
        "score": clamp_round(result["score"]),
        "source": "openclaw",
        "confidence": normalize_confidence(result.get("confidence", fallback.get("confidence", "medium"))),
        "breakdown": normalized_breakdown,
        "reasons": normalize_string_list(result.get("reasons"), MAX_REASON_COUNT),
        "gaps": normalize_string_list(result.get("gaps"), MAX_GAP_COUNT),
        "heuristicScore": clamp_round(fallback.get("heuristicScore", current_job.get("match", 0))),
    }


def validate_openclaw_result(result: dict[str, Any], current_job: dict[str, Any]) -> None:
    job_id = str(result.get("id") or current_job.get("id") or "unknown")
    if "score" not in result:
        raise OpenClawAiMatchError(f"OpenClaw returned an incomplete match for {job_id}: missing score")

    breakdown = result.get("breakdown")
    if not isinstance(breakdown, dict):
        raise OpenClawAiMatchError(
            f"OpenClaw returned an incomplete match for {job_id}: missing breakdown"
        )

    missing_breakdown_keys = [key for key in WEIGHTS if key not in breakdown]
    if missing_breakdown_keys:
        raise OpenClawAiMatchError(
            f"OpenClaw returned an incomplete match for {job_id}: missing breakdown keys "
            f"{', '.join(missing_breakdown_keys)}"
        )


def apply_match_result(
    job: dict[str, Any],
    result: dict[str, Any],
    cache_key: str,
    updated_at: str,
) -> dict[str, Any]:
    next_job = dict(job)
    score = clamp_round(result.get("score", next_job.get("match", 0)))
    next_job["match"] = score
    next_job["aiMatch"] = {
        "version": MATCHER_VERSION,
        "cacheKey": cache_key,
        "source": result.get("source", "openclaw"),
        "score": score,
        "confidence": normalize_confidence(result.get("confidence", "low")),
        "breakdown": result.get("breakdown", {}),
        "reasons": normalize_string_list(result.get("reasons"), MAX_REASON_COUNT),
        "gaps": normalize_string_list(result.get("gaps"), MAX_GAP_COUNT),
        "heuristicScore": clamp_round(result.get("heuristicScore", score)),
        "updatedAt": updated_at,
    }
    return next_job


def build_cache_key(profile_snapshot: dict[str, Any], job_snapshot: dict[str, Any]) -> str:
    payload = json.dumps(
        {"version": MATCHER_VERSION, "candidate": profile_snapshot, "job": job_snapshot},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_profile_hash(profile: ProfilePayload) -> str:
    return build_candidate_snapshot_hash(build_candidate_snapshot(profile))


def build_candidate_snapshot_hash(snapshot: dict[str, Any]) -> str:
    payload = json.dumps(
        {"version": MATCHER_VERSION, "candidate": snapshot},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_cached_match_valid(value: Any, cache_key: str) -> bool:
    return (
        isinstance(value, dict)
        and value.get("version") == MATCHER_VERSION
        and value.get("cacheKey") == cache_key
        and isinstance(value.get("score"), int)
    )


def infer_seniority(text: str) -> str:
    normalized = normalize_text(text).replace(".", " ").replace("-", " ").replace("/", " ")
    padded = f" {normalized} "
    for seniority, terms in SENIORITY_PATTERNS:
        if any(f" {normalize_text(term).replace('.', ' ').replace('-', ' ').replace('/', ' ')} " in padded for term in terms):
            return seniority
    return ""


def summarize_experience(entries: list[Any]) -> list[dict[str, str]]:
    summary: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        summary.append(
            {
                "title": str(entry.get("title") or "")[:160],
                "company": str(entry.get("company") or "")[:120],
                "employment_type": str(entry.get("employment_type") or "")[:80],
                "description": str(entry.get("description") or "")[:500],
            }
        )
    return summary[:12]


def summarize_education(entries: list[Any]) -> list[dict[str, str]]:
    summary: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        summary.append(
            {
                "credential": str(entry.get("credential") or "")[:160],
                "field_of_study": str(entry.get("field_of_study") or "")[:120],
                "institution": str(entry.get("institution") or "")[:120],
            }
        )
    return summary[:8]


def parse_job_salary(job: dict[str, Any]) -> int:
    amounts = [
        parse_number(job.get("salaryAverage", "")),
        parse_number(job.get("salaryMax", "")),
        parse_number(job.get("salary", "")),
    ]
    return max(amounts)


def parse_job_salary_currency(job: dict[str, Any]) -> str:
    explicit_currency = normalize_currency(job.get("salaryCurrency") or job.get("salary_currency"))
    if explicit_currency:
        return explicit_currency

    salary_text = " ".join(
        str(job.get(field) or "")
        for field in ("salary", "salaryAverage", "salaryMin", "salaryMax")
    )
    return normalize_currency(salary_text)


def normalize_currency(value: Any) -> str:
    normalized = normalize_text(str(value or ""))
    raw_value = str(value or "")
    for currency, aliases in CURRENCY_ALIASES.items():
        if any(alias in raw_value for alias in aliases if alias in {"€", "£", "$"}):
            return currency
        if any(f" {normalize_text(alias)} " in f" {normalized} " for alias in aliases):
            return currency
    return ""


def parse_number(value: Any) -> int:
    if value is None:
        return 0
    raw_value = str(value)
    normalized_value = re.sub(r"(?<=\d)[\s'](?=\d{3}\b)", "", raw_value)
    matches = re.findall(r"\d+(?:[,.]\d+)?", normalized_value)
    if not matches:
        return 0
    numbers = []
    for match in matches:
        cleaned = re.sub(r"[,.]", "", match)
        try:
            amount = int(cleaned)
        except ValueError:
            continue
        if amount < 1000 and re.search(r"\d\s*k\b", raw_value, re.IGNORECASE):
            amount *= 1000
        numbers.append(amount)
    return max(numbers, default=0)


def parse_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value) if value.strip() else {}
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def parse_json_list(value: str) -> list[Any]:
    try:
        parsed = json.loads(value) if value.strip() else []
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def parse_lines(value: str) -> list[str]:
    return [
        line.strip(" \t-•*")
        for line in value.replace("\r", "\n").replace(",", "\n").split("\n")
        if line.strip(" \t-•*")
    ]


def normalize_list(value: Any) -> list[str]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = [item for item in value if isinstance(item, str)]
    else:
        values = []
    return list(dict.fromkeys(item.strip() for item in values if item and item.strip()))


def normalize_string_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:180] for item in value if str(item).strip()][:limit]


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#./-]{1,}", canonical_term(text))
    blocked = {
        "and",
        "are",
        "for",
        "from",
        "job",
        "role",
        "the",
        "this",
        "with",
        "you",
        "your",
    }
    keywords = [word for word in words if word not in blocked and len(word) > 2]
    return list(dict.fromkeys(keywords))


def canonical_term(value: str) -> str:
    normalized = normalize_text(value)
    for alias, canonical in sorted(SKILL_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        normalized = re.sub(rf"\b{re.escape(alias)}\b", canonical, normalized)
    return normalized


def normalize_text(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#./-]+", " ", ascii_value.lower())).strip()


def normalize_confidence(value: Any) -> str:
    return str(value).lower() if str(value).lower() in {"low", "medium", "high"} else "low"


def clamp_round(value: Any) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0
    return max(0, min(100, round(number)))
