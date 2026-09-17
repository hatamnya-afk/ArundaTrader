from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


# =============================================================================
# ARUNDA SNAPSHOT FEATURE -> OUTCOME PATH FORENSIC v0.1
# =============================================================================
#
# PURPOSE:
#   READ-ONLY forensic resolution of the REAL Outcome path.
#
# TARGET:
#   SNAPSHOT FEATURE CONTRACT
#       asset_symbol + snapshot_timestamp
#
#   ->
#   REAL upstream/downstream identity
#
#   ->
#   signal_outcomes / actual outcome storage
#
# FORBIDDEN:
#   DB WRITE
#   INSERT
#   UPDATE
#   DELETE
#   ALTER
#   CREATE
#   DROP
#   NETWORK
#   SIGNAL
#   PREDICTION
#   DECISION
#
# IMPORTANT:
#   This script does NOT claim a relationship.
#   It only resolves the real database path and key identity.
# =============================================================================


DB_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

FEATURE_CONTRACT_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)


# =============================================================================
# DATABASE
# =============================================================================

def connect() -> sqlite3.Connection:

    if not DB_PATH.exists():
        raise FileNotFoundError(DB_PATH)

    conn = sqlite3.connect(
        DB_PATH,
        uri=False,
    )

    conn.row_factory = sqlite3.Row

    return conn


# =============================================================================
# TABLE DISCOVERY
# =============================================================================

def list_tables(
    conn: sqlite3.Connection,
) -> list[str]:

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    return [
        str(row["name"])
        for row in rows
    ]


def table_columns(
    conn: sqlite3.Connection,
    table: str,
) -> list[str]:

    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return [
        str(row["name"])
        for row in rows
    ]


# =============================================================================
# CONTRACT
# =============================================================================

def load_contract() -> dict[str, Any]:

    if not FEATURE_CONTRACT_PATH.exists():
        raise FileNotFoundError(
            FEATURE_CONTRACT_PATH
        )

    return json.loads(
        FEATURE_CONTRACT_PATH.read_text(
            encoding="utf-8"
        )
    )


# =============================================================================
# COLUMN NORMALIZATION
# =============================================================================

