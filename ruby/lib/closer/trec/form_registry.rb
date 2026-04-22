# frozen_string_literal: true

module Closer
  module TREC
    # Registry of all TREC promulgated forms with version tracking.
    # TREC publishes specific form versions with effective dates.
    # Using an outdated form in a transaction is a compliance violation.
    class FormRegistry
      FormVersionInfo = Struct.new(:form_type, :version, :effective_date, :is_current, keyword_init: true)

      def initialize
        @forms = {}
        register_standard_forms
      end

      def get_form(form_type, version: nil)
        forms = @forms[form_type.to_s]
        return nil if forms.nil? || forms.empty?

        if version
          forms.find { |f| f[:version] == version }
        else
          forms.find { |f| f[:is_current] }
        end
      end

      def get_versions(form_type)
        @forms[form_type.to_s] || []
      end

      def current_version(form_type)
        form = get_form(form_type)
        form&.dig(:version)
      end

      private

      def register_standard_forms
        # TREC Form 20-18: One to Four Family Residential Contract (Resale)
        register("one_to_four_family", [
          { version: "20-18", effective_date: "2025-06-01", is_current: true },
          { version: "20-17", effective_date: "2023-12-01", is_current: false },
        ])

        # TREC Form 40-9: Third Party Financing Addendum
        register("third_party_financing", [
          { version: "40-9", effective_date: "2023-12-01", is_current: true },
        ])

        # TREC Form 10-6: Seller's Disclosure Notice
        register("property_condition", [
          { version: "10-6", effective_date: "2023-12-01", is_current: true },
        ])

        # TREC Form 39-8: Amendment to Contract
        register("amendment", [
          { version: "39-8", effective_date: "2023-12-01", is_current: true },
        ])
      end

      def register(form_type, versions)
        @forms[form_type] = versions.map do |v|
          {
            form_type: form_type,
            version: v[:version],
            effective_date: v[:effective_date],
            is_current: v[:is_current],
          }
        end
      end
    end
  end
end
