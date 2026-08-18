package config_test

import (
	"os"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"

	"payment-go/src/config"
)

func TestLoadDefaults(t *testing.T) {
	os.Unsetenv("PORT")
	os.Unsetenv("ENV")
	os.Unsetenv("DB_DSN")
	os.Unsetenv("DATABASE_URL")
	os.Unsetenv("DB_HOST")
	os.Unsetenv("DB_PORT")
	os.Unsetenv("DB_USER")
	os.Unsetenv("DB_PASSWORD")
	os.Unsetenv("DB_NAME")
	os.Unsetenv("DB_SSLMODE")
	os.Unsetenv("ANTIFRAUD_SERVICE_URL")
	os.Unsetenv("ANTIFRAUD_TIMEOUT_MS")
	os.Unsetenv("ANTIFRAUD_SECRET_KEY")

	cfg := config.Load()
	assert.Equal(t, "8081", cfg.Port)
	assert.Equal(t, "development", cfg.Environment)
	assert.Contains(t, cfg.DBDSN, "dbname=payment_db")
	assert.Equal(t, "http://antifraud-fastify:8083", cfg.AntiFraudServiceURL)
	assert.Equal(t, 2*time.Second, cfg.AntiFraudTimeout)
	assert.Equal(t, "antifraud-super-secret-key-2026", cfg.AntiFraudSecretKey)
}

func TestLoadCustomEnv(t *testing.T) {
	t.Setenv("PORT", "9090")
	t.Setenv("ENV", "production")
	t.Setenv("DB_DSN", "postgres://custom_user:custom_pass@custom_host:5433/custom_db?sslmode=require")
	t.Setenv("ANTIFRAUD_SERVICE_URL", "http://custom-antifraud:8080")
	t.Setenv("ANTIFRAUD_TIMEOUT_MS", "3500")
	t.Setenv("ANTIFRAUD_SECRET_KEY", "custom-secret-key-999")

	cfg := config.Load()
	assert.Equal(t, "9090", cfg.Port)
	assert.Equal(t, "production", cfg.Environment)
	assert.Equal(t, "postgres://custom_user:custom_pass@custom_host:5433/custom_db?sslmode=require", cfg.DBDSN)
	assert.Equal(t, "http://custom-antifraud:8080", cfg.AntiFraudServiceURL)
	assert.Equal(t, 3500*time.Millisecond, cfg.AntiFraudTimeout)
	assert.Equal(t, "custom-secret-key-999", cfg.AntiFraudSecretKey)
}
