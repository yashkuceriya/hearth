# frozen_string_literal: true

module Closer
  module Negotiation
    # Automated negotiation engine that operates within financial guardrails.
    # Handles counter-offers within predefined boundaries set by Hearth.
    class Engine
      NegotiationRound = Struct.new(
        :id, :transaction_id, :round_number, :proposed_price_cents,
        :concessions, :proposer, :outcome, :created_at,
        keyword_init: true
      )

      Concession = Struct.new(:type, :amount_cents, :description, :post_nar_compliant, keyword_init: true)

      def initialize(guardrail: Guardrail.new)
        @guardrail = guardrail
        @rounds = Hash.new { |h, k| h[k] = [] }
      end

      # Submit an initial offer
      def submit_offer(transaction_id:, proposed_price_cents:, concessions: [], proposer: "buyer")
        round = create_round(
          transaction_id: transaction_id,
          proposed_price_cents: proposed_price_cents,
          concessions: concessions,
          proposer: proposer,
          outcome: :pending
        )
        @rounds[transaction_id] << round
        round
      end

      # Generate a counter-offer within guardrails
      def counter(transaction_id:, valuation_cents:, their_price_cents:,
                  our_floor_cents:, our_target_cents:, max_rounds: 3)
        rounds = @rounds[transaction_id]
        round_number = rounds.size + 1

        # If we've exceeded max rounds, reject
        if round_number > max_rounds
          return create_round(
            transaction_id: transaction_id,
            proposed_price_cents: their_price_cents,
            concessions: [],
            proposer: "agent",
            outcome: :rejected
          )
        end

        # Calculate counter-offer price (split the difference, biased toward our target)
        gap = their_price_cents - our_target_cents
        counter_price = our_target_cents + (gap * 0.4).to_i  # Give 40% of the gap

        # Enforce guardrails
        result = @guardrail.check(
          valuation_cents: valuation_cents,
          proposed_price_cents: counter_price
        )

        unless result.within_bounds
          # Clamp to guardrail bounds
          counter_price = [counter_price, result.floor_cents].max
          counter_price = [counter_price, result.ceiling_cents].min
        end

        # If counter is essentially their price, accept
        if (counter_price - their_price_cents).abs < 100_00  # Within $100
          round = create_round(
            transaction_id: transaction_id,
            proposed_price_cents: their_price_cents,
            concessions: [],
            proposer: "agent",
            outcome: :accepted
          )
        else
          round = create_round(
            transaction_id: transaction_id,
            proposed_price_cents: counter_price,
            concessions: [],
            proposer: "agent",
            outcome: :countered
          )
        end

        @rounds[transaction_id] << round
        round
      end

      def get_rounds(transaction_id)
        @rounds[transaction_id]
      end

      private

      def create_round(transaction_id:, proposed_price_cents:, concessions:, proposer:, outcome:)
        rounds = @rounds[transaction_id]
        NegotiationRound.new(
          id: SecureRandom.uuid,
          transaction_id: transaction_id,
          round_number: rounds.size + 1,
          proposed_price_cents: proposed_price_cents,
          concessions: concessions,
          proposer: proposer,
          outcome: outcome,
          created_at: Time.now.utc
        )
      end
    end
  end
end
