package main

import (
	"database/sql"
	"fmt"
	"net"
	"os"
	"os/signal"
	"syscall"

	_ "github.com/lib/pq"
	"github.com/yashkuceriya/hearth/internal/channel"
	"github.com/yashkuceriya/hearth/internal/compliance"
	"github.com/yashkuceriya/hearth/internal/orchestrator"
	"github.com/yashkuceriya/hearth/internal/routing"
	"github.com/yashkuceriya/hearth/internal/session"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/grpc/health"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
)

func main() {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	// Database connection
	dbURL := fmt.Sprintf("postgres://%s:%s@%s:%s/%s?sslmode=disable",
		envOrDefault("POSTGRES_USER", "hearth"),
		envOrDefault("POSTGRES_PASSWORD", "hearth_dev"),
		envOrDefault("POSTGRES_HOST", "localhost"),
		envOrDefault("POSTGRES_PORT", "5432"),
		envOrDefault("ORCHESTRATOR_DB", "hearth_orchestrator"),
	)

	db, err := sql.Open("postgres", dbURL)
	if err != nil {
		logger.Fatal("failed to connect to database", zap.Error(err))
	}
	defer db.Close()

	if err := db.Ping(); err != nil {
		logger.Fatal("failed to ping database", zap.Error(err))
	}

	// Initialize components
	sessionMgr := session.NewManager(db, logger)
	router := routing.NewProductPathRouter(logger)
	tourGate := routing.NewTourEligibilityGate(logger)

	// Compliance gateway (lawyer client is a placeholder until Python service is wired)
	gw := compliance.NewGateway(nil, logger)

	// Orchestrator engine
	engine := orchestrator.NewEngine(sessionMgr, router, tourGate, gw, logger)

	// Register SMS adapter if configured
	if sid := os.Getenv("TWILIO_ACCOUNT_SID"); sid != "" {
		sms := channel.NewSMSAdapter(
			sid,
			os.Getenv("TWILIO_AUTH_TOKEN"),
			os.Getenv("TWILIO_PHONE_NUMBER"),
			logger,
		)
		engine.RegisterAdapter(sms)
	}

	// Start gRPC server
	port := envOrDefault("ORCHESTRATOR_GRPC_PORT", "50051")
	lis, err := net.Listen("tcp", ":"+port)
	if err != nil {
		logger.Fatal("failed to listen", zap.Error(err))
	}

	grpcServer := grpc.NewServer()

	// Health check
	healthServer := health.NewServer()
	healthpb.RegisterHealthServer(grpcServer, healthServer)
	healthServer.SetServingStatus("orchestrator", healthpb.HealthCheckResponse_SERVING)

	logger.Info("orchestrator starting", zap.String("port", port))

	// Graceful shutdown
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		<-sigCh
		logger.Info("shutting down")
		grpcServer.GracefulStop()
	}()

	_ = engine // Will be registered as gRPC service handlers

	if err := grpcServer.Serve(lis); err != nil {
		logger.Fatal("failed to serve", zap.Error(err))
	}
}

func envOrDefault(key, defaultVal string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultVal
}
