from dataclasses import dataclass

from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    ExchangeAdapterCapabilities,
)
from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from exchange_execution_order_attempt_boundary_v0_1 import attempt_prepared_order


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


def _readiness():
    return {
        "readiness_state": "READY",
        "readiness_validation": "VALID",
        "asset": "BTC",
        "quantity": 1,
        "entry_price": 100,
        "notional": 100,
    }


def _authorized():
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
