"""ARUNDA TRADER — PROVIDER PREFLIGHT EVIDENCE ASSEMBLER v0.1

Pure composition boundary for CP46-A6.

This module does NOT query a provider, calculate state, infer policy,
write a database, submit/cancel orders, retry, or synthesize evidence.

Authoritative state producers remain the owners of their respective
evidence objects. This assembler only verifies that the supplied
objects are the exact CP46-A6 evidence contracts and composes them.

For Spot, portfolio exposure evidence is optional because some Spot
providers expose no authoritative provider-native exposure permission.
No synthetic exposure_allowed value is created.
"""

from __future__ import annotations

from typing import Optional

from provider_preflight_v0_1 import (
    ProviderAccountState,
    ProviderContractState,
    ProviderOrderState,
    ProviderPortfolioState,
    ProviderPreflightEvidence,
    ProviderTimestampState,
)


def build_provider_preflight_evidence(
    *,
    contract: ProviderContractState,
    account: ProviderAccountState,
    orders: ProviderOrderState,
    timestamp: ProviderTimestampState,
    portfolio: Optional[ProviderPortfolioState] = None,
) -> ProviderPreflightEvidence:
    """Compose already-authoritative CP46-A6 evidence.

    No field is calculated or inferred here. Missing provider-owned
    state remains missing and is handled by CP46-A6 fail-closed rules.
    """
    if not isinstance(contract, ProviderContractState):
        raise TypeError("contract must be ProviderContractState")

    if not isinstance(account, ProviderAccountState):
        raise TypeError("account must be ProviderAccountState")

    if not isinstance(orders, ProviderOrderState):
        raise TypeError("orders must be ProviderOrderState")

    if not isinstance(timestamp, ProviderTimestampState):
        raise TypeError("timestamp must be ProviderTimestampState")

    if portfolio is not None and not isinstance(
        portfolio,
        ProviderPortfolioState,
    ):
        raise TypeError("portfolio must be ProviderPortfolioState or None")

    return ProviderPreflightEvidence(
        contract=contract,
        account=account,
        orders=orders,
        timestamp=timestamp,
        portfolio=portfolio,
    )


__all__ = [
    "build_provider_preflight_evidence",
]
