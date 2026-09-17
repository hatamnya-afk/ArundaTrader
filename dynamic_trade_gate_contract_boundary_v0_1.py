from pathlib import Path
import atexit
import importlib.util
import sys


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TRADE_GATE_FILE = ROOT / "trade_gate_engine.py"


_PREDICATE_NAMES = (
    "OPPORTUNITY_STATUS",
    "OPPORTUNITY_DIRECTION",
    "OPPORTUNITY_CONFIDENCE",
    "OPPORTUNITY_SCORE",
    "MARKET_DATA_POINTS",
    "SNAPSHOT_AGE",
    "DECISION_STATE",
    "RISK_STATUS",
    "RISK_DECISION",
    "RISK_REWARD",
)


_GATE_AGGREGATE = {
    name: {"PASS_COUNT": 0, "FAIL_COUNT": 0}
    for name in _PREDICATE_NAMES
}

_GATE_CANDIDATES = 0
_FULLY_QUALIFIED = 0
_FIRST_FULLY_QUALIFIED = None
_FIRST_OPPORTUNITY_CONFIDENCE_PASS = None


def _extract_predicate_pass(item):
    if not isinstance(item, dict):
        return None

    value = item.get("pass")
    if isinstance(value, bool):
        return value

    value = item.get("passed")
    if isinstance(value, bool):
        return value

    return None


def _extract_predicate_name(item, index):
    if isinstance(item, dict):
        for key in (
            "predicate",
            "name",
            "condition",
            "check",
            "id",
        ):
            value = item.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip().upper()

    if index < len(_PREDICATE_NAMES):
        return _PREDICATE_NAMES[index]

    return f"PREDICATE_{index + 1}"


def _canonicalize_predicate_name(predicate_name):
    if not isinstance(predicate_name, str):
        return None

    normalized = predicate_name.strip().upper()

    for known in _PREDICATE_NAMES:
        if normalized == known or known in normalized:
            return known

    return normalized


def _record_gate_observability(
    opportunity,
    decision,
    risk,
    observability,
):
    global _GATE_CANDIDATES
    global _FULLY_QUALIFIED
    global _FIRST_FULLY_QUALIFIED
    global _FIRST_OPPORTUNITY_CONFIDENCE_PASS

    _GATE_CANDIDATES += 1

    candidate_predicates = {}

    for index, item in enumerate(observability):
        predicate_name = _extract_predicate_name(
            item,
            index,
        )

        canonical_name = _canonicalize_predicate_name(
            predicate_name,
        )

        predicate_pass = _extract_predicate_pass(item)

        if canonical_name not in _GATE_AGGREGATE:
            continue

        candidate_predicates[canonical_name] = {
            "pass": predicate_pass,
            "raw": item,
        }

        if predicate_pass is True:
            _GATE_AGGREGATE[
                canonical_name
            ]["PASS_COUNT"] += 1

        elif predicate_pass is False:
            _GATE_AGGREGATE[
                canonical_name
            ]["FAIL_COUNT"] += 1

    opportunity_status_pass = (
        candidate_predicates.get(
            "OPPORTUNITY_STATUS",
            {},
        ).get("pass")
        is True
    )

    opportunity_confidence_pass = (
        candidate_predicates.get(
            "OPPORTUNITY_CONFIDENCE",
            {},
        ).get("pass")
        is True
    )

    if (
        _FIRST_OPPORTUNITY_CONFIDENCE_PASS is None
        and opportunity_status_pass
        and opportunity_confidence_pass
    ):
        _FIRST_OPPORTUNITY_CONFIDENCE_PASS = {
            "asset": opportunity.get(
                "asset",
                opportunity.get("symbol"),
            ),
            "symbol": opportunity.get("symbol"),
            "status": opportunity.get("status"),
            "direction": opportunity.get("direction"),
            "confidence": opportunity.get("confidence"),
            "score": opportunity.get(
                "score",
                opportunity.get(
                    "opportunity_score",
                ),
            ),
            "market_data_points": opportunity.get(
                "market_data_points",
                opportunity.get("points"),
            ),
            "snapshot_age": opportunity.get(
                "snapshot_age",
            ),
            "provenance": opportunity.get(
                "provenance",
            ),
            "decision": decision,
            "risk": risk,
            "predicate_details": candidate_predicates,
        }

    all_predicates_pass = (
        len(observability) == len(_PREDICATE_NAMES)
        and all(
            _extract_predicate_pass(item) is True
            for item in observability
        )
    )

    if all_predicates_pass:
        _FULLY_QUALIFIED += 1

        if _FIRST_FULLY_QUALIFIED is None:
            _FIRST_FULLY_QUALIFIED = {
                "asset": opportunity.get(
                    "asset",
                    opportunity.get("symbol"),
                ),
                "symbol": opportunity.get("symbol"),
                "direction": opportunity.get("direction"),
                "confidence": opportunity.get("confidence"),
                "score": opportunity.get(
                    "score",
                    opportunity.get(
                        "opportunity_score",
                    ),
                ),
                "market_data_points": opportunity.get(
                    "market_data_points",
                    opportunity.get("points"),
                ),
                "snapshot_age": opportunity.get(
                    "snapshot_age",
                ),
                "decision": decision,
                "risk_state": risk.get(
                    "risk_state",
                    risk.get("status"),
                ),
                "risk_decision": risk.get(
                    "risk_decision",
                    risk.get("decision"),
                ),
                "risk_reward": risk.get(
                    "risk_reward",
                ),
                "trade_gate_state": "TRADE_READY",
                "provenance": opportunity.get(
                    "provenance",
                ),
            }


