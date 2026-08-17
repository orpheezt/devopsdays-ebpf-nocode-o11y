package models

import (
	"time"

	"github.com/google/uuid"
)

type Payment struct {
	PaymentID       uuid.UUID `gorm:"type:uuid;primaryKey;column:payment_id" json:"payment_id"`
	OrderID         uuid.UUID `gorm:"type:uuid;not null;index:idx_payments_order_id;column:order_id" json:"order_id"`
	CustomerID      string    `gorm:"size:64;not null;column:customer_id" json:"customer_id"`
	Amount          float64   `gorm:"type:numeric(10,2);not null;column:amount" json:"amount"`
	Status          string    `gorm:"size:32;not null;column:status" json:"status"`
	RiskScore       float64   `gorm:"type:numeric(5,4);column:risk_score" json:"risk_score"`
	AntiFraudEngine string    `gorm:"size:64;column:antifraud_engine" json:"antifraud_engine"`
	CreatedAt       time.Time `gorm:"column:created_at;not null" json:"created_at"`
}

func (Payment) TableName() string {
	return "payments"
}
