# =============================================================================
# ARUNDA TRADER
# MARKET TECHNICAL SOURCE INTEGRITY CHECK
# v0.2
# =============================================================================
#
# MODE
# ----
# READ ONLY
#
# PURPOSE
# -------
# Forensic / integrity inspection of market_technical.
#
# IMPORTANT
# ---------
# This script NEVER:
# - INSERT
# - UPDATE
# - DELETE
# - ALTER
# - CREATE
# - DROP
#
# It does NOT assume that market_technical contains technical_score.
# All checks are schema-aware.
#
# =============================================================================

from __future__ import annotations

import math
import sqlite3
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# CONFIG
# =============================================================================

ENGINE_VERSION = "MARKET_TECHNICAL_SOURCE_INTEGRITY_CHECK_v0.2"

DB_PATH = Path(__file__).resolve().parent / "arunda.db"

EXPECTED_ASSETS = [
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
]


# =============================================================================
# UTILS
# =============================================================================

def normalize_symbol(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().upper()


def normalize_status(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().upper()


def is_finite(value: Any) -> bool:
    if value is None:
        return False

    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def safe_identifier(name: str) -> str:

    if not name:
        raise ValueError("Empty SQL identifier")

    if not name.replace("_", "").isalnum():
        raise ValueError(
            f"Unsafe SQL identifier: {name}"
        )

    return name


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# DATABASE
# =============================================================================

def connect_database() -> sqlite3.Connection:

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


# =============================================================================
# SCHEMA
# =============================================================================

def table_exists(
    conn: sqlite3.Connection,
    table_name: str,
) -> bool:

    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def table_columns(
    conn: sqlite3.Connection,
    table_name: str,
) -> list[str]:

    safe_identifier(table_name)

    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [
        str(row["name"])
        for row in rows
    ]


# =============================================================================
# COLUMN RESOLUTION
# =============================================================================

def first_existing_column(
    columns: set[str],
    candidates: list[str],
) -> str | None:

    for candidate in candidates:

        if candidate in columns:
            return candidate

    return None


# =============================================================================
# HEADER
# =============================================================================

def print_header() -> None:

    print("=" * 90)
    print(
        f"ARUNDA MARKET TECHNICAL SOURCE INTEGRITY CHECK {ENGINE_VERSION}"
    )
    print("=" * 90)

    print(
        f"Database       : {DB_PATH}"
    )

    print(
        "Mode           : READ ONLY"
    )

    print(
        "Target         : market_technical"
    )

    print(
        "Writes         : NONE"
    )

    print(
        "INSERT         : NONE"
    )

    print(
        "UPDATE         : NONE"
    )

    print(
        "DELETE         : NONE"
    )

    print(
        "ALTER          : NONE"
    )

    print(
        "CREATE         : NONE"
    )

    print(
        "DROP           : NONE"
    )

    print("=" * 90)


# =============================================================================
# SCHEMA REPORT
# =============================================================================

def print_schema(
    conn: sqlite3.Connection,
) -> set[str]:

    print()
    print("=" * 90)
    print("MARKET_TECHNICAL SCHEMA")
    print("=" * 90)

    columns = table_columns(
        conn,
        "market_technical",
    )

    column_set = set(columns)

    print(
        f"Column Count : {len(columns)}"
    )

    for index, column in enumerate(columns, start=1):

        print(
            f"{index:03d}. {column}"
        )

    print("=" * 90)

    return column_set


# =============================================================================
# GLOBAL COUNTS
# =============================================================================

def print_global_counts(
    conn: sqlite3.Connection,
    columns: set[str],
) -> None:

    print()
    print("=" * 90)
    print("GLOBAL SOURCE COUNTS")
    print("=" * 90)

    total_rows = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_technical
        """
    ).fetchone()[0]

    print(
        f"Total Rows                  : {int(total_rows)}"
    )

    if "symbol" not in columns:

        print(
            "Distinct Symbols            : N/A"
        )

    else:

        distinct_symbols = conn.execute(
            """
            SELECT COUNT(DISTINCT symbol)
            FROM market_technical
            WHERE symbol IS NOT NULL
            """
        ).fetchone()[0]

        print(
            f"Distinct Symbols            : {int(distinct_symbols)}"
        )

    # -------------------------------------------------------------------------
    # technical_score
    #
    # CRITICAL FIX:
    # Never reference a column that does not exist.
    # -------------------------------------------------------------------------

    if "technical_score" in columns:

        null_score = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_technical
            WHERE technical_score IS NULL
            """
        ).fetchone()[0]

        finite_score = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_technical
            WHERE technical_score IS NOT NULL
            """
        ).fetchone()[0]

        print(
            f"technical_score NULL        : {int(null_score)}"
        )

        print(
            f"technical_score AVAILABLE   : {int(finite_score)}"
        )

    else:

        print(
            "technical_score              : NOT PRESENT"
        )

        print(
            "technical_score audit        : N/A"
        )

    print("=" * 90)


# =============================================================================
# SYMBOL INTEGRITY
# =============================================================================

def inspect_symbols(
    conn: sqlite3.Connection,
    columns: set[str],
) -> None:

    print()
    print("=" * 90)
    print("SYMBOL INTEGRITY")
    print("=" * 90)

    if "symbol" not in columns:

        print(
            "BLOCKED : market_technical.symbol does not exist"
        )

        return

    rows = conn.execute(
        """
        SELECT
            symbol,
            COUNT(*) AS row_count
        FROM market_technical
        WHERE symbol IS NOT NULL
        GROUP BY symbol
        ORDER BY row_count DESC
        """
    ).fetchall()

    normalized: dict[str, int] = {}

    for row in rows:

        symbol = normalize_symbol(
            row["symbol"]
        )

        if symbol:
            normalized[symbol] = (
                normalized.get(symbol, 0)
                + int(row["row_count"])
            )

    print(
        f"Normalized Symbols : {len(normalized)}"
    )

    missing_expected = [
        symbol
        for symbol in EXPECTED_ASSETS
        if symbol not in normalized
    ]

    print(
        f"Expected Assets    : {len(EXPECTED_ASSETS)}"
    )

    print(
        f"Expected Present   : "
        f"{len(EXPECTED_ASSETS) - len(missing_expected)}"
    )

    print(
        f"Expected Missing   : {len(missing_expected)}"
    )

    if missing_expected:

        print(
            "Missing Symbols    : "
            + ", ".join(missing_expected)
        )

    print("=" * 90)


# =============================================================================
# TECHNICAL VALIDATION FIELDS
# =============================================================================

def inspect_validation_fields(
    conn: sqlite3.Connection,
    columns: set[str],
) -> None:

    print()
    print("=" * 90)
    print("TECHNICAL VALIDATION FIELD INTEGRITY")
    print("=" * 90)

    validation_candidates = [
        "technical_available",
        "available",
        "technical_validation_status",
        "technical_completeness",
        "technical_validation_score",
        "technical_validation_flags",
        "technical_validation_version",
        "technical_validated_at",
        "technical_version",
    ]

    found = [
        field
        for field in validation_candidates
        if field in columns
    ]

    missing = [
        field
        for field in validation_candidates
        if field not in columns
    ]

    print(
        f"Validation Fields Present : {len(found)}"
    )

    if found:

        for field in found:

            print(
                f"FOUND                     : {field}"
            )

    print()

    print(
        f"Validation Fields Missing : {len(missing)}"
    )

    if missing:

        for field in missing:

            print(
                f"NOT PRESENT               : {field}"
            )

    # -------------------------------------------------------------------------
    # technical_validation_status
    # -------------------------------------------------------------------------

    if "technical_validation_status" in columns:

        rows = conn.execute(
            """
            SELECT
                technical_validation_status,
                COUNT(*) AS row_count
            FROM market_technical
            GROUP BY technical_validation_status
            ORDER BY row_count DESC
            """
        ).fetchall()

        print()
        print(
            "Validation Status Distribution"
        )

        for row in rows:

            status = row["technical_validation_status"]

            if status is None:
                status = "NULL"

            print(
                f"  {str(status):<25} "
                f"{int(row['row_count'])}"
            )

    else:

        print()
        print(
            "Validation Status Distribution : N/A"
        )

    print("=" * 90)


# =============================================================================
# NUMERIC FIELD INTEGRITY
# =============================================================================

def inspect_numeric_fields(
    conn: sqlite3.Connection,
    columns: set[str],
) -> None:

    print()
    print("=" * 90)
    print("NUMERIC FIELD INTEGRITY")
    print("=" * 90)

    candidates = [
        "price",
        "close",
        "trend_score",
        "momentum_score",
        "volatility_score",
        "volume_score",
        "range_score",
        "breakout_score",
        "fibonacci_position",
        "ichimoku_cloud_distance",
        "sma20_distance",
        "ema20_distance",
        "ema20_slope",
        "price_vs_vwap",
        "technical_score",
        "technical_completeness",
        "technical_validation_score",
    ]

    found = [
        field
        for field in candidates
        if field in columns
    ]

    if not found:

        print(
            "No recognized numeric technical fields found."
        )

        print("=" * 90)

        return

    for field in found:

        safe_identifier(field)

        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                COUNT({field}) AS available
            FROM market_technical
            """
        ).fetchone()

        total = int(row["total"])
        available = int(row["available"])

        print(
            f"{field:<32}"
            f" total={total:<8}"
            f" available={available:<8}"
            f" null={total - available}"
        )

    print("=" * 90)


