package agents

import (
	"context"
	"time"
)

// AgentRole identifies a specialized agent in the multi-agent system.
type AgentRole string

const (
	RoleBrain        AgentRole = "brain"
	RoleVoice        AgentRole = "voice"
	RoleCloser       AgentRole = "closer"
	RoleLawyer       AgentRole = "lawyer"
	RoleOrchestrator AgentRole = "orchestrator"
)

// AgentResponse represents a structured response from the multi-agent system.
type AgentResponse struct {
	Content          string
	Reasoning        string
	Confidence       float64
	ToolCallsMade    []ToolCall
	DelegationsMade  []Delegation
	Claims           []Claim
	NeedsHuman       bool
	HumanReason      string
	AgentsInvolved   []string
	ComplianceResult string
	Blocked          bool
}

// ToolCall represents a tool invocation by an agent.
type ToolCall struct {
	Tool   string
	Result map[string]interface{}
}

// Delegation represents a delegation from one agent to another.
type Delegation struct {
	FromAgent string
	ToRole    AgentRole
	Task      string
}

// Claim represents a factual claim that must be registered with the Lawyer.
type Claim struct {
	Statement    string
	SourceSystem string
	SourceID     string
	FreshnessTTL int // seconds
}

// ConversationTurn represents one complete turn in the multi-agent system.
type ConversationTurn struct {
	TurnID           string
	SessionID        string
	UserMessage      string
	AgentResponses   []AgentTurnResponse
	Delegations      []Delegation
	FinalResponse    string
	ComplianceResult string
	Blocked          bool
	NeedsHuman       bool
	Timestamp        time.Time
}

// AgentTurnResponse is one agent's contribution to a turn.
type AgentTurnResponse struct {
	Agent      string
	Content    string
	Confidence float64
	Reasoning  string
}

// MultiAgentClient is the interface for the multi-agent orchestrator.
type MultiAgentClient interface {
	// ProcessMessage sends a user message through the full multi-agent pipeline:
	// Voice -> (Brain/Closer delegation) -> Lawyer compliance check -> response
	ProcessMessage(ctx context.Context, sessionID, message string, extraContext map[string]interface{}) (*ConversationTurn, error)

	// GetAgentSummary returns the current state of all agents.
	GetAgentSummary(ctx context.Context) (map[string]interface{}, error)
}
