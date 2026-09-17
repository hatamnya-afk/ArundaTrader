import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone


BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

DB_PATH = BASE_DIR / "arunda.db"
FEATURE_CONTRACT_PATH = BASE_DIR / "ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
ARTIFACT_PATH = BASE_DIR / "ARUNDA_SNAPSHOT_FEATURE_MARKET_DATA_RUN_GROUP_FORENSIC_v0.1.json"

TOLERANCES = [0, 120, 300, 600]


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def normalize_value(value):
    if value is None:
        return None

    if isinstance(value, float):
        return repr(value)

    return str(value)


def normalize_timestamp(value):
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        dt = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        pass

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue

    return None


def timestamp_distance_seconds(a, b):
    if a is None or b is None:
        return None

    return abs((a - b).total_seconds())


def fingerprint(parts):
    payload = "|".join(
        normalize_value(x)
        if x is not None
        else "<NULL>"
        for x in parts
    )

    return sha256_text(payload)


def get_table_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row[1] for row in rows]


def pick_column(columns, candidates):
    lower_map = {
        c.lower(): c
        for c in columns
    }

    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]

    return None


def load_feature_contract():

    if not FEATURE_CONTRACT_PATH.exists():
        return {}

    try:
        with open(
            FEATURE_CONTRACT_PATH,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception:
        return {}


def discover_feature_input(contract):

    timestamps = []
    symbols = []

    def recursive_scan(value):

        if isinstance(value, dict):

            for key, item in value.items():

                key_lower = str(key).lower()

                if (
                    "timestamp" in key_lower
                    or key_lower == "time"
                ):

                    if isinstance(item, str):

                        dt = normalize_timestamp(item)

                        if dt is not None:
                            timestamps.append(dt)

                if "symbol" in key_lower:

                    if isinstance(item, str):

                        symbol = item.strip().upper()

                        if symbol:
                            symbols.append(symbol)

                recursive_scan(item)

        elif isinstance(value, list):

            for item in value:
                recursive_scan(item)

    recursive_scan(contract)

    return timestamps, symbols


def load_market_data():

    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True
    )

    columns = get_table_columns(
        conn,
        "market_data"
    )

    symbol_col = pick_column(
        columns,
        ["symbol"]
    )

    timestamp_col = pick_column(
        columns,
        [
            "timestamp",
            "time",
            "datetime",
            "created_at"
        ]
    )

    if symbol_col is None:
        raise RuntimeError(
            "market_data symbol column not found"
        )

    if timestamp_col is None:
        raise RuntimeError(
            "market_data timestamp column not found"
        )

    rows = conn.execute(
        "SELECT * FROM market_data"
    ).fetchall()

    column_index = {
        column: index
        for index, column in enumerate(columns)
    }

    records = []

    for row in rows:

        symbol = row[
            column_index[symbol_col]
        ]

        timestamp = row[
            column_index[timestamp_col]
        ]

        source = (
            row[column_index["source"]]
            if "source" in column_index
            else None
        )

        engine_version = (
            row[column_index["engine_version"]]
            if "engine_version" in column_index
            else None
        )

        timeframe = (
            row[column_index["timeframe"]]
            if "timeframe" in column_index
            else None
        )

        parsed_timestamp = normalize_timestamp(
            timestamp
        )

        records.append(
            {
                "symbol":
                    str(symbol).strip().upper()
                    if symbol is not None
                    else None,

                "timestamp_raw": timestamp,

                "timestamp": parsed_timestamp,

                "source": source,

                "engine_version":
                    engine_version,

                "timeframe": timeframe,
            }
        )

    conn.close()

    return {
        "columns": columns,
        "symbol_column": symbol_col,
        "timestamp_column": timestamp_col,
        "rows": records,
    }


