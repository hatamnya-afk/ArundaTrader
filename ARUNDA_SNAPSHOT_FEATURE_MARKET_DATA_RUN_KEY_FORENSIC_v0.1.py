import sqlite3
import json
import hashlib
import os
from datetime import datetime, timezone


DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"
CONTRACT_PATH = r"C:\Users\ASUS\ArundaTrader\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"

ARTIFACT_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_MARKET_DATA_RUN_KEY_FORENSIC_v0.1.json"
)

TOLERANCES = [0, 120, 300, 600]

READ_ONLY = True
NETWORK_FORBIDDEN = True
OUTCOME_CALCULATED = False
PREDICTION_ALLOWED = False
DECISION_ALLOWED = False


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def parse_timestamp(value):
    if value is None:
        return None

    text = normalize_text(value)

    if not text:
        return None

    text = text.replace("Z", "+00:00")

    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def timestamp_delta_seconds(a, b):
    if a is None or b is None:
        return None

    return abs((a - b).total_seconds())


def canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_text(value):
    return hashlib.sha256(
        normalize_text(value).encode("utf-8")
    ).hexdigest()


def row_fingerprint(row):
    payload = {
        key: row[key]
        for key in row.keys()
    }

    return sha256_text(canonical_json(payload))


def execution_fingerprint(row, columns):
    payload = {
        column: row[column]
        for column in columns
        if column in row.keys()
    }

    return sha256_text(canonical_json(payload))


def run_key_fingerprint(row, columns):
    payload = {}

    for column in columns:
        if column in row.keys():
            payload[column] = row[column]

    return sha256_text(canonical_json(payload))


