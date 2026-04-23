# frozen_string_literal: true

require "sequel"

module Closer
  # Runs Sequel migrations from db/migrate/ on service boot.
  # Skips silently if Postgres is unreachable OR if Sequel's migration
  # extension is unavailable — this keeps unit tests hermetic and lets the
  # service boot in dev without a DB.
  module Migrator
    MIGRATION_DIR = File.expand_path("../../../db/migrate", __dir__)

    def self.run(config, logger)
      Sequel.extension(:migration)
      db = Sequel.connect(config.db_url)
      logger.info("Applying Sequel migrations from #{MIGRATION_DIR}")
      Sequel::Migrator.run(db, MIGRATION_DIR)
      logger.info("Migrations applied")
    rescue LoadError, Sequel::DatabaseConnectionError => e
      logger.warn("Skipping migrations: #{e.class}: #{e.message}")
    ensure
      db&.disconnect
    end
  end
end
