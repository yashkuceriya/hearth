# frozen_string_literal: true

require "closer/trec/populator"
require "closer/trec/third_party_financing"
require "closer/trec/property_condition"
require "closer/trec/amendment"

module Closer
  module TREC
    RSpec.describe ThirdPartyFinancing do
      describe "#populate" do
        it "populates required loan fields" do
          result = described_class.new.populate(
            buyer_name: "Alex Chen",
            seller_name: "Morgan Cruz",
            property_address: "123 Main St, Austin TX",
            loan_type: "conventional",
            loan_amount_cents: 40_000_000,
            loan_term_years: 30,
            buyer_approval_deadline: "2026-05-15",
          )
          expect(result[:is_complete]).to be true
          expect(result[:errors]).to be_empty
          expect(result[:form_number]).to eq "40-9"
        end

        it "rejects invalid loan type" do
          result = described_class.new.populate(
            buyer_name: "X", seller_name: "Y", property_address: "addr",
            loan_type: "crypto", loan_amount_cents: 1, loan_term_years: 30,
            buyer_approval_deadline: "2026-01-01",
          )
          expect(result[:errors]).not_to be_empty
        end

        it "flags missing required fields" do
          result = described_class.new.populate(buyer_name: "only")
          expect(result[:missing_required]).not_to be_empty
          expect(result[:is_complete]).to be false
        end
      end
    end

    RSpec.describe PropertyCondition do
      describe "#populate" do
        it "accepts yes/no/unknown for known defects" do
          result = described_class.new.populate(
            seller_name: "S", property_address: "addr",
            foundation_issues: "unknown", roof_issues: "no",
          )
          expect(result[:is_complete]).to be true
          expect(result[:populated_fields]["foundation_issues"]).to eq "unknown"
        end

        it "rejects non-trinary answers" do
          result = described_class.new.populate(
            seller_name: "S", property_address: "addr",
            foundation_issues: "maybe",
          )
          expect(result[:errors]).not_to be_empty
        end
      end
    end

    RSpec.describe Amendment do
      describe "#populate" do
        it "requires at least one change field" do
          result = described_class.new.populate(
            original_contract_date: "2026-01-01",
            buyer_name: "B", seller_name: "S",
            property_address: "addr", effective_date: "2026-02-01",
          )
          expect(result[:errors]).to include("Amendment must change at least one term")
          expect(result[:is_complete]).to be false
        end

        it "accepts a price change" do
          result = described_class.new.populate(
            original_contract_date: "2026-01-01",
            buyer_name: "B", seller_name: "S",
            property_address: "addr", effective_date: "2026-02-01",
            new_sales_price_cents: 50_000_000,
          )
          expect(result[:is_complete]).to be true
        end

        it "accepts a repair credit" do
          result = described_class.new.populate(
            original_contract_date: "2026-01-01",
            buyer_name: "B", seller_name: "S",
            property_address: "addr", effective_date: "2026-02-01",
            repair_credit_cents: 500_000,
          )
          expect(result[:is_complete]).to be true
        end
      end
    end
  end
end
