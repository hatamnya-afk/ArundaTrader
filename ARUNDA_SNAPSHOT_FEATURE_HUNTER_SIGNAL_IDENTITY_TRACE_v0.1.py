# =============================================================================
# ARUNDA SNAPSHOT FEATURE -> HUNTER SIGNAL IDENTITY TRACE v0.1
# =============================================================================
#
# PURPOSE:
#   READ-ONLY FORENSIC TRACE OF THE REAL IDENTITY PATH BETWEEN:
#
#       SNAPSHOT FEATURE CONTRACT
#               |
#               v
#          hunter_signals
#               |
#          signal_id / id
#               v
#        signal_outcomes
#
# IMPORTANT:
#   This script does NOT calculate predictive relationships.
#   This script does NOT make predictive claims.
#   This script only discovers and verifies the real identity path.
#
# MODE:
#   READ ONLY
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
#   EXCHANGE
#   SIGNAL GENERATION
#   PREDICTION
#   TRADING DECISION
#   SYNTHETIC DATA
#   INTERPOLATION
#   FORWARD FILL
#   BACK FILL
# =============================================================================

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


# =============================================================================
# PATHS
# =============================================================================

DB_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

FEATURE_CONTRACT_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)

OUTPUT_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_HUNTER_SIGNAL_IDENTITY_TRACE_v0.1.json"
)


# =============================================================================
# CONTRACT
# =============================================================================

CONTRACT_VERSION = (
    "ARUNDA_SNAPSHOT_FEATURE_HUNTER_SIGNAL_IDENTITY_TRACE_v0.1"
)

FEATURE_CONTRACT_VERSION = (
    "ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1"
)

OUTCOME_TABLE = "signal_outcomes"
HUNTER_TABLE = "hunter_signals"


# =============================================================================
# DATABASE
# =============================================================================

def connect_database() -> sqlite3.Connection:

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    connection = sqlite3.connect(
        f"file:{DB_PATH.as_posix()}?mode=ro",
        uri=True,
    )

    connection.row_factory = sqlite3.Row

    return connection


# =============================================================================
# SAFE TABLE / SCHEMA HELPERS
# =============================================================================

def quote_identifier(identifier: str) -> str:

    return '"' + identifier.replace('"', '""') + '"'


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:

    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[dict[str, Any]]:

    if not table_exists(
        connection,
        table_name,
    ):
        return []

    rows = connection.execute(
        f"PRAGMA table_info({quote_identifier(table_name)})"
    ).fetchall()

    return [
        {
            "cid": row["cid"],
            "name": row["name"],
            "type": row["type"],
            "notnull": row["notnull"],
            "default": row["dflt_value"],
            "pk": row["pk"],
        }
        for row in rows
    ]


