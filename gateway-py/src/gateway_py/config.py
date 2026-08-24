from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class SettingsSection(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
    )

    enabled: bool = True
