from functools import lru_cache

from pydantic_settings import SettingsConfigDict

from ..config import SettingsSection


class HealthSettings(SettingsSection):
    model_config = SettingsConfigDict(
        env_prefix="HEALTH_",
    )


@lru_cache
def get_settings() -> HealthSettings:
    return HealthSettings()
