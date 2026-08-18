import type { FastifyInstance } from "fastify";
import {
  checkFraudQuerySchema,
  checkFraudResponseSchema,
} from "../schemas/fraud.schema.js";
import type { FraudEngineService } from "../services/fraud.service.js";

export interface FraudRouteOptions {
  fraudService: FraudEngineService;
}

interface CheckFraudQuery {
  customer_id?: string;
  amount?: number;
}

export const fraudRoutes = async (
  fastify: FastifyInstance,
  options: FraudRouteOptions,
): Promise<void> => {
  const { fraudService } = options;

  fastify.get<{ Querystring: CheckFraudQuery }>(
    "/check-fraud",
    {
      schema: {
        querystring: checkFraudQuerySchema,
        response: {
          200: checkFraudResponseSchema,
        },
      },
    },
    async (request, reply) => {
      const { customer_id, amount } = request.query;

      const assessment = await fraudService.evaluate(customer_id, amount);

      const headerSignature = assessment.signature.startsWith("sha256:")
        ? assessment.signature.replace("sha256:", "sha256=")
        : assessment.signature;

      reply.header("X-Antifraud-Signature", headerSignature);
      reply.header("Cache-Control", "no-store, no-cache, must-revalidate");

      return reply.code(200).send(assessment);
    },
  );
};
