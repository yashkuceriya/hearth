package routing

import (
	"context"
	"fmt"

	"github.com/yashkuceriya/hearth/internal/domain"
	"go.uber.org/zap"
)

type ProductPathRouter struct {
	logger *zap.Logger
}

func NewProductPathRouter(logger *zap.Logger) *ProductPathRouter {
	return &ProductPathRouter{logger: logger}
}

// Route determines the optimal Hearth product path for a lead.
// Logic: High-intent + pre-approved => Instant Offer; Medium + agent => Listing Boost; Low => Agent Referral referral.
func (r *ProductPathRouter) Route(ctx context.Context, lead *domain.Lead, propertyValue int64) (*domain.RoutingDecision, error) {
	decision := &domain.RoutingDecision{
		LeadID: lead.ID,
	}

	switch lead.IntentTier {
	case domain.TierHighIntent:
		if lead.BuyerAgreementSigned {
			decision.SelectedPath = domain.PathInstantOffer
			decision.Rationale = "High-intent buyer with signed agreement; direct cash offer maximizes velocity"
		} else {
			decision.SelectedPath = domain.PathListingBoost
			decision.Rationale = "High-intent but no buyer agreement; Listing Boost reduces capital risk"
		}
	case domain.TierMediumIntent:
		decision.SelectedPath = domain.PathListingBoost
		decision.Rationale = "Medium-intent buyer; Listing Boost balances conversion probability with capital efficiency"
	case domain.TierLookyLoo:
		decision.SelectedPath = domain.PathAgentReferral
		decision.Rationale = "Low-intent lead; route to Agent Referral partner agent for nurturing"
		decision.RequiresHumanHandoff = true
	default:
		return nil, fmt.Errorf("unknown intent tier: %s", lead.IntentTier)
	}

	// Estimate expected value based on path
	switch decision.SelectedPath {
	case domain.PathInstantOffer:
		decision.ExpectedValue = int64(float64(propertyValue) * 0.065) // ~6.5% margin target
	case domain.PathListingBoost:
		decision.ExpectedValue = int64(float64(propertyValue) * 0.035) // ~3.5% referral + service fee
	case domain.PathAgentReferral:
		decision.ExpectedValue = int64(float64(propertyValue) * 0.01) // ~1% referral fee
	}

	r.logger.Info("product path routed",
		zap.String("lead", lead.ID.String()),
		zap.String("path", string(decision.SelectedPath)),
		zap.Int64("expected_value", decision.ExpectedValue),
	)

	return decision, nil
}
