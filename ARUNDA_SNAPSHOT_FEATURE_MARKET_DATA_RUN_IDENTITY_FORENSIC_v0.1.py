import sqlite3
import json
import hashlib
import os
from datetime import datetime, timezone


DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

FEATURE_CONTRACT_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)

ARTIFACT_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_MARKET_DATA_RUN_IDENTITY_FORENSIC_v0.1.json"
)

MATCH_TOLERANCES = [0, 120, 300, 600]


SYMBOL_KEYS = {
    "symbol",
    "symbols",
    "ticker",
    "tickers",
    "asset",
    "assets",
    "coin",
    "coins",
    "market_symbols",
    "feature_symbols",
    "universe",
}

TIMESTAMP_KEYS = {
    "timestamp",
    "time",
    "datetime",
    "date_time",
    "created_at",
    "createdat",
    "snapshot_timestamp",
    "feature_timestamp",
    "as_of",
    "asof",
    "ts",
}


def parse_timestamp(value):

    if value is None:
        return None

    if isinstance(value, (int, float)):

        try:
            return datetime.fromtimestamp(
                float(value),
                tz=timezone.utc
            )
        except Exception:
            return None

    if not isinstance(value, str):
        return None

    text = value.strip()

    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        )

    except Exception:
        return None


def normalize_timestamp(dt):

    if dt is None:
        return None

    return dt.astimezone(
        timezone.utc
    ).isoformat(
        timespec="microseconds"
    )


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def walk_json(value, path="root"):

    yield path, value

    if isinstance(value, dict):

        for key, child in value.items():

            child_path = (
                path
                + "."
                + str(key)
            )

            yield from walk_json(
                child,
                child_path
            )

    elif isinstance(value, list):

        for index, child in enumerate(value):

            child_path = (
                path
                + "["
                + str(index)
                + "]"
            )

            yield from walk_json(
                child,
                child_path
            )


def extract_timestamp_candidates(data):

    result = []

    for path, node in walk_json(data):

        if isinstance(node, dict):

            for key, value in node.items():

                key_lower = str(
                    key
                ).lower().strip()

                if key_lower in TIMESTAMP_KEYS:

                    dt = parse_timestamp(
                        value
                    )

                    if dt is not None:

                        result.append(
                            {
                                "path": (
                                    path
                                    + "."
                                    + str(key)
                                ),
                                "key": str(key),
                                "raw": value,
                                "timestamp":
                                    normalize_timestamp(dt),
                            }
                        )

    return result


def extract_all_parseable_timestamps(data):

    result = []

    for path, node in walk_json(data):

        if isinstance(node, (str, int, float)):

            dt = parse_timestamp(node)

            if dt is not None:

                result.append(
                    {
                        "path": path,
                        "raw": node,
                        "timestamp":
                            normalize_timestamp(dt),
                    }
                )

    return result


def normalize_symbol(value):

    if not isinstance(value, str):
        return None

    text = value.strip().upper()

    if not text:
        return None

    return text


def collect_symbols_from_value(value):

    symbols = []

    if isinstance(value, str):

        symbol = normalize_symbol(value)

        if symbol is not None:
            symbols.append(symbol)

    elif isinstance(value, list):

        for item in value:

            symbols.extend(
                collect_symbols_from_value(item)
            )

    elif isinstance(value, dict):

        for key, child in value.items():

            key_lower = str(
                key
            ).lower().strip()

            if key_lower in SYMBOL_KEYS:

                symbols.extend(
                    collect_symbols_from_value(
                        child
                    )
                )

    return symbols


def extract_symbol_candidates(data):

    symbols = []

    for path, node in walk_json(data):

        if not isinstance(node, dict):
            continue

        for key, value in node.items():

            key_lower = str(
                key
            ).lower().strip()

            if key_lower not in SYMBOL_KEYS:
                continue

            values = collect_symbols_from_value(
                value
            )

            for symbol in values:

                symbols.append(
                    {
                        "path": path,
                        "key": str(key),
                        "symbol": symbol,
                    }
                )

    return symbols


