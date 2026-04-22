# frozen_string_literal: true

module Closer
  module TREC
    # Defines a single field on a TREC form.
    # Fields are strictly typed and validated: only factual/business data is allowed.
    class FieldDefinition
      attr_reader :name, :label, :type, :required, :section, :validation

      VALID_TYPES = %i[string money date boolean address phone enum integer].freeze

      def initialize(name:, label:, type:, required: false, section: nil, validation: nil)
        raise ArgumentError, "Invalid field type: #{type}" unless VALID_TYPES.include?(type)

        @name = name.to_s.freeze
        @label = label.freeze
        @type = type
        @required = required
        @section = section&.freeze
        @validation = validation
      end

      def validate(value)
        errors = []
        errors << "#{@name} is required" if @required && (value.nil? || value.to_s.strip.empty?)

        return errors if value.nil? || value.to_s.strip.empty?

        case @type
        when :money
          errors << "#{@name} must be a positive integer (cents)" unless value.is_a?(Integer) && value >= 0
        when :date
          unless value.is_a?(String) && value.match?(/\A\d{4}-\d{2}-\d{2}\z/)
            errors << "#{@name} must be a date in YYYY-MM-DD format"
          end
        when :boolean
          errors << "#{@name} must be true or false" unless [true, false, "true", "false"].include?(value)
        when :phone
          errors << "#{@name} must be a valid phone number" unless value.to_s.match?(/\A[\d\-\(\)\s\+]+\z/)
        when :integer
          errors << "#{@name} must be an integer" unless value.is_a?(Integer)
        when :enum
          if @validation && @validation[:values]
            unless @validation[:values].include?(value.to_s)
              errors << "#{@name} must be one of: #{@validation[:values].join(', ')}"
            end
          end
        end

        # UPL guard: no free-text field should contain legal language patterns
        if @type == :string && value.is_a?(String)
          if contains_legal_language?(value)
            errors << "#{@name} contains what appears to be novel legal language. " \
                      "TREC forms may only be populated with factual/business details per TAC §537.11"
          end
        end

        errors
      end

      private

      # Detect patterns that suggest someone is trying to draft legal clauses
      def contains_legal_language?(text)
        legal_patterns = [
          /\bhereby\b/i,
          /\bwhereas\b/i,
          /\bnotwithstanding\b/i,
          /\bshall be liable\b/i,
          /\bindemnif/i,
          /\bhold harmless\b/i,
          /\bwaive[s]?\s+(any|all)\s+right/i,
          /\brepresent[s]?\s+and\s+warrant/i,
        ]
        legal_patterns.any? { |pattern| text.match?(pattern) }
      end
    end
  end
end
