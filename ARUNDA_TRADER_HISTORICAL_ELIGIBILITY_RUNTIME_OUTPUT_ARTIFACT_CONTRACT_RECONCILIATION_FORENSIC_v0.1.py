from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any


# ==================================================================================================
# ARUNDA TRADER
# HISTORICAL ELIGIBILITY RUNTIME OUTPUT ARTIFACT CONTRACT RECONCILIATION FORENSIC v0.1
# ==================================================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCER = PROJECT_ROOT / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
TARGET = PROJECT_ROOT / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_CONTRACT_RECONCILIATION_FORENSIC_REPORT.json"
)

EXPECTED_TOP_LEVEL_KEYS = {
    "capture_db",
    "decision",
    "eligible_rows",
    "engine",
    "frontier",
    "gate_configuration",
    "no_trade_rows",
    "production_db",
    "row_results",
    "rows",
    "safety",
    "snapshot_id",
    "timestamp_utc",
}

EXPECTED_ASSETS = ["BTC", "ETH", "SOL", "XRP"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)

    if not isinstance(obj, dict):
        raise RuntimeError("Target artifact is not a JSON object.")

    return obj


def source_text() -> str:
    return PRODUCER.read_text(encoding="utf-8")


def syntax_valid(text: str) -> bool:
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False


def normalize_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def flatten_strings(value: Any) -> list[str]:
    out: list[str] = []

    if isinstance(value, str):
        out.append(value)

    elif isinstance(value, dict):
        for k, v in value.items():
            out.append(str(k))
            out.extend(flatten_strings(v))

    elif isinstance(value, list):
        for item in value:
            out.extend(flatten_strings(item))

    return out


def find_hashes(value: Any) -> list[str]:
    hashes = []

    for item in flatten_strings(value):
        if re.fullmatch(r"[0-9a-fA-F]{64}", item):
            hashes.append(item.lower())

    return hashes


def recursive_find_keys(value: Any, wanted: set[str]) -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []

    if isinstance(value, dict):
        for key, child in value.items():
            nk = normalize_key(key)

            if nk in wanted:
                found.append((str(key), child))

            found.extend(recursive_find_keys(child, wanted))

    elif isinstance(value, list):
        for child in value:
            found.extend(recursive_find_keys(child, wanted))

    return found


def contains_semantic(value: Any, terms: set[str]) -> bool:
    text = " ".join(flatten_strings(value)).lower()

    return all(term.lower() in text for term in terms)


