import { Redis, type RedisOptions } from "ioredis";

export function createRedisClient(urlOrOptions: string | RedisOptions): Redis {
  const options: RedisOptions =
    typeof urlOrOptions === "string"
      ? {
          maxRetriesPerRequest: 3,
          enableReadyCheck: true,
          lazyConnect: false,
          retryStrategy(times) {
            return Math.min(times * 50, 2000);
          },
        }
      : urlOrOptions;

  if (typeof urlOrOptions === "string") {
    return new Redis(urlOrOptions, options);
  }

  return new Redis(options);
}