def find_best_matches(
    feature_timestamps,
    feature_symbols,
    market_rows
):

    exact_matches = []

    all_distances = {
        tolerance: []
        for tolerance in TOLERANCES
    }

    if not feature_timestamps:
        return exact_matches, all_distances

    feature_symbols_set = {
        s.upper()
        for s in feature_symbols
    }

    for market_row in market_rows:

        market_timestamp = market_row[
            "timestamp"
        ]

        if market_timestamp is None:
            continue

        if feature_symbols_set:

            if (
                market_row["symbol"]
                not in feature_symbols_set
            ):
                continue

        best_distance = None
        best_feature_timestamp = None

        for feature_timestamp in feature_timestamps:

            distance = timestamp_distance_seconds(
                market_timestamp,
                feature_timestamp
            )

            if distance is None:
                continue

            if (
                best_distance is None
                or distance < best_distance
            ):

                best_distance = distance
                best_feature_timestamp = (
                    feature_timestamp
                )

        if best_distance is None:
            continue

        for tolerance in TOLERANCES:

            if best_distance <= tolerance:

                all_distances[
                    tolerance
                ].append(
                    {
                        "market_row": market_row,
                        "feature_timestamp":
                            best_feature_timestamp,
                        "distance_seconds":
                            best_distance,
                    }
                )

        if best_distance == 0:

            exact_matches.append(
                {
                    "market_row": market_row,
                    "feature_timestamp":
                        best_feature_timestamp,
                    "distance_seconds": 0,
                }
            )

    return exact_matches, all_distances


def row_fingerprint(row):

    return fingerprint(
        [
            row["source"],
            row["engine_version"],
            row["timestamp_raw"],
            row["symbol"],
            row["timeframe"],
        ]
    )


def execution_fingerprint(row):

    return fingerprint(
        [
            row["source"],
            row["engine_version"],
        ]
    )


def run_key_fingerprint(row):

    return fingerprint(
        [
            row["source"],
            row["engine_version"],
            row["timestamp_raw"],
            row["symbol"],
            row["timeframe"],
        ]
    )


def build_execution_groups(exact_matches):

    groups = {}

    for match in exact_matches:

        row = match["market_row"]

        key = (
            normalize_value(row["source"]),
            normalize_value(
                row["engine_version"]
            ),
        )

        if key not in groups:
            groups[key] = []

        groups[key].append(match)

    records = []

    for key, matches in sorted(
        groups.items(),
        key=lambda item: str(item[0])
    ):

        source, engine_version = key

        symbols = sorted(
            {
                m["market_row"]["symbol"]
                for m in matches
                if m["market_row"]["symbol"]
                is not None
            }
        )

        timeframes = sorted(
            {
                normalize_value(
                    m["market_row"]["timeframe"]
                )
                for m in matches
            }
        )

        timestamps = sorted(
            {
                normalize_value(
                    m["market_row"]["timestamp_raw"]
                )
                for m in matches
            }
        )

        run_keys = sorted(
            {
                run_key_fingerprint(
                    m["market_row"]
                )
                for m in matches
            }
        )

        row_count = len(matches)

        symbol_count = len(symbols)

        timeframe_count = len(timeframes)

        timestamp_count = len(timestamps)

        run_key_count = len(run_keys)

        group_coherent = (
            row_count > 0
            and symbol_count == row_count
            and timeframe_count == 1
            and timestamp_count == 1
            and source is not None
            and engine_version is not None
            and run_key_count == row_count
        )

        group_fingerprint = execution_fingerprint(
            {
                "source": source,
                "engine_version":
                    engine_version,
            }
        )

        records.append(
            {
                "execution_fingerprint":
                    group_fingerprint,

                "row_count":
                    row_count,

                "symbol_count":
                    symbol_count,

                "symbols":
                    symbols,

                "timeframe_count":
                    timeframe_count,

                "timeframes":
                    timeframes,

                "timestamp_count":
                    timestamp_count,

                "timestamps":
                    timestamps,

                "run_key_count":
                    run_key_count,

                "source":
                    source,

                "engine_version":
                    engine_version,

                "group_coherent":
                    group_coherent,
            }
        )

    return records


