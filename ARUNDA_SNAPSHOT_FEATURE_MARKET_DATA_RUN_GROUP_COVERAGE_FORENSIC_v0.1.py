import sqlite3
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

DB_PATH = BASE_DIR / "arunda.db"

FEATURE_CONTRACT_PATH = (
    BASE_DIR / "ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)

ARTIFACT_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_MARKET_DATA_RUN_GROUP_COVERAGE_FORENSIC_v0.1.json"
)

TABLE_NAME = "market_data"

MATCH_TOLERANCES = [0, 120, 300, 600]

READ_ONLY_URI = f"file:{DB_PATH.as_posix()}?mode=ro"


# ============================================================
# CONSTANTS
# ============================================================

EXPECTED_EXECUTION_COLUMNS = [
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


# ============================================================
# HELPERS
# ============================================================

def sha256_text(value):
    if value is None:
        value = ""
    value = str(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def fingerprint(value):
    return sha256_text(canonical_json(value))


def parse_timestamp(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()

        if not text:
            return None

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(text)
        except Exception:
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def timestamp_distance_seconds(a, b):
    da = parse_timestamp(a)
    db = parse_timestamp(b)

    if da is None or db is None:
        return None

    return abs((da - db).total_seconds())


def safe_unique(values):
    result = set()

    for value in values:
        if value is None:
            continue

        text = str(value).strip()

        if text:
            result.add(text)

    return sorted(result)


def print_header(title):
    print("=" * 90)
    print(title)
    print("=" * 90)


def print_separator():
    print("-" * 90)


# ============================================================
# DATABASE
# ============================================================

def open_read_only_database():
    conn = sqlite3.connect(READ_ONLY_URI, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table_name):
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    )

    row = cursor.fetchone()
    cursor.close()

    return row is not None


def get_table_columns(conn, table_name):
    cursor = conn.cursor()

    cursor.execute(
        f'PRAGMA table_info("{table_name}")'
    )

    rows = cursor.fetchall()
    cursor.close()

    return [row["name"] for row in rows]


# ============================================================
# FEATURE CONTRACT
# ============================================================

def load_feature_contract():
    if not FEATURE_CONTRACT_PATH.exists():
        return {}

    with FEATURE_CONTRACT_PATH.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def recursive_find_values(obj, target_keys):
    found = []

    if isinstance(obj, dict):
        for key, value in obj.items():

            if str(key).lower() in target_keys:
                if isinstance(value, list):
                    found.extend(value)
                else:
                    found.append(value)

            found.extend(
                recursive_find_values(
                    value,
                    target_keys,
                )
            )

    elif isinstance(obj, list):
        for item in obj:
            found.extend(
                recursive_find_values(
                    item,
                    target_keys,
                )
            )

    return found


# ============================================================
# FEATURE INPUT DISCOVERY
# ============================================================

def discover_feature_timestamps(contract):
    timestamp_keys = {
        "timestamp",
        "timestamps",
        "feature_timestamp",
        "feature_timestamps",
        "snapshot_timestamp",
        "snapshot_timestamps",
        "datetime",
        "datetimes",
        "time",
        "times",
    }

    values = recursive_find_values(
        contract,
        timestamp_keys,
    )

    timestamps = []

    for value in values:

        if isinstance(value, dict):
            continue

        if isinstance(value, list):
            for item in value:
                if parse_timestamp(item) is not None:
                    timestamps.append(str(item))
        else:
            if parse_timestamp(value) is not None:
                timestamps.append(str(value))

    return safe_unique(timestamps)


def discover_feature_symbols(contract):
    symbol_keys = {
        "symbol",
        "symbols",
        "asset",
        "assets",
        "ticker",
        "tickers",
        "market_symbol",
        "market_symbols",
        "feature_symbol",
        "feature_symbols",
        "snapshot_symbol",
        "snapshot_symbols",
    }

    values = recursive_find_values(
        contract,
        symbol_keys,
    )

    symbols = []

    for value in values:

        if isinstance(value, dict):
            continue

        if isinstance(value, list):
            for item in value:
                if item is not None:
                    text = str(item).strip().upper()

                    if text:
                        symbols.append(text)

        else:
            if value is not None:
                text = str(value).strip().upper()

                if text:
                    symbols.append(text)

    return safe_unique(symbols)


# ============================================================
# MARKET DATA
# ============================================================

def load_market_data(conn):
    if not table_exists(conn, TABLE_NAME):
        raise RuntimeError(
            f"Required table does not exist: {TABLE_NAME}"
        )

    columns = get_table_columns(
        conn,
        TABLE_NAME,
    )

    if "symbol" not in columns:
        raise RuntimeError(
            "market_data does not contain symbol column."
        )

    if "timestamp" not in columns:
        raise RuntimeError(
            "market_data does not contain timestamp column."
        )

    cursor = conn.cursor()

    cursor.execute(
        f'SELECT * FROM "{TABLE_NAME}"'
    )

    # IMPORTANT:
    # description belongs to cursor, NOT connection.
    cursor_columns = [
        description[0]
        for description in cursor.description
    ]

    rows = []

    for raw_row in cursor.fetchall():

        row = {
            column: raw_row[index]
            for index, column in enumerate(cursor_columns)
        }

        row["_parsed_timestamp"] = parse_timestamp(
            row.get("timestamp")
        )

        rows.append(row)

    cursor.close()

    return rows, cursor_columns


# ============================================================
# TEMPORAL INVENTORY
# ============================================================

def temporal_inventory(market_data):
    parseable = [
        row
        for row in market_data
        if row.get("_parsed_timestamp") is not None
    ]

    symbols = safe_unique(
        row.get("symbol")
        for row in parseable
    )

    return {
        "rows_loaded": len(market_data),
        "parseable_timestamps": len(parseable),
        "market_symbols": symbols,
        "market_symbol_count": len(symbols),
    }


# ============================================================
# FEATURE -> MARKET MATCHING
# ============================================================

def find_matches(
    market_data,
    feature_timestamps,
    feature_symbols,
    tolerance,
):
    matches = []

    timestamp_targets = [
        parse_timestamp(value)
        for value in feature_timestamps
    ]

    timestamp_targets = [
        value
        for value in timestamp_targets
        if value is not None
    ]

    feature_symbol_set = {
        str(symbol).strip().upper()
        for symbol in feature_symbols
        if symbol is not None
    }

    for row in market_data:

        row_timestamp = row.get("_parsed_timestamp")

        if row_timestamp is None:
            continue

        row_symbol = str(
            row.get("symbol", "")
        ).strip().upper()

        if (
            feature_symbol_set
            and row_symbol not in feature_symbol_set
        ):
            continue

        best_distance = None
        best_target = None

        for target in timestamp_targets:

            distance = abs(
                (
                    row_timestamp - target
                ).total_seconds()
            )

            if distance <= tolerance:

                if (
                    best_distance is None
                    or distance < best_distance
                ):
                    best_distance = distance
                    best_target = target

        if best_distance is not None:

            matches.append(
                {
                    "row": row,
                    "distance_seconds": best_distance,
                    "feature_timestamp": (
                        best_target.isoformat()
                        if best_target
                        else None
                    ),
                }
            )

    return matches


# ============================================================
# RUN GROUP IDENTITY
# ============================================================

def execution_identity(row):
    return (
        row.get("source"),
        row.get("engine_version"),
    )


def run_group_identity(row):
    return (
        row.get("source"),
        row.get("engine_version"),
        row.get("timestamp"),
        row.get("symbol"),
        row.get("timeframe"),
    )


def build_execution_group_records(rows):
    groups = {}

    for row in rows:

        key = execution_identity(row)

        groups.setdefault(
            key,
            [],
        ).append(row)

    records = []

    for key, group_rows in groups.items():

        source, engine_version = key

        symbols = safe_unique(
            row.get("symbol")
            for row in group_rows
        )

        timestamps = safe_unique(
            row.get("timestamp")
            for row in group_rows
        )

        timeframes = safe_unique(
            row.get("timeframe")
            for row in group_rows
        )

        run_keys = {
            run_group_identity(row)
            for row in group_rows
        }

        coherent = (
            len(timestamps) == 1
            and len(timeframes) == 1
        )

        record = {
            "execution_fingerprint": fingerprint(
                {
                    "source": source,
                    "engine_version": engine_version,
                }
            ),
            "row_count": len(group_rows),
            "symbol_count": len(symbols),
            "symbols": symbols,
            "timestamp_count": len(timestamps),
            "timestamps": timestamps,
            "timeframe_count": len(timeframes),
            "timeframes": timeframes,
            "run_key_count": len(run_keys),
            "source": source,
            "engine_version": engine_version,
            "group_coherent": coherent,
        }

        records.append(record)

    records.sort(
        key=lambda item: (
            str(item["source"]),
            str(item["engine_version"]),
        )
    )

    return records


# ============================================================
# COVERAGE MATRIX
# ============================================================

def build_symbol_coverage(
    feature_symbols,
    matched_rows,
):
    feature_symbol_set = set(
        str(symbol).upper()
        for symbol in feature_symbols
    )

    matched_by_symbol = {}

    for row in matched_rows:

        symbol = str(
            row.get("symbol", "")
        ).strip().upper()

        if symbol:
            matched_by_symbol.setdefault(
                symbol,
                [],
            ).append(row)

    records = []

    for symbol in sorted(feature_symbol_set):

        rows = matched_by_symbol.get(
            symbol,
            [],
        )

        execution_identities = {
            execution_identity(row)
            for row in rows
        }

        run_keys = {
            run_group_identity(row)
            for row in rows
        }

        records.append(
            {
                "symbol": symbol,
                "market_data_row_count": len(rows),
                "execution_identity_count": len(
                    execution_identities
                ),
                "run_key_count": len(run_keys),
                "covered": len(rows) > 0,
            }
        )

    return records


def build_group_coverage(
    execution_groups,
    feature_symbols,
):
    expected_symbols = {
        str(symbol).upper()
        for symbol in feature_symbols
    }

    records = []

    for group in execution_groups:

        actual_symbols = set(
            group["symbols"]
        )

        covered_symbols = (
            expected_symbols
            & actual_symbols
        )

        missing_symbols = (
            expected_symbols
            - actual_symbols
        )

        extra_symbols = (
            actual_symbols
            - expected_symbols
        )

        records.append(
            {
                "execution_fingerprint": group[
                    "execution_fingerprint"
                ],
                "source": group["source"],
                "engine_version": group[
                    "engine_version"
                ],
                "expected_symbol_count": len(
                    expected_symbols
                ),
                "covered_symbol_count": len(
                    covered_symbols
                ),
                "missing_symbol_count": len(
                    missing_symbols
                ),
                "missing_symbols": sorted(
                    missing_symbols
                ),
                "extra_symbol_count": len(
                    extra_symbols
                ),
                "extra_symbols": sorted(
                    extra_symbols
                ),
                "coverage_complete": (
                    expected_symbols
                    == actual_symbols
                ),
                "row_count": group[
                    "row_count"
                ],
            }
        )

    return records


# ============================================================
# MAIN
# ============================================================

def main():

    print_header(
        "ARUNDA SNAPSHOT FEATURE -> MARKET DATA RUN GROUP COVERAGE FORENSIC v0.1"
    )

    print(f"Database        : {DB_PATH}")
    print(
        f"Feature Contract: {FEATURE_CONTRACT_PATH}"
    )
    print("Mode            : READ ONLY")
    print("Network         : FORBIDDEN")
    print("Outcome         : NOT CALCULATED")
    print("Prediction      : FORBIDDEN")
    print("Decision        : FORBIDDEN")
    print(
        "Match Tolerance : 0 / 120 / 300 / 600 seconds"
    )

    print_separator()

    contract = load_feature_contract()

    feature_timestamps = (
        discover_feature_timestamps(contract)
    )

    feature_symbols = (
        discover_feature_symbols(contract)
    )

    print(
        f"Feature timestamp candidates : "
        f"{len(feature_timestamps)}"
    )

    print(
        f"Feature symbol candidates    : "
        f"{len(feature_symbols)}"
    )

    print(
        f"Feature symbols discovered   : "
        f"{len(feature_symbols)}"
    )

    print_header(
        "FEATURE TIMESTAMP INPUT"
    )

    print(
        f"Unique timestamps : "
        f"{len(feature_timestamps)}"
    )

    for timestamp in feature_timestamps:
        print(f"  {timestamp}")

    print(
        f"Symbols discovered : "
        f"{len(feature_symbols)}"
    )

    for symbol in feature_symbols:
        print(f"  {symbol}")

    conn = open_read_only_database()

    try:

        market_data, columns = load_market_data(
            conn
        )

        print_header(
            "MARKET DATA SCHEMA"
        )

        print(
            "Symbol column    : symbol"
        )

        print(
            "Timestamp column : timestamp"
        )

        print_header(
            "EXECUTION IDENTITY COLUMNS"
        )

        for column in EXPECTED_EXECUTION_COLUMNS:
            print(f"  {column}")

        print_header(
            "RUN GROUP CANDIDATE COLUMNS"
        )

        for column in RUN_GROUP_COLUMNS:
            print(f"  {column}")

        inventory = temporal_inventory(
            market_data
        )

        print_header(
            "MARKET DATA TEMPORAL INVENTORY"
        )

        print(
            f"Market_data rows loaded : "
            f"{inventory['rows_loaded']}"
        )

        print(
            f"Parseable timestamps    : "
            f"{inventory['parseable_timestamps']}"
        )

        print(
            f"Market symbols          : "
            f"{inventory['market_symbol_count']}"
        )

        print_header(
            "FEATURE TIMESTAMP TEMPORAL COVERAGE"
        )

        coverage_by_tolerance = {}

        for tolerance in MATCH_TOLERANCES:

            matches = find_matches(
                market_data,
                feature_timestamps,
                feature_symbols,
                tolerance,
            )

            coverage_by_tolerance[
                tolerance
            ] = matches

            unique_symbols = safe_unique(
                item["row"].get("symbol")
                for item in matches
            )

            print(
                f"Within {tolerance:4d}s : "
                f"{len(matches)}"
            )

        exact_matches = coverage_by_tolerance[0]

        exact_rows = [
            item["row"]
            for item in exact_matches
        ]

        exact_symbols = safe_unique(
            row.get("symbol")
            for row in exact_rows
        )

        print(
            f"Exact timestamp matches : "
            f"{len(exact_matches)}"
        )

        print(
            f"Exact-match symbols      : "
            f"{len(exact_symbols)}"
        )

        print_header(
            "RUN GROUP COVERAGE FORENSIC SUMMARY"
        )

        unique_exact_fingerprints = {
            fingerprint(
                {
                    key: row.get(key)
                    for key in columns
                }
            )
            for row in exact_rows
        }

        execution_groups = (
            build_execution_group_records(
                exact_rows
            )
        )

        print(
            f"Exact market_data rows : "
            f"{len(exact_rows)}"
        )

        print(
            f"Unique exact row fingerprints : "
            f"{len(unique_exact_fingerprints)}"
        )

        print(
            "Execution identity columns : "
            "source, engine_version"
        )

        print(
            f"Distinct execution groups : "
            f"{len(execution_groups)}"
        )

        print(
            "Run-key columns : "
            "source, engine_version, timestamp, symbol, timeframe"
        )

        distinct_run_keys = {
            run_group_identity(row)
            for row in exact_rows
        }

        print(
            f"Distinct run-key groups : "
            f"{len(distinct_run_keys)}"
        )

        cross_symbol_groups = [
            group
            for group in execution_groups
            if group["symbol_count"] > 1
        ]

        print(
            f"Cross-symbol execution groups : "
            f"{len(cross_symbol_groups)}"
        )

        print_header(
            "EXECUTION GROUP COVERAGE"
        )

        group_coverage = build_group_coverage(
            execution_groups,
            feature_symbols,
        )

        for record in group_coverage:

            print(
                f"EXECUTION FINGERPRINT : "
                f"{record['execution_fingerprint']}"
            )

            print(
                f"SOURCE : "
                f"{record['source']}"
            )

            print(
                f"ENGINE VERSION : "
                f"{record['engine_version']}"
            )

            print(
                f"EXPECTED SYMBOLS : "
                f"{record['expected_symbol_count']}"
            )

            print(
                f"COVERED SYMBOLS : "
                f"{record['covered_symbol_count']}"
            )

            print(
                f"MISSING SYMBOLS : "
                f"{record['missing_symbol_count']}"
            )

            if record["missing_symbols"]:
                print(
                    "  "
                    + ", ".join(
                        record["missing_symbols"]
                    )
                )

            print(
                f"EXTRA SYMBOLS : "
                f"{record['extra_symbol_count']}"
            )

            if record["extra_symbols"]:
                print(
                    "  "
                    + ", ".join(
                        record["extra_symbols"]
                    )
                )

            print(
                f"ROW COUNT : "
                f"{record['row_count']}"
            )

            print(
                f"COVERAGE COMPLETE : "
                f"{record['coverage_complete']}"
            )

            print_separator()

        print_header(
            "PER-SYMBOL RUN GROUP COVERAGE"
        )

        symbol_coverage = build_symbol_coverage(
            feature_symbols,
            exact_rows,
        )

        for record in symbol_coverage:

            print(
                f"SYMBOL : "
                f"{record['symbol']}"
            )

            print(
                f"MARKET DATA ROW COUNT : "
                f"{record['market_data_row_count']}"
            )

            print(
                f"DISTINCT RUN GROUPS : "
                f"{record['execution_identity_count']}"
            )

            print(
                f"DISTINCT RUN KEYS : "
                f"{record['run_key_count']}"
            )

            print(
                f"COVERED : "
                f"{record['covered']}"
            )

            print_separator()

        complete_groups = [
            record
            for record in group_coverage
            if record["coverage_complete"]
        ]

        incomplete_groups = [
            record
            for record in group_coverage
            if not record["coverage_complete"]
        ]

        covered_symbols = [
            record
            for record in symbol_coverage
            if record["covered"]
        ]

        uncovered_symbols = [
            record
            for record in symbol_coverage
            if not record["covered"]
        ]

        coverage_summary = {
            "expected_feature_symbol_count": len(
                feature_symbols
            ),
            "covered_feature_symbol_count": len(
                covered_symbols
            ),
            "uncovered_feature_symbol_count": len(
                uncovered_symbols
            ),
            "complete_execution_group_count": len(
                complete_groups
            ),
            "incomplete_execution_group_count": len(
                incomplete_groups
            ),
            "exact_market_data_row_count": len(
                exact_rows
            ),
            "distinct_execution_group_count": len(
                execution_groups
            ),
        }

        forensic_status = (
            "MARKET_DATA_RUN_GROUP_COVERAGE_ESTABLISHED"
        )

        if incomplete_groups or uncovered_symbols:
            forensic_status = (
                "MARKET_DATA_RUN_GROUP_COVERAGE_PARTIAL"
            )

        print_header(
            "FORENSIC STATUS"
        )

        print(
            f"FORENSIC STATUS : "
            f"{forensic_status}"
        )

        print(
            "PREDICTIVE CLAIM : NOT ESTABLISHED"
        )

        print(
            "RELATIONSHIP CALCULATION : NOT PERFORMED"
        )

        print(
            f"Complete execution groups : "
            f"{len(complete_groups)}"
        )

        print(
            f"Incomplete execution groups : "
            f"{len(incomplete_groups)}"
        )

        print(
            f"Covered feature symbols : "
            f"{len(covered_symbols)}"
        )

        print(
            f"Uncovered feature symbols : "
            f"{len(uncovered_symbols)}"
        )

        artifact = {
            "artifact": (
                "ARUNDA_SNAPSHOT_FEATURE_MARKET_DATA_"
                "RUN_GROUP_COVERAGE_FORENSIC_v0.1"
            ),
            "version": "v0.1",
            "mode": "READ ONLY",
            "network": "FORBIDDEN",
            "outcome": "NOT CALCULATED",
            "prediction": "FORBIDDEN",
            "decision": "FORBIDDEN",
            "database": str(DB_PATH),
            "feature_contract": str(
                FEATURE_CONTRACT_PATH
            ),
            "table": TABLE_NAME,
            "match_tolerances_seconds": (
                MATCH_TOLERANCES
            ),
            "feature_input": {
                "timestamps": feature_timestamps,
                "symbols": feature_symbols,
            },
            "market_data_inventory": inventory,
            "temporal_coverage": {
                str(tolerance): {
                    "row_count": len(
                        coverage_by_tolerance[
                            tolerance
                        ]
                    ),
                    "symbol_count": len(
                        safe_unique(
                            item["row"].get("symbol")
                            for item in coverage_by_tolerance[
                                tolerance
                            ]
                        )
                    ),
                }
                for tolerance in MATCH_TOLERANCES
            },
            "exact_match": {
                "row_count": len(exact_rows),
                "symbol_count": len(exact_symbols),
                "symbols": exact_symbols,
                "unique_row_fingerprint_count": len(
                    unique_exact_fingerprints
                ),
            },
            "execution_groups": execution_groups,
            "group_coverage": group_coverage,
            "symbol_coverage": symbol_coverage,
            "coverage_summary": coverage_summary,
            "forensic_status": forensic_status,
            "predictive_claim": "NOT ESTABLISHED",
            "relationship_calculation": (
                "NOT PERFORMED"
            ),
        }

        artifact_text = canonical_json(
            artifact
        )

        artifact["artifact_sha256"] = (
            sha256_text(artifact_text)
        )

        with ARTIFACT_PATH.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                artifact,
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(
            f"Artifact : {ARTIFACT_PATH}"
        )

        print(
            f"SHA256   : "
            f"{artifact['artifact_sha256']}"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()