import sqlite3
import math
from datetime import datetime, timezone, timedelta


# ============================================================
# ARUNDA SIGNAL OUTCOME ENGINE v0.3.2
# ============================================================

DB_NAME = "arunda.db"
ENGINE_VERSION = "OUTCOME_v0.3.2"

HORIZONS = {
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "60m": 60,
}

# Production tolerance
# 5m TARGETED REPAIR:
# 300s -> 600s
TOLERANCES = {
    "5m": 600,
    "15m": 300,
    "30m": 600,
    "60m": 900,
}

# Minimum directional return required for WIN / LOSS
FLAT_THRESHOLD_PCT = 0.05

# Fusion versions accepted by this engine
FUSION_VERSIONS = (
    "FUSION_v0.5",
    "FUSION_v0.4",
)


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(conn, table_name, column_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        row["name"] == column_name
        for row in rows
    )


def ensure_schema(conn):

    print("Checking outcome schema...")

    required_columns = {
        "snapshot_id": "TEXT",
        "asset": "TEXT",
        "fused_score": "REAL",
        "confidence": "REAL",
        "regime": "TEXT",
        "direction": "TEXT",
        "entry_price": "REAL",
        "entry_timestamp": "TEXT",

        "price_5m": "REAL",
        "price_15m": "REAL",
        "price_30m": "REAL",
        "price_60m": "REAL",

        "return_5m": "REAL",
        "return_15m": "REAL",
        "return_30m": "REAL",
        "return_60m": "REAL",

        "outcome_5m": "TEXT",
        "outcome_15m": "TEXT",
        "outcome_30m": "TEXT",
        "outcome_60m": "TEXT",

        "max_gain": "REAL",
        "max_drawdown": "REAL",

        "engine_version": "TEXT",
    }

    added = 0

    for column, data_type in required_columns.items():

        if not column_exists(
            conn,
            "signal_outcomes",
            column
        ):

            conn.execute(
                f"""
                ALTER TABLE signal_outcomes
                ADD COLUMN {column} {data_type}
                """
            )

            print(
                f"SCHEMA | ADDED | {column}"
            )

            added += 1

    conn.commit()

    if added == 0:
        print(
            "SCHEMA | OK | no changes"
        )


# ============================================================
# HELPERS
# ============================================================

def safe_float(value):

    try:

        if value is None:
            return None

        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except (TypeError, ValueError):

        return None


def parse_timestamp(value):
    """
    Convert ISO timestamp into UTC datetime.
    """

    if value is None:
        return None

    try:

        text = str(value).strip()

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        )

    except Exception:

        return None


def timestamp_to_epoch(value):

    dt = parse_timestamp(value)

    if dt is None:
        return None

    return dt.timestamp()


def epoch_to_timestamp(epoch):

    dt = datetime.fromtimestamp(
        epoch,
        tz=timezone.utc
    )

    return dt.isoformat()


def calculate_return(
    entry,
    future,
    direction
):

    entry = safe_float(entry)
    future = safe_float(future)

    if entry is None or future is None:
        return None

    if entry <= 0:
        return None

    direction = (
        direction or "FLAT"
    ).upper()

    if direction == "LONG":

        return (
            (future - entry)
            / entry
            * 100.0
        )

    if direction == "SHORT":

        return (
            (entry - future)
            / entry
            * 100.0
        )

    return 0.0


def classify_outcome(return_pct):

    if return_pct is None:
        return "PENDING"

    if return_pct > FLAT_THRESHOLD_PCT:
        return "WIN"

    if return_pct < -FLAT_THRESHOLD_PCT:
        return "LOSS"

    return "FLAT"


# ============================================================
# FIND FUTURE MARKET PRICE
# ============================================================

