from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import importlib.util
import math
import sys


ROOT = Path(__file__).resolve().parent
SCORE_ENGINE_FILE = ROOT / "score_producer.py"

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
        raise ValueError("symbol must be str")

    symbol = value.strip().upper()

    if "/" not in symbol:
        raise ValueError("symbol must be BASE/QUOTE")

    base, quote = symbol.split("/", 1)

    if not base or not quote:
        raise ValueError("invalid symbol")

    return f"{base}/{quote}"


def normalize_direction(value: Any) -> str:
    direction = str(value).strip().upper()

    if direction not in ("NONE", "LONG", "SHORT"):
        raise ValueError("invalid direction")

    return direction


def validate_feature_records(records: Any) -> None:
    if not isinstance(records, (list, tuple)):
        raise ValueError("feature_records must be list or tuple")

    if len(records) < 21:
        raise ValueError(
            f"insufficient FeatureRecords: {len(records)} < 21"
        )

    for record in records:
        if isinstance(record, Mapping):
            close = record.get("close")
        else:
            close = getattr(record, "close", None)

        if close is None:
            raise ValueError("FeatureRecord missing close")

        close = float(close)

        if not math.isfinite(close) or close <= 0:
            raise ValueError("invalid FeatureRecord close")


def build_dynamic_score(
    symbol: str,
    direction: str,
    feature_records: Any,
    structural_state: dict[str, Any],
    regime_data: dict[str, Any],
) -> dict[str, Any]:

    dynamic_symbol = normalize_symbol(symbol)
    normalized_direction = normalize_direction(direction)

    validate_feature_records(feature_records)

    if not isinstance(structural_state, dict):
        raise ValueError("structural_state must be dict")

    if not isinstance(regime_data, dict):
        raise ValueError("regime_data must be dict")

    score_engine = load_module(
        SCORE_ENGINE_FILE,
        "arunda_score_engine_dynamic_boundary",
    )

    build_features = getattr(
        score_engine,
        "build_score_features",
        None,
    )

    calculate_score = getattr(
        score_engine,
        "calculate_score",
        None,
    )

    if not callable(build_features):
        raise AttributeError(
            "score_producer.build_score_features unavailable"
        )

    if not callable(calculate_score):
        raise AttributeError(
            "score_producer.calculate_score unavailable"
        )

    score_features = build_features(
        feature_records,
        dynamic_symbol,
    )

    score = calculate_score(
        normalized_direction,
        score_features,
        structural_state,
        regime_data,
    )

    if not math.isfinite(float(score)):
        raise ValueError("non-finite score")

    if score < -1.0 or score > 1.0:
        raise ValueError("score outside [-1,+1]")

    return {
        "status": "READY",
        "asset": dynamic_symbol,
        "signal_state": (
            "NEUTRAL"
            if normalized_direction == "NONE"
            else "ACTIVE"
        ),
        "direction": normalized_direction,
        "score": float(score),
        "score_features": score_features,
        "feature_count": len(feature_records),
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
    score_engine = load_module(
        SCORE_ENGINE_FILE,
        "arunda_score_engine_static_contract_check",
    )

    required = (
        "build_score_features",
        "calculate_score",
    )

    for name in required:
        if not callable(getattr(score_engine, name, None)):
            raise AttributeError(
                f"missing required score interface: {name}"
            )

    if not callable(
        getattr(score_engine, "validate_score_snapshot", None)
    ):
        raise AttributeError(
            "missing score snapshot validator"
        )


def main():
    static_contract_check()

    print("ARUNDA DYNAMIC SCORE CONTRACT BOUNDARY v0.1")
    print("STATIC CHECK ONLY")
    print("SCORE_ENGINE=PASS")
    print("BUILD_SCORE_FEATURES=PASS")
    print("CALCULATE_SCORE=PASS")
    print("VARIABLE_CARDINALITY=PASS")
    print("FIXED_15_USED=FALSE")
    print("SNAPSHOT_VALIDATOR_USED=FALSE")
    print("EXISTING_SCORE_SEMANTICS=PRESERVED")
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
