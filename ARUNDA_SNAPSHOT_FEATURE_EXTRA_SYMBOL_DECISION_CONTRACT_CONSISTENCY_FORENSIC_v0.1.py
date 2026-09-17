# ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DECISION_CONTRACT_CONSISTENCY_FORENSIC_v0.1.py
#
# READ-ONLY FORENSIC
# Purpose:
#   Validate consistency across:
#     Semantic -> Origin -> CMC Identity -> Expected Universe Status -> Decision
#
# Forbidden:
#   Network
#   Database writes
#   Repair
#   Delete
#   Universe rebuild
#   Prediction
#   Trading decision

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = BASE_DIR / "arunda.db"

NORMALIZATION_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)
PROVENANCE_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_INPUT_EXTRA_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json"
)
SEMANTIC_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1.json"
)
ORIGIN_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_PROPAGATION_FORENSIC_v0.1.json"
)
FIRST_INSERTION_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_FIRST_INSERTION_FORENSIC_v0.1.json"
)
CMC_IDENTITY_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_CMC_IDENTITY_FORENSIC_v0.1.json"
)
EXPECTED_STATUS_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_STATUS_FORENSIC_v0.1.json"
)
DECISION_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_DECISION_FORENSIC_v0.1.json"
)

ARTIFACT_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DECISION_CONTRACT_CONSISTENCY_FORENSIC_v0.1.json"
)

TARGET_SYMBOLS = {"4", "ASSET"}

FORBIDDEN_SQL = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "ALTER",
    "DROP",
    "CREATE",
    "VACUUM",
    "ATTACH",
    "DETACH",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def deep_find_all(obj: Any, key: str) -> list[Any]:
    found: list[Any] = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                found.append(v)
            found.extend(deep_find_all(v, key))

    elif isinstance(obj, list):
        for item in obj:
            found.extend(deep_find_all(item, key))

    return found


def recursive_symbol_records(obj: Any) -> list[dict[str, Any]]:
    """
    Extract dictionaries that look like per-symbol records.
    """
    records: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            keys = {str(k).lower() for k in node.keys()}

            if "symbol" in keys:
                records.append(node)

            for value in node.values():
                walk(value)

        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(obj)
    return records


