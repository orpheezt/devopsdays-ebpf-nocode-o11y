from collections.abc import AsyncIterator
from typing import Annotated

import httpx2
from fastapi import Depends

from .service import CheckoutService
from .settings import OrdersSettings, get_settings

CheckoutServiceConfigDep = Annotated[OrdersSettings, Depends(get_settings)]


async def get_http_client(
    settings: Annotated[OrdersSettings, Depends(get_settings)],
) -> AsyncIterator[httpx2.AsyncClient]:
    client = httpx2.AsyncClient(timeout=settings.downstream_timeout)
    try:
        yield client
    finally:
        await client.aclose()


HttpClientDep = Annotated[httpx2.AsyncClient, Depends(get_http_client)]


def get_checkout_service(
    settings: CheckoutServiceConfigDep,
    client: HttpClientDep,
) -> CheckoutService:
    return CheckoutService(settings, client)


CheckoutServiceDep = Annotated[CheckoutService, Depends(get_checkout_service)]
