"""
ARUNDA RISK BUDGET CONTRACT v0.1

Purpose:
    Define the formal structure of the Risk Budget layer.

Architecture:
    Decision
        ↓
    Risk Engine
        ↓
    Risk Budget Contract
        ↓
    Position Sizing (future)
        ↓
    Execution Contract (future)

Rules:
    - MEMORY ONLY
    - NO SQL
    - NO DATABASE WRITES
    - NO EXECUTION
    - NO POSITION SIZING YET
    - NO STOP LOSS
    - NO TAKE PROFIT
    - NO LEVERAGE
    - NO PORTFOLIO EXPOSURE CALCULATION
    - NO PREDICTION
    - NO RANKING
    - NO INTERPRETATION
"""

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

BUDGET_STATES = (
    "ALLOCATED",
    "UNALLOCATED",
    "BLOCKED",
)

DIRECTIONS = (
    "LONG",
    "SHORT",
    "NONE",
)

BUDGET_FIELDS = (
    "asset",
    "budget_state",
    "direction",
    "risk_budget",
    "reason",
)


def build_empty_budget(asset):
    """
    Create an empty Risk Budget structure.

    This function defines structure only.
    No budget calculation is performed.
    """

    if asset not in EXPECTED_ASSETS:
        raise ValueError(
            f"Unknown asset: {asset}"
        )

    return {
        "asset": asset,
        "budget_state": "UNALLOCATED",
        "direction": "NONE",
        "risk_budget": None,
        "reason": None,
    }


def validate_budget(budget):
    """
    Validate one Risk Budget object.
    """

    if not isinstance(budget, dict):
        raise RuntimeError(
            "Risk Budget must be a dictionary"
        )

    missing = [
        field
        for field in BUDGET_FIELDS
        if field not in budget
    ]

    if missing:
        raise RuntimeError(
            f"Missing budget fields: {missing}"
        )

    asset = budget["asset"]

    if asset not in EXPECTED_ASSETS:
        raise RuntimeError(
            f"Invalid asset: {asset}"
        )

    state = budget["budget_state"]

    if state not in BUDGET_STATES:
        raise RuntimeError(
            f"Invalid budget state for {asset}: "
            f"{state}"
        )

    direction = budget["direction"]

    if direction not in DIRECTIONS:
        raise RuntimeError(
            f"Invalid direction for {asset}: "
            f"{direction}"
        )

    risk_budget = budget["risk_budget"]

    if risk_budget is not None:

        if isinstance(risk_budget, bool):
            raise RuntimeError(
                f"Invalid risk budget type for {asset}"
            )

        if not isinstance(
            risk_budget,
            (int, float)
        ):
            raise RuntimeError(
                f"Invalid risk budget for {asset}: "
                f"{risk_budget!r}"
            )

        if risk_budget < 0:
            raise RuntimeError(
                f"Risk budget cannot be negative "
                f"for {asset}"
            )

    reason = budget["reason"]

    if reason is not None:

        if not isinstance(reason, str):
            raise RuntimeError(
                f"Invalid budget reason for {asset}"
            )

    return True


def validate_budget_snapshot(snapshot):
    """
    Validate a complete Risk Budget snapshot.
    """

    if not isinstance(snapshot, dict):
        raise RuntimeError(
            "Risk Budget snapshot must be a dictionary"
        )

    expected = set(EXPECTED_ASSETS)
    actual = set(snapshot.keys())

    missing = expected - actual
    extra = actual - expected

    if missing:
        raise RuntimeError(
            f"Missing assets: {sorted(missing)}"
        )

    if extra:
        raise RuntimeError(
            f"Unexpected assets: {sorted(extra)}"
        )

    for asset in EXPECTED_ASSETS:
        validate_budget(snapshot[asset])

    allocated = sum(
        1
        for asset in EXPECTED_ASSETS
        if snapshot[asset]["budget_state"]
        == "ALLOCATED"
    )

    unallocated = sum(
        1
        for asset in EXPECTED_ASSETS
        if snapshot[asset]["budget_state"]
        == "UNALLOCATED"
    )

    blocked = sum(
        1
        for asset in EXPECTED_ASSETS
        if snapshot[asset]["budget_state"]
        == "BLOCKED"
    )

    return {
        "expected_assets": EXPECTED_ASSET_COUNT,
        "validated_assets": len(snapshot),
        "allocated": allocated,
        "unallocated": unallocated,
        "blocked": blocked,
        "contract_status": "VALID",
    }


def print_header():
    print("=" * 77)
    print("ARUNDA RISK BUDGET CONTRACT v0.1")
    print("=" * 77)
    print("Source   : risk_engine")
    print("Storage  : MEMORY ONLY")
    print("Writes   : NONE")
    print("SQL      : NOT USED")
    print("Execution       : NOT USED")
    print("Position Sizing : NOT USED")
    print("Stop Loss       : NOT USED")
    print("Take Profit     : NOT USED")
    print("Leverage        : NOT USED")
    print("Portfolio Risk  : NOT USED")
    print("Prediction      : NOT USED")
    print("Ranking         : NOT USED")
    print("Interpretation  : NOT USED")
    print("=" * 77)


def print_contract():
    print()
    print("=" * 77)
    print("RISK BUDGET CONTRACT")
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{EXPECTED_ASSET_COUNT}"
    )

    print(
        f"Budget Fields   : "
        f"{len(BUDGET_FIELDS)}"
    )

    print(
        f"Budget States   : "
        f"{len(BUDGET_STATES)}"
    )

    print(
        "States          : "
        + " / ".join(BUDGET_STATES)
    )

    print(
        "Directions      : "
        + " / ".join(DIRECTIONS)
    )

    print("Storage         : MEMORY ONLY")
    print("Database writes : NONE")
    print("SQL             : NOT USED")
    print("Risk Engine     : INPUT ONLY")
    print("Position Sizing : NOT USED")
    print("Stop Loss       : NOT USED")
    print("Take Profit     : NOT USED")
    print("Leverage        : NOT USED")
    print("Portfolio Risk  : NOT USED")
    print("Execution       : NOT USED")
    print("Prediction      : NOT USED")
    print("Ranking         : NOT USED")
    print("Interpretation  : NOT USED")
    print("Contract Status : VALID")
    print("=" * 77)


def main():

    print_header()

    try:

        # Contract-only validation.
        # No real budget allocation occurs here.

        for asset in EXPECTED_ASSETS:

            budget = build_empty_budget(
                asset
            )

            validate_budget(
                budget
            )

        print_contract()

        print()
        print(
            "RISK BUDGET CONTRACT STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()
        print("=" * 77)
        print("RISK BUDGET CONTRACT ERROR")
        print("=" * 77)

        print(
            f"Type   : "
            f"{type(exc).__name__}"
        )

        print(
            f"Error  : {exc}"
        )

        print()
        print(
            "RISK BUDGET CONTRACT STATUS : FAILED"
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())