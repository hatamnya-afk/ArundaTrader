import sqlite3
import math
import os
import shutil
import statistics
import importlib.util
from datetime import datetime, timezone


# ============================================================
# ARUNDA TRADER
# FIND_FUTURE_PRICE_TOLERANCE_REPAIR
# AND RUNTIME VERIFY v0.1
#
# MODE:
#   READ ONLY / RUNTIME REPAIR TEST
#
# SAFETY:
#   Production source = UNMODIFIED
#   Production DB     = UNMODIFIED
#   Synthetic data    = FORBIDDEN
#   Interpolation     = FORBIDDEN
#   Forward fill      = FORBIDDEN
#   Back fill         = FORBIDDEN
#
# IMPORTANT:
#   Production TOLERANCES are NOT modified.
#   Repair is applied only to an in-memory imported module.
# ============================================================


DB_NAME = "arunda.db"
ENGINE_FILE = "signal_outcome_engine.py"

TEMP_DB = "_forensic_outcome_runtime_verify.db"

ENGINE_VERSION_EXPECTED = "OUTCOME_v0.3.2"

# ------------------------------------------------------------
# CURRENT PRODUCTION VALUES
# ------------------------------------------------------------

PRODUCTION_TOLERANCES = {
    "5m": 300,
    "15m": 300,
    "30m": 600,
    "60m": 900,
}

# ------------------------------------------------------------
# TARGETED TEST REPAIR
#
# 550.124s is the minimum observed 5m candidate.
# 600s gives a small safety margin while remaining close
# to the observed market cadence.
#
# This is NOT written to production.
# ------------------------------------------------------------

TEST_TOLERANCES = {
    "5m": 600,
    "15m": 300,
    "30m": 600,
    "60m": 900,
}

HORIZONS = {
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "60m": 60,
}


# ============================================================
# OUTPUT HELPERS
# ============================================================

def line(char="=", length=78):
    print(char * length)


def section(title):
    print()
    line()
    print(title)
    line()


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


# ============================================================
# TIMESTAMP HELPERS
# ============================================================

def parse_timestamp(value):

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


# ============================================================
# DATABASE
# ============================================================

def open_db(path, read_only=False):

    if read_only:

        uri = (
            "file:"
            + os.path.abspath(path)
            + "?mode=ro"
        )

        conn = sqlite3.connect(
            uri,
            uri=True
        )

    else:

        conn = sqlite3.connect(path)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# PRODUCTION DB FINGERPRINT
# ============================================================

def production_db_fingerprint():

    section("PRODUCTION DATABASE SAFETY CHECK")

    if not os.path.exists(DB_NAME):

        print(
            f"ERROR | Database not found: {DB_NAME}"
        )

        return False

    size = os.path.getsize(DB_NAME)

    print(
        f"Database       : {DB_NAME}"
    )

    print(
        f"Database size  : {size:,} bytes"
    )

    return True


# ============================================================
# LOAD PRODUCTION ENGINE
# ============================================================

