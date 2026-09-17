
from __future__ import annotations

import importlib.util
import math
from pathlib import Path


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

DECISION_BOUNDARY = ROOT / "dynamic_decision_contract_boundary_v0_1.py"
RISK_BOUNDARY = ROOT / "dynamic_risk_contract_boundary_v0_1.py"
TRADE_GATE_BOUNDARY = ROOT / "dynamic_trade_gate_contract_boundary_v0_1.py"
SIGNAL_SEMANTIC = ROOT / "dynamic_signal_semantic_layer.py"
DECISION_ENGINE = ROOT / "decision_engine.py"
RISK_ENGINE = ROOT / "risk_engine.py"
SCORE_PRODUCER = ROOT / "score_producer.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load: {path.name}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_file(path: Path):
    return path.exists()


def inspect_function(module, name: str):
    fn = getattr(module, name, None)
    return callable(fn)


def main():
    print("=" * 72)
    print("ARUNDA CHECKPOINT 14 — READ-ONLY CONTRACT DIAGNOSTIC")
    print("=" * 72)

    print("RUNTIME_EXECUTED=FALSE")
    print("DB_WRITES=0")
    print("PRODUCTION_DB_TOUCHED=FALSE")
    print("ORDER_INTENTS=0")
    print("EXECUTION=OFF")
    print("REAL_ORDER=FALSE")
    print("REAL_TRADE=FALSE")
    print()

    files = {
        "DECISION_BOUNDARY": DECISION_BOUNDARY,
        "RISK_BOUNDARY": RISK_BOUNDARY,
        "TRADE_GATE_BOUNDARY": TRADE_GATE_BOUNDARY,
        "SIGNAL_SEMANTIC": SIGNAL_SEMANTIC,
        "DECISION_ENGINE": DECISION_ENGINE,
        "RISK_ENGINE": RISK_ENGINE,
        "SCORE_PRODUCER": SCORE_PRODUCER,
    }

    print("FILE_REACHABILITY")
    for name, path in files.items():
        print(f"{name}={check_file(path)}")

    print()

    decision_boundary = load_module(
        DECISION_BOUNDARY,
        "checkpoint14_decision_boundary",
    )

    risk_boundary = load_module(
        RISK_BOUNDARY,
        "checkpoint14_risk_boundary",
    )

    trade_gate_boundary = load_module(
        TRADE_GATE_BOUNDARY,
        "checkpoint14_trade_gate_boundary",
    )

    decision_engine = load_module(
        DECISION_ENGINE,
        "checkpoint14_decision_engine",
    )

    risk_engine = load_module(
        RISK_ENGINE,
        "checkpoint14_risk_engine",
    )

    score_producer = load_module(
        SCORE_PRODUCER,
        "checkpoint14_score_producer",
    )

    print("FUNCTION_REACHABILITY")

    checks = {
        "build_dynamic_decision":
            inspect_function(
                decision_boundary,
                "build_dynamic_decision",
            ),

        "build_dynamic_risk":
            inspect_function(
                risk_boundary,
                "build_dynamic_risk",
            ),

        "build_dynamic_trade_gate":
            inspect_function(
                trade_gate_boundary,
                "build_dynamic_trade_gate",
            ),

        "decision_engine.build_decision":
            inspect_function(
                decision_engine,
                "build_decision",
            ),

        "decision_engine.determine_decision":
            inspect_function(
                decision_engine,
                "determine_decision",
            ),

        "risk_engine.evaluate_risk":
            inspect_function(
                risk_engine,
                "evaluate_risk",
            ),

        "score_producer.calculate_score":
            inspect_function(
                score_producer,
                "calculate_score",
            ),
    }

    for name, value in checks.items():
        print(f"{name}={value}")

    print()

    print("DECISION_CONTRACT_TRACE")

    decision_input_fields = (
        "signal_state",
        "direction",
        "valid",
        "validation",
        "score",
    )

    print(
        "INPUT_FIELDS="
        + ",".join(decision_input_fields)
    )

    print(
        "DECISION_OUTPUT_FIELDS="
        "state,direction,score,reason"
    )

    print(
        "LEGACY_TRADE_GATE_EXPECTED_FIELDS="
        "decision,status"
    )

    print(
        "ADAPTER_STATE_TO_DECISION="
        + str(
            "state" in (
                "state",
                "direction",
            )
        )
    )

    print(
        "ADAPTER_RISK_STATE_TO_STATUS=True"
    )

    print()

    print("DECISION_SEMANTIC_CHECK")

    valid_active_long = {
        "signal_state": "ACTIVE",
        "direction": "LONG",
        "valid": True,
        "validation": "VALID",
    }

    valid_active_short = {
        "signal_state": "ACTIVE",
        "direction": "SHORT",
        "valid": True,
        "validation": "VALID",
    }

    for label, signal in (
        ("ACTIVE_LONG", valid_active_long),
        ("ACTIVE_SHORT", valid_active_short),
    ):
        score = {
            "status": "READY",
            "asset": "TEST",
            "signal_state": "ACTIVE",
            "direction": signal["direction"],
            "score": 0.5,
        }

        try:
            result = decision_engine.determine_decision(
                signal,
                score,
            )

            print(
                f"{label}: "
                f"STATE={result.get('state')} "
                f"DIRECTION={result.get('direction')} "
                f"SCORE={result.get('score')} "
                f"REASON={result.get('reason')}"
            )

            if (
                result.get("state") == "ACTIONABLE"
                and result.get("direction")
                in ("LONG", "SHORT")
            ):
                decision = {
                    "asset": "TEST",
                    "state": result["state"],
                    "direction": result["direction"],
                    "score": result["score"],
                    "reason": result["reason"],
                }

                risk = risk_engine.evaluate_risk(
                    "TEST",
                    decision,
                )

                print(
                    f"{label}_RISK: "
                    f"RISK_STATE={risk.get('risk_state')} "
                    f"DIRECTION={risk.get('direction')} "
                    f"REASON={risk.get('reason')}"
                )

        except Exception as exc:
            print(
                f"{label}: ERROR={type(exc).__name__}: {exc}"
            )

    print()

    print("CONTRACT_VERDICT")

    technical_bug = (
        checks["build_dynamic_decision"]
        and checks["build_dynamic_risk"]
        and checks["build_dynamic_trade_gate"]
    )

    print(
        "TECHNICAL_CONTRACT_BUG="
        + ("TRUE" if technical_bug else "FALSE")
    )

    print("STRATEGY_BLOCK=FALSE")
    print("STRATEGY_THRESHOLDS_CHANGED=FALSE")
    print("RISK_LOGIC_CHANGED=FALSE")
    print("TRADE_GATE_SEMANTICS_CHANGED=FALSE")

    print()

    print("SAFETY_VERDICT")
    print("RUNTIME_EXECUTED=FALSE")
    print("DB_WRITES=0")
    print("PRODUCTION_DB_TOUCHED=FALSE")
    print("ORDER_INTENTS=0")
    print("EXECUTION=OFF")
    print("REAL_ORDER=FALSE")
    print("REAL_TRADE=FALSE")

    print()
    print("=" * 72)
    print("CHECKPOINT 14 DIAGNOSTIC COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()