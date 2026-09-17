# ==============================================================================
# OUTCOME v0.3 FUTURE-ONLY HORIZON ELIGIBILITY FORENSIC v0.1
# ==============================================================================
#
# PURPOSE:
#   Determine whether a valid FUTURE market observation exists for each
#   signal/horizon.
#
# IMPORTANT:
#   - READ ONLY
#   - Production DB is never modified
#   - Production source is never modified
#   - No synthetic data
#   - No interpolation
#   - No forward fill
#   - No back fill
#
# This forensic deliberately separates:
#
#   1. nearest observation BEFORE target
#   2. nearest observation AFTER target
#   3. valid future observation inside tolerance
#
# It does NOT use the absolute nearest observation as a future price.
#
# ==============================================================================

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


# ==============================================================================
# CONFIGURATION
# ==============================================================================

DB_PATH = Path("arunda.db")

EXPECTED_OUTCOME_VERSION = "OUTCOME_v0.3.2"

# Current production tolerance configuration
TOLERANCE_SECONDS = {
    "5m": 600,
    "15m": 300,
    "30m": 600,
    "60m": 900,
}

HORIZONS = {
    "5m": 5 * 60,
    "15m": 15 * 60,
    "30m": 30 * 60,
    "60m": 60 * 60,
}


# ==============================================================================
# SAFETY
# ==============================================================================

READ_ONLY = True

if not READ_ONLY:
    raise RuntimeError("SAFETY FAILURE: READ_ONLY must remain True")


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def parse_timestamp(value: str | None) -> datetime | None:
    """
    Parse ISO timestamp into timezone-aware UTC datetime.
    """
    if value is None:
        return None

    try:
        text = value.strip()

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def seconds_between(a: datetime, b: datetime) -> float:
    return abs((a - b).total_seconds())


def format_seconds(value: float | None) -> str:
    if value is None:
        return "N/A"

    return f"{value:10.3f}s"


def get_column_names(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return [row[1] for row in rows]


def find_column(columns: list[str], candidates: list[str]) -> str | None:
    lower_map = {c.lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]

    return None


# ==============================================================================
# DATABASE DISCOVERY
# ==============================================================================

def discover_schema(conn: sqlite3.Connection):
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table'"
        ).fetchall()
    }

    required = {"fusion_signals", "market_data"}

    missing = required - tables

    if missing:
        raise RuntimeError(
            "Missing required tables: "
            + ", ".join(sorted(missing))
        )

    fusion_columns = get_column_names(conn, "fusion_signals")
    market_columns = get_column_names(conn, "market_data")

    return fusion_columns, market_columns


# ==============================================================================
# FUSION SIGNAL DISCOVERY
# ==============================================================================

def discover_signal_columns(columns: list[str]):
    signal_id = find_column(
        columns,
        [
            "id",
            "signal_id",
            "fusion_signal_id",
        ],
    )

    symbol = find_column(
        columns,
        [
            "symbol",
            "asset",
            "ticker",
        ],
    )

    entry_time = find_column(
        columns,
        [
            "entry_time",
            "signal_time",
            "timestamp",
            "created_at",
            "signal_timestamp",
        ],
    )

    direction = find_column(
        columns,
        [
            "direction",
            "signal",
            "side",
        ],
    )

    score = find_column(
        columns,
        [
            "score",
            "fusion_score",
        ],
    )

    return signal_id, symbol, entry_time, direction, score


# ==============================================================================
# MARKET DATA DISCOVERY
# ==============================================================================

def discover_market_columns(columns: list[str]):
    symbol = find_column(
        columns,
        [
            "symbol",
            "asset",
            "ticker",
        ],
    )

    timestamp = find_column(
        columns,
        [
            "timestamp",
            "time",
            "datetime",
            "candle_time",
            "created_at",
        ],
    )

    price = find_column(
        columns,
        [
            "price",
            "close",
            "close_price",
            "last_price",
        ],
    )

    return symbol, timestamp, price


