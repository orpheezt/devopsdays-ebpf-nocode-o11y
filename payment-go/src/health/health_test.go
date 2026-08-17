package health_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"

	"payment-go/src/health"
)

func init() {
	gin.SetMode(gin.TestMode)
}

func TestLivenessHandler(t *testing.T) {
	router := gin.New()
	health.RegisterRoutes(router, nil)

	req, _ := http.NewRequest(http.MethodGet, "/livez", nil)
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)

	var res health.HealthStatusResponse
	err := json.Unmarshal(rec.Body.Bytes(), &res)
	require.NoError(t, err)
	assert.Equal(t, "ok", res.Status)
}

func TestReadinessHandler_NilDB(t *testing.T) {
	router := gin.New()
	health.RegisterRoutes(router, nil)

	req, _ := http.NewRequest(http.MethodGet, "/readyz", nil)
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusServiceUnavailable, rec.Code)

	var res health.ReadinessStatusResponse
	err := json.Unmarshal(rec.Body.Bytes(), &res)
	require.NoError(t, err)
	assert.Equal(t, "error", res.Status)
	assert.Equal(t, "disconnected", res.Database)
	assert.NotEmpty(t, res.Error)
}

func TestReadinessHandler_ConnectedAndClosed(t *testing.T) {
	gormDB, err := gorm.Open(sqlite.Open("file::memory:?cache=shared"), &gorm.Config{})
	require.NoError(t, err)

	router := gin.New()
	health.RegisterRoutes(router, gormDB)

	req, _ := http.NewRequest(http.MethodGet, "/readyz", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)
	var res health.ReadinessStatusResponse
	err = json.Unmarshal(rec.Body.Bytes(), &res)
	require.NoError(t, err)
	assert.Equal(t, "ok", res.Status)
	assert.Equal(t, "connected", res.Database)

	sqlDB, err := gormDB.DB()
	require.NoError(t, err)
	_ = sqlDB.Close()

	req2, _ := http.NewRequest(http.MethodGet, "/readyz", nil)
	rec2 := httptest.NewRecorder()
	router.ServeHTTP(rec2, req2)

	assert.Equal(t, http.StatusServiceUnavailable, rec2.Code)
	var res2 health.ReadinessStatusResponse
	err = json.Unmarshal(rec2.Body.Bytes(), &res2)
	require.NoError(t, err)
	assert.Equal(t, "error", res2.Status)
	assert.Equal(t, "disconnected", res2.Database)
}
