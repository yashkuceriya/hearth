# frozen_string_literal: true

require "closer/trec/field_definition"

module Closer
  module TREC
    # TREC Form 40-9: Third Party Financing Addendum.
    # Used when buyer financing is contingent on third-party loan approval.
    # Follows the same POPULATE-only discipline as OneToFourFamily (#1): factual/
    # business data only, no novel legal language. UPL guard runs per-field.
    class ThirdPartyFinancing
      FORM_NUMBER = "40-9"
      REVISION_DATE = "2023-12-01"

      def self.field_definitions
        @field_definitions ||= build_field_definitions
      end

      def self.build_field_definitions
        fields = {}
        add_field(fields, :buyer_name, "Buyer Name", :string, required: true, section: "parties")
        add_field(fields, :seller_name, "Seller Name", :string, required: true, section: "parties")
        add_field(fields, :property_address, "Property Address", :string, required: true, section: "property")

        add_field(fields, :loan_type, "Loan Type", :enum, required: true, section: "loan",
                  validation: { values: %w[conventional fha va usda other] })
        add_field(fields, :loan_amount_cents, "Loan Amount", :money, required: true, section: "loan")
        add_field(fields, :loan_term_years, "Loan Term (years)", :integer, required: true, section: "loan")
        add_field(fields, :interest_rate_bps, "Interest Rate (basis points)", :integer, section: "loan")
        add_field(fields, :origination_fee_bps, "Origination Fee (basis points)", :integer, section: "loan")

        add_field(fields, :buyer_approval_deadline, "Buyer Approval Deadline", :date, required: true, section: "timing")
        add_field(fields, :appraisal_contingency_days, "Appraisal Contingency (days)", :integer, section: "timing")

        add_field(fields, :lender_name, "Lender Name", :string, section: "lender")
        add_field(fields, :lender_phone, "Lender Phone", :phone, section: "lender")
        fields
      end

      def self.add_field(fields, name, label, type, required: false, section: nil, validation: nil)
        fields[name.to_s] = FieldDefinition.new(
          name: name, label: label, type: type,
          required: required, section: section, validation: validation,
        )
      end

      def populate(field_values)
        Populator.run(self.class.field_definitions, field_values, FORM_NUMBER, REVISION_DATE)
      end
    end
  end
end
