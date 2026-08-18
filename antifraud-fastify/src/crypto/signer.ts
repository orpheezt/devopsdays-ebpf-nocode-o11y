import { createHash, createHmac, timingSafeEqual } from "node:crypto";

export interface FraudAssessmentPayload {
  customer_id?: string;
  amount?: number;
  risk_score: number;
  status: string;
  evaluated_at: string;
}

export class CryptoSigner {
  private secretKey: string;

  constructor(secretKey: string) {
    this.secretKey = secretKey;
  }

  private canonicalize(payload: FraudAssessmentPayload): string {
    const custId = payload.customer_id || "";
    const amt =
      payload.amount !== undefined && payload.amount !== null
        ? payload.amount.toFixed(2)
        : "";
    return `${custId}|${amt}|${payload.risk_score.toFixed(2)}|${payload.status}|${payload.evaluated_at}`;
  }

  sign(payload: FraudAssessmentPayload): string {
    const canonical = this.canonicalize(payload);
    const hmac = createHmac("sha256", this.secretKey);
    hmac.update(canonical);
    const digest = hmac.digest("hex");
    return `sha256:${digest}`;
  }

  verify(payload: FraudAssessmentPayload, signature: string): boolean {
    if (!signature.startsWith("sha256:")) {
      return false;
    }
    const expected = this.sign(payload);
    const sigBuffer = Buffer.from(signature, "utf-8");
    const expectedBuffer = Buffer.from(expected, "utf-8");

    if (sigBuffer.length !== expectedBuffer.length) {
      return false;
    }

    return timingSafeEqual(sigBuffer, expectedBuffer);
  }

  createCacheKey(customerId?: string, amount?: number): string {
    const cust = customerId || "anonymous";
    const amt =
      amount !== undefined && amount !== null ? amount.toFixed(2) : "none";
    const raw = `eval:${cust}:${amt}`;
    return createHash("sha256").update(raw).digest("hex");
  }
}
