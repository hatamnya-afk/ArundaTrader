import sqlite3
from pathlib import Path
from collections import Counter


# ============================================================
# ARUNDA TRADER
# LAUNCH READINESS GATE v0.3
# ============================================================

DB_PATH = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

TARGET_TABLE = "fusion_signals"

CURRENT_ENGINE = "FUSION_v0.5"

VALID_DIRECTIONS = {"LONG", "SHORT", "FLAT"}

# Historical engines are NOT launch blockers.
LEGACY_ENGINES = {
    "FUSION_v0.2",
    "FUSION_v0.3",
    "FUSION_v0.4",
}


# ============================================================
# UTILITIES
# ============================================================

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def get_connection():
    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row
    return conn


def get_columns(conn):
    rows = conn.execute(
        f"PRAGMA table_info({TARGET_TABLE})"
    ).fetchall()

    return [row["name"] for row in rows]


def load_all_rows(conn):
    return conn.execute(
        f"""
        SELECT
            id,
            timestamp,
            asset,
            fused_score,
            confidence,
            regime,
            data_quality,
            engine_version,
            snapshot_id,
            signal_strength,
            entry_price,
            direction
        FROM {TARGET_TABLE}
        ORDER BY id
        """
    ).fetchall()


# ============================================================
# MAIN
# ============================================================

