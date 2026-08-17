package health

import (
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

func RegisterRoutes(router gin.IRoutes, db *gorm.DB) {
	router.GET("/livez", LivenessHandler())
	router.GET("/readyz", ReadinessHandler(db))
}
