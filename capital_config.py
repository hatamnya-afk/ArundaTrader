"""
ARUNDA CAPITAL CONFIG v0.1

Initial real-capital configuration.

Important:
    This file only defines capital parameters.
    It does NOT trade.
    It does NOT size positions.
    It does NOT send orders.
"""

from capital_contract import (
    CAPITAL_FIELDS,
    validate_capital,
)


# ============================================================================
# CAPITAL CONFIGURATION
# ============================================================================

CAPITAL = 1_000_000

AVAILABLE_CAPITAL = 1_000_000

# 0.50% risk per trade
RISK_PER_TRADE = 0.005

# 1.00% maximum total portfolio risk
MAX_PORTFOLIO_RISK = 0.01

# Maximum simultaneous positions
MAX_CONCURRENT_POSITIONS = 2


CONFIG = {
    "capital": CAPITAL,
    "available_capital": AVAILABLE_CAPITAL,
    "risk_per_trade": RISK_PER_TRADE,
    "max_portfolio_risk": MAX_PORTFOLIO_RISK,
    "max_concurrent_positions": MAX_CONCURRENT_POSITIONS,
}


def validate_config():

    validate_capital(CONFIG)

    return True


def get_config():

    validate_config()

    return CONFIG.copy()


def get_config_state():

    validate_config()

    if all(
        CONFIG[field] is not None
        for field in CAPITAL_FIELDS
    ):
        return "CONFIGURED"

    return "UNCONFIGURED"


def print_header():

    print("=" * 77)
    print("ARUNDA CAPITAL CONFIG v0.1")
    print("=" * 77)

    print("Source          : capital_contract")
    print("Mode            : REAL CAPITAL CONFIG")
    print("Storage         : MEMORY ONLY")
    print("Writes          : NONE")
    print("SQL             : NOT USED")
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


def print_config():

    state = get_config_state()

    print()
    print("=" * 77)
    print("CAPITAL CONFIGURATION")
    print("=" * 77)

    print(
        f"Capital                  : "
        f"{CONFIG['capital']:,}"
    )

    print(
        f"Available Capital        : "
        f"{CONFIG['available_capital']:,}"
    )

    print(
        f"Risk Per Trade           : "
        f"{CONFIG['risk_per_trade'] * 100:.2f}%"
    )

    print(
        f"Risk Amount Per Trade    : "
        f"{CONFIG['capital'] * CONFIG['risk_per_trade']:,.0f}"
    )

    print(
        f"Max Portfolio Risk       : "
        f"{CONFIG['max_portfolio_risk'] * 100:.2f}%"
    )

    print(
        f"Max Portfolio Risk Amt   : "
        f"{CONFIG['capital'] * CONFIG['max_portfolio_risk']:,.0f}"
    )

    print(
        f"Max Concurrent Positions : "
        f"{CONFIG['max_concurrent_positions']}"
    )

    print()
    print(
        f"Configuration State      : "
        f"{state}"
    )

    print("Contract                 : capital_contract")
    print("Contract Status          : VALID")

    print("=" * 77)


def main():

    print_header()

    try:

        validate_config()

        print_config()

        print()
        print(
            "CAPITAL CONFIG STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()
        print("=" * 77)
        print("CAPITAL CONFIG ERROR")
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
            "CAPITAL CONFIG STATUS : FAILED"
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())