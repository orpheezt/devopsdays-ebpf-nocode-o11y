import { afterAll, beforeAll, describe, expect, it } from "bun:test";
import type { FastifyInstance } from "fastify";
import type { Redis } from "ioredis";
import type { StartedTestContainer } from "testcontainers";
import { buildApp } from "../src/app.js";
import { loadConfig } from "../src/config/config.js";
import { CryptoSigner } from "../src/crypto/signer.js";
import { startRedisContainer } from "./testcontainer-redis.js";

describe("Fraud Evaluation Endpoint Tests (Testcontainers redis:8.10-alpine3.23)", () => {
  let redisContainer: StartedTestContainer;
  let redisClient: Redis;
  let signer: CryptoSigner;
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
      antifraudSecretKey: "test-secret-key-12345",
    };

    signer = new CryptoSigner(config.antifraudSecretKey);
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

  it("GET /check-fraud with standard parameters should return 200 OK with LOW_RISK", async () => {
    const response = await app.inject({
      method: "GET",
      url: "/check-fraud?customer_id=cust_regular&amount=50.00",
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.body);

    expect(body.risk_score).toBe(0.02);
    expect(body.status).toBe("LOW_RISK");
    expect(body.factors).toContain("STANDARD_TRANSACTION_TIER");
    expect(body.velocity_count).toBe(1);
    expect(body.cached).toBe(false);
    expect(body.evaluated_at).toBeDefined();
    expect(body.signature).toBeString();

    const isValid = signer.verify(
      {
        customer_id: "cust_regular",
        amount: 50.0,
        risk_score: body.risk_score,
        status: body.status,
        evaluated_at: body.evaluated_at,
      },
      body.signature,
    );
    expect(isValid).toBe(true);

    const headerSig = response.headers["x-antifraud-signature"];
    expect(headerSig).toBeDefined();
    expect(headerSig).toBe(body.signature.replace("sha256:", "sha256="));
  });

  it("GET /check-fraud with micro-amount should flag micro-transaction probe", async () => {
    const response = await app.inject({
      method: "GET",
      url: "/check-fraud?customer_id=cust_micro&amount=0.50",
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.body);
    expect(body.risk_score).toBe(0.15);
    expect(body.status).toBe("LOW_RISK");
    expect(body.factors).toContain("MICRO_TRANSACTION_PROBE");
  });

  it("GET /check-fraud with high-value amount should return MEDIUM_RISK", async () => {
    const response = await app.inject({
      method: "GET",
      url: "/check-fraud?customer_id=cust_high&amount=3500.00",
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.body);
    expect(body.risk_score).toBe(0.45);
    expect(body.status).toBe("MEDIUM_RISK");
    expect(body.factors).toContain("HIGH_VALUE_TRANSACTION");
  });

  it("GET /check-fraud with critical amount should return HIGH_RISK", async () => {
    const response = await app.inject({
      method: "GET",
      url: "/check-fraud?customer_id=cust_critical&amount=10000.00",
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.body);
    expect(body.risk_score).toBe(0.88);
    expect(body.status).toBe("HIGH_RISK");
    expect(body.factors).toContain("CRITICAL_AMOUNT_ANOMALY");
  });

  it("GET /check-fraud for blacklisted customer should return 0.99 and HIGH_RISK", async () => {
    const response = await app.inject({
      method: "GET",
      url: "/check-fraud?customer_id=fraud_bot_99&amount=25.00",
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.body);
    expect(body.risk_score).toBe(0.99);
    expect(body.status).toBe("HIGH_RISK");
    expect(body.factors).toContain("BLACKLISTED_CUSTOMER");
  });

  it("GET /check-fraud should increase risk score on rapid velocity bursts in live Redis", async () => {
    const customerId = "cust_speedy_bot";

    const res1 = await app.inject({
      method: "GET",
      url: `/check-fraud?customer_id=${customerId}&amount=10.00`,
    });
    const body1 = JSON.parse(res1.body);
    expect(body1.velocity_count).toBe(1);
    expect(body1.risk_score).toBe(0.02);

    await app.inject({
      method: "GET",
      url: `/check-fraud?customer_id=${customerId}&amount=11.00`,
    });

    const res3 = await app.inject({
      method: "GET",
      url: `/check-fraud?customer_id=${customerId}&amount=12.00`,
    });
    const body3 = JSON.parse(res3.body);
    expect(body3.velocity_count).toBe(3);
    expect(body3.risk_score).toBe(0.27);
    expect(body3.factors).toContain("ELEVATED_VELOCITY_SPIKE");
  });

  it("GET /check-fraud should serve subsequent identical requests from Redis cache", async () => {
    const res1 = await app.inject({
      method: "GET",
      url: "/check-fraud?customer_id=cached_user&amount=45.00",
    });
    const body1 = JSON.parse(res1.body);
    expect(body1.cached).toBe(false);

    const res2 = await app.inject({
      method: "GET",
      url: "/check-fraud?customer_id=cached_user&amount=45.00",
    });
    const body2 = JSON.parse(res2.body);
    expect(body2.cached).toBe(true);
    expect(body2.signature).toBe(body1.signature);
    expect(body2.risk_score).toBe(body1.risk_score);
  });

  it("GET /check-fraud with negative amount should return 400 Bad Request", async () => {
    const response = await app.inject({
      method: "GET",
      url: "/check-fraud?amount=-50.00",
    });

    expect(response.statusCode).toBe(400);
    const body = JSON.parse(response.body);
    expect(body.error).toBe("Bad Request");
  });
});
