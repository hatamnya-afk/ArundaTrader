"""
ARUNDA STOP LOSS ENGINE v0.1

Purpose:
    Calculate Stop Loss from Entry / Stop input.

Architecture:

    Entry / Stop Input
          ↓
    Stop Loss Engine
          ↓
    Stop Loss Output

Rules:
    - MEMORY ONLY
    - NO SQL
    - NO DATABASE WRITES
    - NO EXECUTION
    - NO POSITION SIZING
    - NO TAKE PROFIT
    - NO LEVERAGE
    - NO PREDICTION
    - NO RANKING
    - NO INTERPRETATION

Input:
    asset
    direction
    state
    entry_price
    stop_distance

Output:
    asset
    direction
    state
    entry_price
    stop_price
    stop_distance
"""

from entry_stop_contract import (
    EXPECTED_ASSETS,
    ENTRY_STOP_STATES,
    DIRECTIONS,
    validate_entry_stop_snapshot,
)


# ============================================================================
# STOP LOSS STATES
# ============================================================================

STOP_LOSS_STATES = (
    "CALCULATED",
    "UNAVAILABLE",
    "BLOCKED",
)


# ============================================================================
# BUILD ONE STOP LOSS RECORD
# ============================================================================

def calculate_stop_loss(record):
    """
    Calculate one Stop Loss record.

    LONG:
        stop_price = entry_price - stop_distance

    SHORT:
        stop_price = entry_price + stop_distance

    No risk or position calculation occurs here.
    """

    if not isinstance(record, dict):
        raise RuntimeError(
            "Entry / Stop record must be a dictionary"
        )

    asset = record.get("asset")
    direction = record.get("direction")
    state = record.get("state")
    entry_price = record.get("entry_price")
    stop_distance = record.get("stop_distance")

    if asset not in EXPECTED_ASSETS:
        raise RuntimeError(
            f"Unknown asset: {asset}"
        )

    if direction not in DIRECTIONS:
        raise RuntimeError(
            f"Invalid direction for {asset}: {direction}"
        )

    if state not in ENTRY_STOP_STATES:
        raise RuntimeError(
            f"Invalid Entry / Stop state for {asset}: {state}"
        )

    # ------------------------------------------------------------------------
    # UNAVAILABLE
    # ------------------------------------------------------------------------

    if state == "UNAVAILABLE":

        return {
            "asset": asset,
            "direction": "NONE",
            "state": "UNAVAILABLE",
            "entry_price": None,
            "stop_price": None,
            "stop_distance": None,
        }

    # ------------------------------------------------------------------------
    # BLOCKED
    # ------------------------------------------------------------------------

    if state == "BLOCKED":

        return {
            "asset": asset,
            "direction": direction,
            "state": "BLOCKED",
            "entry_price": entry_price,
            "stop_price": None,
            "stop_distance": stop_distance,
        }

    # ------------------------------------------------------------------------
    # READY
    # ------------------------------------------------------------------------

    if state == "READY":

        if direction not in ("LONG", "SHORT"):
            raise RuntimeError(
                f"READY Stop Loss record requires "
                f"LONG or SHORT for {asset}"
            )

        if entry_price is None:
            raise RuntimeError(
                f"Missing entry_price for {asset}"
            )

        if stop_distance is None:
            raise RuntimeError(
                f"Missing stop_distance for {asset}"
            )

        if isinstance(entry_price, bool):
            raise RuntimeError(
                f"Invalid entry_price for {asset}"
            )

        if isinstance(stop_distance, bool):
            raise RuntimeError(
                f"Invalid stop_distance for {asset}"
            )

        if not isinstance(entry_price, (int, float)):
            raise RuntimeError(
                f"Invalid entry_price for {asset}"
            )

        if not isinstance(stop_distance, (int, float)):
            raise RuntimeError(
                f"Invalid stop_distance for {asset}"
            )

        if entry_price <= 0:
            raise RuntimeError(
                f"entry_price must be greater than zero for {asset}"
            )

        if stop_distance <= 0:
            raise RuntimeError(
                f"stop_distance must be greater than zero for {asset}"
            )

        if direction == "LONG":

            stop_price = (
                entry_price
                - stop_distance
            )

        else:

            stop_price = (
                entry_price
                + stop_distance
            )

        if stop_price <= 0:

            return {
                "asset": asset,
                "direction": direction,
                "state": "BLOCKED",
                "entry_price": entry_price,
                "stop_price": None,
                "stop_distance": stop_distance,
            }

        return {
            "asset": asset,
            "direction": direction,
            "state": "CALCULATED",
            "entry_price": float(entry_price),
            "stop_price": float(stop_price),
            "stop_distance": float(stop_distance),
        }

    raise RuntimeError(
        f"Unsupported Entry / Stop state for {asset}: {state}"
    )