def build_cross_symbol_groups(
    exact_matches
):

    grouped = {}

    for match in exact_matches:

        row = match["market_row"]

        key = (
            normalize_value(row["source"]),
            normalize_value(
                row["engine_version"]
            ),
            normalize_value(
                row["timestamp_raw"]
            ),
            normalize_value(
                row["timeframe"]
            ),
        )

        if key not in grouped:
            grouped[key] = []

        grouped[key].append(match)

    records = []

    for key, matches in sorted(
        grouped.items(),
        key=lambda item: str(item[0])
    ):

        source, engine_version, timestamp, timeframe = key

        symbols = sorted(
            {
                m["market_row"]["symbol"]
                for m in matches
                if m["market_row"]["symbol"]
                is not None
            }
        )

        run_keys = sorted(
            {
                run_key_fingerprint(
                    m["market_row"]
                )
                for m in matches
            }
        )

        records.append(
            {
                "source":
                    source,

                "engine_version":
                    engine_version,

                "timestamp":
                    timestamp,

                "timeframe":
                    timeframe,

                "row_count":
                    len(matches),

                "symbol_count":
                    len(symbols),

                "symbols":
                    symbols,

                "run_key_count":
                    len(run_keys),

                "cross_symbol":
                    len(symbols) > 1,

                "coherent":
                    (
                        len(matches)
                        == len(symbols)
                        and len(symbols) > 1
                    ),
            }
        )

    return records


