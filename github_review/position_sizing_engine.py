"""
ARUNDA POSITION SIZING ENGINE v0.6

Purpose:
    Convert allocated Risk Budget + Stop Loss
    into structural Position Size and Exposure.

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

Formula:

    Risk Amount =
        Capital × Risk Per Trade

    Position Size =
        Risk Amount / Stop Distance

    Exposure =
        Position Size × Entry Price

IMPORTANT:

    MEMORY ONLY
    NO SQL
    NO DATABASE WRITES
    NO EXCHANGE CONNECTION
    BITPIN = FUTURE EXECUTION

NOT INCLUDED:

    Leverage
    Take Profit
    Execution
    Prediction
    Ranking
    Interpretation
"""


# ============================================================================
# IMPORTS
# ============================================================================

from position_sizing_contract import (
    EXPECTED_ASSETS,
    DIRECTIONS,
    SIZING_STATES,
    POSITION_SIZING_FIELDS,
    validate_position_sizing,
    validate_snapshot as contract_validate_snapshot,
)

import capital_config
import risk_budget_engine
import stop_loss_engine


# ============================================================================
# CONSTANTS
# ============================================================================

EPSILON = 1e-12


# ============================================================================
# CAPITAL
# ============================================================================

def load_capital_config():
    """
    Load existing capital configuration.
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

    required_fields = [
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
        for field in required_fields
    ):

        return {
            field: getattr(
                capital_config,
                field,
            )
            for field in required_fields
        }

    raise RuntimeError(
        "capital_config does not expose "
        "a supported configuration API"
    )


# ============================================================================
# RISK BUDGET
# ============================================================================

def load_risk_budgets():
    """
    Load the REAL Risk Budget snapshot.

    Expected structure:

        {
            "BTC": {...},
            "UNI": {
                "budget_state": "ALLOCATED",
                "direction": "LONG",
                ...
            },
            ...
        }
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

    if not isinstance(
        snapshot,
        dict,
    ):

        raise RuntimeError(
            "Risk Budget snapshot must be "
            "a dictionary keyed by asset"
        )

    return snapshot


# ============================================================================
# STOP LOSS
# ============================================================================

