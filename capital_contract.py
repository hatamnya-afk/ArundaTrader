"""
ARUNDA CAPITAL CONTRACT v0.1

Purpose:
    Define the formal capital/risk inputs used by future
    capital allocation and position sizing layers.

Architecture:

    Risk Budget Engine
            ↓
    Capital Contract
            ↓
    Capital Configuration
            ↓
    Position Sizing (future)
            ↓
    Stop / Target (future)
            ↓
    Execution Contract (future)

Rules:
    - MEMORY ONLY
    - NO SQL
    - NO DATABASE WRITES
    - NO EXECUTION
    - NO POSITION SIZING
    - NO STOP LOSS
    - NO TAKE PROFIT
    - NO LEVERAGE
    - NO PORTFOLIO CALCULATION
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

CAPITAL_FIELDS = (
    "capital",
    "available_capital",
    "risk_per_trade",
    "max_portfolio_risk",
    "max_concurrent_positions",
)

CAPITAL_STATES = (
    "CONFIGURED",
    "UNCONFIGURED",
)

STORAGE = "MEMORY ONLY"


def build_empty_capital():
    """
    Create the formal capital structure.

    v0.1 intentionally contains no real capital values.
    """

    return {
        "capital": None,
        "available_capital": None,
        "risk_per_trade": None,
        "max_portfolio_risk": None,
        "max_concurrent_positions": None,
    }


def validate_capital(capital):
    """
    Validate the Capital Contract structure.
    """

    if not isinstance(capital, dict):
        raise RuntimeError(
            "Capital configuration must be a dictionary"
        )

    missing = [
        field
        for field in CAPITAL_FIELDS
        if field not in capital
    ]

    if missing:
        raise RuntimeError(
            f"Missing capital fields: {missing}"
        )

    for field in CAPITAL_FIELDS:

        value = capital[field]

        if value is None:
            continue

        if isinstance(value, bool):
            raise RuntimeError(
                f"Invalid boolean value for {field}"
            )

        if not isinstance(
            value,
            (int, float)
        ):
            raise RuntimeError(
                f"Invalid value for {field}: "
                f"{value!r}"
            )

        if value < 0:
            raise RuntimeError(
                f"{field} cannot be negative"
            )

    concurrent = capital[
        "max_concurrent_positions"
    ]

    if concurrent is not None:

        if not isinstance(
            concurrent,
            int
        ):
            raise RuntimeError(
                "max_concurrent_positions "
                "must be an integer"
            )

        if concurrent < 1:
            raise RuntimeError(
                "max_concurrent_positions "
                "must be >= 1"
            )

    return True


def get_capital_state(capital):
    """
    Return the configuration state.

    Since v0.1 does not contain real values,
    the default state is UNCONFIGURED.
    """

    validate_capital(capital)

    if all(
        capital[field] is not None
        for field in CAPITAL_FIELDS
    ):
        return "CONFIGURED"

    return "UNCONFIGURED"


def print_header():

    print("=" * 77)
    print("ARUNDA CAPITAL CONTRACT v0.1")
    print("=" * 77)

    print("Source          : risk_budget_engine")
    print("Storage         : MEMORY ONLY")
    print("Writes          : NONE")
    print("SQL             : NOT USED")
    print("Position Sizing : NOT USED")
    print("Stop Loss       : NOT USED")
    print("Take Profit     : NOT USED")
    print("Leverage        : NOT USED")
    print("Portfolio Risk  : NOT USED")
    print("Execution       : NOT USED")
    print("Prediction      : NOT USED")
    print("Ranking         : NOT USED")
    print("Interpretation  : NOT USED")

    print("=" * 77)


def print_contract(capital):

    state = get_capital_state(
        capital
    )

    print()
    print("=" * 77)
    print("CAPITAL CONTRACT")
    print("=" * 77)

    print(
        f"Capital Fields      : "
        f"{len(CAPITAL_FIELDS)}"
    )

    print(
        "Fields              : "
        + " / ".join(CAPITAL_FIELDS)
    )

    print(
        f"Capital State       : "
        f"{state}"
    )

    print("Capital Value       : NOT SET")
    print("Available Capital   : NOT SET")
    print("Risk Per Trade      : NOT SET")
    print("Max Portfolio Risk  : NOT SET")
    print(
        "Max Concurrent Pos : NOT SET"
    )

    print("Storage             : MEMORY ONLY")
    print("Database writes     : NONE")
    print("SQL                 : NOT USED")
    print("Position Sizing     : NOT USED")
    print("Stop Loss           : NOT USED")
    print("Take Profit         : NOT USED")
    print("Leverage            : NOT USED")
    print("Portfolio Risk      : NOT USED")
    print("Execution           : NOT USED")
    print("Prediction          : NOT USED")
    print("Ranking             : NOT USED")
    print("Interpretation      : NOT USED")

    print("Contract Status     : VALID")
    print("=" * 77)


def main():

    print_header()

    try:

        capital = build_empty_capital()

        validate_capital(
            capital
        )

        print_contract(
            capital
        )

        print()
        print(
            "CAPITAL CONTRACT STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()
        print("=" * 77)
        print("CAPITAL CONTRACT ERROR")
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
            "CAPITAL CONTRACT STATUS : FAILED"
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())