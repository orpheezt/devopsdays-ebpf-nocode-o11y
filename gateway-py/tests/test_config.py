from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from gateway_py.config import SettingsSection
from gateway_py.health.settings import (
    HealthSettings,
)
from gateway_py.health.settings import (
    get_settings as get_health_settings,
)
from gateway_py.modules import MODULES, install_modules
from gateway_py.orders.settings import (
    OrdersSettings,
)
from gateway_py.orders.settings import (
    get_settings as get_orders_settings,
)
from gateway_py.registry import Module


def test_settings_section_default() -> None:
    section = SettingsSection()
    assert section.enabled is True


def test_health_settings_defaults() -> None:
    settings = HealthSettings()
    assert settings.enabled is True
    assert settings.model_config.get("yaml_config_section") == "health"
    assert settings.model_config.get("env_prefix") == "HEALTH_"


def test_orders_settings_defaults() -> None:
    settings = OrdersSettings()
    assert settings.enabled is True
    assert settings.payment_url == "http://payment-go:8081"
    assert settings.inventory_url == "http://inventory-rust:8082"
    assert settings.downstream_timeout == 5.0
    assert settings.model_config.get("yaml_config_section") == "orders"
    assert settings.model_config.get("env_prefix") == "ORDER_"


def test_get_settings_lru_cache() -> None:
    health_s1 = get_health_settings()
    health_s2 = get_health_settings()
    assert health_s1 is health_s2

    orders_s1 = get_orders_settings()
    orders_s2 = get_orders_settings()
    assert orders_s1 is orders_s2


def test_install_modules_enabled_and_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    app = FastAPI()

    # Create mock settings
    enabled_settings_cls = MagicMock(return_value=MagicMock(enabled=True))
    disabled_settings_cls = MagicMock(return_value=MagicMock(enabled=False))

    router_enabled = APIRouter()

    @router_enabled.get("/enabled-path")
    def enabled_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    router_disabled = APIRouter()

    @router_disabled.get("/disabled-path")
    def disabled_endpoint() -> dict[str, str]:
        return {"status": "fail"}

    enabled_module = Module(
        name="test_enabled",
        router=router_enabled,
        settings=enabled_settings_cls,
    )
    disabled_module = Module(
        name="test_disabled",
        router=router_disabled,
        settings=disabled_settings_cls,
    )

    test_modules = (enabled_module, disabled_module)
    monkeypatch.setattr("gateway_py.modules.MODULES", test_modules)

    install_modules(app)

    client = TestClient(app)
    assert client.get("/enabled-path").status_code == 200
    assert client.get("/disabled-path").status_code == 404


def test_modules_tuple_contains_health_and_orders() -> None:
    module_names = [m.name for m in MODULES]
    assert "health" in module_names
    assert "orders" in module_names
