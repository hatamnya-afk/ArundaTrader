import sqlite3
import math
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, Any


# =============================================================================
# ARUNDA MARKET HISTORY INGESTION GUARD v0.1
# =============================================================================
#
# PURPOSE
# -------
# Identity Resolution + Ingestion Validation
#
# IMPORTANT
# ---------
# This module does NOT repair historical data.
# This module does NOT delete historical rows.
# This module does NOT modify existing market_history rows.
# This module does NOT generate fake market data.
#
# Pipeline
# --------
#
# RAW MARKET RECORD
#       |
#       v
# IDENTITY RESOLUTION
#       |
#       v
# INGESTION VALIDATION
#       |
#       +---- INVALID
#       |
#       +---- COLLISION
#       |
#       +---- DUPLICATE
#       |
#       v
# ACCEPT
#
# The canonical identity is deliberately NOT based on symbol alone.
#
# =============================================================================


# =============================================================================
# CONFIGURATION
# =============================================================================

DB = "arunda.db"

ENGINE_VERSION = "INGESTION_GUARD_v0.1"

TABLE = "market_history"

VALID_DECISIONS = {
    "ACCEPT",
    "DUPLICATE",
    "COLLISION",
    "INVALID",
}


# =============================================================================
# RESULT OBJECT
# =============================================================================

@dataclass
class GuardResult:

    decision: str

    reason: str

    canonical_asset_id: Optional[str] = None

    symbol: Optional[str] = None

    name: Optional[str] = None

    timestamp: Optional[str] = None

    source: Optional[str] = None

    source_timestamp: Optional[str] = None


# =============================================================================
# DATABASE
# =============================================================================

def connect_database():

    conn = sqlite3.connect(DB)

    conn.row_factory = sqlite3.Row

    return conn


# =============================================================================
# UTILITY
# =============================================================================

def safe_float(value):

    try:

        if value is None:
            return None

        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except Exception:

        return None


def clean_text(value):

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def normalize_symbol(value):

    value = clean_text(value)

    if value is None:
        return None

    return value.upper()


def normalize_name(value):

    value = clean_text(value)

    if value is None:
        return None

    return " ".join(
        value.lower().split()
    )


def normalize_source(value):

    value = clean_text(value)

    if value is None:
        return None

    return value.upper()


def normalize_timestamp(value):

    value = clean_text(value)

    if value is None:
        return None

    try:

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

        if parsed.tzinfo is None:

            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        parsed = parsed.astimezone(
            timezone.utc
        )

        return parsed.isoformat()

    except Exception:

        return None


# =============================================================================
# CANONICAL IDENTITY
# =============================================================================
#
# symbol alone is NOT identity.
#
# We use the strongest available identity information.
#
# Priority:
#
# 1. explicit provider/source identity
# 2. source + symbol + name
#
# The guard deliberately refuses to silently merge two different names
# carrying the same symbol.
#
# =============================================================================

def build_canonical_asset_id(
    symbol,
    name,
    source,
):

    symbol = normalize_symbol(symbol)

    name = normalize_name(name)

    source = normalize_source(source)

    if symbol is None:

        return None

    if name is None:

        return None

    if source is None:

        return None

    identity_string = (
        f"{source}|{symbol}|{name}"
    )

    digest = hashlib.sha256(
        identity_string.encode(
            "utf-8"
        )
    ).hexdigest()

    return (
        "ARUNDA-"
        + digest[:24]
    )


# =============================================================================
# INPUT VALIDATION
# =============================================================================

def validate_required_identity_fields(
    record
):

    symbol = normalize_symbol(
        record.get("symbol")
    )

    name = clean_text(
        record.get("name")
    )

    source = normalize_source(
        record.get("source")
    )

    if symbol is None:

        return False, "MISSING_SYMBOL"

    if name is None:

        return False, "MISSING_NAME"

    if source is None:

        return False, "MISSING_SOURCE"

    return True, "OK"


def validate_timestamp_fields(
    record
):

    timestamp = normalize_timestamp(
        record.get("timestamp")
    )

    source_timestamp = normalize_timestamp(
        record.get("source_timestamp")
    )

    if timestamp is None:

        return False, (
            "INVALID_TIMESTAMP"
        )

    if source_timestamp is None:

        return False, (
            "INVALID_SOURCE_TIMESTAMP"
        )

    return True, "OK"