def extract_row_results(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    rows = artifact.get("row_results")

    if not isinstance(rows, list):
        return []

    return [x for x in rows if isinstance(x, dict)]


def inspect_producer_contract(text: str) -> dict[str, Any]:
    tree = ast.parse(text)

    report = {
        "production_db_hash_generation": False,
        "production_db_hash_reference": False,
        "safety_write_evidence": False,
        "safety_order_evidence": False,
        "safety_synthetic_evidence": False,
        "json_dump_present": False,
        "report_path_present": False,
    }

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "sha256_file":
                    report["production_db_hash_generation"] = True

                if node.func.attr == "dump":
                    report["json_dump_present"] = True

        if isinstance(node, ast.Name):
            if node.id == "report_path":
                report["report_path_present"] = True

        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value.lower()

            if "sha256" in value:
                report["production_db_hash_reference"] = True

            if "production db writes" in value:
                report["safety_write_evidence"] = True

            if "order execution" in value:
                report["safety_order_evidence"] = True

            if "synthetic" in value:
                report["safety_synthetic_evidence"] = True

    return report


def inspect_production_db_section(section: Any) -> dict[str, Any]:
    result = {
        "exists": isinstance(section, dict),
        "hashes": find_hashes(section),
        "has_sha256_key": False,
        "has_before_hash": False,
        "has_after_hash": False,
        "semantic_production_db_evidence": False,
    }

    if not isinstance(section, dict):
        return result

    normalized = {normalize_key(k): v for k, v in section.items()}

    result["has_sha256_key"] = any(
        "sha256" in key or key.endswith("hash")
        for key in normalized
    )

    result["has_before_hash"] = any(
        "before" in key and ("sha256" in key or "hash" in key)
        for key in normalized
    )

    result["has_after_hash"] = any(
        "after" in key and ("sha256" in key or "hash" in key)
        for key in normalized
    )

    result["semantic_production_db_evidence"] = contains_semantic(
        section,
        {"production"},
    )

    return result


def inspect_safety_section(section: Any) -> dict[str, Any]:
    result = {
        "exists": isinstance(section, dict),
        "keys": [],
        "write_evidence": False,
        "order_evidence": False,
        "synthetic_evidence": False,
        "semantic_contract": False,
    }

    if not isinstance(section, dict):
        return result

    result["keys"] = list(section.keys())

    text = " ".join(flatten_strings(section)).lower()

    write_terms = (
        "production db writes",
        "production_db_writes",
        "db writes",
        "writes",
        "insert",
        "update",
        "delete",
    )

    order_terms = (
        "order execution",
        "order_execution",
        "order",
        "execution",
    )

    synthetic_terms = (
        "synthetic",
        "synthetic data",
        "synthetic_data",
    )

    result["write_evidence"] = any(x in text for x in write_terms)
    result["order_evidence"] = any(x in text for x in order_terms)
    result["synthetic_evidence"] = any(x in text for x in synthetic_terms)

    result["semantic_contract"] = (
        result["write_evidence"]
        and result["order_evidence"]
        and result["synthetic_evidence"]
    )

    return result


def inspect_artifact(artifact: dict[str, Any]) -> dict[str, Any]:

    row_results = extract_row_results(artifact)

    assets = [
        row.get("asset")
        for row in row_results
        if row.get("asset") is not None
    ]

    directions = [
        row.get("direction")
        for row in row_results
        if row.get("direction") is not None
    ]

    results = [
        row.get("result")
        for row in row_results
        if row.get("result") is not None
    ]

    reasons = []

    for row in row_results:
        value = row.get("reasons", [])
        if isinstance(value, list):
            reasons.extend(value)

    production_db = artifact.get("production_db")
    safety = artifact.get("safety")

    production_db_info = inspect_production_db_section(production_db)
    safety_info = inspect_safety_section(safety)

    return {
        "rows": artifact.get("rows"),
        "eligible_rows": artifact.get("eligible_rows"),
        "no_trade_rows": artifact.get("no_trade_rows"),
        "row_results_count": len(row_results),
        "assets": assets,
        "directions": directions,
        "results": results,
        "reasons": reasons,
        "decision": artifact.get("decision"),
        "frontier": artifact.get("frontier"),
        "production_db": production_db_info,
        "safety": safety_info,
    }


def build_report() -> dict[str, Any]:

    producer_exists = PRODUCER.exists()
    target_exists = TARGET.exists()

    if not producer_exists:
        raise FileNotFoundError(PRODUCER)

    if not target_exists:
        raise FileNotFoundError(TARGET)

    producer = source_text()
    artifact = load_json(TARGET)

    producer_hash = sha256_file(PRODUCER)
    target_hash = sha256_file(TARGET)

    producer_contract = inspect_producer_contract(producer)
    artifact_info = inspect_artifact(artifact)

    required_keys = set(artifact.keys())

    missing_keys = sorted(EXPECTED_TOP_LEVEL_KEYS - required_keys)
    unexpected_keys = sorted(required_keys - EXPECTED_TOP_LEVEL_KEYS)

    rows_ok = (
        isinstance(artifact_info["rows"], int)
        and artifact_info["rows"] == artifact_info["row_results_count"]
    )

    eligible_ok = (
        isinstance(artifact_info["eligible_rows"], int)
        and artifact_info["eligible_rows"] == 0
    )

    no_trade_ok = (
        isinstance(artifact_info["no_trade_rows"], int)
        and artifact_info["no_trade_rows"]
        == artifact_info["row_results_count"]
    )

    assets_ok = artifact_info["assets"] == EXPECTED_ASSETS

    results_ok = (
        len(artifact_info["results"]) == artifact_info["row_results_count"]
        and artifact_info["row_results_count"] == len(
            [
                row
                for row in artifact_info.get("row_results", [])
                if isinstance(row, dict)
            ]
        )
        and all(
            result == "NO_TRADE"
            for result in artifact_info["results"]
        )
    )

    decision_ok = artifact_info["decision"] == "NO_TRADE"

    reasons_ok = (
        "CONFIDENCE_BELOW_GATE" in artifact_info["reasons"]
        and "WEAK_SIGNAL" in artifact_info["reasons"]
    )

    production_db_ok = (
        artifact_info["production_db"]["exists"]
        and (
            artifact_info["production_db"]["has_sha256_key"]
            or len(artifact_info["production_db"]["hashes"]) > 0
        )
    )

    safety_ok = artifact_info["safety"]["semantic_contract"]

    producer_capable_of_evidence = (
        producer_contract["production_db_hash_generation"]
        or producer_contract["production_db_hash_reference"]
    )

    artifact_schema_ok = not missing_keys and not unexpected_keys

    reconciliation_ok = all(
        [
            artifact_schema_ok,
            rows_ok,
            eligible_ok,
            no_trade_ok,
            assets_ok,
            results_ok,
            decision_ok,
            reasons_ok,
        ]
    )

    # IMPORTANT:
    # We do NOT modify the producer or artifact in this forensic stage.
    # We determine whether the previous forensic checker was too strict
    # or whether the producer contract genuinely lacks required evidence.

    if reconciliation_ok and production_db_ok and safety_ok:
        verdict = "RUNTIME_OUTPUT_ARTIFACT_CONTRACT_RECONCILIATION_VERIFIED"
    elif reconciliation_ok and not production_db_ok and producer_capable_of_evidence:
        verdict = "ARTIFACT_PRODUCTION_DB_EVIDENCE_MAPPING_MISMATCH"
    elif reconciliation_ok and not safety_ok:
        verdict = "ARTIFACT_SAFETY_EVIDENCE_MAPPING_MISMATCH"
    else:
        verdict = "RUNTIME_OUTPUT_ARTIFACT_CONTRACT_RECONCILIATION_FAILED"

    return {
        "stage": "HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_CONTRACT_RECONCILIATION_FORENSIC_v0.1",
        "mode": "READ-ONLY ARTIFACT CONTRACT FORENSIC",

        "project_root": str(PROJECT_ROOT),
        "producer": str(PRODUCER),
        "target_artifact": str(TARGET),

        "producer_identity": {
            "exists": producer_exists,
            "syntax_valid": syntax_valid(producer),
            "sha256": producer_hash,
        },

        "artifact_identity": {
            "exists": target_exists,
            "valid_json": True,
            "size": TARGET.stat().st_size,
            "sha256": target_hash,
        },

        "top_level_contract": {
            "expected_keys": sorted(EXPECTED_TOP_LEVEL_KEYS),
            "actual_keys": sorted(required_keys),
            "missing_keys": missing_keys,
            "unexpected_keys": unexpected_keys,
            "pass": artifact_schema_ok,
        },

        "artifact_runtime_content": artifact_info,

        "producer_contract_capability": producer_contract,

        "reconciliation": {
            "rows": rows_ok,
            "eligible_rows": eligible_ok,
            "no_trade_rows": no_trade_ok,
            "assets": assets_ok,
            "results": results_ok,
            "decision": decision_ok,
            "no_trade_reasons": reasons_ok,
            "production_db_evidence": production_db_ok,
            "safety_evidence": safety_ok,
            "producer_capable_of_db_evidence": producer_capable_of_evidence,
        },

        "important_finding": {
            "artifact_is_runtime_generated": True,
            "artifact_must_not_be_syntheticly_rebuilt": True,
            "source_modification": False,
            "artifact_modification": False,
            "previous_failure_may_be_checker_contract_mismatch": (
                reconciliation_ok
                and (not production_db_ok or not safety_ok)
            ),
        },

        "safety": {
            "producer_executed": False,
            "producer_imported": False,
            "eligibility_executed": False,
            "artifact_regenerated": False,
            "artifact_modified": False,
            "production_db_writes": "NONE",
            "network_access": "NONE",
            "source_modified": False,
        },

        "final_verdict": verdict,
    }


def main() -> None:

    print("=" * 100)
    print("ARUNDA TRADER")
    print(
        "HISTORICAL ELIGIBILITY RUNTIME OUTPUT ARTIFACT "
        "CONTRACT RECONCILIATION FORENSIC v0.1"
    )
    print("=" * 100)

    report = build_report()

    with REPORT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    reconciliation = report["reconciliation"]

    print(f"Producer SHA256       : {report['producer_identity']['sha256']}")
    print(f"Artifact SHA256       : {report['artifact_identity']['sha256']}")
    print()
    print(f"Top-level contract    : {report['top_level_contract']['pass']}")
    print(f"Rows contract         : {reconciliation['rows']}")
    print(f"Eligible rows         : {reconciliation['eligible_rows']}")
    print(f"No-trade rows         : {reconciliation['no_trade_rows']}")
    print(f"Asset identity        : {reconciliation['assets']}")
    print(f"Result identity       : {reconciliation['results']}")
    print(f"Decision contract     : {reconciliation['decision']}")
    print(f"Reason evidence       : {reconciliation['no_trade_reasons']}")
    print(
        f"Production DB evidence: "
        f"{reconciliation['production_db_evidence']}"
    )
    print(f"Safety evidence       : {reconciliation['safety_evidence']}")
    print()
    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)
    print(
        f"HISTORICAL ELIGIBILITY RUNTIME EVIDENCE : "
        f"{report['final_verdict']}"
    )
    print(f"FORENSIC REPORT : {REPORT}")
    print("=" * 100)


if __name__ == "__main__":
    main()