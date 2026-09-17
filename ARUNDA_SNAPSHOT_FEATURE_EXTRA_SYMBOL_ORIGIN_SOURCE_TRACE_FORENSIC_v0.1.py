import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

TARGET_SYMBOLS = ["4", "ASSET"]

INPUT_ARTIFACT = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_INPUT_EXTRA_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json"
)
SEMANTIC_ARTIFACT = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1.json"
)
ORIGIN_ARTIFACT = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_PROPAGATION_FORENSIC_v0.1.json"
)
FIRST_INSERTION_ARTIFACT = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_FIRST_INSERTION_FORENSIC_v0.1.json"
)
CMC_ARTIFACT = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_CMC_IDENTITY_FORENSIC_v0.1.json"
)
EXPECTED_STATUS_ARTIFACT = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_STATUS_FORENSIC_v0.1.json"
)
DECISION_ARTIFACT = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_DECISION_FORENSIC_v0.1.json"
)
CONTRACT_REPAIR_ARTIFACT = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DECISION_CONTRACT_REPAIR_FORENSIC_v0.1.json"
)
ORIGIN_PATH_ARTIFACT = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DECISION_CONTRACT_ORIGIN_PATH_FORENSIC_v0.1.json"
)

OUTPUT_ARTIFACT = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_SOURCE_TRACE_FORENSIC_v0.1.json"
)
OUTPUT_REPORT = Path(
    r"C:\Users\ASUS\ArundaTrader"
    r"\ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_SOURCE_TRACE_FORENSIC_v0.1.txt"
)

MODE = "READ ONLY"
NETWORK = "FORBIDDEN"
DATABASE_WRITE = "FORBIDDEN"
REPAIR = "FORBIDDEN"
PREDICTION = "FORBIDDEN"
DECISION = "FORENSIC STATUS ONLY"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    if not path.exists():
        return None

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_symbol(value):
    if value is None:
        return None

    if isinstance(value, str):
        return value.strip().upper()

    return str(value).strip().upper()


def flatten_strings(obj, path="$"):
    """
    Recursively collect string values with their JSON paths.
    """
    results = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            child_path = f"{path}.{key}"
            results.extend(flatten_strings(value, child_path))

    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            child_path = f"{path}[{idx}]"
            results.extend(flatten_strings(value, child_path))

    elif isinstance(obj, str):
        results.append((path, obj))

    return results


def find_symbol_paths(obj, symbol):
    """
    Find every JSON path whose scalar string value exactly matches
    the target symbol.
    """
    matches = []

    for path, value in flatten_strings(obj):
        if normalize_symbol(value) == normalize_symbol(symbol):
            matches.append(
                {
                    "json_path": path,
                    "value": value,
                }
            )

    return matches


def inspect_database(conn, symbol):
    cur = conn.cursor()

    tables = []
    table_rows = {}

    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    )

    for row in cur.fetchall():
        tables.append(row[0])

    for table in tables:
        try:
            cur.execute(f'PRAGMA table_info("{table}")')
            columns = [r[1] for r in cur.fetchall()]

            symbol_columns = [
                c for c in columns
                if c.lower() in {
                    "symbol",
                    "base_symbol",
                    "quote_symbol",
                    "asset_symbol",
                    "market_symbol",
                    "target_symbol",
                    "decision_symbol",
                    "source_symbol",
                    "input_symbol",
                    "normalized_symbol",
                    "canonical_symbol",
                }
            ]

            if not symbol_columns:
                continue

            matches = []

            for column in symbol_columns:
                try:
                    cur.execute(
                        f'''
                        SELECT COUNT(*)
                        FROM "{table}"
                        WHERE UPPER(CAST("{column}" AS TEXT)) = ?
                        ''',
                        (normalize_symbol(symbol),),
                    )

                    count = cur.fetchone()[0]

                    if count > 0:
                        matches.append(
                            {
                                "column": column,
                                "count": count,
                            }
                        )

                except Exception:
                    continue

            if matches:
                total = sum(x["count"] for x in matches)

                table_rows[table] = {
                    "matches": matches,
                    "total_symbol_matches": total,
                }

        except Exception:
            continue

    return table_rows


def inspect_table_schema(conn, table):
    cur = conn.cursor()

    try:
        cur.execute(f'PRAGMA table_info("{table}")')
        return [
            {
                "name": r[1],
                "type": r[2],
                "notnull": r[3],
                "default": r[4],
                "pk": r[5],
            }
            for r in cur.fetchall()
        ]
    except Exception:
        return []


