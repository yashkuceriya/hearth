# frozen_string_literal: true

require "closer/trec/field_definition"

module Closer
  module TREC
    # TREC Form 39-8: Amendment to Contract.
    # Used for mid-deal changes: price adjustments, closing-date shifts, repair
    # credits. Factual fields only. The amendment language itself is fixed by
    # TREC; we populate blanks.
    class Amendment
      FORM_NUMBER = "39-8"
      REVISION_DATE = "2023-12-01"

      def self.field_definitions
        @field_definitions ||= build_field_definitions
      end

      def self.build_field_definitions
        fields = {}
        add_field(fields, :original_contract_date, "Original Contract Date", :date, required: true, section: "reference")
        add_field(fields, :buyer_name, "Buyer Name", :string, required: true, section: "parties")
        add_field(fields, :seller_name, "Seller Name", :string, required: true, section: "parties")
        add_field(fields, :property_address, "Property Address", :string, required: true, section: "property")

        # Possible amendments — each is optional; at least one required at populate time
        add_field(fields, :new_sales_price_cents, "New Sales Price", :money, section: "changes")
        add_field(fields, :new_closing_date, "New Closing Date", :date, section: "changes")
        add_field(fields, :new_option_fee_cents, "New Option Fee", :money, section: "changes")
        add_field(fields, :new_option_period_days, "New Option Period (days)", :integer, section: "changes")
        add_field(fields, :repair_credit_cents, "Repair Credit", :money, section: "changes")
        add_field(fields, :seller_concession_cents, "Seller Concession", :money, section: "changes")

        add_field(fields, :effective_date, "Amendment Effective Date", :date, required: true, section: "signatures")
        fields
      end

      def self.add_field(fields, name, label, type, required: false, section: nil, validation: nil)
        fields[name.to_s] = FieldDefinition.new(
          name: name, label: label, type: type,
          required: required, section: section, validation: validation,
        )
      end

      def populate(field_values)
        result = Populator.run(self.class.field_definitions, field_values, FORM_NUMBER, REVISION_DATE)
        # Extra check: at least one of the "changes" fields must be set.
        change_keys = %i[
          new_sales_price_cents new_closing_date new_option_fee_cents
          new_option_period_days repair_credit_cents seller_concession_cents
        ].map(&:to_s)
        unless change_keys.any? { |k| field_values.key?(k) || field_values.key?(k.to_sym) }
          result[:errors] << "Amendment must change at least one term"
          result[:is_complete] = false
        end
        result
      end
    end
  end
end
