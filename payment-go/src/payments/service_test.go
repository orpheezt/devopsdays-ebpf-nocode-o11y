package payments_test

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"

	"payment-go/src/models"
	"payment-go/src/payments"
)

func setupTestDB(t *testing.T) *gorm.DB {
	gormDB, err := gorm.Open(sqlite.Open("file::memory:?cache=shared"), &gorm.Config{})
	require.NoError(t, err)

	err = gormDB.AutoMigrate(&models.Payment{})
	require.NoError(t, err)

	return gormDB
}

func computeSignature(secret, customerID string, amount, riskScore float64, status, evaluatedAt string) string {
	canonical := fmt.Sprintf("%s|%.2f|%.2f|%s|%s", customerID, amount, riskScore, status, evaluatedAt)
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(canonical))
	return fmt.Sprintf("sha256:%s", hex.EncodeToString(mac.Sum(nil)))
}

func TestProcessPayment_Approved(t *testing.T) {
	db := setupTestDB(t)

	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/check-fraud", r.URL.Path)
		assert.Equal(t, "CUST-BOGOTA-2026", r.URL.Query().Get("customer_id"))
		assert.Equal(t, "43.50", r.URL.Query().Get("amount"))
		assert.Equal(t, http.MethodGet, r.Method)
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(payments.FraudAssessment{
			RiskScore: 0.02,
			Status:    "LOW_RISK",
		})
	}))
	defer mockServer.Close()

	svc := payments.NewPaymentService(db, payments.ServiceConfig{
		AntiFraudServiceURL: mockServer.URL,
		AntiFraudTimeout:    2 * time.Second,
	}, mockServer.Client())

	req := payments.PaymentRequest{
		OrderID:    "0191234a-5b6c-7123-8000-000000000001",
		CustomerID: "CUST-BOGOTA-2026",
		Amount:     43.50,
	}

	resp, err := svc.ProcessPayment(context.Background(), req)
	require.NoError(t, err)
	assert.NotEmpty(t, resp.PaymentID)
	_, err = uuid.Parse(resp.PaymentID)
	require.NoError(t, err)
	assert.Equal(t, "0191234a-5b6c-7123-8000-000000000001", resp.OrderID)
	assert.Equal(t, "APPROVED", resp.Status)
	assert.Equal(t, 43.50, resp.AmountProcessed)
	assert.Equal(t, 0.02, resp.FraudAssessment.RiskScore)
	assert.Equal(t, "LOW_RISK", resp.FraudAssessment.Status)

	var saved models.Payment
	err = db.Where("payment_id = ?", resp.PaymentID).First(&saved).Error
	require.NoError(t, err)
	assert.Equal(t, "APPROVED", saved.Status)
	assert.Equal(t, 43.50, saved.Amount)
	assert.False(t, saved.CreatedAt.IsZero())
}

func TestProcessPayment_Declined(t *testing.T) {
	db := setupTestDB(t)

	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(payments.FraudAssessment{
			RiskScore: 0.95,
			Status:    "HIGH_RISK",
		})
	}))
	defer mockServer.Close()

	svc := payments.NewPaymentService(db, payments.ServiceConfig{
		AntiFraudServiceURL: mockServer.URL,
		AntiFraudTimeout:    2 * time.Second,
	}, mockServer.Client())

	req := payments.PaymentRequest{
		OrderID:    "0191234a-5b6c-7123-8000-000000000002",
		CustomerID: "CUST-SUSPICIOUS",
		Amount:     500.00,
	}

	resp, err := svc.ProcessPayment(context.Background(), req)
	require.NoError(t, err)
	assert.Equal(t, "DECLINED", resp.Status)
	assert.Equal(t, 0.95, resp.FraudAssessment.RiskScore)

	var saved models.Payment
	err = db.Where("payment_id = ?", resp.PaymentID).First(&saved).Error
	require.NoError(t, err)
	assert.Equal(t, "DECLINED", saved.Status)
}

