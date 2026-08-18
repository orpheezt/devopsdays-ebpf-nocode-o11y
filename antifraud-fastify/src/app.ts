import fastify, { type FastifyError, type FastifyInstance } from "fastify";
import type { Redis } from "ioredis";
import type { AppConfig } from "./config/config.js";
import { CryptoSigner } from "./crypto/signer.js";
import { fraudRoutes } from "./routes/fraud.js";
import { healthRoutes } from "./routes/health.js";
import { FraudEngineService } from "./services/fraud.service.js";
import { RedisFraudStore } from "./services/redis-fraud.store.js";

export interface AppOptions {
  config: AppConfig;
  redisClient: Redis;
}

export function buildApp(options: AppOptions): FastifyInstance {
  const { config, redisClient } = options;

  const fraudStore = new RedisFraudStore({
    redisClient,
    keyPrefix: config.redisKeyPrefix,
  });

  const signer = new CryptoSigner(config.antifraudSecretKey);

  const fraudService = new FraudEngineService({
    store: fraudStore,
    signer,
    cacheTtlSeconds: config.cacheTtlSeconds,
    velocityWindowSeconds: config.velocityWindowSeconds,
  });

  const app = fastify({
    logger:
      config.environment === "test" && config.logLevel === "silent"
        ? false
        : {
            level: config.logLevel,
          },
    ajv: {
      customOptions: {
        coerceTypes: true,
        removeAdditional: true,
        useDefaults: true,
      },
    },
  });

  app.setNotFoundHandler((request, reply) => {
    reply.code(404).send({
      error: "Not Found",
      message: `Route ${request.method}:${request.url} not found`,
      statusCode: 404,
    });
  });

  app.setErrorHandler((error: FastifyError, request, reply) => {
    const statusCode = error.statusCode || 500;
    request.log.error({ err: error }, "Unhandled request error");

    if (error.validation) {
      return reply.code(400).send({
        error: "Bad Request",
        message: error.message,
        statusCode: 400,
        validation: error.validation,
      });
    }

    return reply.code(statusCode).send({
      error: error.name || "Internal Server Error",
      message: error.message || "An unexpected error occurred",
      statusCode,
    });
  });

  app.register(healthRoutes, { redisClient });
  app.register(fraudRoutes, { fraudService });

  app.decorate("redisClient", redisClient);
  app.decorate("fraudService", fraudService);

  return app;
}
