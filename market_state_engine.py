# =============================================================================
# ARUNDA TRADER
# MARKET STATE ENGINE
# MARKET_STATE_UNIFIED_v0.2.9
# =============================================================================
#
# PURPOSE
# -------
# Unified normalized market-state writer.
#
# CONTRACT
# --------
# Technical layer is AUTHORITATIVE.
# Technical score is PASSTHROUGH.
# Technical semantic fields are PASSTHROUGH.
# Technical regime is PASSTHROUGH.
# Technical validation metadata is PASSTHROUGH.
#
# IMPORTANT CONTRACT REPAIR
# -------------------------
# A technical row is authoritative when:
#
#   technical_validation_status == VALID
#
# If an explicit availability field exists:
#   it must not explicitly say unavailable.
#
# If no availability field exists in market_technical:
#   VALID is sufficient to establish technical availability.
#
# NO technical values are calculated here.
#
# THIS ENGINE DOES NOT:
# ---------------------
# - calculate indicators
# - calculate technical scores
# - calculate signals
# - calculate predictions
# - rank assets
# - create opportunities
# - calculate risk
# - execute orders
# - synthesize technical data
# - interpolate
# - forward-fill
# - back-fill
#
# REQUIRED EXISTING MARKET_STATE FIELDS
# -------------------------------------
# timestamp  NOT NULL
# symbol     NOT NULL
# created_at NOT NULL
#
# Therefore the writer explicitly supplies:
#   timestamp
#   created_at
#
# SNAPSHOT CONTRACT
# -----------------
# One current state per expected asset for this engine version.
#
# Before writing the current snapshot:
#   delete existing rows for this ENGINE_VERSION + EXPECTED_ASSETS
#
# Then insert exactly one state per successfully resolved asset.
#
# READ API CONTRACT
# -----------------
# load_structural_state()
#
# Returns a MEMORY-ONLY dictionary:
#
# {
#     "BTC": {...},
#     ...
#     "NEAR": {...}
# }
#
# It is a reader/adapter over get_current_snapshot().
# It performs NO calculation and NO database write.
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

ENGINE_VERSION = "MARKET_STATE_UNIFIED_v0.2.9"

DB_PATH = (
    Path(__file__).resolve().parent
    / "arunda.db"
)

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
# AUTHORITATIVE TECHNICAL CONTRACT
# =============================================================================

TECHNICAL_AUTHORITATIVE = True

TECHNICAL_SCORE_FIELD = "technical_score"

TECHNICAL_SEMANTIC_FIELDS = [
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
    "trend_regime",
    "regime",
]

TECHNICAL_VALIDATION_FIELDS = [
    "technical_completeness",
    "technical_version",
    "technical_validation_score",
    "technical_validation_status",
    "technical_validation_flags",
    "technical_validation_version",
    "technical_validated_at",
]


# =============================================================================
# REQUIRED MARKET STATE COLUMNS
# =============================================================================

REQUIRED_MARKET_STATE_COLUMNS = {
    "timestamp": "TEXT",
    "symbol": "TEXT",
    "price": "REAL",
    "state_score": "REAL",
    "state_confidence": "REAL",
    "data_completeness": "REAL",
    "technical_score": "REAL",
    "technical_available": "INTEGER",
    "news_available": "INTEGER",
    "whale_available": "INTEGER",
    "microstructure_available": "INTEGER",
    "state_sources": "TEXT",
    "state_version": "TEXT",
    "created_at": "TEXT",
    "updated_at": "TEXT",

    # Technical semantic passthrough
    "trend_score": "REAL",
    "momentum_score": "REAL",
    "volatility_score": "REAL",
    "volume_score": "REAL",
    "range_score": "REAL",
    "breakout_score": "REAL",
    "fibonacci_position": "REAL",
    "ichimoku_cloud_distance": "REAL",
    "sma20_distance": "REAL",
    "ema20_distance": "REAL",
    "ema20_slope": "REAL",
    "price_vs_vwap": "REAL",
    "trend_regime": "TEXT",
    "regime": "TEXT",

    # Technical validation passthrough
    "technical_completeness": "REAL",
    "technical_version": "TEXT",
    "technical_validation_score": "REAL",
    "technical_validation_status": "TEXT",
    "technical_validation_flags": "TEXT",
    "technical_validation_version": "TEXT",
    "technical_validated_at": "TEXT",
}


