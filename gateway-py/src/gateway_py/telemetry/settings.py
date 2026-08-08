from functools import lru_cache

from pydantic_settings import SettingsConfigDict

from ..config import SettingsSection


class TelemetrySettings(SettingsSection):
    model_config = SettingsConfigDict(
        yaml_config_section="telemetry",
        env_prefix="OTEL_",
    )

    service_name: str = "gateway-py"
    exporter_otlp_endpoint: str | None = None
    traces_enabled: bool = True
    metrics_enabled: bool = True
    logs_enabled: bool = True


@lru_cache
def get_settings() -> TelemetrySettings:
    return TelemetrySettings()
