"""Tests for the Claim Ledger."""

from datetime import datetime, timezone, timedelta
from lawyer.claims.ledger import ClaimLedger, ClaimSource, ClaimStatus
import pytest


class TestClaimLedger:
    def setup_method(self):
        self.ledger = ClaimLedger()

    def test_record_claim_with_source(self):
        source = ClaimSource(
            source_system="MLS",
            source_id="listing-123",
            source_statement="Property listed at $450,000",
            relevance_score=0.95,
            retrieved_at=datetime.now(timezone.utc),
        )
        claim = self.ledger.record_claim(
            session_id="session-1",
            statement="This property is listed at $450,000",
            sources=[source],
        )
        assert claim.id is not None
        assert claim.status == ClaimStatus.VERIFIED
        assert len(claim.sources) == 1

    def test_record_claim_requires_source(self):
        with pytest.raises(ValueError, match="at least one source"):
            self.ledger.record_claim(
                session_id="session-1",
                statement="Some unsourced claim",
                sources=[],
            )

    def test_freshness_check_valid(self):
        source = ClaimSource(
            source_system="MLS",
            source_id="listing-123",
            source_statement="Listed at $450k",
            relevance_score=0.9,
            retrieved_at=datetime.now(timezone.utc),
        )
        claim = self.ledger.record_claim(
            session_id="session-1",
            statement="Listed at $450k",
            sources=[source],
            freshness_ttl_seconds=3600,
        )
        results = self.ledger.check_freshness([claim.id])
        assert results[claim.id] is True

    def test_freshness_check_unknown_claim_fails_closed(self):
        results = self.ledger.check_freshness(["nonexistent-id"])
        assert results["nonexistent-id"] is False

    def test_freshness_check_expired(self):
        source = ClaimSource(
            source_system="MLS",
            source_id="listing-123",
            source_statement="Price data",
            relevance_score=0.9,
            retrieved_at=datetime.now(timezone.utc),
        )
        claim = self.ledger.record_claim(
            session_id="session-1",
            statement="Price claim",
            sources=[source],
            freshness_ttl_seconds=1,  # 1 second TTL
        )
        # Manually expire
        claim.valid_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        results = self.ledger.check_freshness([claim.id])
        assert results[claim.id] is False
        assert claim.status == ClaimStatus.STALE

    def test_retracted_claim_not_fresh(self):
        source = ClaimSource(
            source_system="MLS",
            source_id="listing-123",
            source_statement="Data",
            relevance_score=0.9,
            retrieved_at=datetime.now(timezone.utc),
        )
        claim = self.ledger.record_claim(
            session_id="s1",
            statement="Claim",
            sources=[source],
        )
        self.ledger.retract_claim(claim.id, "incorrect")
        results = self.ledger.check_freshness([claim.id])
        assert results[claim.id] is False

    def test_reproduce_state(self):
        source = ClaimSource(
            source_system="TCAD",
            source_id="prop-456",
            source_statement="Appraised at $400k",
            relevance_score=0.85,
            retrieved_at=datetime.now(timezone.utc),
        )
        self.ledger.record_claim(
            session_id="session-1",
            statement="Tax appraised at $400k",
            sources=[source],
        )

        snapshot = self.ledger.reproduce_state(
            "session-1",
            datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        assert len(snapshot.active_claims) == 1
        assert "TCAD:prop-456" in snapshot.data_snapshots

    def test_get_claims_by_session(self):
        source = ClaimSource(
            source_system="MLS",
            source_id="l1",
            source_statement="data",
            relevance_score=0.9,
            retrieved_at=datetime.now(timezone.utc),
        )
        self.ledger.record_claim("s1", "claim 1", [source])
        self.ledger.record_claim("s1", "claim 2", [source])
        self.ledger.record_claim("s2", "claim 3", [source])

        s1_claims = self.ledger.get_claims_by_session("s1")
        assert len(s1_claims) == 2

        s2_claims = self.ledger.get_claims_by_session("s2")
        assert len(s2_claims) == 1
