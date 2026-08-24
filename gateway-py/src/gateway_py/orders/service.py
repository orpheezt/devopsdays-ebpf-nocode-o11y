import asyncio
import logging
import uuid
from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal

import httpx2

from .errors import (
    DownstreamError,
    DownstreamStatusError,
    DownstreamTimeoutError,
    DownstreamTransportError,
)
from .schemas import (
    CheckoutRequest,
    InventoryReserveItem,
    InventoryReserveRequest,
    OrderResponse,
    OrderSummary,
    PaymentRequest,
)
from .settings import OrdersSettings

logger = logging.getLogger(__name__)


class CheckoutService:
    def __init__(self, settings: OrdersSettings, client: httpx2.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    def compute_summary(self, order: CheckoutRequest) -> OrderSummary:
        subtotal = sum(
            (item.unit_price * item.quantity for item in order.items),
            start=Decimal(0),
        )
        subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        discount = (
            self._settings.discount_rate
            if order.coupon_code == self._settings.coupon_code
            else Decimal(0)
        )
        total = (subtotal * (Decimal(1) - discount)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return OrderSummary(
            subtotal=subtotal,
            total=total,
            coupon_applied=order.coupon_code if discount else None,
        )

    async def checkout(
        self,
        order: CheckoutRequest,
        headers: Mapping[str, str] | None = None,
    ) -> OrderResponse:
        order_id = uuid.uuid7()
        summary = self.compute_summary(order)
        logger.info(
            "checkout started: order=%s customer=%s items=%d subtotal=%s total=%s",
            order_id,
            order.customer_id,
            len(order.items),
            summary.subtotal,
            summary.total,
        )

        payment_payload = PaymentRequest(
            order_id=order_id,
            customer_id=order.customer_id,
            amount=summary.total,
        ).model_dump(mode="json")

        inventory_payload = InventoryReserveRequest(
            order_id=order_id,
            items=[
                InventoryReserveItem(
                    product_id=item.product_id,
                    quantity=item.quantity,
                )
                for item in order.items
            ],
        ).model_dump(mode="json")

        forward_headers: dict[str, str] = {}
        if headers:
            for key in (
                "traceparent",
                "tracestate",
                "baggage",
                "x-request-id",
                "x-b3-traceid",
                "x-b3-spanid",
                "x-b3-sampled",
            ):
                if key in headers:
                    forward_headers[key] = headers[key]

        pay_task = self._client.post(
            f"{self._settings.payment_url}/pay",
            json=payment_payload,
            headers=forward_headers,
        )
        inv_task = self._client.post(
            f"{self._settings.inventory_url}/reserve",
            json=inventory_payload,
            headers=forward_headers,
        )

        results = await asyncio.gather(pay_task, inv_task, return_exceptions=True)

        for service, result in zip(("payment", "inventory"), results):
            if isinstance(result, BaseException):
                logger.warning(
                    "checkout %s: downstream %s failed",
                    order_id,
                    service,
                    exc_info=result,
                )
                raise self._map_error(service, result) from result
            try:
                result.raise_for_status()
            except httpx2.HTTPError as exc:
                logger.warning(
                    "checkout %s: downstream %s returned error",
                    order_id,
                    service,
                    exc_info=exc,
                )
                raise self._map_error(service, exc) from exc

        response = OrderResponse(
            order_id=order_id,
            customer_id=order.customer_id,
            summary=summary,
            payment_status="confirmed",
            inventory_status="reserved",
        )
        logger.info(
            "checkout completed: order=%s payment_status=%s inventory_status=%s",
            order_id,
            response.payment_status,
            response.inventory_status,
        )
        return response

    @staticmethod
    def _map_error(service: str, exc: BaseException) -> DownstreamError:
        match exc:
            case DownstreamError():
                return exc
            case httpx2.TimeoutException():
                return DownstreamTimeoutError(service=service, reason=str(exc))
            case httpx2.HTTPStatusError() as status_exc:
                reason = str(status_exc)
                try:
                    data = status_exc.response.json()
                    if isinstance(data, dict):
                        reason = (
                            data.get("error") or data.get("detail") or str(status_exc)
                        )
                except (ValueError, KeyError, TypeError, httpx2.DecodingError):
                    if status_exc.response.text:
                        reason = status_exc.response.text
                return DownstreamStatusError(
                    service=service,
                    reason=str(reason),
                    upstream_status=status_exc.response.status_code,
                )
            case httpx2.RequestError():
                return DownstreamTransportError(service=service, reason=str(exc))
            case _:
                return DownstreamError(service=service, reason=str(exc))
