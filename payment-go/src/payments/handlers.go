package payments

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	service Service
}

func NewHandler(service Service) *Handler {
	return &Handler{
		service: service,
	}
}

func (h *Handler) Pay(c *gin.Context) {
	var req PaymentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid payment request payload: " + err.Error(),
		})
		return
	}

	if req.Amount <= 0 {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Amount must be greater than zero",
		})
		return
	}

	resp, err := h.service.ProcessPayment(c.Request.Context(), req)
	if err != nil {
		if errors.Is(err, ErrInvalidAmount) || errors.Is(err, ErrInvalidOrderID) {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		if errors.Is(err, ErrDownstreamTimeout) {
			c.JSON(http.StatusGatewayTimeout, gin.H{"error": "Downstream antifraud service timed out"})
			return
		}

		var downstreamErr *DownstreamError
		if errors.As(err, &downstreamErr) {
			c.JSON(http.StatusBadGateway, gin.H{
				"error": "Downstream service error: " + downstreamErr.Message,
			})
			return
		}

		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to process payment",
		})
		return
	}

	c.JSON(http.StatusOK, resp)
}
