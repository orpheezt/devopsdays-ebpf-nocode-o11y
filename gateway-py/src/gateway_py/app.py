from fastapi import FastAPI

from .modules import install_modules
from .telemetry import setup_telemetry

app = FastAPI(
    title="E-Commerce API Gateway",
)

install_modules(app)
setup_telemetry(app)
