from fastapi import APIRouter

from .schemas import HealthStatusResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> HealthStatusResponse:
    return HealthStatusResponse()
