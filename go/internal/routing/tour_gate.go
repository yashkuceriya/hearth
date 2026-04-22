package routing

import (
	"context"
	"fmt"

	"github.com/yashkuceriya/hearth/internal/domain"
	"go.uber.org/zap"
)

type TourEligibilityResult struct {
	Eligible             bool
	BuyerAgreementOnFile bool
	DenialReason         string
	RequiredAction       string
}

type TourEligibilityGate struct {
	logger *zap.Logger
}

func NewTourEligibilityGate(logger *zap.Logger) *TourEligibilityGate {
	return &TourEligibilityGate{logger: logger}
}

// CheckEligibility enforces post-NAR settlement requirements.
// Per NAR settlement (effective Aug 17, 2024): buyer agreements specifying
// compensation are required BEFORE an agent takes a buyer on a tour.
func (g *TourEligibilityGate) CheckEligibility(ctx context.Context, lead *domain.Lead) (*TourEligibilityResult, error) {
	if lead == nil {
		return nil, fmt.Errorf("lead is required")
	}

	result := &TourEligibilityResult{
		BuyerAgreementOnFile: lead.BuyerAgreementSigned,
	}

	if !lead.BuyerAgreementSigned {
		result.Eligible = false
		result.DenialReason = "Buyer representation agreement not on file (required per NAR settlement, effective 2024-08-17)"
		result.RequiredAction = "sign_buyer_agreement"
		g.logger.Warn("tour denied: no buyer agreement",
			zap.String("lead", lead.ID.String()),
		)
		return result, nil
	}

	result.Eligible = true
	g.logger.Info("tour eligible", zap.String("lead", lead.ID.String()))
	return result, nil
}