# =============================================================================
# TIMESTAMP INTEGRITY
# =============================================================================

def inspect_timestamps(
    conn: sqlite3.Connection,
    columns: set[str],
) -> None:

    print()
    print("=" * 90)
    print("TIMESTAMP / FRESHNESS FIELD")
    print("=" * 90)

    timestamp_column = first_existing_column(
        columns,
        [
            "timestamp",
            "updated_at",
            "created_at",
            "technical_validated_at",
        ],
    )

    if timestamp_column is None:

        print(
            "Timestamp Field : NOT PRESENT"
        )

        print(
            "Freshness Audit : N/A"
        )

        print("=" * 90)

        return

    safe_identifier(timestamp_column)

    print(
        f"Selected Field : {timestamp_column}"
    )

    rows = conn.execute(
        f"""
        SELECT
            MIN({timestamp_column}) AS min_value,
            MAX({timestamp_column}) AS max_value,
            COUNT(*) AS total,
            COUNT({timestamp_column}) AS available
        FROM market_technical
        """
    ).fetchone()

    print(
        f"Total Rows     : {int(rows['total'])}"
    )

    print(
        f"Available      : {int(rows['available'])}"
    )

    print(
        f"NULL           : "
        f"{int(rows['total']) - int(rows['available'])}"
    )

    print(
        f"MIN            : {rows['min_value']}"
    )

    print(
        f"MAX            : {rows['max_value']}"
    )

    print("=" * 90)


