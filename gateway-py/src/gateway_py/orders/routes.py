from fastapi import APIRouter, Request, status

from .dependencies import CheckoutServiceDep
from .schemas import CheckoutRequest, OrderResponse

router = APIRouter(tags=["orders"])


@router.post("/order", status_code=status.HTTP_201_CREATED)
async def checkout(
    order: CheckoutRequest,
    service: CheckoutServiceDep,
    request: Request,
) -> OrderResponse:
    return await service.checkout(order, headers=request.headers)
