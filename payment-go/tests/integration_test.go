package tests

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/testcontainers/testcontainers-go"
	tcpostgres "github.com/testcontainers/testcontainers-go/modules/postgres"
	"github.com/testcontainers/testcontainers-go/wait"

	"payment-go/src/db"
	"payment-go/src/health"
	"payment-go/src/models"
	"payment-go/src/payments"
)

func init() {
	gin.SetMode(gin.TestMode)
	_ = os.Setenv("TESTCONTAINERS_RYUK_DISABLED", "true")
}

func startPostgresContainer(ctx context.Context, t *testing.T) (*tcpostgres.PostgresContainer, string) {
	pgContainer, err := tcpostgres.Run(ctx,
		"docker.io/library/postgres:18.4-trixie",
		tcpostgres.WithDatabase("payment_db"),
		tcpostgres.WithUsername("postgres"),
		tcpostgres.WithPassword("postgres"),
		testcontainers.WithWaitStrategy(
			wait.ForLog("database system is ready to accept connections").
				WithOccurrence(2).
				WithStartupTimeout(60*time.Second),
		),
	)
	require.NoError(t, err, "failed to start postgres:18.4-trixie testcontainer")

	connStr, err := pgContainer.ConnectionString(ctx, "sslmode=disable")
	require.NoError(t, err, "failed to get testcontainer connection string")

	return pgContainer, connStr
}

func runGooseMigrations(ctx context.Context, t *testing.T, connStr string) {
	cmd := exec.CommandContext(ctx, "goose", "-dir", "../migrations", "postgres", connStr, "up")
	out, err := cmd.CombinedOutput()
	require.NoError(t, err, "goose migration failed: %s", string(out))
}

