# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.14

FROM python:${PYTHON_VERSION}-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_NO_MANAGED_PYTHON=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv build --wheel --out-dir /tmp/dist

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install /tmp/dist/*.whl --target /app/app-packages --no-deps


FROM python:${PYTHON_VERSION}-slim-trixie

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/app-packages:$PYTHONPATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app-packages /app/app-packages

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

USER appuser

EXPOSE 8000

CMD ["uvicorn", "gateway_py.app:app", "--host", "0.0.0.0", "--port", "8000"]
