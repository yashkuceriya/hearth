# frozen_string_literal: true

$LOAD_PATH.unshift File.join(__dir__)

require "logger"
require "closer/config"
require "closer/health"
require "closer/trec/field_definition"
require "closer/trec/form_registry"
require "closer/trec/one_to_four_family"
require "closer/workflow/state_machine"
require "closer/negotiation/guardrail"
require "closer/negotiation/engine"

module Closer
  class Server
    def initialize
      @config = Config.new
      @logger = Logger.new($stdout)
      @logger.level = log_level
      @logger.formatter = proc do |severity, datetime, _progname, msg|
        "#{datetime.utc.iso8601} [closer] [#{severity}] #{msg}\n"
      end
    end

    def start
      @logger.info("Starting Closer service")
      @logger.info("  gRPC port: #{@config.grpc_port}")
      @logger.info("  HTTP port: #{@config.http_port}")
      @logger.info("  Database: #{@config.db_host}:#{@config.db_port}/#{@config.db_name}")

      # Start HTTP health check
      health = HealthServer.new(port: @config.http_port, logger: @logger)
      health.start

      # Keep the main thread alive (gRPC server would go here in production)
      @logger.info("Closer service ready (health check on #{@config.http_port})")

      # Graceful shutdown
      trap("SIGTERM") { shutdown(health) }
      trap("SIGINT") { shutdown(health) }

      sleep
    rescue Interrupt
      shutdown(health)
    end

    private

    def shutdown(health)
      @logger.info("Shutting down Closer service...")
      health&.stop
      exit(0)
    end

    def log_level
      case @config.log_level.downcase
      when "debug" then Logger::DEBUG
      when "warn" then Logger::WARN
      when "error" then Logger::ERROR
      else Logger::INFO
      end
    end
  end
end

# Run if executed directly
Closer::Server.new.start if __FILE__ == $PROGRAM_NAME
