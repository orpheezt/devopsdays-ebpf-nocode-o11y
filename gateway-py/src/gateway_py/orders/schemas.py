from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: UUID
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0, decimal_places=2)


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    customer_id: str
    items: list[OrderItem] = Field(min_length=1)
    coupon_code: str | None = None


class PaymentRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_id: UUID
    customer_id: str
    amount: float = Field(..., gt=0)


class InventoryReserveItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: UUID
    quantity: int = Field(..., gt=0)


class InventoryReserveRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_id: UUID
    items: list[InventoryReserveItem] = Field(min_length=1)


class OrderSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    subtotal: Decimal = Field(..., gt=0, decimal_places=2)
    total: Decimal = Field(..., gt=0, decimal_places=2)
    coupon_applied: str | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_id: UUID
    customer_id: str
    summary: OrderSummary
    payment_status: str
    inventory_status: str