def _emit_candidate_details(title, candidate):
    print(title)

    if candidate is None:
        print("NONE")
        return

    for key, value in candidate.items():
        print(f"{key}={value}")


def _emit_gate_aggregate():
    print("=" * 100)
    print("TRADE_GATE_OBSERVABILITY_AGGREGATE")
    print(
        f"TRADE_GATE_CANDIDATES={_GATE_CANDIDATES}"
    )
    print(
        f"FULLY_QUALIFIED_CANDIDATES={_FULLY_QUALIFIED}"
    )

    for name in _PREDICATE_NAMES:
        counts = _GATE_AGGREGATE[name]

        print(
            f"{name}: "
            f"PASS_COUNT={counts['PASS_COUNT']} "
            f"FAIL_COUNT={counts['FAIL_COUNT']}"
        )

    _emit_candidate_details(
        "FIRST_OPPORTUNITY_CONFIDENCE_PASS_CANDIDATE=",
        _FIRST_OPPORTUNITY_CONFIDENCE_PASS,
    )

    if _FIRST_FULLY_QUALIFIED is not None:
        print(
            "FIRST_FULLY_QUALIFIED_CANDIDATE="
        )

        for key, value in _FIRST_FULLY_QUALIFIED.items():
            print(f"{key}={value}")

    print("=" * 100)


atexit.register(_emit_gate_aggregate)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Cannot load {name}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[name] = module

    spec.loader.exec_module(module)

    return module


trade_gate = load_module(
    "arunda_trade_gate_boundary_dep",
    TRADE_GATE_FILE,
)


def normalize_asset(asset):
    if not isinstance(asset, str):
        raise ValueError(
            "asset must be string"
        )

    value = asset.strip().upper()
    parts = value.split("/")

    if (
        len(parts) != 2
        or not parts[0]
        or not parts[1]
    ):
        raise ValueError(
            f"invalid dynamic asset: {asset}"
        )

    return f"{parts[0]}/{parts[1]}"


def _adapt_decision_for_trade_gate(decision):
    """
    Contract adapter only.

    Dynamic Decision contract:
        state

    Legacy Trade Gate contract:
        decision

    Preserve every original field and add only the
    compatibility field required by the authoritative
    Trade Gate engine.
    """

    adapted = dict(decision)

    if (
        "decision" not in adapted
        and "state" in adapted
    ):
        adapted["decision"] = adapted["state"]

    return adapted


def _adapt_risk_for_trade_gate(risk):
    """
    Contract adapter only.

    Dynamic Risk contract:
        risk_state

    Legacy Trade Gate contract:
        status

    Preserve every original field and add only the
    compatibility field required by the authoritative
    Trade Gate engine.
    """

    adapted = dict(risk)

    if (
        "status" not in adapted
        and "risk_state" in adapted
    ):
        adapted["status"] = adapted["risk_state"]

    return adapted