def validate_market_values(
    record
):

    price = safe_float(
        record.get("price")
    )

    volume_24h = safe_float(
        record.get("volume_24h")
    )

    market_cap = safe_float(
        record.get("market_cap")
    )

    if price is None:

        return False, "INVALID_PRICE"

    if price <= 0:

        return False, "NON_POSITIVE_PRICE"

    if volume_24h is not None:

        if volume_24h < 0:

            return False, (
                "NEGATIVE_VOLUME"
            )

    if market_cap is not None:

        if market_cap < 0:

            return False, (
                "NEGATIVE_MARKET_CAP"
            )

    return True, "OK"


# =============================================================================
# DATABASE IDENTITY LOOKUP
# =============================================================================

def find_identity_collisions(
    conn,
    symbol,
    timestamp,
    source
):

    rows = conn.execute(
        f"""
        SELECT
            id,
            symbol,
            name,
            source,
            timestamp,
            source_timestamp,
            price,
            volume_24h
        FROM {TABLE}
        WHERE
            UPPER(TRIM(symbol)) = ?
            AND timestamp = ?
            AND (
                source = ?
                OR source IS NULL
            )
        ORDER BY id ASC
        """,
        (
            symbol,
            timestamp,
            source,
        )
    ).fetchall()

    return rows


# =============================================================================
# SAME IDENTITY / TIMESTAMP LOOKUP
# =============================================================================

def find_same_identity_timestamp(
    conn,
    symbol,
    name,
    timestamp,
    source
):

    rows = conn.execute(
        f"""
        SELECT
            id,
            symbol,
            name,
            source,
            timestamp,
            source_timestamp,
            price,
            volume_24h
        FROM {TABLE}
        WHERE
            UPPER(TRIM(symbol)) = ?
            AND LOWER(TRIM(name)) = ?
            AND timestamp = ?
            AND (
                source = ?
                OR source IS NULL
            )
        ORDER BY id ASC
        """,
        (
            symbol,
            normalize_name(name),
            timestamp,
            source,
        )
    ).fetchall()

    return rows


# =============================================================================
# COLLISION ANALYSIS
# =============================================================================

def classify_existing_rows(
    rows,
    symbol,
    name,
    price,
    volume_24h,
):

    if not rows:

        return "NONE"

    normalized_name = normalize_name(
        name
    )

    for row in rows:

        existing_name = normalize_name(
            row["name"]
        )

        if (
            existing_name is not None
            and existing_name
            != normalized_name
        ):

            return "COLLISION"

    for row in rows:

        existing_price = safe_float(
            row["price"]
        )

        existing_volume = safe_float(
            row["volume_24h"]
        )

        price_conflict = (
            existing_price is not None
            and price is not None
            and existing_price
            != price
        )

        volume_conflict = (
            existing_volume is not None
            and volume_24h is not None
            and existing_volume
            != volume_24h
        )

        if (
            price_conflict
            or volume_conflict
        ):

            return "DUPLICATE_CONFLICT"

    return "DUPLICATE"


# =============================================================================
# MAIN GUARD
# =============================================================================

