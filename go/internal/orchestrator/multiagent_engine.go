package orchestrator

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/yashkuceriya/hearth/internal/agents"
	"github.com/yashkuceriya/hearth/internal/channel"
	"github.com/yashkuceriya/hearth/internal/domain"
	"github.com/yashkuceriya/hearth/internal/routing"
	"github.com/yashkuceriya/hearth/internal/session"
	"go.uber.org/zap"
)

// MultiAgentEngine processes interactions through the full multi-agent pipeline.
// This is the "real" engine that makes the system multi-agent.
//
// Flow:
// 1. Resolve/create session
// 2. Check product path routing
// 3. Send to multi-agent orchestrator (Voice -> Brain/Closer -> Lawyer)
// 4. Deliver response via channel adapter
type MultiAgentEngine struct {
	sessions    *session.Manager
	router      *routing.ProductPathRouter
	tourGate    *routing.TourEligibilityGate
	agentClient agents.MultiAgentClient
	adapters    map[domain.ChannelType]channel.Adapter
	logger      *zap.Logger
}

func NewMultiAgentEngine(
	sessions *session.Manager,
	router *routing.ProductPathRouter,
	tourGate *routing.TourEligibilityGate,
	agentClient agents.MultiAgentClient,
	logger *zap.Logger,
) *MultiAgentEngine {
	return &MultiAgentEngine{
		sessions:    sessions,
		router:      router,
		tourGate:    tourGate,
		agentClient: agentClient,
		adapters:    make(map[domain.ChannelType]channel.Adapter),
		logger:      logger,
	}
}

func (e *MultiAgentEngine) RegisterAdapter(a channel.Adapter) {
	e.adapters[a.Type()] = a
}

// HandleInteraction processes a message through the multi-agent pipeline.
func (e *MultiAgentEngine) HandleInteraction(ctx context.Context, msg *domain.InboundMessage) (*domain.OutboundMessage, error) {
	// 1. Resolve session
	var sess *domain.Session
	var err error
	if msg.SessionID != "" {
		sid, parseErr := uuid.Parse(msg.SessionID)
		if parseErr != nil {
			return nil, fmt.Errorf("invalid session ID: %w", parseErr)
		}
		sess, err = e.sessions.Get(ctx, sid)
	} else {
		leadID, parseErr := uuid.Parse(msg.Metadata["lead_id"])
		if parseErr != nil {
			return nil, fmt.Errorf("no session_id or lead_id")
		}
		sess, err = e.sessions.Resume(ctx, leadID, msg.Channel)
	}
	if err != nil {
		return nil, fmt.Errorf("session: %w", err)
	}

	e.logger.Info("multi-agent processing",
		zap.String("session", sess.ID.String()),
		zap.String("channel", string(msg.Channel)),
	)

	// 2. Build context for the agent system
	agentContext := map[string]interface{}{
		"session_id":              sess.ID.String(),
		"lead_id":                sess.LeadID.String(),
		"channel":                string(msg.Channel),
		"session_state":          string(sess.State),
		"buyer_agreement_signed": false, // Would come from lead record
	}

	// Add any property context from the message
	if propID, ok := msg.Metadata["property_id"]; ok {
		agentContext["property_id"] = propID
	}

	// 3. Process through multi-agent pipeline
	// This calls: Voice -> (Brain/Closer delegations) -> Lawyer compliance check
	turn, err := e.agentClient.ProcessMessage(ctx, sess.ID.String(), msg.Content, agentContext)
	if err != nil {
		return nil, fmt.Errorf("multi-agent processing: %w", err)
	}

	// 4. Handle blocked messages
	if turn.Blocked {
		e.logger.Warn("message blocked by compliance",
			zap.String("session", sess.ID.String()),
			zap.String("compliance", turn.ComplianceResult),
		)
		// Send a safe fallback response
		turn.FinalResponse = "I apologize, let me rephrase. How can I help you with your real estate needs in Austin?"
	}

	// 5. Handle HITL escalation
	if turn.NeedsHuman {
		e.logger.Info("human escalation triggered",
			zap.String("session", sess.ID.String()),
		)
		_ = e.sessions.UpdateState(ctx, sess.ID, domain.StateHandoffToHuman)
	}

	// 6. Build outbound message
	outbound := &domain.OutboundMessage{
		SessionID: sess.ID.String(),
		Content:   turn.FinalResponse,
		Channel:   msg.Channel,
		Metadata:  msg.Metadata,
	}

	// 7. Deliver via channel adapter
	adapter, ok := e.adapters[msg.Channel]
	if ok {
		if err := adapter.Send(ctx, outbound); err != nil {
			return nil, fmt.Errorf("delivery: %w", err)
		}
	}

	return outbound, nil
}
