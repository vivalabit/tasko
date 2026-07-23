from datetime import UTC, datetime, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.identity import current_owner_id
from app.models.job_search import (
    JobSearchConfigRecord,
    JobSearchRunRecord,
    JobSearchScheduleRecord,
)


def test_job_search_records_are_owner_scoped_and_prevent_duplicate_automatic_runs() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    scheduled_for = datetime(2026, 7, 27, 6, 30, tzinfo=UTC)

    owner_token = current_owner_id.set("owner-a")
    try:
        with Session(engine) as db:
            config = JobSearchConfigRecord(
                name="Zurich product roles",
                filters={"query": "Product Manager", "location": "Zurich"},
            )
            schedule = JobSearchScheduleRecord(
                name="Weekday morning search",
                config=config,
                sources=["linkedin", "jobs_ch"],
                frequency="weekly",
                weekdays=[1, 2, 3, 4, 5],
                local_time=time(7, 30),
                timezone="Europe/Zurich",
                ai_analysis_enabled=True,
                enabled=True,
                next_run_at=scheduled_for,
            )
            db.add(schedule)
            db.flush()
            schedule_id = schedule.id
            db.add_all(
                [
                    JobSearchRunRecord(
                        schedule_id=schedule_id,
                        run_type="automatic",
                        scheduled_for=scheduled_for,
                        config_snapshot={
                            "name": config.name,
                            "filters": config.filters,
                        },
                        sources=list(schedule.sources),
                        status="completed",
                        jobs_found=12,
                        jobs_added=7,
                        source_errors={},
                        completed_at=datetime.now(UTC),
                    ),
                    JobSearchRunRecord(
                        schedule_id=schedule_id,
                        run_type="manual",
                        scheduled_for=scheduled_for,
                        config_snapshot={"filters": config.filters},
                        sources=list(schedule.sources),
                        status="completed",
                    ),
                    JobSearchRunRecord(
                        schedule_id=schedule_id,
                        run_type="manual",
                        scheduled_for=scheduled_for,
                        config_snapshot={"filters": config.filters},
                        sources=list(schedule.sources),
                        status="completed",
                    ),
                ]
            )
            db.commit()

        with Session(engine) as db:
            db.add(
                JobSearchRunRecord(
                    schedule_id=schedule_id,
                    run_type="automatic",
                    scheduled_for=scheduled_for,
                    config_snapshot={"filters": {}},
                    sources=["linkedin"],
                    status="queued",
                )
            )
            with pytest.raises(IntegrityError):
                db.commit()
    finally:
        current_owner_id.reset(owner_token)

    owner_token = current_owner_id.set("owner-b")
    try:
        with Session(engine) as db:
            db.add(JobSearchConfigRecord(name="Owner B search", filters={}))
            db.commit()
            assert [config.name for config in db.query(JobSearchConfigRecord).all()] == [
                "Owner B search"
            ]
            assert db.query(JobSearchScheduleRecord).all() == []
            assert db.query(JobSearchRunRecord).all() == []
    finally:
        current_owner_id.reset(owner_token)