def inspect_market_universe(conn, symbol):
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT *
            FROM market_universe
            WHERE UPPER(CAST(symbol AS TEXT)) = ?
            """,
            (normalize_symbol(symbol),),
        )

        rows = cur.fetchall()
        columns = [d[0] for d in cur.description]

        return [
            dict(zip(columns, row))
            for row in rows
        ]

    except Exception:
        return []


def inspect_source_like_columns(conn, symbol):
    """
    Search all DB tables for columns whose names suggest source/origin
    and return only rows where the target symbol is also present in the
    same table.

    This is forensic only. No INSERT/UPDATE/DELETE/DDL is executed.
    """
    cur = conn.cursor()
    results = []

    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    )

    tables = [r[0] for r in cur.fetchall()]

    source_tokens = (
        "source",
        "origin",
        "input",
        "engine",
        "provider",
        "feed",
        "provenance",
        "created_by",
        "generated_by",
        "pipeline",
        "producer",
    )

    symbol_tokens = (
        "symbol",
        "asset_symbol",
        "market_symbol",
        "base_symbol",
        "canonical_symbol",
        "normalized_symbol",
        "source_symbol",
        "input_symbol",
        "target_symbol",
    )

    for table in tables:
        schema = inspect_table_schema(conn, table)
        columns = [x["name"] for x in schema]

        symbol_columns = [
            c for c in columns
            if any(token in c.lower() for token in symbol_tokens)
        ]

        source_columns = [
            c for c in columns
            if any(token in c.lower() for token in source_tokens)
        ]

        if not symbol_columns or not source_columns:
            continue

        for symbol_column in symbol_columns:
            for source_column in source_columns:
                try:
                    cur.execute(
                        f'''
                        SELECT
                            "{symbol_column}",
                            "{source_column}",
                            COUNT(*)
                        FROM "{table}"
                        WHERE UPPER(CAST("{symbol_column}" AS TEXT)) = ?
                        GROUP BY
                            "{symbol_column}",
                            "{source_column}"
                        ORDER BY COUNT(*) DESC
                        ''',
                        (normalize_symbol(symbol),),
                    )

                    rows = cur.fetchall()

                    for row in rows:
                        results.append(
                            {
                                "table": table,
                                "symbol_column": symbol_column,
                                "source_column": source_column,
                                "symbol_value": row[0],
                                "source_value": row[1],
                                "count": row[2],
                            }
                        )

                except Exception:
                    continue

    return results


def artifact_trace(path, symbol):
    data = load_json(path)

    if data is None:
        return {
            "artifact": path.name,
            "exists": False,
            "records": 0,
            "symbol_paths": [],
        }

    matches = find_symbol_paths(data, symbol)

    return {
        "artifact": path.name,
        "exists": True,
        "records": len(data) if isinstance(data, list) else 1,
        "symbol_paths": matches,
    }


def build_trace(symbol, conn):
    artifact_paths = [
        INPUT_ARTIFACT,
        SEMANTIC_ARTIFACT,
        ORIGIN_ARTIFACT,
        FIRST_INSERTION_ARTIFACT,
        CMC_ARTIFACT,
        EXPECTED_STATUS_ARTIFACT,
        DECISION_ARTIFACT,
        CONTRACT_REPAIR_ARTIFACT,
        ORIGIN_PATH_ARTIFACT,
    ]

    artifact_traces = [
        artifact_trace(path, symbol)
        for path in artifact_paths
    ]

    db_tables = inspect_database(conn, symbol)
    market_universe_rows = inspect_market_universe(conn, symbol)
    source_columns = inspect_source_like_columns(conn, symbol)

    explicit_paths = []

    for artifact in artifact_traces:
        for item in artifact["symbol_paths"]:
            explicit_paths.append(
                {
                    "stage_artifact": artifact["artifact"],
                    "json_path": item["json_path"],
                    "value": item["value"],
                }
            )

    origin_values = sorted(
        {
            str(x["source_value"])
            for x in source_columns
            if x["source_value"] is not None
        }
    )

    source_trace_established = bool(
        explicit_paths or source_columns
    )

    if explicit_paths:
        trace_class = "EXPLICIT_ARTIFACT_SOURCE_TRACE_FOUND"
    elif source_columns:
        trace_class = "DATABASE_SOURCE_COLUMN_TRACE_FOUND"
    else:
        trace_class = "SOURCE_TRACE_NOT_ESTABLISHED"

    contradictions = []

    if not source_trace_established:
        contradictions.append("NO_SOURCE_TRACE_EVIDENCE")

    if not market_universe_rows:
        contradictions.append("MARKET_UNIVERSE_RECORD_NOT_FOUND")

    return {
        "target_symbol": symbol,
        "database_observed": bool(db_tables),
        "database_table_count": len(db_tables),
        "database_tables": sorted(db_tables.keys()),
        "database_total_symbol_matches": sum(
            x["total_symbol_matches"]
            for x in db_tables.values()
        ),
        "market_universe_records": market_universe_rows,
        "artifact_trace": artifact_traces,
        "explicit_origin_paths": explicit_paths,
        "database_source_column_trace": source_columns,
        "observed_source_values": origin_values,
        "source_trace_class": trace_class,
        "source_trace_established": source_trace_established,
        "contradictions": contradictions,
    }


def print_header():
    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL ORIGIN SOURCE TRACE "
        "FORENSIC v0.1"
    )
    print("=" * 90)
    print(f"Database       : {DB_PATH}")
    print(f"Input Provenance: {INPUT_ARTIFACT}")
    print(f"Semantic       : {SEMANTIC_ARTIFACT}")
    print(f"Origin         : {ORIGIN_ARTIFACT}")
    print(f"First Insertion: {FIRST_INSERTION_ARTIFACT}")
    print(f"CMC Identity   : {CMC_ARTIFACT}")
    print(f"Expected Status: {EXPECTED_STATUS_ARTIFACT}")
    print(f"Decision       : {DECISION_ARTIFACT}")
    print(f"Contract Repair: {CONTRACT_REPAIR_ARTIFACT}")
    print(f"Origin Path    : {ORIGIN_PATH_ARTIFACT}")
    print(f"Mode           : {MODE}")
    print(f"Network        : {NETWORK}")
    print(f"Database Write : {DATABASE_WRITE}")
    print(f"Repair         : {REPAIR}")
    print(f"Prediction     : {PREDICTION}")
    print(f"Decision       : {DECISION}")
    print("-" * 90)
    print()


def print_trace(result):
    symbol = result["target_symbol"]

    print("=" * 90)
    print(f"SYMBOL : {symbol}")
    print("=" * 90)

    print(
        f"DATABASE OBSERVED     : "
        f"{result['database_observed']}"
    )
    print(
        f"DATABASE TABLE COUNT  : "
        f"{result['database_table_count']}"
    )
    print(
        f"DATABASE TOTAL MATCHES: "
        f"{result['database_total_symbol_matches']}"
    )

    print()
    print("DATABASE TABLES :")

    for table in result["database_tables"]:
        print(f"  - {table}")

    print()
    print("MARKET_UNIVERSE RECORDS :")

    if not result["market_universe_records"]:
        print("  - None")
    else:
        for row in result["market_universe_records"]:
            safe = {
                k: row.get(k)
                for k in (
                    "id",
                    "cmc_id",
                    "name",
                    "symbol",
                    "slug",
                    "cmc_rank",
                    "source",
                    "engine",
                    "is_active",
                    "date_added",
                    "first_seen",
                    "last_updated",
                )
                if k in row
            }
            print(f"  - {safe}")

    print()
    print("ARTIFACT SOURCE TRACE")
    print("-" * 90)

    for artifact in result["artifact_trace"]:
        print(f"ARTIFACT : {artifact['artifact']}")
        print(f"EXISTS   : {artifact['exists']}")
        print(f"MATCHES  : {len(artifact['symbol_paths'])}")

        if artifact["symbol_paths"]:
            for item in artifact["symbol_paths"]:
                print(
                    f"  PATH : {item['json_path']} "
                    f"| VALUE : {item['value']}"
                )
        else:
            print("  PATH : None")

        print("-" * 90)

    print()
    print("EXPLICIT ORIGIN PATHS")
    if result["explicit_origin_paths"]:
        for item in result["explicit_origin_paths"]:
            print(
                f"  - {item['stage_artifact']} :: "
                f"{item['json_path']} = {item['value']}"
            )
    else:
        print("  - None")

    print()
    print("DATABASE SOURCE COLUMN TRACE")

    if result["database_source_column_trace"]:
        for item in result["database_source_column_trace"]:
            print(
                f"  - TABLE={item['table']} "
                f"| SYMBOL_COLUMN={item['symbol_column']} "
                f"| SOURCE_COLUMN={item['source_column']} "
                f"| SYMBOL={item['symbol_value']} "
                f"| SOURCE={item['source_value']} "
                f"| COUNT={item['count']}"
            )
    else:
        print("  - None")

    print()
    print("OBSERVED SOURCE VALUES")

    if result["observed_source_values"]:
        for value in result["observed_source_values"]:
            print(f"  - {value}")
    else:
        print("  - None")

    print()
    print(
        f"SOURCE TRACE CLASS       : "
        f"{result['source_trace_class']}"
    )
    print(
        f"SOURCE TRACE ESTABLISHED : "
        f"{result['source_trace_established']}"
    )

    print()
    print("CONTRADICTIONS")

    if result["contradictions"]:
        for item in result["contradictions"]:
            print(f"  - {item}")
    else:
        print("  - None")

    print()


def build_status(results):
    established = sum(
        1 for r in results
        if r["source_trace_established"]
    )

    unresolved = len(results) - established

    if established == len(results):
        status = "SOURCE_TRACE_ESTABLISHED_FOR_ALL_TARGETS"
    elif established > 0:
        status = "SOURCE_TRACE_PARTIALLY_ESTABLISHED"
    else:
        status = "ORIGIN_SOURCE_TRACE_NOT_ESTABLISHED"

    return {
        "target_symbols": len(results),
        "source_trace_established": established,
        "unresolved_targets": unresolved,
        "forensic_status": status,
    }


def main():
    print_header()

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    try:
        results = []

        for symbol in TARGET_SYMBOLS:
            result = build_trace(symbol, conn)
            results.append(result)
            print_trace(result)

        status = build_status(results)

        print("=" * 90)
        print("CROSS-SYMBOL SUMMARY")
        print("=" * 90)
        print(
            f"Target Symbols           : "
            f"{status['target_symbols']}"
        )
        print(
            f"Source Trace Established : "
            f"{status['source_trace_established']}"
        )
        print(
            f"Unresolved Targets       : "
            f"{status['unresolved_targets']}"
        )
        print("=" * 90)

        print()
        print("=" * 90)
        print("FORENSIC STATUS")
        print("=" * 90)
        print(
            f"FORENSIC STATUS : "
            f"{status['forensic_status']}"
        )
        print("PREDICTIVE CLAIM : NOT ESTABLISHED")
        print("RELATIONSHIP CALCULATION : NOT PERFORMED")
        print("DATABASE WRITE : NOT PERFORMED")
        print("DATABASE REPAIR : NOT PERFORMED")
        print("UNIVERSE REBUILD : NOT PERFORMED")
        print("SYMBOL DELETION : NOT PERFORMED")
        print("TRADING DECISION : NOT PERFORMED")
        print("=" * 90)

        artifact = {
            "artifact_version": "v0.1",
            "artifact_name": (
                "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_"
                "ORIGIN_SOURCE_TRACE_FORENSIC_v0.1"
            ),
            "generated_at_utc": utc_now(),
            "mode": MODE,
            "network": NETWORK,
            "database_write": DATABASE_WRITE,
            "repair": REPAIR,
            "prediction": PREDICTION,
            "decision": DECISION,
            "database": str(DB_PATH),
            "target_symbols": TARGET_SYMBOLS,
            "input_artifacts": {
                "input_provenance": str(INPUT_ARTIFACT),
                "semantic": str(SEMANTIC_ARTIFACT),
                "origin": str(ORIGIN_ARTIFACT),
                "first_insertion": str(FIRST_INSERTION_ARTIFACT),
                "cmc_identity": str(CMC_ARTIFACT),
                "expected_status": str(EXPECTED_STATUS_ARTIFACT),
                "decision": str(DECISION_ARTIFACT),
                "contract_repair": str(CONTRACT_REPAIR_ARTIFACT),
                "origin_path": str(ORIGIN_PATH_ARTIFACT),
            },
            "input_artifact_sha256": {
                "input_provenance": sha256_file(INPUT_ARTIFACT),
                "semantic": sha256_file(SEMANTIC_ARTIFACT),
                "origin": sha256_file(ORIGIN_ARTIFACT),
                "first_insertion": sha256_file(FIRST_INSERTION_ARTIFACT),
                "cmc_identity": sha256_file(CMC_ARTIFACT),
                "expected_status": sha256_file(
                    EXPECTED_STATUS_ARTIFACT
                ),
                "decision": sha256_file(DECISION_ARTIFACT),
                "contract_repair": sha256_file(
                    CONTRACT_REPAIR_ARTIFACT
                ),
                "origin_path": sha256_file(
                    ORIGIN_PATH_ARTIFACT
                ),
            },
            "status": status,
            "results": results,
            "safety_assertions": {
                "database_open_mode": "READ_ONLY_URI",
                "network_calls": 0,
                "insert": 0,
                "update": 0,
                "delete": 0,
                "alter": 0,
                "create": 0,
                "drop": 0,
                "vacuum": 0,
                "prediction": False,
                "trading_decision": False,
            },
        }

        OUTPUT_ARTIFACT.write_text(
            json.dumps(
                artifact,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        report_lines = []

        report_lines.append(
            "ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL "
            "ORIGIN SOURCE TRACE FORENSIC v0.1"
        )
        report_lines.append("=" * 90)
        report_lines.append(
            f"Database : {DB_PATH}"
        )
        report_lines.append(
            f"Mode : {MODE}"
        )
        report_lines.append(
            f"Network : {NETWORK}"
        )
        report_lines.append(
            f"Database Write : {DATABASE_WRITE}"
        )
        report_lines.append(
            f"Repair : {REPAIR}"
        )
        report_lines.append(
            f"Prediction : {PREDICTION}"
        )
        report_lines.append(
            f"Decision : {DECISION}"
        )
        report_lines.append("")

        for result in results:
            report_lines.append(
                f"SYMBOL : {result['target_symbol']}"
            )
            report_lines.append(
                f"DATABASE OBSERVED : "
                f"{result['database_observed']}"
            )
            report_lines.append(
                f"DATABASE TABLE COUNT : "
                f"{result['database_table_count']}"
            )
            report_lines.append(
                f"DATABASE TOTAL MATCHES : "
                f"{result['database_total_symbol_matches']}"
            )
            report_lines.append(
                f"SOURCE TRACE CLASS : "
                f"{result['source_trace_class']}"
            )
            report_lines.append(
                f"SOURCE TRACE ESTABLISHED : "
                f"{result['source_trace_established']}"
            )
            report_lines.append(
                "EXPLICIT ORIGIN PATHS : "
                + (
                    "; ".join(
                        x["stage_artifact"]
                        + " :: "
                        + x["json_path"]
                        for x in result[
                            "explicit_origin_paths"
                        ]
                    )
                    if result["explicit_origin_paths"]
                    else "None"
                )
            )
            report_lines.append(
                "OBSERVED SOURCE VALUES : "
                + (
                    ", ".join(
                        result["observed_source_values"]
                    )
                    if result["observed_source_values"]
                    else "None"
                )
            )
            report_lines.append(
                "CONTRADICTIONS : "
                + (
                    ", ".join(
                        result["contradictions"]
                    )
                    if result["contradictions"]
                    else "None"
                )
            )
            report_lines.append("-" * 90)

        report_lines.append(
            f"FORENSIC STATUS : "
            f"{status['forensic_status']}"
        )
        report_lines.append(
            "PREDICTIVE CLAIM : NOT ESTABLISHED"
        )
        report_lines.append(
            "RELATIONSHIP CALCULATION : NOT PERFORMED"
        )
        report_lines.append(
            "DATABASE WRITE : NOT PERFORMED"
        )
        report_lines.append(
            "DATABASE REPAIR : NOT PERFORMED"
        )
        report_lines.append(
            "UNIVERSE REBUILD : NOT PERFORMED"
        )
        report_lines.append(
            "SYMBOL DELETION : NOT PERFORMED"
        )
        report_lines.append(
            "TRADING DECISION : NOT PERFORMED"
        )

        OUTPUT_REPORT.write_text(
            "\n".join(report_lines),
            encoding="utf-8",
        )

        artifact_hash = sha256_file(OUTPUT_ARTIFACT)

        print()
        print("=" * 90)
        print("ARTIFACT")
        print("=" * 90)
        print(f"Artifact : {OUTPUT_ARTIFACT}")
        print(f"SHA256   : {artifact_hash}")
        print(f"Report   : {OUTPUT_REPORT}")
        print("=" * 90)

    finally:
        conn.close()


if __name__ == "__main__":
    main()