# ==============================================================================
# SIGNAL QUERY
# ==============================================================================

def load_eligible_signals(
    conn: sqlite3.Connection,
    signal_id_col: str,
    symbol_col: str,
    entry_col: str,
    direction_col: str,
    score_col: str | None,
):
    """
    Preserve the same 16-signal forensic population.

    This intentionally looks for Fusion signals with a valid entry timestamp.
    """

    score_expr = (
        f'"{score_col}"'
        if score_col
        else "NULL"
    )

    query = f"""
        SELECT
            "{signal_id_col}",
            "{symbol_col}",
            "{entry_col}",
            "{direction_col}",
            {score_expr}
        FROM fusion_signals
        WHERE "{entry_col}" IS NOT NULL
        ORDER BY "{signal_id_col}"
    """

    rows = conn.execute(query).fetchall()

    return rows


# ==============================================================================
# MARKET DATA LOADING
# ==============================================================================

def load_market_rows(
    conn: sqlite3.Connection,
    market_symbol_col: str,
    market_timestamp_col: str,
    market_price_col: str,
):
    query = f"""
        SELECT
            "{market_symbol_col}",
            "{market_timestamp_col}",
            "{market_price_col}"
        FROM market_data
        WHERE
            "{market_symbol_col}" IS NOT NULL
            AND "{market_timestamp_col}" IS NOT NULL
            AND "{market_price_col}" IS NOT NULL
        ORDER BY "{market_symbol_col}", "{market_timestamp_col}"
    """

    return conn.execute(query).fetchall()


# ==============================================================================
# MARKET INDEX
# ==============================================================================

def build_market_index(
    rows,
    symbol_index: int,
    timestamp_index: int,
    price_index: int,
):
    market = {}

    for row in rows:

        symbol = row[symbol_index]
        timestamp_raw = row[timestamp_index]
        price_raw = row[price_index]

        timestamp = parse_timestamp(timestamp_raw)

        if timestamp is None:
            continue

        try:
            price = float(price_raw)
        except Exception:
            continue

        market.setdefault(symbol, []).append(
            {
                "timestamp": timestamp,
                "price": price,
            }
        )

    for symbol in market:
        market[symbol].sort(
            key=lambda x: x["timestamp"]
        )

    return market


# ==============================================================================
# FUTURE-ONLY CLASSIFICATION
# ==============================================================================

def classify_future_candidate(
    target: datetime,
    observations: list[dict],
    tolerance: float,
):
    """
    Critical forensic rule:

    FUTURE means timestamp >= target.

    Observations before target are NEVER accepted as future observations.

    Classification:

        ELIGIBLE
            future observation exists inside tolerance

        FUTURE_DATA_GAP
            future observations exist, but nearest future observation
            is outside tolerance

        PAST_ONLY_NEAREST
            no observation exists at/after target,
            but a past observation exists

        NO_MARKET_DATA
            symbol has no usable market data

    Returns a detailed dictionary.
    """

    if not observations:
        return {
            "status": "NO_MARKET_DATA",
            "past": None,
            "future": None,
            "future_distance": None,
            "past_distance": None,
        }

    past_candidates = [
        row
        for row in observations
        if row["timestamp"] < target
    ]

    future_candidates = [
        row
        for row in observations
        if row["timestamp"] >= target
    ]

    past = None

    if past_candidates:
        past = max(
            past_candidates,
            key=lambda x: x["timestamp"]
        )

    future = None

    if future_candidates:
        future = min(
            future_candidates,
            key=lambda x: x["timestamp"]
        )

    past_distance = None

    if past is not None:
        past_distance = (
            target - past["timestamp"]
        ).total_seconds()

    future_distance = None

    if future is not None:
        future_distance = (
            future["timestamp"] - target
        ).total_seconds()

    if future is not None and future_distance <= tolerance:
        status = "ELIGIBLE"

    elif future is not None:
        status = "FUTURE_DATA_GAP"

    elif past is not None:
        status = "PAST_ONLY_NEAREST"

    else:
        status = "NO_MARKET_DATA"

    return {
        "status": status,
        "past": past,
        "future": future,
        "future_distance": future_distance,
        "past_distance": past_distance,
    }