def main():

    banner("OUTCOME_v0.3 LAUNCH READINESS GATE v0.3")

    print(f"Database       : {DB_PATH}")
    print(f"Target table   : {TARGET_TABLE}")
    print()
    print("MODE           : READ ONLY")
    print("PRODUCTION DB  : NEVER MODIFIED")
    print("ENGINE RUN     : NO")
    print()
    print("DESIGN:")
    print("  Historical legacy rows are informational.")
    print("  Current launch cohort is evaluated structurally.")
    print("  Historical direction is NOT reconstructed.")
    print("  Historical entry_price is NOT reconstructed.")
    print("  Universe is NOT treated as final.")
    print("  No live data is injected.")
    print()

    # --------------------------------------------------------
    # CONNECTION
    # --------------------------------------------------------

    conn = get_connection()

    # --------------------------------------------------------
    # SCHEMA
    # --------------------------------------------------------

    banner("REAL PRODUCTION SCHEMA")

    columns = get_columns(conn)

    print(f"Columns discovered : {len(columns)}")

    required = {
        "id",
        "timestamp",
        "asset",
        "fused_score",
        "confidence",
        "regime",
        "data_quality",
        "engine_version",
        "snapshot_id",
        "signal_strength",
        "entry_price",
        "direction",
    }

    missing = sorted(required - set(columns))

    if missing:
        print("SCHEMA : FAIL")
        print("Missing:", missing)
        conn.close()
        return

    print("SCHEMA : PASS")

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    rows = load_all_rows(conn)

    banner("DATABASE BASELINE")

    print(f"Total rows : {len(rows)}")

    # --------------------------------------------------------
    # ENGINE DISTRIBUTION
    # --------------------------------------------------------

    banner("ENGINE DISTRIBUTION")

    engine_counts = Counter(
        row["engine_version"]
        for row in rows
    )

    for engine, count in sorted(engine_counts.items()):
        print(f"{engine:<24} | {count}")

    # --------------------------------------------------------
    # LEGACY COHORT
    # --------------------------------------------------------

    legacy_rows = [
        row for row in rows
        if row["engine_version"] in LEGACY_ENGINES
    ]

    current_rows = [
        row for row in rows
        if row["engine_version"] == CURRENT_ENGINE
    ]

    banner("COHORT CLASSIFICATION")

    print(f"Legacy rows        : {len(legacy_rows)}")
    print(f"Current launch rows: {len(current_rows)}")

    print()
    print("Legacy rows are NOT launch blockers.")

    # --------------------------------------------------------
    # CURRENT LAUNCH COHORT
    # --------------------------------------------------------

    banner("CURRENT LAUNCH COHORT")

    if not current_rows:
        print("CURRENT LAUNCH COHORT : FAIL")
        print("No FUSION_v0.5 rows found.")
        conn.close()
        return

    assets = sorted({
        row["asset"]
        for row in current_rows
    })

    print(f"Rows   : {len(current_rows)}")
    print(f"Assets : {len(assets)}")
    print(f"Assets : {', '.join(assets)}")

    # --------------------------------------------------------
    # IDENTITY
    # --------------------------------------------------------

    banner("CURRENT COHORT IDENTITY")

    ids = [row["id"] for row in current_rows]

    if len(ids) == len(set(ids)):
        print("Identity : PASS")
    else:
        print("Identity : FAIL")

    # --------------------------------------------------------
    # DIRECTION
    # --------------------------------------------------------

    banner("CURRENT COHORT DIRECTION")

    invalid_direction = []

    direction_counts = Counter()

    for row in current_rows:

        direction = row["direction"]

        if direction not in VALID_DIRECTIONS:
            invalid_direction.append(
                (row["id"], row["asset"], direction)
            )
        else:
            direction_counts[direction] += 1

    if invalid_direction:

        print("Direction : FAIL")

        for item in invalid_direction:
            print(
                f"id={item[0]} asset={item[1]} "
                f"value={item[2]}"
            )

    else:

        print("Direction : PASS")

        for direction in sorted(direction_counts):
            print(
                f"{direction:<8} | "
                f"{direction_counts[direction]}"
            )

    # --------------------------------------------------------
    # ENTRY PRICE
    # --------------------------------------------------------

    banner("CURRENT COHORT ENTRY PRICE")

    missing_entry = []

    for row in current_rows:

        if row["entry_price"] is None:
            missing_entry.append(
                (row["id"], row["asset"])
            )

    if missing_entry:

        print("Entry price : FAIL")

        for item in missing_entry:
            print(
                f"id={item[0]} "
                f"asset={item[1]} "
                f"value=NULL"
            )

    else:

        print("Entry price : PASS")

        prices = [
            row["entry_price"]
            for row in current_rows
        ]

        print(
            f"Min : {min(prices)}"
        )

        print(
            f"Max : {max(prices)}"
        )

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    banner("CURRENT COHORT CONFIDENCE")

    missing_confidence = []

    invalid_confidence = []

    for row in current_rows:

        value = row["confidence"]

        if value is None:
            missing_confidence.append(
                (row["id"], row["asset"])
            )
            continue

        if not (0.0 <= float(value) <= 1.0):
            invalid_confidence.append(
                (row["id"], row["asset"], value)
            )

    if missing_confidence or invalid_confidence:

        print("Confidence : FAIL")

        for item in missing_confidence:
            print(
                f"id={item[0]} "
                f"asset={item[1]} "
                f"value=NULL"
            )

        for item in invalid_confidence:
            print(
                f"id={item[0]} "
                f"asset={item[1]} "
                f"value={item[2]}"
            )

    else:

        print("Confidence : PASS")

    # --------------------------------------------------------
    # REGIME
    # --------------------------------------------------------

    banner("CURRENT COHORT REGIME")

    missing_regime = [
        (row["id"], row["asset"])
        for row in current_rows
        if row["regime"] is None
    ]

    if missing_regime:

        print("Regime : FAIL")

        for item in missing_regime:
            print(
                f"id={item[0]} "
                f"asset={item[1]} "
                f"value=NULL"
            )

    else:

        print("Regime : PASS")

        regime_counts = Counter(
            row["regime"]
            for row in current_rows
        )

        for regime, count in sorted(regime_counts.items()):
            print(
                f"{regime:<20} | {count}"
            )

    # --------------------------------------------------------
    # DATA QUALITY
    # --------------------------------------------------------

    banner("CURRENT COHORT DATA QUALITY")

    quality_counts = Counter(
        row["data_quality"]
        for row in current_rows
    )

    for quality, count in sorted(quality_counts.items()):
        print(
            f"{str(quality):<20} | {count}"
        )

    # --------------------------------------------------------
    # SIGNAL STRENGTH
    # --------------------------------------------------------

    banner("CURRENT COHORT SIGNAL STRENGTH")

    strength_counts = Counter(
        row["signal_strength"]
        for row in current_rows
    )

    for strength, count in sorted(strength_counts.items()):
        print(
            f"{str(strength):<20} | {count}"
        )

    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------

    banner("CURRENT COHORT SNAPSHOT")

    snapshot_values = {
        row["snapshot_id"]
        for row in current_rows
    }

    print(
        f"Distinct snapshot IDs : "
        f"{len(snapshot_values)}"
    )

    for snapshot in sorted(
        str(x) for x in snapshot_values
    ):
        print(
            f"  {snapshot}"
        )

    # --------------------------------------------------------
    # UNIVERSE STATUS
    # --------------------------------------------------------

    banner("UNIVERSE STATUS")

    print(f"Assets currently represented : {len(assets)}")
    print(f"Assets                       : {', '.join(assets)}")
    print()
    print("UNIVERSE FINALITY : NOT FINAL")
    print("Universe expansion remains a future frontier.")
    print("This does NOT block the current engine launch gate.")

    # --------------------------------------------------------
    # LAUNCH GATE
    # --------------------------------------------------------

    direction_pass = not invalid_direction
    entry_pass = not missing_entry
    confidence_pass = not missing_confidence and not invalid_confidence
    regime_pass = not missing_regime
    identity_pass = len(ids) == len(set(ids))

    launch_pass = all([
        direction_pass,
        entry_pass,
        confidence_pass,
        regime_pass,
        identity_pass,
    ])

    banner("LAUNCH READINESS")

    print(
        f"CURRENT_ENGINE                  : {CURRENT_ENGINE}"
    )

    print(
        f"CURRENT_COHORT_ROWS             : {len(current_rows)}"
    )

    print(
        f"HISTORICAL_ROWS_IGNORED_AS_GATE : {len(legacy_rows)}"
    )

    print(
        f"IDENTITY_CONTRACT               : "
        f"{'PASS' if identity_pass else 'FAIL'}"
    )

    print(
        f"DIRECTION_CONTRACT              : "
        f"{'PASS' if direction_pass else 'FAIL'}"
    )

    print(
        f"ENTRY_PRICE_CONTRACT            : "
        f"{'PASS' if entry_pass else 'FAIL'}"
    )

    print(
        f"CONFIDENCE_CONTRACT             : "
        f"{'PASS' if confidence_pass else 'FAIL'}"
    )

    print(
        f"REGIME_CONTRACT                 : "
        f"{'PASS' if regime_pass else 'FAIL'}"
    )

    print(
        "HISTORICAL_REPAIR_REQUIRED      : NO"
    )

    print(
        "UNIVERSE_FINALITY_REQUIRED      : NO"
    )

    print()

    if launch_pass:

        print("LAUNCH READINESS : PASS")

    else:

        print("LAUNCH READINESS : FAIL")

    # --------------------------------------------------------
    # SAFETY
    # --------------------------------------------------------

    banner("FINAL SAFETY VERDICT")

    print("Production DB writes : NONE")
    print("INSERT               : NONE")
    print("UPDATE               : NONE")
    print("DELETE               : NONE")
    print("DDL                  : NONE")
    print("Production engine    : NOT EXECUTED")
    print("Historical repair    : NONE")
    print("Direction inference  : NONE")
    print("Entry-price repair   : NONE")
    print("Synthetic data      : NONE")
    print("Live data injection  : NONE")

    conn.close()


if __name__ == "__main__":
    main()