# =============================================================================
# UTILS
# =============================================================================

def utc_now() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


def is_finite(
    value: Any,
) -> bool:

    if value is None:
        return False

    try:

        return math.isfinite(
            float(value)
        )

    except (
        TypeError,
        ValueError,
    ):

        return False


def finite_or_none(
    value: Any,
) -> float | None:

    if not is_finite(value):
        return None

    return float(value)


def normalize_symbol(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip().upper()


def normalize_status(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip().upper()


def safe_identifier(
    name: str,
) -> str:

    if not name:
        raise ValueError(
            "Empty SQL identifier"
        )

    if not name.replace(
        "_",
        "",
    ).isalnum():

        raise ValueError(
            f"Unsafe SQL identifier: {name}"
        )

    return name


# =============================================================================
# DATABASE
# =============================================================================

def connect_database() -> sqlite3.Connection:

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    return conn


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def table_exists(
    conn: sqlite3.Connection,
    table_name: str,
) -> bool:

    table_name = safe_identifier(
        table_name
    )

    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1
        """,
        (
            table_name,
        ),
    ).fetchone()

    return row is not None


def table_columns(
    conn: sqlite3.Connection,
    table_name: str,
) -> list[str]:

    table_name = safe_identifier(
        table_name
    )

    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


def row_has_field(
    row: sqlite3.Row,
    field: str,
) -> bool:

    return field in row.keys()


def row_value(
    row: sqlite3.Row,
    field: str,
    default: Any = None,
) -> Any:

    if field not in row.keys():
        return default

    return row[field]


# =============================================================================
# SCHEMA
# =============================================================================

def ensure_market_state_schema(
    conn: sqlite3.Connection,
) -> None:

    if not table_exists(
        conn,
        "market_state",
    ):

        columns = []

        for name, data_type in (
            REQUIRED_MARKET_STATE_COLUMNS.items()
        ):

            if name == "timestamp":
                columns.append(
                    f"{name} {data_type} NOT NULL"
                )

            elif name == "symbol":
                columns.append(
                    f"{name} {data_type} NOT NULL"
                )

            elif name == "created_at":
                columns.append(
                    f"{name} {data_type} NOT NULL"
                )

            else:
                columns.append(
                    f"{name} {data_type}"
                )

        conn.execute(
            """
            CREATE TABLE market_state (
                """
            + ", ".join(columns)
            + """
            )
            """
        )

        conn.commit()

        return

    existing = set(
        table_columns(
            conn,
            "market_state",
        )
    )

    for name, data_type in (
        REQUIRED_MARKET_STATE_COLUMNS.items()
    ):

        if name in existing:
            continue

        conn.execute(
            f"""
            ALTER TABLE market_state
            ADD COLUMN {safe_identifier(name)}
            {data_type}
            """
        )

    conn.commit()


# =============================================================================
# UNIVERSE
# =============================================================================

def get_universe_assets(
    conn: sqlite3.Connection,
) -> list[str]:

    return list(
        EXPECTED_ASSETS
    )


# =============================================================================
# SYMBOL DISCOVERY
# =============================================================================

def discover_symbol_table(
    conn: sqlite3.Connection,
    table_name: str,
) -> list[str]:

    if not table_exists(
        conn,
        table_name,
    ):
        return []

    columns = table_columns(
        conn,
        table_name,
    )

    if "symbol" not in columns:
        return []

    table_name = safe_identifier(
        table_name
    )

    rows = conn.execute(
        f"""
        SELECT DISTINCT symbol
        FROM {table_name}
        WHERE symbol IS NOT NULL
        """
    ).fetchall()

    return [
        normalize_symbol(
            row["symbol"]
        )
        for row in rows
        if normalize_symbol(
            row["symbol"]
        )
    ]


def load_microstructure_symbols(
    conn: sqlite3.Connection,
) -> set[str]:

    return set(
        discover_symbol_table(
            conn,
            "market_microstructure",
        )
    )


def load_news_symbols(
    conn: sqlite3.Connection,
) -> set[str]:

    return set(
        discover_symbol_table(
            conn,
            "market_news",
        )
    )


def load_whale_symbols(
    conn: sqlite3.Connection,
) -> set[str]:

    return set(
        discover_symbol_table(
            conn,
            "market_whale",
        )
    )


# =============================================================================
# TECHNICAL DISCOVERY
# =============================================================================

def load_all_technical_rows(
    conn: sqlite3.Connection,
) -> list[sqlite3.Row]:

    if not table_exists(
        conn,
        "market_technical",
    ):

        return []

    rows = conn.execute(
        """
        SELECT *
        FROM market_technical
        """
    ).fetchall()

    return rows


def technical_row_id(
    row: sqlite3.Row,
) -> Any:

    for field in (
        "id",
        "row_id",
    ):

        if row_has_field(
            row,
            field,
        ):

            return row_value(
                row,
                field,
            )

    return None


def technical_row_timestamp(
    row: sqlite3.Row,
) -> Any:

    for field in (
        "timestamp",
        "created_at",
        "updated_at",
        "validated_at",
    ):

        if row_has_field(
            row,
            field,
        ):

            return row_value(
                row,
                field,
            )

    return None


def technical_validation_status(
    row: sqlite3.Row,
) -> str:

    value = row_value(
        row,
        "technical_validation_status",
    )

    return normalize_status(
        value
    )


def explicit_availability(
    row: sqlite3.Row,
) -> bool | None:

    candidates = (
        "technical_available",
        "available",
        "availability",
        "technical_availability",
    )

    for field in candidates:

        if not row_has_field(
            row,
            field,
        ):
            continue

        value = row_value(
            row,
            field,
        )

        if value is None:
            continue

        if isinstance(
            value,
            bool,
        ):
            return value

        normalized = normalize_status(
            value
        )

        if normalized in (
            "AVAILABLE",
            "TRUE",
            "YES",
            "1",
            "READY",
            "VALID",
        ):
            return True

        if normalized in (
            "UNAVAILABLE",
            "FALSE",
            "NO",
            "0",
            "MISSING",
            "NOT_AVAILABLE",
        ):
            return False

    return None


def technical_is_authoritative(
    row: sqlite3.Row,
) -> bool:

    status = technical_validation_status(
        row
    )

    if status != "VALID":
        return False

    availability = explicit_availability(
        row
    )

    if availability is False:
        return False

    return True


def technical_quality_rank(
    row: sqlite3.Row,
) -> tuple:

    status = technical_validation_status(
        row
    )

    validation_score = row_value(
        row,
        "technical_validation_score",
    )

    if not is_finite(
        validation_score
    ):

        validation_score = -math.inf

    timestamp = technical_row_timestamp(
        row
    )

    row_id = technical_row_id(
        row
    )

    if not is_finite(row_id):

        row_id = -math.inf

    return (
        1 if status == "VALID" else 0,
        float(validation_score),
        str(timestamp or ""),
        float(row_id),
    )


def resolve_authoritative_technical(
    rows: list[sqlite3.Row],
) -> dict[str, sqlite3.Row]:

    resolved = {}

    for row in rows:

        if not row_has_field(
            row,
            "symbol",
        ):
            continue

        symbol = normalize_symbol(
            row_value(
                row,
                "symbol",
            )
        )

        if symbol not in EXPECTED_ASSETS:
            continue

        if not technical_is_authoritative(
            row
        ):
            continue

        current = resolved.get(
            symbol
        )

        if current is None:

            resolved[symbol] = row
            continue

        if technical_quality_rank(
            row
        ) > technical_quality_rank(
            current
        ):

            resolved[symbol] = row

    return resolved


# =============================================================================
# TECHNICAL VALUES
# =============================================================================

def technical_value(
    row: sqlite3.Row,
    field: str,
) -> Any:

    if not row_has_field(
        row,
        field,
    ):

        return None

    return row_value(
        row,
        field,
    )


def technical_price(
    row: sqlite3.Row,
) -> float | None:

    candidates = (
        "price",
        "close",
        "last_price",
        "current_price",
    )

    for field in candidates:

        value = technical_value(
            row,
            field,
        )

        if is_finite(value):

            return float(value)

    return None


# =============================================================================
# PASSTHROUGH
# =============================================================================

def passthrough_state_score(
    row: sqlite3.Row,
) -> float | None:

    return finite_or_none(
        technical_value(
            row,
            "technical_score",
        )
    )


# =============================================================================
# STATE METRICS
# =============================================================================

def calculate_data_completeness(
    technical_row: sqlite3.Row | None,
    news_available: bool,
    whale_available: bool,
    microstructure_available: bool,
) -> float:

    available = 0
    total = 4

    if technical_row is not None:
        available += 1

    if news_available:
        available += 1

    if whale_available:
        available += 1

    if microstructure_available:
        available += 1

    return round(
        available / total,
        6,
    )


def calculate_state_confidence(
    technical_row: sqlite3.Row | None,
    data_completeness: float,
) -> float:

    if technical_row is None:
        return 0.0

    status = technical_validation_status(
        technical_row
    )

    if status != "VALID":
        return 0.0

    return round(
        max(
            0.0,
            min(
                1.0,
                float(data_completeness),
            ),
        ),
        6,
    )


# =============================================================================
# STATE RECORD
# =============================================================================

def build_state_record(
    asset: str,
    technical_row: sqlite3.Row | None,
    news_available: bool,
    whale_available: bool,
    microstructure_available: bool,
) -> dict[str, Any]:

    if technical_row is None:

        raise RuntimeError(
            "No authoritative technical row: "
            + asset
        )

    timestamp = (
        technical_row_timestamp(
            technical_row
        )
        or utc_now()
    )

    price = technical_price(
        technical_row
    )

    data_completeness = (
        calculate_data_completeness(
            technical_row,
            news_available,
            whale_available,
            microstructure_available,
        )
    )

    state_confidence = (
        calculate_state_confidence(
            technical_row,
            data_completeness,
        )
    )

    state = {

        "timestamp":
            str(timestamp),

        "symbol":
            asset,

        "price":
            price,

        "state_score":
            passthrough_state_score(
                technical_row
            ),

        "state_confidence":
            state_confidence,

        "data_completeness":
            data_completeness,

        "technical_score":
            finite_or_none(
                technical_value(
                    technical_row,
                    "technical_score",
                )
            ),

        "technical_available":
            1,

        "news_available":
            int(news_available),

        "whale_available":
            int(whale_available),

        "microstructure_available":
            int(microstructure_available),

        "state_sources":
            "technical",

        "state_version":
            ENGINE_VERSION,
    }

    for field in TECHNICAL_SEMANTIC_FIELDS:

        if field in state:
            continue

        state[field] = technical_value(
            technical_row,
            field,
        )

    for field in TECHNICAL_VALIDATION_FIELDS:

        if field in state:
            continue

        state[field] = technical_value(
            technical_row,
            field,
        )

    state["created_at"] = utc_now()
    state["updated_at"] = utc_now()

    return state


# =============================================================================
# WRITE MARKET STATE
# =============================================================================

def clear_current_snapshot(
    conn: sqlite3.Connection,
) -> None:

    if not table_exists(
        conn,
        "market_state",
    ):
        return

    placeholders = ",".join(
        "?"
        for _ in EXPECTED_ASSETS
    )

    conn.execute(
        f"""
        DELETE FROM market_state
        WHERE state_version = ?
          AND symbol IN ({placeholders})
        """,
        [
            ENGINE_VERSION,
            *EXPECTED_ASSETS,
        ],
    )


def write_market_state(
    conn: sqlite3.Connection,
    state: dict[str, Any],
) -> None:

    if not isinstance(
        state,
        dict,
    ):

        raise RuntimeError(
            "Invalid market state"
        )

    columns = [
        "timestamp",
        "symbol",
        "price",
        "state_score",
        "state_confidence",
        "data_completeness",
        "technical_score",
        "technical_available",
        "news_available",
        "whale_available",
        "microstructure_available",
        "state_sources",
        "state_version",
        "created_at",
        "updated_at",
    ]

    columns.extend(
        TECHNICAL_SEMANTIC_FIELDS
    )

    columns.extend(
        TECHNICAL_VALIDATION_FIELDS
    )

    columns = list(
        dict.fromkeys(
            columns
        )
    )

    values = [
        state.get(
            column
        )
        for column in columns
    ]

    identifiers = ", ".join(
        safe_identifier(
            column
        )
        for column in columns
    )

    placeholders = ", ".join(
        "?"
        for _ in columns
    )

    conn.execute(
        f"""
        INSERT INTO market_state (
            {identifiers}
        )
        VALUES (
            {placeholders}
        )
        """,
        values,
    )


# =============================================================================
# CURRENT SNAPSHOT READER
# =============================================================================

def get_current_snapshot(
    conn: sqlite3.Connection,
) -> list[sqlite3.Row]:

    if not table_exists(
        conn,
        "market_state",
    ):

        return []

    rows = conn.execute(
        """
        SELECT
            symbol,
            timestamp,
            state_score,
            state_confidence,
            data_completeness,
            technical_score,
            trend_score,
            momentum_score,
            volatility_score,
            volume_score,
            range_score,
            breakout_score,
            regime,
            technical_validation_status,
            technical_validation_flags,
            state_sources,
            state_version
        FROM market_state
        WHERE state_version = ?
          AND symbol IN (
              'BTC',
              'ETH',
              'SOL',
              'XRP',
              'ADA',
              'DOGE',
              'SHIB',
              'LINK',
              'AVAX',
              'DOT',
              'LTC',
              'UNI',
              'AAVE',
              'SUI',
              'NEAR'
          )
        ORDER BY
            CASE symbol
                WHEN 'BTC' THEN 1
                WHEN 'ETH' THEN 2
                WHEN 'SOL' THEN 3
                WHEN 'XRP' THEN 4
                WHEN 'ADA' THEN 5
                WHEN 'DOGE' THEN 6
                WHEN 'SHIB' THEN 7
                WHEN 'LINK' THEN 8
                WHEN 'AVAX' THEN 9
                WHEN 'DOT' THEN 10
                WHEN 'LTC' THEN 11
                WHEN 'UNI' THEN 12
                WHEN 'AAVE' THEN 13
                WHEN 'SUI' THEN 14
                WHEN 'NEAR' THEN 15
            END
        """
        ,
        (
            ENGINE_VERSION,
        ),
    ).fetchall()

    return rows


# =============================================================================
# CONTRACT REPAIR
# =============================================================================
#
# READ-ONLY API FOR DOWNSTREAM SCORER
#
# signal_scorer v0.3 expects:
#
#     market_state_engine.load_structural_state()
#
# The underlying engine already exposes:
#
#     get_current_snapshot(conn)
#
# Therefore this function is a thin adapter only.
#
# IMPORTANT:
#     - No calculations
#     - No writes
#     - No INSERT
#     - No UPDATE
#     - No DELETE
#     - No schema changes
#     - No signal generation
#     - No direction generation
#
# =============================================================================

def load_structural_state() -> dict[str, dict[str, Any]]:

    conn = connect_database()

    try:

        rows = get_current_snapshot(
            conn
        )

        result: dict[
            str,
            dict[str, Any],
        ] = {}

        for row in rows:

            asset = normalize_symbol(
                row["symbol"]
            )

            if not asset:
                continue

            if asset not in EXPECTED_ASSETS:
                continue

            result[asset] = dict(
                row
            )

        expected = set(
            EXPECTED_ASSETS
        )

        actual = set(
            result.keys()
        )

        missing = (
            expected
            - actual
        )

        extra = (
            actual
            - expected
        )

        if missing:

            raise RuntimeError(
                "Structural state missing assets: "
                + str(
                    sorted(missing)
                )
            )

        if extra:

            raise RuntimeError(
                "Structural state contains unexpected assets: "
                + str(
                    sorted(extra)
                )
            )

        if len(result) != len(
            EXPECTED_ASSETS
        ):

            raise RuntimeError(
                "Structural state asset count mismatch: "
                + str(
                    len(result)
                )
                + " != "
                + str(
                    len(EXPECTED_ASSETS)
                )
            )

        return result

    finally:

        conn.close()


# =============================================================================
# COUNT
# =============================================================================

def count_market_state_records(
    conn: sqlite3.Connection,
) -> int:

    if not table_exists(
        conn,
        "market_state",
    ):
        return 0

    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM market_state
        WHERE state_version = ?
          AND symbol IN (
              'BTC',
              'ETH',
              'SOL',
              'XRP',
              'ADA',
              'DOGE',
              'SHIB',
              'LINK',
              'AVAX',
              'DOT',
              'LTC',
              'UNI',
              'AAVE',
              'SUI',
              'NEAR'
          )
        """,
        (
            ENGINE_VERSION,
        ),
    ).fetchone()

    return int(
        row["count"]
    )


# =============================================================================
# MAIN
# =============================================================================

def print_header():

    print(
        "=" * 78
    )

    print(
        "ARUNDA MARKET STATE ENGINE"
    )

    print(
        "=" * 78
    )

    print(
        "Engine Version :",
        ENGINE_VERSION,
    )

    print(
        "Expected Assets:",
        len(
            EXPECTED_ASSETS
        ),
    )

    print(
        "Technical      : AUTHORITATIVE"
    )

    print(
        "Storage        : DATABASE"
    )

    print(
        "Structural Read: MEMORY ONLY"
    )

    print(
        "Prediction     : NOT USED"
    )

    print(
        "Ranking        : NOT USED"
    )

    print(
        "Risk           : NOT USED"
    )

    print(
        "Execution      : NOT USED"
    )

    print(
        "=" * 78
    )


def print_snapshot(
    snapshot,
):

    print()
    print(
        "MARKET STATE SNAPSHOT"
    )
    print(
        "-" * 78
    )

    for asset in EXPECTED_ASSETS:

        item = snapshot.get(
            asset
        )

        if item is None:

            print(
                asset,
                "| MISSING"
            )

            continue

        print(
            asset,
            "|",
            "REGIME=",
            item.get(
                "regime"
            ),
            "|",
            "TECH_STATUS=",
            item.get(
                "technical_validation_status"
            ),
        )

    print()


def main():

    print_header()

    conn = None

    try:

        conn = connect_database()

        ensure_market_state_schema(
            conn
        )

        technical_rows = (
            load_all_technical_rows(
                conn
            )
        )

        technical = (
            resolve_authoritative_technical(
                technical_rows
            )
        )

        news_symbols = (
            load_news_symbols(
                conn
            )
        )

        whale_symbols = (
            load_whale_symbols(
                conn
            )
        )

        microstructure_symbols = (
            load_microstructure_symbols(
                conn
            )
        )

        states = {}

        for asset in EXPECTED_ASSETS:

            technical_row = technical.get(
                asset
            )

            if technical_row is None:
                continue

            state = build_state_record(

                asset,

                technical_row,

                asset in news_symbols,

                asset in whale_symbols,

                asset in microstructure_symbols,

            )

            states[asset] = state

        clear_current_snapshot(
            conn
        )

        for asset in EXPECTED_ASSETS:

            state = states.get(
                asset
            )

            if state is None:
                continue

            write_market_state(
                conn,
                state
            )

        conn.commit()

        count = (
            count_market_state_records(
                conn
            )
        )

        print(
            "Written Records:",
            count,
        )

        print(
            "MARKET STATE ENGINE STATUS : READY"
        )

        return 0

    except Exception as error:

        if conn is not None:

            conn.rollback()

        print()
        print(
            "=" * 78
        )
        print(
            "MARKET STATE ENGINE ERROR"
        )
        print(
            "=" * 78
        )

        print(
            "Type  :",
            type(error).__name__,
        )

        print(
            "Error :",
            str(error),
        )

        print()

        traceback.print_exc()

        print()
        print(
            "MARKET STATE ENGINE STATUS : FAILED"
        )

        return 1

    finally:

        if conn is not None:

            conn.close()


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )