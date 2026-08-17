package health

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

func LivenessHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.JSON(http.StatusOK, HealthStatusResponse{
			Status: "ok",
		})
	}
}

func ReadinessHandler(db *gorm.DB) gin.HandlerFunc {
	return func(c *gin.Context) {
		if db == nil {
			c.JSON(http.StatusServiceUnavailable, ReadinessStatusResponse{
				Status:   "error",
				Database: "disconnected",
				Error:    "database connection is nil",
			})
			return
		}

		sqlDB, err := db.DB()
		if err != nil {
			c.JSON(http.StatusServiceUnavailable, ReadinessStatusResponse{
				Status:   "error",
				Database: "disconnected",
				Error:    err.Error(),
			})
			return
		}

		ctx, cancel := context.WithTimeout(c.Request.Context(), 2*time.Second)
		defer cancel()

		if err := sqlDB.PingContext(ctx); err != nil {
			c.JSON(http.StatusServiceUnavailable, ReadinessStatusResponse{
				Status:   "error",
				Database: "disconnected",
				Error:    err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, ReadinessStatusResponse{
			Status:   "ok",
			Database: "connected",
		})
	}
}
