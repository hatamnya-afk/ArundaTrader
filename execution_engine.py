"""
ARUNDA EXECUTION ENGINE v0.1

Purpose:
    Determine execution eligibility only.

IMPORTANT:
    This engine DOES NOT execute orders.

Architecture:

    Decision
        ↓
    Risk
        ↓
    Risk Budget
        ↓
    Stop Loss
        ↓
    Position Sizing
        ↓
    Portfolio Risk
        ↓
    Execution Eligibility

Execution States:

    EXECUTABLE
    BLOCKED
    NOT_READY

Directions:

    LONG
    SHORT
    NONE

Storage:
    MEMORY ONLY

No:
    SQL
    Database
    Exchange
    Bitpin connection
    Binance
    Order creation
    Leverage
    Take Profit
    Prediction
    Ranking
    Interpretation
"""

# ============================================================================
# IMPORTS
# ============================================================================

from execution_contract import (
    EXPECTED_ASSETS,
    EXECUTION_STATES,
    DIRECTIONS,
    validate_execution_record,
    validate_execution_snapshot,
)

import decision_engine
import risk_engine
import risk_budget_engine
import stop_loss_engine
import position_sizing_engine
import portfolio_risk_engine


# ============================================================================
# CONSTANTS
# ============================================================================

EPSILON = 1e-12


# ============================================================================
# GENERIC HELPERS
# ============================================================================

def index_by_asset(data):
    """
    Convert list-based asset records into:

        {
            "BTC": {...},
            "ETH": {...}
        }
    """

    result = {}

    if isinstance(data, dict):

        # Already asset keyed.
        if all(
            isinstance(value, dict)
            for value in data.values()
        ):
            return data

        # Wrapped structures.
        for key in (
            "snapshot",
            "decision_snapshot",
            "risk_snapshot",
            "budget_snapshot",
            "positions",
            "records",
            "data",
        ):

            nested = data.get(key)

            if isinstance(nested, list):

                return index_by_asset(nested)

            if isinstance(nested, dict):

                return index_by_asset(nested)

        return result

    if isinstance(data, list):

        for record in data:

            if not isinstance(record, dict):
                continue

            asset = record.get("asset")

            if asset is None:
                continue

            result[str(asset)] = record

    return result


def get_first(record, names, default=None):
    """
    Return the first existing field from a record.
    """

    if not isinstance(record, dict):
        return default

    for name in names:

        if name in record:

            value = record.get(name)

            if value is not None:
                return value

    return default


def to_float(value):
    """
    Safe float conversion.
    """

    if value is None:
        return None

    try:

        return float(value)

    except (
        TypeError,
        ValueError,
    ):

        return None


def is_positive(value):
    """
    Positive numeric validation.
    """

    value = to_float(value)

    return (
        value is not None
        and value > EPSILON
    )


# ============================================================================
# DECISION
# ============================================================================

def load_decisions():
    """
    Build the real Decision snapshot using the existing
    Decision Engine APIs.

    We intentionally do NOT invent a new
    load_decision_snapshot() API.
    """

    builder = getattr(
        decision_engine,
        "build_decision_snapshot",
        None,
    )

    if not callable(builder):

        raise RuntimeError(
            "decision_engine must expose "
            "build_decision_snapshot()"
        )

    load_signals = getattr(
        decision_engine,
        "load_validated_signals",
        None,
    )

    load_scores = getattr(
        decision_engine,
        "load_scores",
        None,
    )

    if not callable(load_signals):

        raise RuntimeError(
            "decision_engine must expose "
            "load_validated_signals()"
        )

    if not callable(load_scores):

        raise RuntimeError(
            "decision_engine must expose "
            "load_scores()"
        )

    signals = load_signals()
    scores = load_scores()

    snapshot = builder(
        signals,
        scores,
    )

    if not isinstance(snapshot, dict):

        snapshot = index_by_asset(snapshot)

    if not isinstance(snapshot, dict):

        raise RuntimeError(
            "Decision snapshot must be a dictionary"
        )

    return snapshot


