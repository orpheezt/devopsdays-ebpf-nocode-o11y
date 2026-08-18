import { afterAll, beforeAll, describe, expect, it } from "bun:test";
import type { Redis } from "ioredis";
import type { StartedTestContainer } from "testcontainers";
import { RedisFraudStore } from "../src/services/redis-fraud.store.js";
import { startRedisContainer } from "./testcontainer-redis.js";

describe("RedisFraudStore Tests (Testcontainers redis:8.10-alpine3.23)", () => {
  let redisContainer: StartedTestContainer;
  let redisClient: Redis;
  let store: RedisFraudStore;

  beforeAll(async () => {
    const started = await startRedisContainer();
    redisContainer = started.container;
    redisClient = started.redisClient;
    store = new RedisFraudStore({
      redisClient,
      keyPrefix: "test:store:fraud:",
    });
  }, 120000);

  afterAll(async () => {
    if (redisClient) {
      await redisClient.quit().catch(() => {});
    }
    if (redisContainer) {
      await redisContainer.stop();
    }
  });

  describe("Velocity Checks", () => {
    it("should increment velocity count on each call in live Redis", async () => {
      const customerId = "cust_abc_123";

      const count1 = await store.incrementVelocity(customerId, 60);
      expect(count1).toBe(1);

      const count2 = await store.incrementVelocity(customerId, 60);
      expect(count2).toBe(2);

      const count3 = await store.incrementVelocity(customerId, 60);
      expect(count3).toBe(3);
    });

    it("should handle empty customerId gracefully", async () => {
      const count = await store.incrementVelocity("", 60);
      expect(count).toBe(1);
    });
  });

  describe("Blacklist Management", () => {
    it("should accurately report blacklisted status using Redis Sets", async () => {
      const blockedId = "fraud_scammer_01";
      const regularId = "good_customer_99";

      expect(await store.isCustomerBlacklisted(blockedId)).toBe(false);

      await store.addToBlacklist(blockedId);

      expect(await store.isCustomerBlacklisted(blockedId)).toBe(true);
      expect(await store.isCustomerBlacklisted(regularId)).toBe(false);
    });

    it("should add multiple blacklisted entities", async () => {
      await store.addToBlacklist("blocked_1", "blocked_2", "blocked_3");

      expect(await store.isCustomerBlacklisted("blocked_1")).toBe(true);
      expect(await store.isCustomerBlacklisted("blocked_2")).toBe(true);
      expect(await store.isCustomerBlacklisted("blocked_3")).toBe(true);
      expect(await store.isCustomerBlacklisted("unknown_customer")).toBe(false);
    });
  });

  describe("Assessment Caching", () => {
    it("should store and retrieve cached assessment payloads from live Redis", async () => {
      const hash = "sample_cache_hash_123";
      const payload = JSON.stringify({ risk_score: 0.02, status: "LOW_RISK" });

      expect(await store.getCachedAssessment(hash)).toBeNull();

      await store.setCachedAssessment(hash, payload, 30);

      const cached = await store.getCachedAssessment(hash);
      expect(cached).toBe(payload);
    });
  });
});
