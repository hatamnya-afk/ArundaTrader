import json
from pathlib import Path

from management_execution_authorization_v0_1 import evaluate_management_phase_entry


ROOT = Path(__file__).resolve().parent
MANDATE_PATH = ROOT / "management_mandates" / "real_production_standing_mandate_20261011.json"


def test_recorded_phase_entry_mandate_is_valid_and_provider_scoped():
    observation = json.loads(MANDATE_PATH.read_text(encoding="utf-8"))
    result = evaluate_management_phase_entry(observation)

    assert result["management_state"] == "AUTHORIZED"
    assert result["execution_authorization"] == "AUTHORIZED_STANDING_MANDATE"
    assert result["mandate_id"] == "ARUNDA-REAL-PROD-20261011-001"
    assert result["provider"] == "TOOBIT"
    assert set(result["allowed_markets"]) == {"SPOT", "FUTURES"}
    assert result["autonomous_operation"] is True
    assert result["per_trade_management_authorization_required"] is False
    assert result["authorization_observation"]["authorization_mode"] == "STANDING_MANDATE"


def test_recorded_phase_entry_mandate_contains_no_trade_scoped_fields():
    observation = json.loads(MANDATE_PATH.read_text(encoding="utf-8"))
    forbidden = {
        "attempt_id", "trade_id", "asset", "symbol", "direction", "side",
        "order_type", "quantity", "qty", "per_order_exposure", "exposure",
    }
    assert forbidden.isdisjoint(observation)
