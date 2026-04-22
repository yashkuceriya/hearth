"""
Hearth AI Real Estate Agent — Web Demo
FastAPI server wrapping the multi-agent pipeline.
"""

import sys
import os
import uuid
from pathlib import Path

# Add Python src to path
python_src = str(Path(__file__).resolve().parent.parent / "python" / "src")
sys.path.insert(0, python_src)

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import logging

from agents.orchestrator import MultiAgentOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("hearth.web")

app = FastAPI(title="Hearth AI Agent", version="0.1.0")

# In-memory session store (no DB needed for demo)
sessions: dict[str, MultiAgentOrchestrator] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class AgentDetail(BaseModel):
    agent: str
    confidence: float
    reasoning: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    blocked: bool
    needs_human: bool
    agents_involved: list[str]
    delegations: list[dict]
    confidence: float
    agent_details: list[AgentDetail] = []
    session_memory: dict = {}
    turn_number: int = 0


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Get or create session
    session_id = req.session_id or str(uuid.uuid4())

    if session_id not in sessions:
        sessions[session_id] = MultiAgentOrchestrator()
        logger.info(f"New session: {session_id}")

    orch = sessions[session_id]

    try:
        turn = orch.process_message(session_id, req.message, {})
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    agents_involved = [r["agent"] for r in turn.agent_responses]
    avg_confidence = sum(r.get("confidence", 0) for r in turn.agent_responses) / max(len(turn.agent_responses), 1)

    agent_details = [
        AgentDetail(
            agent=r["agent"],
            confidence=r.get("confidence", 0),
            reasoning=r.get("reasoning", ""),
        )
        for r in turn.agent_responses
    ]

    return ChatResponse(
        session_id=session_id,
        response=turn.final_response or "I'm processing your request.",
        blocked=turn.blocked,
        needs_human=turn.needs_human,
        agents_involved=agents_involved,
        delegations=turn.delegations,
        confidence=round(avg_confidence, 2),
        agent_details=agent_details,
        session_memory=dict(orch.session_memory),
        turn_number=len(orch.conversation_history),
    )


@app.get("/api/session/{session_id}/summary")
async def session_summary(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    orch = sessions[session_id]
    return {
        **orch.get_agent_summary(),
        "history": [
            {
                "user": t.user_message,
                "agent": t.final_response,
                "blocked": t.blocked,
                "agents": [r["agent"] for r in t.agent_responses],
            }
            for t in orch.conversation_history
        ],
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "agents": ["voice", "brain", "closer", "lawyer"]}


# Serve static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(static_dir / "index.html"))
