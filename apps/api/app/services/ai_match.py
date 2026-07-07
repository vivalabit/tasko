from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any

from app.models.profile import ProfilePayload
from app.services.resume_import import extract_json_object, extract_json_objects, summarize_openclaw_error

MATCHER_VERSION = "ai-match-v1"
MAX_REASON_COUNT = 3
MAX_GAP_COUNT = 3

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
    "ci cd": "ci/cd",
    "cv": "computer vision",
    "js": "javascript",
    "ml": "machine learning",
    "nlp": "natural language processing",
    "ts": "typescript",
    "vr": "virtual reality",
    "xr": "extended reality",
}

REMOTE_TERMS = {"remote", "work from home", "wfh"}
HYBRID_TERMS = {"hybrid"}
ONSITE_TERMS = {"onsite", "on-site", "office"}


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
) -> list[dict[str, Any]]:
    profile_snapshot = build_candidate_snapshot(profile)
    prepared_jobs: list[dict[str, Any]] = []
    now = datetime.now(UTC).isoformat()

    for job in jobs:
        if not isinstance(job, dict):
            continue

        job_snapshot = build_job_snapshot(job)
        cache_key = build_cache_key(profile_snapshot, job_snapshot)
        cached_match = job.get("aiMatch")
        if is_cached_match_valid(cached_match, cache_key) and (
            not openclaw_enabled or cached_match.get("source") == "openclaw"
        ):
            prepared_jobs.append(job)
            continue

        local_result = score_locally(profile_snapshot, job_snapshot)
        prepared_jobs.append(apply_match_result(job, local_result, cache_key, now))

    if not openclaw_enabled or openclaw_max_jobs <= 0:
        return prepared_jobs

    candidates = select_openclaw_candidates(prepared_jobs, openclaw_max_jobs)
    if not candidates:
        return prepared_jobs

    try:
        openclaw_results = score_with_openclaw(
            profile_snapshot=profile_snapshot,
            jobs=[build_job_snapshot(job) for job in candidates],
            command=command,
            agent_id=agent_id,
            thinking=thinking,
            timeout_seconds=timeout_seconds,
        )
    except OpenClawAiMatchError as exc:
        return [
            mark_openclaw_fallback(job, str(exc), now)
            if job.get("id") in {candidate.get("id") for candidate in candidates}
            else job
            for job in prepared_jobs
        ]

    by_id = {result["id"]: result for result in openclaw_results if isinstance(result.get("id"), str)}
    matched_jobs: list[dict[str, Any]] = []
    for job in prepared_jobs:
        job_id = job.get("id")
        result = by_id.get(job_id)
        if not result:
            matched_jobs.append(job)
            continue

        cache_key = job.get("aiMatch", {}).get("cacheKey", "")
        matched_jobs.append(apply_match_result(job, normalize_openclaw_result(result, job), cache_key, now))

    return matched_jobs


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
        "salary_currency": str(preferences.get("salary_currency") or "CHF"),
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
        "experience": experience.strip(),
        "department": str(job.get("department") or "").strip(),
        "overview": overview.strip()[:1200],
        "requirements": requirements[:16],
        "responsibilities": responsibilities[:12],
        "skills": skills[:40],
        "keywords": extract_keywords(text)[:40],
        "source_url": str(job.get("sourceUrl") or job.get("applyUrl") or "").strip(),
    }


