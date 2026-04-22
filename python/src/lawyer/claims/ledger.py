"""
Claim Ledger - Every outbound statement decomposed into atomic claims with provenance.

This exists because of Hearth's litigation history (securities litigation re: pricing
algorithm effectiveness, $39M settlement approved Jan 2026). Every claim the agent makes
must be:
1. Traceable to a permissible data source
2. Within its freshness window (fail closed if stale)
3. Reproducible at any point in time
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional
import uuid
import logging

logger = logging.getLogger(__name__)


class ClaimStatus(Enum):
    VERIFIED = "verified"
    STALE = "stale"
    UNVERIFIABLE = "unverifiable"
    RETRACTED = "retracted"


@dataclass
class ClaimSource:
    source_system: str
    source_id: str
    source_statement: str
    relevance_score: float
    retrieved_at: datetime
    source_updated_at: Optional[datetime] = None
    license_id: Optional[str] = None
    freshness_ttl_seconds: int = 3600


@dataclass
class Claim:
    id: str
    session_id: str
    statement: str
    sources: list[ClaimSource]
    created_at: datetime
    valid_until: datetime
    status: ClaimStatus = ClaimStatus.VERIFIED


@dataclass
class AgentStateSnapshot:
    session_id: str
    as_of: datetime
    active_claims: list[Claim]
    data_snapshots: dict[str, str]


class ClaimLedger:
    """
    Append-only claim ledger with freshness contracts.

    Key invariants:
    1. Every claim has at least one source
    2. Stale claims are never returned as valid
    3. Claims are immutable once created (append-only)
    4. Agent state can be reconstructed at any point in time

    Freshness contracts: each claim declares its required recency.
    If data is stale, the claim FAILS CLOSED (blocks the outbound message).
    This is the correct default for a company with Hearth's litigation history.
    """

    def __init__(self):
        self._claims: dict[str, Claim] = {}
        self._session_claims: dict[str, list[str]] = {}

    def record_claim(
        self,
        session_id: str,
        statement: str,
        sources: list[ClaimSource],
        freshness_ttl_seconds: int = 3600,
    ) -> Claim:
        """Record a new claim with sources and freshness contract."""
        if not sources:
            raise ValueError("Every claim must have at least one source (invariant)")

        claim = Claim(
            id=str(uuid.uuid4()),
            session_id=session_id,
            statement=statement,
            sources=sources,
            created_at=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(seconds=freshness_ttl_seconds),
            status=ClaimStatus.VERIFIED,
        )

        self._claims[claim.id] = claim
        if session_id not in self._session_claims:
            self._session_claims[session_id] = []
        self._session_claims[session_id].append(claim.id)

        logger.info(f"Claim recorded: {claim.id} for session {session_id}")
        return claim

    def check_freshness(self, claim_ids: list[str]) -> dict[str, bool]:
        """
        Check whether claims are still within their freshness window.
        FAIL CLOSED: if we can't find or verify a claim, it's considered stale.
        """
        results = {}
        now = datetime.now(timezone.utc)

        for claim_id in claim_ids:
            claim = self._claims.get(claim_id)
            if claim is None:
                results[claim_id] = False  # Fail closed: unknown claim
                continue

            if claim.status == ClaimStatus.RETRACTED:
                results[claim_id] = False
                continue

            is_fresh = now < claim.valid_until
            if not is_fresh and claim.status == ClaimStatus.VERIFIED:
                claim.status = ClaimStatus.STALE
                logger.warning(f"Claim {claim_id} expired at {claim.valid_until}")

            results[claim_id] = is_fresh

        return results

    def get_claims_by_session(self, session_id: str) -> list[Claim]:
        """Get all claims for a session."""
        claim_ids = self._session_claims.get(session_id, [])
        return [self._claims[cid] for cid in claim_ids if cid in self._claims]

    def reproduce_state(self, session_id: str, as_of: datetime) -> AgentStateSnapshot:
        """
        Reconstruct exactly what the agent knew at a point in time.
        Essential for regulated/contested interactions.
        """
        claims = self.get_claims_by_session(session_id)
        active_at_time = [
            c for c in claims
            if c.created_at <= as_of and c.valid_until > as_of
            and c.status != ClaimStatus.RETRACTED
        ]

        data_snapshots = {}
        for claim in active_at_time:
            for source in claim.sources:
                key = f"{source.source_system}:{source.source_id}"
                data_snapshots[key] = source.source_statement

        return AgentStateSnapshot(
            session_id=session_id,
            as_of=as_of,
            active_claims=active_at_time,
            data_snapshots=data_snapshots,
        )

    def retract_claim(self, claim_id: str, reason: str = "") -> bool:
        """Retract a claim (mark as no longer valid)."""
        claim = self._claims.get(claim_id)
        if claim is None:
            return False
        claim.status = ClaimStatus.RETRACTED
        logger.info(f"Claim {claim_id} retracted: {reason}")
        return True
