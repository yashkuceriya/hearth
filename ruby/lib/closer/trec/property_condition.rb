# frozen_string_literal: true

require "closer/trec/field_definition"

module Closer
  module TREC
    # TREC Form 10-6: Seller's Disclosure Notice.
    # Texas Property Code §5.008 requires a seller's disclosure on most residential
    # resales. Per-item answers default to "unknown" unless the seller confirms.
    # Never drafts prose; populates yes/no/unknown + factual fields only.
    class PropertyCondition
      FORM_NUMBER = "10-6"
      REVISION_DATE = "2023-12-01"

      TRINARY = { values: %w[yes no unknown] }.freeze

      def self.field_definitions
        @field_definitions ||= build_field_definitions
      end

      def self.build_field_definitions
        fields = {}
        add_field(fields, :seller_name, "Seller Name", :string, required: true, section: "parties")
        add_field(fields, :property_address, "Property Address", :string, required: true, section: "property")
        add_field(fields, :years_occupied, "Years Seller Occupied", :integer, section: "property")

        # Known defects: each is yes/no/unknown. Defaults remain blank until
        # confirmed — Hearth never auto-answers these on the seller's behalf.
        %i[
          foundation_issues roof_issues plumbing_issues electrical_issues
          hvac_issues termite_issues flood_history fire_damage structural_repairs
          active_leaks mold_known lead_paint_known asbestos_known
        ].each do |item|
          add_field(fields, item, item.to_s.tr("_", " ").capitalize, :enum,
                    section: "known_defects", validation: TRINARY)
        end

        # Factual date/age fields
        add_field(fields, :roof_age_years, "Roof Age (years)", :integer, section: "age")
        add_field(fields, :hvac_age_years, "HVAC Age (years)", :integer, section: "age")
        add_field(fields, :water_heater_age_years, "Water Heater Age (years)", :integer, section: "age")

        # Utilities
        %i[has_gas has_water_well has_septic has_solar].each do |u|
          add_field(fields, u, u.to_s.tr("_", " ").capitalize, :boolean, section: "utilities")
        end

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
