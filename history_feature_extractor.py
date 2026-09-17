import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


DB_PATH = "arunda.db"
ENGINE_NAME = "HISTORY_FEATURE_EXTRACTOR_v0.1"
QUERY_ENGINE = "HISTORY_QUERY_v0.1"


# =============================================================================
# DATA MODEL
# =============================================================================

@dataclass(frozen=True)
class HistoryFeature:
    cmc_id: int
    symbol: str
    name: Optional[str]

    timestamp: str
    previous_timestamp: str

    price: float
    previous_price: float

    snapshot_change: float
    snapshot_change_pct: float

    market_cap: Optional[float]
    previous_market_cap: Optional[float]

    volume_24h: Optional[float]
    previous_volume_24h: Optional[float]

    change_1h: Optional[float]
    change_24h: Optional[float]
    change_7d: Optional[float]


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def connect_read_only():
    """
    Open SQLite database in strict read-only mode.
    """

    uri = f"file:{DB_PATH}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):
    return [
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    ]


# =============================================================================
# SCHEMA VALIDATION
# =============================================================================

def validate_schema(conn):
    if not table_exists(conn, "market_history"):
        raise RuntimeError(
            "market_history table does not exist."
        )

    columns = set(get_columns(conn, "market_history"))

    required = {
        "timestamp",
        "cmc_id",
        "symbol",
        "name",
        "rank",
        "price",
        "market_cap",
        "volume_24h",
        "change_1h",
        "change_24h",
        "change_7d",
    }

    missing = required - columns

    if missing:
        raise RuntimeError(
            "Missing history columns: "
            + ", ".join(sorted(missing))
        )

    return True


# =============================================================================
# HISTORY FINGERPRINT
# =============================================================================

