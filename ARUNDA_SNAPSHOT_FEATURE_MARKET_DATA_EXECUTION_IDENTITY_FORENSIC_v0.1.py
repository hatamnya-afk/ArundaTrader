import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict


# =============================================================================
# ARUNDA SNAPSHOT FEATURE -> MARKET DATA EXECUTION IDENTITY FORENSIC v0.1
# =============================================================================

DB_PATH = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")
FEATURE_CONTRACT_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)

ARTIFACT_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_MARKET_DATA_EXECUTION_IDENTITY_FORENSIC_v0.1.json"
)

MODE = "READ ONLY"
NETWORK = "FORBIDDEN"
OUTCOME = "NOT CALCULATED"
PREDICTION = "FORBIDDEN"
DECISION = "FORBIDDEN"

FEATURE_TABLE = "market_data"
FEATURE_TIMESTAMP = "2026-08-23T13:39:16.730073"

TOLERANCES = [0, 120, 300, 600]


# =============================================================================
# HELPERS
# =============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def parse_timestamp(value):
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def row_fingerprint(row_dict):
    return hashlib.sha256(
        canonical_json(row_dict).encode("utf-8")
    ).hexdigest()


def normalize_symbol(value):
    if value is None:
        return None

    text = str(value).strip().upper()

    return text if text else None


def safe_json_value(value):
    if isinstance(value, bytes):
        return value.hex()

    return value


# =============================================================================
# DATABASE
# =============================================================================

def open_database():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Explicitly read-only at SQLite level.
    conn.execute("PRAGMA query_only = ON")

    return conn


def get_table_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row["name"] for row in rows]


# =============================================================================
# FEATURE CONTRACT
# =============================================================================