# =============================================================================
# EXPECTED ASSET DETAIL
# =============================================================================

def inspect_expected_assets(
    conn: sqlite3.Connection,
    columns: set[str],
) -> None:

    print()
    print("=" * 90)
    print("EXPECTED ASSET SOURCE DETAIL")
    print("=" * 90)

    if "symbol" not in columns:

        print(
            "BLOCKED : symbol field unavailable"
        )

        return

    # -------------------------------------------------------------------------
    # Select only columns that ACTUALLY EXIST.
    # -------------------------------------------------------------------------

    detail_candidates = [
        "symbol",
        "price",
        "close",
        "technical_score",
        "technical_available",
        "available",
        "technical_validation_status",
        "technical_completeness",
        "technical_validation_score",
        "technical_version",
        "technical_validation_version",
        "technical_validated_at",
        "timestamp",
        "updated_at",
        "created_at",
        "trend_score",
        "momentum_score",
        "volatility_score",
        "volume_score",
        "range_score",
        "breakout_score",
        "trend_regime",
        "regime",
    ]

    selected = [
        field
        for field in detail_candidates
        if field in columns
    ]

    if not selected:

        print(
            "No inspectable fields."
        )

        return

    column_sql = ", ".join(
        safe_identifier(field)
        for field in selected
    )

    placeholders = ",".join(
        ["?"] * len(EXPECTED_ASSETS)
    )

    rows = conn.execute(
        f"""
        SELECT
            {column_sql}
        FROM market_technical
        WHERE UPPER(TRIM(symbol)) IN ({placeholders})
        ORDER BY UPPER(TRIM(symbol))
        """,
        tuple(EXPECTED_ASSETS),
    ).fetchall()

    grouped: dict[str, list[sqlite3.Row]] = {}

    for row in rows:

        symbol = normalize_symbol(
            row["symbol"]
        )

        grouped.setdefault(
            symbol,
            [],
        ).append(row)

    for symbol in EXPECTED_ASSETS:

        candidates = grouped.get(
            symbol,
            [],
        )

        print()
        print(
            f"[{symbol}] rows={len(candidates)}"
        )

        if not candidates:

            print(
                "  STATUS : MISSING"
            )

            continue

        # ---------------------------------------------------------------------
        # Print only high-value fields.
        # ---------------------------------------------------------------------

        for row in candidates[:5]:

            parts = []

            for field in selected:

                if field == "symbol":
                    continue

                value = row[field]

                if value is not None:

                    parts.append(
                        f"{field}={value}"
                    )

            print(
                "  "
                + (
                    " | ".join(parts)
                    if parts
                    else "NO NON-NULL INSPECTABLE VALUES"
                )
            )

        if len(candidates) > 5:

            print(
                f"  ... {len(candidates) - 5} additional rows"
            )

    print("=" * 90)


