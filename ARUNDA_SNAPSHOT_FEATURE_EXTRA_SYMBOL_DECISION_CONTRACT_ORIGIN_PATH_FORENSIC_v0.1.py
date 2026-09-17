import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


BASE = Path(r"C:\Users\ASUS\ArundaTrader")

DB_PATH = BASE / "arunda.db"

FILES = {
    "normalization": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json",
    "provenance": BASE / "ARUNDA_SNAPSHOT_FEATURE_INPUT_EXTRA_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json",
    "semantic": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1.json",
    "origin": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_PROPAGATION_FORENSIC_v0.1.json",
    "first_insertion": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_FIRST_INSERTION_FORENSIC_v0.1.json",
    "cmc_identity": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_CMC_IDENTITY_FORENSIC_v0.1.json",
    "expected_status": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_STATUS_FORENSIC_v0.1.json",
    "decision": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_DECISION_FORENSIC_v0.1.json",
    "contract_repair": BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DECISION_CONTRACT_REPAIR_FORENSIC_v0.1.json",
}

OUTPUT_JSON = BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DECISION_CONTRACT_ORIGIN_PATH_FORENSIC_v0.1.json"
OUTPUT_TXT = BASE / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DECISION_CONTRACT_ORIGIN_PATH_FORENSIC_v0.1.txt"

TARGET_SYMBOLS = ["4", "ASSET"]


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
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def norm(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    return value


def lower(value):
    if isinstance(value, str):
        return value.lower()
    return value


def recursive_find_symbol(obj, symbol):
    hits = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and value == symbol:
                hits.append((key, value))
            elif isinstance(value, (dict, list)):
                hits.extend(recursive_find_symbol(value, symbol))

    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                hits.extend(recursive_find_symbol(item, symbol))

    return hits


def recursive_collect_keys(obj, wanted):
    found = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            if lower(key) in wanted:
                found.append((key, value))
            if isinstance(value, (dict, list)):
                found.extend(recursive_collect_keys(value, wanted))

    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                found.extend(recursive_collect_keys(item, wanted))

    return found


def extract_values(obj, keys):
    values = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            if lower(key) in keys:
                if isinstance(value, list):
                    values.extend(value)
                else:
                    values.append(value)

            if isinstance(value, (dict, list)):
                values.extend(extract_values(value, keys))

    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                values.extend(extract_values(item, keys))

    return values


def unique_strings(values):
    out = []

    for value in values:
        if value is None:
            continue

        if isinstance(value, (str, int, float, bool)):
            text = str(value)
            if text not in out:
                out.append(text)

    return out


def find_symbol_records(obj, symbol):
    records = []

    if isinstance(obj, dict):
        direct_symbol = None

        for key in (
            "symbol",
            "target_symbol",
            "decision_symbol",
            "asset_symbol",
            "source_symbol",
        ):
            if key in obj and str(obj[key]) == symbol:
                direct_symbol = key
                break

        if direct_symbol is not None:
            records.append(obj)

        for value in obj.values():
            if isinstance(value, (dict, list)):
                records.extend(find_symbol_records(value, symbol))

    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                records.extend(find_symbol_records(item, symbol))

    return records


def extract_symbol_context(obj, symbol):
    records = find_symbol_records(obj, symbol)

    semantic_keys = {
        "semantic_class",
        "semantic_classes",
        "semantic",
        "classification",
    }

    origin_keys = {
        "origin_class",
        "origin_classes",
        "symbol_origin_class",
        "symbol_origin_classes",
        "decision_symbol_origin_class",
        "decision_symbol_origin_classes",
        "origin",
        "origins",
    }

    path_keys = {
        "origin_path",
        "origin_paths",
        "symbol_origin_path",
        "symbol_origin_paths",
        "decision_origin_path",
        "decision_origin_paths",
        "propagation_path",
        "propagation_paths",
    }

    semantic = []
    origin = []
    paths = []

    for record in records:
        semantic.extend(extract_values(record, semantic_keys))
        origin.extend(extract_values(record, origin_keys))
        paths.extend(extract_values(record, path_keys))

    if not records:
        semantic.extend(extract_values(obj, semantic_keys))
        origin.extend(extract_values(obj, origin_keys))
        paths.extend(extract_values(obj, path_keys))

    return {
        "records_found": len(records),
        "semantic_classes": unique_strings(semantic),
        "origin_classes": unique_strings(origin),
        "origin_paths": unique_strings(paths),
    }


def database_inventory():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    tables = cur.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' ORDER BY name"
    ).fetchall()

    table_names = [row[0] for row in tables]

    result = {
        "table_count": len(table_names),
        "tables": table_names,
        "symbols": {},
    }

    for symbol in TARGET_SYMBOLS:
        observed = []
        total_rows = 0

        for table in table_names:
            try:
                columns = cur.execute(
                    "PRAGMA table_info({})".format(
                        '"' + table.replace('"', '""') + '"'
                    )
                ).fetchall()

                column_names = [row[1] for row in columns]

                if "symbol" not in column_names:
                    continue

                quoted_table = '"' + table.replace('"', '""') + '"'

                row = cur.execute(
                    "SELECT COUNT(*) FROM {} WHERE symbol = ?".format(
                        quoted_table
                    ),
                    (symbol,),
                ).fetchone()

                count = int(row[0])

                if count > 0:
                    observed.append(
                        {
                            "table": table,
                            "rows": count,
                        }
                    )
                    total_rows += count

            except Exception:
                continue

        result["symbols"][symbol] = {
            "observed": len(observed) > 0,
            "table_count": len(observed),
            "total_rows": total_rows,
            "tables": [x["table"] for x in observed],
        }

    conn.close()
    return result


