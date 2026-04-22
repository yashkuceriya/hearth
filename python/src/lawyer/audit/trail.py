"""
Append-only Audit Trail for all agent actions.
Supports disparate impact analysis and regulatory review.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid
import logging

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    id: str
    session_id: str
    action: str
    actor: str  # "agent", "system", "human_<id>"
    details: dict[str, str]
    timestamp: datetime


class AuditTrail:
    """
    Append-only audit trail. Entries cannot be modified or deleted.

    This supports:
    1. Fair Housing disparate impact analysis
    2. Regulatory review of agent decisions
    3. Litigation defense (reconstruct decision chain)
    """

    def __init__(self):
        self._entries: list[AuditEntry] = []

    def record(
        self,
        session_id: str,
        action: str,
        actor: str,
        details: Optional[dict[str, str]] = None,
    ) -> AuditEntry:
        """Record an immutable audit entry."""
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            session_id=session_id,
            action=action,
            actor=actor,
            details=details or {},
            timestamp=datetime.now(timezone.utc),
        )
        self._entries.append(entry)
        logger.debug(f"Audit: {action} by {actor} in session {session_id}")
        return entry

    def get_trail(
        self,
        session_id: str,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> list[AuditEntry]:
        """Get audit trail for a session, optionally filtered by time range."""
        entries = [e for e in self._entries if e.session_id == session_id]
        if from_time:
            entries = [e for e in entries if e.timestamp >= from_time]
        if to_time:
            entries = [e for e in entries if e.timestamp <= to_time]
        return entries

    def get_entries_by_action(self, action: str) -> list[AuditEntry]:
        """Get all entries for a specific action type (for disparate impact analysis)."""
        return [e for e in self._entries if e.action == action]

    @property
    def total_entries(self) -> int:
        return len(self._entries)
