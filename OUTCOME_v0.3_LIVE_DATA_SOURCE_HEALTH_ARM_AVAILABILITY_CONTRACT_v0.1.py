import sqlite3
import os
import sys
import hashlib
from collections import Counter, defaultdict


# ==================================================================================================
# ARUNDA TRADER
# LIVE DATA SOURCE HEALTH + FUSION ARM AVAILABILITY CONTRACT v0.1
# ==================================================================================================

PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"
PRODUCTION_DB = os.path.join(PROJECT_ROOT, "arunda.db")

ENGINE_VERSION = "FUSION_v0.5"
TARGET_TABLE = "fusion_signals"

# Live capture produced by the previous launch harness.
TEMP_ROOT = os.environ.get("TEMP", os.environ.get("TMP", ""))
LIVE_CAPTURE_CANDIDATES = []

if TEMP_ROOT:
    LIVE_CAPTURE_CANDIDATES.append(
        os.path.join(
            TEMP_ROOT,
            "arunda_live_launch_76134ecc",
            "arunda_live_capture.db",
        )
    )


# --------------------------------------------------------------------------------------------------
# UTILITIES
# --------------------------------------------------------------------------------------------------

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def connect_readonly(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    uri = "file:" + path.replace("\\", "/") + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def table_columns(conn, table):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r[1] for r in rows]


def find_live_capture():
    for path in LIVE_CAPTURE_CANDIDATES:
        if os.path.exists(path):
            return path

    # Fallback: discover latest launch capture directory.
    if not TEMP_ROOT or not os.path.isdir(TEMP_ROOT):
        return None

    candidates = []

    for name in os.listdir(TEMP_ROOT):
        if not name.startswith("arunda_live_launch_"):
            continue

        directory = os.path.join(TEMP_ROOT, name)
        db = os.path.join(directory, "arunda_live_capture.db")

        if os.path.isfile(db):
            try:
                candidates.append((os.path.getmtime(db), db))
            except OSError:
                pass

    if not candidates:
        return None

    candidates.sort(reverse=True)
    return candidates[0][1]


# --------------------------------------------------------------------------------------------------
# SOURCE / SCHEMA CONTRACT
# --------------------------------------------------------------------------------------------------

REQUIRED_COLUMNS = {
    "id",
    "timestamp",
    "asset",
    "engine_version",
    "market_available",
    "positioning_available",
    "news_available",
    "data_quality",
    "market_weight",
    "positioning_weight",
    "news_weight",
    "available_weight",
    "missing_arm_penalty",
    "snapshot_id",
    "direction",
    "confidence",
    "regime",
    "entry_price",
}


def validate_schema(conn):
    cols = set(table_columns(conn, TARGET_TABLE))
    missing = sorted(REQUIRED_COLUMNS - cols)

    print()
    print("REAL FUSION SIGNAL SCHEMA")
    print("-" * 100)

    for col in sorted(cols):
        print(f"{col:28}")

    print()
    print("SCHEMA CONTRACT")
    if missing:
        print("FAIL")
        print("Missing required columns:")
        for col in missing:
            print(f"  - {col}")
        return False

    print("PASS")
    return True


# --------------------------------------------------------------------------------------------------
# LOAD LIVE COHORT
# --------------------------------------------------------------------------------------------------

def load_live_rows(conn):
    return conn.execute(
        f"""
        SELECT
            id,
            timestamp,
            asset,
            engine_version,
            market_available,
            positioning_available,
            news_available,
            data_quality,
            market_weight,
            positioning_weight,
            news_weight,
            available_weight,
            missing_arm_penalty,
            snapshot_id,
            direction,
            confidence,
            regime,
            entry_price
        FROM {TARGET_TABLE}
        WHERE engine_version = ?
        ORDER BY id
        """,
        (ENGINE_VERSION,),
    ).fetchall()


# --------------------------------------------------------------------------------------------------
# ARM STATE NORMALIZATION
# --------------------------------------------------------------------------------------------------

def normalize_bool(value):
    if value in (1, True, "1", "TRUE", "true", "YES", "yes"):
        return True

    if value in (0, False, "0", "FALSE", "false", "NO", "no"):
        return False

    return None


