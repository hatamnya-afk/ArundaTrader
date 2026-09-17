"""
ARUNDA TRADER — EXCHANGE ADAPTER SELECTION & ROUTING
READ-ONLY RUNTIME VERIFICATION v0.1

CHECKPOINT:
    EXCHANGE ADAPTER SELECTION & ROUTING

RULES:
    - READ ONLY
    - No order submission
    - No cancellation
    - No withdrawal
    - No exchange write
    - No database write
    - Execution remains disabled
    - No automatic fallback
    - Production Core unchanged
    - CMC market-data path unchanged

IMPORTANT:
    Adapter resolution and capability availability are different
    contracts.

    BITPIN may resolve successfully while its unavailable operations
    remain FAIL_CLOSED.

    TOOBIT may resolve successfully with verified read capabilities.
"""

from __future__ import annotations

from pathlib import Path

from exchange_adapter_boundary import (
    ExchangeAdapter,
    CAPABILITY_ACCOUNT_READ,
    CAPABILITY_BALANCE_READ,
    CAPABILITY_SYMBOL_INFO,
    CAPABILITY_TRADING_CONSTRAINTS,
    CAPABILITY_ORDER_SUBMISSION,
    CAPABILITY_ORDER_CANCELLATION,
    CAPABILITY_WITHDRAWAL,
)

from exchange_adapter_resolver import (
    ADAPTER_REGISTRY,
    resolve_adapter,
    require_capability,
    adapter_capabilities,
)


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PIPELINE_FILE = ROOT / "arunda_pipeline.py"
SNAPSHOT_FILE = ROOT / "market_snapshot_engine.py"
RESOLVER_FILE = ROOT / "exchange_adapter_resolver.py"


READ_CAPABILITIES = (
    CAPABILITY_ACCOUNT_READ,
    CAPABILITY_BALANCE_READ,
    CAPABILITY_SYMBOL_INFO,
    CAPABILITY_TRADING_CONSTRAINTS,
)

WRITE_CAPABILITIES = (
    CAPABILITY_ORDER_SUBMISSION,
    CAPABILITY_ORDER_CANCELLATION,
    CAPABILITY_WITHDRAWAL,
)


