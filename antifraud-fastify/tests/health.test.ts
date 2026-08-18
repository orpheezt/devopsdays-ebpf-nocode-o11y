import { afterAll, beforeAll, describe, expect, it } from "bun:test";
import type { FastifyInstance } from "fastify";
import type { Redis } from "ioredis";
import type { StartedTestContainer } from "testcontainers";
import { buildApp } from "../src/app.js";
import { loadConfig } from "../src/config/config.js";
import { createRedisClient } from "../src/db/redis.js";
import { startRedisContainer } from "./testcontainer-redis.js";

describe("Health Routes Tests (Testcontainers redis:8.10-alpine3.23)", () => {
  let redisContainer: StartedTestContainer;
  let redisClient: Redis;
  let app: FastifyInstance;

  beforeAll(async () => {
    const started = await startRedisContainer();
    redisContainer = started.container;
    redisClient = started.redisClient;

    const config = {
      ...loadConfig(),
      redisUrl: started.redisUrl,
      environment: "test" as const,
      logLevel: "silent",
    };

    app = buildApp({ config, redisClient });
  }, 120000);

  afterAll(async () => {
    if (app) {
      await app.close();
    }
    if (redisClient) {
      await redisClient.quit().catch(() => {});
    }
    if (redisContainer) {
      await redisContainer.stop();
    }
  });

  it("GET /livez should return 200 OK with status ok", async () => {
    const response = await app.inject({
      method: "GET",
      url: "/livez",
    });

    expect(response.statusCode).toBe(200);
    expect(JSON.parse(response.body)).toEqual({ status: "ok" });
  });

  it("GET /readyz should return 200 OK when Redis 8.10 is connected", async () => {
    const response = await app.inject({
      method: "GET",
      url: "/readyz",
    });

    expect(response.statusCode).toBe(200);
    expect(JSON.parse(response.body)).toEqual({
      status: "ok",
      redis: "connected",
    });
  });

  it("GET /readyz should return 503 Service Unavailable when Redis is unreachable", async () => {
    const disconnectedRedis = createRedisClient({
      host: "127.0.0.1",
      port: 59999,
      maxRetriesPerRequest: 0,
      connectTimeout: 100,
      retryStrategy: () => null,
      lazyConnect: true,
    });
    disconnectedRedis.on("error", () => {});

    const config = {
      ...loadConfig(),
      redisUrl: "redis://127.0.0.1:59999",
      environment: "test" as const,
      logLevel: "silent",
    };
    const disconnectedApp = buildApp({
      config,
      redisClient: disconnectedRedis,
    });

    const response = await disconnectedApp.inject({
      method: "GET",
      url: "/readyz",
    });

    expect(response.statusCode).toBe(503);
    const body = JSON.parse(response.body);
    expect(body.status).toBe("error");
    expect(body.redis).toBe("disconnected");

    disconnectedRedis.disconnect();
    await disconnectedApp.close();
  });

  it("GET /health should return service details and timestamp", async () => {
    const response = await app.inject({
      method: "GET",
      url: "/health",
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.body);
    expect(body.status).toBe("ok");
    expect(body.service).toBe("antifraud-fastify");
    expect(body.timestamp).toBeDefined();
  });

  it("GET /non-existent-route should return 404 Not Found", async () => {
    const response = await app.inject({
      method: "GET",
      url: "/non-existent-route",
    });

    expect(response.statusCode).toBe(404);
    expect(JSON.parse(response.body).error).toBe("Not Found");
  });
});
