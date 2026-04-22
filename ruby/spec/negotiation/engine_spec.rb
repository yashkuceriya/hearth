# frozen_string_literal: true

require "spec_helper"

RSpec.describe Closer::Negotiation::Engine do
  subject(:engine) { described_class.new }

  describe "#submit_offer" do
    it "creates an initial offer round" do
      round = engine.submit_offer(
        transaction_id: "txn-1",
        proposed_price_cents: 47_000_000
      )
      expect(round.round_number).to eq(1)
      expect(round.outcome).to eq(:pending)
      expect(round.proposer).to eq("buyer")
    end
  end

  describe "#counter" do
    it "generates a counter-offer within guardrails" do
      engine.submit_offer(transaction_id: "txn-1", proposed_price_cents: 47_000_000)

      round = engine.counter(
        transaction_id: "txn-1",
        valuation_cents: 50_000_000,
        their_price_cents: 47_000_000,
        our_floor_cents: 49_000_000,
        our_target_cents: 51_000_000
      )
      expect(round.proposed_price_cents).to be > 47_000_000
      expect(round.outcome).to eq(:countered)
    end

    it "accepts when counter would be very close to their price" do
      engine.submit_offer(transaction_id: "txn-1", proposed_price_cents: 50_500_000)

      round = engine.counter(
        transaction_id: "txn-1",
        valuation_cents: 50_000_000,
        their_price_cents: 50_500_000,
        our_floor_cents: 49_000_000,
        our_target_cents: 50_500_000  # Target matches their price
      )
      expect(round.outcome).to eq(:accepted)
    end

    it "rejects after max rounds exceeded" do
      3.times do |i|
        engine.submit_offer(transaction_id: "txn-1", proposed_price_cents: 47_000_000 + (i * 500_000))
      end

      round = engine.counter(
        transaction_id: "txn-1",
        valuation_cents: 50_000_000,
        their_price_cents: 48_000_000,
        our_floor_cents: 49_000_000,
        our_target_cents: 51_000_000,
        max_rounds: 3
      )
      expect(round.outcome).to eq(:rejected)
    end
  end
end
