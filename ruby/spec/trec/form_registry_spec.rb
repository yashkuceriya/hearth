# frozen_string_literal: true

require "spec_helper"

RSpec.describe Closer::TREC::FormRegistry do
  subject(:registry) { described_class.new }

  it "returns current form version" do
    version = registry.current_version("one_to_four_family")
    expect(version).to eq("20-18")
  end

  it "returns specific form version" do
    form = registry.get_form("one_to_four_family", version: "20-17")
    expect(form).not_to be_nil
    expect(form[:is_current]).to be false
  end

  it "returns nil for unknown forms" do
    expect(registry.get_form("nonexistent")).to be_nil
  end

  it "lists all versions" do
    versions = registry.get_versions("one_to_four_family")
    expect(versions.size).to eq(2)
  end
end
