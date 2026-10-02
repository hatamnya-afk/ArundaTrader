"""CP49 authoritative real-capital authorization evidence producer v0.1.

Provider-neutral, fail-closed boundary for an already-issued Management
authorization record.

This module does NOT grant authorization. It only translates an independently
authoritative Management authorization record into the existing
RealCapitalAuthorizationEvidence contract when every required fact is present
and bound to the intended account.

No network, exchange, order, execution, database, credential, or configuration
side effect is permitted.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

from cp49_first_execution_evidence_contract_v0_1 import (
    RealCapitalAuthorizationEvidence,
)


_REQUIRED_FIELDS = (
    "authorization_id",
    "account_id",
    "capital_scope",
    "authorized_by",
    "authorized_at",
    "source",
)


def build_management_capital_authorization_evidence(
    authorization_record: Any,
    *,
    expected_account_id: str,
) -> Optional[RealCapitalAuthorizationEvidence]:
    """Build evidence from an already-issued Management authorization.

    The input record is the authoritative source. This function never derives
    authorization from account balance, account-read success, credentials,
    configuration, or execution flags.

    A record is accepted only when:
    - all required fields are non-empty strings;
    - the authorization is explicitly issued by MANAGEMENT;
    - the source is explicitly MANAGEMENT_AUTHORIZATION;
    - the authorized account matches the intended account exactly; and
    - the resulting provider-neutral evidence validates.
    """
    if not isinstance(authorization_record, Mapping):
        return None

    if not isinstance(expected_account_id, str) or not expected_account_id.strip():
        return None

    values = {
        field: authorization_record.get(field)
        for field in _REQUIRED_FIELDS
    }
    if any(
        not isinstance(value, str) or not value.strip()
        for value in values.values()
    ):
        return None

    if values["authorized_by"] != "MANAGEMENT":
        return None
    if values["source"] != "MANAGEMENT_AUTHORIZATION":
        return None
    if values["account_id"] != expected_account_id:
        return None

    evidence = RealCapitalAuthorizationEvidence(
        authorization_id=values["authorization_id"],
        account_id=values["account_id"],
        capital_scope=values["capital_scope"],
        authorized_by=values["authorized_by"],
        authorized_at=values["authorized_at"],
        source=values["source"],
    )
    return evidence if evidence.validate() else None


__all__ = ["build_management_capital_authorization_evidence"]
