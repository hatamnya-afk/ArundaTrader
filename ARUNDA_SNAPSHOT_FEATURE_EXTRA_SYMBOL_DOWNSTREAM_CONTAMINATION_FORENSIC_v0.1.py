import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(r"C:\Users\ASUS\ArundaTrader")

DB = BASE / "arunda.db"

INPUT_ARTIFACTS = {
    "normalization": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json",
    "provenance": BASE / "ARUNDA_SNAPSHOT_FEATURE_INPUT_EXTRA_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json",
    "semantic": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1.json",
    "origin": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_PROPAGATION_FORENSIC_v0.1.json",
    "first_insertion": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_FIRST_INSERTION_FORENSIC_v0.1.json",
    "cmc_identity": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_CMC_IDENTITY_FORENSIC_v0.1.json",
    "expected_status": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_STATUS_FORENSIC_v0.1.json",
    "decision": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_DECISION_FORENSIC_v0.1.json",
    "contract_repair": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DECISION_CONTRACT_REPAIR_FORENSIC_v0.1.json",
    "source_trace": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_SOURCE_TRACE_FORENSIC_v0.1.json",
}

ARTIFACT = BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DOWNSTREAM_CONTAMINATION_FORENSIC_v0.1.json"
REPORT = BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DOWNSTREAM_CONTAMINATION_FORENSIC_v0.1.txt"

TARGET_SYMBOLS = ["4", "ASSET"]

DOWNSTREAM_EXCLUDED = {
    "market_universe",
    "market_history",
    "market_history_legacy",
    "market_microstructure",
    "market_opportunity",
    "market_state",
    "market_technical",
}

IDENTITY_COLUMNS = {
    "symbol",
    "base_symbol",
    "quote_symbol",
    "asset_symbol",
    "market_symbol",
    "coin_symbol",
    "pair_symbol",
    "instrument_symbol",
}

CMC_COLUMNS = {
    "cmc_id",
    "coinmarketcap_id",
    "coin_market_cap_id",
}

TIMESTAMP_COLUMNS = {
    "timestamp",
    "created_at",
    "updated_at",
    "date_added",
    "first_seen",
    "last_updated",
    "time",
    "datetime",
}


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def flatten_strings(obj):
    values = []

    if isinstance(obj, dict):
        for value in obj.values():
            values.extend(flatten_strings(value))

    elif isinstance(obj, list):
        for value in obj:
            values.extend(flatten_strings(value))

    elif isinstance(obj, str):
        values.append(obj)

    return values


def get_symbol_records(obj, symbol):
    records = []

    def walk(node):
        if isinstance(node, dict):
            symbol_values = []

            for key, value in node.items():
                key_l = str(key).lower()

                if key_l in {
                    "symbol",
                    "target_symbol",
                    "target_symbols",
                    "symbols",
                    "asset_symbol",
                }:
                    if isinstance(value, str):
                        symbol_values.append(value)

                    elif isinstance(value, list):
                        symbol_values.extend(
                            str(x) for x in value
                            if isinstance(x, (str, int, float))
                        )

            if symbol in symbol_values:
                records.append(node)

            for value in node.values():
                walk(value)

        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(obj)
    return records


def table_columns(conn, table):
    rows = conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    return [row[1] for row in rows]


def table_row_count(conn, table):
    return conn.execute(
        f'SELECT COUNT(*) FROM "{table}"'
    ).fetchone()[0]


def quote_identifier(value):
    return '"' + value.replace('"', '""') + '"'


def find_symbol_hits(conn, table, columns, symbol):
    hits = []

    candidate_columns = [
        c for c in columns
        if c.lower() in IDENTITY_COLUMNS
    ]

    for column in candidate_columns:
        qcol = quote_identifier(column)

        row = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {quote_identifier(table)}
            WHERE CAST({qcol} AS TEXT) = ?
            """,
            (symbol,),
        ).fetchone()

        count = int(row[0])

        if count > 0:
            sample_rows = conn.execute(
                f"""
                SELECT *
                FROM {quote_identifier(table)}
                WHERE CAST({qcol} AS TEXT) = ?
                LIMIT 5
                """,
                (symbol,),
            ).fetchall()

            hits.append({
                "column": column,
                "match_count": count,
                "sample_rows": [
                    list(r) for r in sample_rows
                ],
            })

    return hits


def find_cmc_hits(conn, table, columns, cmc_ids):
    hits = []

    candidate_columns = [
        c for c in columns
        if c.lower() in CMC_COLUMNS
    ]

    for column in candidate_columns:
        qcol = quote_identifier(column)

        for cmc_id in cmc_ids:
            row = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM {quote_identifier(table)}
                WHERE CAST({qcol} AS TEXT) = ?
                """,
                (str(cmc_id),),
            ).fetchone()

            count = int(row[0])

            if count > 0:
                hits.append({
                    "column": column,
                    "cmc_id": str(cmc_id),
                    "match_count": count,
                })

    return hits


