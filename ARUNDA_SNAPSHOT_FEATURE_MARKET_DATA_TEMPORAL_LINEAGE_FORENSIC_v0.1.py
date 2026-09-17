import hashlib
import json
import os
import sqlite3
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone


# =============================================================================
# ARUNDA SNAPSHOT FEATURE -> MARKET DATA TEMPORAL LINEAGE FORENSIC v0.1
# =============================================================================

DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

FEATURE_CONTRACT_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)

ARTIFACT_PATH = (
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_MARKET_DATA_TEMPORAL_LINEAGE_FORENSIC_v0.1.json"
)

MODE = "READ ONLY"
NETWORK = "FORBIDDEN"
OUTCOME = "NOT CALCULATED"
PREDICTION = "FORBIDDEN"
DECISION = "FORBIDDEN"

TOLERANCES = [0, 120, 300, 600]


# =============================================================================
# UTILITIES
# =============================================================================

def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def parse_timestamp(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()

        if not text:
            return None

        # SQLite / ISO compatibility
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            formats = [
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S.%f",
                "%Y/%m/%d %H:%M:%S",
            ]

            dt = None

            for fmt in formats:
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue

            if dt is None:
                return None

    if dt.tzinfo is None:
        # IMPORTANT:
        # Hunter/SQLite timestamps seen in previous forensic work are naive.
        # We do NOT assume a timezone conversion here.
        return dt

    return dt.astimezone(timezone.utc)


def timestamp_key(dt):
    if dt is None:
        return None

    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)

    return dt.replace(tzinfo=None).isoformat(timespec="microseconds")


def delta_seconds(a, b):
    if a is None or b is None:
        return None

    # Compare absolute wall-clock instants only after normalization.
    if a.tzinfo is not None:
        a = a.astimezone(timezone.utc).replace(tzinfo=None)

    if b.tzinfo is not None:
        b = b.astimezone(timezone.utc).replace(tzinfo=None)

    return abs((a - b).total_seconds())


def json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, bytes):
        return value.hex()

    return value


def row_to_dict(cursor, row):
    result = {}

    for index, column in enumerate(cursor.description):
        result[column[0]] = json_safe(row[index])

    return result


def table_exists(conn, table_name):
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


def table_columns(conn, table_name):
    rows = conn.execute(
        "PRAGMA table_info(" + table_name + ")"
    ).fetchall()

    return [row[1] for row in rows]


def pick_column(columns, candidates):
    lowered = {c.lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]

    return None


def safe_select_all(conn, table_name):
    return conn.execute(
        "SELECT * FROM " + table_name
    ).fetchall()


# =============================================================================
# FEATURE CONTRACT DISCOVERY
# =============================================================================

