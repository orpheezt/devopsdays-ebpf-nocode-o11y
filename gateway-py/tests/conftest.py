import uuid
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gateway_py.app import app
from gateway_py.orders.schemas import CheckoutRequest, OrderItem


@pytest.fixture
def test_app() -> FastAPI:
    """Fixture providing the main FastAPI application instance."""
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Fixture providing a TestClient instance for API route testing."""
    return TestClient(test_app)


@pytest.fixture
def sample_product_id() -> uuid.UUID:
    """Fixture providing a fixed product UUID."""
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def sample_order_item(sample_product_id: uuid.UUID) -> OrderItem:
    """Fixture providing a sample OrderItem."""
    return OrderItem(
        product_id=sample_product_id,
        quantity=2,
        unit_price=Decimal("10.00"),
    )


@pytest.fixture
def sample_checkout_request(sample_order_item: OrderItem) -> CheckoutRequest:
    """Fixture providing a sample CheckoutRequest without coupon."""
    return CheckoutRequest(
        customer_id="cust_123",
        items=[sample_order_item],
        coupon_code=None,
    )
