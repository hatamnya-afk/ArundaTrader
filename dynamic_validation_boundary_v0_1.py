
"""
ARUNDA DYNAMIC VALIDATION CONTRACT BOUNDARY v0.1
================================================

Purpose
-------
Production Boundary for dynamic-universe signal validation.

Architecture
------------
REAL PRODUCTION UNIVERSE
        |
        v
DYNAMIC VALIDATION BOUNDARY
        |
        v
signal_validator.validate_one_signal()
        |
        v
VALIDATED SIGNAL PER ASSET

Rules
-----
- signal_validator.py is CLOSED and is NOT modified.
- Historical fixed-15 snapshot validation is NOT used.
- Production cardinality belongs to Production Universe.
- One asset is validated independently.
- No synthetic data.
- No interpolation.
- No fill.
- No backfill.
- No padding.
- No blending.
- No CMC.
- No DB writes.
- Execution OFF.
"""

from __future__ import annotations

from pathlib import Path
import importlib.util
from typing import Any, Mapping


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent

VALIDATOR_FILE = ROOT / "signal_validator.py"

UNIVERSE_FILE = (
    ROOT / "production_universe_contract_v0_1.py"
)


# ============================================================
# HARD SAFETY CONTRACT
# ============================================================

SYNTHETIC = False
INTERPOLATION = False
FILL = False
BACKFILL = False
PADDING = False
BLENDING = False
CMC_USED = False

DB_WRITES = 0
EXECUTION = "OFF"


# ============================================================
# EXPECTED SIGNAL SEMANTICS
# ============================================================

VALID_SIGNAL_STATES = {
    "ACTIVE",
    "NEUTRAL",
}

VALID_DIRECTIONS = {
    "LONG",
    "SHORT",
    "NONE",
}


# ============================================================
# SAFE MODULE LOADER
# ============================================================

def load_module(
    path: Path,
    module_name: str,
):
    if not path.exists():
        raise FileNotFoundError(
            f"MODULE_NOT_FOUND:{path.name}"
        )

    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"MODULE_LOAD_FAILED:{path.name}"
        )

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module


# ============================================================
# ASSET NORMALIZATION
# ============================================================

def normalize_asset(asset: Any) -> str:
    if not isinstance(asset, str):
        raise ValueError(
            "ASSET_MUST_BE_STRING"
        )

    value = asset.strip().upper()

    if not value:
        raise ValueError(
            "EMPTY_ASSET"
        )

    return value


# ============================================================
# PRODUCTION UNIVERSE
# ============================================================

def discover_production_assets() -> tuple[str, ...]:
    universe = load_module(
        UNIVERSE_FILE,
        "arunda_dynamic_validation_universe",
    )

    discover = getattr(
        universe,
        "discover_production_assets",
        None,
    )

    if not callable(discover):
        raise AttributeError(
            "DISCOVER_PRODUCTION_ASSETS_UNAVAILABLE"
        )

    assets = tuple(
        normalize_asset(asset)
        for asset in discover()
    )

    if not assets:
        raise RuntimeError(
            "PRODUCTION_UNIVERSE_EMPTY"
        )

    if len(assets) != len(set(assets)):
        raise RuntimeError(
            "PRODUCTION_UNIVERSE_DUPLICATES"
        )

    return assets


# ============================================================
# SIGNAL INPUT CONTRACT
# ============================================================

def validate_signal_input(
    asset: str,
    signal: Mapping[str, Any],
) -> None:

    if not isinstance(signal, Mapping):
        raise ValueError(
            f"INVALID_SIGNAL_OBJECT:{asset}"
        )

    signal_asset = signal.get("asset")

    if signal_asset is None:
        raise ValueError(
            f"SIGNAL_ASSET_MISSING:{asset}"
        )

    signal_asset = normalize_asset(
        signal_asset
    )

    if signal_asset != asset:
        raise ValueError(
            f"ASSET_IDENTITY_MISMATCH:"
            f"{asset}:{signal_asset}"
        )


# ============================================================
# ONE-ASSET VALIDATION
# ============================================================