def build_origin_path(symbol, artifacts, db_info):
    semantic_ctx = extract_symbol_context(
        artifacts["semantic"],
        symbol,
    )

    origin_ctx = extract_symbol_context(
        artifacts["origin"],
        symbol,
    )

    decision_ctx = extract_symbol_context(
        artifacts["decision"],
        symbol,
    )

    repair_ctx = extract_symbol_context(
        artifacts["contract_repair"],
        symbol,
    )

    provenance_ctx = extract_symbol_context(
        artifacts["provenance"],
        symbol,
    )

    first_ctx = extract_symbol_context(
        artifacts["first_insertion"],
        symbol,
    )

    cmc_ctx = extract_symbol_context(
        artifacts["cmc_identity"],
        symbol,
    )

    status_ctx = extract_symbol_context(
        artifacts["expected_status"],
        symbol,
    )

    stages = [
        {
            "stage": "INPUT_PROVENANCE",
            "artifact": FILES["provenance"].name,
            "records_found": provenance_ctx["records_found"],
            "semantic_classes": provenance_ctx["semantic_classes"],
            "origin_classes": provenance_ctx["origin_classes"],
            "origin_paths": provenance_ctx["origin_paths"],
        },
        {
            "stage": "SEMANTIC",
            "artifact": FILES["semantic"].name,
            "records_found": semantic_ctx["records_found"],
            "semantic_classes": semantic_ctx["semantic_classes"],
            "origin_classes": semantic_ctx["origin_classes"],
            "origin_paths": semantic_ctx["origin_paths"],
        },
        {
            "stage": "ORIGIN_PROPAGATION",
            "artifact": FILES["origin"].name,
            "records_found": origin_ctx["records_found"],
            "semantic_classes": origin_ctx["semantic_classes"],
            "origin_classes": origin_ctx["origin_classes"],
            "origin_paths": origin_ctx["origin_paths"],
        },
        {
            "stage": "FIRST_INSERTION",
            "artifact": FILES["first_insertion"].name,
            "records_found": first_ctx["records_found"],
            "semantic_classes": first_ctx["semantic_classes"],
            "origin_classes": first_ctx["origin_classes"],
            "origin_paths": first_ctx["origin_paths"],
        },
        {
            "stage": "CMC_IDENTITY",
            "artifact": FILES["cmc_identity"].name,
            "records_found": cmc_ctx["records_found"],
            "semantic_classes": cmc_ctx["semantic_classes"],
            "origin_classes": cmc_ctx["origin_classes"],
            "origin_paths": cmc_ctx["origin_paths"],
        },
        {
            "stage": "EXPECTED_UNIVERSE_STATUS",
            "artifact": FILES["expected_status"].name,
            "records_found": status_ctx["records_found"],
            "semantic_classes": status_ctx["semantic_classes"],
            "origin_classes": status_ctx["origin_classes"],
            "origin_paths": status_ctx["origin_paths"],
        },
        {
            "stage": "DECISION",
            "artifact": FILES["decision"].name,
            "records_found": decision_ctx["records_found"],
            "semantic_classes": decision_ctx["semantic_classes"],
            "origin_classes": decision_ctx["origin_classes"],
            "origin_paths": decision_ctx["origin_paths"],
        },
        {
            "stage": "CONTRACT_REPAIR",
            "artifact": FILES["contract_repair"].name,
            "records_found": repair_ctx["records_found"],
            "semantic_classes": repair_ctx["semantic_classes"],
            "origin_classes": repair_ctx["origin_classes"],
            "origin_paths": repair_ctx["origin_paths"],
        },
    ]

    all_origin_classes = []

    for stage in stages:
        for value in stage["origin_classes"]:
            if value not in all_origin_classes:
                all_origin_classes.append(value)

    all_origin_paths = []

    for stage in stages:
        for value in stage["origin_paths"]:
            if value not in all_origin_paths:
                all_origin_paths.append(value)

    db = db_info["symbols"][symbol]

    contradictions = []

    if len(all_origin_classes) == 0:
        contradictions.append("ORIGIN_CLASS_NOT_ESTABLISHED")

    decision_origins = decision_ctx["origin_classes"]
    repair_origins = repair_ctx["origin_classes"]

    if len(decision_origins) == 0:
        contradictions.append("DECISION_ORIGIN_CLASS_MISSING")

    if len(repair_origins) == 0:
        contradictions.append("REPAIR_ORIGIN_CLASS_MISSING")

    if len(origin_ctx["origin_classes"]) == 0:
        contradictions.append("ORIGIN_PROPAGATION_CLASS_MISSING")

    if len(all_origin_paths) == 0:
        contradictions.append("ORIGIN_PATH_NOT_EXPLICITLY_ESTABLISHED")

    path_established = (
        len(all_origin_classes) > 0
        and len(origin_ctx["origin_classes"]) > 0
    )

    return {
        "symbol": symbol,
        "database": db,
        "semantic_classes_observed": semantic_ctx["semantic_classes"],
        "origin_classes_observed": all_origin_classes,
        "explicit_origin_paths": all_origin_paths,
        "decision_origin_classes": decision_origins,
        "repair_origin_classes": repair_origins,
        "origin_propagation_classes": origin_ctx["origin_classes"],
        "stages": stages,
        "origin_path_established": path_established,
        "contradictions": contradictions,
        "consistency": len(contradictions) == 0,
    }