def load_stop_losses():
    """
    Load the REAL Stop Loss snapshot.

    Current known API:

        stop_loss_engine.calculate_snapshot()

    The function accepts the current Stop Loss structure
    without modifying the Stop Loss Engine.
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

    if isinstance(snapshot, dict):

        # Wrapped snapshot support.
        for key in (
            "positions",
            "stops",
            "stop_snapshot",
            "snapshot",
            "records",
        ):

            value = snapshot.get(key)

            if isinstance(
                value,
                list,
            ):

                return value

        # Asset keyed dictionary.
        if all(
            isinstance(
                value,
                dict,
            )
            for value in snapshot.values()
        ):

            records = []

            for asset, record in snapshot.items():

                item = dict(record)

                if "asset" not in item:

                    item["asset"] = asset

                records.append(item)

            return records

    if isinstance(
        snapshot,
        list,
    ):

        return snapshot

    raise RuntimeError(
        "Stop Loss snapshot must be "
        "a list or asset-keyed dictionary"
    )


# ============================================================================
# INDEX STOP LOSS
# ============================================================================

def index_stop_losses(snapshot):
    """
    Convert Stop Loss records into:

        {
            "BTC": {...},
            "ETH": {...},
            ...
        }
    """

    result = {}

    for record in snapshot:

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
# GENERIC NUMERIC HELPER
# ============================================================================

def to_float(
    value,
    default=None,
):
    """
    Safe numeric conversion.
    """

    if value is None:

        return default

    if isinstance(
        value,
        bool,
    ):

        return default

    try:

        number = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return default

    if number != number:

        return default

    return number


# ============================================================================
# EXTRACT ENTRY PRICE
# ============================================================================

def extract_entry_price(record):
    """
    Extract Entry Price from Stop Loss record.

    Supported keys are intentionally broad so the Position
    Sizing Engine remains compatible with the existing
    Stop Loss Engine.
    """

    if not isinstance(
        record,
        dict,
    ):

        return None

    keys = [
        "entry_price",
        "entry",
        "current_price",
        "price",
        "market_price",
        "reference_price",
    ]

    for key in keys:

        value = to_float(
            record.get(key)
        )

        if (
            value is not None
            and value > EPSILON
        ):

            return value

    return None


# ============================================================================
# EXTRACT STOP PRICE
# ============================================================================

def extract_stop_price(record):
    """
    Extract Stop Price from Stop Loss record.
    """

    if not isinstance(
        record,
        dict,
    ):

        return None

    keys = [
        "stop_price",
        "stop_loss",
        "stop",
        "sl",
        "stop_loss_price",
    ]

    for key in keys:

        value = to_float(
            record.get(key)
        )

        if (
            value is not None
            and value > EPSILON
        ):

            return value

    return None


# ============================================================================
# EXTRACT STOP DISTANCE
# ============================================================================

def extract_stop_distance(
    record,
    entry_price=None,
    stop_price=None,
):
    """
    Extract absolute Stop Distance.

    Priority:

        1. Explicit stop_distance
        2. Derived from entry_price - stop_price

    Direction-independent absolute distance is used.
    """

    if not isinstance(
        record,
        dict,
    ):

        return None

    explicit_keys = [
        "stop_distance",
        "distance",
        "stop_loss_distance",
        "absolute_stop_distance",
    ]

    for key in explicit_keys:

        value = to_float(
            record.get(key)
        )

        if (
            value is not None
            and value > EPSILON
        ):

            return abs(
                value
            )

    if (
        entry_price is not None
        and stop_price is not None
    ):

        distance = abs(
            entry_price
            - stop_price
        )

        if distance > EPSILON:

            return distance

    return None


# ============================================================================
# RISK AMOUNT
# ============================================================================

def calculate_risk_amount(
    capital,
):
    """
    Risk Amount:

        Capital × Risk Per Trade

    Example:

        1,000,000 × 0.005
        =
        5,000
    """

    if not isinstance(
        capital,
        dict,
    ):

        raise RuntimeError(
            "Capital configuration must be a dictionary"
        )

    capital_value = to_float(
        capital.get(
            "capital"
        )
    )

    risk_per_trade = to_float(
        capital.get(
            "risk_per_trade"
        )
    )

    if (
        capital_value is None
        or capital_value <= 0
    ):

        raise RuntimeError(
            "Invalid capital value"
        )

    if (
        risk_per_trade is None
        or risk_per_trade < 0
    ):

        raise RuntimeError(
            "Invalid risk_per_trade value"
        )

    return (
        capital_value
        * risk_per_trade
    )


# ============================================================================
# EXTRACT RISK BUDGET STATE
# ============================================================================

def extract_budget_state(
    record,
):
    """
    Return formal Risk Budget state.
    """

    if not isinstance(
        record,
        dict,
    ):

        return None

    return record.get(
        "budget_state"
    )


# ============================================================================
# EXTRACT DIRECTION
# ============================================================================

def extract_direction(
    record,
):
    """
    Return LONG / SHORT / NONE.
    """

    if not isinstance(
        record,
        dict,
    ):

        return "NONE"

    direction = record.get(
        "direction"
    )

    if direction in (
        "LONG",
        "SHORT",
        "NONE",
    ):

        return direction

    return "NONE"


# ============================================================================
# EXTRACT ALLOCATED RISK BUDGET
# ============================================================================

def extract_risk_budget(
    budget_record,
    risk_amount,
):
    """
    Risk Budget Engine v0.1 intentionally does not calculate
    a monetary budget.

    It only declares:

        ALLOCATED

    Therefore the Position Sizing Engine converts an
    ALLOCATED budget into the configured per-trade
    Risk Amount.

    This is the actual Risk Budget → Position Sizing bridge.
    """

    if not isinstance(
        budget_record,
        dict,
    ):

        return None

    budget_state = extract_budget_state(
        budget_record
    )

    if budget_state != "ALLOCATED":

        return None

    if (
        risk_amount is None
        or risk_amount <= 0
    ):

        return None

    return float(
        risk_amount
    )


# ============================================================================
# CALCULATE POSITION SIZE
# ============================================================================

def calculate_position_size(
    risk_budget,
    stop_distance,
):
    """
    Position Size:

        Risk Budget / Stop Distance
    """

    risk_budget = to_float(
        risk_budget
    )

    stop_distance = to_float(
        stop_distance
    )

    if (
        risk_budget is None
        or risk_budget <= EPSILON
    ):

        return None

    if (
        stop_distance is None
        or stop_distance <= EPSILON
    ):

        return None

    return (
        risk_budget
        / stop_distance
    )


# ============================================================================
# CALCULATE EXPOSURE
# ============================================================================

def calculate_exposure(
    position_size,
    entry_price,
):
    """
    Exposure:

        Position Size × Entry Price
    """

    position_size = to_float(
        position_size
    )

    entry_price = to_float(
        entry_price
    )

    if (
        position_size is None
        or position_size <= EPSILON
    ):

        return None

    if (
        entry_price is None
        or entry_price <= EPSILON
    ):

        return None

    return (
        position_size
        * entry_price
    )


# ============================================================================
# BUILD UNCALCULATED RECORD
# ============================================================================

def build_uncalculated_record(
    asset,
):
    """
    Build a structurally valid UNCALCULATED record.

    Contract requirement:

        UNCALCULATED → direction NONE
    """

    return {
        "asset": asset,
        "direction": "NONE",
        "state": "UNCALCULATED",
        "risk_budget": None,
        "entry_price": None,
        "stop_distance": None,
        "position_size": 0.0,
        "exposure": 0.0,
    }


# ============================================================================
# BUILD BLOCKED RECORD
# ============================================================================

def build_blocked_record(
    asset,
    direction,
    risk_budget=None,
    entry_price=None,
    stop_distance=None,
):
    """
    Build a structurally valid BLOCKED record.

    Contract requirement:

        BLOCKED → LONG / SHORT
    """

    if direction not in (
        "LONG",
        "SHORT",
    ):

        direction = "LONG"

    return {
        "asset": asset,
        "direction": direction,
        "state": "BLOCKED",
        "risk_budget": risk_budget,
        "entry_price": entry_price,
        "stop_distance": stop_distance,
        "position_size": 0.0,
        "exposure": 0.0,
    }


# ============================================================================
# BUILD CALCULATED RECORD
# ============================================================================

def build_calculated_record(
    asset,
    direction,
    risk_budget,
    entry_price,
    stop_distance,
):
    """
    Calculate and build one valid Position Sizing record.
    """

    position_size = calculate_position_size(
        risk_budget,
        stop_distance,
    )

    if position_size is None:

        return build_uncalculated_record(
            asset
        )

    exposure = calculate_exposure(
        position_size,
        entry_price,
    )

    if exposure is None:

        return build_uncalculated_record(
            asset
        )

    return {
        "asset": asset,
        "direction": direction,
        "state": "CALCULATED",
        "risk_budget": float(
            risk_budget
        ),
        "entry_price": float(
            entry_price
        ),
        "stop_distance": float(
            stop_distance
        ),
        "position_size": float(
            position_size
        ),
        "exposure": float(
            exposure
        ),
    }


# ============================================================================
# BUILD ONE POSITION
# ============================================================================

def build_runtime_position_record(
    asset,
    direction,
    risk_budget,
    entry_price,
    stop_distance,
    snapshot_id,
):
    """
    Build one runtime position record from the CURRENT production runtime
    values only.

    Ownership:
        risk_budget + stop_distance
            -> existing position-size formula
            -> position_size

    No recalculation, rescaling, rounding, clipping, normalization,
    leverage conversion, fallback, or synthetic value generation.
    """
    if not isinstance(asset, str) or not asset:
        raise ValueError("INVALID_ASSET")

    if direction not in DIRECTIONS:
        raise ValueError("INVALID_DIRECTION")

    if not isinstance(snapshot_id, str) or not snapshot_id:
        raise ValueError("INVALID_SNAPSHOT_ID")

    position_size = calculate_position_size(
        risk_budget,
        stop_distance,
    )

    if position_size is None:
        raise ValueError("POSITION_SIZE_BLOCKED")

    exposure = calculate_exposure(
        position_size,
        entry_price,
    )

    if exposure is None:
        raise ValueError("EXPOSURE_BLOCKED")

    return {
        "asset": asset,
        "direction": direction,
        "state": "CALCULATED",
        "risk_budget": float(risk_budget),
        "entry_price": float(entry_price),
        "stop_distance": float(stop_distance),
        "position_size": float(position_size),
        "exposure": float(exposure),
        "snapshot_id": snapshot_id,
        "quantity_source": "POSITION_SIZING.position_size",
        "quantity_unit": "BASE_ASSET",
        "quantity_recomputed": False,
        "quantity_rescaled": False,
        "quantity_rounded": False,
        "quantity_clipped": False,
    }

def build_position_record(
    asset,
    budget_record,
    stop_record,
    risk_amount,
):
    """
    Build one Position Sizing record.

    Decision chain:

        Budget State
             ↓
        Direction
             ↓
        Risk Budget
             ↓
        Entry
             ↓
        Stop Distance
             ↓
        Position Size
             ↓
        Exposure
    """

    # ------------------------------------------------------------------------
    # Budget existence
    # ------------------------------------------------------------------------

    if not isinstance(
        budget_record,
        dict,
    ):

        return build_uncalculated_record(
            asset
        )

    # ------------------------------------------------------------------------
    # Budget state
    # ------------------------------------------------------------------------

    budget_state = extract_budget_state(
        budget_record
    )

    # ------------------------------------------------------------------------
    # BLOCKED
    # ------------------------------------------------------------------------

    if budget_state == "BLOCKED":

        direction = extract_direction(
            budget_record
        )

        return build_blocked_record(
            asset=asset,
            direction=direction,
        )

    # ------------------------------------------------------------------------
    # UNALLOCATED
    # ------------------------------------------------------------------------

    if budget_state != "ALLOCATED":

        return build_uncalculated_record(
            asset
        )

    # ------------------------------------------------------------------------
    # Direction
    # ------------------------------------------------------------------------

    direction = extract_direction(
        budget_record
    )

    if direction not in (
        "LONG",
        "SHORT",
    ):

        return build_uncalculated_record(
            asset
        )

    # ------------------------------------------------------------------------
    # Risk Budget
    # ------------------------------------------------------------------------

    risk_budget = extract_risk_budget(
        budget_record,
        risk_amount,
    )

    if (
        risk_budget is None
        or risk_budget <= EPSILON
    ):

        return build_uncalculated_record(
            asset
        )

    # ------------------------------------------------------------------------
    # Stop record
    # ------------------------------------------------------------------------

    if not isinstance(
        stop_record,
        dict,
    ):

        return build_uncalculated_record(
            asset
        )

    # ------------------------------------------------------------------------
    # Entry
    # ------------------------------------------------------------------------

    entry_price = extract_entry_price(
        stop_record
    )

    if (
        entry_price is None
        or entry_price <= EPSILON
    ):

        return build_uncalculated_record(
            asset
        )

    # ------------------------------------------------------------------------
    # Stop
    # ------------------------------------------------------------------------

    stop_price = extract_stop_price(
        stop_record
    )

    # ------------------------------------------------------------------------
    # Stop Distance
    # ------------------------------------------------------------------------

    stop_distance = extract_stop_distance(
        stop_record,
        entry_price=entry_price,
        stop_price=stop_price,
    )

    if (
        stop_distance is None
        or stop_distance <= EPSILON
    ):

        return build_uncalculated_record(
            asset
        )

    # ------------------------------------------------------------------------
    # Directional Stop Validation
    # ------------------------------------------------------------------------

    if stop_price is not None:

        if direction == "LONG":

            if stop_price >= entry_price:

                return build_blocked_record(
                    asset=asset,
                    direction=direction,
                    risk_budget=risk_budget,
                    entry_price=entry_price,
                    stop_distance=stop_distance,
                )

        elif direction == "SHORT":

            if stop_price <= entry_price:

                return build_blocked_record(
                    asset=asset,
                    direction=direction,
                    risk_budget=risk_budget,
                    entry_price=entry_price,
                    stop_distance=stop_distance,
                )

    # ------------------------------------------------------------------------
    # Calculate
    # ------------------------------------------------------------------------

    return build_calculated_record(
        asset=asset,
        direction=direction,
        risk_budget=risk_budget,
        entry_price=entry_price,
        stop_distance=stop_distance,
    )


# ============================================================================
# SNAPSHOT
# ============================================================================

def calculate_snapshot():
    """
    Calculate complete Position Sizing snapshot.

    IMPORTANT:

    The returned object remains compatible with
    portfolio_risk_engine:

        {
            "capital": {...},
            "risk_amount": ...,
            "positions": [...]
        }
    """

    # ------------------------------------------------------------------------
    # Capital
    # ------------------------------------------------------------------------

    capital = load_capital_config()

    # ------------------------------------------------------------------------
    # Risk Amount
    # ------------------------------------------------------------------------

    risk_amount = calculate_risk_amount(
        capital
    )

    # ------------------------------------------------------------------------
    # Risk Budget
    # ------------------------------------------------------------------------

    budget_snapshot = load_risk_budgets()

    # ------------------------------------------------------------------------
    # Stop Loss
    # ------------------------------------------------------------------------

    stop_snapshot = load_stop_losses()

    stop_index = index_stop_losses(
        stop_snapshot
    )

    # ------------------------------------------------------------------------
    # Build all 15 assets
    # ------------------------------------------------------------------------

    positions = []

    for asset in EXPECTED_ASSETS:

        budget_record = budget_snapshot.get(
            asset
        )

        stop_record = stop_index.get(
            asset
        )

        record = build_position_record(
            asset=asset,
            budget_record=budget_record,
            stop_record=stop_record,
            risk_amount=risk_amount,
        )

        # --------------------------------------------------------------------
        # HARD STRUCTURAL GUARANTEE
        # --------------------------------------------------------------------

        if "asset" not in record:

            record["asset"] = asset

        positions.append(
            record
        )

    # ------------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------------

    return {
        "capital": capital,
        "risk_amount": float(
            risk_amount
        ),
        "positions": positions,
    }


# ============================================================================
# VALIDATE SNAPSHOT
# ============================================================================

def validate_snapshot(
    snapshot,
):
    """
    Validate Position Sizing snapshot.

    Supports both:

        calculate_snapshot() wrapper

    and:

        raw list

    The contract itself receives ONLY the position list.
    """

    if isinstance(
        snapshot,
        dict,
    ):

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

    elif isinstance(
        snapshot,
        list,
    ):

        positions = snapshot

    else:

        raise RuntimeError(
            "Position sizing snapshot must be "
            "a dictionary or list"
        )

    # ------------------------------------------------------------------------
    # Validate every record
    # ------------------------------------------------------------------------

    for record in positions:

        validate_position_sizing(
            record
        )

    # ------------------------------------------------------------------------
    # Validate complete asset set
    # ------------------------------------------------------------------------

    contract_validate_snapshot(
        positions
    )

    return True


# ============================================================================
# STATISTICS
# ============================================================================

def calculate_statistics(
    positions,
):
    """
    Calculate display-only statistics.
    """

    calculated = 0
    uncalculated = 0
    blocked = 0

    total_risk = 0.0
    total_exposure = 0.0

    long_count = 0
    short_count = 0

    for record in positions:

        state = record.get(
            "state"
        )

        direction = record.get(
            "direction"
        )

        if state == "CALCULATED":

            calculated += 1

            risk = to_float(
                record.get(
                    "risk_budget"
                ),
                0.0,
            )

            exposure = to_float(
                record.get(
                    "exposure"
                ),
                0.0,
            )

            total_risk += risk
            total_exposure += exposure

        elif state == "UNCALCULATED":

            uncalculated += 1

        elif state == "BLOCKED":

            blocked += 1

        if direction == "LONG":

            long_count += 1

        elif direction == "SHORT":

            short_count += 1

    return {
        "calculated": calculated,
        "uncalculated": uncalculated,
        "blocked": blocked,
        "total_risk": total_risk,
        "total_exposure": total_exposure,
        "long": long_count,
        "short": short_count,
    }


# ============================================================================
# HEADER
# ============================================================================

def print_header():

    print("=" * 77)
    print(
        "ARUNDA POSITION SIZING ENGINE v0.6"
    )
    print("=" * 77)

    print(
        "Source          : risk_budget + capital + stop_loss"
    )

    print(
        "Purpose         : POSITION SIZE + EXPOSURE"
    )

    print(
        "Risk Budget     : ALLOCATION INPUT"
    )

    print(
        "Risk Amount     : CAPITAL × RISK PER TRADE"
    )

    print(
        "Formula         : RISK BUDGET / STOP DISTANCE"
    )

    print(
        "Exposure        : POSITION SIZE × ENTRY PRICE"
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
# PRINT RESULTS
# ============================================================================

def print_results(
    snapshot,
):
    """
    Print complete Position Sizing snapshot.
    """

    positions = snapshot[
        "positions"
    ]

    statistics = calculate_statistics(
        positions
    )

    capital = snapshot[
        "capital"
    ]

    print()

    print("=" * 77)
    print(
        "POSITION SIZING SNAPSHOT"
    )
    print("=" * 77)

    print(
        "Asset  | Direction | State        | Risk Budget | "
        "Entry Price | Stop Distance | Position Size | Exposure"
    )

    print("-" * 77)

    for record in positions:

        asset = record[
            "asset"
        ]

        direction = record[
            "direction"
        ]

        state = record[
            "state"
        ]

        risk_budget = record[
            "risk_budget"
        ]

        entry_price = record[
            "entry_price"
        ]

        stop_distance = record[
            "stop_distance"
        ]

        position_size = record[
            "position_size"
        ]

        exposure = record[
            "exposure"
        ]

        risk_text = (
            "NONE"
            if risk_budget is None
            else f"{risk_budget:,.2f}"
        )

        entry_text = (
            "NONE"
            if entry_price is None
            else f"{entry_price:,.2f}"
        )

        distance_text = (
            "NONE"
            if stop_distance is None
            else f"{stop_distance:,.2f}"
        )

        print(
            f"{asset:<6} | "
            f"{direction:<9} | "
            f"{state:<12} | "
            f"{risk_text:>11} | "
            f"{entry_text:>11} | "
            f"{distance_text:>13} | "
            f"{position_size:>13.8f} | "
            f"{exposure:>10.2f}"
        )

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
        f"Calculated      : "
        f"{statistics['calculated']}"
    )

    print(
        f"Uncalculated    : "
        f"{statistics['uncalculated']}"
    )

    print(
        f"Blocked         : "
        f"{statistics['blocked']}"
    )

    print(
        f"LONG            : "
        f"{statistics['long']}"
    )

    print(
        f"SHORT           : "
        f"{statistics['short']}"
    )

    print(
        f"Capital         : "
        f"{capital['capital']:,.2f}"
    )

    print(
        f"Available       : "
        f"{capital['available_capital']:,.2f}"
    )

    print(
        f"Risk / Trade    : "
        f"{capital['risk_per_trade'] * 100:.2f}%"
    )

    print(
        f"Risk Amount     : "
        f"{snapshot['risk_amount']:,.2f}"
    )

    print(
        f"Total Risk      : "
        f"{statistics['total_risk']:,.2f}"
    )

    print(
        f"Total Exposure  : "
        f"{statistics['total_exposure']:,.2f}"
    )

    print(
        "Risk Budget     : ALLOCATION INPUT"
    )

    print(
        "Position Size   : ENGINE OUTPUT"
    )

    print(
        "Exposure        : ENGINE OUTPUT"
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
        # Calculate
        # --------------------------------------------------------------------

        snapshot = calculate_snapshot()

        # --------------------------------------------------------------------
        # Validate
        # --------------------------------------------------------------------

        validate_snapshot(
            snapshot
        )

        # --------------------------------------------------------------------
        # Print
        # --------------------------------------------------------------------

        print_results(
            snapshot
        )

        print()

        print(
            "POSITION SIZING ENGINE STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()

        print("=" * 77)
        print(
            "ARUNDA POSITION SIZING ENGINE ERROR"
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
            "POSITION SIZING ENGINE STATUS : FAILED"
        )

        return 1


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )