from fastapi import APIRouter

from .schemas import HealthStatusResponse, ReadinessStatusResponse

router = APIRouter(tags=["health"])


@router.get("/livez")
async def livez() -> HealthStatusResponse:
    return HealthStatusResponse()


@router.get("/readyz")
async def readyz() -> ReadinessStatusResponse:
    return ReadinessStatusResponse()