def find_future_price(
    conn,
    asset,
    entry_timestamp,
    minutes,
    tolerance
):
    """
    Find the nearest market_data close to the requested target.

    Rules:
        - target = entry + horizon
        - no synthetic data
        - no interpolation
        - no forward fill
        - no back fill
        - nearest actual market_data observation only
        - candidate must be inside tolerance
    """

    entry_epoch = timestamp_to_epoch(
        entry_timestamp
    )

    if entry_epoch is None:
        return None

    target_epoch = (
        entry_epoch
        + minutes * 60
    )

    lower_epoch = (
        target_epoch
        - tolerance
    )

    upper_epoch = (
        target_epoch
        + tolerance
    )

    lower_timestamp = epoch_to_timestamp(
        lower_epoch
    )

    upper_timestamp = epoch_to_timestamp(
        upper_epoch
    )

    # --------------------------------------------------------
    # IMPORTANT
    #
    # Query only the target window.
    # We do NOT scan the entire asset history.
    # --------------------------------------------------------

    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            close,
            symbol
        FROM market_data
        WHERE
            symbol = ?
            AND close IS NOT NULL
            AND timestamp IS NOT NULL
            AND timestamp >= ?
            AND timestamp <= ?
        ORDER BY timestamp ASC
        """,
        (
            asset,
            lower_timestamp,
            upper_timestamp,
        )
    ).fetchall()

    if not rows:
        return None

    best_price = None
    best_distance = None

    for row in rows:

        row_epoch = timestamp_to_epoch(
            row["timestamp"]
        )

        if row_epoch is None:
            continue

        distance = abs(
            row_epoch - target_epoch
        )

        if distance > tolerance:
            continue

        price = safe_float(
            row["close"]
        )

        if price is None:
            continue

        if (
            best_distance is None
            or distance < best_distance
        ):

            best_distance = distance
            best_price = price

    return best_price


# ============================================================
# FIND EXISTING OUTCOME
# ============================================================

def get_existing_outcome(
    conn,
    snapshot_id,
    asset
):
    """
    Return the latest outcome record for this signal identity.

    IMPORTANT:
    We intentionally do NOT filter by engine_version.

    This allows v0.3.2 to repair/backfill records created
    by previous outcome-engine versions.
    """

    return conn.execute(
        """
        SELECT *
        FROM signal_outcomes
        WHERE
            snapshot_id = ?
            AND asset = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            snapshot_id,
            asset,
        )
    ).fetchone()


# ============================================================
# CREATE / UPDATE OUTCOME
# ============================================================