def discover_cmc_ids(artifacts, symbol):
    ids = set()

    for name, obj in artifacts.items():
        if obj is None:
            continue

        records = get_symbol_records(obj, symbol)

        for record in records:
            for key, value in record.items():
                if str(key).lower() in CMC_COLUMNS:
                    if isinstance(value, (str, int, float)):
                        ids.add(str(value))

                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, (str, int, float)):
                                ids.add(str(item))

                elif str(key).lower() in {
                    "cmc_ids",
                    "coinmarketcap_ids",
                    "coin_market_cap_ids",
                }:
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, (str, int, float)):
                                ids.add(str(item))

    return sorted(ids)


def artifact_symbol_presence(artifacts, symbol):
    result = {}

    for name, obj in artifacts.items():
        if obj is None:
            result[name] = {
                "artifact_exists": False,
                "records_found": 0,
            }
            continue

        records = get_symbol_records(obj, symbol)

        result[name] = {
            "artifact_exists": True,
            "records_found": len(records),
        }

    return result


def main():
    print("=" * 90)
    print("ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL DOWNSTREAM CONTAMINATION FORENSIC v0.1")
    print("=" * 90)
    print(f"Database       : {DB}")

    for name, path in INPUT_ARTIFACTS.items():
        print(f"{name.replace('_', ' ').title():15}: {path}")

    print(f"Mode           : READ ONLY")
    print(f"Network        : FORBIDDEN")
    print(f"Database Write : FORBIDDEN")
    print(f"Repair         : FORBIDDEN")
    print(f"Prediction     : FORBIDDEN")
    print(f"Decision       : FORENSIC STATUS ONLY")
    print("-" * 90)

    artifacts = {}

    for name, path in INPUT_ARTIFACTS.items():
        artifacts[name] = load_json(path)

    conn = sqlite3.connect(
        f"file:{DB}?mode=ro",
        uri=True
    )

    conn.execute("PRAGMA query_only = ON")

    tables = [
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()
    ]

    downstream_tables = [
        t for t in tables
        if t not in DOWNSTREAM_EXCLUDED
        and not t.startswith("sqlite_")
    ]

    print()
    print("=" * 90)
    print("INPUT CONTRACT")
    print("=" * 90)
    print(f"Target Symbols    : {', '.join(TARGET_SYMBOLS)}")
    print(f"Database Tables   : {len(tables)}")
    print(f"Downstream Tables : {len(downstream_tables)}")

    results = {}

    for symbol in TARGET_SYMBOLS:
        print()
        print("=" * 90)
        print(f"SYMBOL : {symbol}")
        print("=" * 90)

        cmc_ids = discover_cmc_ids(artifacts, symbol)

        print(f"CMC IDS FROM ARTIFACT EVIDENCE : {', '.join(cmc_ids) if cmc_ids else 'None'}")

        artifact_presence = artifact_symbol_presence(
            artifacts,
            symbol
        )

        print()
        print("UPSTREAM ARTIFACT PRESENCE")
        for name, info in artifact_presence.items():
            print(
                f"  {name:20} "
                f"exists={info['artifact_exists']} "
                f"records={info['records_found']}"
            )

        downstream_hits = []
        downstream_cmc_hits = []

        for table in downstream_tables:
            columns = table_columns(conn, table)

            symbol_hits = find_symbol_hits(
                conn,
                table,
                columns,
                symbol
            )

            cmc_hits = find_cmc_hits(
                conn,
                table,
                columns,
                cmc_ids
            )

            if symbol_hits:
                downstream_hits.append({
                    "table": table,
                    "table_row_count": table_row_count(
                        conn,
                        table
                    ),
                    "symbol_hits": symbol_hits,
                    "cmc_hits": cmc_hits,
                })

            if cmc_hits:
                downstream_cmc_hits.append({
                    "table": table,
                    "cmc_hits": cmc_hits,
                })

        direct_symbol_contamination = len(
            downstream_hits
        ) > 0

        cmc_contamination = len(
            downstream_cmc_hits
        ) > 0

        contamination = (
            direct_symbol_contamination
            or cmc_contamination
        )

        if contamination:
            classification = "DOWNSTREAM_CONTAMINATION_OBSERVED"
        else:
            classification = "NO_DOWNSTREAM_CONTAMINATION_OBSERVED"

        print()
        print("DOWNSTREAM TRACE")
        print("-" * 90)

        if not downstream_hits:
            print("  Direct symbol propagation : NONE")

        else:
            for hit in downstream_hits:
                print(
                    f"  TABLE : {hit['table']}"
                )

                for sh in hit["symbol_hits"]:
                    print(
                        f"    SYMBOL COLUMN : {sh['column']}"
                    )
                    print(
                        f"    MATCH COUNT   : {sh['match_count']}"
                    )

                for ch in hit["cmc_hits"]:
                    print(
                        f"    CMC COLUMN    : {ch['column']}"
                    )
                    print(
                        f"    CMC ID        : {ch['cmc_id']}"
                    )
                    print(
                        f"    MATCH COUNT   : {ch['match_count']}"
                    )

        print()
        print("CMC ID DOWNSTREAM TRACE")
        print("-" * 90)

        if not downstream_cmc_hits:
            print("  CMC identity propagation : NONE")

        else:
            for hit in downstream_cmc_hits:
                print(
                    f"  TABLE : {hit['table']}"
                )

                for ch in hit["cmc_hits"]:
                    print(
                        f"    COLUMN      : {ch['column']}"
                    )
                    print(
                        f"    CMC ID      : {ch['cmc_id']}"
                    )
                    print(
                        f"    MATCH COUNT : {ch['match_count']}"
                    )

        print()
        print("CONTAMINATION ASSESSMENT")
        print("-" * 90)
        print(
            f"DIRECT SYMBOL CONTAMINATION : "
            f"{direct_symbol_contamination}"
        )
        print(
            f"CMC ID CONTAMINATION        : "
            f"{cmc_contamination}"
        )
        print(
            f"DOWNSTREAM CONTAMINATION    : "
            f"{contamination}"
        )
        print(
            f"CLASSIFICATION              : "
            f"{classification}"
        )

        results[symbol] = {
            "target_symbol": symbol,
            "cmc_ids": cmc_ids,
            "artifact_presence": artifact_presence,
            "downstream_symbol_hits": downstream_hits,
            "downstream_cmc_hits": downstream_cmc_hits,
            "direct_symbol_contamination": direct_symbol_contamination,
            "cmc_identity_contamination": cmc_contamination,
            "downstream_contamination": contamination,
            "classification": classification,
        }

    contaminated_targets = [
        symbol
        for symbol, result in results.items()
        if result["downstream_contamination"]
    ]

    clean_targets = [
        symbol
        for symbol, result in results.items()
        if not result["downstream_contamination"]
    ]

    unresolved_targets = [
        symbol
        for symbol, result in results.items()
        if not result["cmc_ids"]
    ]

    print()
    print("=" * 90)
    print("CROSS-SYMBOL SUMMARY")
    print("=" * 90)
    print(f"Target Symbols              : {len(TARGET_SYMBOLS)}")
    print(f"Contaminated Targets        : {len(contaminated_targets)}")
    print(f"Clean Targets               : {len(clean_targets)}")
    print(f"Unresolved CMC Identity     : {len(unresolved_targets)}")

    if contaminated_targets:
        print(
            "Contaminated Symbols       : "
            + ", ".join(contaminated_targets)
        )
    else:
        print("Contaminated Symbols       : None")

    print()
    print("=" * 90)
    print("FORENSIC STATUS")
    print("=" * 90)

    if unresolved_targets:
        forensic_status = "DOWNSTREAM_CONTAMINATION_TRACE_PARTIALLY_UNRESOLVED"
    elif contaminated_targets:
        forensic_status = "DOWNSTREAM_CONTAMINATION_OBSERVED"
    else:
        forensic_status = "NO_DOWNSTREAM_CONTAMINATION_OBSERVED"

    print(f"FORENSIC STATUS : {forensic_status}")
    print("PREDICTIVE CLAIM : NOT ESTABLISHED")
    print("RELATIONSHIP CALCULATION : NOT PERFORMED")
    print("DATABASE WRITE : NOT PERFORMED")
    print("DATABASE REPAIR : NOT PERFORMED")
    print("UNIVERSE REBUILD : NOT PERFORMED")
    print("SYMBOL DELETION : NOT PERFORMED")
    print("TRADING DECISION : NOT PERFORMED")

    output = {
        "artifact": ARTIFACT.name,
        "generated_at_utc": now_utc(),
        "database": str(DB),
        "mode": "READ ONLY",
        "network": "FORBIDDEN",
        "database_write": False,
        "repair": False,
        "prediction": False,
        "decision": False,
        "target_symbols": TARGET_SYMBOLS,
        "excluded_upstream_tables": sorted(
            DOWNSTREAM_EXCLUDED
        ),
        "downstream_tables_scanned": downstream_tables,
        "results": results,
        "cross_symbol_summary": {
            "target_symbols": len(TARGET_SYMBOLS),
            "contaminated_targets": len(contaminated_targets),
            "clean_targets": len(clean_targets),
            "unresolved_cmc_identity": len(unresolved_targets),
            "contaminated_symbols": contaminated_targets,
        },
        "forensic_status": forensic_status,
        "predictive_claim": "NOT ESTABLISHED",
        "relationship_calculation": "NOT PERFORMED",
        "database_write": "NOT PERFORMED",
        "database_repair": "NOT PERFORMED",
        "universe_rebuild": "NOT PERFORMED",
        "symbol_deletion": "NOT PERFORMED",
        "trading_decision": "NOT PERFORMED",
    }

    with open(
        ARTIFACT,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    report_lines = []

    report_lines.append(
        "ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL DOWNSTREAM CONTAMINATION FORENSIC v0.1"
    )
    report_lines.append("=" * 90)
    report_lines.append(
        f"Generated UTC : {output['generated_at_utc']}"
    )
    report_lines.append(
        f"Database      : {DB}"
    )
    report_lines.append(
        "Mode          : READ ONLY"
    )
    report_lines.append(
        "Network       : FORBIDDEN"
    )
    report_lines.append(
        "Database Write: FORBIDDEN"
    )
    report_lines.append("")

    for symbol, result in results.items():
        report_lines.append("=" * 90)
        report_lines.append(f"SYMBOL : {symbol}")
        report_lines.append("=" * 90)
        report_lines.append(
            f"CMC IDS : {', '.join(result['cmc_ids']) if result['cmc_ids'] else 'None'}"
        )
        report_lines.append(
            f"DOWNSTREAM CONTAMINATION : {result['downstream_contamination']}"
        )
        report_lines.append(
            f"CLASSIFICATION : {result['classification']}"
        )

        if result["downstream_symbol_hits"]:
            for hit in result["downstream_symbol_hits"]:
                report_lines.append(
                    f"TABLE : {hit['table']}"
                )
                for sh in hit["symbol_hits"]:
                    report_lines.append(
                        f"  {sh['column']} = {sh['match_count']}"
                    )

        if result["downstream_cmc_hits"]:
            for hit in result["downstream_cmc_hits"]:
                report_lines.append(
                    f"CMC TABLE : {hit['table']}"
                )
                for ch in hit["cmc_hits"]:
                    report_lines.append(
                        f"  {ch['column']} / {ch['cmc_id']} = {ch['match_count']}"
                    )

    report_lines.append("")
    report_lines.append("=" * 90)
    report_lines.append("CROSS-SYMBOL SUMMARY")
    report_lines.append("=" * 90)
    report_lines.append(
        f"Target Symbols          : {len(TARGET_SYMBOLS)}"
    )
    report_lines.append(
        f"Contaminated Targets    : {len(contaminated_targets)}"
    )
    report_lines.append(
        f"Clean Targets           : {len(clean_targets)}"
    )
    report_lines.append(
        f"Unresolved CMC Identity : {len(unresolved_targets)}"
    )
    report_lines.append("")
    report_lines.append("=" * 90)
    report_lines.append("FORENSIC STATUS")
    report_lines.append("=" * 90)
    report_lines.append(
        f"FORENSIC STATUS : {forensic_status}"
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

    with open(
        REPORT,
        "w",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(report_lines))

    artifact_hash = sha256_file(ARTIFACT)

    print()
    print("=" * 90)
    print("ARTIFACT")
    print("=" * 90)
    print(f"Artifact : {ARTIFACT}")
    print(f"SHA256   : {artifact_hash}")
    print(f"Report   : {REPORT}")
    print("=" * 90)

    conn.close()


if __name__ == "__main__":
    main()