# ============================================================================
# RISK
# ============================================================================

def load_risks(decisions):
    """
    Build Risk snapshot from the real Risk Engine.

    Real API:

        risk_engine.build_risk_snapshot(decisions)
    """

    builder = getattr(
        risk_engine,
        "build_risk_snapshot",
        None,
    )

    if not callable(builder):

        raise RuntimeError(
            "risk_engine must expose "
            "build_risk_snapshot()"
        )

    snapshot = builder(
        decisions
    )

    if not isinstance(snapshot, dict):

        snapshot = index_by_asset(snapshot)

    if not isinstance(snapshot, dict):

        raise RuntimeError(
            "Risk snapshot must be a dictionary"
        )

    return snapshot


# ============================================================================
# RISK BUDGET
# ============================================================================

def load_risk_budgets():
    """
    Load the real Risk Budget snapshot.

    Real API:

        risk_budget_engine.load_risk_snapshot()
    """

    loader = getattr(
        risk_budget_engine,
        "load_risk_snapshot",
        None,
    )

    if not callable(loader):

        raise RuntimeError(
            "risk_budget_engine must expose "
            "load_risk_snapshot()"
        )

    snapshot = loader()

    if not isinstance(snapshot, dict):

        snapshot = index_by_asset(snapshot)

    if not isinstance(snapshot, dict):

        raise RuntimeError(
            "Risk Budget snapshot must be a dictionary"
        )

    return snapshot


# ============================================================================
# STOP LOSS
# ============================================================================

def load_stops():
    """
    Load the real Stop Loss snapshot.

    Real API:

        stop_loss_engine.calculate_snapshot()

    Current known structure:
        list of records.
    """

    loader = getattr(
        stop_loss_engine,
        "calculate_snapshot",
        None,
    )

    if not callable(loader):

        raise RuntimeError(
            "stop_loss_engine must expose "
            "calculate_snapshot()"
        )

    snapshot = loader()

    return index_by_asset(snapshot)


# ============================================================================
# POSITION SIZING
# ============================================================================