func TestProcessPayment_HMACSuccess(t *testing.T) {
	db := setupTestDB(t)
	secret := "test-secret-key-12345"
	evaluatedAt := "2026-08-17T20:00:00.000Z"
	customerID := "CUST-HMAC-VALID"
	amount := 88.00
	riskScore := 0.02
	status := "LOW_RISK"

	sig := computeSignature(secret, customerID, amount, riskScore, status, evaluatedAt)

	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(payments.FraudAssessment{
			RiskScore:   riskScore,
			Status:      status,
			Signature:   sig,
			EvaluatedAt: evaluatedAt,
		})
	}))
	defer mockServer.Close()

	svc := payments.NewPaymentService(db, payments.ServiceConfig{
		AntiFraudServiceURL: mockServer.URL,
		AntiFraudTimeout:    2 * time.Second,
		AntiFraudSecretKey:  secret,
	}, mockServer.Client())

	req := payments.PaymentRequest{
		OrderID:    "0191234a-5b6c-7123-8000-000000000010",
		CustomerID: customerID,
		Amount:     amount,
	}

	resp, err := svc.ProcessPayment(context.Background(), req)
	require.NoError(t, err)
	assert.Equal(t, "APPROVED", resp.Status)
	assert.Equal(t, sig, resp.FraudAssessment.Signature)
}

func TestProcessPayment_HMACTamperedFailure(t *testing.T) {
	db := setupTestDB(t)
	secret := "test-secret-key-12345"
	evaluatedAt := "2026-08-17T20:00:00.000Z"
	customerID := "CUST-HMAC-TAMPERED"
	amount := 88.00

	tamperedSig := "sha256:0000000000000000000000000000000000000000000000000000000000000000"

	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(payments.FraudAssessment{
			RiskScore:   0.02,
			Status:      "LOW_RISK",
			Signature:   tamperedSig,
			EvaluatedAt: evaluatedAt,
		})
	}))
	defer mockServer.Close()

	svc := payments.NewPaymentService(db, payments.ServiceConfig{
		AntiFraudServiceURL: mockServer.URL,
		AntiFraudTimeout:    2 * time.Second,
		AntiFraudSecretKey:  secret,
	}, mockServer.Client())

	req := payments.PaymentRequest{
		OrderID:    "0191234a-5b6c-7123-8000-000000000011",
		CustomerID: customerID,
		Amount:     amount,
	}

	_, err := svc.ProcessPayment(context.Background(), req)
	assert.Error(t, err)
	var downstreamErr *payments.DownstreamError
	assert.ErrorAs(t, err, &downstreamErr)
	assert.Equal(t, "antifraud", downstreamErr.Service)
	assert.Contains(t, downstreamErr.Message, "signature verification failed")
}

func TestProcessPayment_InvalidOrderID(t *testing.T) {
	db := setupTestDB(t)
	svc := payments.NewPaymentService(db, payments.ServiceConfig{}, nil)

	req := payments.PaymentRequest{
		OrderID:    "not-a-valid-uuid",
		CustomerID: "CUST-1",
		Amount:     50.00,
	}

	_, err := svc.ProcessPayment(context.Background(), req)
	assert.ErrorIs(t, err, payments.ErrInvalidOrderID)
}

func TestProcessPayment_InvalidAmount(t *testing.T) {
	db := setupTestDB(t)
	svc := payments.NewPaymentService(db, payments.ServiceConfig{}, nil)

	req := payments.PaymentRequest{
		OrderID:    "0191234a-5b6c-7123-8000-000000000001",
		CustomerID: "CUST-1",
		Amount:     0,
	}

	_, err := svc.ProcessPayment(context.Background(), req)
	assert.ErrorIs(t, err, payments.ErrInvalidAmount)
}

func TestProcessPayment_DownstreamTimeout(t *testing.T) {
	db := setupTestDB(t)

	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(100 * time.Millisecond)
	}))
	defer mockServer.Close()

	svc := payments.NewPaymentService(db, payments.ServiceConfig{
		AntiFraudServiceURL: mockServer.URL,
		AntiFraudTimeout:    20 * time.Millisecond,
	}, mockServer.Client())

	req := payments.PaymentRequest{
		OrderID:    "0191234a-5b6c-7123-8000-000000000003",
		CustomerID: "CUST-TIMEOUT",
		Amount:     10.00,
	}

	_, err := svc.ProcessPayment(context.Background(), req)
	assert.ErrorIs(t, err, payments.ErrDownstreamTimeout)
}
