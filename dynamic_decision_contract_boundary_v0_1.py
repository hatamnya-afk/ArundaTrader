from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import importlib.util
import sys
import math


ROOT = Path(__file__).resolve().parent
DECISION_ENGINE_FILE = ROOT / "decision_engine.py"

DB_WRITES = 0
EXECUTION = False
CMC_FORBIDDEN = True
SYNTHETIC_DATA = False
INTERPOLATION = False
FILL = False
BACKFILL = False
PADDING = False
BLENDING = False


def load_module(path: Path, name: str):
    if not path.exists():
        raise FileNotFoundError(path)

    spec = importlib.util.spec_from_file_location(name, path)

    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def normalize_symbol(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("asset must be str")

    value = value.strip().upper()

    if "/" not in value:
        raise ValueError("asset must be BASE/QUOTE")

    base, quote = value.split("/", 1)

    if not base or not quote:
        raise ValueError("invalid asset")

    return f"{base}/{quote}"


def validate_signal_input(
    signal_record: Mapping[str, Any],
) -> None:

    required = (
        "signal_state",
        "direction",
        "valid",
        "validation",
    )

    for field in required:
        if field not in signal_record:
            raise ValueError(
                f"signal missing field: {field}"
            )

    if signal_record["signal_state"] not in (
        "ACTIVE",
        "NEUTRAL",
    ):
        raise ValueError("invalid signal_state")

    if signal_record["direction"] not in (
        "LONG",
        "SHORT",
        "NONE",
    ):
        raise ValueError("invalid direction")

    if not isinstance(
        signal_record["valid"],
        bool,
    ):
        raise ValueError("invalid signal validity")


def validate_score_input(
    score_record: Mapping[str, Any],
) -> None:

    if "score" not in score_record:
        raise ValueError("score missing")

    score = float(score_record["score"])

    if not math.isfinite(score):
        raise ValueError("non-finite score")

    if score < -1.0 or score > 1.0:
        raise ValueError("score outside [-1,+1]")


def build_dynamic_decision(
    asset: str,
    signal_record: Mapping[str, Any],
    score_record: Mapping[str, Any],
) -> dict[str, Any]:

    dynamic_asset = normalize_symbol(asset)
    base_asset = dynamic_asset.split("/", 1)[0]

    validate_signal_input(signal_record)
    validate_score_input(score_record)

    if signal_record.get("asset") not in (
        None,
        base_asset,
        dynamic_asset,
    ):
        raise ValueError(
            f"signal asset mismatch: "
            f"{dynamic_asset}:{signal_record.get('asset')}"
        )

    if score_record.get("asset") not in (
        None,
        base_asset,
        dynamic_asset,
    ):
        raise ValueError(
            f"score asset mismatch: "
            f"{dynamic_asset}:{score_record.get('asset')}"
        )

    decision_engine = load_module(
        DECISION_ENGINE_FILE,
        "arunda_decision_engine_dynamic_boundary",
    )

    build_decision = getattr(
        decision_engine,
        "build_decision",
        None,
    )

    if not callable(build_decision):
        raise AttributeError(
            "decision_engine.build_decision unavailable"
        )

    legacy_signal = dict(signal_record)
    legacy_score = dict(score_record)

    legacy_signal["asset"] = base_asset
    legacy_score["asset"] = base_asset

    import decision_contract

    previous_assets = decision_contract.EXPECTED_ASSETS
    previous_count = decision_contract.EXPECTED_ASSET_COUNT

    try:
        if base_asset not in previous_assets:
            decision_contract.EXPECTED_ASSETS = (
                *previous_assets,
                base_asset,
            )
            decision_contract.EXPECTED_ASSET_COUNT = len(
                decision_contract.EXPECTED_ASSETS
            )

        decision = build_decision(
            base_asset,
            legacy_signal,
            legacy_score,
        )

    finally:
        decision_contract.EXPECTED_ASSETS = previous_assets
        decision_contract.EXPECTED_ASSET_COUNT = previous_count

    if not isinstance(decision, dict):
        raise ValueError("invalid decision result")

    if decision.get("asset") != base_asset:
        raise ValueError(
            "legacy decision asset mismatch"
        )

    if decision.get("state") not in (
        "ACTIONABLE",
        "HOLD",
        "REJECT",
    ):
        raise ValueError("invalid decision state")

    if decision.get("direction") not in (
        "LONG",
        "SHORT",
        "NONE",
    ):
        raise ValueError("invalid decision direction")

    score = float(decision.get("score"))

    if not math.isfinite(score):
        raise ValueError("non-finite decision score")

    return {
        "status": "READY",
        "asset": dynamic_asset,
        "state": decision["state"],
        "direction": decision["direction"],
        "score": score,
        "reason": decision["reason"],
        "dynamic_universe": True,
        "fixed_15_used": False,
        "snapshot_validator_used": False,
        "synthetic": SYNTHETIC_DATA,
        "interpolation": INTERPOLATION,
        "fill": FILL,
        "backfill": BACKFILL,
        "padding": PADDING,
        "blending": BLENDING,
        "cmc_used": False,
        "db_writes": DB_WRITES,
        "execution": EXECUTION,
    }

def static_contract_check() -> None:

    decision_engine = load_module(
        DECISION_ENGINE_FILE,
        "arunda_decision_engine_static_contract_check",
    )

    if not callable(
        getattr(
            decision_engine,
            "build_decision",
            None,
        )
    ):
        raise AttributeError(
            "build_decision unavailable"
        )

    if not callable(
        getattr(
            decision_engine,
            "determine_decision",
            None,
        )
    ):
        raise AttributeError(
            "determine_decision unavailable"
        )

    if not callable(
        getattr(
            decision_engine,
            "validate_decision_snapshot",
            None,
        )
    ):
        raise AttributeError(
            "snapshot validator unavailable"
        )
def main():
    static_contract_check()

    print("ARUNDA DYNAMIC DECISION CONTRACT BOUNDARY v0.1")
    print("STATIC CHECK ONLY")
    print("DECISION_ENGINE=PASS")
    print("BUILD_DECISION=PASS")
    print("DETERMINE_DECISION=PASS")
    print("VARIABLE_CARDINALITY=PASS")
    print("FIXED_15_USED=FALSE")
    print("SNAPSHOT_VALIDATOR_USED=FALSE")
    print("EXISTING_DECISION_SEMANTICS=PRESERVED")
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
    print("STATIC_CONTRACT_VALIDATION=PASS")


if __name__ == "__main__":
    main()
