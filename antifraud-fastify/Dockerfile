# syntax=docker/dockerfile:1

ARG BUN_VERSION=1.3.14
FROM docker.io/oven/bun:${BUN_VERSION}-alpine AS base
WORKDIR /usr/src/app

FROM base AS install
RUN mkdir -p /temp/prod
COPY package.json bun.lock /temp/prod/
RUN cd /temp/prod && bun install --frozen-lockfile --production

FROM base AS final
RUN apk --no-cache add ca-certificates tzdata

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

WORKDIR /usr/src/app

COPY --from=install /temp/prod/node_modules node_modules
COPY package.json tsconfig.json ./
COPY src src

USER appuser

EXPOSE 8083

ENV PORT=8083 \
    HOST=0.0.0.0 \
    ENVIRONMENT=production

ENTRYPOINT [ "bun", "run", "src/index.ts" ]