func TestEndToEndWithPostgresTestcontainer(t *testing.T) {
	ctx := context.Background()

	pgContainer, connStr := startPostgresContainer(ctx, t)
	defer func() {
		_ = pgContainer.Terminate(ctx)
	}()

	runGooseMigrations(ctx, t, connStr)

	gormDB, err := db.InitDB(connStr)
	require.NoError(t, err)

	antifraudRiskScore := 0.02
	mockAntiFraud := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/check-fraud", r.URL.Path)
		assert.Equal(t, http.MethodGet, r.Method)
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(payments.FraudAssessment{
			RiskScore: antifraudRiskScore,
			Status:    "LOW_RISK",
			Engine:    "fastify-node",
		})
	}))
	defer mockAntiFraud.Close()

	paymentService := payments.NewPaymentService(gormDB, payments.ServiceConfig{
		AntiFraudServiceURL: mockAntiFraud.URL,
		AntiFraudTimeout:    2 * time.Second,
	}, mockAntiFraud.Client())
	paymentHandler := payments.NewHandler(paymentService)

	router := gin.New()
	health.RegisterRoutes(router, gormDB)
	payments.RegisterRoutes(router, paymentHandler)

	t.Run("K8s Probes", func(t *testing.T) {
		liveReq, _ := http.NewRequest(http.MethodGet, "/livez", nil)
		liveRec := httptest.NewRecorder()
		router.ServeHTTP(liveRec, liveReq)
		assert.Equal(t, http.StatusOK, liveRec.Code)
		var liveResp health.HealthStatusResponse
		require.NoError(t, json.Unmarshal(liveRec.Body.Bytes(), &liveResp))
		assert.Equal(t, "ok", liveResp.Status)

		readyReq, _ := http.NewRequest(http.MethodGet, "/readyz", nil)
		readyRec := httptest.NewRecorder()
		router.ServeHTTP(readyRec, readyReq)
		assert.Equal(t, http.StatusOK, readyRec.Code)
		var readyResp health.ReadinessStatusResponse
		require.NoError(t, json.Unmarshal(readyRec.Body.Bytes(), &readyResp))
		assert.Equal(t, "ok", readyResp.Status)
		assert.Equal(t, "connected", readyResp.Database)
	})

	t.Run("POST /pay Approved", func(t *testing.T) {
		antifraudRiskScore = 0.02

		payload := map[string]interface{}{
			"order_id":    "0191234a-5b6c-7123-8000-000000000001",
			"customer_id": "CUST-BOGOTA-2026",
			"amount":      43.50,
		}
		body, _ := json.Marshal(payload)

		req, _ := http.NewRequest(http.MethodPost, "/pay", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		rec := httptest.NewRecorder()

		router.ServeHTTP(rec, req)

		assert.Equal(t, http.StatusOK, rec.Code)

		var res payments.PaymentResponse
		err := json.Unmarshal(rec.Body.Bytes(), &res)
		require.NoError(t, err)

		assert.NotEmpty(t, res.PaymentID)
		_, err = uuid.Parse(res.PaymentID)
		require.NoError(t, err)
		assert.Equal(t, "0191234a-5b6c-7123-8000-000000000001", res.OrderID)
		assert.Equal(t, "APPROVED", res.Status)
		assert.Equal(t, 43.50, res.AmountProcessed)
		assert.Equal(t, 0.02, res.FraudAssessment.RiskScore)
		assert.Equal(t, "LOW_RISK", res.FraudAssessment.Status)
		assert.Equal(t, "fastify-node", res.FraudAssessment.Engine)

		var saved models.Payment
		err = gormDB.Where("payment_id = ?", res.PaymentID).First(&saved).Error
		require.NoError(t, err)
		assert.Equal(t, "CUST-BOGOTA-2026", saved.CustomerID)
		assert.Equal(t, 43.50, saved.Amount)
		assert.Equal(t, "APPROVED", saved.Status)
		assert.Equal(t, 0.02, saved.RiskScore)
		assert.Equal(t, "fastify-node", saved.AntiFraudEngine)
		assert.False(t, saved.CreatedAt.IsZero())
	})

	t.Run("POST /pay Declined", func(t *testing.T) {
		antifraudRiskScore = 0.92

		payload := map[string]interface{}{
			"order_id":    "0191234a-5b6c-7123-8000-000000000002",
			"customer_id": "CUST-FRAUD-RISK",
			"amount":      299.99,
		}
		body, _ := json.Marshal(payload)

		req, _ := http.NewRequest(http.MethodPost, "/pay", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		rec := httptest.NewRecorder()

		router.ServeHTTP(rec, req)

		assert.Equal(t, http.StatusOK, rec.Code)

		var res payments.PaymentResponse
		err := json.Unmarshal(rec.Body.Bytes(), &res)
		require.NoError(t, err)

		assert.Equal(t, "DECLINED", res.Status)
		assert.Equal(t, 0.92, res.FraudAssessment.RiskScore)

		var saved models.Payment
		err = gormDB.Where("payment_id = ?", res.PaymentID).First(&saved).Error
		require.NoError(t, err)
		assert.Equal(t, "DECLINED", saved.Status)
		assert.Equal(t, 299.99, saved.Amount)
	})

	t.Run("Gateway-Py Compatible Payload", func(t *testing.T) {
		antifraudRiskScore = 0.01

		payload := map[string]interface{}{
			"order_id":    "0191234a-5b6c-7123-8000-000000000000",
			"customer_id": "cust_123",
			"amount":      17.00,
		}
		body, _ := json.Marshal(payload)

		req, _ := http.NewRequest(http.MethodPost, "/pay", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		rec := httptest.NewRecorder()

		router.ServeHTTP(rec, req)

		assert.Equal(t, http.StatusOK, rec.Code)

		var res payments.PaymentResponse
		err := json.Unmarshal(rec.Body.Bytes(), &res)
		require.NoError(t, err)
		assert.Equal(t, "0191234a-5b6c-7123-8000-000000000000", res.OrderID)
		assert.Equal(t, "APPROVED", res.Status)
		assert.Equal(t, 17.00, res.AmountProcessed)

		var count int64
		gormDB.Model(&models.Payment{}).Where("order_id = ?", "0191234a-5b6c-7123-8000-000000000000").Count(&count)
		assert.Equal(t, int64(1), count)
	})
}