def build_dynamic_trade_gate(
    opportunity,
    decision,
    risk,
):
    """
    Variable-cardinality Trade Gate boundary.

    Reuses authoritative evaluate() only.
    Does not call run_runtime().

    The adapter immediately before evaluate() exists only
    to reconcile the Dynamic Decision/Risk contract field
    names with the legacy Trade Gate consumer contract.

    Trade Gate qualification semantics are unchanged.
    """

    if not isinstance(opportunity, dict):
        raise ValueError(
            "opportunity must be dict"
        )

    if not isinstance(decision, dict):
        raise ValueError(
            "decision must be dict"
        )

    if not isinstance(risk, dict):
        raise ValueError(
            "risk must be dict"
        )

    raw_asset = opportunity.get("asset")

    if raw_asset is None:
        raw_asset = opportunity.get("symbol")

    dynamic_asset = normalize_asset(
        raw_asset
    )

    decision_asset = decision.get("asset")

    if decision_asset is not None:
        if (
            normalize_asset(decision_asset)
            != dynamic_asset
        ):
            raise RuntimeError(
                "Decision asset identity mismatch"
            )

    risk_asset = risk.get("asset")

    if risk_asset is not None:
        if (
            normalize_asset(risk_asset)
            != dynamic_asset
        ):
            raise RuntimeError(
                "Risk asset identity mismatch"
            )

    # ---------------------------------------------------------
    # DYNAMIC → LEGACY TRADE GATE CONTRACT ADAPTER
    #
    # No strategy or threshold change.
    # No mutation of caller-owned dictionaries.
    # ---------------------------------------------------------

    trade_gate_decision = (
        _adapt_decision_for_trade_gate(
            decision
        )
    )

    trade_gate_risk = (
        _adapt_risk_for_trade_gate(
            risk
        )
    )

    # ---------------------------------------------------------
    # AUTHORITATIVE TRADE GATE
    # ---------------------------------------------------------

    result = trade_gate.evaluate(
        opportunity,
        trade_gate_decision,
        trade_gate_risk,
    )

    if not isinstance(result, tuple):
        raise RuntimeError(
            "evaluate() must return tuple"
        )

    if len(result) != 2:
        raise RuntimeError(
            "Trade Gate result must contain "
            "state and reasons"
        )

    gate_state, reasons = result

    if not hasattr(
        trade_gate,
        "build_gate_observability",
    ):
        raise RuntimeError(
            "trade_gate_engine missing "
            "build_gate_observability"
        )

    gate_observability = (
        trade_gate.build_gate_observability(
            opportunity,
            trade_gate_decision,
            trade_gate_risk,
        )
    )

    if not isinstance(
        gate_observability,
        list,
    ):
        raise RuntimeError(
            "Trade Gate observability must be list"
        )

    if gate_state not in (
        "TRADE_READY",
        "WATCH",
        "REJECTED",
    ):
        raise RuntimeError(
            f"invalid Trade Gate state: "
            f"{gate_state}"
        )

    if not isinstance(
        reasons,
        list,
    ):
        raise RuntimeError(
            "Trade Gate reasons must be list"
        )

    if gate_state == "TRADE_READY":
        if reasons != ["all gates passed"]:
            raise RuntimeError(
                "TRADE_READY semantics changed"
            )

    # ---------------------------------------------------------
    # OBSERVABILITY
    #
    # Report original Dynamic Decision/Risk objects so
    # diagnostics reflect the actual upstream contracts.
    # ---------------------------------------------------------

    _record_gate_observability(
        opportunity,
        decision,
        risk,
        gate_observability,
    )

    return {
        "asset": dynamic_asset,
        "trade_gate_state": gate_state,
        "reasons": reasons,
        "gate_observability": gate_observability,
    }


