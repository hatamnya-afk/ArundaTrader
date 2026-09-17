import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


# =============================================================================
# ARUNDA SNAPSHOT FEATURE TIMESTAMP PROVENANCE FORENSIC v0.1
# =============================================================================

DB_PATH = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")
FEATURE_CONTRACT_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
)

ARTIFACT_PATH = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_TIMESTAMP_PROVENANCE_FORENSIC_v0.1.json"
)

MODE = "READ ONLY"
NETWORK = "FORBIDDEN"
OUTCOME = "NOT CALCULATED"
PREDICTION = "FORBIDDEN"
DECISION = "FORBIDDEN"


# =============================================================================
# HELPERS
# =============================================================================

def canonical_utc(value):
    """
    Parse a timestamp without changing its semantic instant.

    Supports:
      - ISO-8601 with Z
      - ISO-8601 with timezone offset
      - ISO-8601 naive timestamp

    Naive timestamps are retained as naive wall-clock values and are NOT
    assigned an invented timezone.
    """
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))

        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc)

        return dt

    except Exception:
        return None


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):
    return [
        row[1]
        for row in conn.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()
    ]


def read_feature_contract():
    with FEATURE_CONTRACT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


# =============================================================================
# FEATURE CONTRACT TIMESTAMP EXTRACTION
# =============================================================================

def extract_feature_records(contract):
    """
    Locate feature records without assuming a single rigid contract layout.
    No values are fabricated.
    """

    candidates = []

    def walk(node, path="root"):
        if isinstance(node, dict):

            # Common record-like structure
            if (
                "asset_symbol" in node
                and "snapshot_timestamp" in node
            ):
                candidates.append(
                    {
                        "path": path,
                        "asset_symbol": node.get("asset_symbol"),
                        "snapshot_timestamp": node.get(
                            "snapshot_timestamp"
                        ),
                    }
                )

            # Alternative symbol field
            elif (
                "symbol" in node
                and "snapshot_timestamp" in node
            ):
                candidates.append(
                    {
                        "path": path,
                        "asset_symbol": node.get("symbol"),
                        "snapshot_timestamp": node.get(
                            "snapshot_timestamp"
                        ),
                    }
                )

            for key, value in node.items():
                walk(value, f"{path}.{key}")

        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(contract)

    return candidates


# =============================================================================
# DATABASE TIMESTAMP PROVENANCE DISCOVERY
# =============================================================================

PROVENANCE_TABLES = [
    "hunter_signals",
    "fusion_signals",
    "signal_outcomes",
    "market_data",
    "market_history",
    "market_state",
]


def discover_timestamp_rows(conn):
    results = {}

    for table in PROVENANCE_TABLES:

        if not table_exists(conn, table):
            results[table] = {
                "exists": False,
                "timestamp_columns": [],
                "rows": [],
            }
            continue

        columns = get_columns(conn, table)

        timestamp_columns = [
            c for c in columns
            if "timestamp" in c.lower()
            or c.lower() in {
                "created_at",
                "updated_at",
            }
        ]

        table_result = {
            "exists": True,
            "timestamp_columns": timestamp_columns,
            "rows": [],
        }

        if not timestamp_columns:
            results[table] = table_result
            continue

        # Read only timestamp/symbol identity columns.
        identity_columns = []

        for candidate in (
            "id",
            "asset",
            "symbol",
            "market",
            "signal_id",
            "snapshot_id",
        ):
            if candidate in columns:
                identity_columns.append(candidate)

        selected = identity_columns + timestamp_columns

        selected_sql = ", ".join(
            f'"{c}"' for c in selected
        )

        rows = conn.execute(
            f'''
            SELECT {selected_sql}
            FROM "{table}"
            ORDER BY rowid DESC
            LIMIT 5000
            '''
        ).fetchall()

        for row in rows:
            table_result["rows"].append(
                dict(zip(selected, row))
            )

        results[table] = table_result

    return results


# =============================================================================
# PROVENANCE MATCH
# =============================================================================

