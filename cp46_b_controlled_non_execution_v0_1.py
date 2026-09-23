from __future__ import annotations

from dataclasses import dataclass

from exchange_execution_contract import CanonicalOrderRequest
from exchange_execution_boundary import execute_order
from provider_preflight_v0_1 import (
    PreflightStatus,
    ProviderAccountState,
    ProviderContractState,
    ProviderOrderPreflightRequest,
    ProviderOrderState,
    ProviderPortfolioState,
    ProviderPreflightEvidence,
    ProviderTimestampState,
    run_provider_preflight,
)
from toobit_trading_adapter import ToobitTradingAdapter


@dataclass(frozen=True)
class CP46BResult:
    name: str
    passed: bool
    detail: str


def build_pass_request() -> ProviderOrderPreflightRequest:
    return ProviderOrderPreflightRequest(
        symbol="BTCUSDT",
        direction="LONG",
        order_type="LIMIT",
        quantity=1,
        quantity_unit="BASE_ASSET",
        intent_id="CP46-B-TEST-INTENT-001",
        timestamp_ms=1_700_000_000_000,
        venue="SPOT",
        reference_price=100.0,
    )


def build_pass_evidence() -> ProviderPreflightEvidence:
    return ProviderPreflightEvidence(
        contract=ProviderContractState(
            symbol_valid=True,
            contract_valid=True,
            min_quantity=0.001,
            max_quantity=1000,
            quantity_step=0.001,
            min_notional=1.0,
            max_notional=1_000_000.0,
        ),
        account=ProviderAccountState(
            state_known=True,
            balance_sufficient=True,
            margin_state_known=True,
            leverage_state_known=True,
            position_conflict=False,
        ),
        orders=ProviderOrderState(
            state_known=True,
            open_order_client_ids=frozenset(),
            recent_order_client_ids=frozenset(),
        ),
        timestamp=ProviderTimestampState(
            state_known=True,
            exchange_timestamp_ms=1_700_000_000_000,
            max_drift_ms=5000,
        ),
        portfolio=ProviderPortfolioState(
            state_known=True,
            exposure_allowed=True,
        ),
    )


def build_canonical_request() -> CanonicalOrderRequest:
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="LIMIT",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100.0,
        reference_price=100.0,
        intent_id="CP46-B-TEST-INTENT-001",
        snapshot_id="CP46-B-TEST-SNAPSHOT-001",
        timestamp="2026-09-23T00:00:00+00:00",
    )


def build_translation_block_request() -> ProviderOrderPreflightRequest:
    return ProviderOrderPreflightRequest(
        symbol="BTCUSDT",
        direction="LONG",
        order_type="MARKET",
        quantity=1,
        quantity_unit="BASE_ASSET",
        intent_id="CP46-B-TEST-INTENT-002",
        timestamp_ms=1_700_000_000_000,
        venue="SPOT",
        reference_price=None,
    )


def run_cp46_b() -> list[CP46BResult]:
    results: list[CP46BResult] = []

    # --------------------------------------------------------
    # 1. Provider preflight PASS
    # --------------------------------------------------------

    preflight = run_provider_preflight(
        build_pass_request(),
        build_pass_evidence(),
    )

    results.append(
        CP46BResult(
            name="PROVIDER_PREFLIGHT_PASS",
            passed=preflight.status is PreflightStatus.PASS,
            detail=(
                f"{preflight.status.value}:"
                f"{preflight.reason.value}"
            ),
        )
    )

    # --------------------------------------------------------
    # 2. Canonical request reaches execution boundary,
    #    but execution remains fail-closed.
    # --------------------------------------------------------

    canonical = build_canonical_request()
    original_quantity = canonical.quantity

    adapter = ToobitTradingAdapter(
        api_key="CP46_B_TEST_KEY",
        api_secret="CP46_B_TEST_SECRET",
    )

    result = execute_order(
        canonical,
        adapter,
    )

    results.append(
        CP46BResult(
            name="EXECUTION_FAIL_CLOSED",
            passed=(
                result.accepted is False
                and result.status == "FAIL_CLOSED"
                and result.error_code == "CP46_E_REQUIRED"
            ),
            detail=(
                f"{result.status}:"
                f"{result.error_code}"
            ),
        )
    )

    # --------------------------------------------------------
    # 3. Quantity must remain byte-for-byte/object-equal
    #    at the canonical contract level.
    # --------------------------------------------------------

    results.append(
        CP46BResult(
            name="QUANTITY_IMMUTABLE",
            passed=canonical.quantity == original_quantity,
            detail=f"quantity={canonical.quantity}",
        )
    )

    # --------------------------------------------------------
    # 4. No exchange execution result may exist.
    # --------------------------------------------------------

    results.append(
        CP46BResult(
            name="NO_EXCHANGE_ORDER_ID",
            passed=result.exchange_order_id is None,
            detail=(
                "exchange_order_id=None"
                if result.exchange_order_id is None
                else "exchange_order_id PRESENT"
            ),
        )
    )

    results.append(
        CP46BResult(
            name="NO_EXECUTED_QUANTITY",
            passed=result.executed_quantity is None,
            detail=(
                "executed_quantity=None"
                if result.executed_quantity is None
                else "executed_quantity PRESENT"
            ),
        )
    )

    results.append(
        CP46BResult(
            name="NO_EXECUTED_PRICE",
            passed=result.executed_price is None,
            detail=(
                "executed_price=None"
                if result.executed_price is None
                else "executed_price PRESENT"
            ),
        )
    )

    # --------------------------------------------------------
    # 5. Provider translation uncertainty must BLOCK.
    # --------------------------------------------------------

    translation_block = run_provider_preflight(
        build_translation_block_request(),
        build_pass_evidence(),
    )

    results.append(
        CP46BResult(
            name="UNRESOLVED_QUANTITY_TRANSLATION_BLOCKS",
            passed=(
                translation_block.status is PreflightStatus.BLOCK
                and translation_block.reason.value
                == "BLOCK_QUANTITY_TRANSLATION_REQUIRED"
            ),
            detail=(
                f"{translation_block.status.value}:"
                f"{translation_block.reason.value}"
            ),
        )
    )

    return results


if __name__ == "__main__":
    results = run_cp46_b()

    for item in results:
        print(
            f"{'PASS' if item.passed else 'FAIL'} | "
            f"{item.name} | {item.detail}"
        )

    if not all(item.passed for item in results):
        raise SystemExit(1)

    print("CP46-B CONTROLLED NON-EXECUTION: PASS")