from fastapi import APIRouter, HTTPException, Query, status

from app.core.settings import get_settings
from app.models.parsers import (
    IndeedSearchRequest,
    JobsChSearchRequest,
    LinkedInSearchRequest,
    ParserSearchResponse,
)
from app.services.parsers.indeed import IndeedJobsParser
from app.services.parsers.jobs_ch import JobsChParser, JobsChRequestError
from app.services.parsers.linkedin import (
    BrightDataConfigurationError,
    BrightDataRequestError,
    LinkedInJobsParser,
)

router = APIRouter()


def _indeed_parser() -> IndeedJobsParser:
    settings = get_settings()
    return IndeedJobsParser(
        api_key=settings.brightdata_api_key,
        api_url=settings.brightdata_api_url,
        dataset_id=settings.brightdata_indeed_jobs_dataset_id,
    )


def _jobs_ch_parser() -> JobsChParser:
    settings = get_settings()
    return JobsChParser(
        base_url=settings.jobs_ch_base_url,
        timeout_seconds=settings.jobs_ch_timeout_seconds,
        max_pages=settings.jobs_ch_max_pages,
        detail_workers=settings.jobs_ch_detail_workers,
    )


@router.post("/linkedin/search", response_model=ParserSearchResponse)
def search_linkedin_jobs(request: LinkedInSearchRequest) -> ParserSearchResponse:
    settings = get_settings()
    parser = LinkedInJobsParser(
        api_key=settings.brightdata_api_key,
        api_url=settings.brightdata_api_url,
        dataset_id=settings.brightdata_linkedin_jobs_dataset_id,
    )

    try:
        return parser.search(request)
    except BrightDataConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except BrightDataRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get("/linkedin/snapshots/{snapshot_id}", response_model=ParserSearchResponse)
def get_linkedin_snapshot(
    snapshot_id: str,
    results_limit: int = Query(default=100, ge=1, le=1000),
    deduplicate: bool = True,
) -> ParserSearchResponse:
    settings = get_settings()
    parser = LinkedInJobsParser(
        api_key=settings.brightdata_api_key,
        api_url=settings.brightdata_api_url,
        dataset_id=settings.brightdata_linkedin_jobs_dataset_id,
    )

    try:
        return parser.get_snapshot(
            snapshot_id,
            results_limit=results_limit,
            deduplicate=deduplicate,
        )
    except BrightDataConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except BrightDataRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/indeed/search", response_model=ParserSearchResponse)
def search_indeed_jobs(request: IndeedSearchRequest) -> ParserSearchResponse:
    try:
        return _indeed_parser().search(request)
    except BrightDataConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except BrightDataRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get("/indeed/snapshots/{snapshot_id}", response_model=ParserSearchResponse)
def get_indeed_snapshot(
    snapshot_id: str,
    results_limit: int = Query(default=100, ge=1, le=1000),
    deduplicate: bool = True,
) -> ParserSearchResponse:
    try:
        return _indeed_parser().get_snapshot(
            snapshot_id,
            results_limit=results_limit,
            deduplicate=deduplicate,
        )
    except BrightDataConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except BrightDataRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/jobs_ch/search", response_model=ParserSearchResponse)
def search_jobs_ch_jobs(request: JobsChSearchRequest) -> ParserSearchResponse:
    try:
        return _jobs_ch_parser().search(request)
    except JobsChRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
