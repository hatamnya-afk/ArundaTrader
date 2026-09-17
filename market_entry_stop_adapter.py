"""
ARUNDA MARKET ENTRY / STOP ADAPTER v0.1

Purpose:
    Connect Market Data with Entry / Stop Contract.

Architecture:

    MARKET DATA ENGINE
            |
            | latest close
            v
    MARKET ENTRY / STOP ADAPTER
            ^
            |
            | direction
            |
       RISK ENGINE
            |
            v
    ENTRY / STOP CONTRACT
            |
            v
    STOP LOSS ENGINE

Rules:
    - MEMORY ONLY
    - NO DATABASE WRITES
    - NO SQL WRITES
    - NO SIGNAL GENERATION
    - NO SCORING
    - NO PREDICTION
    - NO RANKING
    - NO INTERPRETATION
    - NO STOP CALCULATION
    - NO POSITION SIZING
    - NO EXECUTION

The adapter only transforms existing upstream data
into the Entry / Stop contract format.
"""

# ============================================================
# IMPORTS
# ============================================================

import sqlite3

import entry_stop_contract


# ============================================================
# CONFIG
# ============================================================

DB = "arunda.db"

MARKET_DATA_SOURCE = (
    "CMC_SNAPSHOT_ANALYSIS_v0.2"
)

MARKET_DATA_TIMEFRAME = (
    "SNAPSHOT"
)

EXPECTED_ASSETS = (
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
)

DIRECTIONS = (
    "LONG",
    "SHORT",
    "NONE",
)

RISK_STATES = (
    "APPROVED",
    "BLOCKED",
    "NOT_APPLICABLE",
)


# ============================================================
# DATABASE
# ============================================================

def connect_database():

    conn = sqlite3.connect(DB)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# LOAD MARKET DATA
# ============================================================