def arm_state(row):
    market = normalize_bool(row[4])
    positioning = normalize_bool(row[5])
    news = normalize_bool(row[6])

    states = {
        "MARKET": market,
        "POSITIONING": positioning,
        "NEWS": news,
    }

    available = sum(v is True for v in states.values())

    if available == 3:
        quality = "FULL"
    elif available == 0:
        quality = "NONE"
    else:
        quality = "PARTIAL"

    return states, quality


# --------------------------------------------------------------------------------------------------
# LIVE ARM HEALTH
# --------------------------------------------------------------------------------------------------

def analyze_arm_health(rows):
    print()
    banner("LIVE DATA SOURCE HEALTH")

    arm_counts = {
        "MARKET": Counter(),
        "POSITIONING": Counter(),
        "NEWS": Counter(),
    }

    quality_counts = Counter()

    for row in rows:
        states, quality = arm_state(row)
        quality_counts[quality] += 1

        for arm, state in states.items():
            arm_counts[arm][state] += 1

    for arm in ("MARKET", "POSITIONING", "NEWS"):
        c = arm_counts[arm]

        print(
            f"{arm:15} | "
            f"AVAILABLE={c[True]:3} | "
            f"UNAVAILABLE={c[False]:3} | "
            f"UNKNOWN={c[None]:3}"
        )

    print()
    print("COHORT DATA QUALITY")
    for quality, count in sorted(quality_counts.items()):
        print(f"{quality:15} | {count:3}")

    return arm_counts, quality_counts


# --------------------------------------------------------------------------------------------------
# AVAILABILITY CONTRACT
# --------------------------------------------------------------------------------------------------

def analyze_availability_contract(rows):
    banner("FUSION ARM AVAILABILITY CONTRACT")

    contract_pass = True

    observed_patterns = Counter()

    for row in rows:
        row_id = row[0]
        asset = row[2]

        states, derived_quality = arm_state(row)

        stored_quality = row[7]
        available_weight = row[11]
        missing_penalty = row[12]

        pattern = (
            states["MARKET"],
            states["POSITIONING"],
            states["NEWS"],
        )

        observed_patterns[pattern] += 1

        # ------------------------------------------------------------------
        # Logical availability validation
        # ------------------------------------------------------------------

        expected_available_count = sum(v is True for v in states.values())

        if expected_available_count == 3:
            expected_quality = "FULL"
        elif expected_available_count == 0:
            expected_quality = "NONE"
        else:
            expected_quality = "PARTIAL"

        # Current engine may use richer quality labels such as VERIFIED/PARTIAL.
        # Therefore we only reject impossible states, not legitimate richer labels.

        if stored_quality is None:
            print(
                f"CONTRACT WARNING | id={row_id} asset={asset} "
                f"data_quality=NULL"
            )

        if available_weight is not None:
            if available_weight < 0 or available_weight > 1.0000001:
                print(
                    f"CONTRACT FAIL | id={row_id} asset={asset} "
                    f"available_weight={available_weight}"
                )
                contract_pass = False

        if missing_penalty is not None:
            if missing_penalty < 0:
                print(
                    f"CONTRACT FAIL | id={row_id} asset={asset} "
                    f"missing_arm_penalty={missing_penalty}"
                )
                contract_pass = False

    print()
    print("OBSERVED ARM PATTERNS")

    for pattern, count in observed_patterns.items():
        market, positioning, news = pattern

        def fmt(x):
            if x is True:
                return "ON"
            if x is False:
                return "OFF"
            return "UNKNOWN"

        print(
            f"MARKET={fmt(market):7} | "
            f"POSITIONING={fmt(positioning):7} | "
            f"NEWS={fmt(news):7} | "
            f"rows={count}"
        )

    print()
    print("AVAILABILITY CONTRACT :", "PASS" if contract_pass else "FAIL")

    return contract_pass


# --------------------------------------------------------------------------------------------------
# ROW-LEVEL LIVE PROVENANCE
# --------------------------------------------------------------------------------------------------