def load_contract():
    if not os.path.exists(CONTRACT_PATH):
        raise FileNotFoundError(
            f"Feature contract not found: {CONTRACT_PATH}"
        )

    with open(
        CONTRACT_PATH,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def recursive_collect(value, timestamp_candidates, symbol_candidates):
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = normalize_text(key).lower()

            if isinstance(item, (str, int, float)):
                if (
                    "timestamp" in key_text
                    or key_text in {
                        "time",
                        "datetime",
                        "date_time",
                        "created_at",
                        "updated_at",
                    }
                ):
                    timestamp_candidates.append(str(item))

                if (
                    key_text in {
                        "symbol",
                        "asset",
                        "ticker",
                        "coin",
                        "market",
                    }
                ):
                    symbol_candidates.append(str(item))

            recursive_collect(
                item,
                timestamp_candidates,
                symbol_candidates,
            )

    elif isinstance(value, list):
        for item in value:
            recursive_collect(
                item,
                timestamp_candidates,
                symbol_candidates,
            )


def extract_feature_inputs(contract):
    timestamp_candidates = []
    symbol_candidates = []

    recursive_collect(
        contract,
        timestamp_candidates,
        symbol_candidates,
    )

    timestamps = []

    for value in timestamp_candidates:
        parsed = parse_timestamp(value)

        if parsed is not None:
            timestamps.append(parsed)

    unique_timestamps = sorted(
        {
            value.isoformat()
            for value in timestamps
        }
    )

    symbols = sorted(
        {
            normalize_text(value).upper()
            for value in symbol_candidates
            if normalize_text(value)
        }
    )

    return unique_timestamps, symbols, {
        "timestamp_candidates": len(timestamp_candidates),
        "symbol_candidates": len(symbol_candidates),
    }


def find_market_data_columns(connection):
    cursor = connection.execute(
        "PRAGMA table_info(market_data)"
    )

    columns = cursor.fetchall()

    if not columns:
        raise RuntimeError(
            "market_data table not found"
        )

    names = [
        column[1]
        for column in columns
    ]

    lower_map = {
        name.lower(): name
        for name in names
    }

    symbol_column = None
    timestamp_column = None

    for candidate in [
        "symbol",
        "ticker",
        "asset",
        "coin",
        "market",
    ]:
        if candidate in lower_map:
            symbol_column = lower_map[candidate]
            break

    for candidate in [
        "timestamp",
        "time",
        "datetime",
        "created_at",
    ]:
        if candidate in lower_map:
            timestamp_column = lower_map[candidate]
            break

    if symbol_column is None:
        raise RuntimeError(
            "No symbol column found in market_data"
        )

    if timestamp_column is None:
        raise RuntimeError(
            "No timestamp column found in market_data"
        )

    return names, symbol_column, timestamp_column


def load_market_data(connection, columns):
    query = (
        "SELECT "
        + ", ".join(
            '"' + column.replace('"', '""') + '"'
            for column in columns
        )
        + " FROM market_data"
    )

    cursor = connection.execute(query)

    rows = cursor.fetchall()

    return rows


def choose_execution_columns(columns):
    preferred = [
        "source",
        "engine_version",
    ]

    return [
        column
        for column in preferred
        if column in columns
    ]


def choose_run_key_columns(columns):
    candidates = [
        "source",
        "engine_version",
        "timestamp",
        "symbol",
        "timeframe",
        "snapshot_id",
        "run_id",
        "batch_id",
        "execution_id",
        "created_at",
        "updated_at",
    ]

    return [
        column
        for column in candidates
        if column in columns
    ]


def build_temporal_inventory(
    rows,
    timestamp_column,
    symbol_column,
):
    inventory = []

    for row in rows:
        parsed = parse_timestamp(
            row[timestamp_column]
        )

        symbol = normalize_text(
            row[symbol_column]
        ).upper()

        inventory.append(
            {
                "row": row,
                "timestamp": parsed,
                "symbol": symbol,
                "row_fingerprint": row_fingerprint(row),
            }
        )

    return inventory


def main():
    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> MARKET DATA RUN KEY FORENSIC v0.1"
    )
    print("=" * 90)
    print(f"Database        : {DB_PATH}")
    print(f"Feature Contract: {CONTRACT_PATH}")
    print("Mode            : READ ONLY")
    print("Network         : FORBIDDEN")
    print("Outcome         : NOT CALCULATED")
    print("Prediction      : FORBIDDEN")
    print("Decision        : FORBIDDEN")
    print(
        "Match Tolerance : 0 / 120 / 300 / 600 seconds"
    )
    print("-" * 90)

    contract = load_contract()

    unique_timestamps, feature_symbols, candidate_counts = (
        extract_feature_inputs(contract)
    )

    print(
        f"Feature timestamp candidates : "
        f"{candidate_counts['timestamp_candidates']}"
    )

    print(
        f"Feature symbol candidates    : "
        f"{candidate_counts['symbol_candidates']}"
    )

    print(
        f"Feature symbols discovered   : "
        f"{len(feature_symbols)}"
    )

    if not unique_timestamps:
        raise RuntimeError(
            "No parseable feature timestamps found"
        )

    print("=" * 90)
    print("FEATURE TIMESTAMP INPUT")
    print("=" * 90)

    print(
        f"Unique timestamps : "
        f"{len(unique_timestamps)}"
    )

    for timestamp in unique_timestamps:
        print(f"  {timestamp}")

    print(
        f"Symbols discovered : "
        f"{len(feature_symbols)}"
    )

    for symbol in feature_symbols:
        print(f"  {symbol}")

    connection = sqlite3.connect(
        DB_PATH
    )

    connection.row_factory = sqlite3.Row

    try:
        (
            market_columns,
            symbol_column,
            timestamp_column,
        ) = find_market_data_columns(
            connection
        )

        print("=" * 90)
        print("MARKET DATA SCHEMA")
        print("=" * 90)

        print(
            f"Symbol column    : "
            f"{symbol_column}"
        )

        print(
            f"Timestamp column : "
            f"{timestamp_column}"
        )

        execution_columns = choose_execution_columns(
            market_columns
        )

        run_key_columns = choose_run_key_columns(
            market_columns
        )

        print("=" * 90)
        print("EXECUTION IDENTITY COLUMNS")
        print("=" * 90)

        for column in execution_columns:
            print(f"  {column}")

        print("=" * 90)
        print("RUN KEY CANDIDATE COLUMNS")
        print("=" * 90)

        for column in run_key_columns:
            print(f"  {column}")

        rows = load_market_data(
            connection,
            market_columns,
        )

        inventory = build_temporal_inventory(
            rows,
            timestamp_column,
            symbol_column,
        )

        parseable = [
            item
            for item in inventory
            if item["timestamp"] is not None
        ]

        market_symbols = sorted(
            {
                item["symbol"]
                for item in parseable
                if item["symbol"]
            }
        )

        print("=" * 90)
        print("MARKET DATA TEMPORAL INVENTORY")
        print("=" * 90)

        print(
            f"Market_data rows loaded : "
            f"{len(rows)}"
        )

        print(
            f"Parseable timestamps    : "
            f"{len(parseable)}"
        )

        print(
            f"Market symbols          : "
            f"{len(market_symbols)}"
        )

        target_dt = parse_timestamp(
            unique_timestamps[0]
        )

        exact_rows = []

        for item in parseable:
            delta = timestamp_delta_seconds(
                item["timestamp"],
                target_dt,
            )

            if delta == 0:
                exact_rows.append(item)

        print("=" * 90)
        print("FEATURE TIMESTAMP TEMPORAL COVERAGE")
        print("=" * 90)

        for tolerance in TOLERANCES:
            count = 0

            for item in parseable:
                delta = timestamp_delta_seconds(
                    item["timestamp"],
                    target_dt,
                )

                if delta is not None and delta <= tolerance:
                    count += 1

            print(
                f"Within {tolerance:4d}s : {count}"
            )

        exact_symbols = sorted(
            {
                item["symbol"]
                for item in exact_rows
                if item["symbol"]
            }
        )

        print(
            f"Exact timestamp matches : "
            f"{len(exact_rows)}"
        )

        print(
            f"Exact-match symbols      : "
            f"{len(exact_symbols)}"
        )

        execution_groups = {}

        for item in exact_rows:
            fingerprint = execution_fingerprint(
                item["row"],
                execution_columns,
            )

            execution_groups.setdefault(
                fingerprint,
                [],
            ).append(item)

        run_key_groups = {}

        for item in exact_rows:
            fingerprint = run_key_fingerprint(
                item["row"],
                run_key_columns,
            )

            run_key_groups.setdefault(
                fingerprint,
                [],
            ).append(item)

        print("=" * 90)
        print("RUN KEY FORENSIC SUMMARY")
        print("=" * 90)

        print(
            f"Exact market_data rows : "
            f"{len(exact_rows)}"
        )

        print(
            f"Unique exact row fingerprints : "
            f"{len(set(item['row_fingerprint'] for item in exact_rows))}"
        )

        print(
            f"Execution identity columns : "
            f"{', '.join(execution_columns)}"
        )

        print(
            f"Distinct execution fingerprints : "
            f"{len(execution_groups)}"
        )

        print(
            f"Run-key columns : "
            f"{', '.join(run_key_columns)}"
        )

        print(
            f"Distinct run-key fingerprints : "
            f"{len(run_key_groups)}"
        )

        print("=" * 90)
        print("CROSS-SYMBOL RUN KEY IDENTITY")
        print("=" * 90)

        cross_symbol = {}

        for fingerprint, group in run_key_groups.items():
            symbols = sorted(
                {
                    item["symbol"]
                    for item in group
                    if item["symbol"]
                }
            )

            cross_symbol[fingerprint] = {
                "count": len(group),
                "symbols": symbols,
            }

            print(
                f"RUN KEY FINGERPRINT : "
                f"{fingerprint}"
            )

            print(
                f"COUNT : {len(group)}"
            )

            print(
                f"SYMBOL COUNT : {len(symbols)}"
            )

            print(
                f"SYMBOLS : "
                f"{', '.join(symbols)}"
            )

            representative = group[0]["row"]

            for column in run_key_columns:
                print(
                    f"{column} : "
                    f"{representative[column]}"
                )

            print("-" * 90)

        print("=" * 90)
        print("PER-SYMBOL RUN KEY IDENTITY")
        print("=" * 90)

        per_symbol = {}

        real_feature_symbols = [
            symbol
            for symbol in feature_symbols
            if symbol in market_symbols
        ]

        for symbol in real_feature_symbols:
            symbol_rows = [
                item
                for item in exact_rows
                if item["symbol"] == symbol
            ]

            groups = {}

            for item in symbol_rows:
                fingerprint = run_key_fingerprint(
                    item["row"],
                    run_key_columns,
                )

                groups.setdefault(
                    fingerprint,
                    [],
                ).append(item)

            per_symbol[symbol] = {
                "exact_rows": len(symbol_rows),
                "distinct_run_keys": len(groups),
                "run_keys": {},
            }

            print(
                f"SYMBOL : {symbol}"
            )

            print(
                f"  EXACT ROWS : "
                f"{len(symbol_rows)}"
            )

            print(
                f"  DISTINCT RUN KEYS : "
                f"{len(groups)}"
            )

            for fingerprint, group in groups.items():
                representative = group[0]["row"]

                values = {}

                for column in run_key_columns:
                    values[column] = representative[column]

                per_symbol[symbol]["run_keys"][
                    fingerprint
                ] = {
                    "count": len(group),
                    "values": values,
                    "row_fingerprints": [
                        item["row_fingerprint"]
                        for item in group
                    ],
                }

                print(
                    f"  RUN KEY FINGERPRINT : "
                    f"{fingerprint}"
                )

                print(
                    f"  COUNT : "
                    f"{len(group)}"
                )

                for column in run_key_columns:
                    print(
                        f"  {column} : "
                        f"{representative[column]}"
                    )

            print("-" * 90)

        distinct_cross_symbol_run_keys = 0

        for fingerprint, group in run_key_groups.items():
            symbols = {
                item["symbol"]
                for item in group
                if item["symbol"]
            }

            if len(symbols) >= 2:
                distinct_cross_symbol_run_keys += 1

        if not exact_rows:
            status = (
                "MARKET_DATA_RUN_KEY_NOT_FOUND"
            )
        elif not run_key_columns:
            status = (
                "MARKET_DATA_RUN_KEY_COLUMNS_UNAVAILABLE"
            )
        elif len(run_key_groups) == 1:
            status = (
                "MARKET_DATA_SINGLE_RUN_KEY_ESTABLISHED"
            )
        elif distinct_cross_symbol_run_keys > 0:
            status = (
                "MARKET_DATA_MULTI_RUN_KEY_STRUCTURE_DETECTED"
            )
        else:
            status = (
                "MARKET_DATA_RUN_KEY_IDENTITY_PARTIAL"
            )

        artifact = {
            "artifact": (
                "ARUNDA_SNAPSHOT_FEATURE_"
                "MARKET_DATA_RUN_KEY_FORENSIC_v0.1"
            ),
            "mode": "READ ONLY",
            "network": "FORBIDDEN",
            "outcome": "NOT CALCULATED",
            "prediction": "FORBIDDEN",
            "decision": "FORBIDDEN",
            "database": DB_PATH,
            "feature_contract": CONTRACT_PATH,
            "feature_timestamp": unique_timestamps,
            "feature_symbols_discovered": feature_symbols,
            "market_data_rows_loaded": len(rows),
            "parseable_market_data_rows": len(parseable),
            "market_symbols": market_symbols,
            "symbol_column": symbol_column,
            "timestamp_column": timestamp_column,
            "execution_identity_columns": execution_columns,
            "run_key_columns": run_key_columns,
            "exact_market_data_rows": len(exact_rows),
            "exact_match_symbols": exact_symbols,
            "distinct_execution_fingerprints": len(
                execution_groups
            ),
            "distinct_run_key_fingerprints": len(
                run_key_groups
            ),
            "cross_symbol_run_keys": distinct_cross_symbol_run_keys,
            "cross_symbol_run_key_inventory": cross_symbol,
            "per_symbol": per_symbol,
            "forensic_status": status,
            "predictive_claim": "NOT ESTABLISHED",
            "relationship_calculation": "NOT PERFORMED",
        }

        artifact_json = json.dumps(
            artifact,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        with open(
            ARTIFACT_PATH,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(artifact_json)

        digest = hashlib.sha256(
            artifact_json.encode("utf-8")
        ).hexdigest()

        print("=" * 90)
        print("FORENSIC STATUS")
        print("=" * 90)
        print(
            f"FORENSIC STATUS : {status}"
        )
        print(
            "PREDICTIVE CLAIM : NOT ESTABLISHED"
        )
        print(
            "RELATIONSHIP CALCULATION : NOT PERFORMED"
        )
        print(
            f"Artifact : {ARTIFACT_PATH}"
        )
        print(
            f"SHA256   : {digest}"
        )
        print("=" * 90)

    finally:
        connection.close()


if __name__ == "__main__":
    main()