def inspect_record(
    conn,
    record,
):

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    identity_ok, identity_reason = (
        validate_required_identity_fields(
            record
        )
    )

    if not identity_ok:

        return GuardResult(
            decision="INVALID",
            reason=identity_reason,
        )

    symbol = normalize_symbol(
        record.get("symbol")
    )

    name = clean_text(
        record.get("name")
    )

    source = normalize_source(
        record.get("source")
    )

    canonical_asset_id = (
        build_canonical_asset_id(
            symbol=symbol,
            name=name,
            source=source,
        )
    )

    if canonical_asset_id is None:

        return GuardResult(
            decision="INVALID",
            reason="IDENTITY_RESOLUTION_FAILED",
            symbol=symbol,
            name=name,
            source=source,
        )

    # -------------------------------------------------------------------------
    # Timestamp
    # -------------------------------------------------------------------------

    timestamp_ok, timestamp_reason = (
        validate_timestamp_fields(
            record
        )
    )

    if not timestamp_ok:

        return GuardResult(
            decision="INVALID",
            reason=timestamp_reason,
            canonical_asset_id=(
                canonical_asset_id
            ),
            symbol=symbol,
            name=name,
            source=source,
        )

    timestamp = normalize_timestamp(
        record.get("timestamp")
    )

    source_timestamp = (
        normalize_timestamp(
            record.get("source_timestamp")
        )
    )

    # -------------------------------------------------------------------------
    # Market values
    # -------------------------------------------------------------------------

    market_ok, market_reason = (
        validate_market_values(
            record
        )
    )

    if not market_ok:

        return GuardResult(
            decision="INVALID",
            reason=market_reason,
            canonical_asset_id=(
                canonical_asset_id
            ),
            symbol=symbol,
            name=name,
            timestamp=timestamp,
            source=source,
            source_timestamp=(
                source_timestamp
            ),
        )

    price = safe_float(
        record.get("price")
    )

    volume_24h = safe_float(
        record.get("volume_24h")
    )

    # -------------------------------------------------------------------------
    # Same identity + timestamp
    # -------------------------------------------------------------------------

    same_identity_rows = (
        find_same_identity_timestamp(
            conn=conn,
            symbol=symbol,
            name=name,
            timestamp=timestamp,
            source=source,
        )
    )

    same_identity_classification = (
        classify_existing_rows(
            rows=same_identity_rows,
            symbol=symbol,
            name=name,
            price=price,
            volume_24h=volume_24h,
        )
    )

    if same_identity_classification == (
        "DUPLICATE"
    ):

        return GuardResult(
            decision="DUPLICATE",
            reason=(
                "IDENTITY_AND_TIMESTAMP_ALREADY_EXISTS"
            ),
            canonical_asset_id=(
                canonical_asset_id
            ),
            symbol=symbol,
            name=name,
            timestamp=timestamp,
            source=source,
            source_timestamp=(
                source_timestamp
            ),
        )

    if same_identity_classification == (
        "DUPLICATE_CONFLICT"
    ):

        return GuardResult(
            decision="COLLISION",
            reason=(
                "SAME_IDENTITY_TIMESTAMP_HAS_DIFFERENT_VALUES"
            ),
            canonical_asset_id=(
                canonical_asset_id
            ),
            symbol=symbol,
            name=name,
            timestamp=timestamp,
            source=source,
            source_timestamp=(
                source_timestamp
            ),
        )

    # -------------------------------------------------------------------------
    # Symbol collision
    # -------------------------------------------------------------------------

    collision_rows = (
        find_identity_collisions(
            conn=conn,
            symbol=symbol,
            timestamp=timestamp,
            source=source,
        )
    )

    for row in collision_rows:

        existing_name = normalize_name(
            row["name"]
        )

        incoming_name = normalize_name(
            name
        )

        if (
            existing_name is not None
            and incoming_name is not None
            and existing_name
            != incoming_name
        ):

            return GuardResult(
                decision="COLLISION",
                reason=(
                    "SYMBOL_REUSED_BY_DIFFERENT_ASSET"
                ),
                canonical_asset_id=(
                    canonical_asset_id
                ),
                symbol=symbol,
                name=name,
                timestamp=timestamp,
                source=source,
                source_timestamp=(
                    source_timestamp
                ),
            )

    # -------------------------------------------------------------------------
    # ACCEPT
    # -------------------------------------------------------------------------

    return GuardResult(
        decision="ACCEPT",
        reason="VALID_NEW_RECORD",
        canonical_asset_id=(
            canonical_asset_id
        ),
        symbol=symbol,
        name=name,
        timestamp=timestamp,
        source=source,
        source_timestamp=(
            source_timestamp
        ),
    )


# =============================================================================
# SAFE INSERT
# =============================================================================
#
# IMPORTANT:
# This function inserts ONLY records that passed the guard.
#
# Existing historical rows are NEVER modified.
# =============================================================================