# =============================================================================
# AUTHORITATIVE CONTRACT INTERPRETATION
# =============================================================================

def inspect_authoritative_contract(
    conn: sqlite3.Connection,
    columns: set[str],
) -> None:

    print()
    print("=" * 90)
    print("AUTHORITATIVE TECHNICAL CONTRACT")
    print("=" * 90)

    available_column = first_existing_column(
        columns,
        [
            "technical_available",
            "available",
        ],
    )

    status_column = (
        "technical_validation_status"
        if "technical_validation_status" in columns
        else None
    )

    score_column = (
        "technical_score"
        if "technical_score" in columns
        else None
    )

    print(
        "technical_available field : "
        + (
            available_column
            if available_column
            else "NOT PRESENT"
        )
    )

    print(
        "validation status field   : "
        + (
            status_column
            if status_column
            else "NOT PRESENT"
        )
    )

    print(
        "technical score field     : "
        + (
            score_column
            if score_column
            else "NOT PRESENT"
        )
    )

    # -------------------------------------------------------------------------
    # Do NOT declare source invalid simply because optional contract metadata
    # does not exist in this physical table.
    # -------------------------------------------------------------------------

    if (
        available_column is None
        and status_column is None
    ):

        print()
        print(
            "CONTRACT RESULT : "
            "SOURCE METADATA FIELDS NOT PRESENT"
        )

        print(
            "INTERPRETATION  : "
            "Integrity check cannot infer VALID/AVAILABLE "
            "from absent metadata."
        )

        print(
            "ACTION          : "
            "NO WRITE / NO SCHEMA CHANGE"
        )

        print("=" * 90)

        return

    # -------------------------------------------------------------------------
    # Available distribution
    # -------------------------------------------------------------------------

    if available_column:

        safe_identifier(
            available_column
        )

        rows = conn.execute(
            f"""
            SELECT
                {available_column},
                COUNT(*) AS row_count
            FROM market_technical
            GROUP BY {available_column}
            ORDER BY row_count DESC
            """
        ).fetchall()

        print()
        print(
            "Availability Distribution"
        )

        for row in rows:

            value = row[available_column]

            if value is None:
                value = "NULL"

            print(
                f"  {str(value):<20}"
                f"{int(row['row_count'])}"
            )

    print("=" * 90)