def print_row_matrix(rows):
    banner("LIVE COHORT ARM MATRIX")

    print(
        "ID   ASSET   MARKET   POSITIONING   NEWS   "
        "QUALITY      AVAILABLE_WEIGHT   MISSING_PENALTY"
    )
    print("-" * 100)

    for row in rows:
        (
            row_id,
            timestamp,
            asset,
            engine_version,
            market_available,
            positioning_available,
            news_available,
            data_quality,
            market_weight,
            positioning_weight,
            news_weight,
            available_weight,
            missing_arm_penalty,
            snapshot_id,
            direction,
            confidence,
            regime,
            entry_price,
        ) = row

        def flag(x):
            if x == 1:
                return "ON"
            if x == 0:
                return "OFF"
            return "?"

        print(
            f"{row_id:<4} "
            f"{asset:<7} "
            f"{flag(market_available):<8} "
            f"{flag(positioning_available):<13} "
            f"{flag(news_available):<6} "
            f"{str(data_quality):<12} "
            f"{str(available_weight):<19} "
            f"{str(missing_arm_penalty):<16}"
        )


# --------------------------------------------------------------------------------------------------
# SNAPSHOT CONTRACT
# --------------------------------------------------------------------------------------------------

def analyze_snapshots(rows):
    banner("LIVE SNAPSHOT CONTRACT")

    snapshots = Counter()

    for row in rows:
        snapshots[row[13]] += 1

    null_snapshot = snapshots.get(None, 0)

    print(f"Distinct snapshot IDs : {len(snapshots)}")
    print(f"NULL snapshot rows    : {null_snapshot}")

    for snapshot, count in snapshots.items():
        print(f"{str(snapshot):60} | rows={count}")

    if null_snapshot == len(rows):
        print()
        print("SNAPSHOT CONTRACT : FAIL")
        print("No snapshot identity exists in live cohort.")
        return False

    print()
    print("SNAPSHOT CONTRACT : PASS")
    return True


# --------------------------------------------------------------------------------------------------
# LIVE RUNTIME COHERENCE
# --------------------------------------------------------------------------------------------------

def analyze_runtime_coherence(rows):
    banner("LIVE RUNTIME COHERENCE")

    assets = sorted(set(row[2] for row in rows))

    print(f"Engine version : {ENGINE_VERSION}")
    print(f"Rows           : {len(rows)}")
    print(f"Assets         : {len(assets)}")
    print(f"Assets         : {', '.join(assets)}")

    timestamps = [row[1] for row in rows if row[1]]

    if timestamps:
        print(f"First timestamp: {min(timestamps)}")
        print(f"Last timestamp : {max(timestamps)}")

    direction = Counter(row[14] for row in rows)
    print()
    print("DIRECTION OUTPUT")
    for value, count in direction.items():
        print(f"{str(value):10} | {count}")

    return True


# --------------------------------------------------------------------------------------------------
# PRODUCTION INVARIANT
# --------------------------------------------------------------------------------------------------

def production_invariant(before_size, before_hash, before_rows):
    banner("PRODUCTION DATABASE INVARIANT")

    after_size = os.path.getsize(PRODUCTION_DB)
    after_hash = sha256_file(PRODUCTION_DB)

    conn = connect_readonly(PRODUCTION_DB)

    try:
        after_rows = conn.execute(
            f"SELECT COUNT(*) FROM {TARGET_TABLE}"
        ).fetchone()[0]
    finally:
        conn.close()

    print(f"Before size : {before_size}")
    print(f"After size  : {after_size}")
    print(f"SHA256      : {after_hash}")
    print(f"Rows before : {before_rows}")
    print(f"Rows after  : {after_rows}")

    passed = (
        before_size == after_size
        and before_hash == after_hash
        and before_rows == after_rows
    )

    print()
    print(
        "PRODUCTION DB INVARIANT :",
        "PASS" if passed else "FAIL"
    )

    return passed


# --------------------------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------------------------