# ============================================================================
# BUILD COMPLETE SNAPSHOT
# ============================================================================

def build_stop_loss_snapshot(entry_stop_snapshot):
    """
    Convert complete Entry / Stop snapshot
    into complete Stop Loss snapshot.
    """

    if not isinstance(entry_stop_snapshot, dict):
        raise RuntimeError(
            "Entry / Stop snapshot must be a dictionary"
        )

    # Validate the input against the real contract.
    validate_entry_stop_snapshot(
        entry_stop_snapshot
    )

    snapshot = {}

    for asset in EXPECTED_ASSETS:

        snapshot[asset] = calculate_stop_loss(
            entry_stop_snapshot[asset]
        )

    return snapshot


# ============================================================================
# VALIDATE STOP LOSS SNAPSHOT
# ============================================================================

def validate_stop_loss_snapshot(snapshot):
    """
    Structural validation of generated Stop Loss snapshot.
    """

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
            "Stop Loss snapshot missing assets: "
            + ", ".join(sorted(missing))
        )

    if extra:
        raise RuntimeError(
            "Stop Loss snapshot contains unexpected assets: "
            + ", ".join(sorted(extra))
        )

    for asset in EXPECTED_ASSETS:

        record = snapshot[asset]

        if not isinstance(record, dict):
            raise RuntimeError(
                f"Invalid Stop Loss record for {asset}"
            )

        required_fields = (
            "asset",
            "direction",
            "state",
            "entry_price",
            "stop_price",
            "stop_distance",
        )

        for field in required_fields:

            if field not in record:
                raise RuntimeError(
                    f"Missing Stop Loss field "
                    f"{field} for {asset}"
                )

        if record["asset"] != asset:
            raise RuntimeError(
                f"Asset key mismatch: {asset}"
            )

        if record["direction"] not in DIRECTIONS:
            raise RuntimeError(
                f"Invalid Stop Loss direction for {asset}"
            )

        if record["state"] not in STOP_LOSS_STATES:
            raise RuntimeError(
                f"Invalid Stop Loss state for {asset}"
            )

        state = record["state"]

        if state == "UNAVAILABLE":

            if record["direction"] != "NONE":
                raise RuntimeError(
                    f"UNAVAILABLE Stop Loss must have "
                    f"direction NONE for {asset}"
                )

            if record["stop_price"] is not None:
                raise RuntimeError(
                    f"UNAVAILABLE Stop Loss must have "
                    f"stop_price NONE for {asset}"
                )

        elif state == "CALCULATED":

            if record["direction"] not in (
                "LONG",
                "SHORT",
            ):
                raise RuntimeError(
                    f"CALCULATED Stop Loss requires "
                    f"LONG or SHORT for {asset}"
                )

            if record["entry_price"] is None:
                raise RuntimeError(
                    f"CALCULATED Stop Loss missing "
                    f"entry_price for {asset}"
                )

            if record["stop_price"] is None:
                raise RuntimeError(
                    f"CALCULATED Stop Loss missing "
                    f"stop_price for {asset}"
                )

            if record["stop_distance"] is None:
                raise RuntimeError(
                    f"CALCULATED Stop Loss missing "
                    f"stop_distance for {asset}"
                )

            if record["entry_price"] <= 0:
                raise RuntimeError(
                    f"Invalid entry_price for {asset}"
                )

            if record["stop_price"] <= 0:
                raise RuntimeError(
                    f"Invalid stop_price for {asset}"
                )

            if record["stop_distance"] <= 0:
                raise RuntimeError(
                    f"Invalid stop_distance for {asset}"
                )

        elif state == "BLOCKED":

            if record["direction"] == "NONE":
                raise RuntimeError(
                    f"BLOCKED Stop Loss must preserve "
                    f"LONG or SHORT for {asset}"
                )

    return True


