from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class SettingsSection(BaseSettings):
    model_config = SettingsConfigDict(
        yaml_file="config.yaml",
        extra="ignore",
    )

    enabled: bool = True
