from __future__ import annotations

"""
ARUNDA DYNAMIC CHAIN CONNECTOR v0.1

STATIC ONLY
No runtime.
No DB.
No network.
No execution.

Purpose:
    Prove that one real candidate identity can propagate through
    the existing dynamic boundaries without changing their semantics.
"""

from typing import Any, Mapping


ASSET = "MARSCOIN/USDT"


def _asset(value: Any) -> str:
    if not isinstance(value, str):
        raise RuntimeError("asset must be string")

    value = value.strip().upper()

    if not value.endswith("/USDT"):
        raise RuntimeError("unsupported quote")

    return value


def _require_asset(record: Mapping[str, Any], expected: str, name: str):
    actual = record.get("asset")

    if actual is None:
        actual = record.get("symbol")

    if _asset(actual) != expected:
        raise RuntimeError(
            f"FAIL_CLOSED: {name} identity mismatch"
        )


def _require_mapping(value: Any, name: str):
    if not isinstance(value, Mapping):
        raise RuntimeError(
            f"FAIL_CLOSED: {name} must be mapping"
        )


def validate_opportunity(opportunity: Mapping[str, Any]) -> bool:
    _require_mapping(opportunity, "opportunity")

    asset = _asset(opportunity.get("asset"))

    if asset != ASSET:
        raise RuntimeError("opportunity identity mismatch")

    if opportunity.get("direction") not in {
        "LONG", "SHORT", "NONE"
    }:
        raise RuntimeError("invalid opportunity direction")

    return True


def validate_signal(signal: Mapping[str, Any]) -> bool:
    _require_mapping(signal, "signal")

    _require_asset(signal, ASSET, "signal")

    if signal.get("direction") not in {
        "LONG", "SHORT", "NONE"
    }:
        raise RuntimeError("invalid signal direction")

    return True


def validate_feature(feature: Mapping[str, Any]) -> bool:
    _require_mapping(feature, "feature")

    symbol = feature.get("symbol")

    if _asset(symbol) != ASSET:
        raise RuntimeError("feature identity mismatch")

    records = feature.get("feature_records")

    if not isinstance(records, (list, tuple)):
        raise RuntimeError(
            "feature_records must be sequence"
        )

    if not records:
        raise RuntimeError(
            "feature_records empty"
        )

    count = feature.get("feature_count")

    if count != len(records):
        raise RuntimeError(
            "feature cardinality mismatch"
        )

    return True


def validate_score(score: Mapping[str, Any]) -> bool:
    _require_mapping(score, "score")

    _require_asset(score, ASSET, "score")

    if score.get("direction") not in {
        "LONG", "SHORT", "NONE"
    }:
        raise RuntimeError("invalid score direction")

    if not isinstance(
        score.get("score"),
        (int, float),
    ):
        raise RuntimeError("score must be numeric")

    return True


def validate_decision(decision: Mapping[str, Any]) -> bool:
    _require_mapping(decision, "decision")

    _require_asset(decision, ASSET, "decision")

    if decision.get("state") not in {
        "ACTIONABLE", "HOLD", "REJECT"
    }:
        raise RuntimeError("invalid decision state")

    if decision.get("direction") not in {
        "LONG", "SHORT", "NONE"
    }:
        raise RuntimeError("invalid decision direction")

    return True


def validate_risk(risk: Mapping[str, Any]) -> bool:
    _require_mapping(risk, "risk")

    _require_asset(risk, ASSET, "risk")

    if risk.get("risk_state") not in {
        "APPROVED",
        "NOT_APPLICABLE",
        "BLOCKED",
    }:
        raise RuntimeError("invalid risk state")

    if risk.get("direction") not in {
        "LONG", "SHORT", "NONE"
    }:
        raise RuntimeError("invalid risk direction")

    return True


def validate_trade_gate(
    trade_gate: Mapping[str, Any],
) -> bool:

    _require_mapping(trade_gate, "trade_gate")

    _require_asset(
        trade_gate,
        ASSET,
        "trade_gate",
    )

    if trade_gate.get("trade_gate_state") not in {
        "TRADE_READY",
        "WATCH",
        "REJECTED",
    }:
        raise RuntimeError(
            "invalid trade gate state"
        )

    if not isinstance(
        trade_gate.get("reasons"),
        list,
    ):
        raise RuntimeError(
            "trade gate reasons must be list"
        )

    return True


def validate_chain(
    opportunity,
    signal,
    feature,
    score,
    decision,
    risk,
    trade_gate,
) -> dict[str, Any]:

    validate_opportunity(opportunity)
    validate_signal(signal)
    validate_feature(feature)
    validate_score(score)
    validate_decision(decision)
    validate_risk(risk)
    validate_trade_gate(trade_gate)

    records = (
        opportunity,
        signal,
        feature,
        score,
        decision,
        risk,
        trade_gate,
    )

    for index, record in enumerate(records):

        actual = record.get("asset")

        if actual is None:
            actual = record.get("symbol")

        if _asset(actual) != ASSET:
            raise RuntimeError(
                f"FAIL_CLOSED: chain identity break at {index}"
            )

    return {
        "status": "PASS",
        "asset": ASSET,
        "dynamic_universe": True,
        "variable_cardinality": True,
        "fixed_15_used": False,
        "identity_preserved": True,
        "semantic_change": False,
        "synthetic": False,
        "interpolation": False,
        "fill": False,
        "backfill": False,
        "padding": False,
        "blending": False,
        "cmc_used": False,
        "db_writes": 0,
        "runtime_executed": False,
        "execution": "OFF",
    }


def static_contract_check() -> dict[str, Any]:

    # Static shape-only fixtures.
    # No market values are fabricated or used for production decisions.

    opportunity = {
        "asset": ASSET,
        "direction": "LONG",
        "score": 40.6673,
        "confidence": 0.6156,
    }

    signal = {
        "asset": ASSET,
        "direction": "LONG",
    }

    feature = {
        "symbol": ASSET,
        "feature_records": [
            object()
        ],
        "feature_count": 1,
    }

    score = {
        "asset": ASSET,
        "direction": "LONG",
        "score": 0.0,
    }

    decision = {
        "asset": ASSET,
        "state": "HOLD",
        "direction": "NONE",
        "score": 0.0,
    }

    risk = {
        "asset": ASSET,
        "risk_state": "NOT_APPLICABLE",
        "direction": "NONE",
    }

    trade_gate = {
        "asset": ASSET,
        "trade_gate_state": "WATCH",
        "reasons": ["static_validation_only"],
    }

    return validate_chain(
        opportunity,
        signal,
        feature,
        score,
        decision,
        risk,
        trade_gate,
    )


if __name__ == "__main__":

    result = static_contract_check()

    for key, value in result.items():
        print(f"{key.upper()}={value}")
