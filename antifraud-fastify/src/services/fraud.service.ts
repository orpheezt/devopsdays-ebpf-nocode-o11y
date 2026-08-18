import type { CryptoSigner } from "../crypto/signer.js";
import type { RedisFraudStore } from "./redis-fraud.store.js";

export interface FraudEvaluationResult {
  risk_score: number;
  status: "LOW_RISK" | "MEDIUM_RISK" | "HIGH_RISK";
  factors: string[];
  velocity_count: number;
  cached: boolean;
  signature: string;
  evaluated_at: string;
}

export interface FraudEngineOptions {
  store: RedisFraudStore;
  signer: CryptoSigner;
  cacheTtlSeconds?: number;
  velocityWindowSeconds?: number;
}

export class FraudEngineService {
  private store: RedisFraudStore;
  private signer: CryptoSigner;
  private cacheTtl: number;
  private velocityWindow: number;

  constructor(options: FraudEngineOptions) {
    this.store = options.store;
    this.signer = options.signer;
    this.cacheTtl = options.cacheTtlSeconds || 30;
    this.velocityWindow = options.velocityWindowSeconds || 60;
  }

  async evaluate(
    customerId?: string,
    amount?: number,
  ): Promise<FraudEvaluationResult> {
    const cacheKey = this.signer.createCacheKey(customerId, amount);

    const cachedData = await this.store.getCachedAssessment(cacheKey);
    if (cachedData) {
      const parsed = JSON.parse(cachedData) as FraudEvaluationResult;
      return { ...parsed, cached: true };
    }

    const factors: string[] = [];
    let velocityCount = 1;
    let finalScore = 0.02;
    let status: "LOW_RISK" | "MEDIUM_RISK" | "HIGH_RISK" = "LOW_RISK";

    const isBlacklisted = customerId
      ? (await this.store.isCustomerBlacklisted(customerId)) ||
        /^(fraud_|suspicious_|test_blocked_|banned_)/i.test(customerId)
      : false;

    if (isBlacklisted) {
      factors.push("BLACKLISTED_CUSTOMER");
      finalScore = 0.99;
      status = "HIGH_RISK";
    } else {
      let velocityPenalty = 0;
      if (customerId) {
        velocityCount = await this.store.incrementVelocity(
          customerId,
          this.velocityWindow,
        );
        if (velocityCount > 5) {
          velocityPenalty = 0.5;
          factors.push("EXCESSIVE_VELOCITY_BURST");
        } else if (velocityCount > 2) {
          velocityPenalty = 0.25;
          factors.push("ELEVATED_VELOCITY_SPIKE");
        }
      }

      let baseScore = 0.02;
      if (amount === undefined || amount === null) {
        factors.push("STANDARD_TRANSACTION_TIER");
      } else if (amount < 1.0) {
        baseScore = 0.15;
        factors.push("MICRO_TRANSACTION_PROBE");
      } else if (amount <= 1000.0) {
        factors.push("STANDARD_TRANSACTION_TIER");
      } else if (amount <= 5000.0) {
        baseScore = 0.45;
        factors.push("HIGH_VALUE_TRANSACTION");
      } else {
        baseScore = 0.88;
        factors.push("CRITICAL_AMOUNT_ANOMALY");
      }

      finalScore = Number(
        Math.min(0.99, Math.max(0.01, baseScore + velocityPenalty)).toFixed(2),
      );

      if (finalScore >= 0.85) {
        status = "HIGH_RISK";
      } else if (finalScore >= 0.3) {
        status = "MEDIUM_RISK";
      }
    }

    const evaluatedAt = new Date().toISOString();
    const signature = this.signer.sign({
      customer_id: customerId,
      amount,
      risk_score: finalScore,
      status,
      evaluated_at: evaluatedAt,
    });

    const result: FraudEvaluationResult = {
      risk_score: finalScore,
      status,
      factors,
      velocity_count: velocityCount,
      cached: false,
      signature,
      evaluated_at: evaluatedAt,
    };

    await this.store.setCachedAssessment(
      cacheKey,
      JSON.stringify(result),
      this.cacheTtl,
    );

    return result;
  }
}
