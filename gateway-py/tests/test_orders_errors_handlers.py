from unittest.mock import MagicMock

import pytest
from fastapi import Request

from gateway_py.orders.errors import (
    DownstreamError,
    DownstreamStatusError,
    DownstreamTimeoutError,
    DownstreamTransportError,
)
from gateway_py.orders.handlers import on_downstream_error, on_downstream_timeout


def test_downstream_error_formatting_without_status() -> None:
    err = DownstreamError(service="payment", reason="connection refused")
    assert str(err) == "downstream service 'payment' failed: connection refused"
    assert err.service == "payment"
    assert err.reason == "connection refused"
    assert err.upstream_status is None


def test_downstream_error_formatting_with_status() -> None:
    err = DownstreamStatusError(
        service="inventory", reason="not found", upstream_status=404
    )
    assert str(err) == "downstream service 'inventory' failed: not found (status 404)"
    assert err.service == "inventory"
    assert err.reason == "not found"
    assert err.upstream_status == 404


def test_downstream_error_subclasses() -> None:
    timeout_err = DownstreamTimeoutError(service="payment", reason="timeout")
    assert isinstance(timeout_err, DownstreamError)

    transport_err = DownstreamTransportError(service="payment", reason="network down")
    assert isinstance(transport_err, DownstreamError)


@pytest.mark.anyio
async def test_on_downstream_timeout_handler() -> None:
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = "/order"

    exc = DownstreamTimeoutError(service="payment", reason="timed out after 5s")
    response = await on_downstream_timeout(mock_request, exc)

    assert response.status_code == 504
    assert response.body == b'{"detail":"The request timed out. Please try again."}'


@pytest.mark.anyio
async def test_on_downstream_error_handler() -> None:
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = "/order"

    # Generic downstream error -> 502
    exc_generic = DownstreamError(service="inventory", reason="internal failure")
    response_generic = await on_downstream_error(mock_request, exc_generic)
    assert response_generic.status_code == 502
    assert (
        response_generic.body
        == b'{"detail":"The request could not be completed. Please try again."}'
    )

    # 4xx DownstreamStatusError -> propagates 4xx status with detail
    exc_4xx = DownstreamStatusError(
        service="inventory", reason="out of stock", upstream_status=400
    )
    response_4xx = await on_downstream_error(mock_request, exc_4xx)
    assert response_4xx.status_code == 400
    assert (
        response_4xx.body
        == b'{"detail":"inventory service rejected the request: out of stock"}'
    )

    # 5xx DownstreamStatusError -> 502
    exc_5xx = DownstreamStatusError(
        service="payment", reason="internal server error", upstream_status=500
    )
    response_5xx = await on_downstream_error(mock_request, exc_5xx)
    assert response_5xx.status_code == 502
    assert (
        response_5xx.body
        == b'{"detail":"The request could not be completed. Please try again."}'
    )
