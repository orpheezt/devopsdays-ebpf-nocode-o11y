from decimal import Decimal
from functools import lru_cache

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from ..config import SettingsSection


class OrdersSettings(SettingsSection):
    model_config = SettingsConfigDict(
        env_prefix="ORDER_",
    )

    payment_url: str = "http://payment-go:8081"
    inventory_url: str = "http://inventory-rs:8082"
    downstream_timeout: float = Field(default=5.0, gt=0)
    coupon_code: str = "DEVOPSDAYS"
    discount_rate: Decimal = Decimal("0.15")


@lru_cache
def get_settings() -> OrdersSettings:
    return OrdersSettings()
