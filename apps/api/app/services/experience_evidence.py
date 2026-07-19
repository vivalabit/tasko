import hashlib
import json
import re
from typing import Any


TECHNOLOGY_TERMS = (
    "Amazon Web Services",
    "Google Cloud Platform",
    "Microsoft Azure",
    "Spring Boot",
    "React Native",
    "Node.js",
    "Next.js",
    "Vue.js",
    "Power BI",
    "C++",
    "C#",
    "ASP.NET",
    ".NET",
    "FastAPI",
    "Django",
    "Flask",
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "Kotlin",
    "Swift",
    "Rust",
    "Go",
    "Ruby",
    "PHP",
    "React",
    "Angular",
    "Svelte",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "Elasticsearch",
    "Kafka",
    "RabbitMQ",
    "GraphQL",
    "gRPC",
    "REST",
    "Docker",
    "Kubernetes",
    "Terraform",
    "Ansible",
    "Jenkins",
    "GitHub Actions",
    "GitLab CI",
    "AWS",
    "GCP",
    "Azure",
    "Linux",
    "Git",
    "SQL",
)
EXPLICIT_TECHNOLOGY_FIELDS = ("technologies", "technology", "tech_stack", "skills")
EXPLICIT_ACHIEVEMENT_FIELDS = ("achievements", "achievement")
TECHNOLOGY_LABEL_PATTERN = re.compile(
    r"^(?:technologies|technology|tech stack|stack|tools|technologien)\s*:\s*(.+)$",
    re.IGNORECASE,
)


def build_atomic_experience_evidence(value: Any) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    used_experience_ids: set[str] = set()
    for index, entry in enumerate(parse_experience_entries(value), start=1):
        experience_id = unique_experience_id(
            stable_experience_id(entry, index),
            entry,
            index=index,
            used=used_experience_ids,
        )
        used_experience_ids.add(experience_id)
        append_field_claim(
            claims,
            experience_id=experience_id,
            claim_type="employer",
            text=entry_text(entry, "company"),
        )
        append_field_claim(
            claims,
            experience_id=experience_id,
            claim_type="title",
            text=entry_text(entry, "title"),
        )
        append_field_claim(
            claims,
            experience_id=experience_id,
            claim_type="period",
            text=experience_period(entry),
        )

        description = entry_text(entry, "description")
        for technology in extract_technologies(entry, description):
            append_hashed_claim(
                claims,
                experience_id=experience_id,
                claim_type="technology",
                text=technology,
            )
        for achievement in extract_achievements(entry, description):
            append_hashed_claim(
                claims,
                experience_id=experience_id,
                claim_type="achievement",
                text=achievement,
            )
    return claims


