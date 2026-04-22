"""
Data Rights Manager - Gates ALL external data access through licensing checks.
Every tool call that touches MLS, TCAD, or other external data MUST pass through this gate.
This directly addresses Hearth's 10-K risk factor about MLS compliance and data provider relationships.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DataSource(Enum):
    MLS = "MLS"
    TCAD = "TCAD"
    NEIGHBORHOOD = "NEIGHBORHOOD"
    HEARTH_INTERNAL = "HEARTH_INTERNAL"
    RESO_REFERENCE = "RESO_REFERENCE"


@dataclass
class DataLicense:
    license_id: str
    source: DataSource
    market: str
    allowed_use_cases: list[str]
    restrictions: list[str]  # e.g., ["no_bulk_transfer", "display_only"]
    expires_at: Optional[datetime] = None
    max_requests_per_hour: Optional[int] = None
    request_count_this_hour: int = 0


@dataclass
class AccessDecision:
    allowed: bool
    denial_reason: Optional[str] = None
    restrictions: list[str] = field(default_factory=list)
    license_id: Optional[str] = None


@dataclass
class AccessLog:
    source: DataSource
    market: str
    use_case: str
    license_id: Optional[str]
    record_count: int
    allowed: bool
    denial_reason: Optional[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DataRightsManager:
    """
    Gates ALL data access through licensing checks.
    Every tool call that touches external data MUST pass through this gate.

    Design rationale: Hearth's 10-K explicitly flags MLS data access and
    data provider relationships as a risk factor. This manager ensures:
    1. No data is accessed without a valid license
    2. Bulk transfer restrictions are enforced (TCAD explicitly prohibits bulk)
    3. All access is logged for audit compliance
    4. Rate limits are enforced per license terms
    """

    def __init__(self):
        self._licenses: dict[str, DataLicense] = {}
        self._access_log: list[AccessLog] = []
        self._register_default_licenses()

    def _register_default_licenses(self):
        # RESO Developer Reference Server - free for development/testing
        self.register_license(DataLicense(
            license_id="reso-dev-reference",
            source=DataSource.RESO_REFERENCE,
            market="austin",
            allowed_use_cases=["development", "testing", "prototype"],
            restrictions=["previous_year_data_only", "not_for_production"],
        ))

        # TCAD public access - single property lookups only
        self.register_license(DataLicense(
            license_id="tcad-public",
            source=DataSource.TCAD,
            market="travis_county",
            allowed_use_cases=["single_property_lookup", "valuation_input"],
            restrictions=["no_bulk_transfer", "single_request_only"],
            max_requests_per_hour=60,
        ))

    def register_license(self, license: DataLicense):
        self._licenses[license.license_id] = license

    def check_access(
        self, source: DataSource, market: str, use_case: str, license_id: Optional[str] = None
    ) -> AccessDecision:
        """Check whether access to a data source is permitted."""

        # Find applicable license
        applicable = self._find_license(source, market, use_case, license_id)
        if applicable is None:
            decision = AccessDecision(
                allowed=False,
                denial_reason=f"No valid license found for {source.value} in {market} for use case '{use_case}'",
            )
            self._log_access(source, market, use_case, None, 0, False, decision.denial_reason)
            return decision

        # Check expiry
        if applicable.expires_at and datetime.now(timezone.utc) > applicable.expires_at:
            decision = AccessDecision(
                allowed=False,
                denial_reason=f"License {applicable.license_id} has expired",
            )
            self._log_access(source, market, use_case, applicable.license_id, 0, False, decision.denial_reason)
            return decision

        # Check rate limit
        if applicable.max_requests_per_hour is not None:
            if applicable.request_count_this_hour >= applicable.max_requests_per_hour:
                decision = AccessDecision(
                    allowed=False,
                    denial_reason=f"Rate limit exceeded for license {applicable.license_id} ({applicable.max_requests_per_hour}/hour)",
                )
                self._log_access(source, market, use_case, applicable.license_id, 0, False, decision.denial_reason)
                return decision
            applicable.request_count_this_hour += 1

        # Check use case
        if use_case not in applicable.allowed_use_cases:
            decision = AccessDecision(
                allowed=False,
                denial_reason=f"Use case '{use_case}' not permitted under license {applicable.license_id}. Allowed: {applicable.allowed_use_cases}",
            )
            self._log_access(source, market, use_case, applicable.license_id, 0, False, decision.denial_reason)
            return decision

        decision = AccessDecision(
            allowed=True,
            restrictions=applicable.restrictions,
            license_id=applicable.license_id,
        )
        self._log_access(source, market, use_case, applicable.license_id, 1, True, None)
        logger.info(f"Data access granted: {source.value}/{market}/{use_case} under {applicable.license_id}")
        return decision

    def _find_license(
        self, source: DataSource, market: str, use_case: str, license_id: Optional[str]
    ) -> Optional[DataLicense]:
        if license_id and license_id in self._licenses:
            lic = self._licenses[license_id]
            if lic.source == source:
                return lic
            return None

        for lic in self._licenses.values():
            if lic.source == source and lic.market == market and use_case in lic.allowed_use_cases:
                return lic
        return None

    def _log_access(
        self, source: DataSource, market: str, use_case: str,
        license_id: Optional[str], count: int, allowed: bool, reason: Optional[str]
    ):
        self._access_log.append(AccessLog(
            source=source, market=market, use_case=use_case,
            license_id=license_id, record_count=count,
            allowed=allowed, denial_reason=reason,
        ))

    def get_access_log(self) -> list[AccessLog]:
        return list(self._access_log)
