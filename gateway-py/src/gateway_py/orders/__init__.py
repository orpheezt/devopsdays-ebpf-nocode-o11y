from ..registry import Module
from .errors import DownstreamError, DownstreamTimeoutError
from .handlers import on_downstream_error, on_downstream_timeout
from .routes import router
from .settings import OrdersSettings

MODULE: Module = Module(
    name="orders",
    router=router,
    settings=OrdersSettings,
    exception_handlers={
        DownstreamTimeoutError: on_downstream_timeout,
        DownstreamError: on_downstream_error,
    },
)

__all__ = ["MODULE"]
