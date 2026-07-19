import json

from app.services.experience_evidence import build_atomic_experience_evidence


def test_emits_atomic_claims_for_structured_experience() -> None:
    experience = json.dumps(
        [
            {
                "id": "experience-acme-2022",
                "company": "Acme AG",
                "title": "Platform Engineer",
                "start_date": "2022-01",
                "end_date": "",
                "is_current": True,
                "technologies": ["Python", "FastAPI"],
                "description": (
                    "Built Python and FastAPI services for enterprise customers. "
                    "Reduced API latency by 30%."
                ),
            }
        ]
    )

    first = build_atomic_experience_evidence(experience)
    second = build_atomic_experience_evidence(experience)
    by_type: dict[str, list[dict[str, str]]] = {}
    for claim in first:
        by_type.setdefault(claim["claimType"], []).append(claim)

    assert first == second
    assert all(claim["type"] == "profile" for claim in first)
    assert all(claim["experienceId"] == "experience-acme-2022" for claim in first)
    assert all(claim["id"].startswith("profile:experience:experience-acme-2022:") for claim in first)
    assert "profile:experience" not in {claim["id"] for claim in first}
    assert [claim["text"] for claim in by_type["employer"]] == ["Acme AG"]
    assert [claim["text"] for claim in by_type["title"]] == ["Platform Engineer"]
    assert [claim["text"] for claim in by_type["period"]] == ["2022-01 — Present"]
    assert {claim["text"] for claim in by_type["technology"]} == {
        "Python",
        "FastAPI",
    }
    assert [claim["text"] for claim in by_type["achievement"]] == [
        "Built Python and FastAPI services for enterprise customers.",
        "Reduced API latency by 30%.",
    ]
    assert all(
        ":technology-" in claim["id"]
        for claim in by_type["technology"]
    )
    assert all(
        ":achievement-" in claim["id"]
        for claim in by_type["achievement"]
    )


def test_legacy_experience_is_split_into_atomic_achievements_and_technologies() -> None:
    claims = build_atomic_experience_evidence(
        "- Built a Python API.\n- Deployed it with Docker and Kubernetes."
    )

    assert [claim["claimType"] for claim in claims].count("achievement") == 2
    assert {claim["text"] for claim in claims if claim["claimType"] == "technology"} == {
        "Python",
        "Docker",
        "Kubernetes",
    }
    assert all(claim["id"] != "profile:experience" for claim in claims)


def test_missing_entry_id_uses_content_fingerprint_instead_of_list_position() -> None:
    entry = {
        "company": "Example",
        "title": "Engineer",
        "start_date": "2020-01",
        "description": "Built a service.",
    }
    original = build_atomic_experience_evidence([entry])
    reordered = build_atomic_experience_evidence(
        [
            {"id": "another", "description": "Unrelated achievement."},
            entry,
        ]
    )

    original_ids = {claim["id"] for claim in original}
    reordered_entry_ids = {
        claim["id"]
        for claim in reordered
        if claim["text"] in {"Example", "Engineer", "2020-01", "Built a service."}
    }
    assert reordered_entry_ids == original_ids


def test_labeled_technology_stack_is_atomic_and_not_an_achievement() -> None:
    claims = build_atomic_experience_evidence(
        [
            {
                "id": "elixir-role",
                "description": (
                    "Tech stack: Elixir, Phoenix, OTP\n"
                    "Improved service reliability."
                ),
            }
        ]
    )

    assert {claim["text"] for claim in claims if claim["claimType"] == "technology"} == {
        "Elixir",
        "Phoenix",
        "OTP",
    }
    assert [claim["text"] for claim in claims if claim["claimType"] == "achievement"] == [
        "Improved service reliability."
    ]


def test_duplicate_experience_ids_do_not_collide() -> None:
    claims = build_atomic_experience_evidence(
        [
            {"id": "duplicate", "company": "First", "description": "Built one service."},
            {"id": "duplicate", "company": "Second", "description": "Built another service."},
        ]
    )

    evidence_ids = [claim["id"] for claim in claims]
    assert len(evidence_ids) == len(set(evidence_ids))
    assert len({claim["experienceId"] for claim in claims}) == 2
