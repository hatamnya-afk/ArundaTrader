import os
import json
import sqlite3
import hashlib
from datetime import datetime, timezone


# =============================================================================
# ARUNDA SNAPSHOT FEATURE -> MARKET DATA RUN GROUP COVERAGE REPAIR FORENSIC v0.1
# =============================================================================

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"

DB_PATH = os.path.join(
    BASE_DIR,
    "arunda.db"
)

FEATURE_CONTRACT_PATH = os.path.join(
    BASE_DIR,
    "ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)

SOURCE_SYMBOL_FORENSIC_PATH = os.path.join(
    BASE_DIR,
    "ARUNDA_SNAPSHOT_FEATURE_SOURCE_SYMBOL_INPUT_FORENSIC_v0.1.json"
)

ARTIFACT_PATH = os.path.join(
    BASE_DIR,
    "ARUNDA_SNAPSHOT_FEATURE_MARKET_DATA_RUN_GROUP_COVERAGE_REPAIR_FORENSIC_v0.1.json"
)

MATCH_TOLERANCES = [0, 120, 300, 600]

EXPECTED_TIMEFRAME = "SNAPSHOT"

SYMBOL_COLUMN = "symbol"
TIMESTAMP_COLUMN = "timestamp"

EXECUTION_COLUMNS = [
    "source",
    "engine_version",
]

RUN_GROUP_COLUMNS = [
    "source",
    "engine_version",
    "timestamp",
    "symbol",
    "timeframe",
]


# =============================================================================
# HELPERS
# =============================================================================

def sha256_text(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def print_header(title):
    print("=" * 90)
    print(title)
    print("=" * 90)


def normalize_symbol(value):
    if value is None:
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    return value


def normalize_text(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def parse_timestamp(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    text = str(value).strip()

    if not text:
        return None

    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except Exception:
        return None


def timestamp_to_iso(value):
    dt = parse_timestamp(value)

    if dt is None:
        return None

    return dt.isoformat()


def seconds_difference(a, b):
    dt_a = parse_timestamp(a)
    dt_b = parse_timestamp(b)

    if dt_a is None or dt_b is None:
        return None

    return abs(
        (dt_a - dt_b).total_seconds()
    )


def unique_sorted(values):
    return sorted(
        {
            value
            for value in values
            if value is not None
        }
    )


# =============================================================================
# JSON LOADING
# =============================================================================

def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8"
    ) as handle:
        return json.load(handle)


# =============================================================================
# FEATURE CONTRACT
# =============================================================================

def load_feature_contract(path):
    if not os.path.exists(path):
        return {}

    try:
        return load_json(path)

    except Exception as exc:
        print(
            f"WARNING: Feature contract could not be loaded: {exc}"
        )

        return {}


# =============================================================================
# EXPECTED UNIVERSE EXTRACTION
# =============================================================================

def collect_symbol_lists(node, results=None, path="root"):
    if results is None:
        results = []

    if isinstance(node, dict):

        for key, value in node.items():

            key_text = str(key).lower()

            if isinstance(value, list):

                normalized = []

                for item in value:
                    if isinstance(item, str):
                        symbol = normalize_symbol(item)

                        if symbol:
                            normalized.append(symbol)

                if normalized:
                    results.append(
                        {
                            "path": f"{path}.{key}",
                            "key": key,
                            "symbols": unique_sorted(normalized),
                        }
                    )

            collect_symbol_lists(
                value,
                results,
                f"{path}.{key}"
            )

    elif isinstance(node, list):

        for index, value in enumerate(node):

            collect_symbol_lists(
                value,
                results,
                f"{path}[{index}]"
            )

    return results


def extract_expected_symbols_from_source_artifact(data):
    preferred_keys = {
        "feature_symbols_established",
        "established_feature_symbols",
        "feature_symbols",
        "symbols_established",
        "established_symbols",
        "expected_symbols",
        "expected_universe",
        "source_symbols",
    }

    candidates = collect_symbol_lists(data)

    preferred = []

    for item in candidates:

        key_lower = str(
            item["key"]
        ).lower()

        if key_lower in preferred_keys:

            preferred.append(item)

    if preferred:

        preferred.sort(
            key=lambda item: (
                -len(item["symbols"]),
                item["path"],
            )
        )

        return (
            preferred[0]["symbols"],
            preferred[0]["path"],
        )

    return [], None


def extract_expected_symbols_from_contract(data):
    preferred_keys = {
        "symbols",
        "expected_symbols",
        "feature_symbols",
        "universe",
        "expected_universe",
        "assets",
    }

    candidates = collect_symbol_lists(data)

    preferred = []

    for item in candidates:

        key_lower = str(
            item["key"]
        ).lower()

        if key_lower in preferred_keys:

            preferred.append(item)

    if preferred:

        preferred.sort(
            key=lambda item: (
                -len(item["symbols"]),
                item["path"],
            )
        )

        return (
            preferred[0]["symbols"],
            preferred[0]["path"],
        )

    return [], None


def resolve_expected_universe(
    source_artifact,
    feature_contract,
):
    source_symbols = []
    source_path = None

    if source_artifact:
        (
            source_symbols,
            source_path,
        ) = extract_expected_symbols_from_source_artifact(
            source_artifact
        )

    if source_symbols:
        return {
            "symbols": unique_sorted(source_symbols),
            "source": "FEATURE_SOURCE_FORENSIC",
            "source_path": source_path,
        }

    contract_symbols = []
    contract_path = None

    if feature_contract:
        (
            contract_symbols,
            contract_path,
        ) = extract_expected_symbols_from_contract(
            feature_contract
        )

    if contract_symbols:
        return {
            "symbols": unique_sorted(contract_symbols),
            "source": "FEATURE_CONTRACT",
            "source_path": contract_path,
        }

    return {
        "symbols": [],
        "source": "UNRESOLVED",
        "source_path": None,
    }


# =============================================================================
# SQLITE SCHEMA
# =============================================================================

def get_table_columns(conn, table_name):
    cursor = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    )

    rows = cursor.fetchall()

    return [
        row[1]
        for row in rows
    ]


def resolve_market_data_columns(conn):
    columns = get_table_columns(
        conn,
        "market_data"
    )

    lower_map = {
        column.lower(): column
        for column in columns
    }

    symbol_column = lower_map.get(
        "symbol"
    )

    timestamp_column = lower_map.get(
        "timestamp"
    )

    if symbol_column is None:
        raise RuntimeError(
            "market_data symbol column not found"
        )

    if timestamp_column is None:
        raise RuntimeError(
            "market_data timestamp column not found"
        )

    return {
        "symbol": symbol_column,
        "timestamp": timestamp_column,
        "all_columns": columns,
    }


# =============================================================================
# MARKET DATA LOADING
# =============================================================================

def load_market_data(
    conn,
    symbol_column,
    timestamp_column,
):
    query = (
        f'SELECT * FROM "market_data"'
    )

    cursor = conn.execute(query)

    column_names = [
        description[0]
        for description in cursor.description
    ]

    rows = cursor.fetchall()

    result = []

    for row in rows:

        record = dict(
            zip(
                column_names,
                row,
            )
        )

        symbol = normalize_symbol(
            record.get(symbol_column)
        )

        timestamp = record.get(
            timestamp_column
        )

        parsed_timestamp = parse_timestamp(
            timestamp
        )

        record["_symbol"] = symbol
        record["_timestamp_raw"] = timestamp
        record["_timestamp"] = parsed_timestamp

        result.append(record)

    return result


# =============================================================================
# FEATURE TIMESTAMP
# =============================================================================

def discover_feature_timestamp(
    feature_contract,
    market_data,
):
    timestamps = []

    candidates = [
        "timestamp",
        "feature_timestamp",
        "snapshot_timestamp",
        "created_at",
        "generated_at",
    ]

    def recursive_search(node):

        if isinstance(node, dict):

            for key, value in node.items():

                key_lower = str(key).lower()

                if key_lower in candidates:

                    parsed = parse_timestamp(value)

                    if parsed is not None:
                        timestamps.append(
                            parsed
                        )

                recursive_search(value)

        elif isinstance(node, list):

            for value in node:
                recursive_search(value)

    recursive_search(
        feature_contract
    )

    if timestamps:

        unique = sorted(
            {
                dt.isoformat()
                for dt in timestamps
            }
        )

        return [
            parse_timestamp(value)
            for value in unique
        ]

    market_timestamps = [
        row["_timestamp"]
        for row in market_data
        if row["_timestamp"] is not None
    ]

    if market_timestamps:

        latest = max(
            market_timestamps
        )

        return [latest]

    return []


# =============================================================================
# TEMPORAL MATCHING
# =============================================================================

def exact_or_tolerant_matches(
    market_data,
    feature_timestamps,
    tolerance_seconds,
):
    matched = []

    for row in market_data:

        row_timestamp = row["_timestamp"]

        if row_timestamp is None:
            continue

        for feature_timestamp in feature_timestamps:

            distance = abs(
                (
                    row_timestamp
                    - feature_timestamp
                ).total_seconds()
            )

            if distance <= tolerance_seconds:

                copied = dict(row)

                copied["_feature_timestamp"] = (
                    feature_timestamp
                )

                copied["_distance_seconds"] = (
                    distance
                )

                matched.append(
                    copied
                )

                break

    return matched


# =============================================================================
# GROUP FINGERPRINT
# =============================================================================

def execution_fingerprint(
    source,
    engine_version,
):
    value = (
        f"source={normalize_text(source)}|"
        f"engine_version={normalize_text(engine_version)}"
    )

    return sha256_text(
        value
    )


def run_group_fingerprint(
    source,
    engine_version,
    timestamp,
    symbol,
    timeframe,
):
    value = (
        f"source={normalize_text(source)}|"
        f"engine_version={normalize_text(engine_version)}|"
        f"timestamp={timestamp_to_iso(timestamp)}|"
        f"symbol={normalize_symbol(symbol)}|"
        f"timeframe={normalize_text(timeframe)}"
    )

    return sha256_text(
        value
    )


# =============================================================================
# GROUPING
# =============================================================================

def build_execution_groups(rows):
    groups = {}

    for row in rows:

        source = normalize_text(
            row.get("source")
        )

        engine_version = normalize_text(
            row.get("engine_version")
        )

        fingerprint = execution_fingerprint(
            source,
            engine_version,
        )

        if fingerprint not in groups:

            groups[fingerprint] = {
                "execution_fingerprint": fingerprint,
                "source": source,
                "engine_version": engine_version,
                "rows": [],
            }

        groups[fingerprint]["rows"].append(
            row
        )

    return groups


def build_execution_group_record(
    fingerprint,
    group,
    expected_symbols,
):
    rows = group["rows"]

    symbols = unique_sorted(
        row["_symbol"]
        for row in rows
    )

    timestamps = unique_sorted(
        timestamp_to_iso(
            row["_timestamp"]
        )
        for row in rows
    )

    timeframes = unique_sorted(
        normalize_text(
            row.get("timeframe")
        )
        for row in rows
    )

    missing_symbols = sorted(
        set(expected_symbols)
        - set(symbols)
    )

    extra_symbols = sorted(
        set(symbols)
        - set(expected_symbols)
    )

    coverage_complete = (
        len(expected_symbols) > 0
        and len(missing_symbols) == 0
        and len(extra_symbols) == 0
        and len(symbols) == len(expected_symbols)
    )

    return {
        "execution_fingerprint": fingerprint,
        "source": group["source"],
        "engine_version": group["engine_version"],
        "expected_symbol_count": len(
            expected_symbols
        ),
        "covered_symbol_count": len(
            symbols
        ),
        "expected_symbols": expected_symbols,
        "covered_symbols": symbols,
        "missing_symbols": missing_symbols,
        "extra_symbols": extra_symbols,
        "row_count": len(rows),
        "timestamp_count": len(timestamps),
        "timestamps": timestamps,
        "timeframe_count": len(timeframes),
        "timeframes": timeframes,
        "coverage_complete": coverage_complete,
        "repair_required": not coverage_complete,
    }


# =============================================================================
# PER SYMBOL COVERAGE
# =============================================================================

def build_per_symbol_coverage(
    groups,
    expected_symbols,
):
    result = []

    for symbol in expected_symbols:

        executions = []

        for fingerprint, group in groups.items():

            matching_rows = [
                row
                for row in group["rows"]
                if row["_symbol"] == symbol
            ]

            if matching_rows:

                executions.append(
                    {
                        "execution_fingerprint": fingerprint,
                        "source": group["source"],
                        "engine_version": group["engine_version"],
                        "row_count": len(
                            matching_rows
                        ),
                    }
                )

        result.append(
            {
                "symbol": symbol,
                "expected": True,
                "execution_group_count": len(
                    executions
                ),
                "execution_groups": executions,
            }
        )

    return result


# =============================================================================
# CROSS GROUP COVERAGE
# =============================================================================

def build_cross_group_coverage(
    group_records,
    expected_symbols,
):
    result = []

    for record in group_records:

        result.append(
            {
                "execution_fingerprint": record[
                    "execution_fingerprint"
                ],
                "source": record["source"],
                "engine_version": record[
                    "engine_version"
                ],
                "expected_symbols": expected_symbols,
                "covered_symbols": record[
                    "covered_symbols"
                ],
                "missing_symbols": record[
                    "missing_symbols"
                ],
                "extra_symbols": record[
                    "extra_symbols"
                ],
                "coverage_complete": record[
                    "coverage_complete"
                ],
            }
        )

    return result


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header(
        "ARUNDA SNAPSHOT FEATURE -> MARKET DATA RUN GROUP COVERAGE REPAIR FORENSIC v0.1"
    )

    print(
        f"Database        : {DB_PATH}"
    )

    print(
        f"Feature Contract: {FEATURE_CONTRACT_PATH}"
    )

    print(
        f"Source Forensic : {SOURCE_SYMBOL_FORENSIC_PATH}"
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

    print(
        "Repair          : FORENSIC ONLY / NO DATABASE WRITE"
    )

    print(
        "Match Tolerance : 0 / 120 / 300 / 600 seconds"
    )

    print("-" * 90)

    feature_contract = load_feature_contract(
        FEATURE_CONTRACT_PATH
    )

    source_artifact = {}

    if os.path.exists(
        SOURCE_SYMBOL_FORENSIC_PATH
    ):
        try:
            source_artifact = load_json(
                SOURCE_SYMBOL_FORENSIC_PATH
            )

        except Exception as exc:
            print(
                f"WARNING: Source forensic artifact load failed: {exc}"
            )

    universe = resolve_expected_universe(
        source_artifact,
        feature_contract,
    )

    expected_symbols = universe[
        "symbols"
    ]

    print(
        f"Expected Universe source : {universe['source']}"
    )

    print(
        f"Expected Universe path   : {universe['source_path']}"
    )

    print(
        f"Expected symbols         : {len(expected_symbols)}"
    )

    if expected_symbols:

        print(
            "  "
            + ", ".join(
                expected_symbols
            )
        )

    else:

        print(
            "WARNING: Expected Universe could not be resolved."
        )

    print("=" * 90)
    print(
        "FEATURE TIMESTAMP INPUT"
    )
    print("=" * 90)

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        columns = resolve_market_data_columns(
            conn
        )

        print("=" * 90)
        print(
            "MARKET DATA SCHEMA"
        )
        print("=" * 90)

        print(
            f"Symbol column    : {columns['symbol']}"
        )

        print(
            f"Timestamp column : {columns['timestamp']}"
        )

        print("=" * 90)
        print(
            "EXECUTION IDENTITY COLUMNS"
        )
        print("=" * 90)

        for column in EXECUTION_COLUMNS:
            print(
                f"  {column}"
            )

        print("=" * 90)
        print(
            "RUN GROUP CANDIDATE COLUMNS"
        )
        print("=" * 90)

        for column in RUN_GROUP_COLUMNS:
            print(
                f"  {column}"
            )

        market_data = load_market_data(
            conn,
            columns["symbol"],
            columns["timestamp"],
        )

    finally:

        conn.close()

    feature_timestamps = discover_feature_timestamp(
        feature_contract,
        market_data,
    )

    print(
        f"Unique timestamps : {len(feature_timestamps)}"
    )

    for timestamp in feature_timestamps:

        print(
            f"  {timestamp.isoformat()}"
        )

    print(
        f"Symbols discovered : {len(expected_symbols)}"
    )

    for symbol in expected_symbols:

        print(
            f"  {symbol}"
        )

    print("=" * 90)
    print(
        "MARKET DATA TEMPORAL INVENTORY"
    )
    print("=" * 90)

    parseable_count = sum(
        1
        for row in market_data
        if row["_timestamp"] is not None
    )

    market_symbols = unique_sorted(
        row["_symbol"]
        for row in market_data
        if row["_symbol"] is not None
    )

    print(
        f"Market_data rows loaded : {len(market_data)}"
    )

    print(
        f"Parseable timestamps    : {parseable_count}"
    )

    print(
        f"Market symbols          : {len(market_symbols)}"
    )

    print("=" * 90)
    print(
        "FEATURE TIMESTAMP TEMPORAL COVERAGE"
    )
    print("=" * 90)

    temporal_counts = {}

    for tolerance in MATCH_TOLERANCES:

        matches = exact_or_tolerant_matches(
            market_data,
            feature_timestamps,
            tolerance,
        )

        temporal_counts[
            str(tolerance)
        ] = len(matches)

        print(
            f"Within {tolerance:4d}s : {len(matches)}"
        )

    exact_matches = exact_or_tolerant_matches(
        market_data,
        feature_timestamps,
        0,
    )

    exact_symbols = unique_sorted(
        row["_symbol"]
        for row in exact_matches
        if row["_symbol"] is not None
    )

    print(
        f"Exact timestamp matches : {len(exact_matches)}"
    )

    print(
        f"Exact-match symbols      : {len(exact_symbols)}"
    )

    print("=" * 90)
    print(
        "RUN GROUP COVERAGE REPAIR FORENSIC SUMMARY"
    )
    print("=" * 90)

    print(
        f"Exact market_data rows : {len(exact_matches)}"
    )

    exact_row_fingerprints = set()

    for row in exact_matches:

        value = json.dumps(
            {
                key: row.get(key)
                for key in sorted(row.keys())
                if not key.startswith("_")
            },
            sort_keys=True,
            default=str,
        )

        exact_row_fingerprints.add(
            sha256_text(value)
        )

    print(
        f"Unique exact row fingerprints : {len(exact_row_fingerprints)}"
    )

    groups = build_execution_groups(
        exact_matches
    )

    print(
        f"Execution identity columns : {', '.join(EXECUTION_COLUMNS)}"
    )

    print(
        f"Distinct execution groups : {len(groups)}"
    )

    print(
        f"Run-key columns : {', '.join(RUN_GROUP_COLUMNS)}"
    )

    print(
        f"Cross-symbol execution groups : {len(groups)}"
    )

    group_records = []

    print("=" * 90)
    print(
        "EXECUTION GROUP COVERAGE REPAIR"
    )
    print("=" * 90)

    for fingerprint in sorted(
        groups.keys()
    ):

        record = build_execution_group_record(
            fingerprint,
            groups[fingerprint],
            expected_symbols,
        )

        group_records.append(
            record
        )

        print(
            f"EXECUTION FINGERPRINT : {record['execution_fingerprint']}"
        )

        print(
            f"SOURCE : {record['source']}"
        )

        print(
            f"ENGINE VERSION : {record['engine_version']}"
        )

        print(
            f"EXPECTED SYMBOLS : {record['expected_symbol_count']}"
        )

        print(
            f"COVERED SYMBOLS : {record['covered_symbol_count']}"
        )

        print(
            f"MISSING SYMBOLS : {len(record['missing_symbols'])}"
        )

        if record["missing_symbols"]:

            print(
                "  "
                + ", ".join(
                    record["missing_symbols"]
                )
            )

        print(
            f"EXTRA SYMBOLS : {len(record['extra_symbols'])}"
        )

        if record["extra_symbols"]:

            print(
                "  "
                + ", ".join(
                    record["extra_symbols"]
                )
            )

        print(
            f"ROW COUNT : {record['row_count']}"
        )

        print(
            f"TIMESTAMP COUNT : {record['timestamp_count']}"
        )

        print(
            f"TIMEFRAME COUNT : {record['timeframe_count']}"
        )

        print(
            f"COVERAGE COMPLETE : {record['coverage_complete']}"
        )

        print(
            f"REPAIR REQUIRED : {record['repair_required']}"
        )

        print("-" * 90)

    print("=" * 90)
    print(
        "PER-SYMBOL RUN GROUP COVERAGE REPAIR"
    )
    print("=" * 90)

    per_symbol = build_per_symbol_coverage(
        groups,
        expected_symbols,
    )

    for record in per_symbol:

        print(
            f"SYMBOL : {record['symbol']}"
        )

        print(
            f"EXECUTION GROUP COUNT : {record['execution_group_count']}"
        )

        for execution in record[
            "execution_groups"
        ]:

            print(
                "  "
                f"{execution['source']} | "
                f"{execution['engine_version']} | "
                f"ROWS={execution['row_count']}"
            )

        print("-" * 90)

    complete_groups = sum(
        1
        for record in group_records
        if record["coverage_complete"]
    )

    incomplete_groups = (
        len(group_records)
        - complete_groups
    )

    covered_symbols = unique_sorted(
        symbol
        for record in group_records
        for symbol in record[
            "covered_symbols"
        ]
    )

    uncovered_symbols = sorted(
        set(expected_symbols)
        - set(covered_symbols)
    )

    cross_group_coverage = build_cross_group_coverage(
        group_records,
        expected_symbols,
    )

    if (
        expected_symbols
        and complete_groups == len(group_records)
        and not uncovered_symbols
    ):

        forensic_status = (
            "MARKET_DATA_RUN_GROUP_COVERAGE_REPAIR_ESTABLISHED"
        )

    elif expected_symbols:

        forensic_status = (
            "MARKET_DATA_RUN_GROUP_COVERAGE_REPAIR_PARTIAL"
        )

    else:

        forensic_status = (
            "MARKET_DATA_RUN_GROUP_COVERAGE_REPAIR_BLOCKED"
        )

    print("=" * 90)
    print(
        "FORENSIC STATUS"
    )
    print("=" * 90)

    print(
        f"FORENSIC STATUS : {forensic_status}"
    )

    print(
        "PREDICTIVE CLAIM : NOT ESTABLISHED"
    )

    print(
        "RELATIONSHIP CALCULATION : NOT PERFORMED"
    )

    print(
        "DATABASE REPAIR : NOT PERFORMED"
    )

    print(
        f"Expected Universe : {len(expected_symbols)}"
    )

    print(
        f"Complete execution groups : {complete_groups}"
    )

    print(
        f"Incomplete execution groups : {incomplete_groups}"
    )

    print(
        f"Covered feature symbols : {len(covered_symbols)}"
    )

    print(
        f"Uncovered feature symbols : {len(uncovered_symbols)}"
    )

    if uncovered_symbols:

        print(
            "  "
            + ", ".join(
                uncovered_symbols
            )
        )

    # =========================================================================
    # ARTIFACT
    # =========================================================================

    artifact = {
        "artifact": {
            "name": (
                "ARUNDA_SNAPSHOT_FEATURE_MARKET_DATA_RUN_GROUP_"
                "COVERAGE_REPAIR_FORENSIC_v0.1"
            ),
            "version": "v0.1",
            "generated_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
        },

        "mode": "READ ONLY",

        "network": "FORBIDDEN",

        "database": DB_PATH,

        "feature_contract": FEATURE_CONTRACT_PATH,

        "source_symbol_forensic": (
            SOURCE_SYMBOL_FORENSIC_PATH
        ),

        "constraints": {
            "outcome": "NOT CALCULATED",
            "prediction": "FORBIDDEN",
            "decision": "FORBIDDEN",
            "database_write": "FORBIDDEN",
            "synthetic_data": "FORBIDDEN",
            "interpolation": "FORBIDDEN",
            "forward_fill": "FORBIDDEN",
            "back_fill": "FORBIDDEN",
        },

        "expected_universe": {
            "source": universe["source"],
            "source_path": universe[
                "source_path"
            ],
            "count": len(expected_symbols),
            "symbols": expected_symbols,
        },

        "feature_timestamp_input": {
            "count": len(feature_timestamps),
            "timestamps": [
                timestamp.isoformat()
                for timestamp in feature_timestamps
            ],
        },

        "market_data_inventory": {
            "rows_loaded": len(market_data),
            "parseable_timestamps": parseable_count,
            "market_symbol_count": len(
                market_symbols
            ),
            "market_symbols": market_symbols,
        },

        "temporal_coverage": {
            "counts": temporal_counts,
            "exact_matches": len(
                exact_matches
            ),
            "exact_symbols": exact_symbols,
            "exact_symbol_count": len(
                exact_symbols
            ),
        },

        "execution_groups": {
            "count": len(group_records),
            "complete_count": complete_groups,
            "incomplete_count": incomplete_groups,
            "records": group_records,
        },

        "cross_symbol_coverage": {
            "group_count": len(
                cross_group_coverage
            ),
            "records": cross_group_coverage,
        },

        "per_symbol_coverage": per_symbol,

        "repair_reconciliation": {
            "repair_is_forensic_only": True,
            "database_modified": False,
            "expected_universe_count": len(
                expected_symbols
            ),
            "covered_symbol_count": len(
                covered_symbols
            ),
            "uncovered_symbol_count": len(
                uncovered_symbols
            ),
            "uncovered_symbols": uncovered_symbols,
            "complete_execution_groups": complete_groups,
            "incomplete_execution_groups": incomplete_groups,
        },

        "forensic_status": forensic_status,

        "predictive_claim": "NOT ESTABLISHED",

        "relationship_calculation": "NOT PERFORMED",
    }

    artifact_text = json.dumps(
        artifact,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )

    with open(
        ARTIFACT_PATH,
        "w",
        encoding="utf-8",
    ) as handle:

        handle.write(
            artifact_text
        )

    artifact_sha256 = sha256_file(
        ARTIFACT_PATH
    )

    print(
        f"Artifact : {ARTIFACT_PATH}"
    )

    print(
        f"SHA256   : {artifact_sha256}"
    )


if __name__ == "__main__":
    main()