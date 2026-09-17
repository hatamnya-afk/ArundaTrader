"""
ARUNDA PORTFOLIO RISK CONTRACT v0.2

Purpose:
    Define the formal contract for validating portfolio-level
    risk, exposure, capital utilization and concurrent positions.

Architecture:

    Risk Budget
         ↓
    Capital
         ↓
    Stop Loss
         ↓
    Position Sizing
         ↓
    Portfolio Risk Contract
         ↓
    Future Portfolio Risk Engine
         ↓
    Future Execution

Rules:
    - CONTRACT ONLY
    - VALIDATION ONLY
    - MEMORY ONLY
    - NO SQL
    - NO DATABASE WRITES
    - NO EXCHANGE CONNECTION
    - NO ORDER EXECUTION
    - NO POSITION CALCULATION
    - NO STOP LOSS CALCULATION
    - NO TAKE PROFIT
    - NO LEVERAGE
    - NO PREDICTION
    - NO RANKING
    - NO INTERPRETATION

Capital Utilization Model:
    MAXIMUM VALID UTILIZATION

Meaning:
    The system may use as much valid available capital as the
    upstream risk constraints allow.

Important:
    Unused capital is allowed.
    Forced exposure is forbidden.

Therefore:

    "Use capital when valid"
    !=
    "Force capital into positions"
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
# POSITION CONTRACT
# ============================================================================

POSITION_FIELDS = [
    "asset",
    "direction",
    "state",
    "risk_budget",
    "entry_price",
    "stop_distance",
    "position_size",
    "exposure",
]


POSITION_STATES = [
    "CALCULATED",
    "UNCALCULATED",
    "BLOCKED",
]


DIRECTIONS = [
    "LONG",
    "SHORT",
    "NONE",
]


# ============================================================================
# PORTFOLIO CONTRACT
# ============================================================================

PORTFOLIO_FIELDS = [
    "state",
    "total_risk",
    "total_exposure",
    "active_positions",
    "max_portfolio_risk",
    "max_concurrent_positions",
    "available_capital",
    "capital_utilization",
    "unused_capital",
    "capital_valid",
    "risk_valid",
]


PORTFOLIO_STATES = [
    "VALID",
    "BLOCKED",
    "UNCALCULATED",
]


# ============================================================================
# PORTFOLIO REASONS
# ============================================================================

PORTFOLIO_REASONS = [
    "PORTFOLIO_VALID",
    "RISK_LIMIT_EXCEEDED",
    "EXPOSURE_LIMIT_EXCEEDED",
    "CONCURRENT_POSITION_LIMIT_EXCEEDED",
    "INSUFFICIENT_AVAILABLE_CAPITAL",
    "INVALID_POSITION",
    "CAPITAL_NOT_VALID",
    "PORTFOLIO_NOT_CALCULATED",
]


# ============================================================================
# CONTRACT COUNTS
# ============================================================================

EXPECTED_ASSET_COUNT = len(
    EXPECTED_ASSETS
)

POSITION_FIELD_COUNT = len(
    POSITION_FIELDS
)

PORTFOLIO_FIELD_COUNT = len(
    PORTFOLIO_FIELDS
)

POSITION_STATE_COUNT = len(
    POSITION_STATES
)

PORTFOLIO_STATE_COUNT = len(
    PORTFOLIO_STATES
)

PORTFOLIO_REASON_COUNT = len(
    PORTFOLIO_REASONS
)


# ============================================================================
# POSITION VALIDATION
# ============================================================================

def validate_position(
    position,
):
    """
    Validate one position-sizing record.

    This function validates structure only.

    It does NOT:
        - calculate position size
        - calculate exposure
        - calculate risk
        - modify the position
    """

    if not isinstance(
        position,
        dict,
    ):

        raise RuntimeError(
            "Position must be a dictionary"
        )

    for field in POSITION_FIELDS:

        if field not in position:

            raise RuntimeError(
                f"Missing position field: {field}"
            )

    asset = position[
        "asset"
    ]

    if asset not in EXPECTED_ASSETS:

        raise RuntimeError(
            f"Unknown asset: {asset}"
        )

    direction = position[
        "direction"
    ]

    if direction not in DIRECTIONS:

        raise RuntimeError(
            f"Invalid position direction: {direction}"
        )

    state = position[
        "state"
    ]

    if state not in POSITION_STATES:

        raise RuntimeError(
            f"Invalid position state: {state}"
        )

    return True


# ============================================================================
# POSITION SNAPSHOT VALIDATION
# ============================================================================

def validate_position_snapshot(
    positions,
):
    """
    Validate a complete position-sizing snapshot.

    Expected:
        one record for every expected asset.
    """

    if not isinstance(
        positions,
        list,
    ):

        raise RuntimeError(
            "Position snapshot must be a list"
        )

    assets = set()

    for position in positions:

        validate_position(
            position
        )

        asset = position[
            "asset"
        ]

        if asset in assets:

            raise RuntimeError(
                f"Duplicate position asset: {asset}"
            )

        assets.add(
            asset
        )

    missing = [
        asset
        for asset in EXPECTED_ASSETS
        if asset not in assets
    ]

    if missing:

        raise RuntimeError(
            "Missing position assets: "
            + ", ".join(missing)
        )

    return True


# ============================================================================
# PORTFOLIO VALIDATION
# ============================================================================

def validate_portfolio(
    portfolio,
):
    """
    Validate one portfolio-risk result.

    Structural validation only.
    """

    if not isinstance(
        portfolio,
        dict,
    ):

        raise RuntimeError(
            "Portfolio must be a dictionary"
        )

    for field in PORTFOLIO_FIELDS:

        if field not in portfolio:

            raise RuntimeError(
                f"Missing portfolio field: {field}"
            )

    state = portfolio[
        "state"
    ]

    if state not in PORTFOLIO_STATES:

        raise RuntimeError(
            f"Invalid portfolio state: {state}"
        )

    return True


# ============================================================================
# PORTFOLIO REASON VALIDATION
# ============================================================================

def validate_portfolio_reason(
    reason,
):
    """
    Validate portfolio reason code.
    """

    if reason not in PORTFOLIO_REASONS:

        raise RuntimeError(
            f"Invalid portfolio reason: {reason}"
        )

    return True


# ============================================================================
# COMPLETE PORTFOLIO SNAPSHOT VALIDATION
# ============================================================================

def validate_portfolio_snapshot(
    positions,
    portfolio,
):
    """
    Validate the complete portfolio-risk contract.

    Inputs:
        positions
        portfolio

    This function performs structural validation only.
    """

    validate_position_snapshot(
        positions
    )

    validate_portfolio(
        portfolio
    )

    reason = portfolio.get(
        "reason"
    )

    if reason is not None:

        validate_portfolio_reason(
            reason
        )

    return True


# ============================================================================
# CONTRACT INFORMATION
# ============================================================================

def print_header():

    print("=" * 77)
    print(
        "ARUNDA PORTFOLIO RISK CONTRACT v0.2"
    )
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{EXPECTED_ASSET_COUNT}"
    )

    print(
        f"Position Fields : "
        f"{POSITION_FIELD_COUNT}"
    )

    print(
        f"Portfolio Fields: "
        f"{PORTFOLIO_FIELD_COUNT}"
    )

    print(
        "Position States : "
        "CALCULATED / UNCALCULATED / BLOCKED"
    )

    print(
        "Portfolio States: "
        "VALID / BLOCKED / UNCALCULATED"
    )

    print(
        "Capital Model   : "
        "MAXIMUM VALID UTILIZATION"
    )

    print(
        "Unused Capital  : ALLOWED"
    )

    print(
        "Forced Exposure : NOT ALLOWED"
    )

    print(
        f"Portfolio Reasons: "
        f"{PORTFOLIO_REASON_COUNT}"
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
        "Position Size   : INPUT ONLY"
    )

    print(
        "Risk Budget     : INPUT ONLY"
    )

    print(
        "Capital         : INPUT ONLY"
    )

    print(
        "Portfolio Risk  : OUTPUT VALIDATION"
    )

    print(
        "Capital Usage   : OUTPUT VALIDATION"
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
        "PORTFOLIO RISK CONTRACT"
    )
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{EXPECTED_ASSET_COUNT}"
    )

    print(
        "Portfolio checks:"
    )

    print(
        "  - Total Risk"
    )

    print(
        "  - Total Exposure"
    )

    print(
        "  - Active Positions"
    )

    print(
        "  - Maximum Portfolio Risk"
    )

    print(
        "  - Maximum Concurrent Positions"
    )

    print(
        "  - Available Capital"
    )

    print(
        "  - Capital Utilization"
    )

    print(
        "  - Unused Capital"
    )

    print(
        "Capital Model   : "
        "MAXIMUM VALID UTILIZATION"
    )

    print(
        "Unused Capital  : ALLOWED"
    )

    print(
        "Forced Exposure : NOT ALLOWED"
    )

    print(
        f"Portfolio Reasons: "
        f"{PORTFOLIO_REASON_COUNT}"
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
        "Execution       : NOT USED"
    )

    print(
        "Contract Status : VALID"
    )

    print("=" * 77)


# ============================================================================
# STRUCTURAL SELF TEST
# ============================================================================

def run_self_test():

    if EXPECTED_ASSET_COUNT != 15:

        raise RuntimeError(
            "Expected asset count must be 15"
        )

    if POSITION_FIELD_COUNT != 8:

        raise RuntimeError(
            "Position field count must be 8"
        )

    if PORTFOLIO_FIELD_COUNT != 11:

        raise RuntimeError(
            "Portfolio field count must be 11"
        )

    if POSITION_STATE_COUNT != 3:

        raise RuntimeError(
            "Position state count must be 3"
        )

    if PORTFOLIO_STATE_COUNT != 3:

        raise RuntimeError(
            "Portfolio state count must be 3"
        )

    if len(DIRECTIONS) != 3:

        raise RuntimeError(
            "Direction count must be 3"
        )

    if PORTFOLIO_REASON_COUNT != 8:

        raise RuntimeError(
            "Portfolio reason count must be 8"
        )

    # ------------------------------------------------------------------------
    # Asset uniqueness
    # ------------------------------------------------------------------------

    if len(
        set(EXPECTED_ASSETS)
    ) != EXPECTED_ASSET_COUNT:

        raise RuntimeError(
            "Expected assets contain duplicates"
        )

    # ------------------------------------------------------------------------
    # State uniqueness
    # ------------------------------------------------------------------------

    if len(
        set(POSITION_STATES)
    ) != POSITION_STATE_COUNT:

        raise RuntimeError(
            "Position states contain duplicates"
        )

    if len(
        set(PORTFOLIO_STATES)
    ) != PORTFOLIO_STATE_COUNT:

        raise RuntimeError(
            "Portfolio states contain duplicates"
        )

    # ------------------------------------------------------------------------
    # Direction uniqueness
    # ------------------------------------------------------------------------

    if len(
        set(DIRECTIONS)
    ) != 3:

        raise RuntimeError(
            "Directions contain duplicates"
        )

    # ------------------------------------------------------------------------
    # Reason uniqueness
    # ------------------------------------------------------------------------

    if len(
        set(PORTFOLIO_REASONS)
    ) != PORTFOLIO_REASON_COUNT:

        raise RuntimeError(
            "Portfolio reasons contain duplicates"
        )

    return True


# ============================================================================
# MAIN
# ============================================================================

def main():

    print_header()

    try:

        run_self_test()

        print_contract()

        print()
        print(
            "PORTFOLIO RISK CONTRACT STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()
        print("=" * 77)
        print(
            "PORTFOLIO RISK CONTRACT ERROR"
        )
        print("=" * 77)

        print(
            f"Type  : "
            f"{type(exc).__name__}"
        )

        print(
            f"Error : {exc}"
        )

        print()
        print(
            "PORTFOLIO RISK CONTRACT STATUS : FAILED"
        )

        return 1


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )