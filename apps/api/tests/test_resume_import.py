import base64

from fastapi.testclient import TestClient

from app.core.settings import Settings, get_settings
from app.main import app
from app.services.resume_import import (
    extract_json_object,
    extract_openclaw_education_payload,
    extract_openclaw_experience_payload,
    parse_education_from_text,
    parse_experience_from_text,
    parse_skills_from_text,
)


def test_parse_experience_from_resume_text() -> None:
    entries = parse_experience_from_text(
        """
        PROFESSIONAL EXPERIENCE
        Senior Frontend Engineer | Tasko Labs | Jan 2024 - Present | Zurich, Switzerland
        Built job matching dashboards and profile workflows.
        Improved resume onboarding for candidates.

        Software Developer at Bright Apps
        Mar 2021 - Dec 2023
        Developed React and FastAPI features for internal tools.

        EDUCATION
        Computer Science
        """
    )

    assert len(entries) == 2
    assert entries[0].title == "Senior Frontend Engineer"
    assert entries[0].company == "Tasko Labs"
    assert entries[0].start_date == "2024-01"
    assert entries[0].is_current is True
    assert "profile workflows" in entries[0].description
    assert entries[1].title == "Software Developer"
    assert entries[1].company == "Bright Apps"
    assert entries[1].end_date == "2023-12"


def test_parse_education_from_resume_text() -> None:
    entries = parse_education_from_text(
        """
        PROFESSIONAL EXPERIENCE
        Python Developer | Alpine Systems | 2022 - Present
        Built API integrations.

        EDUCATION & CERTIFICATIONS
        ETH Zurich | Master of Science | Computer Science | Sep 2020 - Jun 2022 | Zurich, Switzerland
        Coursework: distributed systems and machine learning.

        AWS Certified Developer at Amazon Web Services
        2024 - 2024

        SKILLS
        Python, FastAPI
        """
    )

    assert len(entries) == 2
    assert entries[0].institution == "ETH Zurich"
    assert entries[0].credential == "Master of Science"
    assert entries[0].field_of_study == "Computer Science"
    assert entries[0].start_date == "2020-09"
    assert entries[0].end_date == "2022-06"
    assert "distributed systems" in entries[0].description
    assert entries[1].institution == "Amazon Web Services"
    assert entries[1].credential == "AWS Certified Developer"


def test_parse_skills_from_resume_text_deduplicates_case_insensitive() -> None:
    skills = parse_skills_from_text(
        """
        PROFESSIONAL EXPERIENCE
        Python Developer | Alpine Systems | 2022 - Present
        Built API integrations.

        Technical Skills
        Languages: Python, JavaScript, python
        Frameworks: FastAPI, React, Next.js
        Tools: Docker, GitHub Actions, CI/CD

        EDUCATION
        University of Zurich
        """
    )

    assert skills == [
        "Python",
        "JavaScript",
        "FastAPI",
        "React",
        "Next.js",
        "Docker",
        "GitHub Actions",
        "CI/CD",
    ]


def test_import_experience_endpoint_reads_attached_resume_data() -> None:
    resume_text = """
    Work Experience
    Python Developer | Alpine Systems | 2022 - Present
    Automated reporting pipelines and built API integrations.
    Skills
    Python, FastAPI
    """
    encoded_resume = base64.b64encode(resume_text.encode()).decode()
    client = TestClient(app)

    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_resume_import_enabled=False)

    try:
        response = client.post(
            "/profile/import-experience-from-resume",
            json={
                "resume_file_name": "eduard-resume.pdf",
                "resume_data_url": f"data:application/pdf;base64,{encoded_resume}",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["experience"][0]["title"] == "Python Developer"
    assert payload["experience"][0]["company"] == "Alpine Systems"
    assert payload["experience"][0]["is_current"] is True


def test_import_education_endpoint_reads_attached_resume_data() -> None:
    resume_text = """
    Work Experience
    Python Developer | Alpine Systems | 2022 - Present
    Automated reporting pipelines.

    Education
    University of Zurich | Bachelor of Science | Informatics | 2018 - 2021
    Certificates
    """
    encoded_resume = base64.b64encode(resume_text.encode()).decode()
    client = TestClient(app)

    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_resume_import_enabled=False)

    try:
        response = client.post(
            "/profile/import-education-from-resume",
            json={
                "resume_file_name": "eduard-resume.pdf",
                "resume_data_url": f"data:application/pdf;base64,{encoded_resume}",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["education"][0]["institution"] == "University of Zurich"
    assert payload["education"][0]["credential"] == "Bachelor of Science"
    assert payload["education"][0]["field_of_study"] == "Informatics"


def test_import_skills_endpoint_reads_attached_resume_data() -> None:
    resume_text = """
    Work Experience
    Python Developer | Alpine Systems | 2022 - Present
    Automated reporting pipelines.

    Skills
    Python, FastAPI, Docker, PostgreSQL, Python

    Education
    University of Zurich
    """
    encoded_resume = base64.b64encode(resume_text.encode()).decode()
    client = TestClient(app)

    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_resume_import_enabled=False)

    try:
        response = client.post(
            "/profile/import-skills-from-resume",
            json={
                "resume_file_name": "eduard-resume.pdf",
                "resume_data_url": f"data:application/pdf;base64,{encoded_resume}",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["skills"] == ["Python", "FastAPI", "Docker", "PostgreSQL"]


def test_extract_json_object_reads_openclaw_json_output() -> None:
    payload = extract_json_object(
        """
        Here is the JSON:
        ```json
        {"experience":[]}
        ```
        """
    )

    assert payload == {"experience": []}


def test_extract_openclaw_experience_payload_reads_json_result_wrapper() -> None:
    payload = extract_openclaw_experience_payload(
        """
        [plugins] warning with config example {"plugins":{"allow":["codex"]}}
        {
          "status": "ok",
          "result": {
            "payloads": [
              {"text": "{\\"experience\\":[{\\"title\\":\\"Developer\\",\\"company\\":\\"Tasko\\",\\"employment_type\\":\\"Full-time\\",\\"location\\":\\"\\",\\"start_date\\":\\"2024-01\\",\\"end_date\\":\\"\\",\\"is_current\\":true,\\"description\\":\\"Built imports.\\"}]}"}
            ]
          }
        }
        """
    )

    assert payload["experience"][0]["title"] == "Developer"


def test_extract_openclaw_education_payload_reads_json_result_wrapper() -> None:
    payload = extract_openclaw_education_payload(
        """
        [plugins] warning with config example {"plugins":{"allow":["codex"]}}
        {
          "status": "ok",
          "result": {
            "payloads": [
              {"text": "{\\"education\\":[{\\"institution\\":\\"Tasko University\\",\\"credential\\":\\"Certificate\\",\\"field_of_study\\":\\"AI\\",\\"location\\":\\"\\",\\"start_date\\":\\"2024-01\\",\\"end_date\\":\\"2024-12\\",\\"is_current\\":false,\\"description\\":\\"Built imports.\\"}]}"}
            ]
          }
        }
        """
    )

    assert payload["education"][0]["institution"] == "Tasko University"
