from types import SimpleNamespace

import exchange_execution_contract as contract
from dynamic_execution_handoff_v0_1 import build_order_intents_and_boundary_results


def _fixtures():
    decision = {"decision_id": "DECISION-1", "direction": "LONG", "regime": "TRENDING"}
    gate = {"trade_gate_state": "TRADE_READY", "direction": "LONG", "decision_id": "DECISION-1"}
    risk = {
        "risk_status": "APPROVED",
        "position_quantity": 0.01,
        "quantity_unit": "BASE_ASSET",
        "quantity_source": "RISK.position_quantity",
        "quantity_changed": False,
        "quantity_recomputed": False,
        "quantity_rescaled": False,
        "quantity_rounded": False,
        "quantity_clipped": False,
    }
    opportunity = {"price": 60000, "confidence": 0.8, "timestamp": "2026-10-13T10:00:00+00:00"}
    market = SimpleNamespace(
        candles=({"timestamp": 1791885600},),
        source="REAL_PROVIDER",
    )
    return {
        "decision_snapshot": {"BTC": decision},
        "trade_gate_snapshot": {"BTC": gate},
        "risk_snapshot": {"BTC": risk},
        "opportunity_by_asset": {"BTC": opportunity},
        "ready_opportunity_assets": ["BTC"],
        "market_data_by_symbol": {"BTC/USDT": market},
        "regime_snapshot": {"BTC/USDT": {"regime": "TRENDING"}},
    }


def test_trade_ready_builds_intent_request_and_fail_closed_result():
    intents, requests, results, blocked = build_order_intents_and_boundary_results(**_fixtures())
    assert set(intents) == set(requests) == set(results) == {"BTC"}
    assert blocked == {}
    assert requests["BTC"].decision_id == "DECISION-1"
    assert requests["BTC"].quantity == 0.01
    assert set(intents["BTC"]) == {
        "asset", "direction", "entry_price", "confidence",
        "regime", "timestamp", "snapshot_id", "intent_id",
    }
    assert results["BTC"].error_code == "EXECUTION_DISABLED"
    assert results["BTC"].exchange_order_id is None
    assert results["BTC"].trade_event_id is None


def test_missing_quantity_fails_closed_without_request_or_result():
    args = _fixtures()
    args["risk_snapshot"]["BTC"].pop("position_quantity")
    intents, requests, results, blocked = build_order_intents_and_boundary_results(**args)
    assert not intents and not requests and not results
    assert blocked["BTC"] == "RISK_POSITION_QUANTITY_MISSING"


def test_non_trade_ready_does_not_create_intent_or_call_boundary():
    args = _fixtures()
    args["trade_gate_snapshot"]["BTC"]["trade_gate_state"] = "REJECTED"
    intents, requests, results, blocked = build_order_intents_and_boundary_results(**args)
    assert intents == requests == results == blocked == {}


def test_ineligible_opportunity_fails_closed():
    args = _fixtures()
    args["ready_opportunity_assets"] = []
    intents, requests, results, blocked = build_order_intents_and_boundary_results(**args)
    assert not intents and not requests and not results
    assert blocked["BTC"] == "CURRENT_ELIGIBLE_OPPORTUNITY_MISSING"



def test_nonpositive_quantity_fails_closed():
    args = _fixtures()
    args["risk_snapshot"]["BTC"]["position_quantity"] = 0
    intents, requests, results, blocked = build_order_intents_and_boundary_results(**args)
    assert not intents and not requests and not results
    assert blocked["BTC"] == "RISK_POSITION_QUANTITY_NOT_POSITIVE"


def test_decision_identity_mismatch_fails_closed():
    args = _fixtures()
    args["trade_gate_snapshot"]["BTC"]["decision_id"] = "OTHER-DECISION"
    intents, requests, results, blocked = build_order_intents_and_boundary_results(**args)
    assert not intents and not requests and not results
    assert blocked["BTC"] == "DECISION_ID_LINEAGE_MISMATCH"



def test_missing_authoritative_regime_fails_closed():
    args = _fixtures()
    args["regime_snapshot"] = {}
    intents, requests, results, blocked = build_order_intents_and_boundary_results(**args)
    assert not intents and not requests and not results
    assert blocked["BTC"] == "CURRENT_MARKET_REGIME_MISSING"



def test_smart_risk_quantity_provenance_passes_without_relabeling():
    args = _fixtures()
    risk = args["risk_snapshot"]["BTC"]
    risk.update({
        "quantity_source": "SMART_RISK_ENGINE_V0_1",
        "risk_source": "VALIDATED_REAL_CAPITAL_PORTFOLIO_STOP_POLICY",
        "risk_policy_version": "risk-policy-v1",
        "risk_budget": 12.5,
    })
    intents, requests, results, blocked = build_order_intents_and_boundary_results(**args)
    assert blocked == {}
    assert requests["BTC"].quantity == 0.01
    assert requests["BTC"].quantity_source == "SMART_RISK_ENGINE_V0_1"
    assert results["BTC"].error_code == "EXECUTION_DISABLED"


def test_smart_risk_quantity_rejects_missing_validated_source():
    args = _fixtures()
    risk = args["risk_snapshot"]["BTC"]
    risk.update({
        "quantity_source": "SMART_RISK_ENGINE_V0_1",
        "risk_policy_version": "risk-policy-v1",
        "risk_budget": 12.5,
    })
    intents, requests, results, blocked = build_order_intents_and_boundary_results(**args)
    assert not intents and not requests and not results
    assert blocked["BTC"] == "SMART_RISK_SOURCE_PROVENANCE_INVALID"


def test_unknown_quantity_source_fails_closed():
    args = _fixtures()
    args["risk_snapshot"]["BTC"]["quantity_source"] = "RENAMED_TO_LOOK_VALID"
    intents, requests, results, blocked = build_order_intents_and_boundary_results(**args)
    assert not intents and not requests and not results
    assert blocked["BTC"] == "RISK_QUANTITY_PROVENANCE_INVALID"
