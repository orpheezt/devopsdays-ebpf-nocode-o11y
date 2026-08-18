package payments

type PaymentRequest struct {
	OrderID    string  `json:"order_id" binding:"required"`
	CustomerID string  `json:"customer_id" binding:"required"`
	Amount     float64 `json:"amount" binding:"required,gt=0"`
}

type FraudAssessment struct {
	RiskScore   float64  `json:"risk_score"`
	Status      string   `json:"status"`
	Engine      string   `json:"engine,omitempty"`
	Signature   string   `json:"signature,omitempty"`
	EvaluatedAt string   `json:"evaluated_at,omitempty"`
	Factors     []string `json:"factors,omitempty"`
}

type PaymentResponse struct {
	PaymentID       string          `json:"payment_id"`
	OrderID         string          `json:"order_id"`
	Status          string          `json:"status"`
	AmountProcessed float64         `json:"amount_processed"`
	FraudAssessment FraudAssessment `json:"fraud_assessment"`
}
