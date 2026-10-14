"""Provider-native Toobit account observation boundary (read-only, v0.1).

This module preserves exact provider balance rows as raw evidence. It does
not calculate capital, usable capital, portfolio risk, or position sizing.
Those require separately approved valuation and portfolio policies. The
caller supplies the timestamp captured for the same read cycle; this module
never invents one.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_toobit_raw_account_observation(
    *,
    adapter_result: Any,
    observed_at: str,
    account_scope: str,
    provenance: str,
) -> dict[str, Any]:
    """Normalize a successful adapter result without deriving capital values.

    The result must come from the existing GET-only account read method.
    No transport or network call occurs here. Missing or malformed metadata
    and provider payloads fail closed.
    """
    if not isinstance(observed_at, str) or not observed_at.strip():
        return _blocked("TOOBIT_ACCOUNT_OBSERVATION_TIMESTAMP_MISSING")
    if not isinstance(account_scope, str) or not account_scope.strip():
        return _blocked("TOOBIT_ACCOUNT_SCOPE_MISSING")
    if not isinstance(provenance, str) or not provenance.strip():
        return _blocked("TOOBIT_ACCOUNT_PROVENANCE_MISSING")

    allowed = getattr(adapter_result, "allowed", False)
    reason = getattr(adapter_result, "reason", None)
    data = getattr(adapter_result, "data", None)
    if allowed is not True or not isinstance(data, Mapping):
        return _blocked(
            str(reason).strip()
            if isinstance(reason, str) and reason.strip()
            else "TOOBIT_ACCOUNT_READ_NOT_AVAILABLE"
        )

    if data.get("state_known") is not True:
        return _blocked("TOOBIT_ACCOUNT_STATE_UNKNOWN")
    balances = data.get("balances")
    if not isinstance(balances, list) or any(
        not isinstance(row, Mapping) for row in balances
    ):
        return _blocked("TOOBIT_ACCOUNT_BALANCES_INVALID")

    # Preserve provider-native values exactly. Never infer equity, convert
    # assets to a quote currency, or classify a balance as usable.
    return {
        "observation_state": "AVAILABLE",
        "observation_validation": "RAW_PROVIDER_EVIDENCE_ONLY",
        "observation_source": "TOOBIT_SPOT_ACCOUNT_GET",
        "account_scope": account_scope.strip(),
        "observed_at": observed_at.strip(),
        "provenance": provenance.strip(),
        "balances": [dict(row) for row in balances],
        "capital_state": "BLOCKED",
        "capital_block_reason": "APPROVED_VALUATION_AND_USABLE_CAPITAL_POLICY_REQUIRED",
        "usable_capital": None,
        "available_capital": None,
    }


def _blocked(reason: str) -> dict[str, Any]:
    return {
        "observation_state": "BLOCKED",
        "observation_validation": "INVALID",
        "observation_source": "TOOBIT_SPOT_ACCOUNT_GET",
        "balances": None,
        "capital_state": "BLOCKED",
        "capital_block_reason": reason,
        "usable_capital": None,
        "available_capital": None,
    }


__all__ = ["build_toobit_raw_account_observation"]
