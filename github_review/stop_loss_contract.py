"""
ARUNDA STOP LOSS CONTRACT v0.1

Purpose:
    Define the formal structure of Stop Loss output.

Architecture:

    Market Data
          ↓
    Feature Snapshot
          ↓
    Stop Loss Engine
          ↓
    Stop Loss Contract
          ↓
    Entry / Stop Contract
          ↓
    Position Sizing

Rules:
    - CONTRACT ONLY
    - VALIDATION ONLY
    - MEMORY ONLY
    - NO SQL
    - NO DATABASE WRITES
    - NO STOP LOSS CALCULATION
    - NO ENTRY CALCULATION
    - NO RISK CALCULATION
    - NO POSITION SIZING
    - NO EXPOSURE
    - NO LEVERAGE
    - NO EXECUTION
    - NO PREDICTION
    - NO RANKING
    - NO INTERPRETATION
"""

# ============================================================================
# CONTRACT CONSTANTS
# ============================================================================

EXPECTED_ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "SHIB",
    "LINK",
    "AVAX",
    "DOT",
    "LTC",
    "UNI",
    "AAVE",
    "SUI",
    "NEAR",
]

EXPECTED_ASSET_COUNT = 15

STOP_STATES = (
    "CALCULATED",
    "UNAVAILABLE",
    "BLOCKED",
)

DIRECTIONS = (
    "LONG",
    "SHORT",
    "NONE",
)

STOP_LOSS_FIELDS = (
    "asset",
    "direction",
    "state",
    "entry_price",
    "stop_price",
    "stop_distance",
)


# ============================================================================
# BUILD EMPTY STOP RECORD
# ============================================================================

def build_empty_stop(asset):

    if asset not in EXPECTED_ASSETS:
        raise ValueError(
            f"Unknown asset: {asset}"
        )

    return {
        "asset": asset,
        "direction": "NONE",
        "state": "UNAVAILABLE",
        "entry_price": None,
        "stop_price": None,
        "stop_distance": None,
    }


# ============================================================================
# VALIDATE ONE STOP RECORD
# ============================================================================

def validate_stop_loss(data):

    if not isinstance(data, dict):

        raise RuntimeError(
            "Stop Loss record must be a dictionary"
        )

    # ------------------------------------------------------------------------
    # REQUIRED FIELDS
    # ------------------------------------------------------------------------

    missing = [
        field
        for field in STOP_LOSS_FIELDS
        if field not in data
    ]

    if missing:

        raise RuntimeError(
            "Missing Stop Loss fields: "
            + ", ".join(missing)
        )

    # ------------------------------------------------------------------------
    # ASSET
    # ------------------------------------------------------------------------

    asset = data["asset"]

    if asset not in EXPECTED_ASSETS:

        raise RuntimeError(
            f"Invalid asset: {asset}"
        )

    # ------------------------------------------------------------------------
    # DIRECTION
    # ------------------------------------------------------------------------

    direction = data["direction"]

    if direction not in DIRECTIONS:

        raise RuntimeError(
            f"Invalid direction for {asset}: "
            f"{direction}"
        )

    # ------------------------------------------------------------------------
    # STATE
    # ------------------------------------------------------------------------

    state = data["state"]

    if state not in STOP_STATES:

        raise RuntimeError(
            f"Invalid Stop Loss state for {asset}: "
            f"{state}"
        )

    # ------------------------------------------------------------------------
    # NUMERIC FIELDS
    # ------------------------------------------------------------------------

    numeric_fields = (
        "entry_price",
        "stop_price",
        "stop_distance",
    )

    for field in numeric_fields:

        value = data[field]

        if value is None:
            continue

        if isinstance(value, bool):

            raise RuntimeError(
                f"Invalid {field} type for {asset}"
            )

        if not isinstance(
            value,
            (int, float),
        ):

            raise RuntimeError(
                f"Invalid {field} for {asset}: "
                f"{value!r}"
            )

        if value < 0:

            raise RuntimeError(
                f"{field} cannot be negative "
                f"for {asset}"
            )

    # ------------------------------------------------------------------------
    # STATE / DIRECTION CONSISTENCY
    # ------------------------------------------------------------------------

    if state == "CALCULATED":

        if direction not in (
            "LONG",
            "SHORT",
        ):

            raise RuntimeError(
                "CALCULATED Stop Loss must have "
                "LONG or SHORT direction"
            )

        if data["entry_price"] is None:

            raise RuntimeError(
                "CALCULATED Stop Loss requires "
                "entry_price"
            )

        if data["stop_price"] is None:

            raise RuntimeError(
                "CALCULATED Stop Loss requires "
                "stop_price"
            )

        if data["stop_distance"] is None:

            raise RuntimeError(
                "CALCULATED Stop Loss requires "
                "stop_distance"
            )

    # ------------------------------------------------------------------------
    # UNAVAILABLE
    # ------------------------------------------------------------------------

    if state == "UNAVAILABLE":

        if direction != "NONE":

            raise RuntimeError(
                "UNAVAILABLE Stop Loss must have "
                "direction NONE"
            )

    # ------------------------------------------------------------------------
    # BLOCKED
    # ------------------------------------------------------------------------

    if state == "BLOCKED":

        if direction == "NONE":

            raise RuntimeError(
                "BLOCKED Stop Loss must have "
                "LONG or SHORT direction"
            )

    # ------------------------------------------------------------------------
    # NONE DIRECTION
    # ------------------------------------------------------------------------

    if direction == "NONE":

        if state != "UNAVAILABLE":

            raise RuntimeError(
                "NONE direction must have "
                "state UNAVAILABLE"
            )

    return True