def compare_feature_to_database(
    feature_records,
    database_rows,
):
    comparisons = []

    for feature in feature_records:

        symbol = feature.get("asset_symbol")
        raw_timestamp = feature.get("snapshot_timestamp")
        feature_dt = canonical_utc(raw_timestamp)

        record_result = {
            "asset_symbol": symbol,
            "feature_timestamp_raw": raw_timestamp,
            "feature_timestamp_parseable": feature_dt is not None,
            "sources": {},
        }

        for table, table_data in database_rows.items():

            if not table_data.get("exists"):
                record_result["sources"][table] = {
                    "status": "TABLE_NOT_PRESENT"
                }
                continue

            rows = table_data.get("rows", [])

            symbol_candidates = []

            for row in rows:

                row_symbol = (
                    row.get("asset")
                    or row.get("symbol")
                    or row.get("market")
                )

                if (
                    symbol is not None
                    and row_symbol is not None
                    and str(row_symbol).upper() == str(symbol).upper()
                ):
                    symbol_candidates.append(row)

            timestamp_matches = []

            nearest = None

            if feature_dt is not None:

                for row in symbol_candidates:

                    for timestamp_column in table_data.get(
                        "timestamp_columns", []
                    ):

                        raw_db_timestamp = row.get(timestamp_column)
                        db_dt = canonical_utc(raw_db_timestamp)

                        if db_dt is None:
                            continue

                        # Do not compare naive and aware timestamps.
                        if (
                            feature_dt.tzinfo is None
                            and db_dt.tzinfo is not None
                        ):
                            continue

                        if (
                            feature_dt.tzinfo is not None
                            and db_dt.tzinfo is None
                        ):
                            continue

                        delta = abs(
                            (
                                feature_dt - db_dt
                            ).total_seconds()
                        )

                        candidate = {
                            "timestamp_column": timestamp_column,
                            "timestamp_raw": raw_db_timestamp,
                            "delta_seconds": delta,
                            "row": row,
                        }

                        if nearest is None or (
                            delta < nearest["delta_seconds"]
                        ):
                            nearest = candidate

                        if delta == 0:
                            timestamp_matches.append(candidate)

            record_result["sources"][table] = {
                "symbol_rows": len(symbol_candidates),
                "exact_timestamp_matches": len(timestamp_matches),
                "nearest": nearest,
            }

        comparisons.append(record_result)

    return comparisons


# =============================================================================
# MAIN FORENSIC
# =============================================================================

