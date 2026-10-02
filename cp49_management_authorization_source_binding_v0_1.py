"""CP49 Management Authorization source binding v0.1.

Fail-closed adapter boundary for an independently authoritative Management
authorization source.

This module does not issue, grant, infer, or persist authorization. The source
must already own issuance semantics and return an already-issued authorization
record. The adapter only passes that record through the existing CP49
provider-neutral producer.

No balance, credentials, configuration, account-read success, execution flag,
network side effect, exchange write, or database write can create authorization.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional, Protocol

from cp49_first_execution_evidence_contract_v0_1 import (
    RealCapitalAuthorizationEvidence,
)
from cp49_management_capital_authorization_producer_v0_1 import (
    build_management_capital_authorization_evidence,
)


class ManagementAuthorizationSource(Protocol):
    """Authoritative source that returns an already-issued authorization."""

    def read_authorization(self) -> Mapping[str, Any] | None:
        ...


def build_capital_authorization_from_source(
    source: ManagementAuthorizationSource | Callable[[], Mapping[str, Any] | None],
    *,
    expected_account_id: str,
) -> Optional[RealCapitalAuthorizationEvidence]:
    """Translate an already-issued Management record into CP49 evidence.

    The source is the authority. This boundary never creates an authorization
    record and never treats the absence of a source record as authorization.

    Any source exception or malformed/invalid record fails closed.
    """
    if not isinstance(expected_account_id, str) or not expected_account_id.strip():
        return None

    try:
        if hasattr(source, "read_authorization"):
            record = source.read_authorization()
        elif callable(source):
            record = source()
        else:
            return None
    except Exception:
        return None

    return build_management_capital_authorization_evidence(
        record,
        expected_account_id=expected_account_id,
    )


__all__ = [
    "ManagementAuthorizationSource",
    "build_capital_authorization_from_source",
]
