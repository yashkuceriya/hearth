package compliance

import (
	"context"
	"fmt"

	"github.com/yashkuceriya/hearth/internal/domain"
	"go.uber.org/zap"
)

// LawyerClient is the interface for calling the Python Lawyer service.
type LawyerClient interface {
	CheckOutboundMessage(ctx context.Context, sessionID, text, channel string, claimIDs []string) (*ComplianceResult, error)
	CheckFairHousing(ctx context.Context, text, channel, sessionID string) (*FairHousingResult, error)
}

type ComplianceResult struct {
	Approved       bool
	BlockedReasons []string
	StaleWarnings  []string
}

type FairHousingResult struct {
	Compliant     bool
	Violations    []FairHousingViolation
	SanitizedText string
}

type FairHousingViolation struct {
	ViolationType string
	MatchedText   string
	RuleID        string
	Explanation   string
}

// Gateway is a NON-BYPASSABLE compliance check on every outbound message.
// It calls the Lawyer service to verify Fair Housing compliance and claim freshness.
type Gateway struct {
	lawyer LawyerClient
	logger *zap.Logger
}

func NewGateway(lawyer LawyerClient, logger *zap.Logger) *Gateway {
	return &Gateway{lawyer: lawyer, logger: logger}
}

// Check runs the full compliance pipeline on an outbound message.
// Returns an error if the message MUST NOT be sent.
func (g *Gateway) Check(ctx context.Context, msg *domain.OutboundMessage) error {
	// If no lawyer client is configured, fail open during development
	if g.lawyer == nil {
		g.logger.Warn("compliance gateway: no lawyer client configured, skipping checks")
		return nil
	}

	// Step 1: Fair Housing check (deterministic, fast)
	fhResult, err := g.lawyer.CheckFairHousing(ctx, msg.Content, string(msg.Channel), msg.SessionID)
	if err != nil {
		// Fail closed: if we can't check, we don't send
		return fmt.Errorf("fair housing check failed (fail-closed): %w", err)
	}
	if !fhResult.Compliant {
		for _, v := range fhResult.Violations {
			g.logger.Error("fair housing violation blocked",
				zap.String("session", msg.SessionID),
				zap.String("rule", v.RuleID),
				zap.String("matched", v.MatchedText),
			)
		}
		return fmt.Errorf("message blocked: %d Fair Housing violation(s) detected", len(fhResult.Violations))
	}

	// Step 2: Outbound message check (claim freshness + verification)
	result, err := g.lawyer.CheckOutboundMessage(ctx, msg.SessionID, msg.Content, string(msg.Channel), msg.ClaimIDs)
	if err != nil {
		return fmt.Errorf("outbound check failed (fail-closed): %w", err)
	}
	if !result.Approved {
		g.logger.Error("outbound message blocked",
			zap.String("session", msg.SessionID),
			zap.Strings("reasons", result.BlockedReasons),
		)
		return fmt.Errorf("message blocked: %v", result.BlockedReasons)
	}

	if len(result.StaleWarnings) > 0 {
		g.logger.Warn("stale claim warnings",
			zap.String("session", msg.SessionID),
			zap.Strings("warnings", result.StaleWarnings),
		)
	}

	return nil
}
