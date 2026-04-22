# frozen_string_literal: true

Sequel.migration do
  up do
    create_enum(:transaction_state, %w[
      offer_submitted under_negotiation executed
      option_period pending closing closed terminated
    ])

    create_table(:transactions) do
      column :id, :uuid, primary_key: true, default: Sequel.lit("gen_random_uuid()")
      column :property_id, :uuid, null: false
      column :buyer_lead_id, :uuid, null: false
      column :state, :transaction_state, null: false, default: "offer_submitted"
      column :offer_price_cents, :bigint, null: false
      column :product_path, String, size: 50, null: false
      DateTime :created_at, null: false, default: Sequel.lit("now()")
      DateTime :updated_at, null: false, default: Sequel.lit("now()")

      index :property_id
      index :buyer_lead_id
    end

    create_table(:transaction_events) do
      column :id, :uuid, primary_key: true, default: Sequel.lit("gen_random_uuid()")
      foreign_key :transaction_id, :transactions, type: :uuid, null: false
      column :from_state, :transaction_state
      column :to_state, :transaction_state, null: false
      column :metadata, :jsonb, null: false, default: Sequel.lit("'{}'::jsonb")
      String :triggered_by, size: 100, null: false
      DateTime :created_at, null: false, default: Sequel.lit("now()")

      index [:transaction_id, :created_at]
    end

    create_table(:milestones) do
      column :id, :uuid, primary_key: true, default: Sequel.lit("gen_random_uuid()")
      foreign_key :transaction_id, :transactions, type: :uuid, null: false
      String :name, size: 100, null: false
      DateTime :due_date
      TrueClass :completed, null: false, default: false
      DateTime :completed_at
      String :completed_by, size: 100
      DateTime :created_at, null: false, default: Sequel.lit("now()")

      unique [:transaction_id, :name]
    end

    create_table(:contracts) do
      column :id, :uuid, primary_key: true, default: Sequel.lit("gen_random_uuid()")
      foreign_key :transaction_id, :transactions, type: :uuid, null: false
      String :form_type, size: 50, null: false
      String :form_version, size: 20, null: false
      column :field_values, :jsonb, null: false
      String :pdf_storage_key, size: 500
      column :validation_errors, :jsonb, null: false, default: Sequel.lit("'[]'::jsonb")
      TrueClass :is_complete, null: false, default: false
      DateTime :created_at, null: false, default: Sequel.lit("now()")
      DateTime :updated_at, null: false, default: Sequel.lit("now()")

      index :transaction_id
    end

    create_table(:negotiation_rounds) do
      column :id, :uuid, primary_key: true, default: Sequel.lit("gen_random_uuid()")
      foreign_key :transaction_id, :transactions, type: :uuid, null: false
      Integer :round_number, null: false
      Bignum :proposed_price_cents, null: false
      column :concessions, :jsonb, null: false, default: Sequel.lit("'[]'::jsonb")
      String :proposer, size: 50, null: false
      String :outcome, size: 50, null: false, default: "pending"
      TrueClass :guardrail_check_passed
      DateTime :created_at, null: false, default: Sequel.lit("now()")

      unique [:transaction_id, :round_number]
      index [:transaction_id, :round_number]
    end
  end

  down do
    drop_table(:negotiation_rounds)
    drop_table(:contracts)
    drop_table(:milestones)
    drop_table(:transaction_events)
    drop_table(:transactions)
    drop_enum(:transaction_state)
  end
end
