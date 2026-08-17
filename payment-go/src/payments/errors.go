package payments

import (
	"errors"
	"fmt"
)

var (
	ErrInvalidAmount     = errors.New("amount must be greater than zero")
	ErrInvalidOrderID    = errors.New("order_id must be a valid UUID")
	ErrDownstreamTimeout = errors.New("antifraud downstream service timed out")
)

type DownstreamError struct {
	Service    string
	StatusCode int
	Message    string
}

func (e *DownstreamError) Error() string {
	if e.StatusCode > 0 {
		return fmt.Sprintf("downstream %s error (status %d): %s", e.Service, e.StatusCode, e.Message)
	}
	return fmt.Sprintf("downstream %s error: %s", e.Service, e.Message)
}