# ==============================================================================
# MAIN FORENSIC
# ==============================================================================

def main():

    print("=" * 90)
    print(
        "OUTCOME v0.3 FUTURE-ONLY HORIZON "
        "ELIGIBILITY FORENSIC v0.1"
    )
    print("=" * 90)

    print(f"Database          : {DB_PATH}")
    print(f"Outcome version   : {EXPECTED_OUTCOME_VERSION}")
    print("Mode              : READ ONLY")
    print("Production DB     : UNMODIFIED")
    print("Production source : UNMODIFIED")
    print("Synthetic data    : FORBIDDEN")
    print("Interpolation     : FORBIDDEN")
    print("Forward fill      : FORBIDDEN")
    print("Back fill         : FORBIDDEN")

    print("=" * 90)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    # --------------------------------------------------------------------------
    # READ ONLY CONNECTION
    # --------------------------------------------------------------------------

    conn = sqlite3.connect(
        f"file:{DB_PATH.resolve()}?mode=ro",
        uri=True,
    )

    try:

        # ----------------------------------------------------------------------
        # DATABASE STRUCTURE
        # ----------------------------------------------------------------------

        print()
        print("=" * 90)
        print("DATABASE STRUCTURE CHECK")
        print("=" * 90)

        fusion_columns, market_columns = discover_schema(conn)

        print("fusion_signals       | PASS")
        print("market_data          | PASS")

        # ----------------------------------------------------------------------
        # COLUMN DISCOVERY
        # ----------------------------------------------------------------------

        (
            signal_id_col,
            signal_symbol_col,
            signal_entry_col,
            signal_direction_col,
            signal_score_col,
        ) = discover_signal_columns(fusion_columns)

        (
            market_symbol_col,
            market_timestamp_col,
            market_price_col,
        ) = discover_market_columns(market_columns)

        required_signal_columns = {
            "signal_id": signal_id_col,
            "symbol": signal_symbol_col,
            "entry_time": signal_entry_col,
            "direction": signal_direction_col,
        }

        for name, column in required_signal_columns.items():
            if column is None:
                raise RuntimeError(
                    f"Cannot resolve fusion_signals column: {name}"
                )

        required_market_columns = {
            "symbol": market_symbol_col,
            "timestamp": market_timestamp_col,
            "price": market_price_col,
        }

        for name, column in required_market_columns.items():
            if column is None:
                raise RuntimeError(
                    f"Cannot resolve market_data column: {name}"
                )

        # ----------------------------------------------------------------------
        # SIGNALS
        # ----------------------------------------------------------------------

        signals = load_eligible_signals(
            conn,
            signal_id_col,
            signal_symbol_col,
            signal_entry_col,
            signal_direction_col,
            signal_score_col,
        )

        print()
        print("=" * 90)
        print("SIGNAL POPULATION")
        print("=" * 90)

        print(
            f"Eligible Fusion signals : {len(signals)}"
        )

        # ----------------------------------------------------------------------
        # MARKET DATA
        # ----------------------------------------------------------------------

        market_rows = load_market_rows(
            conn,
            market_symbol_col,
            market_timestamp_col,
            market_price_col,
        )

        market_index = build_market_index(
            market_rows,
            0,
            1,
            2,
        )

        # ----------------------------------------------------------------------
        # AGGREGATES
        # ----------------------------------------------------------------------

        aggregate = {}

        for horizon in HORIZONS:

            aggregate[horizon] = {
                "signals": 0,
                "eligible": 0,
                "future_gap": 0,
                "past_only": 0,
                "no_market_data": 0,
                "invalid_entry": 0,
                "future_distances": [],
                "past_distances": [],
            }

        # ----------------------------------------------------------------------
        # SIGNAL / HORIZON FORENSIC
        # ----------------------------------------------------------------------

        for signal in signals:

            signal_id = signal[0]
            symbol = signal[1]
            entry_raw = signal[2]
            direction = signal[3]

            entry = parse_timestamp(entry_raw)

            print()
            print("-" * 90)
            print(
                f"Signal #{signal_id} | "
                f"{str(symbol):6s} | "
                f"{str(direction):5s}"
            )
            print(
                f"Entry : {entry_raw}"
            )

            observations = market_index.get(
                symbol,
                []
            )

            if observations:

                first_market = observations[0]["timestamp"]
                latest_market = observations[-1]["timestamp"]

                print(
                    f"Market rows : {len(observations)}"
                )
                print(
                    f"Market first : "
                    f"{first_market.isoformat()}"
                )
                print(
                    f"Market latest: "
                    f"{latest_market.isoformat()}"
                )

            else:

                print("Market rows : 0")
                print("Market first : NONE")
                print("Market latest: NONE")

            # ------------------------------------------------------------------
            # INVALID ENTRY
            # ------------------------------------------------------------------

            if entry is None:

                for horizon in HORIZONS:
                    aggregate[horizon]["signals"] += 1
                    aggregate[horizon]["invalid_entry"] += 1

                    print(
                        f"{horizon:<4} | "
                        f"INVALID ENTRY TIMESTAMP"
                    )

                continue

            # ------------------------------------------------------------------
            # HORIZONS
            # ------------------------------------------------------------------

            for horizon, horizon_seconds in HORIZONS.items():

                aggregate[horizon]["signals"] += 1

                target = entry

                # --------------------------------------------------------------
                # IMPORTANT:
                # We preserve the actual horizon target.
                # --------------------------------------------------------------

                from datetime import timedelta

                target = entry + timedelta(
                    seconds=horizon_seconds
                )

                tolerance = TOLERANCE_SECONDS[horizon]

                result = classify_future_candidate(
                    target,
                    observations,
                    tolerance,
                )

                status = result["status"]

                future = result["future"]
                past = result["past"]

                future_distance = result[
                    "future_distance"
                ]

                past_distance = result[
                    "past_distance"
                ]

                # --------------------------------------------------------------
                # AGGREGATE
                # --------------------------------------------------------------

                if status == "ELIGIBLE":

                    aggregate[horizon]["eligible"] += 1

                    if future_distance is not None:
                        aggregate[horizon][
                            "future_distances"
                        ].append(
                            future_distance
                        )

                elif status == "FUTURE_DATA_GAP":

                    aggregate[horizon]["future_gap"] += 1

                    if future_distance is not None:
                        aggregate[horizon][
                            "future_distances"
                        ].append(
                            future_distance
                        )

                elif status == "PAST_ONLY_NEAREST":

                    aggregate[horizon]["past_only"] += 1

                    if past_distance is not None:
                        aggregate[horizon][
                            "past_distances"
                        ].append(
                            past_distance
                        )

                elif status == "NO_MARKET_DATA":

                    aggregate[horizon][
                        "no_market_data"
                    ] += 1

                # --------------------------------------------------------------
                # OUTPUT
                # --------------------------------------------------------------

                print()
                print(
                    f"{horizon:<4} | "
                    f"Target={target.isoformat()}"
                )

                if past is not None:

                    print(
                        f"     PAST   = "
                        f"{past['timestamp'].isoformat()} "
                        f"| Distance="
                        f"{format_seconds(past_distance)}"
                    )

                else:

                    print(
                        "     PAST   = NONE"
                    )

                if future is not None:

                    print(
                        f"     FUTURE = "
                        f"{future['timestamp'].isoformat()} "
                        f"| Distance="
                        f"{format_seconds(future_distance)}"
                    )

                    print(
                        f"     Future price = "
                        f"{future['price']}"
                    )

                else:

                    print(
                        "     FUTURE = NONE"
                    )

                print(
                    f"     Tolerance = "
                    f"{tolerance}s"
                )

                print(
                    f"     STATUS = {status}"
                )

        # ----------------------------------------------------------------------
        # AGGREGATE SUMMARY
        # ----------------------------------------------------------------------

        print()
        print("=" * 90)
        print("FUTURE-ONLY HORIZON AGGREGATE SUMMARY")
        print("=" * 90)

        total_checks = 0
        total_eligible = 0
        total_future_gaps = 0
        total_past_only = 0
        total_no_data = 0

        for horizon in HORIZONS:

            a = aggregate[horizon]

            total_checks += a["signals"]
            total_eligible += a["eligible"]
            total_future_gaps += a["future_gap"]
            total_past_only += a["past_only"]
            total_no_data += a["no_market_data"]

            future_distances = a[
                "future_distances"
            ]

            print()
            print(horizon)

            print(
                f"  Signals                 : "
                f"{a['signals']}"
            )

            print(
                f"  Future eligible        : "
                f"{a['eligible']}"
            )

            print(
                f"  Future data gap        : "
                f"{a['future_gap']}"
            )

            print(
                f"  Past-only nearest      : "
                f"{a['past_only']}"
            )

            print(
                f"  No market data         : "
                f"{a['no_market_data']}"
            )

            print(
                f"  Invalid entry          : "
                f"{a['invalid_entry']}"
            )

            if future_distances:

                print(
                    f"  Future distance MIN    : "
                    f"{min(future_distances):.3f}s"
                )

                print(
                    f"  Future distance MEDIAN : "
                    f"{median(future_distances):.3f}s"
                )

                print(
                    f"  Future distance MAX    : "
                    f"{max(future_distances):.3f}s"
                )

            else:

                print(
                    "  Future distance        : NONE"
                )

            print(
                f"  Production tolerance   : "
                f"{TOLERANCE_SECONDS[horizon]}s"
            )

        # ----------------------------------------------------------------------
        # ROOT CAUSE
        # ----------------------------------------------------------------------

        print()
        print("=" * 90)
        print("ROOT-CAUSE CLASSIFICATION")
        print("=" * 90)

        print(
            f"Total horizon checks : {total_checks}"
        )

        print(
            f"Future eligible      : {total_eligible}"
        )

        print(
            f"Future data gaps     : {total_future_gaps}"
        )

        print(
            f"Past-only nearest    : {total_past_only}"
        )

        print(
            f"No market data      : {total_no_data}"
        )

        print()
        print("INTERPRETATION:")

        if total_past_only > 0:
            print(
                "PAST-ONLY OBSERVATIONS EXIST."
            )
            print(
                "These observations MUST NOT be used "
                "as future prices."
            )

        if total_future_gaps > 0:
            print(
                "FUTURE MARKET-DATA GAPS EXIST "
                "BEYOND PRODUCTION TOLERANCE."
            )

        if total_eligible > 0:
            print(
                "VALID FUTURE CANDIDATES EXIST "
                "INSIDE PRODUCTION TOLERANCE."
            )

        if (
            total_future_gaps == 0
            and total_past_only == 0
            and total_no_data == 0
        ):
            print(
                "NO FUTURE DATA-ELIGIBILITY PROBLEM "
                "DETECTED."
            )

        # ----------------------------------------------------------------------
        # SAFETY VERDICT
        # ----------------------------------------------------------------------

        print()
        print("=" * 90)
        print("FINAL SAFETY VERDICT")
        print("=" * 90)

        print("Database writes       : NONE")
        print("INSERT                : NONE")
        print("UPDATE                : NONE")
        print("DELETE                : NONE")
        print("ALTER                 : NONE")
        print("Tolerance modified    : NO")
        print("Production source     : UNMODIFIED")
        print("Production DB         : UNMODIFIED")
        print("Synthetic data        : NOT USED")
        print("Interpolation         : NOT USED")
        print("Forward fill          : NOT USED")
        print("Back fill             : NOT USED")

        print("=" * 90)
        print("FORENSIC COMPLETE.")
        print("=" * 90)

    finally:
        conn.close()


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    main()