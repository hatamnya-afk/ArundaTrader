from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any


# =============================================================================
# ARUNDA SNAPSHOT FEATURE -> HUNTER TIMESTAMP NORMALIZATION FORENSIC v0.3
# =============================================================================
#
# PURPOSE:
#   Diagnose and repair the FEATURE -> HUNTER timestamp identity boundary.
#
# MODE:
#   READ ONLY
#
# FORBIDDEN:
#   DB WRITE
#   NETWORK
#   OUTCOME CALCULATION
#   PREDICTION
#   DECISION
#
# IMPORTANT:
#   This forensic does NOT calculate Feature -> Outcome relationships.
#
#   It only establishes whether:
#
#       Feature asset_symbol + snapshot_timestamp
#           ->
#       hunter_signals asset + timestamp
#
#   can be matched after identity normalization.
#
# KEY REPAIR:
#   DO NOT LIMIT hunter_signals before symbol matching.
#   ALL Hunter rows are inspected.
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
    r"\ARUNDA_SNAPSHOT_FEATURE_HUNTER_TIMESTAMP_NORMALIZATION_FORENSIC_v0.3.json"
)


CONTRACT_VERSION = (
    "ARUNDA_SNAPSHOT_FEATURE_HUNTER_TIMESTAMP_NORMALIZATION_FORENSIC_v0.3"
)

MATCH_TOLERANCES = (
    120,
    300,
    600,
)


# =============================================================================
# DATABASE
# =============================================================================

def connect_database() -> sqlite3.Connection:

    if not DB_PATH.exists():
        raise FileNotFoundError(DB_PATH)

    connection = sqlite3.connect(
        DB_PATH,
        uri=False,
    )

    connection.row_factory = sqlite3.Row

    return connection


# =============================================================================
# TIMESTAMP NORMALIZATION
# =============================================================================

def parse_timestamp(
    value: Any,
) -> datetime | None:

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    # ISO Z
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:

        dt = datetime.fromisoformat(text)

    except ValueError:

        # fallback for common SQLite format
        formats = (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        )

        dt = None

        for fmt in formats:

            try:
                dt = datetime.strptime(
                    text,
                    fmt,
                )
                break

            except ValueError:
                continue

        if dt is None:
            return None

    # Canonical internal representation:
    # UTC-aware datetime.
    if dt.tzinfo is None:

        # IMPORTANT:
        # Naive database timestamps are treated as wall-clock UTC
        # for forensic comparison only.
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    else:

        dt = dt.astimezone(
            timezone.utc
        )

    return dt


# =============================================================================
# SYMBOL NORMALIZATION
# =============================================================================

def normalize_symbol(
    value: Any,
) -> str | None:

    if value is None:
        return None

    text = str(value).strip().upper()

    if not text:
        return None

    # Remove whitespace around separators.
    text = re.sub(
        r"\s+",
        "",
        text,
    )

    # Explicit market suffixes are normalized only for identity comparison.
    #
    # Examples:
    # BTC/USDT -> BTC
    # BTC-USDT -> BTC
    # BTC_USDT -> BTC
    #
    # This does NOT modify DB data.
    for separator in (
        "/",
        "-",
        "_",
    ):

        if separator in text:

            left, right = text.split(
                separator,
                1,
            )

            if right in {
                "USDT",
                "USDC",
                "IRT",
                "IRR",
                "USD",
                "BTC",
                "ETH",
            }:

                text = left

            break

    return text


# =============================================================================
# FEATURE CONTRACT
# =============================================================================

