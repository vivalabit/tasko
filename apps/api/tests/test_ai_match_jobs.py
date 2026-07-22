import time

import pytest

from app.core.settings import Settings
from app.models.profile import ProfilePayload
from app.services import ai_match as ai_match_service
from app.services import ai_match_jobs as ai_match_jobs_service
from app.services.ai_match import OpenClawAiMatchError
from app.services.ai_match_jobs import AiMatchJobManager


def test_bulk_ai_match_continues_after_one_vacancy_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_calculate_ai_matches(
        _profile: ProfilePayload,
        jobs: list[dict],
        **_: object,
    ) -> list[dict]:
        job_ids = [str(job["id"]) for job in jobs]
        calls.append(job_ids)
        if "job-invalid" in job_ids:
            raise OpenClawAiMatchError(
                "applicationGuide.evidenceMatrix.1.importance must be required or preferred"
            )
        return jobs

    monkeypatch.setattr(
        ai_match_service,
        "calculate_ai_matches",
        fake_calculate_ai_matches,
    )
    manager = AiMatchJobManager()
    monkeypatch.setattr(
        manager,
        "_persist_job",
        lambda _session_factory, job, _profile_hash: job,
    )

    started, _ = manager.start(
        owner_id="bulk-test-owner",
        profile=ProfilePayload(),
        jobs=[
            {"id": "job-valid-1"},
            {"id": "job-invalid"},
            {"id": "job-valid-2"},
        ],
        profile_hash="a" * 64,
        candidate_snapshot={},
        settings=Settings(
            openclaw_ai_match_enabled=True,
            openclaw_ai_match_max_jobs=2,
            openclaw_ai_match_max_attempts=1,
        ),
        session_factory=lambda: None,
        force=True,
    )
    assert started is True

    for _ in range(100):
        status = manager.status("bulk-test-owner")
        if status.status in {"completed", "failed"}:
            break
        time.sleep(0.01)

    assert status.status == "completed"
    assert status.processed == status.total == 3
    assert [job.id for job in status.updated_jobs] == ["job-valid-1", "job-valid-2"]
    assert [failure.id for failure in status.failed_jobs] == ["job-invalid"]
    assert "importance" in status.failed_jobs[0].error
    assert calls == [
        ["job-valid-1", "job-invalid"],
        ["job-valid-1"],
        ["job-invalid"],
        ["job-valid-2"],
    ]


def test_background_match_pins_backend_and_model_before_thread_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deferred_threads: list[object] = []
    captured: dict[str, object] = {}

    class DeferredThread:
        def __init__(self, *, target, kwargs, daemon: bool) -> None:
            self.target = target
            self.kwargs = kwargs
            self.daemon = daemon
            deferred_threads.append(self)

        def start(self) -> None:
            return None

    def fake_calculate_ai_matches(
        _profile: ProfilePayload,
        jobs: list[dict],
        **kwargs: object,
    ) -> list[dict]:
        captured.update(kwargs)
        return jobs

    monkeypatch.setattr(ai_match_jobs_service.threading, "Thread", DeferredThread)
    monkeypatch.setattr(ai_match_service, "calculate_ai_matches", fake_calculate_ai_matches)
    manager = AiMatchJobManager()
    monkeypatch.setattr(
        manager,
        "_persist_job",
        lambda _session_factory, job, _profile_hash: job,
    )
    settings = Settings(
        ai_backend_mode="openai_api",
        openai_api_key="launch-key",
        openai_api_model="gpt-5.6-terra",
        openai_api_reasoning_effort="high",
        openclaw_ai_match_enabled=True,
        openclaw_ai_match_max_jobs=2,
    )

    started, _ = manager.start(
        owner_id="pinned-settings-owner",
        profile=ProfilePayload(),
        jobs=[{"id": "job-pinned"}],
        profile_hash="a" * 64,
        candidate_snapshot={},
        settings=settings,
        session_factory=lambda: None,
        force=True,
    )
    assert started is True
    assert len(deferred_threads) == 1

    settings.ai_backend_mode = "openclaw_codex"
    settings.openai_api_model = "changed-after-launch"
    thread = deferred_threads[0]
    thread.target(**thread.kwargs)

    assert captured["backend"].name == "openai_api"
    assert captured["model"] == "gpt-5.6-terra"
    assert captured["thinking"] == "high"
    assert manager.status("pinned-settings-owner").status == "completed"