# =============================================================================
# FINAL RESULT
# =============================================================================

def print_final_result(
    conn: sqlite3.Connection,
    columns: set[str],
) -> None:

    print()
    print("=" * 90)
    print("FINAL INTEGRITY RESULT")
    print("=" * 90)

    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_technical
        """
    ).fetchone()[0]

    print(
        f"Rows Inspected       : {int(total)}"
    )

    print(
        f"Schema Columns       : {len(columns)}"
    )

    if "symbol" in columns:

        distinct_symbols = conn.execute(
            """
            SELECT COUNT(DISTINCT UPPER(TRIM(symbol)))
            FROM market_technical
            WHERE symbol IS NOT NULL
              AND TRIM(symbol) <> ''
            """
        ).fetchone()[0]

        print(
            f"Distinct Symbols     : {int(distinct_symbols)}"
        )

    else:

        print(
            "Distinct Symbols     : N/A"
        )

    print()
    print(
        "WRITE OPERATIONS     : NONE"
    )

    print(
        "SCHEMA MODIFICATION  : NONE"
    )

    print(
        "SYNTHETIC DATA       : NONE"
    )

    print(
        "INTERPOLATION        : NONE"
    )

    print(
        "FORWARD FILL         : NONE"
    )

    print(
        "BACK FILL            : NONE"
    )

    print()
    print(
        "INTEGRITY STATUS     : COMPLETE"
    )

    print(
        "NOTE                 : "
        "Missing physical columns are reported as N/A; "
        "they are never assumed."
    )

    print("=" * 90)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print_header()

    conn: sqlite3.Connection | None = None

    try:

        print()
        print(
            "Checking database..."
        )

        conn = connect_database()

        print(
            "Database : CONNECTED"
        )

        # ---------------------------------------------------------------------
        # Table existence
        # ---------------------------------------------------------------------

        print()
        print(
            "Checking market_technical..."
        )

        if not table_exists(
            conn,
            "market_technical",
        ):

            raise RuntimeError(
                "market_technical table does not exist"
            )

        print(
            "market_technical : EXISTS"
        )

        # ---------------------------------------------------------------------
        # Schema
        # ---------------------------------------------------------------------

        columns = print_schema(
            conn
        )

        # ---------------------------------------------------------------------
        # Audits
        # ---------------------------------------------------------------------

        print_global_counts(
            conn,
            columns,
        )

        inspect_symbols(
            conn,
            columns,
        )

        inspect_validation_fields(
            conn,
            columns,
        )

        inspect_numeric_fields(
            conn,
            columns,
        )

        inspect_timestamps(
            conn,
            columns,
        )

        inspect_expected_assets(
            conn,
            columns,
        )

        inspect_authoritative_contract(
            conn,
            columns,
        )

        print_final_result(
            conn,
            columns,
        )

        print()
        print("=" * 90)
        print(
            f"MARKET TECHNICAL SOURCE INTEGRITY CHECK "
            f"{ENGINE_VERSION} COMPLETE"
        )
        print("=" * 90)

    except Exception:

        print()
        print("=" * 90)
        print(
            "MARKET TECHNICAL SOURCE INTEGRITY CHECK ERROR"
        )
        print("=" * 90)

        traceback.print_exc()

        raise

    finally:

        if conn is not None:
            conn.close()


# =============================================================================
# ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    main()