def extract_symbol_like_strings(data):

    candidates = []

    for path, node in walk_json(data):

        if not isinstance(node, str):
            continue

        value = node.strip().upper()

        if not value:
            continue

        if len(value) > 12:
            continue

        if not value.isalpha():
            continue

        if value in {
            "TRUE",
            "FALSE",
            "NULL",
            "NONE",
            "READ",
            "ONLY",
            "UNKNOWN",
        }:
            continue

        candidates.append(
            {
                "path": path,
                "symbol": value,
            }
        )

    return candidates


def detect_columns(
    conn,
    table_name
):

    rows = conn.execute(
        "PRAGMA table_info(" + table_name + ")"
    ).fetchall()

    columns = [
        row[1]
        for row in rows
    ]

    symbol_column = None
    timestamp_column = None

    for column in columns:

        lower = column.lower()

        if symbol_column is None:

            if lower in {
                "symbol",
                "ticker",
                "asset",
            }:

                symbol_column = column

        if timestamp_column is None:

            if lower in {
                "timestamp",
                "time",
                "datetime",
                "created_at",
                "ts",
            }:

                timestamp_column = column

    return (
        columns,
        symbol_column,
        timestamp_column
    )


def table_exists(
    conn,
    table_name
):

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        """,
        (table_name,)
    ).fetchone()

    return row is not None


def row_fingerprint(row):

    payload = []

    for key in row.keys():

        value = row[key]

        payload.append(
            (
                str(key),
                None
                if value is None
                else str(value)
            )
        )

    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def execution_fingerprint(
    row,
    columns
):

    payload = []

    for column in columns:

        value = row[column]

        payload.append(
            (
                column,
                None
                if value is None
                else str(value)
            )
        )

    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def choose_execution_columns(
    columns
):

    preferred = [
        "source",
        "engine_version",
        "run_id",
        "execution_id",
        "batch_id",
        "job_id",
        "request_id",
        "snapshot_id",
        "created_by",
    ]

    lowered = {
        column.lower(): column
        for column in columns
    }

    result = []

    for name in preferred:

        if name in lowered:

            result.append(
                lowered[name]
            )

    return result


def load_market_data(conn):

    (
        columns,
        symbol_column,
        timestamp_column
    ) = detect_columns(
        conn,
        "market_data"
    )

    if symbol_column is None:

        raise RuntimeError(
            "market_data symbol column not found"
        )

    if timestamp_column is None:

        raise RuntimeError(
            "market_data timestamp column not found"
        )

    rows = conn.execute(
        "SELECT rowid AS __rowid__, * "
        "FROM market_data"
    ).fetchall()

    parsed = []

    for row in rows:

        dt = parse_timestamp(
            row[timestamp_column]
        )

        if dt is None:
            continue

        symbol = normalize_symbol(
            row[symbol_column]
        )

        if symbol is None:
            continue

        parsed.append(
            {
                "row": row,
                "datetime": dt,
                "symbol": symbol,
            }
        )

    return {
        "columns": columns,
        "symbol_column": symbol_column,
        "timestamp_column": timestamp_column,
        "raw_rows": len(rows),
        "rows": parsed,
    }


def main():

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> MARKET DATA "
        "RUN IDENTITY FORENSIC v0.1"
    )
    print("=" * 90)

    print(
        "Database        :",
        DB_PATH
    )

    print(
        "Feature Contract:",
        FEATURE_CONTRACT_PATH
    )

    print("Mode            : READ ONLY")
    print("Network         : FORBIDDEN")
    print("Outcome         : NOT CALCULATED")
    print("Prediction      : FORBIDDEN")
    print("Decision        : FORBIDDEN")

    print(
        "Match Tolerance : 0 / 120 / 300 / 600 seconds"
    )

    print("-" * 90)

    if not os.path.exists(DB_PATH):

        raise FileNotFoundError(
            DB_PATH
        )

    if not os.path.exists(
        FEATURE_CONTRACT_PATH
    ):

        raise FileNotFoundError(
            FEATURE_CONTRACT_PATH
        )

    feature_data = load_json(
        FEATURE_CONTRACT_PATH
    )

    timestamp_candidates = (
        extract_timestamp_candidates(
            feature_data
        )
    )

    all_timestamp_candidates = (
        extract_all_parseable_timestamps(
            feature_data
        )
    )

    symbol_candidates = (
        extract_symbol_candidates(
            feature_data
        )
    )

    symbols = sorted(
        {
            item["symbol"]
            for item in symbol_candidates
        }
    )

    if not symbols:

        fallback_symbols = (
            extract_symbol_like_strings(
                feature_data
            )
        )

        symbols = sorted(
            {
                item["symbol"]
                for item in fallback_symbols
            }
        )

    timestamps = sorted(
        {
            item["timestamp"]
            for item in timestamp_candidates
        }
    )

    if not timestamps:

        timestamps = sorted(
            {
                item["timestamp"]
                for item in all_timestamp_candidates
            }
        )

    print(
        "Feature timestamp candidates :",
        len(all_timestamp_candidates)
    )

    print(
        "Timestamp-key candidates      :",
        len(timestamp_candidates)
    )

    print(
        "Feature symbols discovered    :",
        len(symbols)
    )

    print("=" * 90)
    print("FEATURE TIMESTAMP INPUT")
    print("=" * 90)

    print(
        "Unique timestamps :",
        len(timestamps)
    )

    for timestamp in timestamps:

        print(
            " ",
            timestamp
        )

    print(
        "Symbols discovered :",
        len(symbols)
    )

    for symbol in symbols:

        print(
            " ",
            symbol
        )

    if not timestamps:

        raise RuntimeError(
            "No parseable feature timestamp found"
        )

    if not symbols:

        raise RuntimeError(
            "No feature symbols found"
        )

    target_timestamp = timestamps[0]

    target_dt = parse_timestamp(
        target_timestamp
    )

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    try:

        if not table_exists(
            conn,
            "market_data"
        ):

            raise RuntimeError(
                "market_data table not found"
            )

        market = load_market_data(
            conn
        )

        columns = market["columns"]

        symbol_column = (
            market["symbol_column"]
        )

        timestamp_column = (
            market["timestamp_column"]
        )

        execution_columns = (
            choose_execution_columns(
                columns
            )
        )

        print("=" * 90)
        print("MARKET DATA SCHEMA")
        print("=" * 90)

        print(
            "Symbol column    :",
            symbol_column
        )

        print(
            "Timestamp column :",
            timestamp_column
        )

        print("=" * 90)
        print("EXECUTION IDENTITY COLUMNS")
        print("=" * 90)

        if execution_columns:

            for column in execution_columns:

                print(
                    " ",
                    column
                )

        else:

            print(
                "NONE"
            )

        print("=" * 90)
        print("MARKET DATA TEMPORAL INVENTORY")
        print("=" * 90)

        print(
            "Market_data rows loaded :",
            market["raw_rows"]
        )

        print(
            "Parseable timestamps    :",
            len(market["rows"])
        )

        print(
            "Market symbols          :",
            len(
                {
                    item["symbol"]
                    for item in market["rows"]
                }
            )
        )

        results = []

        all_exact_rows = []

        all_execution_fingerprints = set()

        for symbol in symbols:

            candidates = []

            for item in market["rows"]:

                if item["symbol"] != symbol:
                    continue

                delta = abs(
                    (
                        item["datetime"]
                        - target_dt
                    ).total_seconds()
                )

                candidates.append(
                    (
                        delta,
                        item
                    )
                )

            candidates.sort(
                key=lambda x: x[0]
            )

            exact_items = [
                item
                for delta, item in candidates
                if delta == 0
            ]

            within_120 = [
                item
                for delta, item in candidates
                if delta <= 120
            ]

            within_300 = [
                item
                for delta, item in candidates
                if delta <= 300
            ]

            within_600 = [
                item
                for delta, item in candidates
                if delta <= 600
            ]

            execution_groups = {}

            for item in exact_items:

                row = item["row"]

                all_exact_rows.append(
                    row
                )

                if execution_columns:

                    fingerprint = (
                        execution_fingerprint(
                            row,
                            execution_columns
                        )
                    )

                    values = {}

                    for column in execution_columns:

                        values[column] = row[column]

                else:

                    fingerprint = (
                        "NO_EXPLICIT_EXECUTION_IDENTITY"
                    )

                    values = {}

                all_execution_fingerprints.add(
                    fingerprint
                )

                if fingerprint not in execution_groups:

                    execution_groups[
                        fingerprint
                    ] = {
                        "count": 0,
                        "values": values,
                    }

                execution_groups[
                    fingerprint
                ]["count"] += 1

            nearest = (
                candidates[0]
                if candidates
                else None
            )

            result = {
                "symbol": symbol,
                "feature_timestamp":
                    target_timestamp,
                "candidate_count":
                    len(candidates),
                "exact_count":
                    len(exact_items),
                "within_120_count":
                    len(within_120),
                "within_300_count":
                    len(within_300),
                "within_600_count":
                    len(within_600),
                "exact_row_fingerprints":
                    sorted(
                        {
                            row_fingerprint(
                                item["row"]
                            )
                            for item in exact_items
                        }
                    ),
                "execution_groups": [],
            }

            for fingerprint, group in sorted(
                execution_groups.items()
            ):

                result[
                    "execution_groups"
                ].append(
                    {
                        "execution_fingerprint":
                            fingerprint,
                        "count":
                            group["count"],
                        "values":
                            group["values"],
                    }
                )

            if nearest is not None:

                result[
                    "nearest_timestamp"
                ] = normalize_timestamp(
                    nearest[1]["datetime"]
                )

                result[
                    "nearest_delta_seconds"
                ] = nearest[0]

                result[
                    "nearest_row_fingerprint"
                ] = row_fingerprint(
                    nearest[1]["row"]
                )

            else:

                result[
                    "nearest_timestamp"
                ] = None

                result[
                    "nearest_delta_seconds"
                ] = None

                result[
                    "nearest_row_fingerprint"
                ] = None

            if exact_items:

                result["status"] = (
                    "EXACT_TIMESTAMP_MATCH"
                )

            elif candidates:

                result["status"] = (
                    "SAME_SYMBOL_TEMPORAL_MISMATCH"
                )

            else:

                result["status"] = (
                    "NO_SAME_SYMBOL_MARKET_DATA"
                )

            results.append(
                result
            )

        print("=" * 90)
        print("FEATURE TIMESTAMP TEMPORAL COVERAGE")
        print("=" * 90)

        print(
            "Within    0s :",
            sum(
                r["exact_count"]
                for r in results
            )
        )

        print(
            "Within  120s :",
            sum(
                r["within_120_count"]
                for r in results
            )
        )

        print(
            "Within  300s :",
            sum(
                r["within_300_count"]
                for r in results
            )
        )

        print(
            "Within  600s :",
            sum(
                r["within_600_count"]
                for r in results
            )
        )

        print(
            "Exact timestamp matches :",
            sum(
                r["exact_count"]
                for r in results
            )
        )

        print(
            "Exact-match symbols :",
            len(
                {
                    r["symbol"]
                    for r in results
                    if r["exact_count"] > 0
                }
            )
        )

        print("=" * 90)
        print("EXECUTION / RUN IDENTITY SUMMARY")
        print("=" * 90)

        print(
            "Exact market_data rows :",
            len(all_exact_rows)
        )

        print(
            "Unique exact row fingerprints :",
            len(
                {
                    row_fingerprint(row)
                    for row in all_exact_rows
                }
            )
        )

        print(
            "Execution identity columns :",
            ", ".join(execution_columns)
            if execution_columns
            else "NONE"
        )

        print(
            "Distinct execution fingerprints :",
            len(all_execution_fingerprints)
        )

        print("=" * 90)
        print("PER-SYMBOL RUN IDENTITY")
        print("=" * 90)

        for result in results:

            print(
                "SYMBOL :",
                result["symbol"]
            )

            print(
                "  EXACT ROWS :",
                result["exact_count"]
            )

            print(
                "  DISTINCT EXECUTION GROUPS :",
                len(
                    result[
                        "execution_groups"
                    ]
                )
            )

            for group in result[
                "execution_groups"
            ]:

                print(
                    "  EXECUTION FINGERPRINT :",
                    group[
                        "execution_fingerprint"
                    ]
                )

                print(
                    "  COUNT :",
                    group["count"]
                )

                for key, value in group[
                    "values"
                ].items():

                    print(
                        "  " + str(key) + " :",
                        value
                    )

            print("-" * 90)

        exact_symbols = len(
            {
                r["symbol"]
                for r in results
                if r["exact_count"] > 0
            }
        )

        total_symbols = len(symbols)

        if exact_symbols == 0:

            forensic_status = (
                "NO_MARKET_DATA_TEMPORAL_MATCH"
            )

        elif not execution_columns:

            forensic_status = (
                "MARKET_DATA_RUN_IDENTITY_NOT_EXPLICIT"
            )

        elif (
            exact_symbols == total_symbols
            and len(
                all_execution_fingerprints
            ) == 1
        ):

            forensic_status = (
                "MARKET_DATA_RUN_IDENTITY_ESTABLISHED"
            )

        elif (
            exact_symbols == total_symbols
            and len(
                all_execution_fingerprints
            ) > 1
        ):

            forensic_status = (
                "MARKET_DATA_RUN_IDENTITY_AMBIGUOUS"
            )

        else:

            forensic_status = (
                "MARKET_DATA_PARTIAL_RUN_IDENTITY"
            )

        artifact = {
            "artifact":
                "ARUNDA_SNAPSHOT_FEATURE_MARKET_DATA_"
                "RUN_IDENTITY_FORENSIC_v0.1",
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
                DB_PATH,
            "feature_contract":
                FEATURE_CONTRACT_PATH,
            "feature_timestamp_candidates":
                len(all_timestamp_candidates),
            "feature_timestamp_key_candidates":
                len(timestamp_candidates),
            "feature_identities":
                len(identities)
                if "identities" in locals()
                else len(timestamps),
            "feature_timestamps":
                timestamps,
            "feature_symbols":
                symbols,
            "symbol_provenance":
                symbol_candidates,
            "execution_identity_columns":
                execution_columns,
            "market_data_schema": {
                "columns":
                    columns,
                "symbol_column":
                    symbol_column,
                "timestamp_column":
                    timestamp_column,
            },
            "market_data_inventory": {
                "raw_rows":
                    market["raw_rows"],
                "parseable_rows":
                    len(market["rows"]),
            },
            "results":
                results,
            "cross_symbol": {
                "total_symbols":
                    total_symbols,
                "exact_match_symbols":
                    exact_symbols,
                "all_symbols_exact":
                    exact_symbols == total_symbols,
                "distinct_execution_fingerprints":
                    len(
                        all_execution_fingerprints
                    ),
                "single_cross_symbol_execution_identity":
                    len(
                        all_execution_fingerprints
                    ) == 1,
            },
            "forensic_status":
                forensic_status,
            "predictive_claim":
                "NOT ESTABLISHED",
            "relationship_calculation":
                "NOT PERFORMED",
        }

        payload = json.dumps(
            artifact,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ).encode("utf-8")

        with open(
            ARTIFACT_PATH,
            "wb"
        ) as f:

            f.write(payload)

        sha256 = hashlib.sha256(
            payload
        ).hexdigest()

        print("=" * 90)
        print("FORENSIC STATUS")
        print("=" * 90)

        print(
            "FORENSIC STATUS :",
            forensic_status
        )

        print(
            "PREDICTIVE CLAIM : NOT ESTABLISHED"
        )

        print(
            "RELATIONSHIP CALCULATION : NOT PERFORMED"
        )

        print(
            "Artifact :",
            ARTIFACT_PATH
        )

        print(
            "SHA256   :",
            sha256
        )

        print("=" * 90)

    finally:

        conn.close()


if __name__ == "__main__":
    main()