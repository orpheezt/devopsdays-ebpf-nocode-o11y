export const livenessResponseSchema = {
  description: "Kubernetes liveness probe response",
  type: "object",
  properties: {
    status: { type: "string", example: "ok" },
  },
  required: ["status"],
  additionalProperties: false,
};

export const readinessSuccessResponseSchema = {
  description: "Kubernetes readiness probe success response",
  type: "object",
  properties: {
    status: { type: "string", example: "ok" },
    redis: { type: "string", example: "connected" },
  },
  required: ["status", "redis"],
  additionalProperties: false,
};

export const readinessErrorResponseSchema = {
  description: "Kubernetes readiness probe error response",
  type: "object",
  properties: {
    status: { type: "string", example: "error" },
    redis: { type: "string", example: "disconnected" },
    error: { type: "string" },
  },
  required: ["status", "redis"],
  additionalProperties: false,
};

export const healthResponseSchema = {
  description: "General service health summary",
  type: "object",
  properties: {
    status: { type: "string", example: "ok" },
    service: { type: "string", example: "antifraud-fastify" },
    timestamp: { type: "string", format: "date-time" },
  },
  required: ["status", "service", "timestamp"],
  additionalProperties: false,
};
