package routing

import (
	"context"
	"testing"

	"github.com/google/uuid"
	"github.com/yashkuceriya/hearth/internal/domain"
	"go.uber.org/zap"
)

func TestProductPathRouter_HighIntentWithAgreement(t *testing.T) {
	router := NewProductPathRouter(zap.NewNop())
	lead := &domain.Lead{
		ID:                   uuid.New(),
		IntentTier:           domain.TierHighIntent,
		BuyerAgreementSigned: true,
	}

	decision, err := router.Route(context.Background(), lead, 50000000) // $500k
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if decision.SelectedPath != domain.PathInstantOffer {
		t.Errorf("expected InstantOffer, got %s", decision.SelectedPath)
	}
	if decision.ExpectedValue <= 0 {
		t.Error("expected positive expected value")
	}
}

func TestProductPathRouter_LookyLoo(t *testing.T) {
	router := NewProductPathRouter(zap.NewNop())
	lead := &domain.Lead{
		ID:         uuid.New(),
		IntentTier: domain.TierLookyLoo,
	}

	decision, err := router.Route(context.Background(), lead, 50000000)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if decision.SelectedPath != domain.PathAgentReferral {
		t.Errorf("expected AgentReferral, got %s", decision.SelectedPath)
	}
	if !decision.RequiresHumanHandoff {
		t.Error("expected human handoff for looky-loo")
	}
}

func TestTourEligibilityGate_NoAgreement(t *testing.T) {
	gate := NewTourEligibilityGate(zap.NewNop())
	lead := &domain.Lead{
		ID:                   uuid.New(),
		BuyerAgreementSigned: false,
	}

	result, err := gate.CheckEligibility(context.Background(), lead)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Eligible {
		t.Error("expected ineligible without buyer agreement")
	}
	if result.RequiredAction != "sign_buyer_agreement" {
		t.Errorf("expected sign_buyer_agreement action, got %s", result.RequiredAction)
	}
}

func TestTourEligibilityGate_WithAgreement(t *testing.T) {
	gate := NewTourEligibilityGate(zap.NewNop())
	lead := &domain.Lead{
		ID:                   uuid.New(),
		BuyerAgreementSigned: true,
	}

	result, err := gate.CheckEligibility(context.Background(), lead)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !result.Eligible {
		t.Error("expected eligible with signed buyer agreement")
	}
}
