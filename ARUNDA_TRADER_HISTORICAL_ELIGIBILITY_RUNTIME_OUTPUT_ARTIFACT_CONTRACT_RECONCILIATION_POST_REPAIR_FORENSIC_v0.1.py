from pathlib import Path
import ast
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

VERIFIER = PROJECT_ROOT / (
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_"
    "CONTRACT_RECONCILIATION_FORENSIC_v0.1.py"
)

PRODUCER = PROJECT_ROOT / (
    "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

ARTIFACT = PROJECT_ROOT / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

REPORT = PROJECT_ROOT / (
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_"
    "CONTRACT_RECONCILIATION_POST_REPAIR_FORENSIC_REPORT.json"
)


EXPECTED_ASSETS = ["BTC", "ETH", "SOL", "XRP"]
EXPECTED_RESULTS = ["NO_TRADE", "NO_TRADE", "NO_TRADE", "NO_TRADE"]
EXPECTED_SNAPSHOT = "FUSION-20260824T153800744724+0000-b4f75221aa02defa"
EXPECTED_ROWS = 4


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def syntax_valid(path):
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return True
    except SyntaxError:
        return False


def extract_row_results(artifact):
    rows = artifact.get("row_results")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def inspect_artifact(artifact):
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

    reason_records = []
    for row in row_results:
        reasons = row.get("reasons", [])
        if isinstance(reasons, list):
            reason_records.extend(reasons)

    return {
        "rows": artifact.get("rows"),
        "eligible_rows": artifact.get("eligible_rows"),
        "no_trade_rows": artifact.get("no_trade_rows"),
        "row_results_count": len(row_results),
        "assets": assets,
        "directions": directions,
        "results": results,
        "reason_records": reason_records,
        "decision": artifact.get("decision"),
        "frontier": artifact.get("frontier"),
        "snapshot_id": artifact.get("snapshot_id"),
        "production_db": artifact.get("production_db"),
        "safety": artifact.get("safety"),
    }


def production_db_evidence(info):
    section = info.get("production_db")

    if not isinstance(section, dict):
        return False

    keys = {str(k).lower() for k in section.keys()}

    sha_present = any(
        "sha256" in key
        or "hash" in key
        for key in keys
    )

    return sha_present


def safety_evidence(info):
    section = info.get("safety")

    if not isinstance(section, dict):
        return {
            "exists": False,
            "write": False,
            "order": False,
            "synthetic": False,
            "semantic": False,
            "keys": [],
        }

    normalized = {
        str(k).lower(): v
        for k, v in section.items()
    }

    def truthy_value(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().upper() in {
                "PASS",
                "NONE",
                "NO",
                "FORBIDDEN",
                "NOT_EXECUTED",
                "NOT PERFORMED",
                "NO_TRADE",
            }
        return False

    write = any(
        truthy_value(v)
        for k, v in normalized.items()
        if any(
            token in k
            for token in (
                "write",
                "insert",
                "update",
                "delete",
                "ddl",
                "production_db",
            )
        )
    )

    order = any(
        truthy_value(v)
        for k, v in normalized.items()
        if any(
            token in k
            for token in (
                "order",
                "execution",
                "trade",
            )
        )
    )

    synthetic = any(
        truthy_value(v)
        for k, v in normalized.items()
        if "synthetic" in k
    )

    semantic = write and order and synthetic

    return {
        "exists": True,
        "write": write,
        "order": order,
        "synthetic": synthetic,
        "semantic": semantic,
        "keys": sorted(section.keys()),
    }


def main():
    print("=" * 80)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY RUNTIME OUTPUT ARTIFACT")
    print("CONTRACT RECONCILIATION POST-REPAIR FORENSIC v0.1")
    print("=" * 80)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print(f"VERIFIER     : {VERIFIER}")
    print(f"PRODUCER     : {PRODUCER}")
    print(f"ARTIFACT     : {ARTIFACT}")

    print("=" * 80)
    print("SAFETY")
    print("=" * 80)
    print("Producer execution : FORBIDDEN")
    print("Producer import    : FORBIDDEN")
    print("Artifact write     : FORBIDDEN")
    print("Artifact delete    : FORBIDDEN")
    print("Production DB write: FORBIDDEN")
    print("Network access     : FORBIDDEN")

    if not VERIFIER.exists():
        raise RuntimeError("Verifier does not exist.")

    if not PRODUCER.exists():
        raise RuntimeError("Producer does not exist.")

    if not ARTIFACT.exists():
        raise RuntimeError("Target artifact does not exist.")

    verifier_hash = sha256(VERIFIER)
    producer_hash = sha256(PRODUCER)
    artifact_hash = sha256(ARTIFACT)

    print("=" * 80)
    print("IDENTITY")
    print("=" * 80)
    print(f"Verifier SHA256 : {verifier_hash}")
    print(f"Producer SHA256 : {producer_hash}")
    print(f"Artifact SHA256 : {artifact_hash}")

    if not syntax_valid(VERIFIER):
        raise RuntimeError("Verifier syntax invalid.")

    print(f"Verifier syntax : VALID")

    artifact = load_json(ARTIFACT)

    info = inspect_artifact(artifact)

    print("=" * 80)
    print("ARTIFACT CONTRACT")
    print("=" * 80)

    top_level_expected = {
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

    top_level_actual = set(artifact.keys())

    top_level_ok = (
        isinstance(artifact, dict)
        and top_level_actual == top_level_expected
    )

    rows_ok = (
        info["rows"] == EXPECTED_ROWS
        and info["row_results_count"] == EXPECTED_ROWS
    )

    eligible_ok = info["eligible_rows"] == 0

    no_trade_ok = (
        info["no_trade_rows"] == EXPECTED_ROWS
    )

    assets_ok = (
        info["assets"] == EXPECTED_ASSETS
    )

    results_ok = (
        info["results"] == EXPECTED_RESULTS
        and len(info["results"]) == EXPECTED_ROWS
    )

    decision_ok = (
        info["decision"] == "NO_TRADE"
    )

    reason_ok = (
        "CONFIDENCE_BELOW_GATE" in info["reason_records"]
        and "WEAK_SIGNAL" in info["reason_records"]
    )

    snapshot_ok = (
        info["snapshot_id"] == EXPECTED_SNAPSHOT
    )

    print(f"Top-level contract : {top_level_ok}")
    print(f"Rows contract      : {rows_ok}")
    print(f"Eligible rows      : {eligible_ok}")
    print(f"No-trade rows      : {no_trade_ok}")
    print(f"Asset identity     : {assets_ok}")
    print(f"Result identity    : {results_ok}")
    print(f"Decision contract  : {decision_ok}")
    print(f"Reason evidence    : {reason_ok}")
    print(f"Snapshot identity  : {snapshot_ok}")

    reconciliation_ok = all([
        top_level_ok,
        rows_ok,
        eligible_ok,
        no_trade_ok,
        assets_ok,
        results_ok,
        decision_ok,
        reason_ok,
        snapshot_ok,
    ])

    print("=" * 80)
    print("PRODUCTION DB EVIDENCE")
    print("=" * 80)

    production_ok = production_db_evidence(info)
    print(f"Production DB evidence : {production_ok}")

    print("=" * 80)
    print("SAFETY EVIDENCE")
    print("=" * 80)

    safety = safety_evidence(info)

    print(f"Safety exists          : {safety['exists']}")
    print(f"Write evidence         : {safety['write']}")
    print(f"Order evidence         : {safety['order']}")
    print(f"Synthetic evidence     : {safety['synthetic']}")
    print(f"Semantic safety        : {safety['semantic']}")
    print(f"Safety keys            : {safety['keys']}")

    print("=" * 80)
    print("RECONCILIATION RESULT")
    print("=" * 80)

    print(f"Artifact reconciliation : {reconciliation_ok}")
    print(f"Production DB evidence  : {production_ok}")
    print(f"Safety evidence         : {safety['semantic']}")

    if reconciliation_ok and production_ok and safety["semantic"]:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_CONTRACT_RECONCILIATION_POST_REPAIR_VERIFIED"
        )
    elif reconciliation_ok and production_ok and not safety["semantic"]:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_SAFETY_EVIDENCE_MAPPING_REMAINS_BLOCKED"
        )
    elif reconciliation_ok and not production_ok:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_PRODUCTION_DB_EVIDENCE_MAPPING_REMAINS_BLOCKED"
        )
    else:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_CONTRACT_RECONCILIATION_POST_REPAIR_FAILED"
        )

    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    print(f"HISTORICAL ELIGIBILITY RUNTIME EVIDENCE : {verdict}")

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "verifier": str(VERIFIER),
        "producer": str(PRODUCER),
        "artifact": str(ARTIFACT),
        "verifier_sha256": verifier_hash,
        "producer_sha256": producer_hash,
        "artifact_sha256": artifact_hash,
        "syntax_valid": True,
        "checks": {
            "top_level_contract": top_level_ok,
            "rows_contract": rows_ok,
            "eligible_rows": eligible_ok,
            "no_trade_rows": no_trade_ok,
            "asset_identity": assets_ok,
            "result_identity": results_ok,
            "decision_contract": decision_ok,
            "reason_evidence": reason_ok,
            "snapshot_identity": snapshot_ok,
            "production_db_evidence": production_ok,
            "safety_evidence": safety["semantic"],
        },
        "artifact_summary": info,
        "safety_summary": safety,
        "verdict": verdict,
        "safety": {
            "producer_executed": False,
            "producer_imported": False,
            "artifact_modified": False,
            "artifact_deleted": False,
            "production_db_writes": "NONE",
            "network_access": "NONE",
        },
    }

    with REPORT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"FORENSIC REPORT : {REPORT}")


if __name__ == "__main__":
    main()