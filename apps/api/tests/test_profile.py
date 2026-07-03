from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.profile import ProfileRecord


def test_profile_can_be_updated_and_read() -> None:
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
            "name": "Eduard Ishchenko",
            "current_role": "Frontend Engineer",
            "desired_role": "Product Engineer",
            "location": "Zurich, Switzerland",
            "work_format": "Remote / hybrid",
            "headline": "Builds polished product interfaces and pragmatic AI workflows.",
            "linkedin": "linkedin.com/in/eduard",
            "github": "github.com/eduard",
            "portfolio": "eduard.dev",
            "personal_site": "ishchenko.dev",
        }

        update_response = client.put("/profile", json=payload)
        read_response = client.get("/profile")

        assert update_response.status_code == 200
        assert update_response.json() == payload
        assert read_response.status_code == 200
        assert read_response.json() == payload

        with testing_session_local() as db:
            stored_profile = db.get(ProfileRecord, "default")
            assert stored_profile is not None
            assert stored_profile.data["name"] == "Eduard Ishchenko"
    finally:
        app.dependency_overrides.clear()