def main():

    print("=" * 90)

    print(
        "ARUNDA SNAPSHOT FEATURE -> "
        "MARKET DATA RUN GROUP FORENSIC v0.1"
    )

    print("=" * 90)

    print(
        f"Database        : {DB_PATH}"
    )

    print(
        f"Feature Contract: "
        f"{FEATURE_CONTRACT_PATH}"
    )

    print("Mode            : READ ONLY")
    print("Network         : FORBIDDEN")
    print("Outcome         : NOT CALCULATED")
    print("Prediction      : FORBIDDEN")
    print("Decision        : FORBIDDEN")

    print(
        "Match Tolerance : "
        "0 / 120 / 300 / 600 seconds"
    )

    contract = load_feature_contract()

    (
        feature_timestamps,
        feature_symbols
    ) = discover_feature_input(
        contract
    )

    feature_timestamps = sorted(
        set(feature_timestamps)
    )

    feature_symbols = sorted(
        set(
            s.upper()
            for s in feature_symbols
        )
    )

    print("-" * 90)

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

    print("=" * 90)
    print("FEATURE TIMESTAMP INPUT")
    print("=" * 90)

    print(
        f"Unique timestamps : "
        f"{len(feature_timestamps)}"
    )

    for timestamp in feature_timestamps:

        print(
            f"  {timestamp.isoformat()}"
        )

    print(
        f"Symbols discovered : "
        f"{len(feature_symbols)}"
    )

    for symbol in feature_symbols:
        print(f"  {symbol}")

    market_data = load_market_data()

    print("=" * 90)
    print("MARKET DATA SCHEMA")
    print("=" * 90)

    print(
        f"Symbol column    : "
        f"{market_data['symbol_column']}"
    )

    print(
        f"Timestamp column : "
        f"{market_data['timestamp_column']}"
    )

    print("=" * 90)
    print("EXECUTION IDENTITY COLUMNS")
    print("=" * 90)

    print("  source")
    print("  engine_version")

    print("=" * 90)
    print("RUN GROUP CANDIDATE COLUMNS")
    print("=" * 90)

    print("  source")
    print("  engine_version")
    print("  timestamp")
    print("  symbol")
    print("  timeframe")

    market_rows = market_data["rows"]

    parseable_count = sum(
        1
        for row in market_rows
        if row["timestamp"] is not None
    )

    market_symbols = sorted(
        {
            row["symbol"]
            for row in market_rows
            if row["symbol"] is not None
        }
    )

    print("=" * 90)
    print("MARKET DATA TEMPORAL INVENTORY")
    print("=" * 90)

    print(
        f"Market_data rows loaded : "
        f"{len(market_rows)}"
    )

    print(
        f"Parseable timestamps    : "
        f"{parseable_count}"
    )

    print(
        f"Market symbols          : "
        f"{len(market_symbols)}"
    )

    (
        exact_matches,
        tolerance_matches
    ) = find_best_matches(
        feature_timestamps,
        feature_symbols,
        market_rows
    )

    print("=" * 90)
    print("FEATURE TIMESTAMP TEMPORAL COVERAGE")
    print("=" * 90)

    for tolerance in TOLERANCES:

        print(
            f"Within {tolerance:>4}s : "
            f"{len(tolerance_matches[tolerance])}"
        )

    exact_symbols = sorted(
        {
            m["market_row"]["symbol"]
            for m in exact_matches
            if m["market_row"]["symbol"]
            is not None
        }
    )

    print(
        f"Exact timestamp matches : "
        f"{len(exact_matches)}"
    )

    print(
        f"Exact-match symbols      : "
        f"{len(exact_symbols)}"
    )

    exact_row_fingerprints = sorted(
        {
            row_fingerprint(
                m["market_row"]
            )
            for m in exact_matches
        }
    )

    execution_groups = (
        build_execution_groups(
            exact_matches
        )
    )

    cross_symbol_groups = (
        build_cross_symbol_groups(
            exact_matches
        )
    )

    print("=" * 90)
    print("RUN GROUP FORENSIC SUMMARY")
    print("=" * 90)

    print(
        f"Exact market_data rows : "
        f"{len(exact_matches)}"
    )

    print(
        f"Unique exact row fingerprints : "
        f"{len(exact_row_fingerprints)}"
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
        "source, engine_version, "
        "timestamp, symbol, timeframe"
    )

    distinct_run_keys = len(
        {
            run_key_fingerprint(
                m["market_row"]
            )
            for m in exact_matches
        }
    )

    print(
        f"Distinct run-key groups : "
        f"{distinct_run_keys}"
    )

    cross_symbol_execution_groups = sum(
        1
        for record in execution_groups
        if record["symbol_count"] > 1
    )

    print(
        f"Cross-symbol execution groups : "
        f"{cross_symbol_execution_groups}"
    )

    print("=" * 90)
    print("EXECUTION GROUP IDENTITY")
    print("=" * 90)

    for record in execution_groups:

        print(
            "EXECUTION FINGERPRINT : "
            f"{record['execution_fingerprint']}"
        )

        print(
            f"COUNT : "
            f"{record['row_count']}"
        )

        print(
            f"SYMBOL COUNT : "
            f"{record['symbol_count']}"
        )

        print(
            "SYMBOLS : "
            + ", ".join(record["symbols"])
        )

        print(
            f"TIMEFRAME COUNT : "
            f"{record['timeframe_count']}"
        )

        print(
            "TIMEFRAMES : "
            + ", ".join(
                str(x)
                for x in record["timeframes"]
            )
        )

        print(
            f"TIMESTAMP COUNT : "
            f"{record['timestamp_count']}"
        )

        print(
            f"RUN KEY COUNT : "
            f"{record['run_key_count']}"
        )

        print(
            f"source : "
            f"{record['source']}"
        )

        print(
            f"engine_version : "
            f"{record['engine_version']}"
        )

        print(
            f"GROUP COHERENT : "
            f"{record['group_coherent']}"
        )

        print("-" * 90)

    print("=" * 90)
    print("CROSS-SYMBOL EXECUTION GROUPS")
    print("=" * 90)

    for record in execution_groups:

        if record["symbol_count"] <= 1:
            continue

        print(
            "EXECUTION FINGERPRINT : "
            f"{record['execution_fingerprint']}"
        )

        print(
            f"SYMBOL COUNT : "
            f"{record['symbol_count']}"
        )

        print(
            "SYMBOLS : "
            + ", ".join(record["symbols"])
        )

        print(
            f"COUNT : "
            f"{record['row_count']}"
        )

        print(
            f"TIMESTAMP COUNT : "
            f"{record['timestamp_count']}"
        )

        print(
            f"TIMEFRAME COUNT : "
            f"{record['timeframe_count']}"
        )

        print(
            f"GROUP COHERENT : "
            f"{record['group_coherent']}"
        )

        print("-" * 90)

    print("=" * 90)
    print("PER-SYMBOL RUN GROUP IDENTITY")
    print("=" * 90)

    per_symbol = {}

    for match in exact_matches:

        row = match["market_row"]

        symbol = row["symbol"]

        if symbol not in per_symbol:
            per_symbol[symbol] = []

        per_symbol[symbol].append(
            {
                "source":
                    row["source"],

                "engine_version":
                    row["engine_version"],

                "timestamp":
                    row["timestamp_raw"],

                "timeframe":
                    row["timeframe"],

                "run_key_fingerprint":
                    run_key_fingerprint(row),
            }
        )

    for symbol in sorted(per_symbol):

        records = per_symbol[symbol]

        print(
            f"SYMBOL : {symbol}"
        )

        print(
            f"ROW COUNT : {len(records)}"
        )

        print(
            "DISTINCT RUN KEYS : "
            f"{len({r['run_key_fingerprint'] for r in records})}"
        )

        execution_pairs = sorted(
            {
                (
                    normalize_value(
                        r["source"]
                    ),
                    normalize_value(
                        r["engine_version"]
                    ),
                )
                for r in records
            }
        )

        print(
            "DISTINCT EXECUTION IDENTITIES : "
            f"{len(execution_pairs)}"
        )

        for source, engine_version in execution_pairs:

            print(
                f"  {source} | {engine_version}"
            )

        print("-" * 90)

    all_groups_coherent = all(
        record["group_coherent"]
        for record in execution_groups
    )

    cross_symbol_group_count = sum(
        1
        for record in cross_symbol_groups
        if record["cross_symbol"]
    )

    if (
        len(exact_matches) > 0
        and len(execution_groups) > 0
        and all_groups_coherent
        and cross_symbol_group_count > 0
    ):

        forensic_status = (
            "MARKET_DATA_RUN_GROUP_IDENTITY_ESTABLISHED"
        )

    elif len(exact_matches) > 0:

        forensic_status = (
            "MARKET_DATA_RUN_GROUP_IDENTITY_PARTIAL"
        )

    else:

        forensic_status = (
            "MARKET_DATA_RUN_GROUP_IDENTITY_NOT_ESTABLISHED"
        )

    print("=" * 90)
    print("FORENSIC STATUS")
    print("=" * 90)

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

    artifact = {
        "artifact":
            "ARUNDA_SNAPSHOT_FEATURE_MARKET_DATA_RUN_GROUP_FORENSIC_v0.1",

        "version":
            "v0.1",

        "mode":
            "READ ONLY",

        "network":
            "FORBIDDEN",

        "outcome":
            "NOT CALCULATED",

        "prediction":
            "FORBIDDEN",

        "decision":
            "FORBIDDEN",

        "database":
            str(DB_PATH),

        "feature_contract":
            str(FEATURE_CONTRACT_PATH),

        "match_tolerances_seconds":
            TOLERANCES,

        "feature_input":
            {
                "unique_timestamps":
                    [
                        x.isoformat()
                        for x in feature_timestamps
                    ],

                "symbols":
                    feature_symbols,
            },

        "market_data_inventory":
            {
                "rows_loaded":
                    len(market_rows),

                "parseable_timestamps":
                    parseable_count,

                "market_symbols":
                    market_symbols,
            },

        "temporal_coverage":
            {
                str(tolerance):
                    len(
                        tolerance_matches[tolerance]
                    )
                for tolerance in TOLERANCES
            },

        "exact_match_summary":
            {
                "rows":
                    len(exact_matches),

                "unique_row_fingerprints":
                    len(exact_row_fingerprints),

                "exact_symbols":
                    exact_symbols,
            },

        "execution_groups":
            execution_groups,

        "cross_symbol_groups":
            cross_symbol_groups,

        "per_symbol":
            per_symbol,

        "forensic_status":
            forensic_status,

        "predictive_claim":
            "NOT ESTABLISHED",

        "relationship_calculation":
            "NOT PERFORMED",

        "generated_at_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }

    with open(
        ARTIFACT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            artifact,
            f,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )

    artifact_hash = sha256_file(
        ARTIFACT_PATH
    )

    print(
        f"Artifact : "
        f"{ARTIFACT_PATH}"
    )

    print(
        f"SHA256   : "
        f"{artifact_hash}"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()