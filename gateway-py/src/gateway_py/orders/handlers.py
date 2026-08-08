import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from .errors import DownstreamError, DownstreamTimeoutError

logger = logging.getLogger(__name__)


async def on_downstream_timeout(
    request: Request, exc: DownstreamTimeoutError
) -> JSONResponse:
    logger.error("downstream timeout on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={"detail": "The request timed out. Please try again."},
    )


async def on_downstream_error(request: Request, exc: DownstreamError) -> JSONResponse:
    logger.error("downstream error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": "The request could not be completed. Please try again."},
    )