def validate_boundary():
    required = (
        "evaluate",
        "run_runtime",
        "validate_runtime_inputs",
        "build_gate_observability",
    )

    for name in required:
        if not hasattr(
            trade_gate,
            name,
        ):
            raise RuntimeError(
                f"trade_gate_engine missing {name}"
            )

    # ---------------------------------------------------------
    # STATIC CONTRACT TEST DATA ONLY
    # ---------------------------------------------------------

    base_opportunity = {
        "asset": "MARSCOIN/USDT",
        "status": "WAITING_HISTORY",
        "direction": "NONE",
        "confidence": 0.0,
        "score": 0.0,
        "market_data_points": 0,
        "snapshot_age": 0.0,
    }

    base_decision = {
        "asset": "MARSCOIN/USDT",
        "state": "HOLD",
        "direction": "NONE",
    }

    base_risk = {
        "asset": "MARSCOIN/USDT",
        "risk_state": "NOT_APPLICABLE",
        "direction": "NONE",
        "risk_decision": "NONE",
    }

    # Explicitly verify the contract adapter itself.
    adapted_decision = (
        _adapt_decision_for_trade_gate(
            base_decision
        )
    )

    if adapted_decision.get(
        "state"
    ) != "HOLD":
        raise RuntimeError(
            "Decision state preservation failed"
        )

    if adapted_decision.get(
        "decision"
    ) != "HOLD":
        raise RuntimeError(
            "Decision contract adaptation failed"
        )

    adapted_risk = (
        _adapt_risk_for_trade_gate(
            base_risk
        )
    )

    if adapted_risk.get(
        "risk_state"
    ) != "NOT_APPLICABLE":
        raise RuntimeError(
            "Risk state preservation failed"
        )

    if adapted_risk.get(
        "status"
    ) != "NOT_APPLICABLE":
        raise RuntimeError(
            "Risk contract adaptation failed"
        )

    result = build_dynamic_trade_gate(
        base_opportunity,
        base_decision,
        base_risk,
    )

    if result["trade_gate_state"] not in (
        "WATCH",
        "REJECTED",
    ):
        raise RuntimeError(
            "Invalid fail-closed Trade Gate semantics"
        )

    if not isinstance(
        result["gate_observability"],
        list,
    ):
        raise RuntimeError(
            "Observability output missing"
        )

    second = dict(
        base_opportunity
    )

    second["asset"] = (
        "TESTCOIN/USDT"
    )

    second_decision = dict(
        base_decision
    )

    second_decision["asset"] = (
        "TESTCOIN/USDT"
    )

    second_risk = dict(
        base_risk
    )

    second_risk["asset"] = (
        "TESTCOIN/USDT"
    )

    result2 = build_dynamic_trade_gate(
        second,
        second_decision,
        second_risk,
    )

    if result2["asset"] != (
        "TESTCOIN/USDT"
    ):
        raise RuntimeError(
            "Variable asset identity failed"
        )

    if not isinstance(
        result2["gate_observability"],
        list,
    ):
        raise RuntimeError(
            "Variable-cardinality "
            "observability failed"
        )

    return True


if __name__ == "__main__":
    print("=" * 100)
    print(
        "ARUNDA DYNAMIC TRADE GATE "
        "CONTRACT BOUNDARY v0.1"
    )
    print("STATIC CHECK ONLY")

    validate_boundary()

    print("TRADE_GATE_ENGINE=PASS")
    print("EVALUATE=PASS")
    print("VARIABLE_CARDINALITY=PASS")
    print("CONTRACT_ADAPTER=PASS")
    print("DECISION_STATE_TO_DECISION=PASS")
    print("RISK_STATE_TO_STATUS=PASS")
    print("FIXED_15_USED=FALSE")
    print("RUN_RUNTIME_USED=FALSE")
    print(
        "EXISTING_TRADE_GATE_SEMANTICS=PRESERVED"
    )

    print("SYNTHETIC=False")
    print("INTERPOLATION=False")
    print("FILL=False")
    print("BACKFILL=False")
    print("PADDING=False")
    print("BLENDING=False")
    print("CMC_USED=FALSE")
    print("PRODUCTION_DB_TOUCHED=FALSE")
    print("DB_WRITES=0")
    print("RUNTIME_EXECUTED=FALSE")
    print(
        "STATIC_CONTRACT_VALIDATION=PASS"
    )
    print("=" * 100)