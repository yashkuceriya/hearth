"""
DETERMINISTIC Fair Housing Compliance Checker.

This is NOT an LLM content filter. It uses:
- Explicit word/phrase lists (prohibited terms)
- Pattern matching for steering language
- Regex rules for protected class references in prohibited contexts

All rules are auditable, reproducible, and explainable.
Every decision traces to a specific rule with a human-readable explanation.

Protected classes under FHA (42 U.S.C. ss 3604):
Race, Color, National Origin, Religion, Sex, Familial Status, Disability
"""

import re
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class FairHousingViolation:
    violation_type: str
    matched_text: str
    rule_id: str
    explanation: str


@dataclass
class ComplianceResult:
    compliant: bool
    violations: list[FairHousingViolation] = field(default_factory=list)
    sanitized_text: Optional[str] = None
    rules_checked: int = 0


class FairHousingChecker:
    """
    Deterministic, rule-based Fair Housing compliance checker.

    Design rationale:
    - An LLM content filter cannot produce an audit trail for regulatory scrutiny
    - When a regulator asks "why did you allow/block this?", the answer must trace
      to a specific rule, not "the neural network thought it was fine"
    - Every rule has an ID, explanation, and the legal basis for its existence
    """

    def __init__(self):
        self._rules = self._build_rules()

    def check(self, text: str, channel: str = "", session_id: str = "") -> ComplianceResult:
        """Check text for Fair Housing violations. Returns deterministic result."""
        violations = []
        lower_text = text.lower()

        for rule in self._rules:
            matches = rule["pattern"].findall(lower_text)
            for match in matches:
                matched = match if isinstance(match, str) else match[0] if match else ""
                violations.append(FairHousingViolation(
                    violation_type=rule["type"],
                    matched_text=matched,
                    rule_id=rule["id"],
                    explanation=rule["explanation"],
                ))

        result = ComplianceResult(
            compliant=len(violations) == 0,
            violations=violations,
            rules_checked=len(self._rules),
        )

        if violations:
            # Generate sanitized text by removing violating content
            sanitized = text
            for v in violations:
                if v.matched_text:
                    sanitized = re.sub(
                        re.escape(v.matched_text), "[REMOVED - Fair Housing]",
                        sanitized, flags=re.IGNORECASE,
                    )
            result.sanitized_text = sanitized

            logger.warning(
                f"Fair Housing violations detected: session={session_id}, "
                f"count={len(violations)}, rules={[v.rule_id for v in violations]}"
            )

        return result

    def get_rule_explanation(self, rule_id: str) -> Optional[str]:
        """Returns the human-readable explanation for why a rule exists."""
        for rule in self._rules:
            if rule["id"] == rule_id:
                return rule["explanation"]
        return None

    def _build_rules(self) -> list[dict]:
        """Build the deterministic rule set."""
        rules = []

        # === RACE / NATIONAL ORIGIN STEERING ===
        rules.append({
            "id": "FH-RACE-001",
            "type": "racial_steering",
            "pattern": re.compile(
                r'\b(white\s+neighborhood|black\s+neighborhood|hispanic\s+area|'
                r'asian\s+community|ethnic\s+enclave|racially\s+diverse|'
                r'predominantly\s+(?:white|black|hispanic|asian|latino))\b',
                re.IGNORECASE,
            ),
            "explanation": "Describing neighborhoods by racial/ethnic composition constitutes steering "
                          "in violation of FHA \u00a7 3604(a). Steering involves directing buyers to or "
                          "away from neighborhoods based on protected characteristics.",
        })

        rules.append({
            "id": "FH-RACE-002",
            "type": "discriminatory_preference",
            "pattern": re.compile(
                r'\b(no\s+(?:blacks|whites|hispanics|asians|latinos|mexicans|chinese|indian)|'
                r'(?:blacks|whites|hispanics|asians|latinos)\s+(?:only|preferred|welcome|not\s+welcome))\b',
                re.IGNORECASE,
            ),
            "explanation": "Expressing racial/ethnic preferences in housing is prohibited under "
                          "FHA \u00a7 3604(c). This includes both exclusionary and preferential statements.",
        })

        # === RELIGION ===
        rules.append({
            "id": "FH-REL-001",
            "type": "religious_steering",
            "pattern": re.compile(
                r'\b(christian\s+(?:neighborhood|community|area)|'
                r'jewish\s+(?:neighborhood|community|area)|'
                r'muslim\s+(?:neighborhood|community|area)|'
                r'near\s+(?:church|mosque|synagogue|temple)\s+(?:community|neighborhood))\b',
                re.IGNORECASE,
            ),
            "explanation": "Describing neighborhoods by religious character or proximity to religious "
                          "institutions as a selling point constitutes religious steering under FHA \u00a7 3604(a).",
        })

        # === FAMILIAL STATUS ===
        rules.append({
            "id": "FH-FAM-001",
            "type": "familial_status_discrimination",
            "pattern": re.compile(
                r'\b(no\s+children|no\s+kids|adults?\s+only|'
                r'(?:not\s+suitable|unsuitable|inappropriate)\s+for\s+(?:children|kids|families)|'
                r'(?:children|kids)\s+not\s+(?:allowed|permitted|welcome)|'
                r'prefer\s+(?:no\s+children|singles|couples\s+without\s+children))\b',
                re.IGNORECASE,
            ),
            "explanation": "Discriminating based on familial status (presence of children under 18) "
                          "is prohibited under FHA \u00a7 3604(a), unless the property qualifies as "
                          "housing for older persons under \u00a7 3607(b)(2).",
        })

        # === DISABILITY ===
        rules.append({
            "id": "FH-DIS-001",
            "type": "disability_discrimination",
            "pattern": re.compile(
                r'\b(no\s+(?:disabled|handicapped|wheelchair)|'
                r'(?:disabled|handicapped)\s+(?:not\s+welcome|not\s+allowed)|'
                r'must\s+be\s+able[\s-]bodied|'
                r'no\s+(?:mental\s+illness|emotional\s+support\s+animals?|service\s+animals?))\b',
                re.IGNORECASE,
            ),
            "explanation": "Discriminating against persons with disabilities is prohibited under "
                          "FHA \u00a7 3604(f). This includes physical and mental disabilities, and "
                          "refusal to allow reasonable accommodations including service/support animals.",
        })

        # === SEX / GENDER ===
        rules.append({
            "id": "FH-SEX-001",
            "type": "sex_discrimination",
            "pattern": re.compile(
                r'\b((?:males?|females?|men|women)\s+only|'
                r'no\s+(?:single\s+(?:men|women|males?|females?)|'
                r'unmarried\s+(?:couples?|persons?)))\b',
                re.IGNORECASE,
            ),
            "explanation": "Discriminating based on sex in housing is prohibited under FHA \u00a7 3604(a). "
                          "This includes discrimination based on gender identity and sexual orientation "
                          "per Bostock v. Clayton County interpretation extended to FHA.",
        })

        # === NEIGHBORHOOD DESCRIPTION STEERING ===
        rules.append({
            "id": "FH-STEER-001",
            "type": "demographic_neighborhood_description",
            "pattern": re.compile(
                r'\b((?:good|bad|safe|unsafe|dangerous|sketchy|rough|nice)\s+'
                r'(?:neighborhood|area|part\s+of\s+town))\b',
                re.IGNORECASE,
            ),
            "explanation": "Subjective neighborhood quality assessments (good/bad/safe/dangerous) "
                          "can serve as proxies for racial steering under FHA. Descriptions should "
                          "use objective metrics (school ratings, crime statistics with sources, "
                          "walkability scores) rather than subjective characterizations.",
        })

        # === CODED LANGUAGE ===
        rules.append({
            "id": "FH-CODE-001",
            "type": "coded_discriminatory_language",
            "pattern": re.compile(
                r'\b((?:urban|inner[\s-]city|ghetto|barrio)\s+(?:area|neighborhood|community)|'
                r'(?:exclusive|prestigious|elite)\s+(?:neighborhood|community|enclave)|'
                r'up[\s-]and[\s-]coming\s+(?:neighborhood|area)|'
                r'(?:changing|transitioning)\s+neighborhood)\b',
                re.IGNORECASE,
            ),
            "explanation": "Coded language that serves as a proxy for racial/ethnic characteristics "
                          "is prohibited under FHA. Terms like 'urban', 'inner-city', 'exclusive', "
                          "and 'changing neighborhood' have been found to constitute discriminatory "
                          "steering in enforcement actions.",
        })

        return rules
