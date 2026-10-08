from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    ExchangeAdapterCapabilities,
)
from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from final_execution_attempt_contract_v0_1 import run_final_execution_attempt_contract


def _request():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=100,
        intent_id="intent-001",
        snapshot_id="snapshot-001",
        timestamp="2026-10-08T00:00:00+00:00",
        decision_id="decision-001",
    )


def _package():
    return {
        "package_state": "EXECUTION_READY_PACKAGE",
        "package_validation": "VALID",
        "execution_authorized": False,
        "execution_submitted": False,
        "provider_binding": "DEFERRED",
        "asset": "BTC",
        "direction": "LONG",
        "entry_price": 100,
        "stop_price": 99,
        "stop_distance": 1,
        "quantity": 1,
        "exposure": 100,
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": "POLICY-1",
        "provenance": "REAL_MARKET",
        "observed_at": "2026-10-08T00:00:00+00:00",
    }


def _authorization():
    return {
        "execution_authorization": "AUTHORIZED",
        "authorization_validation": "VALID",
        "authorization_source": "MANAGEMENT_PHASE_ENTRY",
        "authorization_mode": "STANDING_MANDATE",
        "authorization_id": "REAL-PROD-MANDATE-001",
        "mandate_id": "REAL-PROD-MANDATE-001",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "environment": "REAL_PRODUCTION",
        "allowed_markets": ("SPOT", "FUTURES"),
    }
