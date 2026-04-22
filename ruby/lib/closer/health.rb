# frozen_string_literal: true

require "webrick"
require "json"

module Closer
  # Lightweight HTTP health check server for container orchestration.
  class HealthServer
    def initialize(port:, logger: nil)
      @port = port
      @logger = logger
      @server = nil
    end

    def start
      @server = WEBrick::HTTPServer.new(
        Port: @port,
        Logger: WEBrick::Log.new("/dev/null"),
        AccessLog: []
      )

      @server.mount_proc "/healthz" do |_req, res|
        res.content_type = "application/json"
        res.body = '{"status":"healthy"}'
      end

      @server.mount_proc "/readyz" do |_req, res|
        res.content_type = "application/json"
        res.body = '{"status":"ready"}'
      end

      Thread.new { @server.start }
      @logger&.info("Health check server started on port #{@port}")
    end

    def stop
      @server&.shutdown
    end
  end
end