def load_feature_contract(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def recursively_collect_records(obj, records=None):
    if records is None:
        records = []

    if isinstance(obj, dict):
        records.append(obj)

        for value in obj.values():
            recursively_collect_records(value, records)

    elif isinstance(obj, list):
        for item in obj:
            recursively_collect_records(item, records)

    return records


def discover_feature_identities(contract):
    """
    Best-effort forensic extraction.

    We deliberately do NOT mutate the contract and do not assume a single
    schema beyond common timestamp / symbol naming.
    """

    records = recursively_collect_records(contract)

    timestamp_candidates = [
        "timestamp",
        "snapshot_timestamp",
        "feature_timestamp",
        "snapshot_time",
        "time",
        "datetime",
    ]

    symbol_candidates = [
        "asset",
        "symbol",
        "asset_symbol",
        "coin",
        "ticker",
        "market",
    ]

    found = []

    for record in records:
        timestamp_key_name = pick_column(
            list(record.keys()),
            timestamp_candidates,
        )

        symbol_key_name = pick_column(
            list(record.keys()),
            symbol_candidates,
        )

        if timestamp_key_name is None:
            continue

        raw_timestamp = record.get(timestamp_key_name)

        parsed = parse_timestamp(raw_timestamp)

        if parsed is None:
            continue

        symbol = None

        if symbol_key_name is not None:
            symbol = record.get(symbol_key_name)

        if symbol is None:
            # Try nested common identity fields.
            for key in [
                "asset_symbol",
                "asset",
                "symbol",
                "ticker",
            ]:
                if key in record:
                    symbol = record.get(key)
                    break

        if symbol is None:
            continue

        found.append(
            {
                "symbol": str(symbol).strip().upper(),
                "raw_timestamp": str(raw_timestamp),
                "parsed_timestamp": parsed,
                "canonical_timestamp": timestamp_key(parsed),
            }
        )

    # Deduplicate exact feature identities.
    unique = {}
    for item in found:
        key = (
            item["symbol"],
            item["canonical_timestamp"],
        )
        unique[key] = item

    return list(unique.values())


# =============================================================================
# MARKET DATA DISCOVERY
# =============================================================================

def discover_market_data_schema(conn):
    if not table_exists(conn, "market_data"):
        raise RuntimeError("market_data table does not exist")

    columns = table_columns(conn, "market_data")

    symbol_column = pick_column(
        columns,
        [
            "symbol",
            "asset",
            "asset_symbol",
            "coin",
            "ticker",
            "market",
        ],
    )

    timestamp_column = pick_column(
        columns,
        [
            "timestamp",
            "time",
            "datetime",
            "candle_time",
            "open_time",
            "created_at",
        ],
    )

    if symbol_column is None:
        raise RuntimeError(
            "Could not identify market_data symbol column. "
            + "Columns: "
            + ", ".join(columns)
        )

    if timestamp_column is None:
        raise RuntimeError(
            "Could not identify market_data timestamp column. "
            + "Columns: "
            + ", ".join(columns)
        )

    return {
        "columns": columns,
        "symbol_column": symbol_column,
        "timestamp_column": timestamp_column,
    }


def load_market_data(conn, schema):
    symbol_column = schema["symbol_column"]
    timestamp_column = schema["timestamp_column"]

    query = (
        "SELECT * FROM market_data "
        "WHERE " + symbol_column + " IS NOT NULL "
        "AND " + timestamp_column + " IS NOT NULL"
    )

    cursor = conn.execute(query)

    rows = []

    for row in cursor.fetchall():
        record = row_to_dict(cursor, row)

        raw_symbol = record.get(symbol_column)
        raw_timestamp = record.get(timestamp_column)

        if raw_symbol is None or raw_timestamp is None:
            continue

        parsed_timestamp = parse_timestamp(raw_timestamp)

        rows.append(
            {
                "symbol": str(raw_symbol).strip().upper(),
                "raw_timestamp": str(raw_timestamp),
                "parsed_timestamp": parsed_timestamp,
                "canonical_timestamp": timestamp_key(parsed_timestamp),
                "record": record,
            }
        )

    return rows


# =============================================================================
# TEMPORAL INDEX
# =============================================================================

def build_symbol_index(rows):
    index = defaultdict(list)

    for row in rows:
        if row["parsed_timestamp"] is None:
            continue

        index[row["symbol"]].append(row)

    for symbol in index:
        index[symbol].sort(
            key=lambda x: x["parsed_timestamp"]
        )

    return index


def find_nearest(feature, candidates):
    if not candidates:
        return None

    best = None
    best_delta = None

    for candidate in candidates:
        d = delta_seconds(
            feature["parsed_timestamp"],
            candidate["parsed_timestamp"],
        )

        if d is None:
            continue

        if best_delta is None or d < best_delta:
            best = candidate
            best_delta = d

    if best is None:
        return None

    return {
        "row": best,
        "delta_seconds": best_delta,
    }


# =============================================================================
# TEMPORAL FINGERPRINT
# =============================================================================

def build_record_fingerprint(record):
    """
    Stable forensic fingerprint over the actual market_data row.

    This is NOT a prediction feature and is NOT used to alter data.
    """

    normalized = {}

    for key in sorted(record.keys()):
        value = record[key]

        if isinstance(value, str):
            normalized[key] = value.strip()
        else:
            normalized[key] = value

    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def identify_temporal_cluster(matches):
    """
    Try to determine whether the market_data records around the feature
    timestamp form a common execution/snapshot batch.

    No execution identity is invented.
    """

    if not matches:
        return {
            "cluster_identified": False,
            "reason": "NO_MATCHED_MARKET_DATA_ROWS",
        }

    timestamps = []

    for item in matches:
        dt = item["row"]["parsed_timestamp"]

        if dt is not None:
            timestamps.append(dt)

    if not timestamps:
        return {
            "cluster_identified": False,
            "reason": "MATCHED_ROWS_HAVE_NO_PARSEABLE_TIMESTAMP",
        }

    keys = [timestamp_key(dt) for dt in timestamps]

    counts = Counter(keys)

    dominant_timestamp, dominant_count = counts.most_common(1)[0]

    return {
        "cluster_identified": dominant_count >= 2,
        "dominant_timestamp": dominant_timestamp,
        "dominant_timestamp_count": dominant_count,
        "unique_timestamps": len(counts),
        "all_timestamps": sorted(counts.keys()),
    }


# =============================================================================
# MAIN FORENSIC
# =============================================================================

def main():
    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> MARKET DATA TEMPORAL LINEAGE FORENSIC v0.1"
    )
    print("=" * 90)
    print("Database        :", DB_PATH)
    print("Feature Contract:", FEATURE_CONTRACT_PATH)
    print("Mode            :", MODE)
    print("Network         :", NETWORK)
    print("Outcome         :", OUTCOME)
    print("Prediction      :", PREDICTION)
    print("Decision        :", DECISION)
    print("Match Tolerance :", " / ".join(str(x) for x in TOLERANCES), "seconds")
    print("-" * 90)

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(DB_PATH)

    if not os.path.exists(FEATURE_CONTRACT_PATH):
        raise FileNotFoundError(FEATURE_CONTRACT_PATH)

    contract = load_feature_contract(
        FEATURE_CONTRACT_PATH
    )

    feature_identities = discover_feature_identities(
        contract
    )

    print("=" * 90)
    print("FEATURE TIMESTAMP INPUT")
    print("=" * 90)
    print(
        "Feature identities :",
        len(feature_identities),
    )

    unique_feature_timestamps = sorted(
        set(
            item["canonical_timestamp"]
            for item in feature_identities
        )
    )

    print(
        "Unique timestamps  :",
        len(unique_feature_timestamps),
    )

    for ts in unique_feature_timestamps:
        print(" ", ts)

    # -------------------------------------------------------------------------
    # READ ONLY SQLite
    # -------------------------------------------------------------------------

    conn = sqlite3.connect(
        "file:" + DB_PATH + "?mode=ro",
        uri=True,
    )

    try:
        schema = discover_market_data_schema(
            conn
        )

        print("=" * 90)
        print("MARKET DATA SCHEMA")
        print("=" * 90)
        print(
            "Symbol column    :",
            schema["symbol_column"],
        )
        print(
            "Timestamp column :",
            schema["timestamp_column"],
        )

        market_rows = load_market_data(
            conn,
            schema,
        )

    finally:
        conn.close()

    print("=" * 90)
    print("MARKET DATA TEMPORAL INVENTORY")
    print("=" * 90)

    print(
        "Market_data rows loaded :",
        len(market_rows),
    )

    parseable_market_rows = [
        row
        for row in market_rows
        if row["parsed_timestamp"] is not None
    ]

    print(
        "Parseable timestamps    :",
        len(parseable_market_rows),
    )

    market_index = build_symbol_index(
        market_rows
    )

    print(
        "Market symbols          :",
        len(market_index),
    )

    # -------------------------------------------------------------------------
    # MATCH FEATURE -> MARKET DATA
    # -------------------------------------------------------------------------

    per_feature = []

    exact_count = 0
    within_120 = 0
    within_300 = 0
    within_600 = 0

    no_symbol = 0
    timestamp_unavailable = 0

    all_deltas = []

    for feature in feature_identities:

        candidates = market_index.get(
            feature["symbol"],
            [],
        )

        if not candidates:
            no_symbol += 1

            per_feature.append(
                {
                    "symbol": feature["symbol"],
                    "feature_timestamp": feature[
                        "canonical_timestamp"
                    ],
                    "market_data_candidates": 0,
                    "status": "NO_MARKET_DATA_SYMBOL",
                    "nearest": None,
                    "matched_rows": [],
                }
            )

            continue

        nearest = find_nearest(
            feature,
            candidates,
        )

        if nearest is None:
            timestamp_unavailable += 1

            per_feature.append(
                {
                    "symbol": feature["symbol"],
                    "feature_timestamp": feature[
                        "canonical_timestamp"
                    ],
                    "market_data_candidates": len(candidates),
                    "status": "TIMESTAMP_UNAVAILABLE",
                    "nearest": None,
                    "matched_rows": [],
                }
            )

            continue

        nearest_row = nearest["row"]
        nearest_delta = nearest["delta_seconds"]

        all_deltas.append(nearest_delta)

        if nearest_delta == 0:
            exact_count += 1

        if nearest_delta <= 120:
            within_120 += 1

        if nearest_delta <= 300:
            within_300 += 1

        if nearest_delta <= 600:
            within_600 += 1

        # ---------------------------------------------------------------------
        # Actual records inside the strict forensic windows.
        # ---------------------------------------------------------------------

        matched_rows = []

        for candidate in candidates:
            d = delta_seconds(
                feature["parsed_timestamp"],
                candidate["parsed_timestamp"],
            )

            if d is None:
                continue

            if d <= 600:
                record = dict(candidate["record"])

                record["__delta_seconds"] = d
                record["__record_fingerprint"] = (
                    build_record_fingerprint(
                        candidate["record"]
                    )
                )

                matched_rows.append(
                    record
                )

        matched_rows.sort(
            key=lambda x: x["__delta_seconds"]
        )

        temporal_cluster = identify_temporal_cluster(
            [
                {
                    "row": candidate,
                    "delta_seconds": delta_seconds(
                        feature["parsed_timestamp"],
                        candidate["parsed_timestamp"],
                    ),
                }
                for candidate in candidates
                if delta_seconds(
                    feature["parsed_timestamp"],
                    candidate["parsed_timestamp"],
                ) is not None
                and delta_seconds(
                    feature["parsed_timestamp"],
                    candidate["parsed_timestamp"],
                ) <= 600
            ]
        )

        status = "NO_MATCH_WITHIN_600S"

        if nearest_delta == 0:
            status = "EXACT_TIMESTAMP_MATCH"
        elif nearest_delta <= 120:
            status = "MATCH_WITHIN_120S"
        elif nearest_delta <= 300:
            status = "MATCH_WITHIN_300S"
        elif nearest_delta <= 600:
            status = "MATCH_WITHIN_600S"
        else:
            status = "SAME_SYMBOL_TEMPORAL_MISMATCH"

        per_feature.append(
            {
                "symbol": feature["symbol"],
                "feature_timestamp": feature[
                    "canonical_timestamp"
                ],
                "market_data_candidates": len(candidates),
                "status": status,
                "nearest": {
                    "timestamp": nearest_row[
                        "canonical_timestamp"
                    ],
                    "delta_seconds": nearest_delta,
                    "record": nearest_row["record"],
                    "record_fingerprint": (
                        build_record_fingerprint(
                            nearest_row["record"]
                        )
                    ),
                },
                "matched_rows_within_600s": matched_rows,
                "temporal_cluster": temporal_cluster,
            }
        )

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    minimum_delta = (
        min(all_deltas)
        if all_deltas
        else None
    )

    maximum_delta = (
        max(all_deltas)
        if all_deltas
        else None
    )

    mean_delta = (
        statistics.mean(all_deltas)
        if all_deltas
        else None
    )

    median_delta = (
        statistics.median(all_deltas)
        if all_deltas
        else None
    )

    # -------------------------------------------------------------------------
    # Global timestamp coverage
    # -------------------------------------------------------------------------

    exact_market_rows = []

    for feature in feature_identities:

        candidates = market_index.get(
            feature["symbol"],
            [],
        )

        for candidate in candidates:
            d = delta_seconds(
                feature["parsed_timestamp"],
                candidate["parsed_timestamp"],
            )

            if d == 0:
                exact_market_rows.append(
                    candidate
                )

    unique_exact_fingerprints = sorted(
        set(
            build_record_fingerprint(
                row["record"]
            )
            for row in exact_market_rows
        )
    )

    # -------------------------------------------------------------------------
    # Determine whether an execution/run can actually be identified.
    # -------------------------------------------------------------------------

    execution_identity_columns = [
        "run_id",
        "execution_id",
        "batch_id",
        "batch",
        "job_id",
        "execution",
        "run",
        "request_id",
        "snapshot_id",
        "session_id",
        "cycle_id",
        "generated_at",
        "created_at",
        "updated_at",
        "source",
        "engine",
    ]

    discovered_execution_columns = []

    if market_rows:
        available_columns = set(
            market_rows[0]["record"].keys()
        )

        for column in execution_identity_columns:
            if column in available_columns:
                discovered_execution_columns.append(
                    column
                )

    execution_evidence = []

    for item in per_feature:
        nearest = item.get("nearest")

        if nearest is None:
            continue

        record = nearest["record"]

        evidence = {}

        for column in discovered_execution_columns:
            evidence[column] = record.get(column)

        if evidence:
            execution_evidence.append(
                {
                    "symbol": item["symbol"],
                    "feature_timestamp": item[
                        "feature_timestamp"
                    ],
                    "evidence": evidence,
                }
            )

    distinct_execution_fingerprints = set()

    for item in execution_evidence:
        payload = json.dumps(
            item["evidence"],
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )

        distinct_execution_fingerprints.add(
            hashlib.sha256(
                payload.encode("utf-8")
            ).hexdigest()
        )

    # -------------------------------------------------------------------------
    # Forensic status
    # -------------------------------------------------------------------------

    if exact_count > 0:
        if discovered_execution_columns:
            status = "MARKET_DATA_TEMPORAL_LINEAGE_ESTABLISHED"
        else:
            status = "MARKET_DATA_TIMESTAMP_MATCH_ESTABLISHED"
    elif within_120 > 0:
        if discovered_execution_columns:
            status = "MARKET_DATA_NEAR_TEMPORAL_LINEAGE_ESTABLISHED"
        else:
            status = "MARKET_DATA_NEAR_TIMESTAMP_ESTABLISHED"
    elif within_600 > 0:
        status = "MARKET_DATA_TEMPORAL_PROXIMITY_ONLY"
    else:
        status = "MARKET_DATA_TEMPORAL_LINEAGE_NOT_ESTABLISHED"

    # -------------------------------------------------------------------------
    # Console output
    # -------------------------------------------------------------------------

    print("=" * 90)
    print("MARKET DATA TEMPORAL LINEAGE")
    print("=" * 90)

    print(
        "Exact timestamp matches :",
        exact_count,
    )
    print(
        "Within 120s             :",
        within_120,
    )
    print(
        "Within 300s             :",
        within_300,
    )
    print(
        "Within 600s             :",
        within_600,
    )
    print(
        "No market symbol        :",
        no_symbol,
    )
    print(
        "Timestamp unavailable   :",
        timestamp_unavailable,
    )

    print("-" * 90)

    print(
        "Minimum delta (sec)     :",
        minimum_delta,
    )
    print(
        "Maximum delta (sec)     :",
        maximum_delta,
    )
    print(
        "Mean delta (sec)        :",
        mean_delta,
    )
    print(
        "Median delta (sec)      :",
        median_delta,
    )

    print("-" * 90)

    print(
        "Exact market_data rows  :",
        len(exact_market_rows),
    )

    print(
        "Unique exact fingerprints:",
        len(unique_exact_fingerprints),
    )

    print(
        "Execution identity cols :",
        (
            ", ".join(discovered_execution_columns)
            if discovered_execution_columns
            else "NONE"
        ),
    )

    print(
        "Distinct execution fingerprints:",
        len(distinct_execution_fingerprints),
    )

    print("-" * 90)

    print("PER-FEATURE TEMPORAL LINEAGE")

    for item in per_feature:
        print("-" * 90)
        print("SYMBOL :", item["symbol"])
        print(
            "FEATURE TIMESTAMP :",
            item["feature_timestamp"],
        )
        print(
            "MARKET DATA CANDIDATES :",
            item["market_data_candidates"],
        )
        print(
            "STATUS :",
            item["status"],
        )

        nearest = item.get("nearest")

        if nearest is not None:
            print(
                "NEAREST TIMESTAMP :",
                nearest["timestamp"],
            )
            print(
                "NEAREST DELTA SEC :",
                nearest["delta_seconds"],
            )
            print(
                "NEAREST FINGERPRINT :",
                nearest["record_fingerprint"],
            )

        matched = item.get(
            "matched_rows_within_600s",
            [],
        )

        print(
            "ROWS WITHIN 600S :",
            len(matched),
        )

        cluster = item.get(
            "temporal_cluster"
        )

        if cluster:
            print(
                "TEMPORAL CLUSTER :",
                cluster.get(
                    "cluster_identified"
                ),
            )

            print(
                "DOMINANT TIMESTAMP :",
                cluster.get(
                    "dominant_timestamp"
                ),
            )

            print(
                "DOMINANT COUNT :",
                cluster.get(
                    "dominant_timestamp_count"
                ),
            )

    # -------------------------------------------------------------------------
    # Artifact
    # -------------------------------------------------------------------------

    artifact = {
        "artifact": {
            "name": (
                "ARUNDA_SNAPSHOT_FEATURE_MARKET_DATA_"
                "TEMPORAL_LINEAGE_FORENSIC_v0.1"
            ),
            "version": "v0.1",
            "mode": MODE,
            "database": DB_PATH,
            "feature_contract": FEATURE_CONTRACT_PATH,
            "network": NETWORK,
            "outcome": OUTCOME,
            "prediction": PREDICTION,
            "decision": DECISION,
        },

        "feature_input": {
            "feature_identity_count": len(
                feature_identities
            ),
            "unique_timestamps": (
                unique_feature_timestamps
            ),
            "identities": [
                {
                    "symbol": item["symbol"],
                    "raw_timestamp": item[
                        "raw_timestamp"
                    ],
                    "canonical_timestamp": item[
                        "canonical_timestamp"
                    ],
                }
                for item in feature_identities
            ],
        },

        "market_data_schema": schema,

        "market_data_inventory": {
            "rows_loaded": len(market_rows),
            "parseable_timestamp_rows": len(
                parseable_market_rows
            ),
            "symbol_count": len(market_index),
        },

        "temporal_coverage": {
            "exact_timestamp_matches": exact_count,
            "within_120_seconds": within_120,
            "within_300_seconds": within_300,
            "within_600_seconds": within_600,
            "no_market_symbol": no_symbol,
            "timestamp_unavailable": (
                timestamp_unavailable
            ),
            "minimum_delta_seconds": minimum_delta,
            "maximum_delta_seconds": maximum_delta,
            "mean_delta_seconds": mean_delta,
            "median_delta_seconds": median_delta,
        },

        "exact_match_records": [
            {
                "symbol": row["symbol"],
                "timestamp": row[
                    "canonical_timestamp"
                ],
                "record": row["record"],
                "fingerprint": (
                    build_record_fingerprint(
                        row["record"]
                    )
                ),
            }
            for row in exact_market_rows
        ],

        "exact_match_fingerprints": (
            unique_exact_fingerprints
        ),

        "execution_identity": {
            "candidate_columns": (
                discovered_execution_columns
            ),
            "evidence_rows": execution_evidence,
            "distinct_execution_fingerprints": (
                len(
                    distinct_execution_fingerprints
                )
            ),
        },

        "per_feature": per_feature,

        "forensic_conclusion": {
            "status": status,
            "predictive_claim": "NOT ESTABLISHED",
            "relationship_calculation": "NOT PERFORMED",

            "question": (
                "Does market_data contain records at the "
                "Feature Contract timestamp, and can those "
                "records identify the execution/run?"
            ),

            "answer": {
                "exact_market_data_timestamp_match": (
                    exact_count > 0
                ),
                "near_market_data_timestamp_match": (
                    within_600 > 0
                ),
                "execution_run_identity_columns_found": (
                    discovered_execution_columns
                ),
                "execution_run_identity_established": (
                    len(execution_evidence) > 0
                    and len(
                        distinct_execution_fingerprints
                    ) > 0
                ),
            },
        },
    }

    with open(
        ARTIFACT_PATH,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            artifact,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    artifact_sha256 = sha256_file(
        ARTIFACT_PATH
    )

    print("=" * 90)
    print("FORENSIC STATUS :", status)
    print("PREDICTIVE CLAIM : NOT ESTABLISHED")
    print(
        "RELATIONSHIP CALCULATION : NOT PERFORMED"
    )
    print(
        "Artifact :",
        ARTIFACT_PATH,
    )
    print(
        "SHA256   :",
        artifact_sha256,
    )
    print("=" * 90)


if __name__ == "__main__":
    main()