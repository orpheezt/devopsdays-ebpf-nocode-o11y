from ..registry import Module
from .routes import router
from .settings import HealthSettings

MODULE: Module = Module(
    name="health",
    router=router,
    settings=HealthSettings,
)

__all__ = ["MODULE"]
