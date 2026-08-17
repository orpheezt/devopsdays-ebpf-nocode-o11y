package payments_test

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"payment-go/src/payments"
)

type mockService struct {
	processFn func(ctx context.Context, req payments.PaymentRequest) (*payments.PaymentResponse, error)
}

func (m *mockService) ProcessPayment(ctx context.Context, req payments.PaymentRequest) (*payments.PaymentResponse, error) {
	return m.processFn(ctx, req)
}

func init() {
	gin.SetMode(gin.TestMode)
}

func TestPayHandler_Success(t *testing.T) {
	mock := &mockService{
		processFn: func(ctx context.Context, req payments.PaymentRequest) (*payments.PaymentResponse, error) {
			return &payments.PaymentResponse{
				PaymentID:       "0191234a-9999-8888-8000-000000000000",
				OrderID:         req.OrderID,
				Status:          "APPROVED",
				AmountProcessed: req.Amount,
				FraudAssessment: payments.FraudAssessment{
					RiskScore: 0.02,
					Status:    "LOW_RISK",
					Engine:    "fastify-node",
				},
			}, nil
		},
	}

	router := gin.New()
	handler := payments.NewHandler(mock)
	payments.RegisterRoutes(router, handler)

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
	assert.Equal(t, "0191234a-9999-8888-8000-000000000000", res.PaymentID)
	assert.Equal(t, "0191234a-5b6c-7123-8000-000000000001", res.OrderID)
	assert.Equal(t, "APPROVED", res.Status)
	assert.Equal(t, 43.50, res.AmountProcessed)
}

func TestPayHandler_ValidationFailure(t *testing.T) {
	mock := &mockService{}
	router := gin.New()
	handler := payments.NewHandler(mock)
	payments.RegisterRoutes(router, handler)

	payload := map[string]interface{}{
		"order_id": "0191234a-5b6c-7123-8000-000000000001",
		"amount":   -10.0,
	}
	body, _ := json.Marshal(payload)

	req, _ := http.NewRequest(http.MethodPost, "/pay", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusBadRequest, rec.Code)
}

func TestPayHandler_InvalidOrderID(t *testing.T) {
	mock := &mockService{
		processFn: func(ctx context.Context, req payments.PaymentRequest) (*payments.PaymentResponse, error) {
			return nil, payments.ErrInvalidOrderID
		},
	}

	router := gin.New()
	handler := payments.NewHandler(mock)
	payments.RegisterRoutes(router, handler)

	payload := map[string]interface{}{
		"order_id":    "invalid-uuid-string",
		"customer_id": "CUST-1",
		"amount":      20.0,
	}
	body, _ := json.Marshal(payload)

	req, _ := http.NewRequest(http.MethodPost, "/pay", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusBadRequest, rec.Code)
}

func TestPayHandler_DownstreamTimeout(t *testing.T) {
	mock := &mockService{
		processFn: func(ctx context.Context, req payments.PaymentRequest) (*payments.PaymentResponse, error) {
			return nil, payments.ErrDownstreamTimeout
		},
	}

	router := gin.New()
	handler := payments.NewHandler(mock)
	payments.RegisterRoutes(router, handler)

	payload := map[string]interface{}{
		"order_id":    "0191234a-5b6c-7123-8000-000000000002",
		"customer_id": "CUST-1",
		"amount":      20.0,
	}
	body, _ := json.Marshal(payload)

	req, _ := http.NewRequest(http.MethodPost, "/pay", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusGatewayTimeout, rec.Code)
}

func TestPayHandler_DownstreamError(t *testing.T) {
	mock := &mockService{
		processFn: func(ctx context.Context, req payments.PaymentRequest) (*payments.PaymentResponse, error) {
			return nil, &payments.DownstreamError{
				Service:    "antifraud",
				StatusCode: 500,
				Message:    "internal server error",
			}
		},
	}

	router := gin.New()
	handler := payments.NewHandler(mock)
	payments.RegisterRoutes(router, handler)

	payload := map[string]interface{}{
		"order_id":    "0191234a-5b6c-7123-8000-000000000003",
		"customer_id": "CUST-1",
		"amount":      20.0,
	}
	body, _ := json.Marshal(payload)

	req, _ := http.NewRequest(http.MethodPost, "/pay", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusBadGateway, rec.Code)
}
