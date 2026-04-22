# frozen_string_literal: true

require "spec_helper"

RSpec.describe Closer::Workflow::StateMachine do
  subject(:machine) { described_class.new("txn-123") }

  describe "#transition!" do
    it "transitions through valid states" do
      event = machine.transition!(:under_negotiation, triggered_by: "buyer")
      expect(machine.current_state).to eq(:under_negotiation)
      expect(event.from_state).to eq(:offer_submitted)
      expect(event.to_state).to eq(:under_negotiation)
    end

    it "records events" do
      machine.transition!(:under_negotiation)
      machine.transition!(:executed)
      expect(machine.events.size).to eq(2)
    end

    it "rejects invalid transitions" do
      expect {
        machine.transition!(:closed)
      }.to raise_error(Closer::Workflow::InvalidTransitionError)
    end

    it "allows any state to terminate" do
      machine.transition!(:terminated)
      expect(machine.current_state).to eq(:terminated)
      expect(machine.terminal?).to be true
    end

    it "rejects transitions from terminal states" do
      machine.transition!(:terminated)
      expect {
        machine.transition!(:under_negotiation)
      }.to raise_error(Closer::Workflow::InvalidTransitionError)
    end
  end

  describe "milestones" do
    it "creates milestones on state entry" do
      machine.transition!(:under_negotiation)
      machine.transition!(:executed)
      expect(machine.milestones).to have_key("earnest_money_deposit")
      expect(machine.milestones).to have_key("option_fee_payment")
    end

    it "completes milestones" do
      machine.transition!(:under_negotiation)
      machine.transition!(:executed)
      milestone = machine.complete_milestone!("earnest_money_deposit", completed_by: "escrow")
      expect(milestone.completed).to be true
      expect(milestone.completed_by).to eq("escrow")
    end

    it "raises on unknown milestone" do
      expect {
        machine.complete_milestone!("nonexistent")
      }.to raise_error(ArgumentError, /Unknown milestone/)
    end

    it "raises on double-completion" do
      machine.transition!(:under_negotiation)
      machine.transition!(:executed)
      machine.complete_milestone!("earnest_money_deposit")
      expect {
        machine.complete_milestone!("earnest_money_deposit")
      }.to raise_error(ArgumentError, /already completed/)
    end

    it "tracks pending vs completed" do
      machine.transition!(:under_negotiation)
      machine.transition!(:executed)
      machine.complete_milestone!("earnest_money_deposit")
      expect(machine.completed_milestones.size).to eq(1)
      expect(machine.pending_milestones.size).to eq(1)
    end
  end

  describe "#can_transition_to?" do
    it "returns true for valid transitions" do
      expect(machine.can_transition_to?(:under_negotiation)).to be true
    end

    it "returns false for invalid transitions" do
      expect(machine.can_transition_to?(:closed)).to be false
    end
  end

  describe "full transaction lifecycle" do
    it "completes the happy path" do
      machine.transition!(:under_negotiation, triggered_by: "buyer_agent")
      machine.transition!(:executed, triggered_by: "both_parties")
      machine.transition!(:option_period, triggered_by: "system")
      machine.transition!(:pending, triggered_by: "buyer")
      machine.transition!(:closing, triggered_by: "title_company")
      machine.transition!(:closed, triggered_by: "title_company")

      expect(machine.current_state).to eq(:closed)
      expect(machine.terminal?).to be true
      expect(machine.events.size).to eq(6)
    end
  end
end
