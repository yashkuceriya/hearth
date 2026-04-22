# frozen_string_literal: true

module Closer
  module TREC
    # TREC Form 20-18: One to Four Family Residential Contract (Resale)
    # This is the most commonly used residential contract in Texas.
    #
    # IMPORTANT: This class POPULATES existing TREC form fields.
    # It does NOT draft contract language. Per TAC §537.11, license holders
    # must use TREC-approved forms and may only fill in factual/business details.
    # When Hearth acts as principal (not agent), the mandatory-use rule has
    # an exception, but we still use promulgated forms for consistency and safety.
    class OneToFourFamily
      FORM_NUMBER = "20-18"
      REVISION_DATE = "2025-06-01"

      def self.field_definitions
        @field_definitions ||= build_field_definitions
      end

      def self.build_field_definitions
        fields = {}

        # Section 1: Parties
        add_field(fields, :buyer_name, "Buyer Name", :string, required: true, section: "parties")
        add_field(fields, :seller_name, "Seller Name", :string, required: true, section: "parties")

        # Section 2: Property
        add_field(fields, :property_address, "Property Address", :string, required: true, section: "property")
        add_field(fields, :property_city, "City", :string, required: true, section: "property")
        add_field(fields, :property_county, "County", :string, required: true, section: "property")
        add_field(fields, :property_zip, "Zip Code", :string, required: true, section: "property")
        add_field(fields, :legal_description, "Legal Description", :string, required: true, section: "property")
        add_field(fields, :property_lot, "Lot", :string, section: "property")
        add_field(fields, :property_block, "Block", :string, section: "property")
        add_field(fields, :property_addition, "Addition", :string, section: "property")

        # Section 3: Sales Price
        add_field(fields, :sales_price_cents, "Sales Price", :money, required: true, section: "price")
        add_field(fields, :earnest_money_cents, "Earnest Money", :money, required: true, section: "price")
        add_field(fields, :earnest_money_payable_to, "Earnest Money Payable To", :string, section: "price")
        add_field(fields, :option_fee_cents, "Option Fee", :money, section: "price")

        # Section 4: Financing
        add_field(fields, :financing_type, "Financing Type", :enum, required: true, section: "financing",
                  validation: { values: %w[cash conventional fha va usda other] })
        add_field(fields, :loan_amount_cents, "Loan Amount", :money, section: "financing")

        # Section 5: Option Period
        add_field(fields, :option_period_days, "Option Period (days)", :integer, section: "option")

        # Section 6: Title
        add_field(fields, :title_company, "Title Company", :string, section: "title")
        add_field(fields, :title_company_address, "Title Company Address", :string, section: "title")

        # Section 7: Closing
        add_field(fields, :closing_date, "Closing Date", :date, required: true, section: "closing")

        # Section 8: Possession
        add_field(fields, :possession_type, "Possession", :enum, section: "possession",
                  validation: { values: %w[closing funding other] })

        # Section 9: Seller's Concessions
        add_field(fields, :seller_concession_cents, "Seller Concession Amount", :money, section: "concessions")
        add_field(fields, :seller_concession_description, "Concession Description", :string, section: "concessions")

        # Post-NAR: Buyer agent compensation (no longer on MLS, handled via concession)
        add_field(fields, :buyer_agent_compensation_cents, "Buyer Agent Compensation", :money, section: "concessions")
        add_field(fields, :buyer_agent_compensation_type, "Compensation Type", :enum, section: "concessions",
                  validation: { values: %w[seller_concession buyer_paid not_applicable] })

        # Contact Info
        add_field(fields, :buyer_phone, "Buyer Phone", :phone, section: "contacts")
        add_field(fields, :seller_phone, "Seller Phone", :phone, section: "contacts")
        add_field(fields, :buyer_email, "Buyer Email", :string, section: "contacts")
        add_field(fields, :seller_email, "Seller Email", :string, section: "contacts")

        fields
      end

      def self.add_field(fields, name, label, type, required: false, section: nil, validation: nil)
        fields[name.to_s] = FieldDefinition.new(
          name: name,
          label: label,
          type: type,
          required: required,
          section: section,
          validation: validation
        )
      end

      # Populate the form with provided field values.
      # Returns a hash with :populated_fields, :errors, :warnings, :is_complete, :missing_required
      def populate(field_values)
        definitions = self.class.field_definitions
        errors = []
        warnings = []
        populated = {}
        missing_required = []

        # Validate each provided field
        field_values.each do |name, value|
          defn = definitions[name.to_s]
          if defn.nil?
            warnings << "Unknown field: #{name} (ignored)"
            next
          end

          field_errors = defn.validate(value)
          if field_errors.empty?
            populated[name.to_s] = value
          else
            errors.concat(field_errors)
          end
        end

        # Check required fields
        definitions.each do |name, defn|
          next unless defn.required
          unless field_values.key?(name.to_s) || field_values.key?(name.to_sym)
            missing_required << name
          end
        end

        {
          populated_fields: populated,
          errors: errors,
          warnings: warnings,
          is_complete: errors.empty? && missing_required.empty?,
          missing_required: missing_required,
          form_number: FORM_NUMBER,
          revision_date: REVISION_DATE,
        }
      end
    end
  end
end
