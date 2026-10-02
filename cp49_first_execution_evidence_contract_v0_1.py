"""CP49 first-execution evidence contracts v0.1.

Provider-neutral, fail-closed evidence boundaries.
No network, exchange, DB, execution, or authorization side effects.

This module validates evidence that must already exist from an authoritative
source. It never creates identity, capital permission, or management approval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class AccountSignatureEvidence:
    evidence_id: str
    account_id: str
    account_type: str
    authentication_status: str
    source: str
    source_id: str
    observed_at: str

    def validate(self) -> bool:
        required = (
            self.evidence_id,
            self.account_id,
            self.account_type,
            self.authentication_status,
            self.source,
            self.source_id,
            self.observed_at,
        )
        if any(
            not isinstance(value, str) or not value.strip()
            for value in required
        ):
            return False
        if self.authentication_status != "AUTHENTICATED":
            return False
        if self.source != "AUTHENTICATED_ACCOUNT_READ":
            return False
        return True


@dataclass(frozen=True)
class RealCapitalAuthorizationEvidence:
    authorization_id: str
    account_id: str
    capital_scope: str
    authorized_by: str
    authorized_at: str
    source: str

    def validate(self) -> bool:
        required = (
            self.authorization_id,
            self.account_id,
            self.capital_scope,
            self.authorized_by,
            self.authorized_at,
            self.source,
        )
        if any(
            not isinstance(value, str) or not value.strip()
            for value in required
        ):
            return False
        if self.authorized_by != "MANAGEMENT":
            return False
        if self.source != "MANAGEMENT_AUTHORIZATION":
            return False
        return True


def build_account_signature_evidence(
    *,
    api_key_result: Any,
    account_observation: Any,
    evidence_id: str,
    observed_at: str,
) -> Optional[AccountSignatureEvidence]:
    """Correlate existing authenticated account-read evidence.

    The provider account endpoint is authoritative for the concrete account
    identity (userId/account_id), while the authenticated API-key endpoint is
    authoritative for the key account type. These are preserved as separate
    authoritative facts; the account endpoint need not redundantly expose
    accountType. No account identifier or account type is invented or inferred.
    """
    if api_key_result is None:
        return None
    if getattr(api_key_result, "allowed", False) is not True:
        return None
    if getattr(api_key_result, "status", None) != "PASS":
        return None
    if getattr(api_key_result, "operation", None) != "api_key_check":
        return None

    api_data = getattr(api_key_result, "data", None)
    if not isinstance(api_data, Mapping):
        return None

    account = getattr(account_observation, "account", None)
    if account is None:
        return None
    if getattr(account, "status", None) != "PASS":
        return None

    account_id = getattr(account, "account_id", None)
    api_account_type = api_data.get("account_type")
    source_id = getattr(account, "source_id", None)

    if not isinstance(account_id, str) or not account_id.strip():
        return None
    if not isinstance(api_account_type, str) or not api_account_type.strip():
        return None
    if not isinstance(source_id, str) or not source_id.strip():
        return None

    evidence = AccountSignatureEvidence(
        evidence_id=evidence_id,
        account_id=account_id,
        account_type=api_account_type,
        authentication_status="AUTHENTICATED",
        source="AUTHENTICATED_ACCOUNT_READ",
        source_id=source_id,
        observed_at=observed_at,
    )
    return evidence if evidence.validate() else None


def validate_real_capital_authorization(
    evidence: Optional[RealCapitalAuthorizationEvidence],
    *,
    account_id: str,
) -> bool:
    """Validate an already-issued management authorization.

    This function never creates, infers, or grants authorization.
    """
    if evidence is None or not evidence.validate():
        return False
    if not isinstance(account_id, str) or not account_id.strip():
        return False
    return evidence.account_id == account_id


__all__ = [
    "AccountSignatureEvidence",
    "RealCapitalAuthorizationEvidence",
    "build_account_signature_evidence",
    "validate_real_capital_authorization",
]
