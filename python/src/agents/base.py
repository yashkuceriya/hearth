"""
Base agent framework for the Hearth multi-agent system.

Each agent:
- Has a role, goal, and set of tools it can use
- Maintains conversation history
- Can delegate to other agents
- Produces structured outputs with reasoning traces
- All outputs pass through the compliance gateway before reaching the user
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
import logging
import uuid

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    BRAIN = "brain"           # Market intelligence, valuation, visual analysis
    VOICE = "voice"           # Lead engagement, qualification, conversation
    CLOSER = "closer"         # Transaction management, negotiation, contracts
    LAWYER = "lawyer"         # Compliance, claims verification, audit
    ORCHESTRATOR = "orchestrator"  # Routes between agents, manages flow


@dataclass
class Tool:
    """A capability an agent can invoke."""
    name: str
    description: str
    handler: Callable
    requires_compliance_check: bool = False  # If True, output passes through Lawyer before use


@dataclass
class AgentMessage:
    """A message in the agent conversation."""
    role: str  # "user", "agent", "system", "tool_result"
    content: str
    agent_id: Optional[str] = None
    tool_calls: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DelegationRequest:
    """Request from one agent to another."""
    from_agent: str
    to_role: AgentRole
    task: str
    context: dict[str, Any] = field(default_factory=dict)
    require_response: bool = True


@dataclass
class AgentResponse:
    """Structured response from an agent."""
    content: str
    reasoning: str  # Chain-of-thought trace (for audit)
    confidence: float  # 0.0-1.0
    tool_calls_made: list[dict] = field(default_factory=list)
    delegations_made: list[DelegationRequest] = field(default_factory=list)
    claims: list[dict] = field(default_factory=list)  # Claims to register with Lawyer
    needs_human: bool = False
    human_reason: Optional[str] = None


class BaseAgent(ABC):
    """
    Abstract base for all agents in the system.
    Subclasses implement think() which is the core reasoning loop.
    """

    def __init__(self, role: AgentRole, agent_id: Optional[str] = None):
        self.role = role
        self.agent_id = agent_id or f"{role.value}-{uuid.uuid4().hex[:8]}"
        self.tools: dict[str, Tool] = {}
        self.conversation_history: list[AgentMessage] = []
        self._setup_tools()

    @abstractmethod
    def _setup_tools(self):
        """Register tools this agent can use."""
        pass

    @abstractmethod
    def think(self, message: str, context: dict[str, Any]) -> AgentResponse:
        """
        Core reasoning loop. Given a message and context, produce a response.
        This is where the LLM call happens in production.
        """
        pass

    def register_tool(self, tool: Tool):
        self.tools[tool.name] = tool

    def invoke_tool(self, tool_name: str, **kwargs) -> Any:
        """Invoke a registered tool."""
        tool = self.tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Agent {self.agent_id} has no tool '{tool_name}'")

        logger.info(f"Agent {self.agent_id} invoking tool: {tool_name}")
        result = tool.handler(**kwargs)
        return result

    def add_message(self, message: AgentMessage):
        self.conversation_history.append(message)

    def get_system_prompt(self) -> str:
        """Build the system prompt including available tools."""
        tool_descriptions = "\n".join(
            f"- {t.name}: {t.description}" for t in self.tools.values()
        )
        return f"""You are the {self.role.value} agent in the Hearth AI Real Estate system.
Your agent ID is {self.agent_id}.

Available tools:
{tool_descriptions}

CRITICAL RULES:
1. Every factual claim you make MUST be backed by a tool call or data source
2. NEVER describe neighborhoods using subjective quality terms (good/bad/safe/dangerous)
3. NEVER reference protected classes (race, religion, familial status, etc.)
4. If your confidence is below 0.3, request human handoff
5. All pricing claims have a freshness window - do not reuse stale data
"""