def insert_if_accepted(
    conn,
    record,
):

    result = inspect_record(
        conn,
        record,
    )

    if result.decision != "ACCEPT":

        return result

    conn.execute(
        f"""
        INSERT INTO {TABLE} (
            timestamp,
            symbol,
            name,
            rank,
            price,
            market_cap,
            volume_24h,
            change_1h,
            change_24h,
            change_7d,
            source,
            source_timestamp,
            engine_version,
            created_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            result.timestamp,
            result.symbol,
            record.get("name"),
            record.get("rank"),
            safe_float(
                record.get("price")
            ),
            safe_float(
                record.get("market_cap")
            ),
            safe_float(
                record.get("volume_24h")
            ),
            safe_float(
                record.get("change_1h")
            ),
            safe_float(
                record.get("change_24h")
            ),
            safe_float(
                record.get("change_7d")
            ),
            result.source,
            result.source_timestamp,
            ENGINE_VERSION,
            datetime.now(
                timezone.utc
            ).isoformat(),
        ),
    )

    return result


# =============================================================================
# DIAGNOSTIC MODE
# =============================================================================

def print_result(
    result
):

    print(
        f"{result.decision:<10}"
        f" | {result.reason:<48}"
        f" | SYMBOL={result.symbol}"
        f" | NAME={result.name}"
    )


# =============================================================================
# DATABASE INSPECTION
# =============================================================================

def inspect_schema(
    conn
):

    rows = conn.execute(
        f"PRAGMA table_info({TABLE})"
    ).fetchall()

    print()
    print("=" * 78)
    print("MARKET HISTORY SCHEMA")
    print("=" * 78)

    for row in rows:

        print(
            f"{row['name']:<22}"
            f" | TYPE={row['type']:<12}"
            f" | NOT_NULL={row['notnull']}"
            f" | PK={row['pk']}"
        )


def database_summary(
    conn
):

    row = conn.execute(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT symbol)
                AS symbols,
            COUNT(DISTINCT timestamp)
                AS timestamps,
            COUNT(DISTINCT source)
                AS sources
        FROM {TABLE}
        """
    ).fetchone()

    print()
    print("=" * 78)
    print("DATABASE SUMMARY")
    print("=" * 78)

    print(
        f"Rows              : "
        f"{row['total_rows']}"
    )

    print(
        f"Distinct Symbols  : "
        f"{row['symbols']}"
    )

    print(
        f"Distinct Timestamps: "
        f"{row['timestamps']}"
    )

    print(
        f"Distinct Sources   : "
        f"{row['sources']}"
    )


# =============================================================================
# DEMONSTRATION AGAINST EXISTING DATABASE
# =============================================================================

def run_identity_collision_audit(
    conn
):

    rows = conn.execute(
        f"""
        SELECT
            timestamp,
            symbol,
            COUNT(*) AS row_count,
            COUNT(
                DISTINCT LOWER(
                    TRIM(COALESCE(name, ''))
                )
            ) AS asset_names
        FROM {TABLE}
        GROUP BY
            timestamp,
            symbol
        HAVING
            COUNT(*) > 1
        ORDER BY
            row_count DESC,
            timestamp ASC
        LIMIT 25
        """
    ).fetchall()

    print()
    print("=" * 78)
    print("SYMBOL / TIMESTAMP COLLISION AUDIT")
    print("=" * 78)

    if not rows:

        print(
            "No symbol/timestamp collisions detected."
        )

        return

    for row in rows:

        print(
            f"{row['timestamp']}"
            f" | {row['symbol']:<8}"
            f" | ROWS={row['row_count']:<3}"
            f" | ASSETS={row['asset_names']}"
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print("ARUNDA MARKET HISTORY INGESTION GUARD v0.1")
    print("=" * 78)

    print(
        f"Database        : {DB}"
    )

    print(
        f"History Table   : {TABLE}"
    )

    print(
        f"Engine Version  : {ENGINE_VERSION}"
    )

    print(
        "Mode            : VALIDATION / SAFE INSERT"
    )

    print(
        "Historical Repair: DISABLED"
    )

    print(
        "Delete          : DISABLED"
    )

    print(
        "Fake Data       : DISABLED"
    )

    print("=" * 78)

    conn = None

    try:

        conn = connect_database()

        inspect_schema(
            conn
        )

        database_summary(
            conn
        )

        run_identity_collision_audit(
            conn
        )

        print()
        print("=" * 78)
        print("GUARD STATUS")
        print("=" * 78)

        print(
            "IDENTITY RESOLUTION : READY"
        )

        print(
            "SYMBOL-ONLY IDENTITY: DISABLED"
        )

        print(
            "HISTORICAL REPAIR   : DISABLED"
        )

        print(
            "DELETION            : DISABLED"
        )

        print(
            "FAKE DATA            : DISABLED"
        )

        print("=" * 78)
        print("ARUNDA INGESTION GUARD v0.1 READY")
        print("=" * 78)

    except Exception as exc:

        print()
        print(
            "GUARD STATUS : FAILED"
        )

        print(
            f"ERROR        : {exc}"
        )

        raise

    finally:

        if conn is not None:

            conn.close()


if __name__ == "__main__":

    main()