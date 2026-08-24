# syntax=docker/dockerfile:1

ARG BUN_VERSION=1.4.0
FROM docker.io/oven/bun:${BUN_VERSION} AS build
WORKDIR /app

COPY package.json bun.lock tsconfig.json ./
RUN bun install --frozen-lockfile --production

COPY src src

FROM docker.io/oven/bun:${BUN_VERSION}-distroless AS final
WORKDIR /app

COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/tsconfig.json ./tsconfig.json
COPY --from=build /app/src ./src

EXPOSE 8083

ENV PORT=8083 \
    HOST=0.0.0.0 \
    ENVIRONMENT=production

ENTRYPOINT [ "bun", "run", "src/index.ts" ]
