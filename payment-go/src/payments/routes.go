package payments

import (
	"github.com/gin-gonic/gin"
)

func RegisterRoutes(router gin.IRoutes, handler *Handler) {
	router.POST("/pay", handler.Pay)
}
