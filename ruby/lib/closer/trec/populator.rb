# frozen_string_literal: true

module Closer
  module TREC
    # Shared populate logic for TREC forms. Each form class defines its field
    # definitions and delegates actual field-filling here. Single source of
    # truth so the populate semantics stay consistent across forms.
    module Populator
      def self.run(definitions, field_values, form_number, revision_date)
        errors = []
        warnings = []
        populated = {}
        missing_required = []

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
          form_number: form_number,
          revision_date: revision_date,
        }
      end
    end
  end
end