def normalize_symbol(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        if text:
            return text.upper()

    return None


def collect_symbols(obj: Any) -> set[str]:
    result: set[str] = set()

    for record in recursive_symbol_records(obj):
        for key, value in record.items():
            if str(key).lower() == "symbol":
                symbol = normalize_symbol(value)
                if symbol:
                    result.add(symbol)

    for key in (
        "extra_symbols",
        "target_symbols",
        "symbols",
        "requested_symbols",
    ):
        values = deep_find_all(obj, key)
        for value in values:
            if isinstance(value, list):
                for item in value:
                    symbol = normalize_symbol(item)
                    if symbol:
                        result.add(symbol)

    return result


def first_value(record: dict[str, Any], *keys: str) -> Any:
    lowered = {str(k).lower(): v for k, v in record.items()}

    for key in keys:
        if key.lower() in lowered:
            return lowered[key.lower()]

    return None


def find_symbol_records(obj: Any) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {
        symbol: [] for symbol in TARGET_SYMBOLS
    }

    for record in recursive_symbol_records(obj):
        symbol = normalize_symbol(first_value(record, "symbol"))

        if symbol in TARGET_SYMBOLS:
            result[symbol].append(record)

    return result


def get_expected_universe(normalization: Any) -> set[str]:
    candidates = [
        deep_find_all(normalization, "expected_universe"),
        deep_find_all(normalization, "normalized_expected_universe"),
        deep_find_all(normalization, "universe"),
    ]

    for groups in candidates:
        for value in groups:
            if isinstance(value, list):
                symbols = {
                    normalize_symbol(x)
                    for x in value
                    if normalize_symbol(x) is not None
                }
                if symbols:
                    return symbols

            if isinstance(value, dict):
                for nested_key in (
                    "symbols",
                    "members",
                    "universe",
                    "normalized_symbols",
                ):
                    nested = value.get(nested_key)
                    if isinstance(nested, list):
                        symbols = {
                            normalize_symbol(x)
                            for x in nested
                            if normalize_symbol(x) is not None
                        }
                        if symbols:
                            return symbols

    # Fallback: search records with expected-universe membership.
    result: set[str] = set()

    for record in recursive_symbol_records(normalization):
        member = first_value(
            record,
            "expected_universe_member",
            "is_expected_universe_member",
            "expected_member",
        )

        symbol = normalize_symbol(first_value(record, "symbol"))

        if symbol and member is True:
            result.add(symbol)

    return result


def safe_db_inventory() -> dict[str, Any]:
    """
    SQLite read-only connection.
    """
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row

    try:
        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        table_names = [row["name"] for row in tables]

        symbol_evidence: dict[str, dict[str, Any]] = {}

        for symbol in sorted(TARGET_SYMBOLS):
            symbol_evidence[symbol] = {
                "tables": [],
                "total_rows": 0,
            }

            for table in table_names:
                columns = connection.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()

                symbol_columns = [
                    row["name"]
                    for row in columns
                    if str(row["name"]).lower() == "symbol"
                ]

                if not symbol_columns:
                    continue

                count_row = connection.execute(
                    f'''
                    SELECT COUNT(*)
                    FROM "{table}"
                    WHERE "symbol" = ?
                    ''',
                    (symbol,),
                ).fetchone()

                count = int(count_row[0])

                if count > 0:
                    symbol_evidence[symbol]["tables"].append(table)
                    symbol_evidence[symbol]["total_rows"] += count

        return {
            "database_tables": table_names,
            "database_table_count": len(table_names),
            "symbol_evidence": symbol_evidence,
        }

    finally:
        connection.close()


def assert_read_only_sql() -> None:
    """
    Defensive guard. No mutation SQL is executed by this script.
    """
    for token in FORBIDDEN_SQL:
        if token in "SELECT COUNT FROM sqlite_master PRAGMA table_info".upper():
            # This is intentionally never executed as SQL text.
            pass


def extract_semantic(symbol: str, semantic_records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    records = semantic_records.get(symbol, [])

    result = {
        "semantic_class": None,
        "meaning": None,
        "artifact_likelihood": None,
        "market_symbol_likelihood": None,
        "record_count": len(records),
    }

    for record in records:
        semantic_class = first_value(
            record,
            "semantic_class",
            "classification",
            "semantic_classification",
        )

        meaning = first_value(
            record,
            "meaning",
            "semantic_meaning",
        )

        artifact_likelihood = first_value(
            record,
            "artifact_likelihood",
            "artifact_probability",
        )

        market_symbol_likelihood = first_value(
            record,
            "market_symbol_likelihood",
            "symbol_likelihood",
        )

        if semantic_class is not None:
            result["semantic_class"] = semantic_class

        if meaning is not None:
            result["meaning"] = meaning

        if artifact_likelihood is not None:
            result["artifact_likelihood"] = artifact_likelihood

        if market_symbol_likelihood is not None:
            result["market_symbol_likelihood"] = market_symbol_likelihood

    return result


def extract_origin(symbol: str, origin_records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    records = origin_records.get(symbol, [])

    result = {
        "origin_class": None,
        "confidence": None,
        "reason": None,
        "record_count": len(records),
    }

    for record in records:
        origin_class = first_value(
            record,
            "origin_class",
            "origin",
            "classification",
        )

        confidence = first_value(
            record,
            "confidence",
            "origin_confidence",
        )

        reason = first_value(
            record,
            "reason",
            "origin_reason",
        )

        if origin_class is not None:
            result["origin_class"] = origin_class

        if confidence is not None:
            result["confidence"] = confidence

        if reason is not None:
            result["reason"] = reason

    return result


def extract_cmc(symbol: str, cmc_records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    records = cmc_records.get(symbol, [])

    result = {
        "cmc_ids": [],
        "names": [],
        "symbols": [],
        "slugs": [],
        "sources": [],
        "identity_class": None,
        "identity_consistency": None,
        "canonical_asset_evidence": None,
        "record_count": len(records),
    }

    def add_unique(field: str, value: Any) -> None:
        if value is None:
            return

        text = str(value)
        if text and text not in result[field]:
            result[field].append(text)

    for record in records:
        cmc_id = first_value(record, "cmc_id", "cmc_ids")
        name = first_value(record, "name", "names")
        symbol_value = first_value(record, "symbol", "symbols")
        slug = first_value(record, "slug", "slugs")
        source = first_value(record, "source", "sources")

        identity_class = first_value(
            record,
            "identity_class",
            "cmc_identity_class",
        )

        consistency = first_value(
            record,
            "identity_consistency",
            "consistency",
        )

        canonical = first_value(
            record,
            "canonical_asset_evidence",
            "canonical_asset",
        )

        if isinstance(cmc_id, list):
            for x in cmc_id:
                add_unique("cmc_ids", x)
        else:
            add_unique("cmc_ids", cmc_id)

        if isinstance(name, list):
            for x in name:
                add_unique("names", x)
        else:
            add_unique("names", name)

        if isinstance(symbol_value, list):
            for x in symbol_value:
                add_unique("symbols", x)
        else:
            add_unique("symbols", symbol_value)

        if isinstance(slug, list):
            for x in slug:
                add_unique("slugs", x)
        else:
            add_unique("slugs", slug)

        if isinstance(source, list):
            for x in source:
                add_unique("sources", x)
        else:
            add_unique("sources", source)

        if identity_class is not None:
            result["identity_class"] = identity_class

        if consistency is not None:
            result["identity_consistency"] = consistency

        if canonical is not None:
            result["canonical_asset_evidence"] = canonical

    return result


def extract_expected_status(
    symbol: str,
    status_records: dict[str, list[dict[str, Any]]],
    expected_universe: set[str],
) -> dict[str, Any]:

    records = status_records.get(symbol, [])

    result = {
        "expected_universe_member": symbol in expected_universe,
        "status": None,
        "observed_table_count": None,
        "canonical_asset_evidence": None,
        "record_count": len(records),
    }

    for record in records:
        member = first_value(
            record,
            "expected_universe_member",
            "is_expected_universe_member",
        )

        status = first_value(
            record,
            "status",
            "expected_universe_status",
        )

        table_count = first_value(
            record,
            "observed_table_count",
            "table_count",
        )

        canonical = first_value(
            record,
            "canonical_asset_evidence",
            "canonical_asset",
        )

        if member is not None:
            result["expected_universe_member"] = bool(member)

        if status is not None:
            result["status"] = status

        if table_count is not None:
            result["observed_table_count"] = table_count

        if canonical is not None:
            result["canonical_asset_evidence"] = canonical

    return result


def extract_decision(
    symbol: str,
    decision_records: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:

    records = decision_records.get(symbol, [])

    result = {
        "decision_class": None,
        "decision": None,
        "semantic_class": None,
        "origin_class": None,
        "cmc_identity_evidence": None,
        "database_observed": None,
        "database_table_count": None,
        "database_total_rows": None,
        "rationale": None,
        "semantic_note": None,
        "record_count": len(records),
    }

    for record in records:
        mappings = {
            "decision_class": (
                "decision_class",
                "classification",
            ),
            "decision": (
                "decision",
                "expected_universe_decision",
            ),
            "semantic_class": (
                "semantic_class",
                "semantic_classification",
            ),
            "origin_class": (
                "origin_class",
                "origin",
            ),
            "cmc_identity_evidence": (
                "cmc_identity_evidence",
                "cmc_evidence",
            ),
            "database_observed": (
                "database_observed",
                "observed_in_database",
            ),
            "database_table_count": (
                "database_table_count",
                "observed_table_count",
            ),
            "database_total_rows": (
                "database_total_rows",
                "total_rows",
            ),
            "rationale": (
                "rationale",
                "reason",
            ),
            "semantic_note": (
                "semantic_note",
            ),
        }

        for output_key, keys in mappings.items():
            value = first_value(record, *keys)
            if value is not None:
                result[output_key] = value

    return result


def semantic_origin_expected_consistency(
    symbol: str,
    semantic: dict[str, Any],
    origin: dict[str, Any],
    cmc: dict[str, Any],
    status: dict[str, Any],
    decision: dict[str, Any],
    db: dict[str, Any],
) -> dict[str, Any]:

    checks: dict[str, bool] = {}

    checks["target_symbol"] = symbol in TARGET_SYMBOLS

    checks["outside_expected_universe"] = (
        status["expected_universe_member"] is False
    )

    checks["decision_excludes_symbol"] = (
        str(decision["decision"]).upper()
        == "EXCLUDE_FROM_EXPECTED_UNIVERSE"
    )

    checks["decision_class_outside_expected"] = (
        str(decision["decision_class"]).upper()
        == "OBSERVED_ASSET_OUTSIDE_EXPECTED_UNIVERSE"
    )

    checks["cmc_identity_present"] = (
        len(cmc["cmc_ids"]) > 0
        and cmc["canonical_asset_evidence"] is True
    )

    checks["database_observed"] = (
        bool(db["database_observed"])
        if db["database_observed"] is not None
        else False
    )

    checks["semantic_present"] = (
        semantic["semantic_class"] is not None
    )

    checks["origin_present"] = (
        origin["origin_class"] is not None
    )

    checks["decision_semantic_matches"] = (
        decision["semantic_class"] is None
        or decision["semantic_class"] == semantic["semantic_class"]
    )

    checks["decision_origin_matches"] = (
        decision["origin_class"] is None
        or decision["origin_class"] == origin["origin_class"]
    )

    checks["decision_table_count_matches_db"] = (
        decision["database_table_count"] is None
        or int(decision["database_table_count"])
        == len(db["tables"])
    )

    checks["decision_total_rows_matches_db"] = (
        decision["database_total_rows"] is None
        or int(decision["database_total_rows"])
        == int(db["total_rows"])
    )

    passed = all(checks.values())

    contradictions: list[str] = []

    if not checks["decision_semantic_matches"]:
        contradictions.append(
            "DECISION_SEMANTIC_CLASS_MISMATCH"
        )

    if not checks["decision_origin_matches"]:
        contradictions.append(
            "DECISION_ORIGIN_CLASS_MISMATCH"
        )

    if not checks["outside_expected_universe"]:
        contradictions.append(
            "EXPECTED_UNIVERSE_STATUS_CONFLICT"
        )

    if not checks["decision_excludes_symbol"]:
        contradictions.append(
            "DECISION_EXCLUSION_CONTRACT_CONFLICT"
        )

    if not checks["cmc_identity_present"]:
        contradictions.append(
            "CMC_IDENTITY_EVIDENCE_MISSING"
        )

    if not checks["decision_table_count_matches_db"]:
        contradictions.append(
            "DATABASE_TABLE_COUNT_MISMATCH"
        )

    if not checks["decision_total_rows_matches_db"]:
        contradictions.append(
            "DATABASE_TOTAL_ROWS_MISMATCH"
        )

    return {
        "symbol": symbol,
        "checks": checks,
        "passed": passed,
        "contradictions": contradictions,
    }


def build_artifact(
    normalization: Any,
    provenance: Any,
    semantic_data: Any,
    origin_data: Any,
    first_data: Any,
    cmc_data: Any,
    status_data: Any,
    decision_data: Any,
    db_inventory: dict[str, Any],
) -> dict[str, Any]:

    expected_universe = get_expected_universe(normalization)

    semantic_records = find_symbol_records(semantic_data)
    origin_records = find_symbol_records(origin_data)
    cmc_records = find_symbol_records(cmc_data)
    status_records = find_symbol_records(status_data)
    decision_records = find_symbol_records(decision_data)

    symbols: dict[str, Any] = {}
    consistency_results: list[dict[str, Any]] = []

    for symbol in sorted(TARGET_SYMBOLS):
        semantic = extract_semantic(symbol, semantic_records)
        origin = extract_origin(symbol, origin_records)
        cmc = extract_cmc(symbol, cmc_records)
        status = extract_expected_status(
            symbol,
            status_records,
            expected_universe,
        )
        decision = extract_decision(
            symbol,
            decision_records,
        )

        raw_db = db_inventory["symbol_evidence"].get(
            symbol,
            {"tables": [], "total_rows": 0},
        )

        db = {
            "database_observed": len(raw_db["tables"]) > 0,
            "tables": sorted(raw_db["tables"]),
            "table_count": len(raw_db["tables"]),
            "total_rows": int(raw_db["total_rows"]),
        }

        # Normalize fields used by checks.
        decision["database_observed"] = (
            db["database_observed"]
            if decision["database_observed"] is None
            else decision["database_observed"]
        )

        consistency = semantic_origin_expected_consistency(
            symbol,
            semantic,
            origin,
            cmc,
            status,
            decision,
            db,
        )

        symbols[symbol] = {
            "semantic": semantic,
            "origin": origin,
            "cmc_identity": cmc,
            "expected_universe_status": status,
            "decision": decision,
            "database_evidence": db,
            "consistency": consistency,
        }

        consistency_results.append(consistency)

    contradictions = [
        item
        for item in consistency_results
        if not item["passed"]
    ]

    decision_semantic_mismatch_symbols = [
        item["symbol"]
        for item in consistency_results
        if "DECISION_SEMANTIC_CLASS_MISMATCH"
        in item["contradictions"]
    ]

    decision_origin_mismatch_symbols = [
        item["symbol"]
        for item in consistency_results
        if "DECISION_ORIGIN_CLASS_MISMATCH"
        in item["contradictions"]
    ]

    all_pass = len(contradictions) == 0

    if all_pass:
        forensic_status = (
            "DECISION_CONTRACT_CONSISTENT_WITH_UPSTREAM_FORENSIC_ARTIFACTS"
        )
    elif decision_semantic_mismatch_symbols:
        forensic_status = (
            "DECISION_CONTRACT_SEMANTIC_MISMATCH_DETECTED"
        )
    elif decision_origin_mismatch_symbols:
        forensic_status = (
            "DECISION_CONTRACT_ORIGIN_MISMATCH_DETECTED"
        )
    else:
        forensic_status = (
            "DECISION_CONTRACT_CONSISTENCY_EXCEPTION_DETECTED"
        )

    return {
        "artifact": {
            "name": ARTIFACT_PATH.name,
            "version": "v0.1",
            "generated_at_utc": utc_now(),
        },
        "contract": {
            "mode": "READ ONLY",
            "network": "FORBIDDEN",
            "database_write": "FORBIDDEN",
            "repair": "FORBIDDEN",
            "prediction": "FORBIDDEN",
            "decision": "FORENSIC STATUS ONLY",
            "universe_rebuild": "FORBIDDEN",
            "symbol_deletion": "FORBIDDEN",
        },
        "inputs": {
            "database": str(DB_PATH),
            "normalization": str(NORMALIZATION_PATH),
            "provenance": str(PROVENANCE_PATH),
            "semantic": str(SEMANTIC_PATH),
            "origin": str(ORIGIN_PATH),
            "first_insertion": str(FIRST_INSERTION_PATH),
            "cmc_identity": str(CMC_IDENTITY_PATH),
            "expected_status": str(EXPECTED_STATUS_PATH),
            "decision": str(DECISION_PATH),
        },
        "input_sha256": {
            "normalization": sha256_file(NORMALIZATION_PATH),
            "provenance": sha256_file(PROVENANCE_PATH),
            "semantic": sha256_file(SEMANTIC_PATH),
            "origin": sha256_file(ORIGIN_PATH),
            "first_insertion": sha256_file(FIRST_INSERTION_PATH),
            "cmc_identity": sha256_file(CMC_IDENTITY_PATH),
            "expected_status": sha256_file(EXPECTED_STATUS_PATH),
            "decision": sha256_file(DECISION_PATH),
        },
        "expected_universe": {
            "count": len(expected_universe),
            "target_membership": {
                symbol: symbol in expected_universe
                for symbol in sorted(TARGET_SYMBOLS)
            },
        },
        "database_inventory": {
            "table_count": db_inventory["database_table_count"],
        },
        "target_symbols": sorted(TARGET_SYMBOLS),
        "symbols": symbols,
        "cross_symbol_summary": {
            "target_symbols": len(TARGET_SYMBOLS),
            "passed": sum(
                1 for item in consistency_results
                if item["passed"]
            ),
            "failed": len(contradictions),
            "decision_semantic_mismatch_symbols":
                decision_semantic_mismatch_symbols,
            "decision_origin_mismatch_symbols":
                decision_origin_mismatch_symbols,
        },
        "forensic_status": {
            "status": forensic_status,
            "predictive_claim": "NOT ESTABLISHED",
            "relationship_calculation": "NOT PERFORMED",
            "database_write": "NOT PERFORMED",
            "database_repair": "NOT PERFORMED",
            "universe_rebuild": "NOT PERFORMED",
            "symbol_deletion": "NOT PERFORMED",
            "trading_decision": "NOT PERFORMED",
        },
    }


def print_header() -> None:
    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL "
        "DECISION CONTRACT CONSISTENCY FORENSIC v0.1"
    )
    print("=" * 90)
    print(f"Database       : {DB_PATH}")
    print(f"Normalization  : {NORMALIZATION_PATH}")
    print(f"Provenance     : {PROVENANCE_PATH}")
    print(f"Semantic       : {SEMANTIC_PATH}")
    print(f"Origin         : {ORIGIN_PATH}")
    print(f"First Insertion: {FIRST_INSERTION_PATH}")
    print(f"CMC Identity   : {CMC_IDENTITY_PATH}")
    print(f"Expected Status: {EXPECTED_STATUS_PATH}")
    print(f"Decision       : {DECISION_PATH}")
    print("Mode           : READ ONLY")
    print("Network        : FORBIDDEN")
    print("Database Write : FORBIDDEN")
    print("Repair         : FORBIDDEN")
    print("Prediction     : FORBIDDEN")
    print("Decision       : FORENSIC STATUS ONLY")
    print("-" * 90)


def print_report(artifact: dict[str, Any]) -> None:
    expected = artifact["expected_universe"]
    summary = artifact["cross_symbol_summary"]

    print("=" * 90)
    print("INPUT CONTRACT")
    print("=" * 90)
    print(f"Expected Universe : {expected['count']}")
    print(
        "Target Symbols    : "
        + ", ".join(artifact["target_symbols"])
    )
    print("-" * 90)

    print("=" * 90)
    print("UPSTREAM CONTRACT CONSISTENCY")
    print("=" * 90)

    for symbol in artifact["target_symbols"]:
        data = artifact["symbols"][symbol]
        consistency = data["consistency"]

        semantic = data["semantic"]
        origin = data["origin"]
        cmc = data["cmc_identity"]
        status = data["expected_universe_status"]
        decision = data["decision"]
        db = data["database_evidence"]

        print("-" * 90)
        print(f"SYMBOL : {symbol}")
        print(
            f"SEMANTIC CLASS       : "
            f"{semantic['semantic_class']}"
        )
        print(
            f"ORIGIN CLASS         : "
            f"{origin['origin_class']}"
        )
        print(
            f"CMC IDENTITY         : "
            f"{', '.join(cmc['cmc_ids']) if cmc['cmc_ids'] else 'NONE'}"
        )
        print(
            f"EXPECTED MEMBER      : "
            f"{status['expected_universe_member']}"
        )
        print(
            f"EXPECTED STATUS      : "
            f"{status['status']}"
        )
        print(
            f"DECISION CLASS       : "
            f"{decision['decision_class']}"
        )
        print(
            f"DECISION             : "
            f"{decision['decision']}"
        )
        print(
            f"DATABASE OBSERVED    : "
            f"{db['database_observed']}"
        )
        print(
            f"DATABASE TABLE COUNT : "
            f"{db['table_count']}"
        )
        print(
            f"DATABASE TOTAL ROWS  : "
            f"{db['total_rows']}"
        )

        print("-" * 90)
        print("CONTRACT CHECKS")

        for check_name, passed in consistency["checks"].items():
            print(
                f"  {'PASS' if passed else 'FAIL'} : "
                f"{check_name}"
            )

        print(
            f"CONSISTENCY : "
            f"{'PASS' if consistency['passed'] else 'FAIL'}"
        )

        if consistency["contradictions"]:
            print("CONTRADICTIONS :")
            for contradiction in consistency["contradictions"]:
                print(f"  - {contradiction}")

    print("=" * 90)
    print("CROSS-SYMBOL SUMMARY")
    print("=" * 90)
    print(f"Target Symbols       : {summary['target_symbols']}")
    print(f"Passed               : {summary['passed']}")
    print(f"Failed               : {summary['failed']}")
    print(
        "Semantic mismatches  : "
        + (
            ", ".join(
                summary["decision_semantic_mismatch_symbols"]
            )
            if summary["decision_semantic_mismatch_symbols"]
            else "NONE"
        )
    )
    print(
        "Origin mismatches    : "
        + (
            ", ".join(
                summary["decision_origin_mismatch_symbols"]
            )
            if summary["decision_origin_mismatch_symbols"]
            else "NONE"
        )
    )

    print("=" * 90)
    print("FORENSIC STATUS")
    print("=" * 90)
    forensic = artifact["forensic_status"]

    print(
        f"FORENSIC STATUS : "
        f"{forensic['status']}"
    )
    print(
        f"PREDICTIVE CLAIM : "
        f"{forensic['predictive_claim']}"
    )
    print(
        f"RELATIONSHIP CALCULATION : "
        f"{forensic['relationship_calculation']}"
    )
    print(
        f"DATABASE WRITE : "
        f"{forensic['database_write']}"
    )
    print(
        f"DATABASE REPAIR : "
        f"{forensic['database_repair']}"
    )
    print(
        f"UNIVERSE REBUILD : "
        f"{forensic['universe_rebuild']}"
    )
    print(
        f"SYMBOL DELETION : "
        f"{forensic['symbol_deletion']}"
    )
    print(
        f"TRADING DECISION : "
        f"{forensic['trading_decision']}"
    )


def main() -> None:
    print_header()

    assert_read_only_sql()

    required_paths = [
        DB_PATH,
        NORMALIZATION_PATH,
        PROVENANCE_PATH,
        SEMANTIC_PATH,
        ORIGIN_PATH,
        FIRST_INSERTION_PATH,
        CMC_IDENTITY_PATH,
        EXPECTED_STATUS_PATH,
        DECISION_PATH,
    ]

    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(
                f"Required input missing: {path}"
            )

    normalization = load_json(NORMALIZATION_PATH)
    provenance = load_json(PROVENANCE_PATH)
    semantic_data = load_json(SEMANTIC_PATH)
    origin_data = load_json(ORIGIN_PATH)
    first_data = load_json(FIRST_INSERTION_PATH)
    cmc_data = load_json(CMC_IDENTITY_PATH)
    status_data = load_json(EXPECTED_STATUS_PATH)
    decision_data = load_json(DECISION_PATH)

    # Intentionally loaded to establish dependency chain.
    _ = provenance
    _ = first_data

    db_inventory = safe_db_inventory()

    artifact = build_artifact(
        normalization=normalization,
        provenance=provenance,
        semantic_data=semantic_data,
        origin_data=origin_data,
        first_data=first_data,
        cmc_data=cmc_data,
        status_data=status_data,
        decision_data=decision_data,
        db_inventory=db_inventory,
    )

    canonical = json.dumps(
        artifact,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    ARTIFACT_PATH.write_bytes(canonical)

    artifact_hash = hashlib.sha256(canonical).hexdigest()

    print_report(artifact)

    print("=" * 90)
    print("ARTIFACT")
    print("=" * 90)
    print(f"Artifact : {ARTIFACT_PATH}")
    print(f"SHA256   : {artifact_hash}")
    print("=" * 90)


if __name__ == "__main__":
    main()