from pydantic import BaseModel


class HealthStatusResponse(BaseModel):
    status: str = "ok"


class ReadinessStatusResponse(BaseModel):
    status: str = "ok"
