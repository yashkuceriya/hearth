# frozen_string_literal: true

require "spec_helper"

RSpec.describe Closer::TREC::FieldDefinition do
  describe "#validate" do
    it "requires required fields" do
      field = described_class.new(name: :test, label: "Test", type: :string, required: true)
      errors = field.validate(nil)
      expect(errors).to include(match(/required/))
    end

    it "accepts valid string values" do
      field = described_class.new(name: :test, label: "Test", type: :string)
      errors = field.validate("John Doe")
      expect(errors).to be_empty
    end

    it "validates money fields" do
      field = described_class.new(name: :price, label: "Price", type: :money)
      expect(field.validate(50000000)).to be_empty
      expect(field.validate(-1)).not_to be_empty
      expect(field.validate("not a number")).not_to be_empty
    end

    it "validates date format" do
      field = described_class.new(name: :date, label: "Date", type: :date)
      expect(field.validate("2025-06-15")).to be_empty
      expect(field.validate("June 15")).not_to be_empty
    end

    it "validates enum values" do
      field = described_class.new(
        name: :financing, label: "Financing", type: :enum,
        validation: { values: %w[cash conventional fha] }
      )
      expect(field.validate("cash")).to be_empty
      expect(field.validate("crypto")).not_to be_empty
    end

    it "detects legal language in string fields (UPL guard)" do
      field = described_class.new(name: :notes, label: "Notes", type: :string)
      errors = field.validate("Buyer hereby waives all rights to inspection")
      expect(errors).to include(match(/legal language/i))
    end

    it "allows normal business text" do
      field = described_class.new(name: :notes, label: "Notes", type: :string)
      errors = field.validate("Seller to leave washer and dryer")
      expect(errors).to be_empty
    end
  end
end