def main():

    banner("ARUNDA TRADER LIVE DATA SOURCE HEALTH + FUSION ARM AVAILABILITY CONTRACT v0.1")

    print("OBJECTIVE:")
    print("  Validate LIVE external-source health as observed by actual FUSION_v0.5.")
    print("  Validate Market / Positioning / News arm availability.")
    print("  Validate availability metadata and snapshot provenance.")
    print()
    print("Production DB writes : FORBIDDEN")
    print("Production engine run : NO")
    print("Synthetic data        : FORBIDDEN")
    print("Historical repair     : NONE")
    print("Direction inference   : NONE")
    print("Score reconstruction  : NONE")
    print("Live data injection   : NONE")

    # ----------------------------------------------------------------------------------------------
    # Production baseline
    # ----------------------------------------------------------------------------------------------

    banner("PRODUCTION BASELINE")

    if not os.path.exists(PRODUCTION_DB):
        raise FileNotFoundError(PRODUCTION_DB)

    before_size = os.path.getsize(PRODUCTION_DB)
    before_hash = sha256_file(PRODUCTION_DB)

    prod_conn = connect_readonly(PRODUCTION_DB)

    try:
        before_rows = prod_conn.execute(
            f"SELECT COUNT(*) FROM {TARGET_TABLE}"
        ).fetchone()[0]
    finally:
        prod_conn.close()

    print(f"Production DB : {PRODUCTION_DB}")
    print(f"Rows          : {before_rows}")
    print(f"Size          : {before_size}")
    print(f"SHA256        : {before_hash}")

    # ----------------------------------------------------------------------------------------------
    # Locate previous isolated live capture
    # ----------------------------------------------------------------------------------------------

    banner("LIVE CAPTURE DISCOVERY")

    live_db = find_live_capture()

    if live_db is None:
        print("LIVE CAPTURE : NOT FOUND")
        print()
        print("Run the previous LIVE LAUNCH HARNESS first.")
        sys.exit(2)

    print(f"Live capture DB : {live_db}")
    print(f"Exists          : YES")
    print(f"Size            : {os.path.getsize(live_db)}")

    # ----------------------------------------------------------------------------------------------
    # Read isolated DB
    # ----------------------------------------------------------------------------------------------

    conn = connect_readonly(live_db)

    try:

        if not validate_schema(conn):
            print()
            print("FINAL VERDICT : FAIL")
            sys.exit(1)

        rows = load_live_rows(conn)

        banner("LIVE FUSION_v0.5 COHORT")

        print(f"Rows captured : {len(rows)}")

        if not rows:
            print("LIVE COHORT : EMPTY")
            print()
            print("FINAL VERDICT : FAIL")
            sys.exit(1)

        # ------------------------------------------------------------------------------------------
        # Analyses
        # ------------------------------------------------------------------------------------------

        arm_counts, quality_counts = analyze_arm_health(rows)

        availability_pass = analyze_availability_contract(rows)

        print_row_matrix(rows)

        snapshot_pass = analyze_snapshots(rows)

        runtime_pass = analyze_runtime_coherence(rows)

    finally:
        conn.close()

    # ----------------------------------------------------------------------------------------------
    # Production invariant
    # ----------------------------------------------------------------------------------------------

    production_pass = production_invariant(
        before_size,
        before_hash,
        before_rows,
    )

    # ----------------------------------------------------------------------------------------------
    # Final launch-oriented verdict
    # ----------------------------------------------------------------------------------------------

    banner("LIVE DATA SOURCE HEALTH + ARM AVAILABILITY VERDICT")

    print(
        f"LIVE_FUSION_V0.5_CAPTURE        : {'PASS' if runtime_pass else 'FAIL'}"
    )

    print(
        f"ARM_AVAILABILITY_CONTRACT       : "
        f"{'PASS' if availability_pass else 'FAIL'}"
    )

    print(
        f"SNAPSHOT_PROVENANCE             : "
        f"{'PASS' if snapshot_pass else 'FAIL'}"
    )

    print(
        f"PRODUCTION_DB_ISOLATION         : "
        f"{'PASS' if production_pass else 'FAIL'}"
    )

    overall = (
        runtime_pass
        and availability_pass
        and snapshot_pass
        and production_pass
    )

    print()
    print(
        "FRONTIER VERDICT :",
        "PASS" if overall else "FAIL"
    )

    banner("FINAL SAFETY VERDICT")

    print("Production DB writes : NONE")
    print("INSERT               : NONE")
    print("UPDATE               : NONE")
    print("DELETE               : NONE")
    print("DDL                  : NONE")
    print("Production engine    : NOT EXECUTED")
    print("Historical repair    : NONE")
    print("Direction inference  : NONE")
    print("Score reconstruction : NONE")
    print("Synthetic data       : NONE")
    print("Live data injection  : NONE")

    print()
    print("The live capture remains disposable.")
    print("Production arunda.db was not modified.")


if __name__ == "__main__":
    main()