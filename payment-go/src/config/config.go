package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

type Config struct {
	Port                string
	Environment         string
	DBDSN               string
	AntiFraudServiceURL string
	AntiFraudTimeout    time.Duration
	AntiFraudSecretKey  string
}

func Load() *Config {
	port := getEnv("PORT", "8081")
	environment := getEnv("ENV", "development")

	dsn := os.Getenv("DB_DSN")
	if dsn == "" {
		dbURL := os.Getenv("DATABASE_URL")
		if dbURL != "" {
			dsn = dbURL
		} else {
			dbHost := getEnv("DB_HOST", "localhost")
			dbPort := getEnv("DB_PORT", "5432")
			dbUser := getEnv("DB_USER", "postgres")
			dbPassword := getEnv("DB_PASSWORD", "postgres")
			dbName := getEnv("DB_NAME", "payment_db")
			dbSSLMode := getEnv("DB_SSLMODE", "disable")

			dsn = fmt.Sprintf(
				"host=%s port=%s user=%s password=%s dbname=%s sslmode=%s TimeZone=UTC",
				dbHost, dbPort, dbUser, dbPassword, dbName, dbSSLMode,
			)
		}
	}

	antifraudURL := getEnv("ANTIFRAUD_SERVICE_URL", "http://antifraud-fastify:8083")
	antifraudSecretKey := getEnv("ANTIFRAUD_SECRET_KEY", "antifraud-super-secret-key-2026")
	timeoutMsStr := getEnv("ANTIFRAUD_TIMEOUT_MS", "2000")
	timeoutMs, err := strconv.Atoi(timeoutMsStr)
	if err != nil || timeoutMs <= 0 {
		timeoutMs = 2000
	}

	return &Config{
		Port:                port,
		Environment:         environment,
		DBDSN:               dsn,
		AntiFraudServiceURL: antifraudURL,
		AntiFraudTimeout:    time.Duration(timeoutMs) * time.Millisecond,
		AntiFraudSecretKey:  antifraudSecretKey,
	}
}

func getEnv(key, fallback string) string {
	if val, exists := os.LookupEnv(key); exists && val != "" {
		return val
	}
	return fallback
}
