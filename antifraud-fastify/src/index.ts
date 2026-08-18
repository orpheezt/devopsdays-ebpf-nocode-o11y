import { buildApp } from "./app.js";
import { loadConfig } from "./config/config.js";
import { createRedisClient } from "./db/redis.js";

async function main(): Promise<void> {
  const config = loadConfig();
  const redisClient = createRedisClient(config.redisUrl);

  const app = buildApp({
    config,
    redisClient,
  });

  let isShuttingDown = false;
  const shutdown = async (signal: string) => {
    if (isShuttingDown) return;
    isShuttingDown = true;

    app.log.info(
      { signal },
      "Received shutdown signal, starting graceful shutdown...",
    );

    const forceExitTimer = setTimeout(() => {
      app.log.error("Graceful shutdown timed out, forcing exit");
      process.exit(1);
    }, 10000);

    try {
      await app.close();
      app.log.info("HTTP server closed");

      try {
        await redisClient.quit();
        app.log.info("Redis connection closed");
      } catch {
        redisClient.disconnect();
      }

      clearTimeout(forceExitTimer);
      app.log.info("Service exited gracefully");
      process.exit(0);
    } catch (err) {
      clearTimeout(forceExitTimer);
      app.log.error({ err }, "Error during graceful shutdown");
      process.exit(1);
    }
  };

  process.on("SIGINT", () => shutdown("SIGINT"));
  process.on("SIGTERM", () => shutdown("SIGTERM"));

  try {
    await app.listen({
      port: config.port,
      host: config.host,
    });
    app.log.info(
      {
        port: config.port,
        host: config.host,
        env: config.environment,
        redisUrl: config.redisUrl,
      },
      "antifraud-fastify microservice started successfully",
    );
  } catch (err) {
    app.log.error({ err }, "Failed to start antifraud-fastify microservice");
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Fatal startup error:", err);
  process.exit(1);
});
