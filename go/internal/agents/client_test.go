package agents

import (
	"testing"
)

func TestAgentRoles(t *testing.T) {
	roles := []AgentRole{RoleBrain, RoleVoice, RoleCloser, RoleLawyer, RoleOrchestrator}
	for _, role := range roles {
		if role == "" {
			t.Error("agent role should not be empty")
		}
	}
}

func TestConversationTurn(t *testing.T) {
	turn := &ConversationTurn{
		TurnID:        "turn-1",
		SessionID:     "session-1",
		UserMessage:   "Hello",
		FinalResponse: "Welcome!",
		Blocked:       false,
		NeedsHuman:    false,
	}

	if turn.Blocked {
		t.Error("turn should not be blocked")
	}
	if turn.NeedsHuman {
		t.Error("turn should not need human")
	}
	if turn.FinalResponse != "Welcome!" {
		t.Errorf("expected Welcome!, got %s", turn.FinalResponse)
	}
}

func TestClaim(t *testing.T) {
	claim := Claim{
		Statement:    "Property valued at $450k",
		SourceSystem: "VALUATION_ENGINE",
		SourceID:     "prop-123",
		FreshnessTTL: 3600,
	}

	if claim.Statement == "" {
		t.Error("claim statement should not be empty")
	}
	if claim.FreshnessTTL != 3600 {
		t.Errorf("expected TTL 3600, got %d", claim.FreshnessTTL)
	}
}

func TestDelegation(t *testing.T) {
	del := Delegation{
		FromAgent: "voice-abc123",
		ToRole:    RoleBrain,
		Task:      "Get property valuation",
	}

	if del.ToRole != RoleBrain {
		t.Errorf("expected brain role, got %s", del.ToRole)
	}
}
