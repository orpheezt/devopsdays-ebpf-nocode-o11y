package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"

	"payment-go/src/config"
	"payment-go/src/db"
	"payment-go/src/health"
	"payment-go/src/payments"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}))
	slog.SetDefault(logger)

	slog.Info("starting payment-go microservice...")

	cfg := config.Load()
	slog.Info("configuration loaded",
		"port", cfg.Port,
		"env", cfg.Environment,
		"antifraud_url", cfg.AntiFraudServiceURL,
		"antifraud_timeout", cfg.AntiFraudTimeout.String(),
	)

	if cfg.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	database, err := db.InitDB(cfg.DBDSN)
	if err != nil {
		slog.Error("failed to initialize database", "error", err)
		os.Exit(1)
	}

	paymentService := payments.NewPaymentService(database, payments.ServiceConfig{
		AntiFraudServiceURL: cfg.AntiFraudServiceURL,
		AntiFraudTimeout:    cfg.AntiFraudTimeout,
		AntiFraudSecretKey:  cfg.AntiFraudSecretKey,
	}, nil)
	paymentHandler := payments.NewHandler(paymentService)

	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(slogMiddleware())

	health.RegisterRoutes(router, database)
	payments.RegisterRoutes(router, paymentHandler)

	serverAddr := fmt.Sprintf(":%s", cfg.Port)
	srv := &http.Server{
		Addr:         serverAddr,
		Handler:      router,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		slog.Info("HTTP server listening", "addr", serverAddr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			slog.Error("HTTP server failed", "error", err)
			os.Exit(1)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	sig := <-quit

	slog.Info("received shutdown signal", "signal", sig.String())

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		slog.Error("server forced to shutdown", "error", err)
	} else {
		slog.Info("server exited gracefully")
	}
}

func slogMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		raw := c.Request.URL.RawQuery

		c.Next()

		latency := time.Since(start)
		status := c.Writer.Status()

		if raw != "" {
			path = path + "?" + raw
		}

		attrs := []slog.Attr{
			slog.Int("status", status),
			slog.String("method", c.Request.Method),
			slog.String("path", path),
			slog.String("ip", c.ClientIP()),
			slog.Duration("latency", latency),
			slog.Int("bytes", c.Writer.Size()),
		}

		if len(c.Errors) > 0 {
			attrs = append(attrs, slog.String("error", c.Errors.String()))
			slog.LogAttrs(c.Request.Context(), slog.LevelError, "HTTP Request Error", attrs...)
		} else {
			slog.LogAttrs(c.Request.Context(), slog.LevelInfo, "HTTP Request", attrs...)
		}
	}
}