def load_engine():

    section("LOADING PRODUCTION ENGINE")

    if not os.path.exists(ENGINE_FILE):

        raise FileNotFoundError(
            ENGINE_FILE
        )

    spec = importlib.util.spec_from_file_location(
        "arunda_signal_outcome_engine_forensic",
        ENGINE_FILE
    )

    if spec is None or spec.loader is None:

        raise RuntimeError(
            "Unable to load signal_outcome_engine.py"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(module)

    print(
        f"Engine file    : {ENGINE_FILE}"
    )

    print(
        f"Engine version : "
        f"{getattr(module, 'ENGINE_VERSION', 'UNKNOWN')}"
    )

    return module


# ============================================================
# VERIFY PRODUCTION TOLERANCE
# ============================================================

def verify_production_tolerance(engine):

    section("RUNTIME PRODUCTION TOLERANCE")

    actual = getattr(
        engine,
        "TOLERANCES",
        None
    )

    if not isinstance(actual, dict):

        raise RuntimeError(
            "Production TOLERANCES not found."
        )

    for horizon in HORIZONS:

        value = actual.get(horizon)

        print(
            f"{horizon:<5} | "
            f"{safe_float(value):>8.0f} sec"
        )

    return dict(actual)


# ============================================================
# GET ELIGIBLE SIGNALS
# ============================================================

def get_signals(conn, engine):

    versions = tuple(
        engine.FUSION_VERSIONS
    )

    placeholders = ",".join(
        "?"
        for _ in versions
    )

    rows = conn.execute(
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
        versions
    ).fetchall()

    return rows


# ============================================================
# FIND NEAREST MARKET DATA
#
# This reproduces the production search logic without
# modifying production source.
# ============================================================

def nearest_market_data(
    conn,
    asset,
    entry_timestamp,
    minutes
):

    entry_epoch = timestamp_to_epoch(
        entry_timestamp
    )

    if entry_epoch is None:
        return None

    target_epoch = (
        entry_epoch
        + minutes * 60
    )

    # Deliberately search the available asset history
    # around the target. No synthetic data is created.
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
        ORDER BY timestamp ASC
        """,
        (
            asset,
        )
    ).fetchall()

    if not rows:
        return None

    best = None

    for row in rows:

        row_epoch = timestamp_to_epoch(
            row["timestamp"]
        )

        if row_epoch is None:
            continue

        price = safe_float(
            row["close"]
        )

        if price is None:
            continue

        distance = abs(
            row_epoch - target_epoch
        )

        if (
            best is None
            or distance < best["distance"]
        ):

            best = {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "close": price,
                "distance": distance,
            }

    return best


# ============================================================
# FORENSIC DISTRIBUTION
# ============================================================

def collect_distance_distribution(
    conn,
    signals
):

    section("RUNTIME DISTANCE DISTRIBUTION")

    results = {
        horizon: []
        for horizon in HORIZONS
    }

    total = 0
    no_data = 0

    for signal in signals:

        asset = signal["asset"]
        entry_timestamp = signal["timestamp"]

        for horizon, minutes in HORIZONS.items():

            nearest = nearest_market_data(
                conn,
                asset,
                entry_timestamp,
                minutes
            )

            total += 1

            if nearest is None:

                no_data += 1

                continue

            results[horizon].append(
                nearest["distance"]
            )

    print(
        f"Total horizon checks : {total}"
    )

    print(
        f"No market_data       : {no_data}"
    )

    print()

    for horizon in HORIZONS:

        values = results[horizon]

        if not values:

            print(
                f"{horizon:<5} | NO DATA"
            )

            continue

        print(
            f"{horizon:<5} | "
            f"N={len(values):<3} | "
            f"MIN={min(values):>10.3f}s | "
            f"MEDIAN={statistics.median(values):>10.3f}s | "
            f"MAX={max(values):>10.3f}s"
        )

    return results


# ============================================================
# TEST find_future_price DIRECTLY
#
# IMPORTANT:
# The production function itself is called.
# Only its tolerance argument is changed.
# ============================================================

def runtime_find_future_price_test(
    engine,
    conn,
    signals,
    tolerances,
    label
):

    section(
        f"RUNTIME FIND_FUTURE_PRICE TEST | {label}"
    )

    stats = {}

    for horizon, minutes in HORIZONS.items():

        tolerance = tolerances[horizon]

        found = 0
        none_count = 0
        distances = []

        for signal in signals:

            price = engine.find_future_price(
                conn=conn,
                asset=signal["asset"],
                entry_timestamp=signal["timestamp"],
                minutes=minutes,
                tolerance=tolerance,
            )

            if price is None:

                none_count += 1

            else:

                found += 1

                nearest = nearest_market_data(
                    conn,
                    signal["asset"],
                    signal["timestamp"],
                    minutes
                )

                if nearest is not None:

                    distances.append(
                        nearest["distance"]
                    )

        stats[horizon] = {
            "found": found,
            "none": none_count,
            "distances": distances,
        }

        print(
            f"{horizon:<5} | "
            f"Tolerance={tolerance:>5.0f}s | "
            f"FOUND={found:<3} | "
            f"NONE={none_count:<3}"
        )

    return stats


# ============================================================
# COMPARE BEFORE / AFTER
# ============================================================

def compare_results(
    production_stats,
    repair_stats
):

    section("BEFORE / AFTER RUNTIME COMPARISON")

    total_gain = 0

    for horizon in HORIZONS:

        before = production_stats[horizon]
        after = repair_stats[horizon]

        gain = (
            after["found"]
            - before["found"]
        )

        total_gain += gain

        print(
            f"{horizon:<5} | "
            f"Before FOUND={before['found']:<3} "
            f"NONE={before['none']:<3} | "
            f"After FOUND={after['found']:<3} "
            f"NONE={after['none']:<3} | "
            f"GAIN={gain:+d}"
        )

    print()
    print(
        f"TOTAL NEW FUTURE PRICES : {total_gain:+d}"
    )

    return total_gain


# ============================================================
# CREATE TEMPORARY DB
# ============================================================

def create_temp_database():

    section("CREATING TEMPORARY RUNTIME DB COPY")

    if os.path.exists(TEMP_DB):

        os.remove(TEMP_DB)

        print(
            "Removed previous temporary DB."
        )

    shutil.copy2(
        DB_NAME,
        TEMP_DB
    )

    print(
        f"Temporary DB : {TEMP_DB}"
    )

    print(
        "Production DB : UNMODIFIED"
    )


# ============================================================
# OUTCOME RUNTIME VERIFY
#
# Runs the REAL create_outcome/process_signals against
# a temporary database while TOLERANCES is overridden
# only inside the imported module.
# ============================================================

def runtime_outcome_verify(
    engine
):

    section(
        "OUTCOME RUNTIME VERIFY ON TEMPORARY DB"
    )

    conn = open_db(
        TEMP_DB,
        read_only=False
    )

    try:

        # ----------------------------------------------------
        # Runtime-only repair
        # ----------------------------------------------------

        engine.TOLERANCES = dict(
            TEST_TOLERANCES
        )

        print(
            "Runtime tolerance override:"
        )

        for horizon in HORIZONS:

            print(
                f"{horizon:<5} | "
                f"{engine.TOLERANCES[horizon]:>5.0f}s"
            )

        print()

        # ----------------------------------------------------
        # Run the REAL production process_signals()
        # ----------------------------------------------------

        result = engine.process_signals(
            conn
        )

        processed, pending, skipped, errors = (
            result
        )

        print()
        print(
            "Production process_signals() executed "
            "against TEMP DB."
        )

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

        # ----------------------------------------------------
        # Verify actual populated horizons
        # ----------------------------------------------------

        print()
        print(
            "HORIZON POPULATION"
        )
        print("-" * 78)

        population = {}

        for horizon in HORIZONS:

            price_column = (
                f"price_{horizon}"
            )

            return_column = (
                f"return_{horizon}"
            )

            outcome_column = (
                f"outcome_{horizon}"
            )

            row = conn.execute(
                f"""
                SELECT
                    COUNT(*) AS total,
                    COUNT({price_column}) AS prices,
                    COUNT({return_column}) AS returns,
                    COUNT({outcome_column}) AS outcomes
                FROM signal_outcomes
                WHERE engine_version = ?
                """,
                (
                    engine.ENGINE_VERSION,
                )
            ).fetchone()

            population[horizon] = dict(
                row
            )

            print(
                f"{horizon:<5} | "
                f"Records={row['total']:<4} | "
                f"Prices={row['prices']:<4} | "
                f"Returns={row['returns']:<4} | "
                f"Outcomes={row['outcomes']:<4}"
            )

        conn.commit()

        return (
            population,
            errors
        )

    finally:

        conn.close()


# ============================================================
# FINAL VERDICT
# ============================================================

def final_verdict(
    production_stats,
    repair_stats,
    population,
    errors
):

    section("FINAL FORENSIC / REPAIR VERDICT")

    five_before = production_stats["5m"]["found"]
    five_after = repair_stats["5m"]["found"]

    five_gain = (
        five_after - five_before
    )

    populated_5m = population["5m"]["prices"]
    populated_15m = population["15m"]["prices"]
    populated_30m = population["30m"]["prices"]
    populated_60m = population["60m"]["prices"]

    print(
        f"5m runtime future prices : "
        f"{five_before} → {five_after}"
    )

    print(
        f"5m improvement           : "
        f"{five_gain:+d}"
    )

    print()

    print(
        f"5m  populated prices      : {populated_5m}"
    )

    print(
        f"15m populated prices      : {populated_15m}"
    )

    print(
        f"30m populated prices      : {populated_30m}"
    )

    print(
        f"60m populated prices      : {populated_60m}"
    )

    print(
        f"Runtime errors            : {errors}"
    )

    print()

    if (
        five_gain > 0
        and errors == 0
        and populated_5m > 0
    ):

        print(
            "VERDICT : TARGETED 5m TOLERANCE "
            "REPAIR IS RUNTIME EFFECTIVE."
        )

        print(
            "Production repair is NOT applied "
            "by this script."
        )

        return True

    if five_gain == 0:

        print(
            "VERDICT : TOLERANCE REPAIR DID NOT "
            "IMPROVE 5m FUTURE PRICE RESOLUTION."
        )

        print(
            "Do NOT modify production tolerance."
        )

        return False

    print(
        "VERDICT : RUNTIME VERIFICATION "
        "INCONCLUSIVE / FAILED."
    )

    return False


# ============================================================
# MAIN
# ============================================================

def main():

    line()

    print(
        "FIND_FUTURE_PRICE TOLERANCE REPAIR "
        "& RUNTIME VERIFY v0.1"
    )

    line()

    print(
        f"Database           : {DB_NAME}"
    )

    print(
        f"Production source  : {ENGINE_FILE}"
    )

    print(
        "Production source  : UNMODIFIED"
    )

    print(
        "Production DB      : UNMODIFIED"
    )

    print(
        "Synthetic data     : FORBIDDEN"
    )

    print(
        "Interpolation      : FORBIDDEN"
    )

    print(
        "Forward fill       : FORBIDDEN"
    )

    print(
        "Back fill          : FORBIDDEN"
    )

    print(
        "Mode               : READ ONLY + TEMP DB RUNTIME TEST"
    )

    line()

    engine = None
    production_conn = None

    try:

        # ----------------------------------------------------
        # Safety
        # ----------------------------------------------------

        if not production_db_fingerprint():

            return

        # ----------------------------------------------------
        # Load actual production module
        # ----------------------------------------------------

        engine = load_engine()

        if (
            getattr(
                engine,
                "ENGINE_VERSION",
                None
            )
            != ENGINE_VERSION_EXPECTED
        ):

            print()
            print(
                "WARNING | Unexpected engine version."
            )

        # ----------------------------------------------------
        # Capture actual runtime production tolerance
        # ----------------------------------------------------

        production_runtime = (
            verify_production_tolerance(
                engine
            )
        )

        # ----------------------------------------------------
        # Production DB read-only connection
        # ----------------------------------------------------

        production_conn = open_db(
            DB_NAME,
            read_only=True
        )

        signals = get_signals(
            production_conn,
            engine
        )

        section("ELIGIBLE SIGNALS")

        print(
            f"Eligible signals : {len(signals)}"
        )

        if not signals:

            print(
                "No eligible fusion signals."
            )

            return

        # ----------------------------------------------------
        # Distance distribution
        # ----------------------------------------------------

        collect_distance_distribution(
            production_conn,
            signals
        )

        # ----------------------------------------------------
        # BEFORE:
        # actual production tolerance
        # ----------------------------------------------------

        before_stats = runtime_find_future_price_test(
            engine,
            production_conn,
            signals,
            production_runtime,
            "PRODUCTION TOLERANCE"
        )

        # ----------------------------------------------------
        # AFTER:
        # temporary runtime repair
        #
        # IMPORTANT:
        # engine.TOLERANCES is changed only in memory.
        # ----------------------------------------------------

        print()
        print(
            "Applying TEST repair in memory only..."
        )

        engine.TOLERANCES = dict(
            TEST_TOLERANCES
        )

        after_stats = runtime_find_future_price_test(
            engine,
            production_conn,
            signals,
            TEST_TOLERANCES,
            "TEST REPAIR — MEMORY ONLY"
        )

        # ----------------------------------------------------
        # Compare
        # ----------------------------------------------------

        compare_results(
            before_stats,
            after_stats
        )

        production_conn.close()
        production_conn = None

        # ----------------------------------------------------
        # Temporary DB runtime verification
        # ----------------------------------------------------

        create_temp_database()

        population, errors = (
            runtime_outcome_verify(
                engine
            )
        )

        # ----------------------------------------------------
        # Final verdict
        # ----------------------------------------------------

        final_verdict(
            before_stats,
            after_stats,
            population,
            errors
        )

    except KeyboardInterrupt:

        print()
        print(
            "USER INTERRUPT"
        )

    except Exception as exc:

        print()
        line()

        print(
            "FORENSIC SCRIPT ERROR"
        )

        line()

        print(
            repr(exc)
        )

    finally:

        if production_conn is not None:

            try:
                production_conn.close()
            except Exception:
                pass

        # ----------------------------------------------------
        # Temporary DB cleanup
        # ----------------------------------------------------

        if os.path.exists(TEMP_DB):

            try:

                os.remove(TEMP_DB)

                print()
                print(
                    f"Temporary DB removed: {TEMP_DB}"
                )

            except Exception as exc:

                print()
                print(
                    f"WARNING | Could not remove "
                    f"temporary DB: {exc}"
                )

        print()
        line()

        print(
            "SAFETY FINAL"
        )

        line()

        print(
            "Production source : UNMODIFIED"
        )

        print(
            "Production DB     : UNMODIFIED"
        )

        print(
            "Production formula: UNMODIFIED"
        )

        print(
            "Repair persisted  : NO"
        )

        line()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()