def print_stage(stage):
    print("-" * 90)
    print("STAGE :", stage["stage"])
    print("ARTIFACT :", stage["artifact"])
    print("RECORDS FOUND :", stage["records_found"])

    semantic_text = ", ".join(stage["semantic_classes"])
    origin_text = ", ".join(stage["origin_classes"])
    path_text = ", ".join(stage["origin_paths"])

    print("SEMANTIC CLASSES :", semantic_text if semantic_text else "None")
    print("ORIGIN CLASSES   :", origin_text if origin_text else "None")
    print("ORIGIN PATHS     :", path_text if path_text else "None")


def main():
    print("=" * 90)
    print("ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL DECISION CONTRACT ORIGIN PATH FORENSIC v0.1")
    print("=" * 90)
    print("Database       :", DB_PATH)
    print("Normalization  :", FILES["normalization"])
    print("Provenance     :", FILES["provenance"])
    print("Semantic       :", FILES["semantic"])
    print("Origin         :", FILES["origin"])
    print("First Insertion:", FILES["first_insertion"])
    print("CMC Identity   :", FILES["cmc_identity"])
    print("Expected Status:", FILES["expected_status"])
    print("Decision       :", FILES["decision"])
    print("Contract Repair:", FILES["contract_repair"])
    print("Mode           : READ ONLY")
    print("Network        : FORBIDDEN")
    print("Database Write : FORBIDDEN")
    print("Repair         : FORBIDDEN")
    print("Prediction     : FORBIDDEN")
    print("Decision       : FORENSIC STATUS ONLY")
    print("-" * 90)

    artifacts = {}

    for key, path in FILES.items():
        artifacts[key] = load_json(path)

    db_info = database_inventory()

    expected_universe = None

    normalization = artifacts["normalization"]

    if isinstance(normalization, dict):
        possible_keys = [
            "expected_universe",
            "expected_universe_count",
            "universe_size",
            "count",
        ]

        for key in possible_keys:
            if key in normalization:
                expected_universe = normalization[key]
                break

    print()
    print("=" * 90)
    print("INPUT CONTRACT")
    print("=" * 90)
    print("Expected Universe :", expected_universe)
    print("Target Symbols    :", ", ".join(TARGET_SYMBOLS))

    results = {}

    for symbol in TARGET_SYMBOLS:
        result = build_origin_path(
            symbol,
            artifacts,
            db_info,
        )

        results[symbol] = result

        print()
        print("=" * 90)
        print("SYMBOL :", symbol)
        print("=" * 90)

        db = result["database"]

        print("DATABASE OBSERVED     :", db["observed"])
        print("DATABASE TABLE COUNT  :", db["table_count"])
        print("DATABASE TOTAL ROWS   :", db["total_rows"])
        print("DATABASE TABLES       :", ", ".join(db["tables"]))

        print()
        print("SEMANTIC CLASSES OBSERVED :")
        if result["semantic_classes_observed"]:
            for value in result["semantic_classes_observed"]:
                print("  -", value)
        else:
            print("  - None")

        print()
        print("ORIGIN CLASSES OBSERVED :")
        if result["origin_classes_observed"]:
            for value in result["origin_classes_observed"]:
                print("  -", value)
        else:
            print("  - None")

        print()
        print("EXPLICIT ORIGIN PATHS :")
        if result["explicit_origin_paths"]:
            for value in result["explicit_origin_paths"]:
                print("  -", value)
        else:
            print("  - None")

        print()
        print("DECISION ORIGIN CLASSES :")
        if result["decision_origin_classes"]:
            for value in result["decision_origin_classes"]:
                print("  -", value)
        else:
            print("  - None")

        print()
        print("REPAIR ORIGIN CLASSES :")
        if result["repair_origin_classes"]:
            for value in result["repair_origin_classes"]:
                print("  -", value)
        else:
            print("  - None")

        print()
        print("ORIGIN PROPAGATION CLASSES :")
        if result["origin_propagation_classes"]:
            for value in result["origin_propagation_classes"]:
                print("  -", value)
        else:
            print("  - None")

        print()
        print("UPSTREAM ORIGIN PATH")
        print("-" * 90)

        for stage in result["stages"]:
            print_stage(stage)

        print()
        print("ORIGIN PATH ESTABLISHED :", result["origin_path_established"])
        print("CONSISTENCY             :", result["consistency"])

        if result["contradictions"]:
            print("CONTRADICTIONS :")
            for contradiction in result["contradictions"]:
                print("  -", contradiction)
        else:
            print("CONTRADICTIONS : NONE")

    established = sum(
        1 for value in results.values()
        if value["origin_path_established"]
    )

    consistent = sum(
        1 for value in results.values()
        if value["consistency"]
    )

    unresolved = len(TARGET_SYMBOLS) - established

    if established == len(TARGET_SYMBOLS) and consistent == len(TARGET_SYMBOLS):
        forensic_status = "DECISION_ORIGIN_PATH_ESTABLISHED"
    elif established == len(TARGET_SYMBOLS):
        forensic_status = "DECISION_ORIGIN_PATH_ESTABLISHED_WITH_CONTRACT_INCONSISTENCIES"
    elif established > 0:
        forensic_status = "PARTIAL_DECISION_ORIGIN_PATH_ESTABLISHED"
    else:
        forensic_status = "DECISION_ORIGIN_PATH_NOT_ESTABLISHED"

    artifact = {
        "artifact_version": "v0.1",
        "artifact_name": "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DECISION_CONTRACT_ORIGIN_PATH_FORENSIC_v0.1",
        "generated_at_utc": now_utc(),
        "mode": "READ_ONLY",
        "network": "FORBIDDEN",
        "database_write": False,
        "repair": False,
        "prediction": False,
        "trading_decision": False,
        "database": str(DB_PATH),
        "expected_universe": expected_universe,
        "target_symbols": TARGET_SYMBOLS,
        "database_inventory": db_info,
        "input_artifacts": {},
        "results": results,
        "summary": {
            "target_symbols": len(TARGET_SYMBOLS),
            "origin_paths_established": established,
            "consistent_targets": consistent,
            "unresolved_targets": unresolved,
            "forensic_status": forensic_status,
        },
        "forensic_status": forensic_status,
        "predictive_claim": "NOT_ESTABLISHED",
        "relationship_calculation": "NOT_PERFORMED",
        "database_write": "NOT_PERFORMED",
        "database_repair": "NOT_PERFORMED",
        "universe_rebuild": "NOT_PERFORMED",
        "symbol_deletion": "NOT_PERFORMED",
        "trading_decision": "NOT_PERFORMED",
    }

    for key, path in FILES.items():
        artifact["input_artifacts"][key] = {
            "path": str(path),
            "exists": path.exists(),
            "sha256": sha256_file(path) if path.exists() else None,
        }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(
            artifact,
            f,
            ensure_ascii=False,
            indent=2,
        )

    report_lines = []

    report_lines.append("=" * 90)
    report_lines.append(
        "ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL DECISION CONTRACT ORIGIN PATH FORENSIC v0.1"
    )
    report_lines.append("=" * 90)
    report_lines.append("Database       : " + str(DB_PATH))
    report_lines.append("Mode           : READ ONLY")
    report_lines.append("Network        : FORBIDDEN")
    report_lines.append("Database Write : FORBIDDEN")
    report_lines.append("Repair         : FORBIDDEN")
    report_lines.append("Prediction     : FORBIDDEN")
    report_lines.append("Decision       : FORENSIC STATUS ONLY")
    report_lines.append("-" * 90)

    for symbol, result in results.items():
        report_lines.append("")
        report_lines.append("SYMBOL : " + symbol)
        report_lines.append(
            "DATABASE OBSERVED : " +
            str(result["database"]["observed"])
        )
        report_lines.append(
            "DATABASE TABLE COUNT : " +
            str(result["database"]["table_count"])
        )
        report_lines.append(
            "DATABASE TOTAL ROWS : " +
            str(result["database"]["total_rows"])
        )

        report_lines.append(
            "SEMANTIC CLASSES : " +
            (", ".join(result["semantic_classes_observed"])
             if result["semantic_classes_observed"]
             else "None")
        )

        report_lines.append(
            "ORIGIN CLASSES : " +
            (", ".join(result["origin_classes_observed"])
             if result["origin_classes_observed"]
             else "None")
        )

        report_lines.append(
            "EXPLICIT ORIGIN PATHS : " +
            (", ".join(result["explicit_origin_paths"])
             if result["explicit_origin_paths"]
             else "None")
        )

        report_lines.append(
            "ORIGIN PATH ESTABLISHED : " +
            str(result["origin_path_established"])
        )

        report_lines.append(
            "CONSISTENCY : " +
            str(result["consistency"])
        )

        if result["contradictions"]:
            report_lines.append("CONTRADICTIONS :")
            for item in result["contradictions"]:
                report_lines.append("  - " + item)

    report_lines.append("")
    report_lines.append("=" * 90)
    report_lines.append("CROSS-SYMBOL SUMMARY")
    report_lines.append("=" * 90)
    report_lines.append(
        "Target Symbols             : " +
        str(len(TARGET_SYMBOLS))
    )
    report_lines.append(
        "Origin Paths Established   : " +
        str(established)
    )
    report_lines.append(
        "Consistent Targets         : " +
        str(consistent)
    )
    report_lines.append(
        "Unresolved Targets         : " +
        str(unresolved)
    )

    report_lines.append("")
    report_lines.append("=" * 90)
    report_lines.append("FORENSIC STATUS")
    report_lines.append("=" * 90)
    report_lines.append(
        "FORENSIC STATUS : " +
        forensic_status
    )
    report_lines.append("PREDICTIVE CLAIM : NOT ESTABLISHED")
    report_lines.append("RELATIONSHIP CALCULATION : NOT PERFORMED")
    report_lines.append("DATABASE WRITE : NOT PERFORMED")
    report_lines.append("DATABASE REPAIR : NOT PERFORMED")
    report_lines.append("UNIVERSE REBUILD : NOT PERFORMED")
    report_lines.append("SYMBOL DELETION : NOT PERFORMED")
    report_lines.append("TRADING DECISION : NOT PERFORMED")
    report_lines.append("")
    report_lines.append("=" * 90)
    report_lines.append("ARTIFACT")
    report_lines.append("=" * 90)
    report_lines.append("Artifact : " + str(OUTPUT_JSON))

    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print()
    print("=" * 90)
    print("CROSS-SYMBOL SUMMARY")
    print("=" * 90)
    print("Target Symbols             :", len(TARGET_SYMBOLS))
    print("Origin Paths Established   :", established)
    print("Consistent Targets         :", consistent)
    print("Unresolved Targets         :", unresolved)

    print()
    print("=" * 90)
    print("FORENSIC STATUS")
    print("=" * 90)
    print("FORENSIC STATUS :", forensic_status)
    print("PREDICTIVE CLAIM : NOT ESTABLISHED")
    print("RELATIONSHIP CALCULATION : NOT PERFORMED")
    print("DATABASE WRITE : NOT PERFORMED")
    print("DATABASE REPAIR : NOT PERFORMED")
    print("UNIVERSE REBUILD : NOT PERFORMED")
    print("SYMBOL DELETION : NOT PERFORMED")
    print("TRADING DECISION : NOT PERFORMED")

    print()
    print("=" * 90)
    print("ARTIFACT")
    print("=" * 90)
    print("Artifact :", OUTPUT_JSON)
    print("SHA256   :", sha256_file(OUTPUT_JSON))
    print("Report   :", OUTPUT_TXT)
    print("=" * 90)


if __name__ == "__main__":
    main()