def load_feature_contract() -> dict[str, Any]:

    if not FEATURE_CONTRACT_PATH.exists():
        raise FileNotFoundError(
            FEATURE_CONTRACT_PATH
        )

    artifact = json.loads(
        FEATURE_CONTRACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not artifact.get("records"):
        raise RuntimeError(
            "Feature contract contains no records."
        )

    return artifact


# =============================================================================
# FEATURE IDENTITY EXTRACTION
# =============================================================================

def load_feature_identities(
    artifact: dict[str, Any],
) -> list[dict[str, Any]]:

    identities = []

    for record in artifact["records"]:

        symbol = record.get(
            "asset_symbol"
        )

        timestamp = record.get(
            "snapshot_timestamp"
        )

        parsed = parse_timestamp(
            timestamp
        )

        normalized = normalize_symbol(
            symbol
        )

        identities.append(
            {
                "asset_symbol": symbol,
                "normalized_symbol": normalized,
                "snapshot_timestamp": timestamp,
                "parsed_timestamp": parsed,
            }
        )

    return identities


# =============================================================================
# HUNTER SCHEMA
# =============================================================================

def get_table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[str]:

    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    if not rows:
        raise RuntimeError(
            f"Table not found: {table_name}"
        )

    return [
        row["name"]
        for row in rows
    ]


def resolve_column(
    columns: list[str],
    aliases: tuple[str, ...],
) -> str | None:

    lookup = {
        column.lower(): column
        for column in columns
    }

    for alias in aliases:

        if alias.lower() in lookup:
            return lookup[alias.lower()]

    return None


def resolve_hunter_schema(
    connection: sqlite3.Connection,
) -> dict[str, str]:

    columns = get_table_columns(
        connection,
        "hunter_signals",
    )

    id_column = resolve_column(
        columns,
        (
            "id",
            "signal_id",
        ),
    )

    symbol_column = resolve_column(
        columns,
        (
            "asset",
            "symbol",
            "asset_symbol",
            "market",
        ),
    )

    timestamp_column = resolve_column(
        columns,
        (
            "timestamp",
            "signal_timestamp",
            "created_at",
            "entry_timestamp",
        ),
    )

    if not id_column:
        raise RuntimeError(
            "hunter_signals ID column not resolved."
        )

    if not symbol_column:
        raise RuntimeError(
            "hunter_signals symbol column not resolved."
        )

    if not timestamp_column:
        raise RuntimeError(
            "hunter_signals timestamp column not resolved."
        )

    return {
        "id": id_column,
        "symbol": symbol_column,
        "timestamp": timestamp_column,
    }


# =============================================================================
# CRITICAL REPAIR:
# LOAD ALL HUNTER ROWS
# =============================================================================

def load_all_hunter_rows(
    connection: sqlite3.Connection,
    schema: dict[str, str],
) -> list[sqlite3.Row]:

    query = f"""
        SELECT
            {schema["id"]} AS hunter_id,
            {schema["symbol"]} AS hunter_symbol,
            {schema["timestamp"]} AS hunter_timestamp
        FROM hunter_signals
        ORDER BY {schema["timestamp"]} ASC
    """

    return connection.execute(
        query
    ).fetchall()


# =============================================================================
# INDEX HUNTER ROWS BY NORMALIZED SYMBOL
# =============================================================================

def build_hunter_index(
    rows: list[sqlite3.Row],
) -> dict[str, list[dict[str, Any]]]:

    index: dict[
        str,
        list[dict[str, Any]]
    ] = {}

    for row in rows:

        symbol = normalize_symbol(
            row["hunter_symbol"]
        )

        timestamp = parse_timestamp(
            row["hunter_timestamp"]
        )

        if symbol is None:
            continue

        item = {
            "hunter_id":
                row["hunter_id"],

            "hunter_symbol":
                row["hunter_symbol"],

            "hunter_timestamp":
                row["hunter_timestamp"],

            "parsed_timestamp":
                timestamp,
        }

        index.setdefault(
            symbol,
            [],
        ).append(
            item
        )

    return index


# =============================================================================
# NEAREST HUNTER MATCH
# =============================================================================

def find_nearest_hunter(
    feature_timestamp: datetime,
    hunter_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, float | None]:

    nearest = None
    nearest_delta = None

    for hunter in hunter_rows:

        hunter_timestamp = hunter[
            "parsed_timestamp"
        ]

        if hunter_timestamp is None:
            continue

        delta = abs(
            (
                hunter_timestamp
                - feature_timestamp
            ).total_seconds()
        )

        if (
            nearest_delta is None
            or delta < nearest_delta
        ):

            nearest_delta = delta
            nearest = hunter

    return nearest, nearest_delta


# =============================================================================
# FORENSIC
# =============================================================================

def run_forensic(
    feature_identities: list[dict[str, Any]],
    hunter_rows: list[sqlite3.Row],
    hunter_index: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:

    results = []

    exact_matches = 0
    within_120 = 0
    within_300 = 0
    within_600 = 0

    no_symbol_match = 0
    timestamp_unavailable = 0

    deltas = []

    hunter_symbols_seen = set()

    for row in hunter_rows:

        normalized = normalize_symbol(
            row["hunter_symbol"]
        )

        if normalized:
            hunter_symbols_seen.add(
                normalized
            )

    for feature in feature_identities:

        feature_symbol = feature[
            "asset_symbol"
        ]

        normalized_symbol = feature[
            "normalized_symbol"
        ]

        feature_timestamp = feature[
            "parsed_timestamp"
        ]

        symbol_candidates = hunter_index.get(
            normalized_symbol,
            [],
        )

        result = {
            "asset_symbol":
                feature_symbol,

            "normalized_symbol":
                normalized_symbol,

            "feature_timestamp":
                feature["snapshot_timestamp"],

            "feature_timestamp_utc":
                (
                    feature_timestamp.isoformat()
                    if feature_timestamp
                    else None
                ),

            "symbol_candidate_count":
                len(symbol_candidates),

            "nearest_hunter_id":
                None,

            "nearest_hunter_symbol":
                None,

            "nearest_hunter_timestamp":
                None,

            "nearest_hunter_timestamp_utc":
                None,

            "delta_seconds":
                None,

            "within_120s":
                False,

            "within_300s":
                False,

            "within_600s":
                False,

            "identity_status":
                None,
        }

        if not symbol_candidates:

            no_symbol_match += 1

            result[
                "identity_status"
            ] = "NO_SYMBOL_MATCH"

            results.append(
                result
            )

            continue

        if feature_timestamp is None:

            timestamp_unavailable += 1

            result[
                "identity_status"
            ] = "FEATURE_TIMESTAMP_UNPARSEABLE"

            results.append(
                result
            )

            continue

        nearest, delta = find_nearest_hunter(
            feature_timestamp,
            symbol_candidates,
        )

        if nearest is None:

            timestamp_unavailable += 1

            result[
                "identity_status"
            ] = "HUNTER_TIMESTAMP_UNPARSEABLE"

            results.append(
                result
            )

            continue

        result[
            "nearest_hunter_id"
        ] = nearest[
            "hunter_id"
        ]

        result[
            "nearest_hunter_symbol"
        ] = nearest[
            "hunter_symbol"
        ]

        result[
            "nearest_hunter_timestamp"
        ] = nearest[
            "hunter_timestamp"
        ]

        result[
            "nearest_hunter_timestamp_utc"
        ] = nearest[
            "parsed_timestamp"
        ].isoformat()

        result[
            "delta_seconds"
        ] = delta

        deltas.append(
            delta
        )

        if delta == 0:
            exact_matches += 1

        if delta <= 120:

            within_120 += 1
            result[
                "within_120s"
            ] = True

        if delta <= 300:

            within_300 += 1
            result[
                "within_300s"
            ] = True

        if delta <= 600:

            within_600 += 1
            result[
                "within_600s"
            ] = True

        if delta == 0:

            result[
                "identity_status"
            ] = "EXACT_TIMESTAMP_MATCH"

        elif delta <= 120:

            result[
                "identity_status"
            ] = "MATCH_WITHIN_120S"

        elif delta <= 300:

            result[
                "identity_status"
            ] = "MATCH_WITHIN_300S"

        elif delta <= 600:

            result[
                "identity_status"
            ] = "MATCH_WITHIN_600S"

        else:

            result[
                "identity_status"
            ] = "SAME_SYMBOL_TIMESTAMP_MISMATCH"

        results.append(
            result
        )

    summary = {

        "feature_identities":
            len(feature_identities),

        "hunter_rows_total":
            len(hunter_rows),

        "hunter_symbols_total":
            len(hunter_symbols_seen),

        "exact_timestamp_matches":
            exact_matches,

        "within_120s":
            within_120,

        "within_300s":
            within_300,

        "within_600s":
            within_600,

        "same_symbol_timestamp_mismatch":
            sum(
                1
                for item in results
                if item["identity_status"]
                == "SAME_SYMBOL_TIMESTAMP_MISMATCH"
            ),

        "no_symbol_match":
            no_symbol_match,

        "timestamp_unavailable":
            timestamp_unavailable,

        "minimum_delta_seconds":
            min(deltas)
            if deltas
            else None,

        "maximum_delta_seconds":
            max(deltas)
            if deltas
            else None,

        "mean_delta_seconds":
            mean(deltas)
            if deltas
            else None,

        "median_delta_seconds":
            median(deltas)
            if deltas
            else None,
    }

    if (
        exact_matches == len(feature_identities)
    ):

        status = "TIMESTAMP_IDENTITY_ESTABLISHED"

    elif (
        within_120 == len(feature_identities)
    ):

        status = "TIMESTAMP_IDENTITY_WITHIN_120S"

    elif (
        within_300 == len(feature_identities)
    ):

        status = "TIMESTAMP_IDENTITY_WITHIN_300S"

    elif (
        within_600 == len(feature_identities)
    ):

        status = "TIMESTAMP_IDENTITY_WITHIN_600S"

    elif (
        no_symbol_match == 0
        and deltas
    ):

        status = (
            "SAME_SYMBOL_TIMESTAMP_DELTA_ESTABLISHED"
        )

    else:

        status = "TIMESTAMP_IDENTITY_NOT_ESTABLISHED"

    return {

        "contract":
            CONTRACT_VERSION,

        "mode":
            "READ_ONLY",

        "database":
            str(DB_PATH),

        "feature_contract":
            str(FEATURE_CONTRACT_PATH),

        "outcome":
            "NOT_CALCULATED",

        "prediction":
            False,

        "decision":
            False,

        "match_tolerances_seconds":
            list(MATCH_TOLERANCES),

        "hunter_schema":
            {
                "id":
                    "id",

                "symbol":
                    "asset",

                "timestamp":
                    "timestamp",
            },

        "critical_repair":
            "ALL hunter_signals rows were inspected before "
            "symbol/timestamp matching. No premature LIMIT was used.",

        "summary":
            summary,

        "results":
            results,

        "forensic_status":
            status,

        "predictive_claim":
            "NOT_ESTABLISHED",

        "relationship_calculation":
            "NOT_PERFORMED",

    }


# =============================================================================
# HASH
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
        canonical.encode(
            "utf-8"
        )
    ).hexdigest()

    artifact[
        "artifact_sha256"
    ] = digest

    return artifact


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> HUNTER "
        "TIMESTAMP NORMALIZATION FORENSIC v0.3"
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
        "Outcome         : NOT CALCULATED"
    )

    print(
        "Prediction      : FORBIDDEN"
    )

    print(
        "Decision        : FORBIDDEN"
    )

    print("-" * 90)

    artifact = load_feature_contract()

    feature_identities = (
        load_feature_identities(
            artifact
        )
    )

    connection = connect_database()

    try:

        hunter_schema = (
            resolve_hunter_schema(
                connection
            )
        )

        hunter_rows = (
            load_all_hunter_rows(
                connection,
                hunter_schema,
            )
        )

    finally:

        connection.close()

    hunter_index = build_hunter_index(
        hunter_rows
    )

    forensic = run_forensic(
        feature_identities,
        hunter_rows,
        hunter_index,
    )

    forensic[
        "hunter_schema"
    ] = hunter_schema

    output = attach_hash(
        forensic
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    summary = output[
        "summary"
    ]

    print("=" * 90)
    print(
        "TIMESTAMP NORMALIZATION FORENSIC"
    )
    print("=" * 90)

    print(
        f"Feature identities       : "
        f"{summary['feature_identities']}"
    )

    print(
        f"Hunter rows total        : "
        f"{summary['hunter_rows_total']}"
    )

    print(
        f"Hunter symbols total     : "
        f"{summary['hunter_symbols_total']}"
    )

    print(
        f"Exact timestamp matches  : "
        f"{summary['exact_timestamp_matches']}"
    )

    print(
        f"Within 120s              : "
        f"{summary['within_120s']}"
    )

    print(
        f"Within 300s              : "
        f"{summary['within_300s']}"
    )

    print(
        f"Within 600s              : "
        f"{summary['within_600s']}"
    )

    print(
        f"Same symbol delta        : "
        f"{summary['same_symbol_timestamp_mismatch']}"
    )

    print(
        f"No symbol match          : "
        f"{summary['no_symbol_match']}"
    )

    print(
        f"Timestamp unavailable    : "
        f"{summary['timestamp_unavailable']}"
    )

    print(
        f"Minimum delta (sec)      : "
        f"{summary['minimum_delta_seconds']}"
    )

    print(
        f"Maximum delta (sec)      : "
        f"{summary['maximum_delta_seconds']}"
    )

    print(
        f"Mean delta (sec)         : "
        f"{summary['mean_delta_seconds']}"
    )

    print(
        f"Median delta (sec)       : "
        f"{summary['median_delta_seconds']}"
    )

    print("-" * 90)

    # Detailed identity table
    for item in output[
        "results"
    ]:

        print(
            f"SYMBOL : "
            f"{item['asset_symbol']}"
        )

        print(
            f"  FEATURE : "
            f"{item['feature_timestamp']}"
        )

        print(
            f"  NORMALIZED : "
            f"{item['normalized_symbol']}"
        )

        print(
            f"  HUNTER CANDIDATES : "
            f"{item['symbol_candidate_count']}"
        )

        print(
            f"  HUNTER ID : "
            f"{item['nearest_hunter_id']}"
        )

        print(
            f"  HUNTER SYMBOL : "
            f"{item['nearest_hunter_symbol']}"
        )

        print(
            f"  HUNTER TIMESTAMP : "
            f"{item['nearest_hunter_timestamp']}"
        )

        print(
            f"  DELTA SEC : "
            f"{item['delta_seconds']}"
        )

        print(
            f"  STATUS : "
            f"{item['identity_status']}"
        )

        print("-" * 90)

    print(
        f"Artifact : {OUTPUT_PATH}"
    )

    print(
        f"SHA256   : "
        f"{output['artifact_sha256']}"
    )

    print("=" * 90)

    print(
        f"FORENSIC STATUS : "
        f"{output['forensic_status']}"
    )

    print(
        "PREDICTIVE CLAIM : NOT ESTABLISHED"
    )

    print(
        "RELATIONSHIP CALCULATION : NOT PERFORMED"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()