# ============================================================================
# VALIDATE COMPLETE SNAPSHOT
# ============================================================================

def validate_stop_loss_snapshot(snapshot):

    if not isinstance(snapshot, dict):

        raise RuntimeError(
            "Stop Loss snapshot must be a dictionary"
        )

    expected = set(EXPECTED_ASSETS)
    actual = set(snapshot.keys())

    missing = expected - actual
    extra = actual - expected

    if missing:

        raise RuntimeError(
            "Missing assets: "
            + ", ".join(sorted(missing))
        )

    if extra:

        raise RuntimeError(
            "Unexpected assets: "
            + ", ".join(sorted(extra))
        )

    for asset in EXPECTED_ASSETS:

        validate_stop_loss(
            snapshot[asset]
        )

    calculated = sum(
        1
        for asset in EXPECTED_ASSETS
        if snapshot[asset]["state"]
        == "CALCULATED"
    )

    unavailable = sum(
        1
        for asset in EXPECTED_ASSETS
        if snapshot[asset]["state"]
        == "UNAVAILABLE"
    )

    blocked = sum(
        1
        for asset in EXPECTED_ASSETS
        if snapshot[asset]["state"]
        == "BLOCKED"
    )

    return {
        "expected_assets": EXPECTED_ASSET_COUNT,
        "validated_assets": len(snapshot),
        "calculated": calculated,
        "unavailable": unavailable,
        "blocked": blocked,
        "contract_status": "VALID",
    }


# ============================================================================
# HEADER
# ============================================================================

def print_header():

    print("=" * 77)
    print("ARUNDA STOP LOSS CONTRACT v0.1")
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{EXPECTED_ASSET_COUNT}"
    )

    print(
        f"Fields          : "
        f"{len(STOP_LOSS_FIELDS)}"
    )

    print(
        "Fields          : "
        "asset / direction / state / "
        "entry_price / stop_price / stop_distance"
    )

    print(
        "States          : "
        + " / ".join(STOP_STATES)
    )

    print(
        "Directions      : "
        + " / ".join(DIRECTIONS)
    )

    print("Storage         : MEMORY ONLY")
    print("Database writes : NONE")
    print("SQL             : NOT USED")
    print("Entry           : INPUT / REFERENCE ONLY")
    print("Stop Price      : OUTPUT FIELD")
    print("Stop Distance   : OUTPUT FIELD")
    print("Risk Calculation: NOT USED")
    print("Position Sizing : NOT USED")
    print("Exposure        : NOT USED")
    print("Execution       : NOT USED")
    print("Prediction      : NOT USED")
    print("Ranking         : NOT USED")
    print("Interpretation  : NOT USED")
    print("Contract Status : VALID")

    print("=" * 77)