def load_feature_contract():
    if not FEATURE_CONTRACT_PATH.exists():
        return None

    try:
        with FEATURE_CONTRACT_PATH.open(
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception:
        return None


def extract_feature_timestamp(contract):
    """
    The forensic target is deliberately fixed to the timestamp already
    established by the previous provenance/temporal-lineage forensic.

    The contract is inspected only for provenance metadata; no prediction
    or feature calculation is performed.
    """

    candidates = []

    def walk(obj, path="root"):
        if isinstance(obj, dict):
            for key, value in obj.items():

                key_lower = str(key).lower()

                if (
                    "timestamp" in key_lower
                    or key_lower in {
                        "time",
                        "datetime",
                        "as_of",
                        "asof",
                    }
                ):
                    if isinstance(value, str):
                        candidates.append(
                            {
                                "path": f"{path}.{key}",
                                "value": value,
                            }
                        )

                walk(value, f"{path}.{key}")

        elif isinstance(obj, list):
            for index, value in enumerate(obj):
                walk(value, f"{path}[{index}]")

    if contract is not None:
        walk(contract)

    return candidates


# =============================================================================
# SCHEMA DISCOVERY
# =============================================================================

def identify_columns(columns):
    lower_map = {
        str(col).lower(): col
        for col in columns
    }

    symbol_candidates = [
        "symbol",
        "normalized_symbol",
        "ticker",
        "asset",
    ]

    timestamp_candidates = [
        "timestamp",
        "datetime",
        "time",
        "created_at",
        "recorded_at",
        "as_of",
    ]

    symbol_column = None
    timestamp_column = None

    for candidate in symbol_candidates:
        if candidate in lower_map:
            symbol_column = lower_map[candidate]
            break

    for candidate in timestamp_candidates:
        if candidate in lower_map:
            timestamp_column = lower_map[candidate]
            break

    return symbol_column, timestamp_column


# =============================================================================
# EXECUTION IDENTITY
# =============================================================================

def classify_identity_columns(columns):
    """
    Identity candidates are discovered from the actual schema.

    We deliberately avoid assuming a specific architecture.
    """

    preferred = [
        "source",
        "engine",
        "engine_version",
        "run_id",
        "execution_id",
        "batch_id",
        "job_id",
        "process_id",
        "request_id",
        "collector",
        "collector_version",
        "provider",
        "exchange",
        "market_source",
        "pipeline",
        "pipeline_version",
        "created_at",
        "updated_at",
    ]

    result = []

    lower_map = {
        str(col).lower(): col
        for col in columns
    }

    for name in preferred:
        if name in lower_map:
            result.append(lower_map[name])

    return result


def build_execution_fingerprint(row_dict, identity_columns):
    identity_payload = {}

    for column in identity_columns:
        identity_payload[column] = row_dict.get(column)

    return row_fingerprint(identity_payload), identity_payload


# =============================================================================
# EXACT TEMPORAL RECORDS
# =============================================================================

def load_market_data(conn, columns, symbol_column, timestamp_column):
    sql = (
        f"SELECT * FROM market_data "
        f"WHERE {timestamp_column} IS NOT NULL"
    )

    rows = conn.execute(sql).fetchall()

    records = []

    for row in rows:
        row_dict = {
            column: safe_json_value(row[column])
            for column in columns
        }

        timestamp = parse_timestamp(
            row_dict.get(timestamp_column)
        )

        symbol = normalize_symbol(
            row_dict.get(symbol_column)
        )

        records.append(
            {
                "row": row_dict,
                "timestamp": timestamp,
                "symbol": symbol,
            }
        )

    return records


def calculate_temporal_delta(feature_dt, row_dt):
    if feature_dt is None or row_dt is None:
        return None

    return abs(
        (row_dt - feature_dt).total_seconds()
    )


# =============================================================================
# MAIN FORENSIC
# =============================================================================

def run_forensic():
    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> MARKET DATA "
        "EXECUTION IDENTITY FORENSIC v0.1"
    )
    print("=" * 90)
    print(f"Database        : {DB_PATH}")
    print(f"Feature Contract: {FEATURE_CONTRACT_PATH}")
    print(f"Mode            : {MODE}")
    print(f"Network         : {NETWORK}")
    print(f"Outcome         : {OUTCOME}")
    print(f"Prediction      : {PREDICTION}")
    print(f"Decision        : {DECISION}")
    print(
        "Target timestamp: "
        f"{FEATURE_TIMESTAMP}"
    )
    print(
        "Match Tolerance : "
        + " / ".join(str(x) for x in TOLERANCES)
        + " seconds"
    )
    print("-" * 90)

    feature_dt = parse_timestamp(FEATURE_TIMESTAMP)

    if feature_dt is None:
        raise RuntimeError(
            "Feature timestamp is not parseable."
        )

    contract = load_feature_contract()

    provenance_candidates = extract_feature_timestamp(
        contract
    )

    conn = open_database()

    try:
        columns = get_table_columns(
            conn,
            "market_data"
        )

        symbol_column, timestamp_column = identify_columns(
            columns
        )

        if symbol_column is None:
            raise RuntimeError(
                "Could not identify market_data symbol column."
            )

        if timestamp_column is None:
            raise RuntimeError(
                "Could not identify market_data timestamp column."
            )

        identity_columns = classify_identity_columns(
            columns
        )

        print("=" * 90)
        print("MARKET DATA SCHEMA")
        print("=" * 90)
        print(
            f"Symbol column    : {symbol_column}"
        )
        print(
            f"Timestamp column : {timestamp_column}"
        )

        print("=" * 90)
        print("EXECUTION IDENTITY COLUMNS")
        print("=" * 90)

        if identity_columns:
            for column in identity_columns:
                print(f"  {column}")
        else:
            print("  NONE DISCOVERED")

        records = load_market_data(
            conn,
            columns,
            symbol_column,
            timestamp_column,
        )

        parseable_records = [
            record
            for record in records
            if record["timestamp"] is not None
        ]

        symbols = sorted(
            {
                record["symbol"]
                for record in parseable_records
                if record["symbol"] is not None
            }
        )

        print("=" * 90)
        print("MARKET DATA TEMPORAL INVENTORY")
        print("=" * 90)
        print(
            f"Market_data rows loaded : {len(records)}"
        )
        print(
            f"Parseable timestamps    : "
            f"{len(parseable_records)}"
        )
        print(
            f"Market symbols          : "
            f"{len(symbols)}"
        )

        exact_records = []

        for record in parseable_records:
            if record["timestamp"] == feature_dt:
                exact_records.append(record)

        within = {}

        for tolerance in TOLERANCES:
            within[tolerance] = [
                record
                for record in parseable_records
                if (
                    calculate_temporal_delta(
                        feature_dt,
                        record["timestamp"],
                    )
                    is not None
                    and calculate_temporal_delta(
                        feature_dt,
                        record["timestamp"],
                    )
                    <= tolerance
                )
            ]

        print("=" * 90)
        print("FEATURE TIMESTAMP TEMPORAL COVERAGE")
        print("=" * 90)

        for tolerance in TOLERANCES:
            print(
                f"Within {tolerance:>4}s : "
                f"{len(within[tolerance])}"
            )

        print(
            f"Exact timestamp matches : "
            f"{len(exact_records)}"
        )

        # ---------------------------------------------------------------------
        # Exact records by symbol
        # ---------------------------------------------------------------------

        by_symbol = defaultdict(list)

        for record in exact_records:
            if record["symbol"] is not None:
                by_symbol[record["symbol"]].append(record)

        exact_symbols = sorted(by_symbol.keys())

        print(
            f"Exact-match symbols      : "
            f"{len(exact_symbols)}"
        )

        # ---------------------------------------------------------------------
        # Fingerprints
        # ---------------------------------------------------------------------

        row_fingerprints = []

        execution_fingerprints = []

        execution_payloads = []

        for record in exact_records:

            row_fp = row_fingerprint(
                record["row"]
            )

            row_fingerprints.append(row_fp)

            exec_fp, exec_payload = (
                build_execution_fingerprint(
                    record["row"],
                    identity_columns,
                )
            )

            execution_fingerprints.append(
                exec_fp
            )

            execution_payloads.append(
                exec_payload
            )

        distinct_row_fingerprints = sorted(
            set(row_fingerprints)
        )

        distinct_execution_fingerprints = sorted(
            set(execution_fingerprints)
        )

        print("=" * 90)
        print("EXECUTION IDENTITY SUMMARY")
        print("=" * 90)
        print(
            f"Exact market_data rows       : "
            f"{len(exact_records)}"
        )
        print(
            f"Unique exact row fingerprints: "
            f"{len(distinct_row_fingerprints)}"
        )
        print(
            f"Execution identity columns   : "
            f"{', '.join(identity_columns) if identity_columns else 'NONE'}"
        )
        print(
            f"Distinct execution fingerprints: "
            f"{len(distinct_execution_fingerprints)}"
        )

        # ---------------------------------------------------------------------
        # Fingerprint counts
        # ---------------------------------------------------------------------

        row_fp_counts = Counter(
            row_fingerprints
        )

        execution_fp_counts = Counter(
            execution_fingerprints
        )

        # ---------------------------------------------------------------------
        # Per-symbol identity
        # ---------------------------------------------------------------------

        per_symbol = []

        print("=" * 90)
        print("PER-SYMBOL EXECUTION IDENTITY")
        print("=" * 90)

        for symbol in exact_symbols:

            symbol_records = by_symbol[symbol]

            symbol_row_fps = []
            symbol_exec_fps = []
            symbol_exec_payloads = []

            for record in symbol_records:

                row_fp = row_fingerprint(
                    record["row"]
                )

                exec_fp, exec_payload = (
                    build_execution_fingerprint(
                        record["row"],
                        identity_columns,
                    )
                )

                symbol_row_fps.append(row_fp)
                symbol_exec_fps.append(exec_fp)
                symbol_exec_payloads.append(
                    exec_payload
                )

            symbol_row_fp_counts = Counter(
                symbol_row_fps
            )

            symbol_exec_fp_counts = Counter(
                symbol_exec_fps
            )

            dominant_exec_fp, dominant_exec_count = (
                symbol_exec_fp_counts.most_common(1)[0]
            )

            dominant_exec_payload = (
                symbol_exec_payloads[
                    symbol_exec_fps.index(
                        dominant_exec_fp
                    )
                ]
            )

            symbol_result = {
                "symbol": symbol,
                "exact_row_count": len(symbol_records),
                "distinct_row_fingerprints": len(
                    set(symbol_row_fps)
                ),
                "distinct_execution_fingerprints": len(
                    set(symbol_exec_fps)
                ),
                "dominant_execution_fingerprint":
                    dominant_exec_fp,
                "dominant_execution_count":
                    dominant_exec_count,
                "dominant_execution_payload":
                    dominant_exec_payload,
            }

            per_symbol.append(symbol_result)

            print(f"SYMBOL : {symbol}")
            print(
                f"  EXACT ROWS : "
                f"{len(symbol_records)}"
            )
            print(
                f"  DISTINCT ROW FINGERPRINTS : "
                f"{len(set(symbol_row_fps))}"
            )
            print(
                f"  DISTINCT EXECUTION FINGERPRINTS : "
                f"{len(set(symbol_exec_fps))}"
            )
            print(
                f"  DOMINANT EXECUTION FINGERPRINT : "
                f"{dominant_exec_fp}"
            )
            print(
                f"  DOMINANT EXECUTION COUNT : "
                f"{dominant_exec_count}"
            )

            if identity_columns:
                for key, value in dominant_exec_payload.items():
                    print(
                        f"  {key} : {value}"
                    )

            print("-" * 90)

        # ---------------------------------------------------------------------
        # Cross-symbol consistency
        # ---------------------------------------------------------------------

        cross_symbol_execution_fps = []

        for item in per_symbol:
            cross_symbol_execution_fps.append(
                item[
                    "dominant_execution_fingerprint"
                ]
            )

        distinct_cross_symbol_execution = sorted(
            set(cross_symbol_execution_fps)
        )

        all_symbols_same_execution_identity = (
            len(distinct_cross_symbol_execution) == 1
            and len(per_symbol) > 0
        )

        print("=" * 90)
        print("CROSS-SYMBOL EXECUTION IDENTITY")
        print("=" * 90)

        print(
            "Distinct dominant execution identities : "
            f"{len(distinct_cross_symbol_execution)}"
        )

        print(
            "All exact-match symbols share one "
            "execution identity : "
            f"{all_symbols_same_execution_identity}"
        )

        # ---------------------------------------------------------------------
        # Determine forensic status
        # ---------------------------------------------------------------------

        if not exact_records:

            forensic_status = (
                "NO_MARKET_DATA_EXECUTION_IDENTITY"
            )

        elif not identity_columns:

            forensic_status = (
                "MARKET_DATA_TEMPORAL_MATCH_"
                "IDENTITY_COLUMNS_UNAVAILABLE"
            )

        elif len(distinct_execution_fingerprints) == 1:

            forensic_status = (
                "MARKET_DATA_EXECUTION_IDENTITY_"
                "ESTABLISHED"
            )

        else:

            forensic_status = (
                "MARKET_DATA_EXECUTION_IDENTITY_"
                "AMBIGUOUS"
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
            "RELATIONSHIP CALCULATION : "
            "NOT PERFORMED"
        )

        # ---------------------------------------------------------------------
        # Artifact
        # ---------------------------------------------------------------------

        artifact = {
            "forensic": {
                "name":
                    "ARUNDA SNAPSHOT FEATURE -> "
                    "MARKET DATA EXECUTION IDENTITY "
                    "FORENSIC",
                "version": "v0.1",
                "mode": MODE,
                "network": NETWORK,
                "outcome": OUTCOME,
                "prediction": PREDICTION,
                "decision": DECISION,
            },

            "database": str(DB_PATH),

            "feature_contract": str(
                FEATURE_CONTRACT_PATH
            ),

            "feature_timestamp": FEATURE_TIMESTAMP,

            "feature_timestamp_utc":
                feature_dt.isoformat(),

            "feature_timestamp_contract_candidates":
                provenance_candidates,

            "schema": {
                "symbol_column":
                    symbol_column,
                "timestamp_column":
                    timestamp_column,
                "all_columns":
                    columns,
            },

            "execution_identity_columns":
                identity_columns,

            "inventory": {
                "market_data_rows_loaded":
                    len(records),
                "parseable_timestamp_rows":
                    len(parseable_records),
                "market_symbols":
                    len(symbols),
            },

            "temporal_coverage": {
                "exact_timestamp_matches":
                    len(exact_records),
                "within_120_seconds":
                    len(within[120]),
                "within_300_seconds":
                    len(within[300]),
                "within_600_seconds":
                    len(within[600]),
            },

            "exact_match_summary": {
                "exact_rows":
                    len(exact_records),
                "unique_row_fingerprints":
                    len(distinct_row_fingerprints),
                "unique_execution_fingerprints":
                    len(
                        distinct_execution_fingerprints
                    ),
                "execution_fingerprints":
                    distinct_execution_fingerprints,
                "all_symbols_same_execution_identity":
                    all_symbols_same_execution_identity,
            },

            "execution_fingerprint_counts": {
                fp: count
                for fp, count in
                execution_fp_counts.items()
            },

            "row_fingerprint_counts": {
                fp: count
                for fp, count in
                row_fp_counts.items()
            },

            "per_symbol": per_symbol,

            "forensic_status":
                forensic_status,

            "predictive_claim":
                "NOT ESTABLISHED",

            "relationship_calculation":
                "NOT PERFORMED",
        }

        with ARTIFACT_PATH.open(
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

        artifact_hash = sha256_file(
            ARTIFACT_PATH
        )

        print(
            f"Artifact : {ARTIFACT_PATH}"
        )
        print(
            f"SHA256   : {artifact_hash}"
        )
        print("=" * 90)

        return artifact

    finally:
        conn.close()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    run_forensic()