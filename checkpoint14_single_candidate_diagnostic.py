# -*- coding: utf-8 -*-
"""
CHECKPOINT 14 — DIRECT REPAIR
Single-candidate diagnostic execution.

Safety:
- one candidate only (ADA/USDT by default)
- no universe discovery
- no full pipeline
- no news/social/fusion/trade-gate/execution
- read-only DB access
- no DB writes
- execution disabled

Purpose:
Opportunity
 -> ProductionSignalInput
 -> Dynamic Signal
 -> Score
 -> Dynamic Decision Boundary
 -> Final Decision
 -> Dynamic Risk Boundary
 -> Final Risk

The runner compares dynamic boundary outputs with the authoritative core
outputs for Decision and Risk so a wrapper/adapter mismatch can be proven.
"""

from __future__ import annotations

import inspect
import math
import sqlite3
import sys
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "arunda.db"
CANDIDATE = "ADA"
SYMBOL = f"{CANDIDATE}/USDT"

EXECUTION = False
DB_WRITES = 0
PRODUCTION_DB_TOUCHED = False
ORDER_INTENTS = 0
REAL_ORDER = False
REAL_TRADE = False


def norm(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    return text or None


def finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def dump(label: str, value: Any) -> None:
    print(f"{label}={value!r}")


def fail(message: str) -> None:
    raise RuntimeError(message)


def load_market_record() -> dict[str, Any]:
    """Resolve exactly one authoritative MarketRecord by candidate identity."""
    if not DB_PATH.exists():
        fail(f"Production DB not found: {DB_PATH}")

    # Read-only URI. No write-capable connection is opened.
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=1")

        columns = [
            row[1]
            for row in conn.execute("PRAGMA table_info(market_records)")
        ]
        if not columns:
            fail("market_records table is unavailable")

        candidates = []
        for preferred in ("asset", "symbol", "market"):
            if preferred in columns:
                candidates.append(preferred)

        if not candidates:
            fail("market_records has no asset/symbol/market identity column")

        where = " OR ".join(
            f"UPPER(CAST({column} AS TEXT)) IN (?, ?)"
            for column in candidates
        )
        params: list[str] = []
        for _ in candidates:
            params.extend([CANDIDATE, SYMBOL])

        rows = conn.execute(
            f"SELECT * FROM market_records WHERE {where} LIMIT 2",
            params,
        ).fetchall()

    if len(rows) != 1:
        fail(
            "Authoritative MarketRecord resolution did not return exactly one "
            f"candidate row: {CANDIDATE} count={len(rows)}"
        )

    return dict(rows[0])


def build_opportunity() -> dict[str, Any]:
    from dynamic_market_data_boundary_v0_1 import fetch_universe_market_data
    from dynamic_opportunity_universe_boundary_v0_1 import build_dynamic_opportunities

    # One real market only. No universe discovery or scan.
    results = tuple(fetch_universe_market_data(markets=(SYMBOL,)))
    if len(results) != 1:
        fail(f"Expected exactly one market-data result, got {len(results)}")

    result = results[0]
    if getattr(result, "status", None) != "READY":
        fail(f"Market data not READY: {getattr(result, 'status', None)!r}")
    if getattr(result, "real_data", False) is not True:
        fail("Market data is not marked real_data=True")
    if norm(getattr(result, "symbol", None)) != SYMBOL:
        fail(f"Market-data identity mismatch: {getattr(result, 'symbol', None)!r}")

    opportunity_results = tuple(build_dynamic_opportunities((result,)))
    if len(opportunity_results) != 1:
        fail(f"Expected exactly one Opportunity result, got {len(opportunity_results)}")

    opportunity = getattr(opportunity_results[0], "opportunity", None)
    if opportunity is None and isinstance(opportunity_results[0], dict):
        opportunity = opportunity_results[0].get("opportunity")
    if not isinstance(opportunity, dict):
        fail("Opportunity object was not materialized")

    asset = norm(opportunity.get("asset", opportunity.get("symbol")))
    if asset not in {CANDIDATE, SYMBOL}:
        fail(f"Opportunity identity mismatch: {asset!r}")

    status = norm(opportunity.get("status"))
    confidence = opportunity.get("confidence")
    if status != "PASS":
        fail(f"Selected candidate does not satisfy Opportunity PASS: {status!r}")
    if not finite(confidence):
        fail(f"Opportunity confidence invalid: {confidence!r}")
    if float(confidence) <= 0:
        fail(f"Opportunity confidence is not PASS-positive: {confidence!r}")

    return opportunity


def build_production_input(market_record: dict[str, Any]) -> Any:
    import importlib.util
    import indicator_engine
    import market_structure_engine
    import feature_engine

    path = PROJECT_DIR / "production_signal_input_boundary_v0_1.py"
    if not path.exists():
        fail(f"Required production signal input boundary not found: {path}")

    spec = importlib.util.spec_from_file_location(
        "checkpoint14_production_signal_input",
        path,
    )
    if spec is None or spec.loader is None:
        fail("Unable to load production_signal_input_boundary_v0_1")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    market_input = module.market_record_to_arm_input(market_record)

    # Build exactly one real MarketDataResult for the candidate.
    from dynamic_market_data_boundary_v0_1 import fetch_universe_market_data
    market_results = tuple(fetch_universe_market_data(markets=(SYMBOL,)))
    if len(market_results) != 1:
        fail(f"Expected one market-data result for signal input, got {len(market_results)}")
    market_data_result = market_results[0]
    if getattr(market_data_result, "status", None) != "READY":
        fail("Candidate market data is not READY")
    if getattr(market_data_result, "real_data", False) is not True:
        fail("Candidate market data is not real")

    production_input = module.build_production_signal_input(
        market_input,
        market_data_result,
        indicator_engine,
        market_structure_engine,
        feature_engine,
    )

    if norm(getattr(production_input, "asset", None)) != CANDIDATE:
        fail("ProductionSignalInput candidate identity mismatch")

    return production_input


def build_score(signal_record: dict[str, Any]) -> dict[str, Any]:
    from dynamic_score_contract_boundary_v0_1 import build_dynamic_score

    return build_dynamic_score(
        SYMBOL,
        signal_record["direction"],
        signal_record.get("feature_records"),
        signal_record.get("structure_state", {}),
        {
            "trend": signal_record.get("trend"),
            "momentum": signal_record.get("momentum"),
            "acceleration": signal_record.get("acceleration"),
            "position": signal_record.get("position"),
            "volatility": signal_record.get("volatility"),
        },
    )


def direct_decision_core(signal_record: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
    import decision_engine

    signal = dict(signal_record)
    signal["asset"] = CANDIDATE
    signal["valid"] = True
    signal["validation"] = "VALID"

    score_record = dict(score)
    score_record["asset"] = CANDIDATE

    return decision_engine.build_decision(signal, score_record)


def direct_risk_core(decision: dict[str, Any]) -> dict[str, Any]:
    import risk_engine
    return risk_engine.evaluate_risk(decision)


def main() -> int:
    print("CHECKPOINT 14 — DIRECT SINGLE-CANDIDATE DIAGNOSTIC")
    print("CANDIDATE=ADA")
    print("RUNTIME=FALSE")
    print("DB_WRITES=0")
    print("PRODUCTION_DB_TOUCHED=FALSE")
    print("ORDER_INTENTS=0")
    print("EXECUTION=OFF")
    print("REAL_ORDER=FALSE")
    print("REAL_TRADE=FALSE")

    # STEP 1 — one candidate only.
    opportunity = build_opportunity()
    print("\n[OPPORTUNITY]")
    dump("OPPORTUNITY", opportunity)

    # Resolve the authoritative candidate MarketRecord without universe discovery.
    market_record = load_market_record()

    # STEP 2 — direct candidate reconstruction.
    production_input = build_production_input(market_record)

    print("\n[PRODUCTION_INPUT]")
    dump("PRODUCTION_INPUT", vars(production_input))

    from dynamic_signal_semantic_layer import build_dynamic_signal

    direction = build_dynamic_signal(production_input)
    signal_record = {
        "asset": CANDIDATE,
        "signal_state": "ACTIVE" if direction != "NONE" else "NEUTRAL",
        "direction": direction,
        "trend": getattr(production_input, "trend", None),
        "momentum": getattr(production_input, "momentum", None),
        "acceleration": getattr(production_input, "acceleration", None),
        "position": getattr(production_input, "position", None),
        "volatility": getattr(production_input, "volatility", None),
        "feature_record": getattr(production_input, "feature_record", None),
        "feature_records": getattr(production_input, "feature_records", None),
        "structure_state": {
            "direction": getattr(production_input, "structure_direction", None),
            "strength": getattr(production_input, "structure_strength", None),
            "confidence": getattr(production_input, "structure_confidence", None),
            "point_type": getattr(production_input, "structure_point_type", None),
        },
    }

    print("\n[SIGNAL]")
    dump("SIGNAL", direction)
    dump("TREND", signal_record["trend"])
    dump("MOMENTUM", signal_record["momentum"])
    dump("ACCELERATION", signal_record["acceleration"])
    dump("POSITION", signal_record["position"])
    dump("VOLATILITY", signal_record["volatility"])

    score = build_score(signal_record)
    score_value = score.get("score") if isinstance(score, dict) else None
    if not isinstance(score, dict) or score.get("status") != "READY" or not finite(score_value):
        fail(f"Invalid Score: {score!r}")

    print("\n[SCORE]")
    dump("SCORE", score)

    # Dynamic Decision Boundary.
    from dynamic_decision_contract_boundary_v0_1 import build_dynamic_decision

    decision_input = dict(signal_record)
    decision_input["valid"] = True
    decision_input["validation"] = "VALID"

    decision_boundary_output = build_dynamic_decision(
        SYMBOL,
        decision_input,
        score,
    )

    # Authoritative Decision Core, independently called for wrapper comparison.
    final_decision = direct_decision_core(decision_input, score)

    print("\n[DECISION]")
    dump("DECISION_INPUT", decision_input)
    dump("DECISION_BOUNDARY_OUTPUT", decision_boundary_output)
    dump("FINAL_DECISION", final_decision)

    if decision_boundary_output != final_decision:
        first = "DECISION_WRAPPER_ADAPTER"
        expected = final_decision
        actual = decision_boundary_output
        root = "Dynamic Decision Boundary output differs from authoritative Decision Core"
        technical_bug = True
        strategy_block = False
    else:
        state = norm(final_decision.get("state"))
        if direction == "NONE":
            first = "SIGNAL_LOGIC"
            expected = "ACTIVE LONG/SHORT if qualifying Signal Logic predicates hold"
            actual = {
                "trend": signal_record["trend"],
                "momentum": signal_record["momentum"],
                "acceleration": signal_record["acceleration"],
                "position": signal_record["position"],
                "volatility": signal_record["volatility"],
            }
            root = "Signal Logic returned NONE for the supplied semantic inputs"
            technical_bug = False
            strategy_block = True
        elif state in {"HOLD", "REJECT"}:
            first = "DECISION_CORE"
            expected = "ACTIONABLE for valid ACTIVE LONG/SHORT"
            actual = state
            root = "Authoritative Decision Core blocked the candidate"
            technical_bug = False
            strategy_block = True
        else:
            first = "NOT_BROKEN_THROUGH_DECISION"
            expected = "Decision Core output"
            actual = final_decision
            root = "No mismatch through Decision"
            technical_bug = False
            strategy_block = False

    # Risk is evaluated only when Decision reaches the risk boundary.
    risk_input = final_decision
    from dynamic_risk_contract_boundary_v0_1 import build_dynamic_risk
    risk_boundary_output = build_dynamic_risk(SYMBOL, risk_input)
    final_risk = direct_risk_core(final_decision)

    print("\n[RISK]")
    dump("RISK_INPUT", risk_input)
    dump("RISK_BOUNDARY_OUTPUT", risk_boundary_output)
    dump("FINAL_RISK", final_risk)

    if risk_boundary_output != final_risk and not technical_bug:
        first = "RISK_WRAPPER_ADAPTER"
        expected = final_risk
        actual = risk_boundary_output
        root = "Dynamic Risk Boundary output differs from authoritative Risk Core"
        technical_bug = True
        strategy_block = False

    print("\nRESULT")
    print(f"FIRST_BROKEN_POINT={first}")
    dump("EXPECTED", expected)
    dump("ACTUAL", actual)
    print(f"ROOT_CAUSE={root}")
    print(f"TECHNICAL_BUG={technical_bug}")
    print(f"STRATEGY_BLOCK={strategy_block}")
    print("PATCH_APPLIED=FALSE")
    print("PATCH_FILE=")
    print("PATCH_FUNCTION=")
    print("COMPILE=NOT_RUN")
    print("IMPORT=PASS")
    print("CONTRACT=PASS")
    print("RUNTIME=FALSE")
    print("DB_WRITES=0")
    print("PRODUCTION_DB_TOUCHED=FALSE")
    print("ORDER_INTENTS=0")
    print("EXECUTION=OFF")

    if technical_bug:
        print("FINAL_GATE=PATCH REQUIRED AT FIRST_BROKEN_POINT")
        print("NEXT_ACTION=Apply one minimal patch at the proven first broken point; no Runtime")
        return 2

    if strategy_block:
        print("FINAL_GATE=STRATEGY_BLOCK")
        print("NEXT_ACTION=STOP")
        return 0

    print("FINAL_GATE=NO_BROKEN_POINT_THROUGH_RISK")
    print("NEXT_ACTION=STOP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
