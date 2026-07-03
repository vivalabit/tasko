from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app


def test_jobs_can_be_upserted_and_read() -> None:
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

        upsert_response = client.put("/jobs", json=payload)
        read_response = client.get("/jobs")

        assert upsert_response.status_code == 200
        assert read_response.status_code == 200
        assert read_response.json()[0]["id"] == "linkedin-product-designer"
        assert read_response.json()[0]["data"]["title"] == "Product Designer"
    finally:
        app.dependency_overrides.clear()
