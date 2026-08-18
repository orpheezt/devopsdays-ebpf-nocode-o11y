export const checkFraudQuerySchema = {
  type: "object",
  properties: {
    customer_id: {
      type: "string",
      description: "Optional customer or user identifier",
    },
    amount: {
      type: "number",
      minimum: 0,
      description: "Optional transaction amount in USD or base currency",
    },
  },
  additionalProperties: false,
};

export const checkFraudResponseSchema = {
  description: "Cryptographically signed fraud risk evaluation response",
  type: "object",
  properties: {
    risk_score: {
      type: "number",
      minimum: 0,
      maximum: 1,
      example: 0.02,
    },
    status: {
      type: "string",
      enum: ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"],
      example: "LOW_RISK",
    },
    factors: {
      type: "array",
      items: { type: "string" },
      example: ["STANDARD_TRANSACTION_TIER"],
    },
    velocity_count: {
      type: "integer",
      minimum: 0,
      example: 1,
    },
    cached: {
      type: "boolean",
      example: false,
    },
    signature: {
      type: "string",
      example:
        "sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
    },
    evaluated_at: {
      type: "string",
      format: "date-time",
      example: "2026-08-17T20:00:00.000Z",
    },
  },
  required: [
    "risk_score",
    "status",
    "factors",
    "velocity_count",
    "cached",
    "signature",
    "evaluated_at",
  ],
  additionalProperties: false,
};