def score_locally(candidate: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    breakdown = {
        "role_fit": score_role_fit(candidate, job),
        "skills_fit": score_skills_fit(candidate, job),
        "experience_fit": score_experience_fit(candidate, job),
        "preferences_fit": score_preferences_fit(candidate, job),
        "constraints_fit": score_constraints_fit(candidate, job),
        "industry_fit": score_industry_fit(candidate, job),
        "evidence_fit": score_evidence_fit(candidate),
    }
    raw_score = sum(breakdown.values())
    caps, cap_reasons = calculate_caps(candidate, job)
    score = min(raw_score, *caps) if caps else raw_score
    reasons = build_reasons(candidate, job, breakdown)
    gaps = build_gaps(candidate, job, breakdown, cap_reasons)

    return {
        "score": clamp_round(score),
        "source": "local",
        "confidence": infer_confidence(candidate, job),
        "breakdown": {key: clamp_round(value) for key, value in breakdown.items()},
        "reasons": reasons[:MAX_REASON_COUNT],
        "gaps": gaps[:MAX_GAP_COUNT],
        "heuristicScore": clamp_round(raw_score),
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
        raise OpenClawAiMatchError(f"OpenClaw command was not found: {command}") from exc
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
            "requirements": job["requirements"],
            "skills": job["skills"],
            "keywords": job["keywords"],
        }
        for job in jobs
    ]
    payload = json.dumps(
        {"candidate": profile_snapshot, "jobs": compact_jobs, "weights": WEIGHTS},
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return (
        "You score job fit for a personal job search app.\n"
        "Return ONLY one valid JSON object, no markdown and no prose.\n"
        "Use only the provided snapshots. Do not invent missing evidence.\n"
        "For every job, apply these weights: role_fit 20, skills_fit 30, experience_fit 15, "
        "preferences_fit 15, constraints_fit 10, industry_fit 5, evidence_fit 5.\n"
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

        payloads = result.get("payloads")
        if isinstance(payloads, list):
            for item in payloads:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if not isinstance(text, str):
                    continue
                final_payload = extract_json_object(text)
                if isinstance(final_payload.get("matches"), list):
                    return final_payload

    return {}


def normalize_openclaw_result(result: dict[str, Any], current_job: dict[str, Any]) -> dict[str, Any]:
    fallback = current_job.get("aiMatch", {}) if isinstance(current_job.get("aiMatch"), dict) else {}
    breakdown = result.get("breakdown") if isinstance(result.get("breakdown"), dict) else {}
    normalized_breakdown = {
        key: clamp_round(breakdown.get(key, fallback.get("breakdown", {}).get(key, 0)))
        for key in WEIGHTS
    }

    return {
        "score": clamp_round(result.get("score", current_job.get("match", 0))),
        "source": "openclaw",
        "confidence": normalize_confidence(result.get("confidence", fallback.get("confidence", "medium"))),
        "breakdown": normalized_breakdown,
        "reasons": normalize_string_list(result.get("reasons"), MAX_REASON_COUNT),
        "gaps": normalize_string_list(result.get("gaps"), MAX_GAP_COUNT),
        "heuristicScore": clamp_round(fallback.get("heuristicScore", current_job.get("match", 0))),
    }


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
        "source": result.get("source", "local"),
        "score": score,
        "confidence": normalize_confidence(result.get("confidence", "low")),
        "breakdown": result.get("breakdown", {}),
        "reasons": normalize_string_list(result.get("reasons"), MAX_REASON_COUNT),
        "gaps": normalize_string_list(result.get("gaps"), MAX_GAP_COUNT),
        "heuristicScore": clamp_round(result.get("heuristicScore", score)),
        "updatedAt": updated_at,
    }
    return next_job


def mark_openclaw_fallback(job: dict[str, Any], error: str, updated_at: str) -> dict[str, Any]:
    next_job = dict(job)
    ai_match = dict(next_job.get("aiMatch") or {})
    ai_match["source"] = "local"
    ai_match["openclawError"] = error[:240]
    ai_match["updatedAt"] = updated_at
    next_job["aiMatch"] = ai_match
    return next_job


def select_openclaw_candidates(jobs: list[dict[str, Any]], max_jobs: int) -> list[dict[str, Any]]:
    uncached = [
        job
        for job in jobs
        if isinstance(job.get("aiMatch"), dict) and job["aiMatch"].get("source") != "openclaw"
    ]
    return sorted(uncached, key=lambda job: abs(int(job.get("match", 0)) - 65))[:max_jobs]


def build_cache_key(profile_snapshot: dict[str, Any], job_snapshot: dict[str, Any]) -> str:
    payload = json.dumps(
        {"version": MATCHER_VERSION, "candidate": profile_snapshot, "job": job_snapshot},
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


def score_role_fit(candidate: dict[str, Any], job: dict[str, Any]) -> float:
    job_tokens = token_set(" ".join([job["title"], job["experience"], *job["keywords"]]))
    role_scores = [token_overlap_score(role, job_tokens) for role in candidate.get("roles", [])]
    if not role_scores:
        return 6

    return WEIGHTS["role_fit"] * max(role_scores)


def score_skills_fit(candidate: dict[str, Any], job: dict[str, Any]) -> float:
    candidate_skills = [canonical_term(skill) for skill in candidate.get("skills", [])]
    job_text = canonical_term(" ".join([job["title"], job["overview"], *job["requirements"], *job["skills"], *job["keywords"]]))
    job_skill_terms = {canonical_term(skill) for skill in job.get("skills", [])}
    if not candidate_skills:
        return 4

    matches = [skill for skill in candidate_skills if skill and (skill in job_text or skill in job_skill_terms)]
    if not job_skill_terms and not job["requirements"]:
        return 12 if matches else 8

    ratio = len(set(matches)) / max(1, min(len(candidate_skills), max(4, len(job_skill_terms) or 8)))
    return WEIGHTS["skills_fit"] * min(1.0, ratio)


def score_experience_fit(candidate: dict[str, Any], job: dict[str, Any]) -> float:
    job_seniority = infer_seniority(" ".join([job["title"], job["experience"]]))
    candidate_seniority = infer_candidate_seniority(candidate)
    explicit_preferences = " ".join(candidate.get("seniority", []))

    if explicit_preferences and normalize_text(job_seniority) in normalize_text(explicit_preferences):
        return WEIGHTS["experience_fit"]

    if not job_seniority or not candidate_seniority:
        return 8

    gap = abs(seniority_rank(candidate_seniority) - seniority_rank(job_seniority))
    if gap == 0:
        return WEIGHTS["experience_fit"]
    if gap == 1:
        return 10
    return 4


def score_preferences_fit(candidate: dict[str, Any], job: dict[str, Any]) -> float:
    checks: list[float] = []
    if candidate.get("locations") and "locations" not in candidate.get("no_preference", []):
        checks.append(1.0 if matches_any(job["location"], candidate["locations"]) else 0.25)
    if candidate.get("work_formats") and "work_formats" not in candidate.get("no_preference", []):
        checks.append(1.0 if matches_work_format(job, candidate["work_formats"]) else 0.35)
    if candidate.get("employment_types") and "employment_types" not in candidate.get("no_preference", []):
        checks.append(1.0 if matches_any(job["employment_type"], candidate["employment_types"]) else 0.35)

    if not checks:
        return 10

    return WEIGHTS["preferences_fit"] * (sum(checks) / len(checks))


def score_constraints_fit(candidate: dict[str, Any], job: dict[str, Any]) -> float:
    caps, _ = calculate_caps(candidate, job)
    if 30 in caps or 35 in caps:
        return 1
    if 50 in caps:
        return 4
    return WEIGHTS["constraints_fit"]


def score_industry_fit(candidate: dict[str, Any], job: dict[str, Any]) -> float:
    industry_terms = candidate.get("industries", []) + candidate.get("domains", []) + candidate.get("priorities", [])
    if not industry_terms:
        return 3

    job_text = " ".join([job["title"], job["department"], job["overview"], *job["keywords"]])
    return WEIGHTS["industry_fit"] if matches_any(job_text, industry_terms) else 1


def score_evidence_fit(candidate: dict[str, Any]) -> float:
    evidence = candidate.get("evidence", {})
    points = 0
    points += 2 if evidence.get("resume") else 0
    points += 1 if evidence.get("linkedin") else 0
    points += 1 if evidence.get("github") or evidence.get("portfolio") else 0
    points += 1 if evidence.get("documents") else 0
    return min(WEIGHTS["evidence_fit"], points)


def calculate_caps(candidate: dict[str, Any], job: dict[str, Any]) -> tuple[list[int], list[str]]:
    caps: list[int] = []
    reasons: list[str] = []
    job_text = " ".join([job["title"], job["location"], job["employment_type"], job["overview"], *job["requirements"]])

    for dealbreaker in candidate.get("dealbreakers", []):
        if dealbreaker and normalize_text(dealbreaker) in normalize_text(job_text):
            caps.append(30)
            reasons.append(f"Potential dealbreaker: {dealbreaker}")
            break

    salary_min = candidate.get("salary_min")
    salary_amount = job.get("salary_amount")
    if salary_min and salary_amount and salary_amount < salary_min:
        caps.append(50)
        reasons.append("Salary appears below your minimum")

    candidate_seniority = infer_candidate_seniority(candidate)
    job_seniority = infer_seniority(" ".join([job["title"], job["experience"], *job["requirements"]]))
    if candidate_seniority and job_seniority and seniority_rank(job_seniority) - seniority_rank(candidate_seniority) >= 2:
        caps.append(45)
        reasons.append("Seniority appears higher than profile evidence")

    return caps, reasons


def build_reasons(candidate: dict[str, Any], job: dict[str, Any], breakdown: dict[str, float]) -> list[str]:
    reasons: list[str] = []
    if breakdown["role_fit"] >= 12:
        reasons.append("Role title aligns with your target/current role")
    matched_skills = matched_skill_names(candidate, job)
    if matched_skills:
        reasons.append(f"Matched skills: {', '.join(matched_skills[:4])}")
    if breakdown["preferences_fit"] >= 10:
        reasons.append("Location, work format, or employment preferences look compatible")
    if breakdown["experience_fit"] >= 10:
        reasons.append("Seniority appears compatible")
    return reasons or ["Some profile signals overlap with this vacancy"]


def build_gaps(
    candidate: dict[str, Any],
    job: dict[str, Any],
    breakdown: dict[str, float],
    cap_reasons: list[str],
) -> list[str]:
    gaps = list(cap_reasons)
    if breakdown["skills_fit"] < 12:
        gaps.append("Few required skills are explicit in your profile")
    if breakdown["role_fit"] < 8:
        gaps.append("Role title is not close to your target roles")
    if breakdown["preferences_fit"] < 9:
        gaps.append("Some location/work format preferences may not match")
    if not candidate.get("evidence", {}).get("resume"):
        gaps.append("Attach a resume to increase match confidence")
    return gaps or ["No major gaps detected from available data"]


def matched_skill_names(candidate: dict[str, Any], job: dict[str, Any]) -> list[str]:
    job_text = canonical_term(" ".join([job["title"], job["overview"], *job["requirements"], *job["skills"], *job["keywords"]]))
    return [skill for skill in candidate.get("skills", []) if canonical_term(skill) in job_text]


def infer_confidence(candidate: dict[str, Any], job: dict[str, Any]) -> str:
    signal_count = 0
    signal_count += 1 if candidate.get("roles") else 0
    signal_count += 1 if candidate.get("skills") else 0
    signal_count += 1 if candidate.get("experience") else 0
    signal_count += 1 if job.get("overview") or job.get("requirements") else 0
    signal_count += 1 if job.get("skills") else 0
    if signal_count >= 4:
        return "high"
    if signal_count >= 2:
        return "medium"
    return "low"


def infer_candidate_seniority(candidate: dict[str, Any]) -> str:
    text = " ".join(
        [
            candidate.get("current_role", ""),
            candidate.get("desired_role", ""),
            " ".join(candidate.get("roles", [])),
            " ".join(candidate.get("seniority", [])),
        ]
    )
    return infer_seniority(text)


def infer_seniority(text: str) -> str:
    normalized = normalize_text(text)
    if any(term in normalized for term in ("intern", "trainee", "apprentice")):
        return "intern"
    if any(term in normalized for term in ("junior", "entry", "associate")):
        return "junior"
    if any(term in normalized for term in ("principal", "staff", "lead", "manager", "head")):
        return "lead"
    if any(term in normalized for term in ("senior", "sr ")):
        return "senior"
    if any(term in normalized for term in ("mid", "intermediate")):
        return "mid"
    return ""


def seniority_rank(value: str) -> int:
    return {"intern": 0, "junior": 1, "mid": 2, "senior": 3, "lead": 4}.get(value, 2)


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


def token_set(text: str) -> set[str]:
    return set(extract_keywords(text))


def token_overlap_score(value: str, target_tokens: set[str]) -> float:
    tokens = token_set(value)
    if not tokens:
        return 0
    overlap = len(tokens & target_tokens) / len(tokens)
    return math.sqrt(overlap)


def canonical_term(value: str) -> str:
    normalized = normalize_text(value)
    for alias, canonical in SKILL_ALIASES.items():
        normalized = re.sub(rf"\b{re.escape(alias)}\b", canonical, normalized)
    return normalized


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#./-]+", " ", str(value).lower())).strip()


def matches_any(text: str, candidates: list[str]) -> bool:
    normalized_text = canonical_term(text)
    return any(canonical_term(candidate) in normalized_text for candidate in candidates if candidate)


def matches_work_format(job: dict[str, Any], work_formats: list[str]) -> bool:
    job_text = normalize_text(" ".join([job["title"], job["location"], job["employment_type"], job["overview"]]))
    preferred = normalize_text(" ".join(work_formats))
    if any(term in preferred for term in REMOTE_TERMS):
        return any(term in job_text for term in REMOTE_TERMS) or "hybrid" in job_text
    if any(term in preferred for term in HYBRID_TERMS):
        return "hybrid" in job_text or any(term in job_text for term in REMOTE_TERMS)
    if any(term in preferred for term in ONSITE_TERMS):
        return any(term in job_text for term in ONSITE_TERMS)
    return matches_any(job_text, work_formats)


def normalize_confidence(value: Any) -> str:
    return str(value).lower() if str(value).lower() in {"low", "medium", "high"} else "low"


def clamp_round(value: Any) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0
    return max(0, min(100, round(number)))
