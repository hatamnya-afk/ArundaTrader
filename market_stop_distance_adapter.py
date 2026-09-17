# ============================================================
# ARUNDA MARKET STOP DISTANCE ADAPTER v0.3
# ============================================================
#
# PURPOSE
#
# Connect REAL market_data
# with EXISTING Risk Budget allocations.
#
# Architecture:
#
#       MARKET DATA
#          |
#          | close + ATR14
#          v
#   MARKET STOP DISTANCE
#        ADAPTER
#          ^
#          |
#        budgets
#          |
#          v
#   ENTRY / STOP CONTRACT
#
# IMPORTANT
#
# This module:
#
#   - READS market_data
#   - READS existing Risk Budget
#   - USES existing direction
#   - USES real market close
#   - USES real ATR14
#   - CALCULATES stop distance only
#
# This module DOES NOT:
#
#   - create Risk
#   - create Decision
#   - rank assets
#   - predict
#   - calculate Risk Budget
#   - calculate Position Size
#   - calculate Stop Price
#   - execute orders
#   - write to database
#
# Formula:
#
#       stop_distance = ATR14 * ATR_MULTIPLIER
#
# Entry:
#
#       entry_price = latest real market close
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import sqlite3
import math


from entry_stop_contract import (
    EXPECTED_ASSETS,
    ENTRY_STOP_STATES,
    DIRECTIONS,
    validate_entry_stop,
    validate_entry_stop_snapshot,
)


import risk_budget_engine


# ============================================================
# CONFIG
# ============================================================

DB = "arunda.db"

ADAPTER_VERSION = (
    "MARKET_STOP_DISTANCE_ADAPTER_v0.3"
)

MARKET_DATA_SOURCE = (
    "CMC_SNAPSHOT_ANALYSIS_v0.2"
)

MARKET_DATA_TIMEFRAME = (
    "SNAPSHOT"
)

ATR_MULTIPLIER = 1.5


# ============================================================
# DATABASE
# ============================================================

def connect_database():

    conn = sqlite3.connect(DB)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# SAFE NUMBER
# ============================================================

def safe_positive_float(
    value,
    field,
    asset,
):

    if value is None:

        raise RuntimeError(
            f"{field} unavailable for {asset}"
        )

    if isinstance(value, bool):

        raise RuntimeError(
            f"Invalid {field} type for {asset}"
        )

    try:

        number = float(value)

    except Exception:

        raise RuntimeError(
            f"Invalid {field} for {asset}: {value!r}"
        )

    if not math.isfinite(number):

        raise RuntimeError(
            f"Non-finite {field} for {asset}"
        )

    if number <= 0:

        raise RuntimeError(
            f"{field} must be greater than zero for {asset}"
        )

    return number


# ============================================================
# MARKET DATA
# ============================================================