def get_foreign_keys(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[dict[str, Any]]:

    if not table_exists(
        connection,
        table_name,
    ):
        return []

    rows = connection.execute(
        f"PRAGMA foreign_key_list({quote_identifier(table_name)})"
    ).fetchall()

    return [
        {
            "id": row["id"],
            "seq": row["seq"],
            "table": row["table"],
            "from": row["from"],
            "to": row["to"],
            "on_update": row["on_update"],
            "on_delete": row["on_delete"],
            "match": row["match"],
        }
        for row in rows
    ]


def normalize_name(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip().lower()


# =============================================================================
# FEATURE CONTRACT
# =============================================================================

def load_feature_contract() -> dict[str, Any]:

    if not FEATURE_CONTRACT_PATH.exists():
        raise FileNotFoundError(
            "Feature contract not found: "
            f"{FEATURE_CONTRACT_PATH}"
        )

    artifact = json.loads(
        FEATURE_CONTRACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if artifact.get("contract") != FEATURE_CONTRACT_VERSION:
        raise RuntimeError(
            "Unexpected feature contract version: "
            f"{artifact.get('contract')}"
        )

    if artifact.get("mode") != "READ_ONLY":
        raise RuntimeError(
            "Feature contract is not READ_ONLY."
        )

    return artifact


def extract_feature_identities(
    artifact: dict[str, Any],
) -> list[dict[str, Any]]:

    identities = []

    seen = set()

    for record in artifact.get(
        "records",
        [],
    ):

        symbol = record.get(
            "asset_symbol"
        )

        timestamp = record.get(
            "snapshot_timestamp"
        )

        key = (
            str(symbol),
            str(timestamp),
        )

        if key in seen:
            continue

        seen.add(key)

        identities.append(
            {
                "asset_symbol": symbol,
                "snapshot_timestamp": timestamp,
            }
        )

    return identities


# =============================================================================
# HUNTER SIGNAL SCHEMA DISCOVERY
# =============================================================================

def discover_identity_columns(
    columns: list[dict[str, Any]],
) -> dict[str, str | None]:

    names = {
        normalize_name(column["name"]):
            column["name"]
        for column in columns
    }

    aliases = {

        "id": (
            "id",
            "signal_id",
        ),

        "symbol": (
            "asset",
            "symbol",
            "asset_symbol",
            "market",
        ),

        "timestamp": (
            "timestamp",
            "signal_timestamp",
            "entry_timestamp",
            "created_at",
            "time",
        ),

        "entry_price": (
            "entry_price",
            "price",
        ),

        "direction": (
            "direction",
        ),

    }

    resolved = {}

    for logical_name, candidates in aliases.items():

        resolved[logical_name] = None

        for candidate in candidates:

            if candidate.lower() in names:

                resolved[logical_name] = names[
                    candidate.lower()
                ]

                break

    return resolved


# =============================================================================
# OUTCOME SCHEMA DISCOVERY
# =============================================================================

def discover_outcome_columns(
    columns: list[dict[str, Any]],
) -> dict[str, str | None]:

    names = {
        normalize_name(column["name"]):
            column["name"]
        for column in columns
    }

    aliases = {

        "id": (
            "id",
        ),

        "signal_id": (
            "signal_id",
        ),

        "symbol": (
            "asset",
            "symbol",
            "asset_symbol",
            "market",
        ),

        "timestamp": (
            "timestamp",
            "entry_timestamp",
        ),

        "entry_price": (
            "entry_price",
        ),

        "price_5m": (
            "price_5m",
        ),

        "price_15m": (
            "price_15m",
        ),

        "price_30m": (
            "price_30m",
        ),

        "price_60m": (
            "price_60m",
        ),

        "return_5m": (
            "return_5m",
        ),

        "return_15m": (
            "return_15m",
        ),

        "return_30m": (
            "return_30m",
        ),

        "return_60m": (
            "return_60m",
        ),

        "outcome_5m": (
            "outcome_5m",
        ),

        "outcome_15m": (
            "outcome_15m",
        ),

        "outcome_30m": (
            "outcome_30m",
        ),

        "outcome_60m": (
            "outcome_60m",
        ),

    }

    resolved = {}

    for logical_name, candidates in aliases.items():

        resolved[logical_name] = None

        for candidate in candidates:

            if candidate.lower() in names:

                resolved[logical_name] = names[
                    candidate.lower()
                ]

                break

    return resolved


# =============================================================================
# FEATURE -> HUNTER SIGNAL MATCHING
# =============================================================================

def find_direct_matches(
    connection: sqlite3.Connection,
    feature_identities: list[dict[str, Any]],
    hunter_columns: dict[str, str | None],
) -> list[dict[str, Any]]:

    symbol_column = hunter_columns["symbol"]
    timestamp_column = hunter_columns["timestamp"]
    id_column = hunter_columns["id"]

    if not (
        symbol_column
        and timestamp_column
        and id_column
    ):
        return []

    query = f"""
        SELECT
            {quote_identifier(id_column)} AS hunter_id,
            {quote_identifier(symbol_column)} AS hunter_symbol,
            {quote_identifier(timestamp_column)} AS hunter_timestamp
        FROM {quote_identifier(HUNTER_TABLE)}
        WHERE {quote_identifier(symbol_column)} = ?
          AND {quote_identifier(timestamp_column)} = ?
        LIMIT 20
    """

    matches = []

    for identity in feature_identities:

        rows = connection.execute(
            query,
            (
                identity["asset_symbol"],
                identity["snapshot_timestamp"],
            ),
        ).fetchall()

        for row in rows:

            matches.append(
                {
                    "asset_symbol":
                        identity["asset_symbol"],

                    "snapshot_timestamp":
                        identity["snapshot_timestamp"],

                    "hunter_id":
                        row["hunter_id"],

                    "hunter_symbol":
                        row["hunter_symbol"],

                    "hunter_timestamp":
                        row["hunter_timestamp"],

                    "match_type":
                        "DIRECT_SYMBOL_TIMESTAMP",
                }
            )

    return matches


# =============================================================================
# RELAXED TIMESTAMP MATCHING
# =============================================================================

def find_relaxed_matches(
    connection: sqlite3.Connection,
    feature_identities: list[dict[str, Any]],
    hunter_columns: dict[str, str | None],
    tolerance_seconds: int = 2,
) -> list[dict[str, Any]]:

    symbol_column = hunter_columns["symbol"]
    timestamp_column = hunter_columns["timestamp"]
    id_column = hunter_columns["id"]

    if not (
        symbol_column
        and timestamp_column
        and id_column
    ):
        return []

    # SQLite datetime arithmetic is intentionally avoided here.
    # The stored timestamps may contain different timezone representations.
    #
    # Therefore this pass first retrieves candidate rows by symbol and
    # performs timestamp normalization in Python.
    #
    # No timestamp is synthesized or modified.

    query = f"""
        SELECT
            {quote_identifier(id_column)} AS hunter_id,
            {quote_identifier(symbol_column)} AS hunter_symbol,
            {quote_identifier(timestamp_column)} AS hunter_timestamp
        FROM {quote_identifier(HUNTER_TABLE)}
        WHERE {quote_identifier(symbol_column)} = ?
        ORDER BY {quote_identifier(timestamp_column)} ASC
    """

    matches = []

    for identity in feature_identities:

        rows = connection.execute(
            query,
            (
                identity["asset_symbol"],
            ),
        ).fetchall()

        target = normalize_timestamp(
            identity["snapshot_timestamp"]
        )

        if target is None:
            continue

        best = None
        best_distance = None

        for row in rows:

            candidate = normalize_timestamp(
                row["hunter_timestamp"]
            )

            if candidate is None:
                continue

            distance = abs(
                (candidate - target).total_seconds()
            )

            if distance <= tolerance_seconds:

                if (
                    best_distance is None
                    or distance < best_distance
                ):

                    best = row
                    best_distance = distance

        if best is not None:

            matches.append(
                {
                    "asset_symbol":
                        identity["asset_symbol"],

                    "snapshot_timestamp":
                        identity["snapshot_timestamp"],

                    "hunter_id":
                        best["hunter_id"],

                    "hunter_symbol":
                        best["hunter_symbol"],

                    "hunter_timestamp":
                        best["hunter_timestamp"],

                    "timestamp_distance_seconds":
                        best_distance,

                    "match_type":
                        "RELAXED_SYMBOL_TIMESTAMP",
                }
            )

    return matches


# =============================================================================
# TIMESTAMP NORMALIZATION
# =============================================================================

def normalize_timestamp(
    value: Any,
):
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    from datetime import datetime, timezone

    candidate = text

    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(
            candidate
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:

        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


# =============================================================================
# OUTCOME -> HUNTER IDENTITY MATCH
# =============================================================================

def trace_outcome_to_hunter(
    connection: sqlite3.Connection,
    hunter_columns: dict[str, str | None],
    outcome_columns: dict[str, str | None],
) -> dict[str, Any]:

    hunter_id = hunter_columns["id"]
    outcome_signal_id = outcome_columns["signal_id"]
    outcome_id = outcome_columns["id"]

    if not (
        hunter_id
        and outcome_signal_id
        and outcome_id
    ):
        return {
            "available": False,
            "reason":
                "Required identity columns unavailable.",
        }

    outcome_total = connection.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM {quote_identifier(OUTCOME_TABLE)}
        """
    ).fetchone()["count"]

    linked = connection.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM {quote_identifier(OUTCOME_TABLE)} o
        INNER JOIN {quote_identifier(HUNTER_TABLE)} h
            ON o.{quote_identifier(outcome_signal_id)}
             = h.{quote_identifier(hunter_id)}
        """
    ).fetchone()["count"]

    distinct_signal_ids = connection.execute(
        f"""
        SELECT COUNT(DISTINCT {quote_identifier(outcome_signal_id)}) AS count
        FROM {quote_identifier(OUTCOME_TABLE)}
        WHERE {quote_identifier(outcome_signal_id)} IS NOT NULL
        """
    ).fetchone()["count"]

    null_signal_ids = connection.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM {quote_identifier(OUTCOME_TABLE)}
        WHERE {quote_identifier(outcome_signal_id)} IS NULL
        """
    ).fetchone()["count"]

    orphaned = outcome_total - linked

    return {

        "available": True,

        "outcome_rows":
            outcome_total,

        "distinct_outcome_signal_ids":
            distinct_signal_ids,

        "null_outcome_signal_ids":
            null_signal_ids,

        "outcome_rows_linked_to_hunter":
            linked,

        "outcome_rows_without_hunter_match":
            orphaned,

        "link_ratio":
            (
                linked / outcome_total
                if outcome_total
                else 0.0
            ),

        "identity_relation":
            "signal_outcomes.signal_id -> hunter_signals.id",

    }


# =============================================================================
# SAMPLE IDENTITY CHAIN
# =============================================================================

def build_sample_chains(
    connection: sqlite3.Connection,
    hunter_columns: dict[str, str | None],
    outcome_columns: dict[str, str | None],
    limit: int = 20,
) -> list[dict[str, Any]]:

    hunter_id = hunter_columns["id"]
    hunter_symbol = hunter_columns["symbol"]
    hunter_timestamp = hunter_columns["timestamp"]

    outcome_id = outcome_columns["id"]
    outcome_signal_id = outcome_columns["signal_id"]
    outcome_symbol = outcome_columns["symbol"]
    outcome_timestamp = outcome_columns["timestamp"]

    if not (
        hunter_id
        and outcome_id
        and outcome_signal_id
    ):
        return []

    selected_hunter_symbol = (
        quote_identifier(hunter_symbol)
        if hunter_symbol
        else "NULL"
    )

    selected_hunter_timestamp = (
        quote_identifier(hunter_timestamp)
        if hunter_timestamp
        else "NULL"
    )

    selected_outcome_symbol = (
        quote_identifier(outcome_symbol)
        if outcome_symbol
        else "NULL"
    )

    selected_outcome_timestamp = (
        quote_identifier(outcome_timestamp)
        if outcome_timestamp
        else "NULL"
    )

    query = f"""
        SELECT
            h.{quote_identifier(hunter_id)} AS hunter_id,
            h.{selected_hunter_symbol} AS hunter_symbol,
            h.{selected_hunter_timestamp} AS hunter_timestamp,

            o.{quote_identifier(outcome_id)} AS outcome_id,
            o.{quote_identifier(outcome_signal_id)}
                AS outcome_signal_id,

            o.{selected_outcome_symbol} AS outcome_symbol,
            o.{selected_outcome_timestamp}
                AS outcome_timestamp

        FROM {quote_identifier(HUNTER_TABLE)} h

        INNER JOIN {quote_identifier(OUTCOME_TABLE)} o
            ON o.{quote_identifier(outcome_signal_id)}
             = h.{quote_identifier(hunter_id)}

        ORDER BY
            h.{quote_identifier(hunter_id)} ASC

        LIMIT ?
    """

    rows = connection.execute(
        query,
        (limit,),
    ).fetchall()

    return [
        {
            "hunter_id":
                row["hunter_id"],

            "hunter_symbol":
                row["hunter_symbol"],

            "hunter_timestamp":
                row["hunter_timestamp"],

            "outcome_id":
                row["outcome_id"],

            "outcome_signal_id":
                row["outcome_signal_id"],

            "outcome_symbol":
                row["outcome_symbol"],

            "outcome_timestamp":
                row["outcome_timestamp"],
        }
        for row in rows
    ]


# =============================================================================
# COLUMN VALUE STATISTICS
# =============================================================================

def column_population(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> dict[str, Any]:

    total = connection.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM {quote_identifier(table_name)}
        """
    ).fetchone()["count"]

    non_null = connection.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM {quote_identifier(table_name)}
        WHERE {quote_identifier(column_name)} IS NOT NULL
        """
    ).fetchone()["count"]

    distinct = connection.execute(
        f"""
        SELECT COUNT(DISTINCT {quote_identifier(column_name)}) AS count
        FROM {quote_identifier(table_name)}
        WHERE {quote_identifier(column_name)} IS NOT NULL
        """
    ).fetchone()["count"]

    return {
        "total_rows": total,
        "non_null_rows": non_null,
        "null_rows": total - non_null,
        "distinct_non_null": distinct,
        "population_ratio":
            (
                non_null / total
                if total
                else 0.0
            ),
    }


# =============================================================================
# ARTIFACT HASH
# =============================================================================

def attach_hash(
    artifact: dict[str, Any],
) -> dict[str, Any]:

    canonical = json.dumps(
        artifact,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()

    artifact["artifact_sha256"] = digest

    return artifact


# =============================================================================
# VALIDATION
# =============================================================================

def validate_artifact(
    artifact: dict[str, Any],
) -> None:

    assert (
        artifact["contract"]
        == CONTRACT_VERSION
    )

    assert (
        artifact["mode"]
        == "READ_ONLY"
    )

    assert (
        artifact["network"]
        is False
    )

    assert (
        artifact["prediction"]
        is False
    )

    assert (
        artifact["trading_decision"]
        is False
    )

    assert (
        artifact["database_modified"]
        is False
    )

    assert (
        artifact["feature_contract"]
        == FEATURE_CONTRACT_VERSION
    )


# =============================================================================
# BUILD FORENSIC ARTIFACT
# =============================================================================

def build_artifact(
    connection: sqlite3.Connection,
    feature_contract: dict[str, Any],
) -> dict[str, Any]:

    feature_identities = (
        extract_feature_identities(
            feature_contract
        )
    )

    hunter_columns = get_table_columns(
        connection,
        HUNTER_TABLE,
    )

    outcome_columns = get_table_columns(
        connection,
        OUTCOME_TABLE,
    )

    if not hunter_columns:
        raise RuntimeError(
            "hunter_signals table not found."
        )

    if not outcome_columns:
        raise RuntimeError(
            "signal_outcomes table not found."
        )

    hunter_identity = discover_identity_columns(
        hunter_columns
    )

    outcome_identity = discover_outcome_columns(
        outcome_columns
    )

    direct_matches = find_direct_matches(
        connection,
        feature_identities,
        hunter_identity,
    )

    relaxed_matches = find_relaxed_matches(
        connection,
        feature_identities,
        hunter_identity,
    )

    outcome_trace = trace_outcome_to_hunter(
        connection,
        hunter_identity,
        outcome_identity,
    )

    sample_chains = build_sample_chains(
        connection,
        hunter_identity,
        outcome_identity,
    )

    foreign_keys = {
        HUNTER_TABLE:
            get_foreign_keys(
                connection,
                HUNTER_TABLE,
            ),

        OUTCOME_TABLE:
            get_foreign_keys(
                connection,
                OUTCOME_TABLE,
            ),
    }

    population = {}

    for logical_name, column_name in (
        (
            "hunter_id",
            hunter_identity["id"],
        ),
        (
            "hunter_symbol",
            hunter_identity["symbol"],
        ),
        (
            "hunter_timestamp",
            hunter_identity["timestamp"],
        ),
        (
            "outcome_id",
            outcome_identity["id"],
        ),
        (
            "outcome_signal_id",
            outcome_identity["signal_id"],
        ),
        (
            "outcome_symbol",
            outcome_identity["symbol"],
        ),
        (
            "outcome_timestamp",
            outcome_identity["timestamp"],
        ),
    ):

        if column_name:

            table_name = (
                HUNTER_TABLE
                if logical_name.startswith("hunter_")
                else OUTCOME_TABLE
            )

            population[
                logical_name
            ] = column_population(
                connection,
                table_name,
                column_name,
            )

    feature_count = len(
        feature_identities
    )

    direct_count = len(
        direct_matches
    )

    relaxed_count = len(
        relaxed_matches
    )

    if (
        outcome_trace.get("available")
        and outcome_trace.get(
            "outcome_rows_linked_to_hunter",
            0,
        ) > 0
        and (
            direct_count > 0
            or relaxed_count > 0
        )
    ):

        forensic_status = (
            "IDENTITY_PATH_ESTABLISHED"
        )

    elif (
        outcome_trace.get("available")
        and outcome_trace.get(
            "outcome_rows_linked_to_hunter",
            0,
        ) > 0
    ):

        forensic_status = (
            "OUTCOME_TO_HUNTER_ESTABLISHED"
        )

    else:

        forensic_status = (
            "IDENTITY_PATH_NOT_ESTABLISHED"
        )

    return {

        "contract":
            CONTRACT_VERSION,

        "mode":
            "READ_ONLY",

        "database":
            str(DB_PATH),

        "feature_contract":
            FEATURE_CONTRACT_VERSION,

        "feature_contract_path":
            str(FEATURE_CONTRACT_PATH),

        "network":
            False,

        "prediction":
            False,

        "trading_decision":
            False,

        "database_modified":
            False,

        "feature_identity_count":
            feature_count,

        "feature_identities_sample":
            feature_identities[:20],

        "tables": {

            HUNTER_TABLE: {
                "exists": True,
                "columns": hunter_columns,
                "resolved_identity":
                    hunter_identity,
                "foreign_keys":
                    foreign_keys[HUNTER_TABLE],
            },

            OUTCOME_TABLE: {
                "exists": True,
                "columns": outcome_columns,
                "resolved_identity":
                    outcome_identity,
                "foreign_keys":
                    foreign_keys[OUTCOME_TABLE],
            },

        },

        "column_population":
            population,

        "feature_to_hunter": {

            "direct_match_count":
                direct_count,

            "direct_match_ratio":
                (
                    direct_count / feature_count
                    if feature_count
                    else 0.0
                ),

            "relaxed_match_count":
                relaxed_count,

            "relaxed_match_ratio":
                (
                    relaxed_count / feature_count
                    if feature_count
                    else 0.0
                ),

            "direct_matches":
                direct_matches[:100],

            "relaxed_matches":
                relaxed_matches[:100],

        },

        "outcome_to_hunter":
            outcome_trace,

        "sample_identity_chains":
            sample_chains,

        "candidate_real_identity_path":
            {
                "feature_identity":
                    "asset_symbol + snapshot_timestamp",

                "candidate_intermediate_table":
                    HUNTER_TABLE,

                "candidate_intermediate_identity":
                    "hunter_signals.id",

                "outcome_table":
                    OUTCOME_TABLE,

                "outcome_identity":
                    "signal_outcomes.signal_id",

                "relationship":
                    "signal_outcomes.signal_id = hunter_signals.id",
            },

        "forensic_status":
            forensic_status,

        "predictive_claim":
            "NOT_ESTABLISHED",

        "relationship_calculation":
            "NOT_PERFORMED",

    }


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> HUNTER SIGNAL IDENTITY TRACE v0.1"
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
        "Prediction      : FORBIDDEN"
    )

    print(
        "Decision        : FORBIDDEN"
    )

    print("-" * 90)

    feature_contract = (
        load_feature_contract()
    )

    connection = connect_database()

    try:

        artifact = build_artifact(
            connection,
            feature_contract,
        )

    finally:

        connection.close()

    validate_artifact(
        artifact
    )

    artifact = attach_hash(
        artifact
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            artifact,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    hunter_identity = (
        artifact["tables"]
        [HUNTER_TABLE]
        ["resolved_identity"]
    )

    outcome_identity = (
        artifact["tables"]
        [OUTCOME_TABLE]
        ["resolved_identity"]
    )

    feature_to_hunter = (
        artifact["feature_to_hunter"]
    )

    outcome_to_hunter = (
        artifact["outcome_to_hunter"]
    )

    print("=" * 90)
    print(
        "HUNTER SIGNAL IDENTITY TRACE"
    )
    print("=" * 90)

    print(
        f"Feature identities       : "
        f"{artifact['feature_identity_count']}"
    )

    print(
        f"Hunter ID column        : "
        f"{hunter_identity['id']}"
    )

    print(
        f"Hunter Symbol column    : "
        f"{hunter_identity['symbol']}"
    )

    print(
        f"Hunter Timestamp column : "
        f"{hunter_identity['timestamp']}"
    )

    print(
        f"Outcome ID column       : "
        f"{outcome_identity['id']}"
    )

    print(
        f"Outcome signal_id       : "
        f"{outcome_identity['signal_id']}"
    )

    print("-" * 90)

    print(
        f"Feature -> Hunter direct matches : "
        f"{feature_to_hunter['direct_match_count']}"
    )

    print(
        f"Feature -> Hunter relaxed matches: "
        f"{feature_to_hunter['relaxed_match_count']}"
    )

    print(
        f"Outcome rows              : "
        f"{outcome_to_hunter.get('outcome_rows', 0)}"
    )

    print(
        f"Outcome -> Hunter linked   : "
        f"{outcome_to_hunter.get('outcome_rows_linked_to_hunter', 0)}"
    )

    print(
        f"Outcome -> Hunter orphaned : "
        f"{outcome_to_hunter.get('outcome_rows_without_hunter_match', 0)}"
    )

    print("-" * 90)

    print(
        "CANDIDATE REAL OUTCOME IDENTITY PATH"
    )

    print(
        "Feature:"
    )

    print(
        "    asset_symbol + snapshot_timestamp"
    )

    print(
        "        -> hunter_signals"
    )

    print(
        "        -> hunter_signals.id"
    )

    print(
        "        -> signal_outcomes.signal_id"
    )

    print(
        "        -> signal_outcomes"
    )

    print("-" * 90)

    print(
        f"FORENSIC STATUS : "
        f"{artifact['forensic_status']}"
    )

    print(
        "PREDICTIVE CLAIM : NOT ESTABLISHED"
    )

    print(
        "RELATIONSHIP CALCULATION : NOT PERFORMED"
    )

    print(
        f"Artifact : {OUTPUT_PATH}"
    )

    print(
        f"SHA256   : "
        f"{artifact['artifact_sha256']}"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()