# syntax=docker/dockerfile:1

ARG RUST_VERSION=1.97.1
ARG APP_NAME=favsound
ARG ALPINE_VERSION=3.24
ARG PORT=8082

FROM rust:${RUST_VERSION}-alpine AS build
ARG APP_NAME
WORKDIR /app

RUN apk add --no-cache clang lld musl-dev git

RUN --mount=type=bind,source=src,target=src \
    --mount=type=bind,source=Cargo.toml,target=Cargo.toml \
    --mount=type=bind,source=Cargo.lock,target=Cargo.lock \
    --mount=type=bind,source=.sqlx,target=.sqlx \
    --mount=type=cache,target=/app/target/ \
    --mount=type=cache,target=/usr/local/cargo/git/db \
    --mount=type=cache,target=/usr/local/cargo/registry/ \
    SQLX_OFFLINE=true cargo build --locked --release && \
    cp ./target/release/${APP_NAME} /bin/server

FROM alpine:${ALPINE_VERSION} AS final

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser
USER appuser

COPY --from=build /bin/server /bin/

EXPOSE ${PORT}

CMD ["/bin/server"]