import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from gateway_py.orders.schemas import (
    CheckoutRequest,
    InventoryReserveItem,
    InventoryReserveRequest,
    OrderItem,
    OrderResponse,
    OrderSummary,
    PaymentRequest,
)


def test_order_item_valid(sample_product_id: uuid.UUID) -> None:
    item = OrderItem(
        product_id=sample_product_id,
        quantity=3,
        unit_price=Decimal("19.99"),
    )
    assert item.product_id == sample_product_id
    assert item.quantity == 3
    assert item.unit_price == Decimal("19.99")


def test_order_item_invalid_quantity(sample_product_id: uuid.UUID) -> None:
    with pytest.raises(ValidationError):
        OrderItem(
            product_id=sample_product_id,
            quantity=0,
            unit_price=Decimal("10.00"),
        )

    with pytest.raises(ValidationError):
        OrderItem(
            product_id=sample_product_id,
            quantity=-1,
            unit_price=Decimal("10.00"),
        )


def test_order_item_invalid_unit_price(sample_product_id: uuid.UUID) -> None:
    with pytest.raises(ValidationError):
        OrderItem(
            product_id=sample_product_id,
            quantity=1,
            unit_price=Decimal("0.00"),
        )

    with pytest.raises(ValidationError):
        OrderItem(
            product_id=sample_product_id,
            quantity=1,
            unit_price=Decimal("-5.00"),
        )


def test_checkout_request_valid(sample_order_item: OrderItem) -> None:
    req = CheckoutRequest(
        customer_id="cust_1",
        items=[sample_order_item],
        coupon_code="DEVOPSDAYS",
    )
    assert req.customer_id == "cust_1"
    assert len(req.items) == 1
    assert req.coupon_code == "DEVOPSDAYS"


def test_checkout_request_empty_items() -> None:
    with pytest.raises(ValidationError):
        CheckoutRequest(
            customer_id="cust_1",
            items=[],
        )


def test_payment_request_valid() -> None:
    order_id = uuid.uuid4()
    pay_req = PaymentRequest(
        order_id=order_id,
        customer_id="cust_1",
        amount=Decimal("25.50"),
    )
    assert pay_req.order_id == order_id
    assert pay_req.amount == Decimal("25.50")


def test_payment_request_invalid_amount() -> None:
    with pytest.raises(ValidationError):
        PaymentRequest(
            order_id=uuid.uuid4(),
            customer_id="cust_1",
            amount=Decimal("0.00"),
        )


def test_inventory_reserve_request_valid(sample_product_id: uuid.UUID) -> None:
    order_id = uuid.uuid4()
    item = InventoryReserveItem(product_id=sample_product_id, quantity=2)
    inv_req = InventoryReserveRequest(order_id=order_id, items=[item])
    assert inv_req.order_id == order_id
    assert len(inv_req.items) == 1


def test_inventory_reserve_request_empty_items() -> None:
    with pytest.raises(ValidationError):
        InventoryReserveRequest(order_id=uuid.uuid4(), items=[])


def test_order_summary_valid() -> None:
    summary = OrderSummary(
        subtotal=Decimal("100.00"),
        total=Decimal("85.00"),
        coupon_applied="DEVOPSDAYS",
    )
    assert summary.subtotal == Decimal("100.00")
    assert summary.total == Decimal("85.00")
    assert summary.coupon_applied == "DEVOPSDAYS"


def test_order_response_valid() -> None:
    order_id = uuid.uuid4()
    summary = OrderSummary(subtotal=Decimal("20.00"), total=Decimal("20.00"))
    resp = OrderResponse(
        order_id=order_id,
        customer_id="cust_1",
        summary=summary,
        payment_status="confirmed",
        inventory_status="reserved",
    )
    assert resp.order_id == order_id
    assert resp.payment_status == "confirmed"
    assert resp.inventory_status == "reserved"
