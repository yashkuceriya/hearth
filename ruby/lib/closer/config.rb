# frozen_string_literal: true

module Closer
  # Centralized configuration loaded from environment variables.
  class Config
    attr_reader :grpc_port, :http_port, :log_level, :db_host, :db_port,
                :db_user, :db_password, :db_name

    def initialize
      @grpc_port = Integer(ENV.fetch("GRPC_PORT", "50055"))
      @http_port = Integer(ENV.fetch("HTTP_PORT", "8084"))
      @log_level = ENV.fetch("LOG_LEVEL", "info")
      @db_host = ENV.fetch("POSTGRES_HOST", "localhost")
      @db_port = Integer(ENV.fetch("POSTGRES_PORT", "5432"))
      @db_user = ENV.fetch("POSTGRES_USER", "hearth")
      @db_password = ENV.fetch("POSTGRES_PASSWORD", "hearth_dev")
      @db_name = ENV.fetch("CLOSER_DB", "hearth_closer")
    end

    def database_url
      "postgres://#{@db_user}:#{@db_password}@#{@db_host}:#{@db_port}/#{@db_name}"
    end
  end
end
