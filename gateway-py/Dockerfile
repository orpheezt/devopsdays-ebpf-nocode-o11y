# syntax=docker/dockerfile:1

FROM docker.io/bellsoft/alpaquita-linux-base:stream-glibc AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.2 /uv /uvx /bin/

RUN apk add --no-cache python3 py3-pip

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_NO_MANAGED_PYTHON=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY uv.lock pyproject.toml ./
RUN uv sync --locked --no-install-project --no-dev

COPY . /app
RUN uv build --wheel --out-dir /tmp/dist && \
    uv pip install /tmp/dist/*.whl --target /app/app-packages --no-deps

FROM docker.io/bellsoft/alpaquita-linux-base:stream-glibc AS final

RUN apk add --no-cache python3 ca-certificates tzdata

ARG UID=10001
RUN adduser -u ${UID} -D -s /sbin/nologin appuser

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/app-packages:$PYTHONPATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app-packages /app/app-packages

USER appuser

EXPOSE 8000

CMD ["uvicorn", "gateway_py.app:app", "--host", "0.0.0.0", "--port", "8000"]
