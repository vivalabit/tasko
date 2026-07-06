from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.parsers import router as parsers_router
from app.api.profile import router as profile_router
from app.api.settings import router as settings_router
from app.core.database import init_db
from app.core.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        init_db()
    except SQLAlchemyError:
        pass

    yield


app = FastAPI(
    title="tasko API",
    version="0.1.0",
    description="Backend skeleton for the personal AI job search assistant.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
app.include_router(parsers_router, prefix="/parsers", tags=["parsers"])
app.include_router(profile_router, prefix="/profile", tags=["profile"])
app.include_router(settings_router, prefix="/settings", tags=["settings"])


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "tasko-api", "status": "ready"}