def parse_experience_entries(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        return [entry for entry in parsed if isinstance(entry, dict)]
    return [
        {
            "id": f"legacy-{index:04d}",
            "description": text,
        }
        for index, text in enumerate(split_achievements(value), start=1)
    ]


def stable_experience_id(entry: dict[str, Any], index: int) -> str:
    raw_id = str(entry.get("id") or "").strip()
    if raw_id:
        normalized = re.sub(r"[^a-z0-9_-]+", "-", raw_id.casefold()).strip("-_")
        if normalized:
            return normalized[:80]
    identity = "\x1f".join(
        entry_text(entry, field).casefold()
        for field in ("company", "title", "start_date", "end_date")
    )
    if identity.strip("\x1f"):
        return f"entry-{claim_digest(identity)}"
    return f"entry-{index:04d}"


def unique_experience_id(
    base_id: str,
    entry: dict[str, Any],
    *,
    index: int,
    used: set[str],
) -> str:
    if base_id not in used:
        return base_id
    fingerprint_source = json.dumps(entry, ensure_ascii=False, sort_keys=True, default=str)
    fingerprinted = f"{base_id}-{claim_digest(fingerprint_source.casefold())}"
    if fingerprinted not in used:
        return fingerprinted
    return f"{fingerprinted}-{index:04d}"


def append_field_claim(
    claims: list[dict[str, str]],
    *,
    experience_id: str,
    claim_type: str,
    text: str,
) -> None:
    if not text:
        return
    claims.append(
        atomic_claim(
            evidence_id=f"profile:experience:{experience_id}:{claim_type}",
            experience_id=experience_id,
            claim_type=claim_type,
            text=text,
        )
    )


def append_hashed_claim(
    claims: list[dict[str, str]],
    *,
    experience_id: str,
    claim_type: str,
    text: str,
) -> None:
    if not text:
        return
    evidence_id = (
        f"profile:experience:{experience_id}:{claim_type}-{claim_digest(text.casefold())}"
    )
    if any(claim["id"] == evidence_id for claim in claims):
        return
    claims.append(
        atomic_claim(
            evidence_id=evidence_id,
            experience_id=experience_id,
            claim_type=claim_type,
            text=text,
        )
    )


def atomic_claim(
    *,
    evidence_id: str,
    experience_id: str,
    claim_type: str,
    text: str,
) -> dict[str, str]:
    return {
        "id": evidence_id,
        "type": "profile",
        "claimType": claim_type,
        "experienceId": experience_id,
        "text": text,
    }


def experience_period(entry: dict[str, Any]) -> str:
    start = entry_text(entry, "start_date")
    end = entry_text(entry, "end_date")
    if bool(entry.get("is_current")):
        end = "Present"
    if start and end:
        return f"{start} — {end}"
    return start or end


def extract_technologies(entry: dict[str, Any], description: str) -> list[str]:
    technologies: list[str] = []
    seen: set[str] = set()

    def append(value: str) -> None:
        cleaned = value.strip().strip(".,;:()[]{}")
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            technologies.append(cleaned)

    for field in EXPLICIT_TECHNOLOGY_FIELDS:
        raw_value = entry.get(field)
        if isinstance(raw_value, list):
            for item in raw_value:
                if isinstance(item, str):
                    append(item)
        elif isinstance(raw_value, str):
            for item in re.split(r"[,;|\n]+", raw_value):
                append(item)

    for line in description.splitlines():
        labeled = TECHNOLOGY_LABEL_PATTERN.match(line.strip())
        if labeled:
            for item in re.split(r"[,;|]+", labeled.group(1)):
                append(item)

    for term in TECHNOLOGY_TERMS:
        match = re.search(
            rf"(?<![\w]){re.escape(term)}(?![\w])",
            description,
            flags=re.IGNORECASE,
        )
        if match:
            append(match.group(0))
    return technologies


def extract_achievements(entry: dict[str, Any], description: str) -> list[str]:
    achievements: list[str] = []
    seen: set[str] = set()

    def append(value: str) -> None:
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            achievements.append(cleaned)

    for field in EXPLICIT_ACHIEVEMENT_FIELDS:
        raw_value = entry.get(field)
        if isinstance(raw_value, list):
            for item in raw_value:
                if isinstance(item, str):
                    append(item)
        elif isinstance(raw_value, str):
            for item in split_achievements(raw_value):
                append(item)
    for achievement in split_achievements(description):
        if not TECHNOLOGY_LABEL_PATTERN.match(achievement):
            append(achievement)
    return achievements


def split_achievements(value: str) -> list[str]:
    if not value.strip():
        return []
    lines = re.split(r"\r?\n+", value)
    achievements: list[str] = []
    for line in lines:
        cleaned_line = re.sub(r"^\s*(?:[-*•▪◦]|\d+[.)])\s*", "", line).strip()
        if not cleaned_line:
            continue
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-ÞА-Я])", cleaned_line)
        achievements.extend(sentence.strip() for sentence in sentences if sentence.strip())
    return achievements


def entry_text(entry: dict[str, Any], field: str) -> str:
    return str(entry.get(field) or "").strip()


def claim_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