# ============================================================================
# SELF TEST
# ============================================================================

def self_test():

    # ------------------------------------------------------------------------
    # LONG
    # ------------------------------------------------------------------------

    long_record = {
        "asset": "UNI",
        "direction": "LONG",
        "state": "READY",
        "entry_price": 100.0,
        "stop_distance": 5.0,
    }

    long_result = calculate_stop_loss(
        long_record
    )

    if long_result["state"] != "CALCULATED":
        raise RuntimeError(
            "LONG calculation failed"
        )

    if long_result["stop_price"] != 95.0:
        raise RuntimeError(
            "LONG stop price calculation failed"
        )

    # ------------------------------------------------------------------------
    # SHORT
    # ------------------------------------------------------------------------

    short_record = {
        "asset": "NEAR",
        "direction": "SHORT",
        "state": "READY",
        "entry_price": 10.0,
        "stop_distance": 0.5,
    }

    short_result = calculate_stop_loss(
        short_record
    )

    if short_result["state"] != "CALCULATED":
        raise RuntimeError(
            "SHORT calculation failed"
        )

    if short_result["stop_price"] != 10.5:
        raise RuntimeError(
            "SHORT stop price calculation failed"
        )

    # ------------------------------------------------------------------------
    # UNAVAILABLE
    # ------------------------------------------------------------------------

    empty_record = {
        "asset": "BTC",
        "direction": "NONE",
        "state": "UNAVAILABLE",
        "entry_price": None,
        "stop_distance": None,
    }

    empty_result = calculate_stop_loss(
        empty_record
    )

    if empty_result["state"] != "UNAVAILABLE":
        raise RuntimeError(
            "UNAVAILABLE calculation failed"
        )

    # ------------------------------------------------------------------------
    # COMPLETE SNAPSHOT
    # ------------------------------------------------------------------------

    snapshot = {
        asset: {
            "asset": asset,
            "direction": "NONE",
            "state": "UNAVAILABLE",
            "entry_price": None,
            "stop_distance": None,
        }
        for asset in EXPECTED_ASSETS
    }

    snapshot["UNI"] = long_record
    snapshot["NEAR"] = short_record

    result = build_stop_loss_snapshot(
        snapshot
    )

    validate_stop_loss_snapshot(
        result
    )

    if result["UNI"]["stop_price"] != 95.0:
        raise RuntimeError(
            "Snapshot LONG test failed"
        )

    if result["NEAR"]["stop_price"] != 10.5:
        raise RuntimeError(
            "Snapshot SHORT test failed"
        )

    return True


# ============================================================================
# PRINT HEADER
# ============================================================================

def print_header():

    print("=" * 77)
    print("ARUNDA STOP LOSS ENGINE v0.1")
    print("=" * 77)
    print("Source          : entry_stop_contract")
    print("Purpose         : STOP LOSS CALCULATION")
    print("Storage         : MEMORY ONLY")
    print("Writes          : NONE")
    print("SQL             : NOT USED")
    print("Entry           : INPUT")
    print("Stop Distance   : INPUT")
    print("Stop Price      : CALCULATED")
    print("Risk Budget     : NOT USED")
    print("Position Sizing : NOT USED")
    print("Exposure        : NOT USED")
    print("Execution       : NOT USED")
    print("Prediction      : NOT USED")
    print("Ranking         : NOT USED")
    print("Interpretation  : NOT USED")
    print("=" * 77)


# ============================================================================
# MAIN
# ============================================================================

def main():

    print_header()

    try:

        self_test()

        print()
        print("=" * 77)
        print("STOP LOSS SELF TEST")
        print("=" * 77)

        print(
            "UNI LONG  : Entry 100.00 | "
            "Distance 5.00 | Stop 95.00"
        )

        print(
            "NEAR SHORT: Entry 10.00 | "
            "Distance 0.50 | Stop 10.50"
        )

        print(
            "UNAVAILABLE: VALID"
        )

        print()
        print(
            "STOP LOSS ENGINE STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()
        print("=" * 77)
        print("ARUNDA STOP LOSS ENGINE ERROR")
        print("=" * 77)

        print(
            f"Type  : {type(exc).__name__}"
        )

        print(
            f"Error : {exc}"
        )

        print()

        print(
            "STOP LOSS ENGINE STATUS : FAILED"
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