def load_latest_market_data(
    conn,
    asset,
):
    """
    Load the latest Market Data analysis row.

    IMPORTANT:

        This function reads data only.

        It does NOT:
            - calculate signals
            - interpret score
            - calculate stop
            - calculate position size
    """

    row = conn.execute(
        """
        SELECT
            symbol,
            timestamp,
            source_timestamp,
            close,
            technical_score,
            source
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = ?
            AND close IS NOT NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            asset,
            MARKET_DATA_SOURCE,
            MARKET_DATA_TIMEFRAME,
        ),
    ).fetchone()

    return row


# ============================================================
# VALIDATE MARKET PRICE
# ============================================================

def validate_market_price(
    asset,
    price,
):
    """
    Validate existing market price.

    No calculation is performed.
    """

    if price is None:

        raise RuntimeError(
            f"Market price unavailable for {asset}"
        )

    if isinstance(
        price,
        bool,
    ):

        raise RuntimeError(
            f"Invalid market price for {asset}"
        )

    try:

        price = float(price)

    except Exception:

        raise RuntimeError(
            f"Invalid market price for {asset}: "
            f"{price!r}"
        )

    if price <= 0:

        raise RuntimeError(
            f"Market price must be greater than zero "
            f"for {asset}"
        )

    return price


# ============================================================
# VALIDATE RISK INPUT
# ============================================================

def validate_risk_record(
    asset,
    risk,
):
    """
    Validate the already-existing Risk record.

    Risk Engine remains the authority.

    This adapter does NOT create or modify Risk.
    """

    if not isinstance(
        risk,
        dict,
    ):

        raise RuntimeError(
            f"Invalid Risk record for {asset}"
        )

    risk_state = risk.get(
        "risk_state"
    )

    direction = risk.get(
        "direction"
    )

    if risk_state not in RISK_STATES:

        raise RuntimeError(
            f"Invalid Risk state for {asset}: "
            f"{risk_state}"
        )

    if direction not in DIRECTIONS:

        raise RuntimeError(
            f"Invalid Risk direction for {asset}: "
            f"{direction}"
        )

    return True


# ============================================================
# BUILD ONE ENTRY / STOP RECORD
# ============================================================

def build_entry_stop_record(
    asset,
    market_row,
    risk,
):
    """
    Convert Market Data + existing Risk direction
    into Entry / Stop Contract format.

    No stop calculation occurs here.
    """

    validate_risk_record(
        asset,
        risk,
    )

    risk_state = risk[
        "risk_state"
    ]

    direction = risk[
        "direction"
    ]

    # --------------------------------------------------------
    # Market Data unavailable
    # --------------------------------------------------------

    if market_row is None:

        return {
            "asset": asset,
            "direction": "NONE",
            "state": "UNAVAILABLE",
            "entry_price": None,
            "stop_distance": None,
        }

    # --------------------------------------------------------
    # Validate latest close
    # --------------------------------------------------------

    price = validate_market_price(
        asset,
        market_row["close"],
    )

    # --------------------------------------------------------
    # Risk not applicable
    # --------------------------------------------------------

    if risk_state == "NOT_APPLICABLE":

        return {
            "asset": asset,
            "direction": "NONE",
            "state": "UNAVAILABLE",
            "entry_price": None,
            "stop_distance": None,
        }

    # --------------------------------------------------------
    # Risk blocked
    # --------------------------------------------------------

    if risk_state == "BLOCKED":

        if direction == "NONE":

            return {
                "asset": asset,
                "direction": "NONE",
                "state": "BLOCKED",
                "entry_price": price,
                "stop_distance": None,
            }

        return {
            "asset": asset,
            "direction": direction,
            "state": "BLOCKED",
            "entry_price": price,
            "stop_distance": None,
        }

    # --------------------------------------------------------
    # Risk approved
    # --------------------------------------------------------

    if risk_state == "APPROVED":

        if direction not in (
            "LONG",
            "SHORT",
        ):

            return {
                "asset": asset,
                "direction": "NONE",
                "state": "BLOCKED",
                "entry_price": price,
                "stop_distance": None,
            }

        return {
            "asset": asset,
            "direction": direction,
            "state": "READY",
            "entry_price": price,
            "stop_distance": None,
        }

    # --------------------------------------------------------
    # Safety fallback
    # --------------------------------------------------------

    return {
        "asset": asset,
        "direction": "NONE",
        "state": "BLOCKED",
        "entry_price": None,
        "stop_distance": None,
    }


# ============================================================
# BUILD COMPLETE SNAPSHOT
# ============================================================

def build_snapshot(
    risk_snapshot,
):
    """
    Build complete Entry / Stop snapshot.

    Input:
        Existing Risk snapshot.

    Market price:
        Loaded from existing Market Data.

    Output:
        Entry / Stop Contract structure.
    """

    if not isinstance(
        risk_snapshot,
        dict,
    ):

        raise RuntimeError(
            "Risk snapshot must be a dictionary"
        )

    expected = set(
        EXPECTED_ASSETS
    )

    actual = set(
        risk_snapshot.keys()
    )

    missing = expected - actual
    extra = actual - expected

    if missing:

        raise RuntimeError(
            "Risk snapshot missing assets: "
            + ", ".join(
                sorted(missing)
            )
        )

    if extra:

        raise RuntimeError(
            "Risk snapshot contains unexpected assets: "
            + ", ".join(
                sorted(extra)
            )
        )

    conn = connect_database()

    try:

        snapshot = {}

        for asset in EXPECTED_ASSETS:

            market_row = (
                load_latest_market_data(
                    conn,
                    asset,
                )
            )

            snapshot[asset] = (
                build_entry_stop_record(
                    asset=asset,
                    market_row=market_row,
                    risk=risk_snapshot[asset],
                )
            )

        return snapshot

    finally:

        conn.close()


# ============================================================
# VALIDATE CONTRACT
# ============================================================

def validate_snapshot(
    snapshot,
):
    """
    Validate the generated snapshot
    using entry_stop_contract.py.
    """

    validator = getattr(
        entry_stop_contract,
        "validate_entry_stop_snapshot",
        None,
    )

    if not callable(
        validator
    ):

        raise RuntimeError(
            "entry_stop_contract.py must expose "
            "validate_entry_stop_snapshot()"
        )

    result = validator(
        snapshot
    )

    if not isinstance(
        result,
        dict,
    ):

        raise RuntimeError(
            "Entry / Stop contract validation failed"
        )

    if result.get(
        "contract_status"
    ) != "VALID":

        raise RuntimeError(
            "Entry / Stop contract status is not VALID"
        )

    return result


# ============================================================
# PRINT RESULTS
# ============================================================

def print_results(
    snapshot,
):

    print()

    print(
        "MARKET → ENTRY / STOP ADAPTER SNAPSHOT"
    )

    print(
        "-" * 82
    )

    print(
        "Asset  | State       | Direction | Entry Price     | Stop Distance"
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

        entry_text = (
            "NONE"
            if entry is None
            else f"{entry:,.6f}"
        )

        distance_text = (
            "NONE"
            if distance is None
            else f"{distance:,.6f}"
        )

        print(
            f"{asset:<6} | "
            f"{record['state']:<11} | "
            f"{record['direction']:<9} | "
            f"{entry_text:<15} | "
            f"{distance_text}"
        )


# ============================================================
# CONTRACT SUMMARY
# ============================================================

def print_contract(
    validation,
):

    print()

    print(
        "=" * 82
    )

    print(
        "MARKET ENTRY / STOP ADAPTER CONTRACT"
    )

    print(
        "=" * 82
    )

    print(
        f"Expected Assets : "
        f"{validation['expected_assets']}"
    )

    print(
        f"Validated       : "
        f"{validation['validated_assets']}"
    )

    print(
        f"READY           : "
        f"{validation['ready']}"
    )

    print(
        f"UNAVAILABLE     : "
        f"{validation['unavailable']}"
    )

    print(
        f"BLOCKED         : "
        f"{validation['blocked']}"
    )

    print(
        "Market Data     : INPUT ONLY"
    )

    print(
        "Risk Direction  : INPUT ONLY"
    )

    print(
        "Entry Price     : MARKET CLOSE REFERENCE"
    )

    print(
        "Stop Distance   : NOT CALCULATED"
    )

    print(
        "Stop Price      : NOT CALCULATED"
    )

    print(
        "Risk Budget     : NOT USED"
    )

    print(
        "Position Size   : NOT USED"
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
        "Storage         : MEMORY ONLY"
    )

    print(
        "Database Writes : NONE"
    )

    print(
        "Contract Status : VALID"
    )

    print(
        "=" * 82
    )


# ============================================================
# SELF TEST
# ============================================================

def self_test():

    fake_market = {
        "close": 100.0,
    }

    fake_risk = {
        "risk_state": "APPROVED",
        "direction": "LONG",
    }

    record = build_entry_stop_record(
        asset="UNI",
        market_row=fake_market,
        risk=fake_risk,
    )

    if record["asset"] != "UNI":

        raise RuntimeError(
            "Self test asset failed"
        )

    if record["state"] != "READY":

        raise RuntimeError(
            "Self test state failed"
        )

    if record["direction"] != "LONG":

        raise RuntimeError(
            "Self test direction failed"
        )

    if record["entry_price"] != 100.0:

        raise RuntimeError(
            "Self test entry price failed"
        )

    if record["stop_distance"] is not None:

        raise RuntimeError(
            "Adapter must not calculate stop distance"
        )

    unavailable = build_entry_stop_record(
        asset="BTC",
        market_row=None,
        risk=fake_risk,
    )

    if unavailable["state"] != "UNAVAILABLE":

        raise RuntimeError(
            "Unavailable self test failed"
        )

    return True


# ============================================================
# DEMO RISK SNAPSHOT
# ============================================================

def load_risk_snapshot_for_demo():
    """
    Load the real Risk Engine.

    This function does NOT rebuild Risk.
    """

    import risk_engine

    loader = getattr(
        risk_engine,
        "load_decisions",
        None,
    )

    builder = getattr(
        risk_engine,
        "build_risk_snapshot",
        None,
    )

    if not callable(loader):

        raise RuntimeError(
            "risk_engine.py must expose load_decisions()"
        )

    if not callable(builder):

        raise RuntimeError(
            "risk_engine.py must expose "
            "build_risk_snapshot()"
        )

    decisions = loader()

    snapshot = builder(
        decisions
    )

    if not isinstance(
        snapshot,
        dict,
    ):

        raise RuntimeError(
            "Risk snapshot must be a dictionary"
        )

    return snapshot


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 82
    )

    print(
        "ARUNDA MARKET ENTRY / STOP ADAPTER v0.1"
    )

    print(
        "=" * 82
    )

    print(
        "Market Data : CMC SNAPSHOT ANALYSIS"
    )

    print(
        "Risk Source : risk_engine"
    )

    print(
        "Destination : entry_stop_contract"
    )

    print(
        "Entry       : MARKET CLOSE REFERENCE"
    )

    print(
        "Stop        : NOT CALCULATED"
    )

    print(
        "Position    : NOT USED"
    )

    print(
        "Execution   : NOT USED"
    )

    print(
        "Storage     : MEMORY ONLY"
    )

    print(
        "=" * 82
    )

    try:

        print()

        print(
            "Running adapter self-test..."
        )

        self_test()

        print(
            "SELF TEST : PASSED"
        )

        print()

        print(
            "Loading existing Risk snapshot..."
        )

        risk_snapshot = (
            load_risk_snapshot_for_demo()
        )

        print(
            "Risk snapshot : LOADED"
        )

        print()

        print(
            "Connecting Market Data → Entry / Stop..."
        )

        snapshot = build_snapshot(
            risk_snapshot
        )

        validation = validate_snapshot(
            snapshot
        )

        print_results(
            snapshot
        )

        print_contract(
            validation
        )

        print()

        print(
            "MARKET ENTRY / STOP ADAPTER STATUS : READY"
        )

        return 0

    except Exception as exc:

        print()

        print(
            "=" * 82
        )

        print(
            "ARUNDA MARKET ENTRY / STOP ADAPTER ERROR"
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
            "MARKET ENTRY / STOP ADAPTER STATUS : FAILED"
        )

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )