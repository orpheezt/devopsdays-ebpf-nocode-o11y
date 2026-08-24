import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gateway_py.orders.dependencies import get_checkout_service
from gateway_py.orders.errors import (
    DownstreamError,
    DownstreamStatusError,
    DownstreamTimeoutError,
)
from gateway_py.orders.schemas import OrderResponse, OrderSummary


@pytest.fixture
def mock_checkout_service() -> AsyncMock:
    return AsyncMock()


def test_checkout_route_success(
    test_app: FastAPI,
    client: TestClient,
    mock_checkout_service: AsyncMock,
    sample_product_id: uuid.UUID,
) -> None:
    order_id = uuid.uuid4()
    mock_checkout_service.checkout.return_value = OrderResponse(
        order_id=order_id,
        customer_id="cust_123",
        summary=OrderSummary(
            subtotal=Decimal("20.00"),
            total=Decimal("17.00"),
            coupon_applied="DEVOPSDAYS",
        ),
        payment_status="confirmed",
        inventory_status="reserved",
    )

    test_app.dependency_overrides[get_checkout_service] = lambda: mock_checkout_service

    try:
        payload = {
            "customer_id": "cust_123",
            "items": [
                {
                    "product_id": str(sample_product_id),
                    "quantity": 2,
                    "unit_price": "10.00",
                }
            ],
            "coupon_code": "DEVOPSDAYS",
        }
        response = client.post("/order", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["order_id"] == str(order_id)
        assert data["customer_id"] == "cust_123"
        assert data["summary"]["subtotal"] == "20.00"
        assert data["summary"]["total"] == "17.00"
        assert data["summary"]["coupon_applied"] == "DEVOPSDAYS"
        assert data["payment_status"] == "confirmed"
        assert data["inventory_status"] == "reserved"
    finally:
        test_app.dependency_overrides.clear()


def test_checkout_route_validation_error(client: TestClient) -> None:
    # Empty items list
    payload = {
        "customer_id": "cust_123",
        "items": [],
    }
    response = client.post("/order", json=payload)
    assert response.status_code == 422


def test_checkout_route_downstream_timeout(
    test_app: FastAPI,
    client: TestClient,
    mock_checkout_service: AsyncMock,
    sample_product_id: uuid.UUID,
) -> None:
    mock_checkout_service.checkout.side_effect = DownstreamTimeoutError(
        service="payment", reason="Timeout after 5.0s"
    )

    test_app.dependency_overrides[get_checkout_service] = lambda: mock_checkout_service

    try:
        payload = {
            "customer_id": "cust_123",
            "items": [
                {
                    "product_id": str(sample_product_id),
                    "quantity": 1,
                    "unit_price": "15.00",
                }
            ],
        }
        response = client.post("/order", json=payload)

        assert response.status_code == 504
        assert response.json() == {"detail": "The request timed out. Please try again."}
    finally:
        test_app.dependency_overrides.clear()


def test_checkout_route_downstream_error(
    test_app: FastAPI,
    client: TestClient,
    mock_checkout_service: AsyncMock,
    sample_product_id: uuid.UUID,
) -> None:
    mock_checkout_service.checkout.side_effect = DownstreamError(
        service="inventory", reason="Internal server failure"
    )

    test_app.dependency_overrides[get_checkout_service] = lambda: mock_checkout_service

    try:
        payload = {
            "customer_id": "cust_123",
            "items": [
                {
                    "product_id": str(sample_product_id),
                    "quantity": 1,
                    "unit_price": "15.00",
                }
            ],
        }
        response = client.post("/order", json=payload)

        assert response.status_code == 502
        assert response.json() == {
            "detail": "The request could not be completed. Please try again."
        }
    finally:
        test_app.dependency_overrides.clear()


def test_checkout_route_downstream_client_error(
    test_app: FastAPI,
    client: TestClient,
    mock_checkout_service: AsyncMock,
    sample_product_id: uuid.UUID,
) -> None:
    mock_checkout_service.checkout.side_effect = DownstreamStatusError(
        service="inventory", reason="Insufficient stock", upstream_status=409
    )

    test_app.dependency_overrides[get_checkout_service] = lambda: mock_checkout_service

    try:
        payload = {
            "customer_id": "cust_123",
            "items": [
                {
                    "product_id": str(sample_product_id),
                    "quantity": 1,
                    "unit_price": "15.00",
                }
            ],
        }
        response = client.post("/order", json=payload)

        assert response.status_code == 409
        assert response.json() == {
            "detail": "inventory service rejected the request: Insufficient stock"
        }
    finally:
        test_app.dependency_overrides.clear()