def load_latest_market_data(
    conn,
    asset,
):
    """
    Load the latest REAL market analysis
    for one asset.

    Source:
        CMC_SNAPSHOT_ANALYSIS_v0.2

    Timeframe:
        SNAPSHOT

    Required:
        close
        atr14
    """

    row = conn.execute(
        """
        SELECT
            id,
            timestamp,
            symbol,
            timeframe,
            close,
            atr14,
            source,
            source_timestamp,
            engine_version
        FROM market_data
        WHERE
            symbol = ?
            AND timeframe = ?
            AND source = ?
            AND close IS NOT NULL
            AND atr14 IS NOT NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            asset,
            MARKET_DATA_TIMEFRAME,
            MARKET_DATA_SOURCE,
        ),
    ).fetchone()

    return row


# ============================================================
# STOP DISTANCE
# ============================================================

def calculate_stop_distance(
    atr14,
    multiplier=ATR_MULTIPLIER,
):

    atr_value = float(atr14)

    multiplier_value = float(
        multiplier
    )

    if not math.isfinite(
        atr_value
    ):

        raise RuntimeError(
            "ATR14 must be finite"
        )

    if atr_value <= 0:

        raise RuntimeError(
            "ATR14 must be greater than zero"
        )

    if not math.isfinite(
        multiplier_value
    ):

        raise RuntimeError(
            "ATR multiplier must be finite"
        )

    if multiplier_value <= 0:

        raise RuntimeError(
            "ATR multiplier must be greater than zero"
        )

    return (
        atr_value
        * multiplier_value
    )


# ============================================================
# BUILD UNAVAILABLE RECORD
# ============================================================

def build_unavailable_record(
    asset,
):

    record = {
        "asset": asset,
        "direction": "NONE",
        "state": "UNAVAILABLE",
        "entry_price": None,
        "stop_distance": None,
    }

    validate_entry_stop(
        record
    )

    return record


# ============================================================
# BUILD BLOCKED RECORD
# ============================================================

def build_blocked_record(
    asset,
    direction,
):

    # --------------------------------------------------------
    # Current Entry/Stop Contract requires BLOCKED
    # records to preserve a LONG/SHORT direction.
    #
    # Therefore a BLOCKED record with direction NONE
    # cannot legally enter this contract.
    #
    # We deliberately reject it instead of inventing
    # a trading direction.
    # --------------------------------------------------------

    if direction not in (
        "LONG",
        "SHORT",
    ):

        raise RuntimeError(
            f"BLOCKED budget for {asset} "
            f"has invalid direction: {direction}. "
            f"Current entry_stop_contract requires "
            f"BLOCKED direction LONG or SHORT."
        )

    record = {
        "asset": asset,
        "direction": direction,
        "state": "BLOCKED",
        "entry_price": None,
        "stop_distance": None,
    }

    validate_entry_stop(
        record
    )

    return record


# ============================================================
# BUILD READY RECORD
# ============================================================

def build_ready_record(
    asset,
    direction,
    market_row,
):

    if direction not in (
        "LONG",
        "SHORT",
    ):

        raise RuntimeError(
            f"Invalid allocated direction "
            f"for {asset}: {direction}"
        )

    close = safe_positive_float(
        market_row["close"],
        "close",
        asset,
    )

    atr14 = safe_positive_float(
        market_row["atr14"],
        "ATR14",
        asset,
    )

    stop_distance = (
        calculate_stop_distance(
            atr14,
            ATR_MULTIPLIER,
        )
    )

    record = {
        "asset": asset,
        "direction": direction,
        "state": "READY",
        "entry_price": close,
        "stop_distance": stop_distance,
    }

    validate_entry_stop(
        record
    )

    return record


# ============================================================
# BUILD ONE ASSET
# ============================================================

def build_asset_record(
    conn,
    asset,
    budget_record,
):
    """
    Convert existing Risk Budget information
    plus real market data into Entry/Stop input.

    No decision is created here.
    """

    if not isinstance(
        budget_record,
        dict,
    ):

        raise RuntimeError(
            f"Invalid budget record for {asset}"
        )

    budget_state = budget_record.get(
        "budget_state"
    )

    direction = budget_record.get(
        "direction"
    )

    if budget_state == "ALLOCATED":

        if direction not in (
            "LONG",
            "SHORT",
        ):

            raise RuntimeError(
                f"ALLOCATED budget for {asset} "
                f"has invalid direction: {direction}"
            )

        market_row = (
            load_latest_market_data(
                conn,
                asset,
            )
        )

        if market_row is None:

            return (
                build_unavailable_record(
                    asset
                )
            )

        return build_ready_record(
            asset,
            direction,
            market_row,
        )

    if budget_state == "UNALLOCATED":

        return (
            build_unavailable_record(
                asset
            )
        )

    if budget_state == "BLOCKED":

        return build_blocked_record(
            asset,
            direction,
        )

    raise RuntimeError(
        f"Unknown budget state for "
        f"{asset}: {budget_state}"
    )


# ============================================================
# BUILD SNAPSHOT
# ============================================================

def build_adapter_snapshot(
    budgets,
):

    if not isinstance(
        budgets,
        dict,
    ):

        raise RuntimeError(
            "Budgets must be a dictionary"
        )

    expected = set(
        EXPECTED_ASSETS
    )

    actual = set(
        budgets.keys()
    )

    missing = (
        expected
        - actual
    )

    extra = (
        actual
        - expected
    )

    if missing:

        raise RuntimeError(
            "Risk Budget missing assets: "
            + ", ".join(
                sorted(missing)
            )
        )

    if extra:

        raise RuntimeError(
            "Risk Budget contains unexpected assets: "
            + ", ".join(
                sorted(extra)
            )
        )

    conn = None

    snapshot = {}

    try:

        conn = connect_database()

        for asset in EXPECTED_ASSETS:

            budget_record = budgets[
                asset
            ]

            snapshot[asset] = (
                build_asset_record(
                    conn,
                    asset,
                    budget_record,
                )
            )

    finally:

        if conn is not None:

            conn.close()

    return snapshot


# ============================================================
# VALIDATE SNAPSHOT
# ============================================================

def validate_snapshot(
    snapshot,
):

    result = (
        validate_entry_stop_snapshot(
            snapshot
        )
    )

    if not isinstance(
        result,
        dict,
    ):

        raise RuntimeError(
            "Entry/Stop contract returned "
            "an invalid validation result"
        )

    if result.get(
        "contract_status"
    ) != "VALID":

        raise RuntimeError(
            "Entry/Stop contract validation failed"
        )

    return result


# ============================================================
# LOAD EXISTING RISK BUDGET
# ============================================================

def load_existing_budgets():
    """
    Use the EXISTING Risk Budget Engine.

    No Risk or Decision logic is recreated.
    """

    calculator = getattr(
        risk_budget_engine,
        "calculate_snapshot",
        None,
    )

    if not callable(
        calculator
    ):

        raise RuntimeError(
            "risk_budget_engine.py must expose "
            "calculate_snapshot()"
        )

    snapshot = calculator()

    if not isinstance(
        snapshot,
        dict,
    ):

        raise RuntimeError(
            "Risk Budget snapshot must be a dictionary"
        )

    if "budgets" not in snapshot:

        raise RuntimeError(
            "Risk Budget snapshot missing 'budgets'"
        )

    budgets = snapshot[
        "budgets"
    ]

    if not isinstance(
        budgets,
        dict,
    ):

        raise RuntimeError(
            "'budgets' must be a dictionary"
        )

    return snapshot


# ============================================================
# PRINT HEADER
# ============================================================

def print_header():

    print(
        "=" * 82
    )

    print(
        "ARUNDA MARKET STOP DISTANCE ADAPTER v0.3"
    )

    print(
        "=" * 82
    )

    print(
        f"Source          : {MARKET_DATA_SOURCE}"
    )

    print(
        f"Timeframe       : {MARKET_DATA_TIMEFRAME}"
    )

    print(
        f"ATR Multiplier  : {ATR_MULTIPLIER}"
    )

    print(
        "Close           : REAL MARKET DATA"
    )

    print(
        "ATR14           : REAL MARKET DATA"
    )

    print(
        "Entry Price     : MARKET DATA CLOSE"
    )

    print(
        "Stop Distance   : ATR14 × MULTIPLIER"
    )

    print(
        "Stop Price      : NOT CALCULATED"
    )

    print(
        "Direction       : EXISTING RISK BUDGET"
    )

    print(
        "Risk Budget     : READ ONLY"
    )

    print(
        "Position Sizing : NOT USED"
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
        "Database Reads  : YES"
    )

    print(
        "Database Writes : NONE"
    )

    print(
        "Storage Output  : MEMORY ONLY"
    )

    print(
        "=" * 82
    )


# ============================================================
# PRINT RESULTS
# ============================================================

def print_results(
    snapshot,
):

    print()

    print(
        "MARKET STOP DISTANCE ADAPTER"
    )

    print(
        "-" * 82
    )

    print(
        "Asset | State       | Direction | "
        "Entry Price       | ATR14             | Stop Distance"
    )

    print(
        "-" * 82
    )

    for asset in EXPECTED_ASSETS:

        record = snapshot[
            asset
        ]

        entry = record[
            "entry_price"
        ]

        distance = record[
            "stop_distance"
        ]

        if entry is None:

            entry_text = "NONE"

        else:

            entry_text = (
                f"{entry:,.6f}"
            )

        if distance is None:

            distance_text = "NONE"

        else:

            distance_text = (
                f"{distance:,.6f}"
            )

        # ----------------------------------------------------
        # ATR is displayed only for READY records.
        # It is not part of the Entry/Stop Contract itself.
        # ----------------------------------------------------

        atr_text = "NONE"

        if (
            record["state"]
            == "READY"
        ):

            if entry is not None:

                atr_value = (
                    distance
                    / ATR_MULTIPLIER
                )

                atr_text = (
                    f"{atr_value:,.6f}"
                )

        print(
            f"{asset:<5} | "
            f"{record['state']:<11} | "
            f"{record['direction']:<9} | "
            f"{entry_text:<17} | "
            f"{atr_text:<17} | "
            f"{distance_text}"
        )


# ============================================================
# PRINT CONTRACT
# ============================================================

def print_contract(
    snapshot,
    validation,
):

    ready = sum(
        1
        for record in snapshot.values()
        if record["state"]
        == "READY"
    )

    unavailable = sum(
        1
        for record in snapshot.values()
        if record["state"]
        == "UNAVAILABLE"
    )

    blocked = sum(
        1
        for record in snapshot.values()
        if record["state"]
        == "BLOCKED"
    )

    long_count = sum(
        1
        for record in snapshot.values()
        if record["direction"]
        == "LONG"
    )

    short_count = sum(
        1
        for record in snapshot.values()
        if record["direction"]
        == "SHORT"
    )

    none_count = sum(
        1
        for record in snapshot.values()
        if record["direction"]
        == "NONE"
    )

    print()

    print(
        "=" * 82
    )

    print(
        "MARKET STOP DISTANCE ADAPTER CONTRACT"
    )

    print(
        "=" * 82
    )

    print(
        f"Expected Assets : "
        f"{len(EXPECTED_ASSETS)}"
    )

    print(
        f"Validated       : "
        f"{validation['validated_assets']}"
    )

    print(
        f"READY           : "
        f"{ready}"
    )

    print(
        f"UNAVAILABLE     : "
        f"{unavailable}"
    )

    print(
        f"BLOCKED         : "
        f"{blocked}"
    )

    print(
        f"LONG            : "
        f"{long_count}"
    )

    print(
        f"SHORT           : "
        f"{short_count}"
    )

    print(
        f"NONE            : "
        f"{none_count}"
    )

    print(
        f"ATR Multiplier  : "
        f"{ATR_MULTIPLIER}"
    )

    print(
        "Close           : REAL MARKET DATA"
    )

    print(
        "ATR14           : REAL MARKET DATA"
    )

    print(
        "Entry Price     : MARKET DATA CLOSE"
    )

    print(
        "Stop Distance   : ATR14 × MULTIPLIER"
    )

    print(
        "Stop Price      : NOT CALCULATED"
    )

    print(
        "Risk Budget     : EXISTING INPUT"
    )

    print(
        "Position Sizing : NOT USED"
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
        "Database Reads  : YES"
    )

    print(
        "Database Writes : NONE"
    )

    print(
        "Storage         : MEMORY ONLY"
    )

    print(
        "Contract Status : VALID"
    )

    print(
        "=" * 82
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print_header()

    try:

        print()

        print(
            "Loading existing Risk Budget..."
        )

        risk_snapshot = (
            load_existing_budgets()
        )

        budgets = risk_snapshot[
            "budgets"
        ]

        print(
            "Risk Budget Source : "
            "risk_budget_engine.calculate_snapshot()"
        )

        print()

        print(
            "Reading real market_data..."
        )

        snapshot = (
            build_adapter_snapshot(
                budgets
            )
        )

        validation = (
            validate_snapshot(
                snapshot
            )
        )

        print_results(
            snapshot
        )

        print_contract(
            snapshot,
            validation
        )

        print()

        print(
            "MARKET STOP DISTANCE ADAPTER STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()

        print(
            "=" * 82
        )

        print(
            "MARKET STOP DISTANCE ADAPTER ERROR"
        )

        print(
            "=" * 82
        )

        print(
            f"Type  : {type(exc).__name__}"
        )

        print(
            f"Error : {exc}"
        )

        print()

        print(
            "MARKET STOP DISTANCE ADAPTER STATUS : FAILED"
        )

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )

