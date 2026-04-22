"""Tests for the Audit Trail."""

from datetime import datetime, timezone, timedelta
from lawyer.audit.trail import AuditTrail


class TestAuditTrail:
    def setup_method(self):
        self.trail = AuditTrail()

    def test_record_entry(self):
        entry = self.trail.record("s1", "message_sent", "voice_agent", {"content": "hello"})
        assert entry.id is not None
        assert entry.session_id == "s1"
        assert entry.action == "message_sent"
        assert entry.actor == "voice_agent"

    def test_append_only(self):
        self.trail.record("s1", "action_1", "agent")
        self.trail.record("s1", "action_2", "agent")
        assert self.trail.total_entries == 2

    def test_get_trail_by_session(self):
        self.trail.record("s1", "a1", "agent")
        self.trail.record("s2", "a2", "agent")
        self.trail.record("s1", "a3", "agent")

        s1_trail = self.trail.get_trail("s1")
        assert len(s1_trail) == 2

        s2_trail = self.trail.get_trail("s2")
        assert len(s2_trail) == 1

    def test_get_trail_time_filter(self):
        self.trail.record("s1", "old_action", "agent")
        now = datetime.now(timezone.utc)
        self.trail.record("s1", "new_action", "agent")

        recent = self.trail.get_trail("s1", from_time=now - timedelta(seconds=1))
        assert len(recent) >= 1

    def test_get_entries_by_action(self):
        self.trail.record("s1", "fair_housing_check", "lawyer")
        self.trail.record("s2", "fair_housing_check", "lawyer")
        self.trail.record("s1", "claim_registered", "lawyer")

        fh_entries = self.trail.get_entries_by_action("fair_housing_check")
        assert len(fh_entries) == 2

    def test_entry_has_timestamp(self):
        entry = self.trail.record("s1", "test", "agent")
        assert entry.timestamp is not None
        assert entry.timestamp.tzinfo is not None
