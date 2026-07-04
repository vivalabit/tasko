import base64

from fastapi.testclient import TestClient

from app.core.settings import Settings, get_settings
from app.main import app
from app.services.resume_import import (
    extract_json_object,
    extract_openclaw_experience_payload,
    parse_experience_from_text,
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