def normalize(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip().lower()


def find_alias(
    columns: list[str],
    aliases: tuple[str, ...],
) -> str | None:

    lookup = {
        normalize(column): column
        for column in columns
    }

    for alias in aliases:

        found = lookup.get(
            normalize(alias)
        )

        if found:
            return found

    return None


# =============================================================================
# IDENTITY CANDIDATES
# =============================================================================

SYMBOL_ALIASES = (
    "symbol",
    "asset_symbol",
    "asset",
    "asset_name",
    "ticker",
)

TIMESTAMP_ALIASES = (
    "timestamp",
    "snapshot_timestamp",
    "signal_timestamp",
    "created_at",
    "event_timestamp",
    "entry_timestamp",
    "time",
    "datetime",
)

SIGNAL_ID_ALIASES = (
    "signal_id",
    "fusion_signal_id",
    "id",
)

OUTCOME_ID_ALIASES = (
    "outcome_id",
    "id",
)

ENTRY_PRICE_ALIASES = (
    "entry_price",
    "entry",
)

FUTURE_PRICE_ALIASES = (
    "future_price",
    "future_price_5m",
    "future_price_15m",
    "future_price_30m",
    "future_price_60m",
)

HORIZON_ALIASES = (
    "horizon",
    "horizon_minutes",
    "future_horizon",
)

DIRECTION_ALIASES = (
    "direction",
    "signal_direction",
    "side",
)


# =============================================================================
# TABLE INSPECTION
# =============================================================================

def inspect_table(
    conn: sqlite3.Connection,
    table: str,
) -> dict[str, Any]:

    columns = table_columns(
        conn,
        table,
    )

    return {
        "table": table,
        "columns": columns,
        "symbol": find_alias(
            columns,
            SYMBOL_ALIASES,
        ),
        "timestamp": find_alias(
            columns,
            TIMESTAMP_ALIASES,
        ),
        "signal_id": find_alias(
            columns,
            SIGNAL_ID_ALIASES,
        ),
        "outcome_id": find_alias(
            columns,
            OUTCOME_ID_ALIASES,
        ),
        "entry_price": find_alias(
            columns,
            ENTRY_PRICE_ALIASES,
        ),
        "future_price": find_alias(
            columns,
            FUTURE_PRICE_ALIASES,
        ),
        "horizon": find_alias(
            columns,
            HORIZON_ALIASES,
        ),
        "direction": find_alias(
            columns,
            DIRECTION_ALIASES,
        ),
    }


# =============================================================================
# SAMPLE
# =============================================================================

def sample_rows(
    conn: sqlite3.Connection,
    table: str,
    limit: int = 5,
) -> list[dict[str, Any]]:

    rows = conn.execute(
        f"""
        SELECT *
        FROM {table}
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    result = []

    for row in rows:

        item = {}

        for key in row.keys():

            value = row[key]

            if isinstance(value, bytes):
                value = value.hex()

            item[key] = value

        result.append(item)

    return result


# =============================================================================
# EXACT FEATURE IDENTITY
# =============================================================================

def feature_identity_set(
    contract: dict[str, Any],
) -> set[tuple[str, str]]:

    identities = set()

    for record in contract.get(
        "records",
        [],
    ):

        symbol = normalize(
            record.get("asset_symbol")
        )

        timestamp = normalize(
            record.get("snapshot_timestamp")
        )

        if symbol and timestamp:

            identities.add(
                (
                    symbol,
                    timestamp,
                )
            )

    return identities


# =============================================================================
# DIRECT MATCH TEST
# =============================================================================

def direct_match_test(
    conn: sqlite3.Connection,
    table: str,
    identities: set[tuple[str, str]],
) -> dict[str, Any]:

    info = inspect_table(
        conn,
        table,
    )

    symbol_col = info["symbol"]
    timestamp_col = info["timestamp"]

    result = {
        "table": table,
        "symbol_column": symbol_col,
        "timestamp_column": timestamp_col,
        "tested": len(identities),
        "matches": 0,
    }

    if not symbol_col or not timestamp_col:

        return result

    matched = set()

    for symbol, timestamp in identities:

        rows = conn.execute(
            f"""
            SELECT 1
            FROM {table}
            WHERE LOWER(TRIM(CAST({symbol_col} AS TEXT))) = ?
              AND TRIM(CAST({timestamp_col} AS TEXT)) = ?
            LIMIT 1
            """,
            (
                symbol,
                timestamp,
            ),
        ).fetchall()

        if rows:

            matched.add(
                (
                    symbol,
                    timestamp,
                )
            )

    result["matches"] = len(
        matched
    )

    result["match_ratio"] = (
        len(matched) / len(identities)
        if identities
        else 0.0
    )

    return result


# =============================================================================
# TIMESTAMP RELAXED MATCH
# =============================================================================

def relaxed_timestamp_match(
    conn: sqlite3.Connection,
    table: str,
    identities: set[tuple[str, str]],
) -> dict[str, Any]:

    info = inspect_table(
        conn,
        table,
    )

    symbol_col = info["symbol"]
    timestamp_col = info["timestamp"]

    result = {
        "table": table,
        "symbol_column": symbol_col,
        "timestamp_column": timestamp_col,
        "matches": 0,
    }

    if not symbol_col or not timestamp_col:

        return result

    matched = set()

    for symbol, timestamp in identities:

        rows = conn.execute(
            f"""
            SELECT {timestamp_col}
            FROM {table}
            WHERE LOWER(TRIM(CAST({symbol_col} AS TEXT))) = ?
            LIMIT 100
            """,
            (symbol,),
        ).fetchall()

        target = normalize(
            timestamp
        )

        for row in rows:

            candidate = normalize(
                row[0]
            )

            if candidate == target:

                matched.add(
                    (
                        symbol,
                        timestamp,
                    )
                )

                break

    result["matches"] = len(
        matched
    )

    result["match_ratio"] = (
        len(matched) / len(identities)
        if identities
        else 0.0
    )

    return result


# =============================================================================
# MAIN FORENSIC
# =============================================================================

def main() -> None:

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> OUTCOME PATH FORENSIC v0.1"
    )
    print("=" * 90)

    print(
        f"Database        : {DB_PATH}"
    )

    print(
        f"Feature Contract: {FEATURE_CONTRACT_PATH}"
    )

    print(
        "Mode            : READ ONLY"
    )

    print(
        "Network         : FORBIDDEN"
    )

    print(
        "Signal          : FORBIDDEN"
    )

    print(
        "Prediction      : FORBIDDEN"
    )

    print(
        "Decision        : FORBIDDEN"
    )

    print("-" * 90)

    contract = load_contract()

    identities = feature_identity_set(
        contract
    )

    print(
        f"Feature identities : {len(identities)}"
    )

    conn = connect()

    try:

        tables = list_tables(
            conn
        )

        print(
            f"Database tables   : {len(tables)}"
        )

        print("=" * 90)
        print(
            "OUTCOME PATH TABLE DISCOVERY"
        )
        print("=" * 90)

        priority_tables = [
            table
            for table in (
                "signal_outcomes",
                "fusion_signals",
                "market_data",
                "market_history",
                "market_state",
            )
            if table in tables
        ]

        for table in priority_tables:

            info = inspect_table(
                conn,
                table,
            )

            print()
            print(
                f"[TABLE] {table}"
            )

            print(
                f"Columns       : {info['columns']}"
            )

            print(
                f"Symbol        : {info['symbol']}"
            )

            print(
                f"Timestamp     : {info['timestamp']}"
            )

            print(
                f"Signal ID     : {info['signal_id']}"
            )

            print(
                f"Outcome ID     : {info['outcome_id']}"
            )

            print(
                f"Entry Price    : {info['entry_price']}"
            )

            print(
                f"Future Price   : {info['future_price']}"
            )

            print(
                f"Horizon        : {info['horizon']}"
            )

            print(
                f"Direction      : {info['direction']}"
            )

            print(
                "Sample:"
            )

            for sample in sample_rows(
                conn,
                table,
                3,
            ):

                print(
                    json.dumps(
                        sample,
                        ensure_ascii=False,
                        default=str,
                    )
                )

        print("=" * 90)
        print(
            "FEATURE IDENTITY -> TABLE MATCH TEST"
        )
        print("=" * 90)

        for table in priority_tables:

            direct = direct_match_test(
                conn,
                table,
                identities,
            )

            relaxed = relaxed_timestamp_match(
                conn,
                table,
                identities,
            )

            print()
            print(
                f"TABLE                  : {table}"
            )

            print(
                f"DIRECT MATCHES         : {direct['matches']}"
            )

            print(
                f"DIRECT RATIO           : "
                f"{direct.get('match_ratio', 0.0):.4f}"
            )

            print(
                f"RELAXED MATCHES        : {relaxed['matches']}"
            )

            print(
                f"RELAXED RATIO          : "
                f"{relaxed.get('match_ratio', 0.0):.4f}"
            )

        print("=" * 90)
        print(
            "SCHEMA-LEVEL FOREIGN KEY / IDENTITY TRACE"
        )
        print("=" * 90)

        for table in priority_tables:

            print()
            print(
                f"[FOREIGN KEYS] {table}"
            )

            rows = conn.execute(
                f"PRAGMA foreign_key_list({table})"
            ).fetchall()

            if not rows:

                print(
                    "None declared."
                )

            else:

                for row in rows:

                    print(
                        dict(row)
                    )

        print("=" * 90)
        print(
            "FORENSIC STATUS"
        )
        print("=" * 90)

        print(
            "NO PREDICTIVE CLAIM WAS MADE."
        )

        print(
            "NO RELATIONSHIP WAS CALCULATED."
        )

        print(
            "NO DATABASE WAS MODIFIED."
        )

        print(
            "The output above identifies the real "
            "Outcome schema and identity path required "
            "for the next repair."
        )

        print("=" * 90)

    finally:

        conn.close()


if __name__ == "__main__":
    main()