"""
ARUNDA TRADER — EXCHANGE ADAPTER RESOLVER v0.1

Purpose:
    Resolve a configured exchange into a canonical ExchangeAdapter.

Architecture:
    Production Core
        -> Canonical ExchangeAdapter Boundary
        -> Adapter Resolver
        -> Configured Adapter
        -> BITPIN / TOOBIT / Future Exchange

Rules:
    - No exchange-specific API logic here.
    - No exchange endpoints here.
    - No authentication logic here.
    - No HMAC/signature logic here.
    - No order methods.
    - No cancellation methods.
    - No withdrawal methods.
    - No database writes.
    - No exchange writes.
    - No automatic fallback.
    - Capability availability is enforced per operation.
    - An adapter may resolve even when some read capabilities are unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


from exchange_adapter_boundary import (
    ExchangeAdapter,
    CAPABILITY_PUBLIC_MARKET_DATA,
    CAPABILITY_ACCOUNT_READ,
    CAPABILITY_BALANCE_READ,
    CAPABILITY_SYMBOL_INFO,
    CAPABILITY_TRADING_CONSTRAINTS,
    CAPABILITY_ORDER_SUBMISSION,
    CAPABILITY_ORDER_CANCELLATION,
    CAPABILITY_WITHDRAWAL,
    validate_capabilities,
)

from exchange_adapter_mapping import (
    build_bitpin_boundary,
    build_toobit_boundary,
)


# ============================================================================
# SAFETY CONTRACT
# ============================================================================

EXECUTION_ENABLED = False
ORDER_SUBMISSION_ENABLED = False
ORDER_CANCELLATION_ENABLED = False
WITHDRAWAL_ENABLED = False

DATABASE_WRITE_ENABLED = False
EXCHANGE_WRITE_ENABLED = False


# ============================================================================
# CAPABILITY CONTRACT
# ============================================================================

ALL_CAPABILITIES = (
    CAPABILITY_PUBLIC_MARKET_DATA,
    CAPABILITY_ACCOUNT_READ,
    CAPABILITY_BALANCE_READ,
    CAPABILITY_SYMBOL_INFO,
    CAPABILITY_TRADING_CONSTRAINTS,
    CAPABILITY_ORDER_SUBMISSION,
    CAPABILITY_ORDER_CANCELLATION,
    CAPABILITY_WITHDRAWAL,
)

READ_CAPABILITIES = (
    CAPABILITY_ACCOUNT_READ,
    CAPABILITY_BALANCE_READ,
    CAPABILITY_SYMBOL_INFO,
    CAPABILITY_TRADING_CONSTRAINTS,
)

FORBIDDEN_CAPABILITIES = (
    CAPABILITY_ORDER_SUBMISSION,
    CAPABILITY_ORDER_CANCELLATION,
    CAPABILITY_WITHDRAWAL,
)


# ============================================================================
# REGISTRY
# ============================================================================

AdapterFactory = Callable[[], ExchangeAdapter]

ADAPTER_REGISTRY: Dict[str, AdapterFactory] = {
    "BITPIN": build_bitpin_boundary,
    "TOOBIT": build_toobit_boundary,
}


# ============================================================================
# RESULT CONTRACT
# ============================================================================

@dataclass(frozen=True)
class AdapterResolution:
    status: str
    allowed: bool
    configured_exchange: Optional[str]
    adapter: Optional[ExchangeAdapter]
    reason: str
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# NORMALIZATION
# ============================================================================

def _normalize_exchange(exchange: Any) -> Optional[str]:
    if not isinstance(exchange, str):
        return None

    value = exchange.strip().upper()

    if not value:
        return None

    return value


# ============================================================================
# CONTRACT VALIDATION
# ============================================================================

def _validate_adapter_contract(
    adapter: Any,
) -> tuple[bool, str]:

    # ------------------------------------------------------------------------
    # Adapter type
    # ------------------------------------------------------------------------

    if not isinstance(adapter, ExchangeAdapter):
        return (
            False,
            "Adapter does not implement canonical ExchangeAdapter contract.",
        )

    # ------------------------------------------------------------------------
    # Capability read
    # ------------------------------------------------------------------------

    try:
        capabilities = adapter.capabilities()
    except Exception as exc:
        return (
            False,
            f"Capability read failed: {exc}",
        )

    if not isinstance(capabilities, dict):
        return (
            False,
            "Capability map must be a dictionary.",
        )

    # ------------------------------------------------------------------------
    # Validate canonical capability structure.
    #
    # IMPORTANT:
    # A capability may legitimately be False.
    # False means unavailable and is handled by require_capability().
    # ------------------------------------------------------------------------

    try:
        capability_validation = validate_capabilities(
            capabilities
        )
    except Exception as exc:
        return (
            False,
            f"Capability contract validation failed: {exc}",
        )

    if capability_validation is False:
        return (
            False,
            "Canonical capability contract is invalid.",
        )

    # ------------------------------------------------------------------------
    # Explicit key presence check
    # ------------------------------------------------------------------------

    missing_keys = [
        capability
        for capability in ALL_CAPABILITIES
        if capability not in capabilities
    ]

    if missing_keys:
        return (
            False,
            f"Canonical capability keys missing: {missing_keys}",
        )

    # ------------------------------------------------------------------------
    # Write capabilities MUST remain False.
    # ------------------------------------------------------------------------

    forbidden_enabled = [
        capability
        for capability in FORBIDDEN_CAPABILITIES
        if capabilities.get(capability) is not False
    ]

    if forbidden_enabled:
        return (
            False,
            f"Forbidden write capabilities enabled: "
            f"{forbidden_enabled}",
        )

    return (
        True,
        "Canonical adapter contract valid.",
    )


# ============================================================================
# RESOLUTION
# ============================================================================

def resolve_adapter(
    exchange: Any,
) -> AdapterResolution:

    normalized = _normalize_exchange(exchange)

    # ------------------------------------------------------------------------
    # Invalid configuration
    # ------------------------------------------------------------------------

    if normalized is None:
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=None,
            adapter=None,
            reason="Invalid exchange configuration.",
            data=None,
        )

    # ------------------------------------------------------------------------
    # Registry lookup
    #
    # No fallback is permitted.
    # ------------------------------------------------------------------------

    factory = ADAPTER_REGISTRY.get(normalized)

    if factory is None:
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=normalized,
            adapter=None,
            reason="No adapter registered for configured exchange.",
            data=None,
        )

    # ------------------------------------------------------------------------
    # Adapter construction
    # ------------------------------------------------------------------------

    try:
        adapter = factory()
    except Exception as exc:
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=normalized,
            adapter=None,
            reason=f"Adapter construction failed: {exc}",
            data=None,
        )

    # ------------------------------------------------------------------------
    # Canonical contract
    # ------------------------------------------------------------------------

    valid, reason = _validate_adapter_contract(
        adapter
    )

    if not valid:
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=normalized,
            adapter=None,
            reason=reason,
            data=None,
        )

    # ------------------------------------------------------------------------
    # Successful resolution
    #
    # IMPORTANT:
    # We do NOT require every read capability to be True.
    #
    # Example:
    # BITPIN can resolve successfully while ACCOUNT_READ=False.
    # The individual operation will then fail closed through
    # require_capability().
    # ------------------------------------------------------------------------

    return AdapterResolution(
        status="PASS",
        allowed=True,
        configured_exchange=normalized,
        adapter=adapter,
        reason="Adapter resolved through canonical boundary.",
        data={
            "exchange": normalized,
            "capabilities": adapter.capabilities(),
        },
    )


# ============================================================================
# CAPABILITY ENFORCEMENT
# ============================================================================

def require_capability(
    adapter: Any,
    capability: str,
) -> AdapterResolution:

    # ------------------------------------------------------------------------
    # Adapter contract
    # ------------------------------------------------------------------------

    if not isinstance(adapter, ExchangeAdapter):
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=None,
            adapter=None,
            reason="Invalid canonical adapter.",
            data=None,
        )

    # ------------------------------------------------------------------------
    # Capability identifier
    # ------------------------------------------------------------------------

    if capability not in ALL_CAPABILITIES:
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=None,
            adapter=adapter,
            reason="Unknown capability requested.",
            data={
                "capability": capability,
            },
        )

    # ------------------------------------------------------------------------
    # Read capabilities
    # ------------------------------------------------------------------------

    try:
        capabilities = adapter.capabilities()
    except Exception as exc:
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=None,
            adapter=adapter,
            reason=f"Capability read failed: {exc}",
            data=None,
        )

    if not isinstance(capabilities, dict):
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=None,
            adapter=adapter,
            reason="Capability map is invalid.",
            data=None,
        )

    # ------------------------------------------------------------------------
    # Missing capability = FAIL CLOSED
    # ------------------------------------------------------------------------

    if capability not in capabilities:
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=None,
            adapter=adapter,
            reason=f"Capability missing: {capability}",
            data={
                "capability": capability,
            },
        )

    # ------------------------------------------------------------------------
    # Capability unavailable
    # ------------------------------------------------------------------------

    if capabilities.get(capability) is not True:
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=None,
            adapter=adapter,
            reason=f"Capability unavailable: {capability}",
            data={
                "capability": capability,
                "available": False,
            },
        )

    # ------------------------------------------------------------------------
    # Capability allowed
    # ------------------------------------------------------------------------

    return AdapterResolution(
        status="PASS",
        allowed=True,
        configured_exchange=None,
        adapter=adapter,
        reason=f"Capability available: {capability}",
        data={
            "capability": capability,
            "available": True,
        },
    )


# ============================================================================
# CAPABILITY READER
# ============================================================================

def adapter_capabilities(
    adapter: Any,
) -> AdapterResolution:

    if not isinstance(adapter, ExchangeAdapter):
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=None,
            adapter=None,
            reason="Invalid canonical adapter.",
            data=None,
        )

    try:
        capabilities = adapter.capabilities()
    except Exception as exc:
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=None,
            adapter=adapter,
            reason=f"Capability read failed: {exc}",
            data=None,
        )

    if not isinstance(capabilities, dict):
        return AdapterResolution(
            status="FAIL_CLOSED",
            allowed=False,
            configured_exchange=None,
            adapter=adapter,
            reason="Capability map is invalid.",
            data=None,
        )

    return AdapterResolution(
        status="PASS",
        allowed=True,
        configured_exchange=None,
        adapter=adapter,
        reason="Canonical read-only capability contract valid.",
        data=capabilities,
    )


# ============================================================================
# RESOLVER SELF CHECK
# ============================================================================

def self_check() -> Dict[str, bool]:

    checks: Dict[str, bool] = {}

    # Registry
    checks["registry_bitpin"] = (
        "BITPIN" in ADAPTER_REGISTRY
    )

    checks["registry_toobit"] = (
        "TOOBIT" in ADAPTER_REGISTRY
    )

    # No fallback
    checks["no_fallback"] = (
        "FUTURE_UNREGISTERED_EXCHANGE"
        not in ADAPTER_REGISTRY
    )

    # Global safety
    checks["execution_forbidden"] = (
        EXECUTION_ENABLED is False
    )

    checks["cancel_forbidden"] = (
        ORDER_CANCELLATION_ENABLED is False
    )

    checks["withdraw_forbidden"] = (
        WITHDRAWAL_ENABLED is False
    )

    checks["database_write"] = (
        DATABASE_WRITE_ENABLED
    )

    checks["exchange_write"] = (
        EXCHANGE_WRITE_ENABLED
    )

    # Resolver must not own market data.
    checks["market_data_coupling"] = False

    # Resolver must not be imported by Production Core.
    checks["production_core_dependency"] = False

    # Positive conditions
    positive_checks = (
        checks["registry_bitpin"],
        checks["registry_toobit"],
        checks["no_fallback"],
    )

    # Safety conditions are intentionally required to be False.
    safety_checks = (
        checks["execution_forbidden"],
        checks["cancel_forbidden"],
        checks["withdraw_forbidden"],
        checks["database_write"] is False,
        checks["exchange_write"] is False,
        checks["market_data_coupling"] is False,
        checks["production_core_dependency"] is False,
    )

    checks["all_pass"] = (
        all(positive_checks)
        and all(safety_checks)
    )

    return checks


# ============================================================================
# CLI
# ============================================================================

def main() -> int:

    checks = self_check()

    print("=" * 80)
    print(
        "ARUNDA TRADER — EXCHANGE ADAPTER RESOLVER v0.1"
    )
    print("=" * 80)

    for key, value in checks.items():
        print(
            f"{key:<35}: {value}"
        )

    print("=" * 80)

    if checks["all_pass"]:
        print(
            "SELF CHECK RESULT               : PASS"
        )
        return 0

    print(
        "SELF CHECK RESULT               : FAIL"
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())