# ============================================================================
# CONTRACT DETAILS
# ============================================================================

def print_contract():

    print()
    print("=" * 77)
    print("STOP LOSS CONTRACT")
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{EXPECTED_ASSET_COUNT}"
    )

    print(
        f"Fields          : "
        f"{len(STOP_LOSS_FIELDS)}"
    )

    print(
        "States          : "
        + " / ".join(STOP_STATES)
    )

    print(
        "Directions      : "
        + " / ".join(DIRECTIONS)
    )

    print("Storage         : MEMORY ONLY")
    print("Database writes : NONE")
    print("SQL             : NOT USED")
    print("Entry           : INPUT / REFERENCE ONLY")
    print("Stop Price      : OUTPUT FIELD")
    print("Stop Distance   : OUTPUT FIELD")
    print("Risk Budget     : NOT USED")
    print("Position Sizing : NOT USED")
    print("Exposure        : NOT USED")
    print("Execution       : NOT USED")
    print("Contract Status : VALID")

    print("=" * 77)


# ============================================================================
# STRUCTURAL SELF TEST
# ============================================================================

def self_test():

    if len(EXPECTED_ASSETS) != 15:

        raise RuntimeError(
            "Expected asset count must be 15"
        )

    if len(STOP_LOSS_FIELDS) != 6:

        raise RuntimeError(
            "Stop Loss field count must be 6"
        )

    expected_fields = (
        "asset",
        "direction",
        "state",
        "entry_price",
        "stop_price",
        "stop_distance",
    )

    if STOP_LOSS_FIELDS != expected_fields:

        raise RuntimeError(
            "Stop Loss field definition mismatch"
        )

    expected_states = (
        "CALCULATED",
        "UNAVAILABLE",
        "BLOCKED",
    )

    if STOP_STATES != expected_states:

        raise RuntimeError(
            "Stop Loss state definition mismatch"
        )

    expected_directions = (
        "LONG",
        "SHORT",
        "NONE",
    )

    if DIRECTIONS != expected_directions:

        raise RuntimeError(
            "Stop Loss direction definition mismatch"
        )

    # ------------------------------------------------------------------------
    # Test one empty record
    # ------------------------------------------------------------------------

    record = build_empty_stop("BTC")

    validate_stop_loss(record)

    # ------------------------------------------------------------------------
    # Test one calculated LONG record
    # ------------------------------------------------------------------------

    calculated_long = {
        "asset": "BTC",
        "direction": "LONG",
        "state": "CALCULATED",
        "entry_price": 100000.0,
        "stop_price": 98000.0,
        "stop_distance": 2000.0,
    }

    validate_stop_loss(
        calculated_long
    )

    # ------------------------------------------------------------------------
    # Test one calculated SHORT record
    # ------------------------------------------------------------------------

    calculated_short = {
        "asset": "NEAR",
        "direction": "SHORT",
        "state": "CALCULATED",
        "entry_price": 5.0,
        "stop_price": 5.2,
        "stop_distance": 0.2,
    }

    validate_stop_loss(
        calculated_short
    )

    # ------------------------------------------------------------------------
    # Test complete empty snapshot
    # ------------------------------------------------------------------------

    snapshot = {
        asset: build_empty_stop(asset)
        for asset in EXPECTED_ASSETS
    }

    result = validate_stop_loss_snapshot(
        snapshot
    )

    if result["contract_status"] != "VALID":

        raise RuntimeError(
            "Complete Stop Loss snapshot "
            "validation failed"
        )

    return True


# ============================================================================
# MAIN
# ============================================================================

def main():

    print_header()

    try:

        self_test()

        print_contract()

        print()
        print(
            "STOP LOSS CONTRACT STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()
        print("=" * 77)
        print("STOP LOSS CONTRACT ERROR")
        print("=" * 77)

        print(
            f"Type   : "
            f"{type(exc).__name__}"
        )

        print(
            f"Error  : "
            f"{exc}"
        )

        print()
        print(
            "STOP LOSS CONTRACT STATUS : FAILED"
        )

        return 1


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
