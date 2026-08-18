import type { Redis } from "ioredis";
import {
  GenericContainer,
  type StartedTestContainer,
  Wait,
} from "testcontainers";
import { createRedisClient } from "../src/db/redis.js";

export async function startRedisContainer(): Promise<{
  container: StartedTestContainer;
  redisUrl: string;
  redisClient: Redis;
}> {
  const container = await new GenericContainer("redis:8.10-alpine3.23")
    .withExposedPorts(6379)
    .withWaitStrategy(Wait.forListeningPorts())
    .start();

  const host = container.getHost();
  const port = container.getMappedPort(6379);
  const redisUrl = `redis://${host}:${port}`;
  const redisClient = createRedisClient(redisUrl);

  return { container, redisUrl, redisClient };
}
