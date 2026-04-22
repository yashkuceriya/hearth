# frozen_string_literal: true

module Closer
  module Workflow
    # Event-sourced state machine for the transaction lifecycle.
    # State transitions are immutable events. The machine can be reconstructed
    # from its event log at any point for audit/compliance purposes.
    #
    # States map to Texas real estate transaction milestones:
    # offer_submitted -> under_negotiation -> executed -> option_period ->
    # pending -> closing -> closed
    # (Any state can transition to terminated)
    class StateMachine
      STATES = %i[
        offer_submitted under_negotiation executed
        option_period pending closing closed terminated
      ].freeze

      TRANSITIONS = {
        offer_submitted: %i[under_negotiation terminated],
        under_negotiation: %i[executed terminated],
        executed: %i[option_period terminated],
        option_period: %i[pending terminated],
        pending: %i[closing terminated],
        closing: %i[closed terminated],
        closed: [],
        terminated: [],
      }.freeze

      # Milestones auto-created when entering specific states
      STATE_MILESTONES = {
        executed: ["earnest_money_deposit", "option_fee_payment"],
        option_period: ["inspection", "appraisal_ordered"],
        pending: ["appraisal_completed", "loan_approval", "title_commitment"],
        closing: ["final_walkthrough", "closing_disclosure_review", "funding"],
      }.freeze

      attr_reader :transaction_id, :current_state, :events, :milestones

      TransitionEvent = Struct.new(:id, :from_state, :to_state, :metadata, :triggered_by, :timestamp, keyword_init: true)
      Milestone = Struct.new(:name, :due_date, :completed, :completed_at, :completed_by, keyword_init: true)

      def initialize(transaction_id, initial_state: :offer_submitted)
        @transaction_id = transaction_id
        @current_state = initial_state
        @events = []
        @milestones = {}
        create_milestones_for_state(initial_state)
      end

      def transition!(to_state, triggered_by: "system", metadata: {})
        to_state = to_state.to_sym
        validate_transition!(to_state)

        event = TransitionEvent.new(
          id: SecureRandom.uuid,
          from_state: @current_state,
          to_state: to_state,
          metadata: metadata,
          triggered_by: triggered_by,
          timestamp: Time.now.utc
        )

        @events << event
        @current_state = to_state
        create_milestones_for_state(to_state)

        event
      end

      def complete_milestone!(name, completed_by: "system")
        milestone = @milestones[name.to_s]
        raise ArgumentError, "Unknown milestone: #{name}" if milestone.nil?
        raise ArgumentError, "Milestone already completed: #{name}" if milestone.completed

        milestone.completed = true
        milestone.completed_at = Time.now.utc
        milestone.completed_by = completed_by
        milestone
      end

      def pending_milestones
        @milestones.values.reject(&:completed)
      end

      def completed_milestones
        @milestones.values.select(&:completed)
      end

      def can_transition_to?(state)
        allowed = TRANSITIONS[@current_state] || []
        allowed.include?(state.to_sym)
      end

      def terminal?
        @current_state == :closed || @current_state == :terminated
      end

      # Reconstruct state machine from events
      def self.reconstitute(transaction_id, events)
        machine = new(transaction_id, initial_state: events.first&.from_state || :offer_submitted)
        events.each do |event|
          machine.instance_variable_set(:@current_state, event.to_state)
          machine.events << event
        end
        machine
      end

      private

      def validate_transition!(to_state)
        unless STATES.include?(to_state)
          raise ArgumentError, "Invalid state: #{to_state}. Valid states: #{STATES.join(', ')}"
        end

        unless can_transition_to?(to_state)
          allowed = TRANSITIONS[@current_state] || []
          raise InvalidTransitionError,
                "Cannot transition from #{@current_state} to #{to_state}. " \
                "Allowed transitions: #{allowed.join(', ')}"
        end
      end

      def create_milestones_for_state(state)
        milestone_names = STATE_MILESTONES[state] || []
        milestone_names.each do |name|
          next if @milestones.key?(name)

          @milestones[name] = Milestone.new(
            name: name,
            due_date: nil,
            completed: false,
            completed_at: nil,
            completed_by: nil
          )
        end
      end
    end

    class InvalidTransitionError < StandardError; end
  end
end