def status(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def read_text(path: Path) -> str:
    return path.read_text(
        encoding="utf-8"
    ).lower()


def main() -> int:

    failures = []

    print("=" * 80)
    print(
        "ARUNDA TRADER — EXCHANGE ADAPTER SELECTION & ROUTING"
    )
    print(
        "READ-ONLY RUNTIME VERIFICATION v0.1"
    )
    print("=" * 80)

    # ========================================================================
    # RUNTIME SAFETY
    # ========================================================================

    print()
    print("RUNTIME SAFETY")
    print("-" * 80)

    print("REAL EXCHANGE ORDER       : NONE")
    print("DATABASE WRITE            : NONE")
    print("EXCHANGE WRITE            : NONE")
    print("ORDER SUBMISSION          : NONE")
    print("ORDER CANCELLATION        : NONE")
    print("WITHDRAWAL                : NONE")
    print("EXECUTION                 : FALSE")

    # ========================================================================
    # REGISTRY
    # ========================================================================

    print()
    print("ADAPTER REGISTRY")
    print("-" * 80)

    bitpin_registered = (
        "BITPIN" in ADAPTER_REGISTRY
    )

    toobit_registered = (
        "TOOBIT" in ADAPTER_REGISTRY
    )

    print(
        f"BITPIN REGISTERED         : "
        f"{status(bitpin_registered)}"
    )

    print(
        f"TOOBIT REGISTERED         : "
        f"{status(toobit_registered)}"
    )

    if not bitpin_registered:
        failures.append("BITPIN registry")

    if not toobit_registered:
        failures.append("TOOBIT registry")

    # ========================================================================
    # BITPIN RESOLUTION
    # ========================================================================

    print()
    print("BITPIN RESOLUTION")
    print("-" * 80)

    bitpin_resolution = resolve_adapter(
        "BITPIN"
    )

    bitpin_adapter = (
        bitpin_resolution.adapter
    )

    bitpin_resolution_pass = (
        bitpin_resolution.status == "PASS"
        and bitpin_resolution.allowed is True
        and bitpin_resolution.configured_exchange == "BITPIN"
        and isinstance(
            bitpin_adapter,
            ExchangeAdapter,
        )
    )

    print(
        f"STATUS                    : "
        f"{bitpin_resolution.status}"
    )

    print(
        f"ALLOWED                   : "
        f"{bitpin_resolution.allowed}"
    )

    print(
        f"CONFIGURED EXCHANGE      : "
        f"{bitpin_resolution.configured_exchange}"
    )

    print(
        f"CANONICAL ADAPTER        : "
        f"{isinstance(bitpin_adapter, ExchangeAdapter)}"
    )

    print(
        f"REASON                    : "
        f"{bitpin_resolution.reason}"
    )

    print(
        f"BITPIN RESOLUTION         : "
        f"{status(bitpin_resolution_pass)}"
    )

    if not bitpin_resolution_pass:
        failures.append("BITPIN resolution")

    # ========================================================================
    # TOOBIT RESOLUTION
    # ========================================================================

    print()
    print("TOOBIT RESOLUTION")
    print("-" * 80)

    toobit_resolution = resolve_adapter(
        "TOOBIT"
    )

    toobit_adapter = (
        toobit_resolution.adapter
    )

    toobit_resolution_pass = (
        toobit_resolution.status == "PASS"
        and toobit_resolution.allowed is True
        and toobit_resolution.configured_exchange == "TOOBIT"
        and isinstance(
            toobit_adapter,
            ExchangeAdapter,
        )
    )

    print(
        f"STATUS                    : "
        f"{toobit_resolution.status}"
    )

    print(
        f"ALLOWED                   : "
        f"{toobit_resolution.allowed}"
    )

    print(
        f"CONFIGURED EXCHANGE      : "
        f"{toobit_resolution.configured_exchange}"
    )

    print(
        f"CANONICAL ADAPTER        : "
        f"{isinstance(toobit_adapter, ExchangeAdapter)}"
    )

    print(
        f"REASON                    : "
        f"{toobit_resolution.reason}"
    )

    print(
        f"TOOBIT RESOLUTION         : "
        f"{status(toobit_resolution_pass)}"
    )

    if not toobit_resolution_pass:
        failures.append("TOOBIT resolution")

    # ========================================================================
    # BITPIN CAPABILITIES
    # ========================================================================

    print()
    print("BITPIN CAPABILITY CONTRACT")
    print("-" * 80)

    bitpin_capability_map = {}

    if isinstance(
        bitpin_adapter,
        ExchangeAdapter,
    ):

        bitpin_capabilities_result = (
            adapter_capabilities(
                bitpin_adapter
            )
        )

        bitpin_capability_pass = (
            bitpin_capabilities_result.status == "PASS"
            and bitpin_capabilities_result.allowed is True
            and isinstance(
                bitpin_capabilities_result.data,
                dict,
            )
        )

        if bitpin_capability_pass:
            bitpin_capability_map = (
                bitpin_capabilities_result.data
            )

        print(
            f"STATUS                    : "
            f"{bitpin_capabilities_result.status}"
        )

        print(
            f"ALLOWED                   : "
            f"{bitpin_capabilities_result.allowed}"
        )

        print(
            f"REASON                    : "
            f"{bitpin_capabilities_result.reason}"
        )

        print(
            f"DATA                      : "
            f"{bitpin_capability_map}"
        )

    else:

        bitpin_capability_pass = False

        print(
            "STATUS                    : FAIL_CLOSED"
        )

        print(
            "ALLOWED                   : False"
        )

    print(
        f"BITPIN CAPABILITY CONTRACT: "
        f"{status(bitpin_capability_pass)}"
    )

    if not bitpin_capability_pass:
        failures.append(
            "Bitpin capability contract"
        )

    # ========================================================================
    # TOOBIT CAPABILITIES
    # ========================================================================

    print()
    print("TOOBIT CAPABILITY CONTRACT")
    print("-" * 80)

    toobit_capability_map = {}

    if isinstance(
        toobit_adapter,
        ExchangeAdapter,
    ):

        toobit_capabilities_result = (
            adapter_capabilities(
                toobit_adapter
            )
        )

        toobit_capability_pass = (
            toobit_capabilities_result.status == "PASS"
            and toobit_capabilities_result.allowed is True
            and isinstance(
                toobit_capabilities_result.data,
                dict,
            )
        )

        if toobit_capability_pass:
            toobit_capability_map = (
                toobit_capabilities_result.data
            )

        print(
            f"STATUS                    : "
            f"{toobit_capabilities_result.status}"
        )

        print(
            f"ALLOWED                   : "
            f"{toobit_capabilities_result.allowed}"
        )

        print(
            f"REASON                    : "
            f"{toobit_capabilities_result.reason}"
        )

        print(
            f"DATA                      : "
            f"{toobit_capability_map}"
        )

    else:

        toobit_capability_pass = False

        print(
            "STATUS                    : FAIL_CLOSED"
        )

        print(
            "ALLOWED                   : False"
        )

    print(
        f"TOOBIT CAPABILITY CONTRACT: "
        f"{status(toobit_capability_pass)}"
    )

    if not toobit_capability_pass:
        failures.append(
            "Toobit capability contract"
        )

    # ========================================================================
    # TOOBIT READ CAPABILITIES
    # ========================================================================

    print()
    print("TOOBIT REQUIRED READ CAPABILITIES")
    print("-" * 80)

    toobit_read_pass = True

    for capability in READ_CAPABILITIES:

        available = (
            toobit_capability_map.get(
                capability,
                False,
            )
            is True
        )

        print(
            f"{capability:<30}: "
            f"{status(available)}"
        )

        if not available:
            toobit_read_pass = False

    print(
        f"REQUIRED READ CAPABILITIES : "
        f"{status(toobit_read_pass)}"
    )

    if not toobit_read_pass:
        failures.append(
            "Toobit required read capabilities"
        )

    # ========================================================================
    # WRITE CAPABILITY SAFETY
    # ========================================================================

    print()
    print("FORBIDDEN WRITE CAPABILITIES")
    print("-" * 80)

    write_safety_pass = True

    # Test BOTH resolved adapters.
    for exchange_name, capability_map in (
        ("BITPIN", bitpin_capability_map),
        ("TOOBIT", toobit_capability_map),
    ):

        print()
        print(f"{exchange_name}:")

        for capability in WRITE_CAPABILITIES:

            value = capability_map.get(
                capability,
                None,
            )

            safe = value is False

            print(
                f"  {capability:<28}: "
                f"{value} -> {status(safe)}"
            )

            if not safe:
                write_safety_pass = False

    print()
    print(
        f"WRITE SAFETY              : "
        f"{status(write_safety_pass)}"
    )

    if not write_safety_pass:
        failures.append(
            "write capability safety"
        )

    # ========================================================================
    # BITPIN OPERATION FAIL-CLOSED
    # ========================================================================

    print()
    print("BITPIN CAPABILITY FAIL-CLOSED")
    print("-" * 80)

    bitpin_fail_closed_pass = False

    if isinstance(
        bitpin_adapter,
        ExchangeAdapter,
    ):

        account_gate = require_capability(
            bitpin_adapter,
            CAPABILITY_ACCOUNT_READ,
        )

        balance_gate = require_capability(
            bitpin_adapter,
            CAPABILITY_BALANCE_READ,
        )

        symbol_gate = require_capability(
            bitpin_adapter,
            CAPABILITY_SYMBOL_INFO,
        )

        constraints_gate = require_capability(
            bitpin_adapter,
            CAPABILITY_TRADING_CONSTRAINTS,
        )

        print(
            f"ACCOUNT_READ              : "
            f"{account_gate.status}"
        )

        print(
            f"BALANCE_READ              : "
            f"{balance_gate.status}"
        )

        print(
            f"SYMBOL_INFO               : "
            f"{symbol_gate.status}"
        )

        print(
            f"TRADING_CONSTRAINTS       : "
            f"{constraints_gate.status}"
        )

        bitpin_fail_closed_pass = (
            account_gate.allowed is False
            and balance_gate.allowed is False
            and symbol_gate.allowed is False
            and constraints_gate.allowed is False
        )

    print(
        f"BITPIN UNAVAILABLE OPS    : "
        f"{status(bitpin_fail_closed_pass)}"
    )

    if not bitpin_fail_closed_pass:
        failures.append(
            "Bitpin capability fail-closed"
        )

    # ========================================================================
    # TOOBIT CANONICAL READ OPERATIONS
    # ========================================================================

    print()
    print("TOOBIT CANONICAL READ OPERATIONS")
    print("-" * 80)

    toobit_operations_pass = True

    if isinstance(
        toobit_adapter,
        ExchangeAdapter,
    ):

        # ------------------------------------------------------------
        # Account
        # ------------------------------------------------------------

        try:

            account_result = (
                toobit_adapter.get_account()
            )

            account_pass = (
                account_result.status == "PASS"
                and account_result.allowed is True
            )

            print(
                f"ACCOUNT READ              : "
                f"{status(account_pass)}"
            )

            print(
                f"  STATUS                  : "
                f"{account_result.status}"
            )

        except Exception as exc:

            account_pass = False

            print(
                "ACCOUNT READ              : FAIL"
            )

            print(
                f"  ERROR                   : {exc}"
            )

        # ------------------------------------------------------------
        # Balance
        # ------------------------------------------------------------

        try:

            balance_result = (
                toobit_adapter.get_balances()
            )

            balance_pass = (
                balance_result.status == "PASS"
                and balance_result.allowed is True
            )

            print(
                f"BALANCE READ              : "
                f"{status(balance_pass)}"
            )

            print(
                f"  STATUS                  : "
                f"{balance_result.status}"
            )

        except Exception as exc:

            balance_pass = False

            print(
                "BALANCE READ              : FAIL"
            )

            print(
                f"  ERROR                   : {exc}"
            )

        # ------------------------------------------------------------
        # Exchange Info
        # ------------------------------------------------------------

        try:

            exchange_info_result = (
                toobit_adapter.get_exchange_info()
            )

            exchange_info_pass = (
                exchange_info_result.status == "PASS"
                and exchange_info_result.allowed is True
            )

            print(
                f"EXCHANGE INFO             : "
                f"{status(exchange_info_pass)}"
            )

            print(
                f"  STATUS                  : "
                f"{exchange_info_result.status}"
            )

        except Exception as exc:

            exchange_info_pass = False

            print(
                "EXCHANGE INFO             : FAIL"
            )

            print(
                f"  ERROR                   : {exc}"
            )

        # ------------------------------------------------------------
        # Symbol
        # ------------------------------------------------------------

        try:

            symbol_result = (
                toobit_adapter.validate_symbol(
                    "BTC"
                )
            )

            symbol_pass = (
                symbol_result.status == "PASS"
                and symbol_result.allowed is True
            )

            print(
                f"SYMBOL VALIDATION        : "
                f"{status(symbol_pass)}"
            )

            print(
                f"  STATUS                  : "
                f"{symbol_result.status}"
            )

        except Exception as exc:

            symbol_pass = False

            print(
                "SYMBOL VALIDATION        : FAIL"
            )

            print(
                f"  ERROR                   : {exc}"
            )

        # ------------------------------------------------------------
        # Trading Constraints
        # ------------------------------------------------------------

        try:

            constraints_result = (
                toobit_adapter.get_trading_constraints(
                    "BTC"
                )
            )

            constraints_pass = (
                constraints_result.status == "PASS"
                and constraints_result.allowed is True
            )

            print(
                f"TRADING CONSTRAINTS      : "
                f"{status(constraints_pass)}"
            )

            print(
                f"  STATUS                  : "
                f"{constraints_result.status}"
            )

        except Exception as exc:

            constraints_pass = False

            print(
                "TRADING CONSTRAINTS      : FAIL"
            )

            print(
                f"  ERROR                   : {exc}"
            )

        toobit_operations_pass = (
            account_pass
            and balance_pass
            and exchange_info_pass
            and symbol_pass
            and constraints_pass
        )

    else:

        toobit_operations_pass = False

    print()
    print(
        f"TOOBIT READ OPERATIONS    : "
        f"{status(toobit_operations_pass)}"
    )

    if not toobit_operations_pass:
        failures.append(
            "Toobit canonical read operations"
        )

    # ========================================================================
    # INVALID EXCHANGE
    # ========================================================================

    print()
    print("INVALID EXCHANGE")
    print("-" * 80)

    invalid = resolve_adapter(
        "INVALID_EXCHANGE"
    )

    invalid_pass = (
        invalid.status == "FAIL_CLOSED"
        and invalid.allowed is False
        and invalid.adapter is None
    )

    print(
        f"STATUS                    : "
        f"{invalid.status}"
    )

    print(
        f"ALLOWED                   : "
        f"{invalid.allowed}"
    )

    print(
        f"ADAPTER                   : "
        f"{invalid.adapter}"
    )

    print(
        f"INVALID EXCHANGE          : "
        f"{status(invalid_pass)}"
    )

    if not invalid_pass:
        failures.append(
            "invalid exchange fail-closed"
        )

    # ========================================================================
    # MISSING ADAPTER / NO FALLBACK
    # ========================================================================

    print()
    print("MISSING ADAPTER")
    print("-" * 80)

    missing = resolve_adapter(
        "FUTURE_UNREGISTERED_EXCHANGE"
    )

    missing_pass = (
        missing.status == "FAIL_CLOSED"
        and missing.allowed is False
        and missing.adapter is None
    )

    print(
        f"STATUS                    : "
        f"{missing.status}"
    )

    print(
        f"ALLOWED                   : "
        f"{missing.allowed}"
    )

    print(
        f"ADAPTER                   : "
        f"{missing.adapter}"
    )

    print(
        f"MISSING ADAPTER           : "
        f"{status(missing_pass)}"
    )

    if not missing_pass:
        failures.append(
            "missing adapter fail-closed"
        )

    no_fallback_pass = (
        invalid.adapter is None
        and missing.adapter is None
    )

    print(
        f"NO AUTOMATIC FALLBACK     : "
        f"{status(no_fallback_pass)}"
    )

    if not no_fallback_pass:
        failures.append(
            "automatic fallback detected"
        )

    # ========================================================================
    # RESOLVER EXCHANGE-SPECIFIC COUPLING
    # ========================================================================

    print()
    print("RESOLVER COUPLING")
    print("-" * 80)

    resolver_text = read_text(
        RESOLVER_FILE
    )

    # These are actual exchange-specific implementation markers.
    # Generic capability names are intentionally NOT included.
    forbidden_exchange_implementation = (
        "api.toobit.com",
        "api.bitpin.com",
        "x-bb-apikey",
        "x-cmc-pro-api-key",
        "hmac.new",
        "requests.get(",
        "requests.post(",
        "requests.put(",
        "requests.delete(",
    )

    coupling_hits = [
        marker
        for marker in forbidden_exchange_implementation
        if marker in resolver_text
    ]

    resolver_coupling_pass = (
        len(coupling_hits) == 0
    )

    print(
        "EXCHANGE-SPECIFIC COUPLING : "
        + (
            "NONE"
            if resolver_coupling_pass
            else str(coupling_hits)
        )
    )

    if not resolver_coupling_pass:
        failures.append(
            "resolver exchange-specific coupling"
        )

    # ========================================================================
    # PRODUCTION CORE / CMC ISOLATION
    # ========================================================================

    print()
    print("PRODUCTION CORE / CMC ISOLATION")
    print("-" * 80)

    core_text = read_text(
        PIPELINE_FILE
    )

    snapshot_text = read_text(
        SNAPSHOT_FILE
    )

    core_exchange_markers = (
        "toobit",
        "bitpin",
        "place_order",
        "cancel_order",
        "withdraw",
        "exchange_adapter_resolver",
    )

    core_hits = [
        marker
        for marker in core_exchange_markers
        if marker in core_text
    ]

    production_core_unchanged = (
        len(core_hits) == 0
    )

    cmc_path_unchanged = (
        "market_snapshot_engine"
        in core_text
        and "coinmarketcap"
        in snapshot_text
        and "current_runtime_snapshot"
        in snapshot_text
    )

    print(
        "PRODUCTION CORE EXCHANGE COUPLING : "
        + (
            "NONE"
            if production_core_unchanged
            else str(core_hits)
        )
    )

    print(
        f"CMC MARKET DATA PATH       : "
        f"{status(cmc_path_unchanged)}"
    )

    print(
        f"PRODUCTION CORE UNCHANGED   : "
        f"{status(production_core_unchanged)}"
    )

    if not production_core_unchanged:
        failures.append(
            "production core exchange coupling"
        )

    if not cmc_path_unchanged:
        failures.append(
            "CMC market data path changed"
        )

    # ========================================================================
    # STATIC RESOLVER WRITE SURFACE
    # ========================================================================

    print()
    print("RESOLVER WRITE SURFACE")
    print("-" * 80)

    resolver_write_markers = (
        "requests.post(",
        "requests.put(",
        "requests.delete(",
        "insert into",
        "update ",
        "delete from",
    )

    resolver_write_hits = [
        marker
        for marker in resolver_write_markers
        if marker in resolver_text
    ]

    resolver_write_pass = (
        len(resolver_write_hits) == 0
    )

    print(
        "RESOLVER WRITE SURFACE     : "
        + (
            "NONE"
            if resolver_write_pass
            else str(resolver_write_hits)
        )
    )

    if not resolver_write_pass:
        failures.append(
            "resolver write surface"
        )

    # ========================================================================
    # FINAL SAFETY CONTRACT
    # ========================================================================

    print()
    print("FINAL SAFETY CONTRACT")
    print("-" * 80)

    execution_false = (
        write_safety_pass
        and resolver_write_pass
        and resolver_coupling_pass
    )

    print(
        "ORDER WRITE                : NONE"
    )

    print(
        "EXCHANGE WRITE             : NONE"
    )

    print(
        "DATABASE WRITE             : NONE"
    )

    print(
        f"EXECUTION                  : "
        f"{'FALSE' if execution_false else 'FAIL'}"
    )

    if not execution_false:
        failures.append(
            "execution safety"
        )

    # ========================================================================
    # FINAL REPORT
    # ========================================================================

    print()
    print("=" * 80)

    if failures:

        print(
            "OVERALL RESULT             : BLOCKED"
        )

        print()
        print("FAILURES:")

        for failure in failures:
            print(
                f"- {failure}"
            )

        print("=" * 80)

        return 1

    print(
        "ADAPTER RESOLVER STATUS    : READY"
    )

    print(
        "CONFIGURATION SOURCE       : ADAPTER_REGISTRY"
    )

    print(
        "BITPIN RESOLUTION          : PASS"
    )

    print(
        "TOOBIT RESOLUTION          : PASS"
    )

    print(
        "CANONICAL CONTRACT         : PASS"
    )

    print(
        "EXCHANGE-SPECIFIC COUPLING : NONE"
    )

    print(
        "INVALID EXCHANGE           : PASS / FAIL-CLOSED"
    )

    print(
        "MISSING ADAPTER            : PASS / FAIL-CLOSED"
    )

    print(
        "MISSING CAPABILITY         : PASS / FAIL-CLOSED"
    )

    print(
        "CMC PATH                   : UNCHANGED"
    )

    print(
        "PRODUCTION CORE            : UNCHANGED"
    )

    print(
        "DATABASE WRITE             : NONE"
    )

    print(
        "EXCHANGE WRITE             : NONE"
    )

    print(
        "ORDER                      : NONE"
    )

    print(
        "EXECUTION                  : FALSE"
    )

    print(
        "OVERALL RESULT             : PASS"
    )

    print(
        "STATUS                     : "
        "EXCHANGE_SELECTION_ROUTING_READY"
    )

    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())