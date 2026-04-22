package orchestrator

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/yashkuceriya/hearth/internal/channel"
	"github.com/yashkuceriya/hearth/internal/compliance"
	"github.com/yashkuceriya/hearth/internal/domain"
	"github.com/yashkuceriya/hearth/internal/routing"
	"github.com/yashkuceriya/hearth/internal/session"
	"go.uber.org/zap"
)

type Engine struct {
	sessions *session.Manager
	router   *routing.ProductPathRouter
	tourGate *routing.TourEligibilityGate
	gateway  *compliance.Gateway
	adapters map[domain.ChannelType]channel.Adapter
	logger   *zap.Logger
}

func NewEngine(
	sessions *session.Manager,
	router *routing.ProductPathRouter,
	tourGate *routing.TourEligibilityGate,
	gateway *compliance.Gateway,
	logger *zap.Logger,
) *Engine {
	return &Engine{
		sessions: sessions,
		router:   router,
		tourGate: tourGate,
		gateway:  gateway,
		adapters: make(map[domain.ChannelType]channel.Adapter),
		logger:   logger,
	}
}

func (e *Engine) RegisterAdapter(a channel.Adapter) {
	e.adapters[a.Type()] = a
}

// HandleInteraction processes a single inbound message through the full pipeline:
// 1. Session lookup/creation
// 2. Intent analysis
// 3. Response generation (placeholder - will call Brain/Closer)
// 4. Compliance check (mandatory, non-bypassable)
// 5. Delivery
func (e *Engine) HandleInteraction(ctx context.Context, msg *domain.InboundMessage) (*domain.OutboundMessage, error) {
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
			return nil, fmt.Errorf("no session_id or lead_id provided")
		}
		sess, err = e.sessions.Resume(ctx, leadID, msg.Channel)
	}
	if err != nil {
		return nil, fmt.Errorf("session resolution: %w", err)
	}

	e.logger.Info("processing interaction",
		zap.String("session", sess.ID.String()),
		zap.String("state", string(sess.State)),
		zap.String("channel", string(msg.Channel)),
	)

	// 2. Generate response (placeholder: echo + state-based response)
	responseContent := e.generateResponse(sess, msg)

	// 3. Build outbound message
	outbound := &domain.OutboundMessage{
		SessionID: sess.ID.String(),
		Content:   responseContent,
		Channel:   msg.Channel,
		Metadata:  msg.Metadata,
	}

	// 4. MANDATORY compliance check - non-bypassable
	if err := e.gateway.Check(ctx, outbound); err != nil {
		return nil, fmt.Errorf("compliance gateway blocked message: %w", err)
	}

	// 5. Deliver via channel adapter
	adapter, ok := e.adapters[msg.Channel]
	if ok {
		if err := adapter.Send(ctx, outbound); err != nil {
			e.logger.Error("delivery failed", zap.Error(err))
			return nil, fmt.Errorf("delivery: %w", err)
		}
	}

	return outbound, nil
}

func (e *Engine) generateResponse(sess *domain.Session, msg *domain.InboundMessage) string {
	switch sess.State {
	case domain.StateGreeting:
		return "Welcome to Hearth! I'm your AI real estate assistant for the Austin market. Are you looking to buy, sell, or just exploring your options?"
	case domain.StateQualifying:
		return "I'd love to help. To find the best path for you, could you share: Are you pre-approved for financing? And what's your timeline for moving?"
	case domain.StatePropertyDiscussion:
		return "Let me pull up the latest market data for that property. One moment while I check current valuations and comparable sales."
	case domain.StateScheduling:
		return "I can help schedule a tour. Let me check available times."
	case domain.StateOfferDiscussion:
		return "Based on the current market analysis, I can walk you through the offer process. Would you like to discuss pricing strategy?"
	default:
		return "I'm here to help with your real estate needs in Austin. What can I assist you with?"
	}
}