def main():

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE TIMESTAMP PROVENANCE FORENSIC v0.1"
    )
    print("=" * 90)

    print(f"Database        : {DB_PATH}")
    print(f"Feature Contract: {FEATURE_CONTRACT_PATH}")
    print(f"Mode            : {MODE}")
    print(f"Network         : {NETWORK}")
    print(f"Outcome         : {OUTCOME}")
    print(f"Prediction      : {PREDICTION}")
    print(f"Decision        : {DECISION}")
    print("-" * 90)

    if not DB_PATH.exists():
        raise FileNotFoundError(DB_PATH)

    if not FEATURE_CONTRACT_PATH.exists():
        raise FileNotFoundError(FEATURE_CONTRACT_PATH)

    contract = read_feature_contract()

    feature_records = extract_feature_records(contract)

    print("=" * 90)
    print("FEATURE TIMESTAMP SOURCE")
    print("=" * 90)

    print(
        f"Feature identities : {len(feature_records)}"
    )

    feature_timestamps = sorted(
        {
            str(x.get("snapshot_timestamp"))
            for x in feature_records
            if x.get("snapshot_timestamp") is not None
        }
    )

    print(
        f"Unique timestamps  : {len(feature_timestamps)}"
    )

    for ts in feature_timestamps:
        print(f"  {ts}")

    # -------------------------------------------------------------------------
    # READ-ONLY DB
    # -------------------------------------------------------------------------

    conn = sqlite3.connect(
        f"file:{DB_PATH.as_posix()}?mode=ro",
        uri=True,
    )

    try:

        database_rows = discover_timestamp_rows(conn)

        comparisons = compare_feature_to_database(
            feature_records,
            database_rows,
        )

    finally:
        conn.close()

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------

    print("=" * 90)
    print("TIMESTAMP PROVENANCE COMPARISON")
    print("=" * 90)

    summary = {}

    for table in PROVENANCE_TABLES:

        table_result = database_rows.get(table, {})

        if not table_result.get("exists"):
            summary[table] = {
                "table_present": False,
                "symbol_rows": 0,
                "exact_timestamp_matches": 0,
                "nearest_delta_available": 0,
            }
            continue

        symbol_rows = 0
        exact_matches = 0
        nearest_available = 0

        for comparison in comparisons:

            source = comparison["sources"].get(table, {})

            symbol_rows += source.get("symbol_rows", 0)
            exact_matches += source.get(
                "exact_timestamp_matches", 0
            )

            if source.get("nearest") is not None:
                nearest_available += 1

        summary[table] = {
            "table_present": True,
            "symbol_rows": symbol_rows,
            "exact_timestamp_matches": exact_matches,
            "nearest_delta_available": nearest_available,
        }

        print(f"\nTABLE : {table}")
        print(
            f"  Symbol rows             : {symbol_rows}"
        )
        print(
            f"  Exact timestamp matches : {exact_matches}"
        )
        print(
            f"  Nearest timestamp found : {nearest_available}"
        )

    # -------------------------------------------------------------------------
    # HUNTER-SPECIFIC PROVENANCE
    # -------------------------------------------------------------------------

    hunter = summary.get(
        "hunter_signals",
        {
            "table_present": False,
            "symbol_rows": 0,
            "exact_timestamp_matches": 0,
            "nearest_delta_available": 0,
        },
    )

    hunter_contemporary = (
        hunter["exact_timestamp_matches"] > 0
    )

    if hunter_contemporary:
        status = "FEATURE_TIMESTAMP_HAS_HUNTER_PROVENANCE"
    elif hunter["nearest_delta_available"] > 0:
        status = "HUNTER_EXISTS_BUT_TEMPORAL_PROVENANCE_MISMATCH"
    else:
        status = "NO_HUNTER_TEMPORAL_PROVENANCE"

    # -------------------------------------------------------------------------
    # PER FEATURE OUTPUT
    # -------------------------------------------------------------------------

    print("=" * 90)
    print("PER-FEATURE TIMESTAMP PROVENANCE")
    print("=" * 90)

    for comparison in comparisons:

        symbol = comparison["asset_symbol"]
        timestamp = comparison["feature_timestamp_raw"]

        print(f"SYMBOL : {symbol}")
        print(f"  FEATURE TIMESTAMP : {timestamp}")

        source = comparison["sources"].get(
            "hunter_signals",
            {}
        )

        nearest = source.get("nearest")

        if nearest is None:
            print("  HUNTER : NONE")
        else:
            row = nearest["row"]

            hunter_id = row.get("id")

            hunter_ts = nearest.get(
                "timestamp_raw"
            )

            delta = nearest.get(
                "delta_seconds"
            )

            print(f"  HUNTER ID        : {hunter_id}")
            print(f"  HUNTER TIMESTAMP : {hunter_ts}")
            print(f"  DELTA SEC        : {delta}")

            if delta == 0:
                print(
                    "  STATUS           : EXACT_TEMPORAL_PROVENANCE"
                )
            else:
                print(
                    "  STATUS           : TEMPORAL_PROVENANCE_MISMATCH"
                )

        print("-" * 90)

    # -------------------------------------------------------------------------
    # ARTIFACT
    # -------------------------------------------------------------------------

    artifact = {
        "artifact": "ARUNDA_SNAPSHOT_FEATURE_TIMESTAMP_PROVENANCE_FORENSIC_v0.1",
        "database": str(DB_PATH),
        "feature_contract": str(FEATURE_CONTRACT_PATH),
        "mode": MODE,
        "network": NETWORK,
        "outcome": OUTCOME,
        "prediction": PREDICTION,
        "decision": DECISION,
        "feature_contract_sha256": sha256_file(
            FEATURE_CONTRACT_PATH
        ),
        "feature_identities": len(feature_records),
        "feature_timestamps": feature_timestamps,
        "database_summary": summary,
        "per_feature": comparisons,
        "forensic_status": status,
        "predictive_claim": "NOT_ESTABLISHED",
        "relationship_calculation": "NOT_PERFORMED",
        "database_modified": False,
    }

    payload = json.dumps(
        artifact,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")

    ARTIFACT_PATH.write_bytes(payload)

    artifact_sha256 = hashlib.sha256(payload).hexdigest()

    print("=" * 90)
    print("FORENSIC STATUS")
    print("=" * 90)
    print(f"FORENSIC STATUS : {status}")
    print("PREDICTIVE CLAIM : NOT ESTABLISHED")
    print("RELATIONSHIP CALCULATION : NOT PERFORMED")
    print(f"Artifact : {ARTIFACT_PATH}")
    print(f"SHA256   : {artifact_sha256}")
    print("=" * 90)


if __name__ == "__main__":
    main()