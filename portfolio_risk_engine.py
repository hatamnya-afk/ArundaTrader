"""
ARUNDA PORTFOLIO RISK ENGINE v0.1

Purpose:
    Validate the complete position-sizing portfolio
    against capital and portfolio-risk constraints.

Architecture:

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
    Future Execution

Rules:
    - MEMORY ONLY
    - NO SQL
    - NO DATABASE WRITES
    - NO EXCHANGE CONNECTION
    - BITPIN = FUTURE EXECUTION
    - NO LEVERAGE
    - NO TAKE PROFIT
    - NO EXECUTION
    - NO PREDICTION
    - NO RANKING
    - NO INTERPRETATION

Capital Model:
    MAXIMUM VALID UTILIZATION

Important:
    Unused capital is allowed.
    Forced exposure is NOT allowed.
"""

# ============================================================================
# IMPORTS
# ============================================================================

from portfolio_risk_contract import (
    EXPECTED_ASSETS,
    validate_portfolio,
)

import capital_config
import position_sizing_engine


# ============================================================================
# CONSTANTS
# ============================================================================

EPSILON = 1e-12


# ============================================================================
# CAPITAL
# ============================================================================

def load_capital_config():
    """
    Load the existing capital configuration.

    No new capital API is invented.
    """

    loader_names = [
        "get_config",
        "load_config",
        "get_capital_config",
        "load_capital_config",
    ]

    for name in loader_names:

        loader = getattr(
            capital_config,
            name,
            None,
        )

        if callable(loader):

            data = loader()

            if isinstance(data, dict):

                return data

    required = [
        "capital",
        "available_capital",
        "risk_per_trade",
        "max_portfolio_risk",
        "max_concurrent_positions",
    ]

    if all(
        hasattr(
            capital_config,
            field,
        )
        for field in required
    ):

        return {
            field: getattr(
                capital_config,
                field,
            )
            for field in required
        }

    raise RuntimeError(
        "capital_config does not expose "
        "a supported configuration API"
    )


# ============================================================================
# POSITION SIZING SNAPSHOT
# ============================================================================

def load_position_snapshot():
    """
    Load the real Position Sizing snapshot.

    Real API:
        position_sizing_engine.calculate_snapshot()

    Expected structure:

        {
            "capital": {...},
            "risk_amount": ...,
            "positions": [...]
        }
    """

    loader = getattr(
        position_sizing_engine,
        "calculate_snapshot",
        None,
    )

    if not callable(loader):

        raise RuntimeError(
            "position_sizing_engine must expose "
            "calculate_snapshot()"
        )

    snapshot = loader()

    if not isinstance(
        snapshot,
        dict,
    ):

        raise RuntimeError(
            "Position sizing snapshot must be a dictionary"
        )

    positions = snapshot.get(
        "positions"
    )

    if not isinstance(
        positions,
        list,
    ):

        raise RuntimeError(
            "Position sizing snapshot must contain "
            "a positions list"
        )

    return snapshot


# ============================================================================
# POSITION INDEX
# ============================================================================

def index_positions(
    positions,
):

    result = {}

    for record in positions:

        if not isinstance(
            record,
            dict,
        ):
            continue

        asset = record.get(
            "asset"
        )

        if asset is None:
            continue

        result[asset] = record

    return result


# ============================================================================
# TOTAL RISK
# ============================================================================

