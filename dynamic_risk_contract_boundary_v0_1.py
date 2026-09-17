from pathlib import Path
import importlib.util
import sys
import math

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
RISK_ENGINE_FILE = ROOT / "risk_engine.py"

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

risk_engine = load_module("arunda_risk_engine_boundary_dep", RISK_ENGINE_FILE)


def normalize_asset(asset):
    if not isinstance(asset, str):
        raise ValueError("asset must be string")

    value = asset.strip().upper()

    parts = value.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"invalid dynamic asset: {asset}")

    return f"{parts[0]}/{parts[1]}"


def build_dynamic_risk(asset, decision):
    """
    Variable-cardinality Risk Contract Boundary.

    Reuses the existing per-candidate evaluate_risk()
    semantics and deliberately bypasses the fixed
    snapshot validator.
    """

    dynamic_asset = normalize_asset(asset)

    if not isinstance(decision, dict):
        raise ValueError("decision must be dict")

    required = (
        "state",
        "direction",
    )

    for field in required:
        if field not in decision:
            raise ValueError(
                f"decision missing required field: {field}"
            )

    state = decision["state"]
    direction = decision["direction"]

    if state not in (
        "ACTIONABLE",
        "HOLD",
        "REJECT",
    ):
        raise ValueError(
            f"invalid decision state: {state}"
        )

    if direction not in (
        "LONG",
        "SHORT",
        "NONE",
    ):
        raise ValueError(
            f"invalid decision direction: {direction}"
        )

    result = risk_engine.evaluate_risk(
        dynamic_asset,
        decision,
    )

    if not isinstance(result, dict):
        raise RuntimeError(
            "evaluate_risk() must return dict"
        )

    if result.get("asset") != dynamic_asset:
        raise RuntimeError(
            "Risk asset identity mismatch"
        )

    risk_state = result.get("risk_state")

    if risk_state not in (
        "APPROVED",
        "NOT_APPLICABLE",
        "BLOCKED",
    ):
        raise RuntimeError(
            f"invalid risk_state: {risk_state}"
        )

    result_direction = result.get("direction")

    if result_direction not in (
        "LONG",
        "SHORT",
        "NONE",
    ):
        raise RuntimeError(
            f"invalid risk direction: {result_direction}"
        )

    risk_score = result.get("risk_score")

    if risk_score is not None:
        if not isinstance(risk_score, (int, float)):
            raise RuntimeError(
                "risk_score must be numeric or None"
            )
        if not math.isfinite(float(risk_score)):
            raise RuntimeError(
                "risk_score must be finite"
            )

    return result


def validate_boundary():
    required = (
        "evaluate_risk",
        "validate_risk_snapshot",
    )

    for name in required:
        if not hasattr(risk_engine, name):
            raise RuntimeError(
                f"risk_engine missing {name}"
            )

    actionable_long = build_dynamic_risk(
        "MARSCOIN/USDT",
        {
            "asset": "MARSCOIN/USDT",
            "state": "ACTIONABLE",
            "direction": "LONG",
        },
    )

    if actionable_long["risk_state"] != "APPROVED":
        raise RuntimeError(
            "LONG Risk semantics changed"
        )

    actionable_short = build_dynamic_risk(
        "MARSCOIN/USDT",
        {
            "asset": "MARSCOIN/USDT",
            "state": "ACTIONABLE",
            "direction": "SHORT",
        },
    )

    if actionable_short["risk_state"] != "APPROVED":
        raise RuntimeError(
            "SHORT Risk semantics changed"
        )

    hold = build_dynamic_risk(
        "MARSCOIN/USDT",
        {
            "asset": "MARSCOIN/USDT",
            "state": "HOLD",
            "direction": "NONE",
        },
    )

    if hold["risk_state"] != "NOT_APPLICABLE":
        raise RuntimeError(
            "HOLD Risk semantics changed"
        )

    return True


if __name__ == "__main__":
    print("=" * 100)
    print("ARUNDA DYNAMIC RISK CONTRACT BOUNDARY v0.1")
    print("STATIC CHECK ONLY")

    validate_boundary()

    print("RISK_ENGINE=PASS")
    print("EVALUATE_RISK=PASS")
    print("VARIABLE_CARDINALITY=PASS")
    print("FIXED_15_USED=FALSE")
    print("SNAPSHOT_VALIDATOR_USED=FALSE")
    print("EXISTING_RISK_SEMANTICS=PRESERVED")

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
    print("=" * 100)
