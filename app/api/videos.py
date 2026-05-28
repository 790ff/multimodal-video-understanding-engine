from __future__ import annotations

from fastapi import APIRouter

from app.schemas import VideosModuleResponse

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("", response_model=VideosModuleResponse)
async def videos_module_status() -> VideosModuleResponse:
    return VideosModuleResponse(
        module="videos",
        status="ready",
        milestone="M1 scaffold",
    )
