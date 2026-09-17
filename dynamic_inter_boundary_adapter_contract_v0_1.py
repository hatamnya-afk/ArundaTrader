from __future__ import annotations

"""
ARUNDA DYNAMIC INTER-BOUNDARY ADAPTER CONTRACT v0.1

Purpose:
    Connect existing dynamic boundaries without modifying closed engines.

Rules:
    - variable cardinality
    - per-candidate identity preservation
    - no synthetic data
    - no interpolation/fill/backfill/padding/blending
    - no CMC
    - no legacy/pre-launch data
    - no DB writes
    - no execution
    - no fixed-15 container
    - existing engine semantics preserved
"""

from typing import Any, Mapping


ADAPTER_VERSION = "DYNAMIC_INTER_BOUNDARY_ADAPTER_v0.1"

FORBIDDEN_FLAGS = (
    "synthetic",
    "interpolation",
    "fill",
    "backfill",
    "padding",
    "blending",
    "cmc_used",
)


def _asset(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("asset must be string")

    value = value.strip().upper()

    if not value.endswith("/USDT"):
        raise ValueError("asset must be /USDT")

    return value


def _dict(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be mapping")
    return value


def _same_asset(expected: str, value: Any, name: str) -> None:
    actual = _asset(value)

    if actual != expected:
        raise RuntimeError(
            f"FAIL_CLOSED: identity mismatch at {name}: "
            f"{actual} != {expected}"
        )


def _clean_flags(record: Mapping[str, Any]) -> None:
    for field in FORBIDDEN_FLAGS:
        if field in record and bool(record[field]):
            raise RuntimeError(
                f"FAIL_CLOSED: forbidden flag enabled: {field}"
            )


def adapt_opportunity_to_candidate(
    opportunity: Mapping[str, Any],
) -> dict[str, Any]:

    opportunity = _dict(opportunity, "opportunity")

    asset = _asset(opportunity.get("asset"))

    _clean_flags(opportunity)

    return {
        "asset": asset,
        "direction": opportunity.get("direction"),
        "score": opportunity.get("score"),
        "confidence": opportunity.get("confidence"),
        "opportunity": opportunity,
    }


def adapt_signal_to_candidate(
    signal: Mapping[str, Any],
    candidate_asset: str,
) -> dict[str, Any]:

    signal = _dict(signal, "signal")

    candidate_asset = _asset(candidate_asset)

    signal_asset = signal.get("asset")

    _same_asset(candidate_asset, signal_asset, "signal")

    _clean_flags(signal)

    return {
        "asset": candidate_asset,
        "signal": signal,
    }


def adapt_feature_to_candidate(
    feature_contract: Mapping[str, Any],
    candidate_asset: str,
) -> dict[str, Any]:

    feature_contract = _dict(
        feature_contract,
        "feature_contract",
    )

    candidate_asset = _asset(candidate_asset)

    _same_asset(
        candidate_asset,
        feature_contract.get("symbol"),
        "feature",
    )

    records = feature_contract.get("feature_records")

    if not isinstance(records, (list, tuple)):
        raise RuntimeError(
            "FAIL_CLOSED: feature_records must be sequence"
        )

    if not records:
        raise RuntimeError(
            "FAIL_CLOSED: empty feature_records"
        )

    count = feature_contract.get("feature_count")

    if count != len(records):
        raise RuntimeError(
            "FAIL_CLOSED: feature cardinality mismatch"
        )

    _clean_flags(feature_contract)

    return {
        "asset": candidate_asset,
        "feature_records": records,
        "feature_count": len(records),
        "feature_contract": feature_contract,
    }


def adapt_score_to_candidate(
    score: Mapping[str, Any],
    candidate_asset: str,
) -> dict[str, Any]:

    score = _dict(score, "score")

    candidate_asset = _asset(candidate_asset)

    _same_asset(candidate_asset, score.get("asset"), "score")

    direction = score.get("direction")

    if direction not in {"LONG", "SHORT", "NONE"}:
        raise RuntimeError(
            "FAIL_CLOSED: invalid score direction"
        )

    value = score.get("score")

    if not isinstance(value, (int, float)):
        raise RuntimeError(
            "FAIL_CLOSED: score must be numeric"
        )

    _clean_flags(score)

    return {
        "asset": candidate_asset,
        "direction": direction,
        "score": float(value),
        "score_record": score,
    }


def adapt_decision_to_candidate(
    decision: Mapping[str, Any],
    candidate_asset: str,
) -> dict[str, Any]:

    decision = _dict(decision, "decision")

    candidate_asset = _asset(candidate_asset)

    _same_asset(
        candidate_asset,
        decision.get("asset"),
        "decision",
    )

    state = decision.get("state")
    direction = decision.get("direction")

    if state not in {"ACTIONABLE", "HOLD", "REJECT"}:
        raise RuntimeError(
            "FAIL_CLOSED: invalid decision state"
        )

    if direction not in {"LONG", "SHORT", "NONE"}:
        raise RuntimeError(
            "FAIL_CLOSED: invalid decision direction"
        )

    _clean_flags(decision)

    return {
        "asset": candidate_asset,
        "state": state,
        "direction": direction,
        "score": decision.get("score"),
        "decision": decision,
    }


def adapt_risk_to_candidate(
    risk: Mapping[str, Any],
    candidate_asset: str,
) -> dict[str, Any]:

    risk = _dict(risk, "risk")

    candidate_asset = _asset(candidate_asset)

    _same_asset(
        candidate_asset,
        risk.get("asset"),
        "risk",
    )

    _clean_flags(risk)

    return {
        "asset": candidate_asset,
        "risk_state": risk.get("risk_state"),
        "direction": risk.get("direction"),
        "risk_score": risk.get("risk_score"),
        "risk": risk,
    }


def adapt_trade_gate_to_candidate(
    trade_gate: Mapping[str, Any],
    candidate_asset: str,
) -> dict[str, Any]:

    trade_gate = _dict(
        trade_gate,
        "trade_gate",
    )

    candidate_asset = _asset(candidate_asset)

    _same_asset(
        candidate_asset,
        trade_gate.get("asset"),
        "trade_gate",
    )

    _clean_flags(trade_gate)

    return {
        "asset": candidate_asset,
        "trade_gate_state": trade_gate.get(
            "trade_gate_state"
        ),
        "reasons": trade_gate.get("reasons"),
        "trade_gate": trade_gate,
    }


def validate_variable_cardinality(
    candidates: Any,
) -> bool:

    if not isinstance(candidates, (list, tuple)):
        return False

    seen = set()

    for candidate in candidates:

        if not isinstance(candidate, Mapping):
            return False

        asset = _asset(candidate.get("asset"))

        if asset in seen:
            return False

        seen.add(asset)

    return True


def validate_identity_chain(
    candidate_asset: str,
    *records: Mapping[str, Any],
) -> bool:

    candidate_asset = _asset(candidate_asset)

    for record in records:

        if not isinstance(record, Mapping):
            return False

        if "asset" in record:
            _same_asset(
                candidate_asset,
                record["asset"],
                "identity_chain",
            )

        if "symbol" in record:
            _same_asset(
                candidate_asset,
                record["symbol"],
                "identity_chain",
            )

    return True


def static_contract_check() -> dict[str, Any]:

    candidate = "MARSCOIN/USDT"

    opportunity = {
        "asset": candidate,
        "direction": "LONG",
        "score": 40.6673,
        "confidence": 0.6156,
        "synthetic": False,
        "interpolation": False,
        "fill": False,
        "backfill": False,
        "padding": False,
        "blending": False,
        "cmc_used": False,
    }

    adapted = adapt_opportunity_to_candidate(
        opportunity
    )

    assert adapted["asset"] == candidate

    assert validate_variable_cardinality(
        [adapted]
    )

    assert validate_identity_chain(
        candidate,
        adapted,
    )

    return {
        "status": "PASS",
        "adapter_version": ADAPTER_VERSION,
        "dynamic_universe": True,
        "variable_cardinality": True,
        "fixed_15_used": False,
        "identity_preserved": True,
        "synthetic": False,
        "interpolation": False,
        "fill": False,
        "backfill": False,
        "padding": False,
        "blending": False,
        "cmc_used": False,
        "db_writes": 0,
        "execution": "OFF",
    }


if __name__ == "__main__":
    result = static_contract_check()

    for key, value in result.items():
        print(f"{key.upper()}={value}")