def create_outcome(
    conn,
    signal
):

    snapshot_id = signal["snapshot_id"]
    asset = signal["asset"]

    entry_price = safe_float(
        signal["entry_price"]
    )

    direction = (
        signal["direction"]
        or "FLAT"
    ).upper()

    entry_timestamp = (
        signal["timestamp"]
    )

    # --------------------------------------------------------
    # EXISTING RECORD
    # --------------------------------------------------------

    existing = get_existing_outcome(
        conn,
        snapshot_id,
        asset
    )

    # --------------------------------------------------------
    # FLAT
    # --------------------------------------------------------

    if direction == "FLAT":

        if existing:

            conn.execute(
                """
                UPDATE signal_outcomes
                SET
                    direction = ?,
                    outcome = 'FLAT',
                    fused_score = ?,
                    confidence = ?,
                    regime = ?,
                    entry_price = COALESCE(
                        entry_price,
                        ?
                    ),
                    entry_timestamp = ?,
                    engine_version = ?
                WHERE id = ?
                """,
                (
                    direction,
                    safe_float(
                        signal["fused_score"]
                    ),
                    safe_float(
                        signal["confidence"]
                    ),
                    signal["regime"],
                    entry_price,
                    entry_timestamp,
                    ENGINE_VERSION,
                    existing["id"],
                )
            )

            return "UPDATED"

        conn.execute(
            """
            INSERT INTO signal_outcomes (
                signal_id,
                timestamp,
                market,
                entry_price,
                outcome,

                snapshot_id,
                asset,
                fused_score,
                confidence,
                regime,
                direction,
                entry_timestamp,
                engine_version
            )
            VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                signal["id"],
                signal["timestamp"],
                asset,
                entry_price,
                "FLAT",

                snapshot_id,
                asset,
                safe_float(
                    signal["fused_score"]
                ),
                safe_float(
                    signal["confidence"]
                ),
                signal["regime"],
                direction,
                entry_timestamp,
                ENGINE_VERSION,
            )
        )

        return "FLAT"

    # --------------------------------------------------------
    # INVALID ENTRY
    # --------------------------------------------------------

    if (
        entry_price is None
        or entry_price <= 0
    ):

        return "PENDING"

    # --------------------------------------------------------
    # CALCULATE HORIZONS
    # --------------------------------------------------------

    prices = {}
    returns = {}
    outcomes = {}

    for label, minutes in HORIZONS.items():

        tolerance = TOLERANCES[label]

        price = find_future_price(
            conn=conn,
            asset=asset,
            entry_timestamp=entry_timestamp,
            minutes=minutes,
            tolerance=tolerance,
        )

        prices[label] = price

        returns[label] = calculate_return(
            entry_price,
            price,
            direction
        )

        outcomes[label] = classify_outcome(
            returns[label]
        )

    # --------------------------------------------------------
    # COMPLETED RETURNS
    # --------------------------------------------------------

    completed_returns = [
        value
        for value in returns.values()
        if value is not None
    ]

    if completed_returns:

        max_gain = max(
            completed_returns
        )

        max_drawdown = min(
            completed_returns
        )

    else:

        max_gain = None
        max_drawdown = None

    # --------------------------------------------------------
    # OVERALL OUTCOME
    #
    # 60m is the final horizon.
    # --------------------------------------------------------

    overall_outcome = "PENDING"

    if returns["60m"] is not None:

        overall_outcome = classify_outcome(
            returns["60m"]
        )

    # ========================================================
    # UPDATE EXISTING RECORD
    # ========================================================

    if existing:

        conn.execute(
            """
            UPDATE signal_outcomes

            SET

                signal_id = COALESCE(
                    signal_id,
                    ?
                ),

                timestamp = COALESCE(
                    timestamp,
                    ?
                ),

                market = COALESCE(
                    market,
                    ?
                ),

                entry_price = COALESCE(
                    entry_price,
                    ?
                ),

                snapshot_id = COALESCE(
                    snapshot_id,
                    ?
                ),

                asset = COALESCE(
                    asset,
                    ?
                ),

                fused_score = COALESCE(
                    ?,
                    fused_score
                ),

                confidence = COALESCE(
                    ?,
                    confidence
                ),

                regime = COALESCE(
                    ?,
                    regime
                ),

                direction = COALESCE(
                    ?,
                    direction
                ),

                entry_timestamp = COALESCE(
                    entry_timestamp,
                    ?
                ),

                price_5m = COALESCE(
                    ?,
                    price_5m
                ),

                price_15m = COALESCE(
                    ?,
                    price_15m
                ),

                price_30m = COALESCE(
                    ?,
                    price_30m
                ),

                price_60m = COALESCE(
                    ?,
                    price_60m
                ),

                return_5m = COALESCE(
                    ?,
                    return_5m
                ),

                return_15m = COALESCE(
                    ?,
                    return_15m
                ),

                return_30m = COALESCE(
                    ?,
                    return_30m
                ),

                return_60m = COALESCE(
                    ?,
                    return_60m
                ),

                outcome_5m = CASE
                    WHEN ? IS NOT NULL
                    THEN ?
                    ELSE outcome_5m
                END,

                outcome_15m = CASE
                    WHEN ? IS NOT NULL
                    THEN ?
                    ELSE outcome_15m
                END,

                outcome_30m = CASE
                    WHEN ? IS NOT NULL
                    THEN ?
                    ELSE outcome_30m
                END,

                outcome_60m = CASE
                    WHEN ? IS NOT NULL
                    THEN ?
                    ELSE outcome_60m
                END,

                max_gain = CASE
                    WHEN ? IS NOT NULL
                    THEN ?
                    ELSE max_gain
                END,

                max_drawdown = CASE
                    WHEN ? IS NOT NULL
                    THEN ?
                    ELSE max_drawdown
                END,

                outcome = CASE
                    WHEN ? != 'PENDING'
                    THEN ?
                    ELSE outcome
                END,

                engine_version = ?

            WHERE id = ?
            """,
            (
                signal["id"],
                signal["timestamp"],
                asset,
                entry_price,

                snapshot_id,
                asset,

                safe_float(
                    signal["fused_score"]
                ),
                safe_float(
                    signal["confidence"]
                ),
                signal["regime"],
                direction,
                entry_timestamp,

                prices["5m"],
                prices["15m"],
                prices["30m"],
                prices["60m"],

                returns["5m"],
                returns["15m"],
                returns["30m"],
                returns["60m"],

                returns["5m"],
                outcomes["5m"],

                returns["15m"],
                outcomes["15m"],

                returns["30m"],
                outcomes["30m"],

                returns["60m"],
                outcomes["60m"],

                max_gain,
                max_gain,

                max_drawdown,
                max_drawdown,

                overall_outcome,
                overall_outcome,

                ENGINE_VERSION,

                existing["id"],
            )
        )

        if overall_outcome == "PENDING":
            return "PENDING"

        return "UPDATED"

    # ========================================================
    # INSERT NEW RECORD
    # ========================================================

    conn.execute(
        """
        INSERT INTO signal_outcomes (

            signal_id,
            timestamp,
            market,
            entry_price,
            outcome,

            snapshot_id,
            asset,
            fused_score,
            confidence,
            regime,
            direction,
            entry_timestamp,

            price_5m,
            price_15m,
            price_30m,
            price_60m,

            return_5m,
            return_15m,
            return_30m,
            return_60m,

            outcome_5m,
            outcome_15m,
            outcome_30m,
            outcome_60m,

            max_gain,
            max_drawdown,

            engine_version
        )

        VALUES (

            ?, ?, ?, ?, ?,

            ?, ?, ?, ?, ?, ?, ?,

            ?, ?, ?, ?,

            ?, ?, ?, ?,

            ?, ?, ?, ?,

            ?, ?,

            ?
        )
        """,
        (
            signal["id"],
            signal["timestamp"],
            asset,
            entry_price,
            overall_outcome,

            snapshot_id,
            asset,
            safe_float(
                signal["fused_score"]
            ),
            safe_float(
                signal["confidence"]
            ),
            signal["regime"],
            direction,
            entry_timestamp,

            prices["5m"],
            prices["15m"],
            prices["30m"],
            prices["60m"],

            returns["5m"],
            returns["15m"],
            returns["30m"],
            returns["60m"],

            outcomes["5m"],
            outcomes["15m"],
            outcomes["30m"],
            outcomes["60m"],

            max_gain,
            max_drawdown,

            ENGINE_VERSION,
        )
    )

    if overall_outcome == "PENDING":
        return "PENDING"

    return overall_outcome


# ============================================================
# PROCESS SIGNALS
# ============================================================

def process_signals(conn):

    placeholders = ",".join(
        "?"
        for _ in FUSION_VERSIONS
    )

    signals = conn.execute(
        f"""
        SELECT *
        FROM fusion_signals

        WHERE
            engine_version IN (
                {placeholders}
            )

            AND entry_price IS NOT NULL

        ORDER BY id ASC
        """,
        FUSION_VERSIONS
    ).fetchall()

    print(
        f"Eligible Fusion signals : {len(signals)}"
    )

    print("-" * 78)

    processed = 0
    pending = 0
    skipped = 0
    errors = 0

    for signal in signals:

        asset = signal["asset"]

        score = safe_float(
            signal["fused_score"]
        )

        direction = (
            signal["direction"]
            or "FLAT"
        ).upper()

        try:

            result = create_outcome(
                conn,
                signal
            )

            if result == "PENDING":

                pending += 1

                print(
                    f"{asset:<6} | "
                    f"Signal #{signal['id']:<5} | "
                    f"Score {score:8.2f} | "
                    f"{direction:<5} | "
                    f"PENDING"
                )

            elif result == "FLAT":

                processed += 1

                print(
                    f"{asset:<6} | "
                    f"Signal #{signal['id']:<5} | "
                    f"FLAT"
                )

            elif result == "UPDATED":

                processed += 1

                print(
                    f"{asset:<6} | "
                    f"Signal #{signal['id']:<5} | "
                    f"Score {score:8.2f} | "
                    f"{direction:<5} | "
                    f"UPDATED"
                )

            else:

                processed += 1

                print(
                    f"{asset:<6} | "
                    f"Signal #{signal['id']:<5} | "
                    f"Score {score:8.2f} | "
                    f"{direction:<5} | "
                    f"{result}"
                )

        except Exception as exc:

            errors += 1

            print(
                f"{asset:<6} | "
                f"Signal #{signal['id']:<5} | "
                f"ERROR | {repr(exc)}"
            )

    conn.commit()

    return (
        processed,
        pending,
        skipped,
        errors
    )


# ============================================================
# DATABASE SUMMARY
# ============================================================

def print_summary(conn):

    print()
    print("=" * 78)
    print(
        "                    OUTCOME DATABASE SUMMARY"
    )
    print("=" * 78)

    # --------------------------------------------------------
    # Current engine records
    # --------------------------------------------------------

    rows = conn.execute(
        """
        SELECT
            direction,
            outcome,
            COUNT(*) AS count

        FROM signal_outcomes

        WHERE
            engine_version = ?

        GROUP BY
            direction,
            outcome

        ORDER BY
            direction,
            outcome
        """,
        (
            ENGINE_VERSION,
        )
    ).fetchall()

    if not rows:

        print(
            "No v0.3.2 outcome records yet."
        )

        return

    for row in rows:

        print(
            f"{row['direction']:<8} | "
            f"{row['outcome']:<8} | "
            f"{row['count']}"
        )

    print("-" * 78)

    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM signal_outcomes
        WHERE engine_version = ?
        """,
        (
            ENGINE_VERSION,
        )
    ).fetchone()[0]

    print(
        f"TOTAL v0.3.2 OUTCOMES : {total}"
    )

    # --------------------------------------------------------
    # Horizon performance
    # --------------------------------------------------------

    print()
    print(
        "HORIZON PERFORMANCE"
    )
    print("-" * 78)

    for horizon in (
        "5m",
        "15m",
        "30m",
        "60m"
    ):

        outcome_column = (
            f"outcome_{horizon}"
        )

        return_column = (
            f"return_{horizon}"
        )

        row = conn.execute(
            f"""
            SELECT

                COUNT({return_column}),

                AVG({return_column}),

                SUM(
                    CASE
                        WHEN {outcome_column} = 'WIN'
                        THEN 1
                        ELSE 0
                    END
                ),

                SUM(
                    CASE
                        WHEN {outcome_column} = 'LOSS'
                        THEN 1
                        ELSE 0
                    END
                ),

                SUM(
                    CASE
                        WHEN {outcome_column} = 'FLAT'
                        THEN 1
                        ELSE 0
                    END
                )

            FROM signal_outcomes

            WHERE
                engine_version = ?
            """,
            (
                ENGINE_VERSION,
            )
        ).fetchone()

        samples = row[0]
        avg_return = row[1]

        wins = row[2] or 0
        losses = row[3] or 0
        flats = row[4] or 0

        if samples:

            win_rate = (
                wins / samples * 100
            )

            print(
                f"{horizon:<5} | "
                f"N={samples:<4} | "
                f"Avg={avg_return:8.4f}% | "
                f"W={wins:<3} | "
                f"L={losses:<3} | "
                f"F={flats:<3} | "
                f"WinRate={win_rate:6.2f}%"
            )

        else:

            print(
                f"{horizon:<5} | "
                f"N=0 | NO DATA"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 78)
    print(
        "             ARUNDA SIGNAL OUTCOME ENGINE v0.3.2"
    )
    print("=" * 78)

    print(
        f"Database : {DB_NAME}"
    )

    print(
        "Source   : Fusion v0.5 + Market Data"
    )

    print(
        "Mode     : DIRECTIONAL PERFORMANCE TRACKING"
    )

    print(
        "Horizons : 5m / 15m / 30m / 60m"
    )

    print(
        "Tolerance: "
        "5m=600s | "
        "15m=300s | "
        "30m=600s | "
        "60m=900s"
    )

    print("=" * 78)

    conn = None

    try:

        conn = get_connection()

        # ----------------------------------------------------
        # Check table
        # ----------------------------------------------------

        table_exists = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE
                type = 'table'
                AND name = 'signal_outcomes'
            """
        ).fetchone()

        if not table_exists:

            print(
                "ERROR | signal_outcomes table does not exist."
            )

            return

        # ----------------------------------------------------
        # Schema
        # ----------------------------------------------------

        ensure_schema(
            conn
        )

        print()

        # ----------------------------------------------------
        # Process
        # ----------------------------------------------------

        processed, pending, skipped, errors = (
            process_signals(conn)
        )

        print()
        print("=" * 78)
        print(
            "                 OUTCOME ENGINE COMPLETE"
        )
        print("=" * 78)

        print(
            f"Processed : {processed}"
        )

        print(
            f"Pending   : {pending}"
        )

        print(
            f"Skipped   : {skipped}"
        )

        print(
            f"Errors    : {errors}"
        )

        print(
            f"Engine    : {ENGINE_VERSION}"
        )

        print("=" * 78)

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        print_summary(
            conn
        )

        print("=" * 78)

    except Exception as exc:

        print()
        print("=" * 78)
        print(
            "                 OUTCOME ENGINE ERROR"
        )
        print("=" * 78)

        print(
            repr(exc)
        )

        print("=" * 78)

    finally:

        if conn is not None:
            conn.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()