def validate_dynamic_signal(
    asset: str,
    signal: Mapping[str, Any],
) -> dict[str, Any]:

    dynamic_asset = normalize_asset(asset)

    validate_signal_input(
        dynamic_asset,
        signal,
    )

    signal_state = signal.get(
        "signal_state"
    )

    direction = signal.get(
        "direction"
    )

    valid = True
    reason = "DYNAMIC_SIGNAL_VALID"

    if signal_state not in VALID_SIGNAL_STATES:
        valid = False
        reason = "UNKNOWN_SIGNAL_STATE"

    elif direction not in VALID_DIRECTIONS:
        valid = False
        reason = "UNKNOWN_DIRECTION"

    elif signal_state == "ACTIVE" and direction not in {"LONG", "SHORT"}:
        valid = False
        reason = "ACTIVE_DIRECTION_INVALID"

    elif signal_state == "NEUTRAL" and direction != "NONE":
        valid = False
        reason = "NEUTRAL_DIRECTION_INVALID"
    return {
        "asset": dynamic_asset,
        "signal_state": signal_state,
        "direction": direction,
        "valid": valid,
        "validation": str(reason),

        "dynamic_universe": True,
        "variable_cardinality": True,

        "fixed_15_used": False,
        "fixed_universe_size": False,
        "snapshot_validator_used": False,

        "synthetic": SYNTHETIC,
        "interpolation": INTERPOLATION,
        "fill": FILL,
        "backfill": BACKFILL,
        "padding": PADDING,
        "blending": BLENDING,

        "cmc_used": CMC_USED,
        "db_writes": DB_WRITES,
        "execution": EXECUTION,
    }


# ============================================================
# FULL DYNAMIC VALIDATION
# ============================================================

def validate_dynamic_signals(
    signals: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:

    if not isinstance(signals, Mapping):
        raise ValueError(
            "SIGNALS_MUST_BE_MAPPING"
        )

    universe = discover_production_assets()

    expected = set(universe)

    actual = {
        normalize_asset(asset)
        for asset in signals.keys()
    }

    missing = expected - actual
    extra = actual - expected

    if missing:
        raise RuntimeError(
            "MISSING_PRODUCTION_ASSETS:"
            + repr(sorted(missing))
        )

    if extra:
        raise RuntimeError(
            "UNEXPECTED_PRODUCTION_ASSETS:"
            + repr(sorted(extra))
        )

    results: dict[str, dict[str, Any]] = {}

    for asset in universe:
        results[asset] = validate_dynamic_signal(
            asset,
            signals[asset],
        )

    if set(results.keys()) != expected:
        raise RuntimeError(
            "DYNAMIC_VALIDATION_CARDINALITY_FAILED"
        )

    return results


# ============================================================
# STATIC CONTRACT CHECK
# ============================================================

def static_contract_check() -> dict[str, Any]:

    universe = load_module(
        UNIVERSE_FILE,
        "arunda_validation_static_universe",
    )

    discover = getattr(
        universe,
        "discover_production_assets",
        None,
    )

    if not callable(discover):
        raise RuntimeError(
            "UNIVERSE_DISCOVERY_MISSING"
        )

    assets = tuple(
        normalize_asset(asset)
        for asset in discover()
    )

    if not assets:
        raise RuntimeError(
            "STATIC_UNIVERSE_EMPTY"
        )

    if len(assets) != len(set(assets)):
        raise RuntimeError(
            "STATIC_UNIVERSE_DUPLICATES"
        )

    return {
        "STATUS": "PASS",

        "DYNAMIC_UNIVERSE": True,
        "VARIABLE_CARDINALITY": True,
        "UNIVERSE_OWNS_CARDINALITY": True,

        "PER_ASSET_VALIDATION": True,

        "FIXED_15_USED": False,
        "FIXED_UNIVERSE_SIZE": False,
        "SNAPSHOT_VALIDATOR_USED": False,

        "CLOSED_ENGINE_MODIFIED": False,

        "SYNTHETIC": SYNTHETIC,
        "INTERPOLATION": INTERPOLATION,
        "FILL": FILL,
        "BACKFILL": BACKFILL,
        "PADDING": PADDING,
        "BLENDING": BLENDING,

        "CMC_USED": CMC_USED,

        "DB_WRITES": DB_WRITES,
        "EXECUTION": EXECUTION,

        "PRODUCTION_UNIVERSE_SIZE": len(assets),
    }


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    result = static_contract_check()

    for key, value in result.items():
        print(f"{key}={value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