def calculate_total_risk(
    positions,
):

    total = 0.0

    for record in positions:

        if not isinstance(
            record,
            dict,
        ):
            continue

        if record.get(
            "state"
        ) != "CALCULATED":

            continue

        risk = record.get(
            "risk_budget"
        )

        if risk is None:
            continue

        try:

            risk = float(
                risk
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        if risk > 0:

            total += risk

    return total


# ============================================================================
# TOTAL EXPOSURE
# ============================================================================

def calculate_total_exposure(
    positions,
):

    total = 0.0

    for record in positions:

        if not isinstance(
            record,
            dict,
        ):
            continue

        if record.get(
            "state"
        ) != "CALCULATED":

            continue

        exposure = record.get(
            "exposure"
        )

        if exposure is None:
            continue

        try:

            exposure = float(
                exposure
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        if exposure > 0:

            total += exposure

    return total


# ============================================================================
# ACTIVE POSITIONS
# ============================================================================

def calculate_active_positions(
    positions,
):

    return sum(
        1
        for record in positions
        if isinstance(
            record,
            dict,
        )
        and record.get(
            "state"
        ) == "CALCULATED"
    )


# ============================================================================
# AVAILABLE CAPITAL
# ============================================================================

def calculate_available_capital(
    capital,
    total_exposure,
):

    capital = float(
        capital
    )

    total_exposure = float(
        total_exposure
    )

    if capital < 0:

        raise RuntimeError(
            "Capital cannot be negative"
        )

    if total_exposure < 0:

        raise RuntimeError(
            "Exposure cannot be negative"
        )

    available = (
        capital
        - total_exposure
    )

    # Small floating point noise.
    if abs(available) <= EPSILON:

        available = 0.0

    return available


# ============================================================================
# CAPITAL UTILIZATION
# ============================================================================

def calculate_capital_utilization(
    capital,
    total_exposure,
):

    capital = float(
        capital
    )

    total_exposure = float(
        total_exposure
    )

    if capital <= EPSILON:

        return 0.0

    utilization = (
        total_exposure
        / capital
    )

    return utilization


# ============================================================================
# UNUSED CAPITAL
# ============================================================================

def calculate_unused_capital(
    capital,
    total_exposure,
):

    available = calculate_available_capital(
        capital=capital,
        total_exposure=total_exposure,
    )

    if available < 0 and abs(available) <= EPSILON:

        return 0.0

    return max(
        0.0,
        available,
    )


# ============================================================================
# PORTFOLIO RISK LIMIT
# ============================================================================

def calculate_max_portfolio_risk_amount(
    capital,
    max_portfolio_risk,
):

    capital = float(
        capital
    )

    max_portfolio_risk = float(
        max_portfolio_risk
    )

    if capital <= 0:

        raise RuntimeError(
            "Capital must be greater than zero"
        )

    if max_portfolio_risk < 0:

        raise RuntimeError(
            "Maximum portfolio risk cannot be negative"
        )

    return (
        capital
        * max_portfolio_risk
    )


# ============================================================================
# VALIDATION
# ============================================================================

def validate_portfolio_limits(
    total_risk,
    total_exposure,
    active_positions,
    capital,
    available_capital,
    max_portfolio_risk_amount,
    max_concurrent_positions,
):
    """
    Validate portfolio-level limits.

    Returns:

        {
            "state": "VALID" / "BLOCKED",
            "reason": ...
        }
    """

    # ------------------------------------------------------------------------
    # Risk
    # ------------------------------------------------------------------------

    if total_risk > (
        max_portfolio_risk_amount
        + EPSILON
    ):

        return {
            "state": "BLOCKED",
            "reason": "MAX_PORTFOLIO_RISK_EXCEEDED",
        }

    # ------------------------------------------------------------------------
    # Concurrent positions
    # ------------------------------------------------------------------------

    if active_positions > int(
        max_concurrent_positions
    ):

        return {
            "state": "BLOCKED",
            "reason": "MAX_CONCURRENT_POSITIONS_EXCEEDED",
        }

    # ------------------------------------------------------------------------
    # Capital
    # ------------------------------------------------------------------------

    if total_exposure > (
        capital
        + EPSILON
    ):

        return {
            "state": "BLOCKED",
            "reason": "CAPITAL_EXCEEDED",
        }

    if available_capital < -EPSILON:

        return {
            "state": "BLOCKED",
            "reason": "AVAILABLE_CAPITAL_NEGATIVE",
        }

    # ------------------------------------------------------------------------
    # Valid
    # ------------------------------------------------------------------------

    return {
        "state": "VALID",
        "reason": "PORTFOLIO_WITHIN_LIMITS",
    }


# ============================================================================
# BUILD PORTFOLIO RECORD
# ============================================================================

def build_portfolio_record(
    capital,
    available_capital,
    total_risk,
    total_exposure,
    active_positions,
    max_portfolio_risk,
    max_portfolio_risk_amount,
    max_concurrent_positions,
    capital_utilization,
    unused_capital,
    state,
    reason,
):

    return {
        "state": state,
        "reason": reason,
        "capital": float(
            capital
        ),
        "available_capital": float(
            available_capital
        ),
        "total_risk": float(
            total_risk
        ),
        "total_exposure": float(
            total_exposure
        ),
        "active_positions": int(
            active_positions
        ),
        "max_portfolio_risk": float(
            max_portfolio_risk
        ),
        "max_portfolio_risk_amount": float(
            max_portfolio_risk_amount
        ),
        "max_concurrent_positions": int(
            max_concurrent_positions
        ),
        "capital_utilization": float(
            capital_utilization
        ),
        "unused_capital": float(
            unused_capital
        ),
    }


# ============================================================================
# SNAPSHOT
# ============================================================================

def calculate_snapshot():

    # ------------------------------------------------------------------------
    # Capital
    # ------------------------------------------------------------------------

    capital_config_snapshot = (
        load_capital_config()
    )

    capital = float(
        capital_config_snapshot[
            "capital"
        ]
    )

    configured_available_capital = float(
        capital_config_snapshot[
            "available_capital"
        ]
    )

    max_portfolio_risk = float(
        capital_config_snapshot[
            "max_portfolio_risk"
        ]
    )

    max_concurrent_positions = int(
        capital_config_snapshot[
            "max_concurrent_positions"
        ]
    )

    # ------------------------------------------------------------------------
    # Position Sizing
    # ------------------------------------------------------------------------

    position_snapshot = (
        load_position_snapshot()
    )

    positions = position_snapshot[
        "positions"
    ]

    # ------------------------------------------------------------------------
    # Structural validation
    # ------------------------------------------------------------------------

    position_map = index_positions(
        positions
    )

    missing_assets = [
        asset
        for asset in EXPECTED_ASSETS
        if asset not in position_map
    ]

    if missing_assets:

        raise RuntimeError(
            "Position sizing snapshot missing assets: "
            + ", ".join(
                missing_assets
            )
        )

    # ------------------------------------------------------------------------
    # Portfolio calculations
    # ------------------------------------------------------------------------

    total_risk = (
        calculate_total_risk(
            positions
        )
    )

    total_exposure = (
        calculate_total_exposure(
            positions
        )
    )

    active_positions = (
        calculate_active_positions(
            positions
        )
    )

    available_capital = (
        calculate_available_capital(
            capital=capital,
            total_exposure=total_exposure,
        )
    )

    capital_utilization = (
        calculate_capital_utilization(
            capital=capital,
            total_exposure=total_exposure,
        )
    )

    unused_capital = (
        calculate_unused_capital(
            capital=capital,
            total_exposure=total_exposure,
        )
    )

    max_portfolio_risk_amount = (
        calculate_max_portfolio_risk_amount(
            capital=capital,
            max_portfolio_risk=max_portfolio_risk,
        )
    )

    # ------------------------------------------------------------------------
    # Limit validation
    # ------------------------------------------------------------------------

    validation = (
        validate_portfolio_limits(
            total_risk=total_risk,
            total_exposure=total_exposure,
            active_positions=active_positions,
            capital=capital,
            available_capital=available_capital,
            max_portfolio_risk_amount=max_portfolio_risk_amount,
            max_concurrent_positions=max_concurrent_positions,
        )
    )

    state = validation[
        "state"
    ]

    reason = validation[
        "reason"
    ]

    # ------------------------------------------------------------------------
    # Build portfolio
    # ------------------------------------------------------------------------

    portfolio = (
        build_portfolio_record(
            capital=capital,
            available_capital=available_capital,
            total_risk=total_risk,
            total_exposure=total_exposure,
            active_positions=active_positions,
            max_portfolio_risk=max_portfolio_risk,
            max_portfolio_risk_amount=max_portfolio_risk_amount,
            max_concurrent_positions=max_concurrent_positions,
            capital_utilization=capital_utilization,
            unused_capital=unused_capital,
            state=state,
            reason=reason,
        )
    )

    return {
        "capital": capital_config_snapshot,
        "positions": positions,
        "portfolio": portfolio,
        "configured_available_capital": configured_available_capital,
    }


# ============================================================================
# HEADER
# ============================================================================

def print_header():

    print("=" * 77)
    print("ARUNDA PORTFOLIO RISK ENGINE v0.1")
    print("=" * 77)

    print(
        "Source          : position_sizing"
    )

    print(
        "Capital         : capital_config"
    )

    print(
        "Formula         : Portfolio Validation"
    )

    print(
        "Capital Model   : MAXIMUM VALID UTILIZATION"
    )

    print(
        "Unused Capital  : ALLOWED"
    )

    print(
        "Forced Exposure : NOT ALLOWED"
    )

    print(
        "Storage         : MEMORY ONLY"
    )

    print(
        "Writes          : NONE"
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
        "Leverage        : NOT USED"
    )

    print(
        "Take Profit     : NOT USED"
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

    print("=" * 77)


# ============================================================================
# RESULTS
# ============================================================================

def print_results(
    snapshot,
):

    portfolio = snapshot[
        "portfolio"
    ]

    positions = snapshot[
        "positions"
    ]

    calculated = sum(
        1
        for row in positions
        if row.get(
            "state"
        ) == "CALCULATED"
    )

    uncalculated = sum(
        1
        for row in positions
        if row.get(
            "state"
        ) == "UNCALCULATED"
    )

    blocked = sum(
        1
        for row in positions
        if row.get(
            "state"
        ) == "BLOCKED"
    )

    print()
    print("=" * 77)
    print("PORTFOLIO POSITION INPUT")
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{len(EXPECTED_ASSETS)}"
    )

    print(
        f"Calculated      : "
        f"{calculated}"
    )

    print(
        f"Uncalculated    : "
        f"{uncalculated}"
    )

    print(
        f"Blocked         : "
        f"{blocked}"
    )

    print()
    print("=" * 77)
    print("PORTFOLIO RISK SNAPSHOT")
    print("=" * 77)

    print(
        f"State                   : "
        f"{portfolio['state']}"
    )

    print(
        f"Reason                  : "
        f"{portfolio['reason']}"
    )

    print(
        f"Capital                 : "
        f"{portfolio['capital']:,.2f}"
    )

    print(
        f"Available Capital       : "
        f"{portfolio['available_capital']:,.2f}"
    )

    print(
        f"Total Risk              : "
        f"{portfolio['total_risk']:,.2f}"
    )

    print(
        f"Max Portfolio Risk      : "
        f"{portfolio['max_portfolio_risk_amount']:,.2f}"
    )

    print(
        f"Total Exposure          : "
        f"{portfolio['total_exposure']:,.2f}"
    )

    print(
        f"Active Positions       : "
        f"{portfolio['active_positions']}"
    )

    print(
        f"Max Concurrent Positions: "
        f"{portfolio['max_concurrent_positions']}"
    )

    print(
        f"Capital Utilization     : "
        f"{portfolio['capital_utilization'] * 100:.2f}%"
    )

    print(
        f"Unused Capital          : "
        f"{portfolio['unused_capital']:,.2f}"
    )

    print()
    print("=" * 77)
    print("PORTFOLIO RISK ENGINE CONTRACT")
    print("=" * 77)

    print(
        f"Expected Assets : "
        f"{len(EXPECTED_ASSETS)}"
    )

    print(
        f"Position Fields : 8"
    )

    print(
        f"Portfolio State : "
        f"{portfolio['state']}"
    )

    print(
        "Capital Model   : MAXIMUM VALID UTILIZATION"
    )

    print(
        "Unused Capital : ALLOWED"
    )

    print(
        "Forced Exposure : NOT ALLOWED"
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
# MAIN
# ============================================================================

def main():

    print_header()

    try:

        snapshot = (
            calculate_snapshot()
        )

        print_results(
            snapshot
        )

        portfolio_state = snapshot[
            "portfolio"
        ][
            "state"
        ]

        print()

        if portfolio_state == "VALID":

            print(
                "PORTFOLIO RISK ENGINE STATUS : READY"
            )

            return 0

        print(
            "PORTFOLIO RISK ENGINE STATUS : BLOCKED"
        )

        return 1

    except Exception as exc:

        print()
        print("=" * 77)
        print("PORTFOLIO RISK ENGINE ERROR")
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
            "PORTFOLIO RISK ENGINE STATUS : FAILED"
        )

        return 1


if __name__ == "__main__":

    raise SystemExit(
        main()
    )