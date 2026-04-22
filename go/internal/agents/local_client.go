package agents

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"time"

	"go.uber.org/zap"
)

// LocalAgentClient runs the Python multi-agent system in-process via subprocess.
// In production, this would be replaced by a gRPC client to the Python service.
type LocalAgentClient struct {
	pythonPath string
	scriptPath string
	logger     *zap.Logger
}

func NewLocalAgentClient(pythonPath, projectRoot string, logger *zap.Logger) *LocalAgentClient {
	return &LocalAgentClient{
		pythonPath: pythonPath,
		scriptPath: projectRoot + "/python",
		logger:     logger,
	}
}

func (c *LocalAgentClient) ProcessMessage(ctx context.Context, sessionID, message string, extraContext map[string]interface{}) (*ConversationTurn, error) {
	// Build the Python command that invokes the orchestrator
	input := map[string]interface{}{
		"session_id": sessionID,
		"message":    message,
		"context":    extraContext,
	}

	inputJSON, err := json.Marshal(input)
	if err != nil {
		return nil, fmt.Errorf("marshal input: %w", err)
	}

	cmd := exec.CommandContext(ctx, c.pythonPath, "-c", fmt.Sprintf(`
import sys, json
sys.path.insert(0, "%s/src")
from agents.orchestrator import MultiAgentOrchestrator
orch = MultiAgentOrchestrator()
input_data = json.loads('%s')
turn = orch.process_message(
    input_data["session_id"],
    input_data["message"],
    input_data.get("context", {}),
)
result = {
    "turn_id": turn.turn_id,
    "session_id": turn.session_id,
    "user_message": turn.user_message,
    "final_response": turn.final_response,
    "compliance_result": turn.compliance_result,
    "blocked": turn.blocked,
    "needs_human": turn.needs_human,
    "agent_responses": turn.agent_responses,
    "delegations": turn.delegations,
}
print(json.dumps(result))
`, c.scriptPath, string(inputJSON)))

	output, err := cmd.Output()
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			return nil, fmt.Errorf("python agent error: %s", string(exitErr.Stderr))
		}
		return nil, fmt.Errorf("run python agent: %w", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(output, &result); err != nil {
		return nil, fmt.Errorf("unmarshal response: %w", err)
	}

	turn := &ConversationTurn{
		TurnID:           getString(result, "turn_id"),
		SessionID:        getString(result, "session_id"),
		UserMessage:      getString(result, "user_message"),
		FinalResponse:    getString(result, "final_response"),
		ComplianceResult: getString(result, "compliance_result"),
		Blocked:          getBool(result, "blocked"),
		NeedsHuman:       getBool(result, "needs_human"),
		Timestamp:        time.Now().UTC(),
	}

	c.logger.Info("multi-agent turn completed",
		zap.String("session", sessionID),
		zap.Bool("blocked", turn.Blocked),
		zap.Bool("needs_human", turn.NeedsHuman),
	)

	return turn, nil
}

func (c *LocalAgentClient) GetAgentSummary(ctx context.Context) (map[string]interface{}, error) {
	return map[string]interface{}{
		"type":   "local",
		"status": "running",
	}, nil
}

func getString(m map[string]interface{}, key string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

func getBool(m map[string]interface{}, key string) bool {
	if v, ok := m[key]; ok {
		if b, ok := v.(bool); ok {
			return b
		}
	}
	return false
}
