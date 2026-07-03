from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.parsers import router as parsers_router
from app.core.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="tasko API",
    version="0.1.0",
    description="Backend skeleton for the personal AI job search assistant.",
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
app.include_router(parsers_router, prefix="/parsers", tags=["parsers"])


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "tasko-api", "status": "ready"}
