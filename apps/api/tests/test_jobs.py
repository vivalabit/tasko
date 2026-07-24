from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.jobs import StoredJobRecord


def test_manual_jobs_can_be_upserted_but_parser_imports_require_screening() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        payload = {
            "jobs": [
                {
                    "id": "linkedin-product-designer",
                    "data": {
                        "id": "linkedin-product-designer",
                        "company": "Figma",
                        "title": "Product Designer",
                        "location": "Remote",
                        "type": "Full-time",
                        "salary": "Not specified",
                        "posted": "LinkedIn",
                        "experience": "Mid-Senior level",
                        "department": "LinkedIn import",
                        "match": 72,
                        "logo": "linkedin",
                    },
                },
                {
                    "id": "manual-job-product-designer",
                    "data": {
                        "id": "manual-job-product-designer",
                        "company": "Figma",
                        "title": "Manually added Product Designer",
                        "location": "Remote",
                        "type": "Full-time",
                        "salary": "Not specified",
                        "posted": "Today",
                        "experience": "Mid-Senior level",
                        "department": "Manual",
                        "match": 0,
                        "logo": "manual",
                    },
                }
            ]
        }

        upsert_response = client.put("/jobs", json=payload)
        read_response = client.get("/jobs")

        assert upsert_response.status_code == 200
        assert read_response.status_code == 200
        assert [item["id"] for item in read_response.json()] == [
            "manual-job-product-designer"
        ]
        assert read_response.json()[0]["data"]["title"] == (
            "Manually added Product Designer"
        )
    finally:
        app.dependency_overrides.clear()


def test_job_can_be_deleted() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        payload = {
            "jobs": [
                {
                    "id": "linkedin-product-designer",
                    "data": {
                        "id": "linkedin-product-designer",
                        "company": "Figma",
                        "title": "Product Designer",
                        "location": "Remote",
                        "type": "Full-time",
                        "salary": "Not specified",
                        "posted": "LinkedIn",
                        "experience": "Mid-Senior level",
                        "department": "LinkedIn import",
                        "match": 72,
                        "logo": "linkedin",
                    },
                }
            ]
        }

        with testing_session_local() as db:
            db.add(
                StoredJobRecord(
                    owner_id="local-owner",
                    id="linkedin-product-designer",
                    data=payload["jobs"][0]["data"],
                    status="active",
                )
            )
            db.commit()
        delete_response = client.delete("/jobs/linkedin-product-designer")
        read_response = client.get("/jobs")

        assert delete_response.status_code == 204
        assert read_response.status_code == 200
        assert read_response.json() == []

        with testing_session_local() as db:
            dismissed_job = db.get(
                StoredJobRecord,
                ("local-owner", "linkedin-product-designer"),
            )
            assert dismissed_job is not None
            assert dismissed_job.status == "dismissed"
            assert dismissed_job.dismissed_at is not None
            assert dismissed_job.data["title"] == "Product Designer"

        repeated_upsert_response = client.put("/jobs", json=payload)
        assert repeated_upsert_response.status_code == 200
        assert repeated_upsert_response.json() == []
        assert client.get("/jobs/dismissed-ids").json() == ["linkedin-product-designer"]
    finally:
        app.dependency_overrides.clear()


def test_missing_job_delete_creates_a_tombstone_that_blocks_future_upserts() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        job_id = "indeed-hidden-vacancy"
        assert client.delete(f"/jobs/{job_id}").status_code == 204
        assert client.put(
            "/jobs",
            json={"jobs": [{"id": job_id, "data": {"id": job_id, "title": "Hidden"}}]},
        ).json() == []
        assert client.get("/jobs/dismissed-ids").json() == [job_id]
    finally:
        app.dependency_overrides.clear()


def test_local_deleted_job_ids_can_be_imported_as_server_tombstones() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        response = client.put(
            "/jobs/dismissed-ids",
            json={"job_ids": ["linkedin-old-job", "linkedin-old-job", ""]},
        )
        assert response.status_code == 200
        assert response.json() == ["linkedin-old-job"]
        assert client.get("/jobs").json() == []
    finally:
        app.dependency_overrides.clear()
