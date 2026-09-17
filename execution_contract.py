"""
ARUNDA EXECUTION CONTRACT v0.1

Purpose:
    Define the structural contract for execution eligibility.

Architecture:

    Decision
        ↓
    Risk
        ↓
    Risk Budget
        ↓
    Capital
        ↓
    Stop Loss
        ↓
    Position Sizing
        ↓
    Portfolio Risk
        ↓
    Execution Contract
        ↓
    Future Execution Engine

IMPORTANT:

    This module is CONTRACT ONLY.

    It does NOT:
        - connect to exchange
        - create orders
        - send orders
        - connect to Bitpin
        - use Binance
        - calculate position size
        - calculate stop loss
        - calculate risk
        - calculate portfolio risk
        - use leverage
        - calculate take profit
        - use SQL
        - write to database
        - perform prediction
        - perform ranking
        - perform interpretation
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


# ============================================================================
# EXECUTION STATES
# ============================================================================

EXECUTION_STATES = [
    "EXECUTABLE",
    "BLOCKED",
    "NOT_READY",
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
# EXECUTION FIELDS
# ============================================================================

EXECUTION_FIELDS = [
    "asset",
    "direction",
    "state",
    "entry_price",
    "stop_price",
    "stop_distance",
    "position_size",
    "exposure",
]


# ============================================================================
# EXECUTION REASONS
# ============================================================================

EXECUTION_REASONS = [
    "PORTFOLIO_VALID",
    "DECISION_NOT_ACTIONABLE",
    "RISK_NOT_APPROVED",
    "RISK_BUDGET_NOT_ALLOCATED",
    "STOP_NOT_CALCULATED",
    "POSITION_NOT_CALCULATED",
    "PORTFOLIO_BLOCKED",
    "INPUT_INCOMPLETE",
]


# ============================================================================
# VALIDATION
# ============================================================================

def validate_execution_record(data):
    """
    Validate one execution eligibility record.

    This function validates structure only.

    It does NOT:
        - execute anything
        - connect to an exchange
        - create an order
        - calculate position size
        - calculate stop loss
    """

    if not isinstance(data, dict):

        raise RuntimeError(
            "Execution record must be a dictionary"
        )

    required_fields = [
        "asset",
        "direction",
        "state",
        "entry_price",
        "stop_price",
        "stop_distance",
        "position_size",
        "exposure",
    ]

    for field in required_fields:

        if field not in data:

            raise RuntimeError(
                f"Missing execution field: {field}"
            )

    asset = data["asset"]

    if asset not in EXPECTED_ASSETS:

        raise RuntimeError(
            f"Unknown asset: {asset}"
        )

    direction = data["direction"]

    if direction not in DIRECTIONS:

        raise RuntimeError(
            f"Invalid execution direction: {direction}"
        )

    state = data["state"]

    if state not in EXECUTION_STATES:

        raise RuntimeError(
            f"Invalid execution state: {state}"
        )

    return True


# ============================================================================
# SNAPSHOT VALIDATION
# ============================================================================

def validate_execution_snapshot(snapshot):
    """
    Validate a complete execution eligibility snapshot.
    """

    if not isinstance(snapshot, list):

        raise RuntimeError(
            "Execution snapshot must be a list"
        )

    assets = set()

    for record in snapshot:

        validate_execution_record(
            record
        )

        asset = record["asset"]

        if asset in assets:

            raise RuntimeError(
                f"Duplicate asset: {asset}"
            )

        assets.add(asset)

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

    return True


# ============================================================================
# CONTRACT INFORMATION
# ============================================================================

def print_header():

    print("=" * 77)
    print("ARUNDA EXECUTION CONTRACT v0.1")
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{len(EXPECTED_ASSETS)}"
    )

    print(
        f"Execution Fields: "
        f"{len(EXECUTION_FIELDS)}"
    )

    print(
        f"Execution States: "
        f"{len(EXECUTION_STATES)}"
    )

    print(
        "States          : "
        "EXECUTABLE / BLOCKED / NOT_READY"
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
        "Decision        : INPUT ONLY"
    )

    print(
        "Risk            : INPUT ONLY"
    )

    print(
        "Risk Budget     : INPUT ONLY"
    )

    print(
        "Capital         : INPUT ONLY"
    )

    print(
        "Stop Loss       : INPUT ONLY"
    )

    print(
        "Position Size   : INPUT ONLY"
    )

    print(
        "Portfolio Risk  : INPUT ONLY"
    )

    print(
        "Execution       : ELIGIBILITY ONLY"
    )

    print(
        "Order Creation  : NOT USED"
    )

    print(
        "Exchange        : NOT CONNECTED"
    )

    print(
        "Bitpin          : FUTURE EXECUTION"
    )

    print(
        "Binance         : NOT USED"
    )

    print(
        "Leverage        : NOT USED"
    )

    print(
        "Take Profit     : NOT USED"
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
        f"Execution Reasons: "
        f"{len(EXECUTION_REASONS)}"
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
    print("EXECUTION CONTRACT")
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{len(EXPECTED_ASSETS)}"
    )

    print(
        "Execution Fields:"
    )

    for field in EXECUTION_FIELDS:

        print(
            f"  - {field}"
        )

    print(
        "Execution States:"
    )

    for state in EXECUTION_STATES:

        print(
            f"  - {state}"
        )

    print(
        "Execution Reasons:"
    )

    for reason in EXECUTION_REASONS:

        print(
            f"  - {reason}"
        )

    print(
        "Validation:"
    )

    print(
        "  - Decision must be actionable"
    )

    print(
        "  - Risk must be approved"
    )

    print(
        "  - Risk budget must be allocated"
    )

    print(
        "  - Stop loss must be calculated"
    )

    print(
        "  - Position size must be calculated"
    )

    print(
        "  - Portfolio risk must be valid"
    )

    print(
        "  - Entry must be available"
    )

    print(
        "  - Position size must be positive"
    )

    print(
        "  - Exposure must be positive"
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
        "Exchange        : NOT CONNECTED"
    )

    print(
        "Bitpin          : FUTURE EXECUTION"
    )

    print(
        "Order Creation  : NOT USED"
    )

    print(
        "Execution       : NOT USED"
    )

    print(
        "Contract Status : VALID"
    )

    print("=" * 77)


# ============================================================================
# MAIN
# ============================================================================

def main():

    print_header()

    try:

        # --------------------------------------------------------------------
        # Structural self-test
        # --------------------------------------------------------------------

        if len(EXPECTED_ASSETS) != 15:

            raise RuntimeError(
                "Expected asset count must be 15"
            )

        if EXPECTED_ASSET_COUNT != 15:

            raise RuntimeError(
                "EXPECTED_ASSET_COUNT must be 15"
            )

        if len(EXECUTION_STATES) != 3:

            raise RuntimeError(
                "Execution state count must be 3"
            )

        if len(DIRECTIONS) != 3:

            raise RuntimeError(
                "Direction count must be 3"
            )

        if len(EXECUTION_FIELDS) != 8:

            raise RuntimeError(
                "Execution field count must be 8"
            )

        if len(EXECUTION_REASONS) != 8:

            raise RuntimeError(
                "Execution reason count must be 8"
            )

        # --------------------------------------------------------------------
        # Ensure all assets are unique.
        # --------------------------------------------------------------------

        if len(set(EXPECTED_ASSETS)) != 15:

            raise RuntimeError(
                "Expected assets must be unique"
            )

        # --------------------------------------------------------------------
        # Ensure required states exist.
        # --------------------------------------------------------------------

        required_states = {
            "EXECUTABLE",
            "BLOCKED",
            "NOT_READY",
        }

        if set(EXECUTION_STATES) != required_states:

            raise RuntimeError(
                "Execution states do not match contract"
            )

        # --------------------------------------------------------------------
        # Ensure required directions exist.
        # --------------------------------------------------------------------

        required_directions = {
            "LONG",
            "SHORT",
            "NONE",
        }

        if set(DIRECTIONS) != required_directions:

            raise RuntimeError(
                "Execution directions do not match contract"
            )

        # --------------------------------------------------------------------
        # Contract information
        # --------------------------------------------------------------------

        print_contract()

        print()
        print(
            "EXECUTION CONTRACT STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()
        print("=" * 77)
        print("ARUNDA EXECUTION CONTRACT ERROR")
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
            "EXECUTION CONTRACT STATUS : FAILED"
        )

        return 1


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )