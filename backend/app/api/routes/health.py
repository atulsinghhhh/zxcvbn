"""Health check endpoint."""

from fastapi import APIRouter

from app.api.schemas import HealthResponse

router = APIRouter(tags=["health"])

_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=_VERSION)
