"""Arunda Position Sizing Contract v0.2 compatibility boundary.

Contract-only validation. No calculation, persistence, execution, leverage, or
stop-loss logic.
"""

EXPECTED_ASSETS = [
    "BTC","ETH","SOL","XRP","ADA","DOGE","SHIB","LINK","AVAX","DOT",
    "LTC","UNI","AAVE","SUI","NEAR",
]
POSITION_SIZING_FIELDS = [
    "asset","direction","state","risk_budget",
    "entry_price","stop_distance","position_size","exposure",
]
DIRECTIONS = ["LONG","SHORT","NONE"]
SIZING_STATES = ["CALCULATED","UNCALCULATED","BLOCKED"]

def validate_position_sizing(data):
    if not isinstance(data, dict):
        raise RuntimeError("Position sizing record must be a dictionary")
    for field in POSITION_SIZING_FIELDS:
        if field not in data:
            raise RuntimeError(f"Missing position sizing field: {field}")
    if data["asset"] not in EXPECTED_ASSETS:
        raise RuntimeError(f"Unknown asset: {data['asset']}")
    if data["direction"] not in DIRECTIONS:
        raise RuntimeError(f"Invalid direction: {data['direction']}")
    if data["state"] not in SIZING_STATES:
        raise RuntimeError(f"Invalid position sizing state: {data['state']}")
    if data["state"] == "UNCALCULATED" and data["direction"] != "NONE":
        raise RuntimeError("UNCALCULATED position must have direction NONE")
    if data["direction"] == "NONE" and data["state"] != "UNCALCULATED":
        raise RuntimeError("NONE direction must have state UNCALCULATED")
    if data["state"] == "CALCULATED" and data["direction"] not in ("LONG","SHORT"):
        raise RuntimeError("CALCULATED position must have LONG or SHORT direction")
    if data["state"] == "BLOCKED" and data["direction"] == "NONE":
        raise RuntimeError("BLOCKED position must have LONG or SHORT direction")
    return True

def validate_snapshot(snapshot):
    if not isinstance(snapshot, list):
        raise RuntimeError("Position sizing snapshot must be a list")
    assets=set()
    for record in snapshot:
        validate_position_sizing(record)
        asset=record["asset"]
        if asset in assets:
            raise RuntimeError(f"Duplicate asset: {asset}")
        assets.add(asset)
    missing=[a for a in EXPECTED_ASSETS if a not in assets]
    if missing:
        raise RuntimeError("Missing assets: "+", ".join(missing))
    extra=[a for a in assets if a not in EXPECTED_ASSETS]
    if extra:
        raise RuntimeError("Unexpected assets: "+", ".join(extra))
    return True
