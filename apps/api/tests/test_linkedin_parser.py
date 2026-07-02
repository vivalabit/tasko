from fastapi.testclient import TestClient

from app.main import app
from app.models.parsers import LinkedInSearchRequest
from app.services.parsers.linkedin import LinkedInJobsParser


def test_linkedin_parser_builds_search_url() -> None:
    request = LinkedInSearchRequest(
        keywords="Product Designer",
        location="Europe",
        remote="Remote only",
        experience_level="Mid-Senior level",
        job_type="Full-time",
        date_posted="Past week",
        results_limit=50,
    )

    url = LinkedInJobsParser.build_search_url(request)

    assert url.startswith("https://www.linkedin.com/jobs/search/?")
    assert "keywords=Product+Designer" in url
    assert "location=Europe" in url
    assert "f_WT=2" in url
    assert "f_E=4" in url
    assert "f_JT=F" in url
    assert "f_TPR=r604800" in url


def test_linkedin_parser_normalizes_job_record() -> None:
    job = LinkedInJobsParser.normalize_job(
        {
            "job_title": "Senior Product Designer",
            "company_name": "Stripe",
            "job_location": "Remote",
            "url": "https://www.linkedin.com/jobs/view/123",
            "apply_link": "https://www.linkedin.com/jobs/view/123/apply",
            "job_employment_type": "Full-time",
            "job_seniority_level": "Mid-Senior level",
            "job_summary": "Design payment products.",
        }
    )

    assert job.title == "Senior Product Designer"
    assert job.company == "Stripe"
    assert job.location == "Remote"
    assert job.apply_url == "https://www.linkedin.com/jobs/view/123/apply"
    assert job.raw["job_title"] == "Senior Product Designer"


def test_linkedin_search_requires_brightdata_key() -> None:
    client = TestClient(app)

    response = client.post(
        "/parsers/linkedin/search",
        json={
            "keywords": "Product Designer",
            "location": "Europe",
            "remote": "Remote only",
            "experience_level": "Any",
            "job_type": "Any",
            "date_posted": "Any time",
            "results_limit": 10,
            "country": "Any",
            "deduplicate": True,
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "BRIGHTDATA_API_KEY is not configured"
