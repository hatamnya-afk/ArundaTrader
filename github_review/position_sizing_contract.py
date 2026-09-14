"""
ARUNDA POSITION SIZING CONTRACT v0.2

Purpose:
    Define the formal contract for Position Sizing.

Architecture:

    Validated Signal
           ↓
    Market State
           ↓
    Feature Snapshot
           ↓
    Stop Loss
           ↓
    Risk Budget
           ↓
    Position Sizing Contract
           ↓
    Position Sizing Engine

Rules:
    - CONTRACT ONLY
    - VALIDATION ONLY
    - MEMORY ONLY
    - NO SQL
    - NO DATABASE WRITES
    - NO POSITION CALCULATION
    - NO ORDER EXECUTION
    - NO STOP LOSS CALCULATION
    - NO TAKE PROFIT
    - NO LEVERAGE
    - NO PREDICTION
    - NO RANKING
    - NO INTERPRETATION

Position Sizing Engine owns:
    - Risk Amount
    - Position Size
    - Exposure

This contract owns:
    - Structure
    - Allowed fields
    - Allowed directions
    - Allowed states
    - Snapshot integrity
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


# ============================================================================
# POSITION SIZING FIELDS
# ============================================================================

POSITION_SIZING_FIELDS = [
    "asset",
    "direction",
    "state",
    "risk_budget",
    "entry_price",
    "stop_distance",
    "position_size",
    "exposure",
]


# ============================================================================
# DIRECTIONS
# ============================================================================

DIRECTIONS = [
    "LONG",
    "SHORT",
    "NONE",
]


# ============================================================================
# STATES
# ============================================================================

SIZING_STATES = [
    "CALCULATED",
    "UNCALCULATED",
    "BLOCKED",
]


# ============================================================================
# VALIDATE ONE POSITION RECORD
# ============================================================================

def validate_position_sizing(data):
    """
    Validate one Position Sizing record.

    This function validates structure and allowed values only.

    It does NOT:
        - calculate position size
        - calculate exposure
        - calculate risk
        - calculate stop loss
        - modify data
    """

    # ------------------------------------------------------------------------
    # TYPE
    # ------------------------------------------------------------------------

    if not isinstance(
        data,
        dict,
    ):

        raise RuntimeError(
            "Position sizing record must be a dictionary"
        )

    # ------------------------------------------------------------------------
    # REQUIRED FIELDS
    # ------------------------------------------------------------------------

    for field in POSITION_SIZING_FIELDS:

        if field not in data:

            raise RuntimeError(
                "Missing position sizing field: "
                f"{field}"
            )

    # ------------------------------------------------------------------------
    # ASSET
    # ------------------------------------------------------------------------

    asset = data["asset"]

    if asset not in EXPECTED_ASSETS:

        raise RuntimeError(
            f"Unknown asset: {asset}"
        )

    # ------------------------------------------------------------------------
    # DIRECTION
    # ------------------------------------------------------------------------

    direction = data["direction"]

    if direction not in DIRECTIONS:

        raise RuntimeError(
            f"Invalid direction: {direction}"
        )

    # ------------------------------------------------------------------------
    # STATE
    # ------------------------------------------------------------------------

    state = data["state"]

    if state not in SIZING_STATES:

        raise RuntimeError(
            f"Invalid position sizing state: {state}"
        )

    # ------------------------------------------------------------------------
    # STATE / DIRECTION CONSISTENCY
    # ------------------------------------------------------------------------

    if state == "UNCALCULATED":

        if direction != "NONE":

            raise RuntimeError(
                "UNCALCULATED position must have "
                "direction NONE"
            )

    # ------------------------------------------------------------------------
    # NONE DIRECTION
    # ------------------------------------------------------------------------

    if direction == "NONE":

        if state != "UNCALCULATED":

            raise RuntimeError(
                "NONE direction must have "
                "state UNCALCULATED"
            )

    # ------------------------------------------------------------------------
    # CALCULATED
    # ------------------------------------------------------------------------

    if state == "CALCULATED":

        if direction not in (
            "LONG",
            "SHORT",
        ):

            raise RuntimeError(
                "CALCULATED position must have "
                "LONG or SHORT direction"
            )

    # ------------------------------------------------------------------------
    # BLOCKED
    # ------------------------------------------------------------------------

    if state == "BLOCKED":

        if direction == "NONE":

            raise RuntimeError(
                "BLOCKED position must have "
                "LONG or SHORT direction"
            )

    # ------------------------------------------------------------------------
    # RETURN
    # ------------------------------------------------------------------------

    return True


# ============================================================================
# VALIDATE COMPLETE SNAPSHOT
# ============================================================================

def validate_snapshot(snapshot):
    """
    Validate a complete Position Sizing snapshot.

    Requirements:

        - snapshot must be a list
        - every record must be valid
        - every expected asset must appear exactly once
    """

    # ------------------------------------------------------------------------
    # TYPE
    # ------------------------------------------------------------------------

    if not isinstance(
        snapshot,
        list,
    ):

        raise RuntimeError(
            "Position sizing snapshot must be a list"
        )

    # ------------------------------------------------------------------------
    # ASSET INDEX
    # ------------------------------------------------------------------------

    assets = set()

    for record in snapshot:

        validate_position_sizing(
            record
        )

        asset = record["asset"]

        if asset in assets:

            raise RuntimeError(
                f"Duplicate asset: {asset}"
            )

        assets.add(
            asset
        )

    # ------------------------------------------------------------------------
    # MISSING ASSETS
    # ------------------------------------------------------------------------

    missing = [
        asset
        for asset in EXPECTED_ASSETS
        if asset not in assets
    ]

    if missing:

        raise RuntimeError(
            "Missing assets: "
            + ", ".join(missing)
        )

    # ------------------------------------------------------------------------
    # EXTRA ASSETS
    # ------------------------------------------------------------------------

    extra = [
        asset
        for asset in assets
        if asset not in EXPECTED_ASSETS
    ]

    if extra:

        raise RuntimeError(
            "Unexpected assets: "
            + ", ".join(extra)
        )

    # ------------------------------------------------------------------------
    # RETURN
    # ------------------------------------------------------------------------

    return True


# ============================================================================
# CONTRACT HEADER
# ============================================================================

def print_header():

    print("=" * 77)
    print(
        "ARUNDA POSITION SIZING CONTRACT v0.2"
    )
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{len(EXPECTED_ASSETS)}"
    )

    print(
        f"Sizing Fields   : "
        f"{len(POSITION_SIZING_FIELDS)}"
    )

    print(
        f"Sizing States   : "
        f"{len(SIZING_STATES)}"
    )

    print(
        f"Directions      : "
        f"{len(DIRECTIONS)}"
    )

    print(
        "States          : "
        "CALCULATED / UNCALCULATED / BLOCKED"
    )

    print(
        "Directions      : "
        "LONG / SHORT / NONE"
    )

    print(
        "Storage         : MEMORY ONLY"
    )

    print(
        "Database writes : NONE"
    )

    print(
        "SQL             : NOT USED"
    )

    print(
        "Capital         : INPUT ONLY"
    )

    print(
        "Risk Budget     : INPUT ONLY"
    )

    print(
        "Entry Price     : INPUT ONLY"
    )

    print(
        "Stop Distance   : INPUT ONLY"
    )

    print(
        "Position Size   : OUTPUT FIELD"
    )

    print(
        "Exposure        : OUTPUT FIELD"
    )

    print(
        "Stop Loss       : NOT USED"
    )

    print(
        "Take Profit     : NOT USED"
    )

    print(
        "Leverage        : NOT USED"
    )

    print(
        "Portfolio Risk  : NOT USED"
    )

    print(
        "Execution       : NOT USED"
    )

    print(
        "Prediction      : NOT USED"
    )

    print(
        "Ranking         : NOT USED"
    )

    print(
        "Interpretation  : NOT USED"
    )

    print(
        "Contract Status : VALID"
    )

    print("=" * 77)


# ============================================================================
# CONTRACT DETAILS
# ============================================================================

def print_contract():

    print()

    print("=" * 77)
    print(
        "POSITION SIZING CONTRACT"
    )
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{len(EXPECTED_ASSETS)}"
    )

    print(
        f"Sizing Fields   : "
        f"{len(POSITION_SIZING_FIELDS)}"
    )

    print(
        "Fields          : "
        "asset / direction / state / "
        "risk_budget / entry_price / "
        "stop_distance / position_size / exposure"
    )

    print(
        f"Sizing States   : "
        f"{len(SIZING_STATES)}"
    )

    print(
        "States          : "
        "CALCULATED / UNCALCULATED / BLOCKED"
    )

    print(
        f"Directions      : "
        f"{len(DIRECTIONS)}"
    )

    print(
        "Directions      : "
        "LONG / SHORT / NONE"
    )

    print(
        "Storage         : MEMORY ONLY"
    )

    print(
        "Database writes : NONE"
    )

    print(
        "SQL             : NOT USED"
    )

    print(
        "Capital         : INPUT ONLY"
    )

    print(
        "Risk Budget     : INPUT ONLY"
    )

    print(
        "Entry Price     : INPUT ONLY"
    )

    print(
        "Stop Distance   : INPUT ONLY"
    )

    print(
        "Position Size   : OUTPUT FIELD"
    )

    print(
        "Exposure        : OUTPUT FIELD"
    )

    print(
        "Stop Loss       : NOT USED"
    )

    print(
        "Take Profit     : NOT USED"
    )

    print(
        "Leverage        : NOT USED"
    )

    print(
        "Portfolio Risk  : NOT USED"
    )

    print(
        "Execution       : NOT USED"
    )

    print(
        "Prediction      : NOT USED"
    )

    print(
        "Ranking         : NOT USED"
    )

    print(
        "Interpretation  : NOT USED"
    )

    print(
        "Contract Status : VALID"
    )

    print("=" * 77)


# ============================================================================
# STRUCTURAL SELF TEST
# ============================================================================

def self_test():

    # ------------------------------------------------------------------------
    # Asset count
    # ------------------------------------------------------------------------

    if len(EXPECTED_ASSETS) != 15:

        raise RuntimeError(
            "Expected asset count must be 15"
        )

    # ------------------------------------------------------------------------
    # Field count
    # ------------------------------------------------------------------------

    if len(POSITION_SIZING_FIELDS) != 8:

        raise RuntimeError(
            "Position sizing field count "
            "must be 8"
        )

    # ------------------------------------------------------------------------
    # State count
    # ------------------------------------------------------------------------

    if len(SIZING_STATES) != 3:

        raise RuntimeError(
            "Position sizing state count "
            "must be 3"
        )

    # ------------------------------------------------------------------------
    # Direction count
    # ------------------------------------------------------------------------

    if len(DIRECTIONS) != 3:

        raise RuntimeError(
            "Direction count must be 3"
        )

    # ------------------------------------------------------------------------
    # Required fields
    # ------------------------------------------------------------------------

    expected_fields = [
        "asset",
        "direction",
        "state",
        "risk_budget",
        "entry_price",
        "stop_distance",
        "position_size",
        "exposure",
    ]

    if POSITION_SIZING_FIELDS != expected_fields:

        raise RuntimeError(
            "Position sizing field definition "
            "does not match Engine v0.3"
        )

    # ------------------------------------------------------------------------
    # Required states
    # ------------------------------------------------------------------------

    expected_states = [
        "CALCULATED",
        "UNCALCULATED",
        "BLOCKED",
    ]

    if SIZING_STATES != expected_states:

        raise RuntimeError(
            "Position sizing states do not "
            "match Engine v0.3"
        )

    # ------------------------------------------------------------------------
    # Required directions
    # ------------------------------------------------------------------------

    expected_directions = [
        "LONG",
        "SHORT",
        "NONE",
    ]

    if DIRECTIONS != expected_directions:

        raise RuntimeError(
            "Position sizing directions do not "
            "match Engine v0.3"
        )

    return True


# ============================================================================
# MAIN
# ============================================================================

def main():

    print_header()

    try:

        # --------------------------------------------------------------------
        # Structural self-test
        # --------------------------------------------------------------------

        self_test()

        # --------------------------------------------------------------------
        # Print contract
        # --------------------------------------------------------------------

        print_contract()

        # --------------------------------------------------------------------
        # Status
        # --------------------------------------------------------------------

        print()

        print(
            "POSITION SIZING CONTRACT STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()

        print("=" * 77)
        print(
            "POSITION SIZING CONTRACT ERROR"
        )
        print("=" * 77)

        print(
            f"Type  : "
            f"{type(exc).__name__}"
        )

        print(
            f"Error : "
            f"{exc}"
        )

        print()

        print(
            "POSITION SIZING CONTRACT STATUS : FAILED"
        )

        return 1


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )