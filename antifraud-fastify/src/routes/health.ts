import type { FastifyInstance } from "fastify";
import type { Redis } from "ioredis";
import {
  healthResponseSchema,
  livenessResponseSchema,
  readinessErrorResponseSchema,
  readinessSuccessResponseSchema,
} from "../schemas/health.schema.js";

export interface HealthRouteOptions {
  redisClient: Redis;
}

export const healthRoutes = async (
  fastify: FastifyInstance,
  options: HealthRouteOptions,
): Promise<void> => {
  const { redisClient } = options;

  fastify.get(
    "/livez",
    {
      schema: {
        response: {
          200: livenessResponseSchema,
        },
      },
    },
    async (_request, reply) => {
      return reply.code(200).send({ status: "ok" });
    },
  );

  fastify.get(
    "/readyz",
    {
      schema: {
        response: {
          200: readinessSuccessResponseSchema,
          503: readinessErrorResponseSchema,
        },
      },
    },
    async (_request, reply) => {
      try {
        await redisClient.ping();
        return reply.code(200).send({
          status: "ok",
          redis: "connected",
        });
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Redis connection failed";
        fastify.log.warn({ err }, "Readiness check failed: Redis unreachable");
        return reply.code(503).send({
          status: "error",
          redis: "disconnected",
          error: errorMessage,
        });
      }
    },
  );

  fastify.get(
    "/health",
    {
      schema: {
        response: {
          200: healthResponseSchema,
        },
      },
    },
    async (_request, reply) => {
      return reply.code(200).send({
        status: "ok",
        service: "antifraud-fastify",
        timestamp: new Date().toISOString(),
      });
    },
  );
};
