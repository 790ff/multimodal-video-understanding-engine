from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.videos import router as videos_router
from app.config import ensure_runtime_dirs, get_settings
from app.domain.errors import AppError
from app.schemas import HealthResponse


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    ensure_runtime_dirs()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend API for the Multimodal Video Understanding Engine MVP.",
        lifespan=lifespan,
    )

    @application.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    async def health_check() -> HealthResponse:
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
        )

    application.include_router(videos_router)
    return application


app = create_app()
