package payments

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"

	"payment-go/src/models"
)

type Service interface {
	ProcessPayment(ctx context.Context, req PaymentRequest) (*PaymentResponse, error)
}

type ServiceConfig struct {
	AntiFraudServiceURL string
	AntiFraudTimeout    time.Duration
	AntiFraudSecretKey  string
}

type PaymentService struct {
	db         *gorm.DB
	cfg        ServiceConfig
	httpClient *http.Client
}

func NewPaymentService(db *gorm.DB, cfg ServiceConfig, client *http.Client) *PaymentService {
	if client == nil {
		client = &http.Client{
			Timeout: cfg.AntiFraudTimeout,
		}
	}
	return &PaymentService{
		db:         db,
		cfg:        cfg,
		httpClient: client,
	}
}

func (s *PaymentService) ProcessPayment(ctx context.Context, req PaymentRequest) (*PaymentResponse, error) {
	if req.Amount <= 0 {
		return nil, ErrInvalidAmount
	}

	orderUUID, err := uuid.Parse(req.OrderID)
	if err != nil {
		return nil, ErrInvalidOrderID
	}

	paymentUUID, err := uuid.NewV7()
	if err != nil {
		slog.Error("failed to generate uuid v7", "error", err)
		return nil, fmt.Errorf("failed to generate payment id: %w", err)
	}
	paymentIDStr := paymentUUID.String()

	antifraudURL := fmt.Sprintf("%s/check-fraud?customer_id=%s&amount=%.2f",
		strings.TrimRight(s.cfg.AntiFraudServiceURL, "/"),
		url.QueryEscape(req.CustomerID),
		req.Amount,
	)

	reqCtx, cancel := context.WithTimeout(ctx, s.cfg.AntiFraudTimeout)
	defer cancel()

	httpReq, err := http.NewRequestWithContext(reqCtx, http.MethodGet, antifraudURL, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create antifraud request: %w", err)
	}
	httpReq.Header.Set("Accept", "application/json")

	slog.Info("querying antifraud engine", "url", antifraudURL, "order_id", req.OrderID, "payment_id", paymentIDStr)

	resp, err := s.httpClient.Do(httpReq)
	if err != nil {
		if errors.Is(err, context.DeadlineExceeded) || osIsTimeout(err) {
			slog.Warn("antifraud request timed out", "order_id", req.OrderID, "error", err)
			return nil, ErrDownstreamTimeout
		}
		slog.Error("antifraud request failed", "order_id", req.OrderID, "error", err)
		return nil, &DownstreamError{Service: "antifraud", Message: err.Error()}
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		slog.Warn("antifraud returned non-2xx status", "status", resp.StatusCode, "order_id", req.OrderID)
		return nil, &DownstreamError{
			Service:    "antifraud",
			StatusCode: resp.StatusCode,
			Message:    fmt.Sprintf("antifraud returned status %d", resp.StatusCode),
		}
	}

	var fraudAssessment FraudAssessment
	if err := json.NewDecoder(resp.Body).Decode(&fraudAssessment); err != nil {
		slog.Error("failed to decode antifraud response", "error", err)
		return nil, &DownstreamError{Service: "antifraud", Message: fmt.Sprintf("invalid json response: %v", err)}
	}

	if s.cfg.AntiFraudSecretKey != "" && fraudAssessment.Signature != "" {
		canonical := fmt.Sprintf("%s|%.2f|%.2f|%s|%s",
			req.CustomerID,
			req.Amount,
			fraudAssessment.RiskScore,
			fraudAssessment.Status,
			fraudAssessment.EvaluatedAt,
		)
		mac := hmac.New(sha256.New, []byte(s.cfg.AntiFraudSecretKey))
		mac.Write([]byte(canonical))
		expectedSig := fmt.Sprintf("sha256:%s", hex.EncodeToString(mac.Sum(nil)))

		if !hmac.Equal([]byte(fraudAssessment.Signature), []byte(expectedSig)) {
			slog.Error("antifraud HMAC signature mismatch (possible tampering)",
				"order_id", req.OrderID,
				"received_sig", fraudAssessment.Signature,
				"expected_sig", expectedSig,
			)
			return nil, &DownstreamError{Service: "antifraud", Message: "fraud assessment signature verification failed"}
		}
	}

	status := "APPROVED"
	if fraudAssessment.RiskScore >= 0.85 {
		status = "DECLINED"
	}

	payment := models.Payment{
		PaymentID:       paymentUUID,
		OrderID:         orderUUID,
		CustomerID:      req.CustomerID,
		Amount:          req.Amount,
		Status:          status,
		RiskScore:       fraudAssessment.RiskScore,
		AntiFraudEngine: fraudAssessment.Engine,
		CreatedAt:       time.Now().UTC(),
	}

	if err := s.db.WithContext(ctx).Create(&payment).Error; err != nil {
		slog.Error("failed to persist payment to database", "payment_id", paymentIDStr, "error", err)
		return nil, fmt.Errorf("failed to persist payment: %w", err)
	}

	slog.Info("payment processed successfully",
		"payment_id", paymentIDStr,
		"order_id", req.OrderID,
		"status", status,
		"risk_score", fraudAssessment.RiskScore,
	)

	return &PaymentResponse{
		PaymentID:       paymentIDStr,
		OrderID:         req.OrderID,
		Status:          payment.Status,
		AmountProcessed: payment.Amount,
		FraudAssessment: fraudAssessment,
	}, nil
}

func osIsTimeout(err error) bool {
	var netErr interface{ Timeout() bool }
	if errors.As(err, &netErr) {
		return netErr.Timeout()
	}
	return false
}
