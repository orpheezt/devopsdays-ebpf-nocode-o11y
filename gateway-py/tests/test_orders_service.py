import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import httpx2
import pytest

from gateway_py.orders.errors import (
    DownstreamError,
    DownstreamStatusError,
    DownstreamTimeoutError,
    DownstreamTransportError,
)
from gateway_py.orders.schemas import CheckoutRequest, OrderItem
from gateway_py.orders.service import CheckoutService
from gateway_py.orders.settings import OrdersSettings


@pytest.fixture
def mock_settings() -> OrdersSettings:
    return OrdersSettings(
        payment_url="http://mock-payment:8081",
        inventory_url="http://mock-inventory:8082",
        downstream_timeout=2.0,
    )


def test_compute_summary_without_coupon(
    mock_settings: OrdersSettings, sample_product_id: uuid.UUID
) -> None:
    service = CheckoutService(settings=mock_settings, client=AsyncMock())
    order = CheckoutRequest(
        customer_id="cust_1",
        items=[
            OrderItem(
                product_id=sample_product_id, quantity=2, unit_price=Decimal("10.00")
            ),
            OrderItem(
                product_id=sample_product_id, quantity=1, unit_price=Decimal("5.50")
            ),
        ],
        coupon_code=None,
    )

    summary = service.compute_summary(order)
    assert summary.subtotal == Decimal("25.50")
    assert summary.total == Decimal("25.50")
    assert summary.coupon_applied is None


def test_compute_summary_with_devopsdays_coupon(
    mock_settings: OrdersSettings, sample_product_id: uuid.UUID
) -> None:
    service = CheckoutService(settings=mock_settings, client=AsyncMock())
    order = CheckoutRequest(
        customer_id="cust_1",
        items=[
            OrderItem(
                product_id=sample_product_id, quantity=1, unit_price=Decimal("100.00")
            ),
        ],
        coupon_code="DEVOPSDAYS",
    )

    summary = service.compute_summary(order)
    assert summary.subtotal == Decimal("100.00")
    # 100 * (1 - 0.15) = 85.00
    assert summary.total == Decimal("85.00")
    assert summary.coupon_applied == "DEVOPSDAYS"


def test_compute_summary_invalid_coupon(
    mock_settings: OrdersSettings, sample_product_id: uuid.UUID
) -> None:
    service = CheckoutService(settings=mock_settings, client=AsyncMock())
    order = CheckoutRequest(
        customer_id="cust_1",
        items=[
            OrderItem(
                product_id=sample_product_id, quantity=1, unit_price=Decimal("100.00")
            ),
        ],
        coupon_code="INVALID_CODE",
    )

    summary = service.compute_summary(order)
    assert summary.subtotal == Decimal("100.00")
    assert summary.total == Decimal("100.00")
    assert summary.coupon_applied is None


@pytest.mark.anyio
async def test_checkout_success(
    mock_settings: OrdersSettings, sample_checkout_request: CheckoutRequest
) -> None:
    mock_client = AsyncMock(spec=httpx2.AsyncClient)
    pay_resp = MagicMock(spec=httpx2.Response)
    pay_resp.raise_for_status.return_value = None
    inv_resp = MagicMock(spec=httpx2.Response)
    inv_resp.raise_for_status.return_value = None

    mock_client.post.side_effect = [pay_resp, inv_resp]

    service = CheckoutService(settings=mock_settings, client=mock_client)
    res = await service.checkout(sample_checkout_request)

    assert res.customer_id == "cust_123"
    assert res.payment_status == "confirmed"
    assert res.inventory_status == "reserved"
    assert mock_client.post.call_count == 2


@pytest.mark.anyio
async def test_checkout_payment_timeout(
    mock_settings: OrdersSettings, sample_checkout_request: CheckoutRequest
) -> None:
    mock_client = AsyncMock(spec=httpx2.AsyncClient)
    req = httpx2.Request("POST", "http://mock-payment:8081/pay")
    timeout_exc = httpx2.TimeoutException("Payment connection timed out", request=req)
    inv_resp = MagicMock(spec=httpx2.Response)
    inv_resp.raise_for_status.return_value = None

    mock_client.post.side_effect = [timeout_exc, inv_resp]

    service = CheckoutService(settings=mock_settings, client=mock_client)
    with pytest.raises(DownstreamTimeoutError) as exc_info:
        await service.checkout(sample_checkout_request)

    assert exc_info.value.service == "payment"


@pytest.mark.anyio
async def test_checkout_inventory_status_error(
    mock_settings: OrdersSettings, sample_checkout_request: CheckoutRequest
) -> None:
    mock_client = AsyncMock(spec=httpx2.AsyncClient)
    pay_resp = MagicMock(spec=httpx2.Response)
    pay_resp.raise_for_status.return_value = None

    req = httpx2.Request("POST", "http://mock-inventory:8082/reserve")
    resp = httpx2.Response(status_code=500, request=req)
    inv_resp = MagicMock(spec=httpx2.Response)
    inv_resp.raise_for_status.side_effect = httpx2.HTTPStatusError(
        "500 Server Error", request=req, response=resp
    )

    mock_client.post.side_effect = [pay_resp, inv_resp]

    service = CheckoutService(settings=mock_settings, client=mock_client)
    with pytest.raises(DownstreamStatusError) as exc_info:
        await service.checkout(sample_checkout_request)

    assert exc_info.value.service == "inventory"
    assert exc_info.value.upstream_status == 500


def test_map_error_variants() -> None:
    req = httpx2.Request("POST", "http://example.com")
    resp = httpx2.Response(status_code=404, request=req)

    # DownstreamError pass-through
    existing = DownstreamError(service="payment", reason="custom")
    assert CheckoutService._map_error("payment", existing) is existing

    # TimeoutException -> DownstreamTimeoutError
    timeout_exc = httpx2.TimeoutException("timeout", request=req)
    mapped_timeout = CheckoutService._map_error("payment", timeout_exc)
    assert isinstance(mapped_timeout, DownstreamTimeoutError)
    assert mapped_timeout.service == "payment"

    # HTTPStatusError -> DownstreamStatusError
    status_exc = httpx2.HTTPStatusError("404", request=req, response=resp)
    mapped_status = CheckoutService._map_error("inventory", status_exc)
    assert isinstance(mapped_status, DownstreamStatusError)
    assert mapped_status.service == "inventory"
    assert mapped_status.upstream_status == 404

    # RequestError -> DownstreamTransportError
    req_exc = httpx2.RequestError("connection failed", request=req)
    mapped_req = CheckoutService._map_error("payment", req_exc)
    assert isinstance(mapped_req, DownstreamTransportError)
    assert mapped_req.service == "payment"

    # General Exception -> DownstreamError
    gen_exc = RuntimeError("unknown failure")
    mapped_gen = CheckoutService._map_error("payment", gen_exc)
    assert isinstance(mapped_gen, DownstreamError)
    assert mapped_gen.service == "payment"