def load_positions():
    """
    Load the real Position Sizing snapshot.

    Real API:

        position_sizing_engine.calculate_snapshot()

    Important:
        NO positional argument is passed.
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

    if not isinstance(snapshot, dict):

        raise RuntimeError(
            "Position Sizing snapshot must be a dictionary"
        )

    positions = snapshot.get(
        "positions"
    )

    if not isinstance(
        positions,
        list,
    ):

        raise RuntimeError(
            "Position Sizing snapshot must contain "
            "a positions list"
        )

    return index_by_asset(
        positions
    )


# ============================================================================
# PORTFOLIO RISK
# ============================================================================

def load_portfolio_risk():
    """
    Load the real Portfolio Risk snapshot.

    IMPORTANT:

        portfolio_risk_engine.calculate_snapshot()

    takes ZERO arguments.

    The Portfolio Risk Engine itself loads
    Position Sizing internally.
    """

    loader = getattr(
        portfolio_risk_engine,
        "calculate_snapshot",
        None,
    )

    if not callable(loader):

        raise RuntimeError(
            "portfolio_risk_engine must expose "
            "calculate_snapshot()"
        )

    snapshot = loader()

    if not isinstance(snapshot, dict):

        raise RuntimeError(
            "Portfolio Risk snapshot must be a dictionary"
        )

    return snapshot


# ============================================================================
# PORTFOLIO STATE
# ============================================================================

def portfolio_is_valid(
    portfolio_snapshot,
):
    """
    Determine whether Portfolio Risk is valid.
    """

    if not isinstance(
        portfolio_snapshot,
        dict,
    ):

        return False

    portfolio = portfolio_snapshot.get(
        "portfolio"
    )

    if not isinstance(
        portfolio,
        dict,
    ):

        return False

    state = portfolio.get(
        "state"
    )

    return state == "VALID"


# ============================================================================
# FIELD EXTRACTION
# ============================================================================

def extract_entry(
    decision,
    stop,
    position,
):
    """
    Entry price may originate from the downstream
    structural layers.

    No price is invented.
    """

    value = get_first(
        position,
        (
            "entry_price",
            "entry",
        ),
    )

    if value is not None:
        return value

    value = get_first(
        stop,
        (
            "entry_price",
            "entry",
        ),
    )

    if value is not None:
        return value

    return get_first(
        decision,
        (
            "entry_price",
            "entry",
        ),
    )


def extract_stop(
    stop,
    position,
):
    """
    Stop price extraction.
    """

    value = get_first(
        position,
        (
            "stop_price",
            "stop",
        ),
    )

    if value is not None:
        return value

    return get_first(
        stop,
        (
            "stop_price",
            "stop",
        ),
    )


def extract_stop_distance(
    stop,
    position,
):
    """
    Stop distance extraction.
    """

    value = get_first(
        position,
        (
            "stop_distance",
            "distance",
        ),
    )

    if value is not None:
        return value

    return get_first(
        stop,
        (
            "stop_distance",
            "distance",
        ),
    )


def extract_position_size(
    position,
):
    """
    Position size extraction.
    """

    return get_first(
        position,
        (
            "position_size",
            "size",
            "quantity",
        ),
    )


def extract_exposure(
    position,
):
    """
    Exposure extraction.
    """

    return get_first(
        position,
        (
            "exposure",
            "position_exposure",
        ),
    )


# ============================================================================
# EXECUTION RECORD
# ============================================================================

def build_execution_record(
    asset,
    decision,
    risk,
    budget,
    stop,
    position,
    portfolio_valid,
):
    """
    Build exactly one Execution Eligibility record.

    Required contract fields:

        asset
        direction
        state
        entry_price
        stop_price
        stop_distance
        position_size
        exposure
    """

    decision_state = get_first(
        decision,
        (
            "state",
            "decision_state",
        ),
    )

    direction = get_first(
        decision,
        (
            "direction",
        ),
        "NONE",
    )

    if direction not in DIRECTIONS:
        direction = "NONE"

    risk_state = get_first(
        risk,
        (
            "risk_state",
            "state",
        ),
    )

    budget_state = get_first(
        budget,
        (
            "budget_state",
            "state",
        ),
    )

    position_state = get_first(
        position,
        (
            "state",
            "position_state",
        ),
    )

    entry_price = extract_entry(
        decision,
        stop,
        position,
    )

    stop_price = extract_stop(
        stop,
        position,
    )

    stop_distance = extract_stop_distance(
        stop,
        position,
    )

    position_size = extract_position_size(
        position
    )

    exposure = extract_exposure(
        position
    )

    # ------------------------------------------------------------------------
    # DECISION
    # ------------------------------------------------------------------------

    if decision_state != "ACTIONABLE":

        return {
            "asset": asset,
            "direction": direction,
            "state": "NOT_READY",
            "entry_price": None,
            "stop_price": None,
            "stop_distance": None,
            "position_size": 0.0,
            "exposure": 0.0,
            "reason": "DECISION_NOT_ACTIONABLE",
        }

    # ------------------------------------------------------------------------
    # RISK
    # ------------------------------------------------------------------------

    if risk_state != "APPROVED":

        return {
            "asset": asset,
            "direction": direction,
            "state": "BLOCKED",
            "entry_price": entry_price,
            "stop_price": stop_price,
            "stop_distance": stop_distance,
            "position_size": 0.0,
            "exposure": 0.0,
            "reason": "RISK_NOT_APPROVED",
        }

    # ------------------------------------------------------------------------
    # RISK BUDGET
    # ------------------------------------------------------------------------

    if budget_state != "ALLOCATED":

        return {
            "asset": asset,
            "direction": direction,
            "state": "NOT_READY",
            "entry_price": entry_price,
            "stop_price": stop_price,
            "stop_distance": stop_distance,
            "position_size": 0.0,
            "exposure": 0.0,
            "reason": "RISK_BUDGET_NOT_ALLOCATED",
        }

    # ------------------------------------------------------------------------
    # STOP
    # ------------------------------------------------------------------------

    if not is_positive(
        stop_distance
    ):

        return {
            "asset": asset,
            "direction": direction,
            "state": "NOT_READY",
            "entry_price": entry_price,
            "stop_price": stop_price,
            "stop_distance": stop_distance,
            "position_size": 0.0,
            "exposure": 0.0,
            "reason": "STOP_NOT_CALCULATED",
        }

    if not is_positive(
        entry_price
    ):

        return {
            "asset": asset,
            "direction": direction,
            "state": "NOT_READY",
            "entry_price": None,
            "stop_price": stop_price,
            "stop_distance": stop_distance,
            "position_size": 0.0,
            "exposure": 0.0,
            "reason": "INPUT_INCOMPLETE",
        }

    # ------------------------------------------------------------------------
    # POSITION
    # ------------------------------------------------------------------------

    if (
        position_state != "CALCULATED"
        or not is_positive(position_size)
    ):

        return {
            "asset": asset,
            "direction": direction,
            "state": "NOT_READY",
            "entry_price": entry_price,
            "stop_price": stop_price,
            "stop_distance": stop_distance,
            "position_size": 0.0,
            "exposure": 0.0,
            "reason": "POSITION_NOT_CALCULATED",
        }

    if not is_positive(
        exposure
    ):

        return {
            "asset": asset,
            "direction": direction,
            "state": "NOT_READY",
            "entry_price": entry_price,
            "stop_price": stop_price,
            "stop_distance": stop_distance,
            "position_size": position_size,
            "exposure": 0.0,
            "reason": "INPUT_INCOMPLETE",
        }

    # ------------------------------------------------------------------------
    # PORTFOLIO
    # ------------------------------------------------------------------------

    if not portfolio_valid:

        return {
            "asset": asset,
            "direction": direction,
            "state": "BLOCKED",
            "entry_price": entry_price,
            "stop_price": stop_price,
            "stop_distance": stop_distance,
            "position_size": position_size,
            "exposure": exposure,
            "reason": "PORTFOLIO_BLOCKED",
        }

    # ------------------------------------------------------------------------
    # EXECUTABLE
    # ------------------------------------------------------------------------

    return {
        "asset": asset,
        "direction": direction,
        "state": "EXECUTABLE",
        "entry_price": entry_price,
        "stop_price": stop_price,
        "stop_distance": stop_distance,
        "position_size": position_size,
        "exposure": exposure,
        "reason": "PORTFOLIO_VALID",
    }


# ============================================================================
# SNAPSHOT
# ============================================================================

def calculate_snapshot():
    """
    Calculate complete Execution Eligibility snapshot.

    IMPORTANT:

        RETURNS A LIST.

    This is required by execution_contract.py.
    """

    # ------------------------------------------------------------------------
    # INPUTS
    # ------------------------------------------------------------------------

    decisions = load_decisions()

    risks = load_risks(
        decisions
    )

    budgets = load_risk_budgets()

    stops = load_stops()

    positions = load_positions()

    portfolio = load_portfolio_risk()

    portfolio_valid = portfolio_is_valid(
        portfolio
    )

    # ------------------------------------------------------------------------
    # BUILD
    # ------------------------------------------------------------------------

    snapshot = []

    for asset in EXPECTED_ASSETS:

        decision = decisions.get(
            asset,
            {},
        )

        risk = risks.get(
            asset,
            {},
        )

        budget = budgets.get(
            asset,
            {},
        )

        stop = stops.get(
            asset,
            {},
        )

        position = positions.get(
            asset,
            {},
        )

        record = build_execution_record(
            asset=asset,
            decision=decision,
            risk=risk,
            budget=budget,
            stop=stop,
            position=position,
            portfolio_valid=portfolio_valid,
        )

        snapshot.append(
            record
        )

    return snapshot


# ============================================================================
# VALIDATION
# ============================================================================

def validate_snapshot(
    snapshot,
):
    """
    Validate complete execution snapshot
    against execution_contract.py.
    """

    if not isinstance(
        snapshot,
        list,
    ):

        raise RuntimeError(
            "Execution snapshot must be a list"
        )

    return validate_execution_snapshot(
        snapshot
    )


# ============================================================================
# PRINT HEADER
# ============================================================================

def print_header():

    print("=" * 77)
    print("ARUNDA EXECUTION ENGINE v0.1")
    print("=" * 77)

    print(
        "Source          : "
        "decision + risk + budget + stop + sizing + portfolio"
    )

    print(
        "Purpose         : EXECUTION ELIGIBILITY"
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
        "Storage         : MEMORY ONLY"
    )

    print(
        "Writes          : NONE"
    )

    print(
        "SQL             : NOT USED"
    )

    print(
        "Database        : NOT USED"
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

    print("=" * 77)


# ============================================================================
# PRINT RESULTS
# ============================================================================

def print_results(
    snapshot,
):

    print()
    print("=" * 77)
    print("EXECUTION ELIGIBILITY SNAPSHOT")
    print("=" * 77)

    print(
        "Asset  | Direction | State        | "
        "Entry Price | Stop Price | Position Size | Exposure | Reason"
    )

    print("-" * 77)

    for record in snapshot:

        asset = record["asset"]

        direction = record["direction"]

        state = record["state"]

        entry = record["entry_price"]

        stop = record["stop_price"]

        size = record["position_size"]

        exposure = record["exposure"]

        reason = record["reason"]

        if entry is None:
            entry_text = "NONE"
        else:
            entry_text = f"{float(entry):,.2f}"

        if stop is None:
            stop_text = "NONE"
        else:
            stop_text = f"{float(stop):,.2f}"

        print(
            f"{asset:<6} | "
            f"{direction:<9} | "
            f"{state:<12} | "
            f"{entry_text:>11} | "
            f"{stop_text:>10} | "
            f"{float(size):>13.8f} | "
            f"{float(exposure):>8.2f} | "
            f"{reason}"
        )


# ============================================================================
# CONTRACT SUMMARY
# ============================================================================

def print_contract(
    snapshot,
):

    executable = sum(
        1
        for record in snapshot
        if record["state"] == "EXECUTABLE"
    )

    blocked = sum(
        1
        for record in snapshot
        if record["state"] == "BLOCKED"
    )

    not_ready = sum(
        1
        for record in snapshot
        if record["state"] == "NOT_READY"
    )

    long_count = sum(
        1
        for record in snapshot
        if record["direction"] == "LONG"
    )

    short_count = sum(
        1
        for record in snapshot
        if record["direction"] == "SHORT"
    )

    none_count = sum(
        1
        for record in snapshot
        if record["direction"] == "NONE"
    )

    print()
    print("=" * 77)
    print("EXECUTION ENGINE CONTRACT")
    print("=" * 77)

    print(
        f"Expected Assets : {len(EXPECTED_ASSETS)}"
    )

    print(
        f"Executable      : {executable}"
    )

    print(
        f"Blocked         : {blocked}"
    )

    print(
        f"Not Ready       : {not_ready}"
    )

    print(
        f"LONG            : {long_count}"
    )

    print(
        f"SHORT           : {short_count}"
    )

    print(
        f"NONE            : {none_count}"
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
        "Storage         : MEMORY ONLY"
    )

    print(
        "Database writes : NONE"
    )

    print(
        "SQL             : NOT USED"
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
        "Contract Status : VALID"
    )

    print("=" * 77)


# ============================================================================
# MAIN
# ============================================================================

def main():

    print_header()

    try:

        snapshot = calculate_snapshot()

        validate_snapshot(
            snapshot
        )

        print_results(
            snapshot
        )

        print_contract(
            snapshot
        )

        print()
        print(
            "EXECUTION ENGINE STATUS : READY"
        )

    except Exception as exc:

        print()
        print("=" * 77)
        print("ARUNDA EXECUTION ENGINE ERROR")
        print("=" * 77)

        print(
            f"Type  : {type(exc).__name__}"
        )

        print(
            f"Error : {exc}"
        )

        print()
        print(
            "EXECUTION ENGINE STATUS : FAILED"
        )

        raise


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()