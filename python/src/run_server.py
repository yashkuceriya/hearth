"""
Production entry point. Run with: python src/run_server.py
Or from Docker: PYTHONPATH=/app/src python -c "from run_server import main; main()"
"""

import os
import sys
import signal
import logging
import json
from concurrent import futures
from datetime import datetime, timezone

from config import ServiceConfig
from health import start_health_server


def setup_logging(config: ServiceConfig):
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            return json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "service": config.name,
            })

    level = getattr(logging, config.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    if config.log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            f"%(asctime)s [{config.name}] [%(levelname)s] %(name)s: %(message)s"
        ))
    logging.basicConfig(level=level, handlers=[handler])


def main():
    import grpc
    from grpc_health.v1 import health_pb2, health_pb2_grpc
    from grpc_health.v1.health import HealthServicer

    config = ServiceConfig.from_env()
    setup_logging(config)
    logger = logging.getLogger(__name__)

    logger.info(f"Starting {config.name} service")
    logger.info(f"  gRPC port: {config.grpc_port}")
    logger.info(f"  HTTP port: {config.http_port}")
    logger.info(f"  Database: {config.db.host}:{config.db.port}/{config.db.name}")

    # Start HTTP health server
    start_health_server(config.http_port, config.name)

    # Create gRPC server
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )

    # Health check
    health_servicer = HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set(config.name, health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)

    server.add_insecure_port(f"0.0.0.0:{config.grpc_port}")

    # Graceful shutdown
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        server.stop(grace=5)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    server.start()
    logger.info(f"{config.name} gRPC server started on port {config.grpc_port}")
    server.wait_for_termination()
    logger.info(f"{config.name} service stopped")


if __name__ == "__main__":
    main()
