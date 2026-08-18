import type { Redis } from "ioredis";

export interface RedisFraudStoreOptions {
  redisClient: Redis;
  keyPrefix?: string;
}

export class RedisFraudStore {
  private redis: Redis;
  private prefix: string;

  constructor(options: RedisFraudStoreOptions) {
    this.redis = options.redisClient;
    this.prefix = options.keyPrefix || "fraud:";
  }

  private userVelocityKey(customerId: string): string {
    return `${this.prefix}velocity:user:${customerId}`;
  }

  private blacklistUsersKey(): string {
    return `${this.prefix}blacklist:users`;
  }

  private cacheKey(hash: string): string {
    return `${this.prefix}cache:${hash}`;
  }

  async incrementVelocity(
    customerId: string,
    windowSeconds = 60,
  ): Promise<number> {
    if (!customerId) return 1;
    const key = this.userVelocityKey(customerId);
    const count = await this.redis.incr(key);
    if (count === 1) {
      await this.redis.expire(key, windowSeconds);
    }
    return count;
  }

  async isCustomerBlacklisted(customerId: string): Promise<boolean> {
    if (!customerId) return false;
    const isMember = await this.redis.sismember(
      this.blacklistUsersKey(),
      customerId,
    );
    return isMember === 1;
  }

  async addToBlacklist(...customerIds: string[]): Promise<number> {
    if (customerIds.length === 0) return 0;
    return await this.redis.sadd(this.blacklistUsersKey(), ...customerIds);
  }

  async getCachedAssessment(hash: string): Promise<string | null> {
    return await this.redis.get(this.cacheKey(hash));
  }

  async setCachedAssessment(
    hash: string,
    payload: string,
    ttlSeconds = 30,
  ): Promise<void> {
    await this.redis.setex(this.cacheKey(hash), ttlSeconds, payload);
  }
}
