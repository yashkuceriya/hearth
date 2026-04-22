# frozen_string_literal: true

require "spec_helper"

RSpec.describe Closer::TREC::OneToFourFamily do
  subject(:form) { described_class.new }

  describe ".field_definitions" do
    it "defines required fields" do
      defs = described_class.field_definitions
      required = defs.select { |_, d| d.required }
      expect(required.keys).to include("buyer_name", "seller_name", "property_address",
                                        "sales_price_cents", "closing_date", "financing_type")
    end

    it "includes post-NAR concession fields" do
      defs = described_class.field_definitions
      expect(defs).to have_key("buyer_agent_compensation_cents")
      expect(defs).to have_key("buyer_agent_compensation_type")
    end
  end

  describe "#populate" do
    let(:valid_fields) do
      {
        "buyer_name" => "Jane Smith",
        "seller_name" => "Hearth Homes LLC",
        "property_address" => "123 Main St",
        "property_city" => "Austin",
        "property_county" => "Travis",
        "property_zip" => "78701",
        "legal_description" => "Lot 5, Block 3, Riverside Estates",
        "sales_price_cents" => 47500000,
        "earnest_money_cents" => 1000000,
        "financing_type" => "conventional",
        "closing_date" => "2025-08-15",
      }
    end

    it "populates valid fields successfully" do
      result = form.populate(valid_fields)
      expect(result[:errors]).to be_empty
      expect(result[:is_complete]).to be true
      expect(result[:form_number]).to eq("20-18")
    end

    it "reports missing required fields" do
      result = form.populate({ "buyer_name" => "Jane" })
      expect(result[:is_complete]).to be false
      expect(result[:missing_required]).to include("seller_name", "property_address")
    end

    it "validates field values" do
      fields = valid_fields.merge("sales_price_cents" => -100)
      result = form.populate(fields)
      expect(result[:errors]).not_to be_empty
    end

    it "warns on unknown fields" do
      fields = valid_fields.merge("unknown_field" => "value")
      result = form.populate(fields)
      expect(result[:warnings]).to include(match(/Unknown field/))
    end

    it "blocks legal language in text fields" do
      fields = valid_fields.merge(
        "seller_concession_description" => "Seller hereby indemnifies buyer against all claims"
      )
      result = form.populate(fields)
      expect(result[:errors]).to include(match(/legal language/i))
    end
  end
end
