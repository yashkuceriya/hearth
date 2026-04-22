# frozen_string_literal: true

module Closer
  module Negotiation
    # Financial guardrails for automated negotiation.
    # Every counter-offer MUST pass guardrail checks before submission.
    # Post-NAR: also validates concession/compensation structures.
    class Guardrail
      GuardrailResult = Struct.new(:within_bounds, :violations, :floor_cents, :ceiling_cents, :expected_margin, keyword_init: true)
      ConcessionValidation = Struct.new(:compliant, :issues, keyword_init: true)

      # Default guardrail parameters (would be per-market/per-property in production)
      DEFAULT_FLOOR_MARGIN = 0.02    # 2% minimum margin
      DEFAULT_CEILING_MARGIN = 0.15  # 15% maximum margin (anti-gouging)
      DEFAULT_MAX_CONCESSION_PCT = 0.06  # 6% max total concessions

      def initialize(floor_margin: DEFAULT_FLOOR_MARGIN, ceiling_margin: DEFAULT_CEILING_MARGIN,
                     max_concession_pct: DEFAULT_MAX_CONCESSION_PCT)
        @floor_margin = floor_margin
        @ceiling_margin = ceiling_margin
        @max_concession_pct = max_concession_pct
      end

      # Check whether a proposed price + concessions are within Hearth's risk tolerance.
      def check(valuation_cents:, proposed_price_cents:, concessions_cents: 0)
        violations = []

        floor_cents = (valuation_cents * (1 - @floor_margin)).to_i
        ceiling_cents = (valuation_cents * (1 + @ceiling_margin)).to_i

        if proposed_price_cents < floor_cents
          violations << "Proposed price $#{proposed_price_cents / 100} is below floor " \
                        "$#{floor_cents / 100} (#{(@floor_margin * 100).round(1)}% margin minimum)"
        end

        if proposed_price_cents > ceiling_cents
          violations << "Proposed price $#{proposed_price_cents / 100} exceeds ceiling " \
                        "$#{ceiling_cents / 100} (#{(@ceiling_margin * 100).round(1)}% margin maximum)"
        end

        # Check concession limits
        if concessions_cents > 0
          concession_pct = concessions_cents.to_f / proposed_price_cents
          if concession_pct > @max_concession_pct
            violations << "Total concessions #{(concession_pct * 100).round(1)}% exceed " \
                          "maximum #{(@max_concession_pct * 100).round(1)}%"
          end
        end

        # Calculate expected margin
        net_proceeds = proposed_price_cents - concessions_cents
        expected_margin = (net_proceeds - valuation_cents).to_f / valuation_cents

        GuardrailResult.new(
          within_bounds: violations.empty?,
          violations: violations,
          floor_cents: floor_cents,
          ceiling_cents: ceiling_cents,
          expected_margin: expected_margin
        )
      end

      # Post-NAR: validates that concession/compensation structures are compliant.
      # After Aug 17, 2024: MLS can't display compensation offers,
      # buyer agreements specifying compensation required before tours.
      def validate_concession(type:, amount_cents:, description: "")
        issues = []

        valid_types = %w[seller_concession closing_cost_credit repair_credit buyer_agent_compensation]
        unless valid_types.include?(type)
          issues << "Unknown concession type: #{type}. Valid types: #{valid_types.join(', ')}"
        end

        if amount_cents <= 0
          issues << "Concession amount must be positive"
        end

        # Post-NAR check: buyer agent compensation must be structured as seller concession
        # or paid directly by buyer, NOT offered through MLS
        if type == "buyer_agent_compensation" && description.downcase.include?("mls")
          issues << "Post-NAR (effective 2024-08-17): buyer agent compensation cannot be " \
                    "offered or displayed through MLS. Must be structured as seller concession " \
                    "or buyer-paid."
        end

        ConcessionValidation.new(compliant: issues.empty?, issues: issues)
      end
    end
  end
end