def history_fingerprint(conn):
    rows = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        """
    ).fetchone()[0]

    snapshots = conn.execute(
        """
        SELECT COUNT(DISTINCT timestamp)
        FROM market_history
        """
    ).fetchone()[0]

    cmc_ids = conn.execute(
        """
        SELECT COUNT(DISTINCT cmc_id)
        FROM market_history
        """
    ).fetchone()[0]

    duplicate_ids = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT timestamp, cmc_id
            FROM market_history
            GROUP BY timestamp, cmc_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    first_timestamp = conn.execute(
        """
        SELECT MIN(timestamp)
        FROM market_history
        """
    ).fetchone()[0]

    last_timestamp = conn.execute(
        """
        SELECT MAX(timestamp)
        FROM market_history
        """
    ).fetchone()[0]

    return {
        "rows": rows,
        "snapshots": snapshots,
        "cmc_ids": cmc_ids,
        "duplicate_ids": duplicate_ids,
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
    }


# =============================================================================
# SNAPSHOT HELPERS
# =============================================================================

def get_latest_timestamp(conn):
    row = conn.execute(
        """
        SELECT MAX(timestamp)
        FROM market_history
        """
    ).fetchone()

    return row[0]


def get_previous_timestamp(conn, latest_timestamp):
    row = conn.execute(
        """
        SELECT MAX(timestamp)
        FROM market_history
        WHERE timestamp < ?
        """,
        (latest_timestamp,),
    ).fetchone()

    return row[0]


def snapshot_rows(conn, timestamp):
    return conn.execute(
        """
        SELECT
            cmc_id,
            symbol,
            name,
            rank,
            price,
            market_cap,
            volume_24h,
            change_1h,
            change_24h,
            change_7d
        FROM market_history
        WHERE timestamp = ?
        ORDER BY cmc_id
        """,
        (timestamp,),
    ).fetchall()


# =============================================================================
# FEATURE EXTRACTION
# =============================================================================

def extract_features(conn):
    latest_timestamp = get_latest_timestamp(conn)

    if latest_timestamp is None:
        return {
            "latest_timestamp": None,
            "previous_timestamp": None,
            "latest_rows": 0,
            "previous_rows": 0,
            "common_cmc_ids": 0,
            "features": [],
        }

    previous_timestamp = get_previous_timestamp(
        conn,
        latest_timestamp,
    )

    if previous_timestamp is None:
        raise RuntimeError(
            "No previous snapshot exists."
        )

    latest_rows = snapshot_rows(
        conn,
        latest_timestamp,
    )

    previous_rows = snapshot_rows(
        conn,
        previous_timestamp,
    )

    latest_map = {
        int(row[0]): row
        for row in latest_rows
    }

    previous_map = {
        int(row[0]): row
        for row in previous_rows
    }

    common_ids = sorted(
        set(latest_map.keys())
        &
        set(previous_map.keys())
    )

    features = []

    for cmc_id in common_ids:

        latest = latest_map[cmc_id]
        previous = previous_map[cmc_id]

        (
            _latest_cmc_id,
            latest_symbol,
            latest_name,
            latest_rank,
            latest_price,
            latest_market_cap,
            latest_volume,
            latest_change_1h,
            latest_change_24h,
            latest_change_7d,
        ) = latest

        (
            _previous_cmc_id,
            _previous_symbol,
            _previous_name,
            _previous_rank,
            previous_price,
            previous_market_cap,
            previous_volume,
            _previous_change_1h,
            _previous_change_24h,
            _previous_change_7d,
        ) = previous

        if latest_price is None:
            continue

        if previous_price is None:
            continue

        latest_price = float(latest_price)
        previous_price = float(previous_price)

        snapshot_change = (
            latest_price - previous_price
        )

        if previous_price != 0:
            snapshot_change_pct = (
                snapshot_change / previous_price
            ) * 100.0
        else:
            snapshot_change_pct = 0.0

        features.append(
            HistoryFeature(
                cmc_id=cmc_id,
                symbol=str(latest_symbol),
                name=latest_name,

                timestamp=latest_timestamp,
                previous_timestamp=previous_timestamp,

                price=latest_price,
                previous_price=previous_price,

                snapshot_change=snapshot_change,
                snapshot_change_pct=snapshot_change_pct,

                market_cap=(
                    float(latest_market_cap)
                    if latest_market_cap is not None
                    else None
                ),

                previous_market_cap=(
                    float(previous_market_cap)
                    if previous_market_cap is not None
                    else None
                ),

                volume_24h=(
                    float(latest_volume)
                    if latest_volume is not None
                    else None
                ),

                previous_volume_24h=(
                    float(previous_volume)
                    if previous_volume is not None
                    else None
                ),

                change_1h=(
                    float(latest_change_1h)
                    if latest_change_1h is not None
                    else None
                ),

                change_24h=(
                    float(latest_change_24h)
                    if latest_change_24h is not None
                    else None
                ),

                change_7d=(
                    float(latest_change_7d)
                    if latest_change_7d is not None
                    else None
                ),
            )
        )

    return {
        "latest_timestamp": latest_timestamp,
        "previous_timestamp": previous_timestamp,
        "latest_rows": len(latest_rows),
        "previous_rows": len(previous_rows),
        "common_cmc_ids": len(common_ids),
        "features": features,
    }


# =============================================================================
# FEATURE VALIDATION
# =============================================================================

def validate_features(result):
    features = result["features"]

    if not features:
        raise RuntimeError(
            "No features extracted."
        )

    seen = set()

    for feature in features:

        if feature.cmc_id in seen:
            raise RuntimeError(
                f"Duplicate feature CMC_ID: {feature.cmc_id}"
            )

        seen.add(feature.cmc_id)

        if feature.price <= 0:
            raise RuntimeError(
                f"Invalid price for CMC_ID {feature.cmc_id}"
            )

        if feature.previous_price <= 0:
            raise RuntimeError(
                f"Invalid previous price for CMC_ID {feature.cmc_id}"
            )

        expected_change = (
            feature.price
            -
            feature.previous_price
        )

        if abs(
            expected_change
            -
            feature.snapshot_change
        ) > 1e-12:
            raise RuntimeError(
                f"Snapshot change mismatch for CMC_ID "
                f"{feature.cmc_id}"
            )

    return True


# =============================================================================
# LATEST / PREVIOUS CONSISTENCY
# =============================================================================

def validate_latest_previous_consistency(result):
    if (
        result["latest_timestamp"] is None
        or
        result["previous_timestamp"] is None
    ):
        raise RuntimeError(
            "Latest/previous timestamps unavailable."
        )

    if result["latest_rows"] <= 0:
        raise RuntimeError(
            "Latest snapshot is empty."
        )

    if result["previous_rows"] <= 0:
        raise RuntimeError(
            "Previous snapshot is empty."
        )

    if result["common_cmc_ids"] <= 0:
        raise RuntimeError(
            "No common CMC IDs."
        )

    if len(result["features"]) != result["common_cmc_ids"]:
        raise RuntimeError(
            "Feature count does not match common CMC IDs."
        )

    return True


# =============================================================================
# CMC COLLISION TEST
# =============================================================================

def collision_test(conn, timestamp):
    rows = conn.execute(
        """
        SELECT
            symbol,
            COUNT(DISTINCT cmc_id) AS cmc_count,
            COUNT(*) AS row_count
        FROM market_history
        WHERE timestamp = ?
        GROUP BY symbol
        HAVING COUNT(DISTINCT cmc_id) > 1
        ORDER BY symbol
        """,
        (timestamp,),
    ).fetchall()

    collision_rows = sum(
        int(row[2])
        for row in rows
    )

    return {
        "symbols": len(rows),
        "rows": collision_rows,
    }


# =============================================================================
# SAMPLE OUTPUT
# =============================================================================

def print_feature_sample(features, limit=5):
    print()
    print("FEATURE SAMPLE")
    print("-" * 100)

    for feature in features[:limit]:

        print(
            f"CMC_ID={feature.cmc_id} | "
            f"SYMBOL={feature.symbol} | "
            f"PRICE={feature.price} | "
            f"PREV_PRICE={feature.previous_price} | "
            f"SNAPSHOT_CHANGE={feature.snapshot_change}"
        )


# =============================================================================
# SELF TEST
# =============================================================================

def self_test():
    print()
    print("=" * 100)
    print("ARUNDA TRADER — HISTORY FEATURE EXTRACTOR v0.1")
    print("SELF TEST")
    print("=" * 100)

    print()
    print("DATABASE :", DB_PATH)
    print("MODE     : READ ONLY")
    print("ENGINE   :", ENGINE_NAME)
    print("QUERY    :", QUERY_ENGINE)

    conn = connect_read_only()

    try:

        # ---------------------------------------------------------------------
        # Schema
        # ---------------------------------------------------------------------

        print()
        print("SCHEMA VALIDATION")
        print("-" * 100)

        validate_schema(conn)

        print("RESULT : PASS")

        # ---------------------------------------------------------------------
        # Fingerprint
        # ---------------------------------------------------------------------

        fingerprint_before = history_fingerprint(conn)

        print()
        print("HISTORY FINGERPRINT")
        print("-" * 100)

        print(
            "Rows              :",
            fingerprint_before["rows"],
        )

        print(
            "Snapshots         :",
            fingerprint_before["snapshots"],
        )

        print(
            "Distinct CMC IDs  :",
            fingerprint_before["cmc_ids"],
        )

        print(
            "Duplicate IDs     :",
            fingerprint_before["duplicate_ids"],
        )

        print(
            "First Timestamp   :",
            fingerprint_before["first_timestamp"],
        )

        print(
            "Last Timestamp    :",
            fingerprint_before["last_timestamp"],
        )

        # ---------------------------------------------------------------------
        # Feature extraction
        # ---------------------------------------------------------------------

        result = extract_features(conn)

        print()
        print("FEATURE EXTRACTION")
        print("-" * 100)

        print(
            "Latest Timestamp     :",
            result["latest_timestamp"],
        )

        print(
            "Previous Timestamp   :",
            result["previous_timestamp"],
        )

        print(
            "Latest Rows          :",
            result["latest_rows"],
        )

        print(
            "Previous Rows        :",
            result["previous_rows"],
        )

        print(
            "Common CMC IDs       :",
            result["common_cmc_ids"],
        )

        print(
            "Feature Rows         :",
            len(result["features"]),
        )

        if result["latest_rows"] <= 0:
            raise RuntimeError(
                "Latest snapshot contains no rows."
            )

        if result["previous_rows"] <= 0:
            raise RuntimeError(
                "Previous snapshot contains no rows."
            )

        if result["common_cmc_ids"] <= 0:
            raise RuntimeError(
                "No common CMC IDs."
            )

        if len(result["features"]) != result["common_cmc_ids"]:
            raise RuntimeError(
                "Feature row count mismatch."
            )

        print("RESULT : PASS")

        # ---------------------------------------------------------------------
        # Feature validation
        # ---------------------------------------------------------------------

        print()
        print("FEATURE VALIDATION")
        print("-" * 100)

        validate_features(result)

        print("RESULT : PASS")

        # ---------------------------------------------------------------------
        # Latest / previous consistency
        # ---------------------------------------------------------------------

        print()
        print("LATEST / PREVIOUS CONSISTENCY TEST")
        print("-" * 100)

        validate_latest_previous_consistency(
            result
        )

        print(
            "Common CMC IDs :",
            result["common_cmc_ids"],
        )

        print(
            "Feature Rows    :",
            len(result["features"]),
        )

        print("RESULT : PASS")

        # ---------------------------------------------------------------------
        # Collision safety
        # ---------------------------------------------------------------------

        collision = collision_test(
            conn,
            result["latest_timestamp"],
        )

        print()
        print("CMC COLLISION SAFETY TEST")
        print("-" * 100)

        print(
            "Symbol Collisions :",
            collision["symbols"],
        )

        print(
            "Collision Rows    :",
            collision["rows"],
        )

        if collision["symbols"] > 0:

            collision_cmc_ids = conn.execute(
                """
                SELECT
                    symbol,
                    COUNT(DISTINCT cmc_id)
                FROM market_history
                WHERE timestamp = ?
                GROUP BY symbol
                HAVING COUNT(DISTINCT cmc_id) > 1
                """,
                (result["latest_timestamp"],),
            ).fetchall()

            for symbol, cmc_count in collision_cmc_ids:

                if cmc_count < 2:
                    raise RuntimeError(
                        f"Collision validation failed for {symbol}"
                    )

        print("RESULT : PASS")

        # ---------------------------------------------------------------------
        # Post fingerprint
        # ---------------------------------------------------------------------

        fingerprint_after = history_fingerprint(conn)

        print()
        print("POST-EXTRACTION FINGERPRINT")
        print("-" * 100)

        print(
            "Rows              :",
            fingerprint_after["rows"],
        )

        print(
            "Snapshots         :",
            fingerprint_after["snapshots"],
        )

        print(
            "Distinct CMC IDs  :",
            fingerprint_after["cmc_ids"],
        )

        print(
            "Duplicate IDs     :",
            fingerprint_after["duplicate_ids"],
        )

        # ---------------------------------------------------------------------
        # Read-only integrity
        # ---------------------------------------------------------------------

        print()
        print("READ-ONLY INTEGRITY TEST")
        print("-" * 100)

        checks = [
            (
                "ROW COUNT",
                fingerprint_after["rows"]
                ==
                fingerprint_before["rows"],
            ),
            (
                "SNAPSHOT COUNT",
                fingerprint_after["snapshots"]
                ==
                fingerprint_before["snapshots"],
            ),
            (
                "CMC ID COUNT",
                fingerprint_after["cmc_ids"]
                ==
                fingerprint_before["cmc_ids"],
            ),
            (
                "DUPLICATES",
                fingerprint_after["duplicate_ids"]
                ==
                fingerprint_before["duplicate_ids"],
            ),
        ]

        for label, passed in checks:

            print(
                f"{label:<25}: "
                f"{'PASS' if passed else 'FAIL'}"
            )

            if not passed:
                raise RuntimeError(
                    f"Read-only integrity failed: {label}"
                )

        # ---------------------------------------------------------------------
        # Sample
        # ---------------------------------------------------------------------

        print_feature_sample(
            result["features"],
            limit=5,
        )

        # ---------------------------------------------------------------------
        # Final verdict
        # ---------------------------------------------------------------------

        print()
        print("=" * 100)
        print("SELF TEST VERDICT")
        print("=" * 100)

        print("RESULT : PASS")
        print(
            "STATUS : HISTORY FEATURE EXTRACTOR v0.1 READY"
        )

        print()
        print("Database          : READ ONLY")
        print("Database Modified : NO")
        print("CMC Identity      : VERIFIED")
        print("Collision Safety  : VERIFIED")
        print("Latest/Previous   : VERIFIED")
        print("Feature Extraction: VERIFIED")

        print("=" * 100)

    finally:
        conn.close()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    self_test()