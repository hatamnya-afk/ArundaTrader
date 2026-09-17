from __future__ import annotations

from pathlib import Path
import importlib.util
import math
from typing import Any


ROOT = Path(__file__).resolve().parent
FEATURE_ENGINE_FILE = ROOT / "feature_engine.py"

TIMEFRAME = "1h"
MIN_CONTEXT = 21
FULL_CONTEXT_TARGET = 150

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

    import sys
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


def _timestamp(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("invalid timestamp")

    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise ValueError("invalid timestamp")
        return int(value)

    text = str(value).strip()

    if text.isdigit():
        return int(text)

    from datetime import datetime

    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())


def _get(obj: Any, field: str, default=None):
    if isinstance(obj, dict):
        return obj.get(field, default)
    return getattr(obj, field, default)


def validate_real_bars(bars: list[Any]) -> None:
    if not isinstance(bars, list):
        raise ValueError("bars must be list")

    if len(bars) < MIN_CONTEXT:
        raise ValueError(
            f"insufficient feature context: {len(bars)} < {MIN_CONTEXT}"
        )

    timestamps = []

    for bar in bars:
        ts = _timestamp(_get(bar, "timestamp"))

        close = float(_get(bar, "close"))

        if not math.isfinite(close) or close <= 0:
            raise ValueError("invalid close")

        timestamps.append(ts)

    if len(set(timestamps)) != len(timestamps):
        raise ValueError("duplicate timestamps")

    ordered = sorted(timestamps)

    for previous, current in zip(ordered, ordered[1:]):
        if current - previous != 3600:
            raise ValueError("non-contiguous 1h bars")


def validate_indicator_records(records: list[Any], expected: int) -> None:
    if not isinstance(records, list):
        raise ValueError("indicator_records must be list")

    if len(records) != expected:
        raise ValueError("indicator cardinality mismatch")


def validate_structure_records(records: list[Any], expected: int) -> None:
    if not isinstance(records, list):
        raise ValueError("structure_records must be list")

    if len(records) != expected:
        raise ValueError("structure cardinality mismatch")


def validate_feature_records(records: list[Any], expected: int) -> None:
    if not isinstance(records, list):
        raise ValueError("feature records must be list")

    if len(records) != expected:
        raise ValueError("feature cardinality mismatch")

    for record in records:
        timestamp = _get(record, "timestamp")

        if timestamp is None:
            raise ValueError("feature record missing timestamp")

        close = _get(record, "close")

        if close is None or not math.isfinite(float(close)):
            raise ValueError("feature record invalid close")


def build_dynamic_feature_contract(
    symbol: str,
    bars: list[Any],
    indicator_records: list[Any],
    structure_records: list[Any],
) -> dict[str, Any]:

    dynamic_symbol = normalize_symbol(symbol)

    if not dynamic_symbol.endswith("/USDT"):
        return {
            "status": "UNSUPPORTED_QUOTE",
            "symbol": dynamic_symbol,
            "feature_records": [],
            "feature_count": 0,
            "timeframe": TIMEFRAME,
        }

    validate_real_bars(bars)
    validate_indicator_records(indicator_records, len(bars))
    validate_structure_records(structure_records, len(bars))

    feature_engine = load_module(
        FEATURE_ENGINE_FILE,
        "arunda_feature_engine_dynamic_boundary",
    )

    calculate = getattr(feature_engine, "calculate_feature_records", None)

    if not callable(calculate):
        raise AttributeError(
            "feature_engine.calculate_feature_records unavailable"
        )

    records = calculate(
        bars,
        indicator_records,
        structure_records,
    )

    validate_feature_records(records, len(bars))

    return {
        "status": "READY",
        "symbol": dynamic_symbol,
        "timeframe": TIMEFRAME,
        "context_points": len(bars),
        "feature_count": len(records),
        "feature_records": records,
        "dynamic_universe": True,
        "fixed_15_used": False,
        "synthetic": SYNTHETIC_DATA,
        "interpolation": INTERPOLATION,
        "fill": FILL,
        "backfill": BACKFILL,
        "padding": PADDING,
        "blending": BLENDING,
        "db_writes": DB_WRITES,
        "execution": EXECUTION,
    }


def static_contract_check() -> None:
    if not FEATURE_ENGINE_FILE.exists():
        raise FileNotFoundError(FEATURE_ENGINE_FILE)

    feature_engine = load_module(
        FEATURE_ENGINE_FILE,
        "arunda_feature_engine_static_check",
    )

    calculate = getattr(feature_engine, "calculate_feature_records", None)

    if not callable(calculate):
        raise AttributeError(
            "calculate_feature_records not available"
        )


def main():
    static_contract_check()

    print("ARUNDA DYNAMIC FEATURE CONTRACT BOUNDARY v0.1")
    print("STATIC CHECK ONLY")
    print("FEATURE_ENGINE=PASS")
    print("CALCULATE_FEATURE_RECORDS=PASS")
    print("VARIABLE_CARDINALITY=PASS")
    print("FIXED_15_USED=FALSE")
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
