# frozen_string_literal: true

require "spec_helper"

RSpec.describe Closer::Negotiation::Guardrail do
  subject(:guardrail) { described_class.new }

  describe "#check" do
    let(:valuation_cents) { 50_000_000 } # $500k

    it "approves prices within bounds" do
      result = guardrail.check(
        valuation_cents: valuation_cents,
        proposed_price_cents: 51_000_000 # $510k
      )
      expect(result.within_bounds).to be true
      expect(result.violations).to be_empty
    end

    it "rejects prices below floor" do
      result = guardrail.check(
        valuation_cents: valuation_cents,
        proposed_price_cents: 40_000_000 # $400k - way below 2% floor
      )
      expect(result.within_bounds).to be false
      expect(result.violations.first).to match(/below floor/)
    end

    it "rejects prices above ceiling" do
      result = guardrail.check(
        valuation_cents: valuation_cents,
        proposed_price_cents: 70_000_000 # $700k - above 15% ceiling
      )
      expect(result.within_bounds).to be false
      expect(result.violations.first).to match(/exceeds ceiling/)
    end

    it "rejects excessive concessions" do
      result = guardrail.check(
        valuation_cents: valuation_cents,
        proposed_price_cents: 51_000_000,
        concessions_cents: 5_000_000 # ~10% - above 6% limit
      )
      expect(result.within_bounds).to be false
      expect(result.violations.first).to match(/concessions/)
    end

    it "calculates expected margin" do
      result = guardrail.check(
        valuation_cents: valuation_cents,
        proposed_price_cents: 52_500_000 # $525k = 5% above valuation
      )
      expect(result.expected_margin).to be_within(0.01).of(0.05)
    end
  end

  describe "#validate_concession" do
    it "accepts valid concession types" do
      result = guardrail.validate_concession(
        type: "seller_concession",
        amount_cents: 500_000
      )
      expect(result.compliant).to be true
    end

    it "rejects unknown concession types" do
      result = guardrail.validate_concession(
        type: "crypto_payment",
        amount_cents: 500_000
      )
      expect(result.compliant).to be false
    end

    it "flags MLS-advertised buyer agent compensation (post-NAR)" do
      result = guardrail.validate_concession(
        type: "buyer_agent_compensation",
        amount_cents: 1_500_000,
        description: "Listed on MLS as buyer agent comp"
      )
      expect(result.compliant).to be false
      expect(result.issues.first).to match(/Post-NAR/)
    end

    it "allows non-MLS buyer agent compensation" do
      result = guardrail.validate_concession(
        type: "buyer_agent_compensation",
        amount_cents: 1_500_000,
        description: "Seller concession to buyer for agent fees"
      )
      expect(result.compliant).to be true
    end
  end
end
