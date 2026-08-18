export interface AppConfig {
  port: number;
  host: string;
  environment: "development" | "production" | "test";
  logLevel: string;
  redisUrl: string;
  redisKeyPrefix: string;
  antifraudSecretKey: string;
  cacheTtlSeconds: number;
  velocityWindowSeconds: number;
}

export function loadConfig(): AppConfig {
  const port = Number.parseInt(process.env.PORT || "8083", 10);
  const host = process.env.HOST || "0.0.0.0";
  const environment = (process.env.ENVIRONMENT ||
    process.env.NODE_ENV ||
    "development") as AppConfig["environment"];
  const logLevel =
    process.env.LOG_LEVEL || (environment === "production" ? "info" : "debug");
  const redisUrl = process.env.REDIS_URL || "redis://localhost:6379";
  const redisKeyPrefix = process.env.REDIS_KEY_PREFIX || "fraud:";
  const antifraudSecretKey =
    process.env.ANTIFRAUD_SECRET_KEY || "antifraud-super-secret-key-2026";
  const cacheTtlSeconds = Number.parseInt(
    process.env.FRAUD_CACHE_TTL_SECONDS || "30",
    10,
  );
  const velocityWindowSeconds = Number.parseInt(
    process.env.FRAUD_VELOCITY_WINDOW_SECONDS || "60",
    10,
  );

  return {
    port: Number.isNaN(port) ? 8083 : port,
    host,
    environment,
    logLevel,
    redisUrl,
    redisKeyPrefix,
    antifraudSecretKey,
    cacheTtlSeconds: Number.isNaN(cacheTtlSeconds) ? 30 : cacheTtlSeconds,
    velocityWindowSeconds: Number.isNaN(velocityWindowSeconds)
      ? 60
      : velocityWindowSeconds,
  };
}
