from fastapi import FastAPI

from .modules import install_modules

app = FastAPI(
    title="E-Commerce API Gateway",
)

install_modules(app)
