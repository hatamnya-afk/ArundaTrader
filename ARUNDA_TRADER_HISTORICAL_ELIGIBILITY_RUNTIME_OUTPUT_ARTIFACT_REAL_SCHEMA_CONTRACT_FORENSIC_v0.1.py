from pathlib import Path
import ast
import hashlib
import json
from datetime import datetime, timezone


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER = PROJECT_ROOT / (
    "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

ARTIFACT = PROJECT_ROOT / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

REPORT = PROJECT_ROOT / (
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_"
    "REAL_SCHEMA_CONTRACT_FORENSIC_REPORT.json"
)


EXPECTED_ASSETS = ["BTC", "ETH", "SOL", "XRP"]
EXPECTED_RESULTS = ["NO_TRADE"] * 4
EXPECTED_ROWS = 4
EXPECTED_SNAPSHOT = "FUSION-20260824T153800744724+0000-b4f75221aa02defa"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def syntax_valid(path):
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return True
    except SyntaxError:
        return False


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalized(value):
    if isinstance(value, str):
        return value.strip().upper()
    return value


def extract_row_results(artifact):
    rows = artifact.get("row_results")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def inspect_rows(artifact):
    rows = extract_row_results(artifact)

    assets = [
        row.get("asset")
        for row in rows
        if row.get("asset") is not None
    ]

    results = [
        normalized(row.get("result"))
        for row in rows
        if row.get("result") is not None
    ]

    directions = [
        normalized(row.get("direction"))
        for row in rows
        if row.get("direction") is not None
    ]

    reasons = []

    for row in rows:
        value = row.get("reasons", [])

        if isinstance(value, list):
            reasons.extend(
                normalized(x)
                for x in value
                if isinstance(x, str)
            )

    return {
        "count": len(rows),
        "assets": assets,
        "results": results,
        "directions": directions,
        "reasons": reasons,
    }


def inspect_production_db(section):
    if not isinstance(section, dict):
        return {
            "exists": False,
            "keys": [],
            "values": {},
            "evidence": False,
        }

    values = dict(section)

    key_names = {
        str(k).lower()
        for k in section.keys()
    }

    evidence = any(
        token in key
        for key in key_names
        for token in (
            "sha256",
            "hash",
            "fingerprint",
            "size",
            "rows",
            "invariant",
        )
    )

    return {
        "exists": True,
        "keys": sorted(section.keys()),
        "values": values,
        "evidence": evidence,
    }


def inspect_safety(section):
    if not isinstance(section, dict):
        return {
            "exists": False,
            "keys": [],
            "values": {},
            "production_db_modified": None,
            "order_execution": None,
            "synthetic_data": None,
            "semantic_no_write": False,
            "semantic_no_order": False,
            "semantic_no_synthetic": False,
        }

    values = dict(section)

    def safe_text(key):
        value = section.get(key)
        if isinstance(value, str):
            return value.strip().upper()
        return value

    db_modified = safe_text("production_db_modified")
    order_execution = safe_text("order_execution")
    synthetic_data = safe_text("synthetic_data")

    no_write = db_modified in {
        False,
        "NONE",
        "NO",
        "FALSE",
        "NOT_MODIFIED",
        "NOT MODIFIED",
    }

    no_order = order_execution in {
        False,
        "NONE",
        "NO",
        "FALSE",
        "NOT_EXECUTED",
        "NOT EXECUTED",
        "FORBIDDEN",
    }

    no_synthetic = synthetic_data in {
        False,
        "NONE",
        "NO",
        "FALSE",
        "FORBIDDEN",
    }

    return {
        "exists": True,
        "keys": sorted(section.keys()),
        "values": values,
        "production_db_modified": db_modified,
        "order_execution": order_execution,
        "synthetic_data": synthetic_data,
        "semantic_no_write": no_write,
        "semantic_no_order": no_order,
        "semantic_no_synthetic": no_synthetic,
    }


def main():
    print("=" * 80)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY RUNTIME OUTPUT ARTIFACT")
    print("REAL SCHEMA / CONTRACT FORENSIC v0.1")
    print("=" * 80)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
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

    if not PRODUCER.exists():
        raise RuntimeError("Producer missing.")

    if not ARTIFACT.exists():
        raise RuntimeError("Artifact missing.")

    producer_hash = sha256(PRODUCER)
    artifact_hash = sha256(ARTIFACT)

    producer_syntax = syntax_valid(PRODUCER)

    artifact = load_json(ARTIFACT)

    print("=" * 80)
    print("IDENTITY")
    print("=" * 80)
    print(f"Producer SHA256 : {producer_hash}")
    print(f"Artifact SHA256 : {artifact_hash}")
    print(f"Producer syntax : {producer_syntax}")
    print(f"Artifact JSON   : {isinstance(artifact, dict)}")

    print("=" * 80)
    print("TOP-LEVEL REAL SCHEMA")
    print("=" * 80)

    top_keys = sorted(artifact.keys())

    for key in top_keys:
        value = artifact[key]
        print(
            f"{key:24} "
            f"type={type(value).__name__:10} "
            f"present=True"
        )

    rows = inspect_rows(artifact)

    print("=" * 80)
    print("REAL ROW RESULT SCHEMA")
    print("=" * 80)

    print(f"row_results count : {rows['count']}")
    print(f"assets            : {rows['assets']}")
    print(f"results           : {rows['results']}")
    print(f"directions        : {rows['directions']}")
    print(f"reason count      : {len(rows['reasons'])}")

    print("=" * 80)
    print("RESULT CONTRACT")
    print("=" * 80)

    result_identity = (
        rows["count"] == EXPECTED_ROWS
        and rows["assets"] == EXPECTED_ASSETS
        and rows["results"] == EXPECTED_RESULTS
        and len(rows["results"]) == EXPECTED_ROWS
    )

    print(f"Expected results : {EXPECTED_RESULTS}")
    print(f"Actual results   : {rows['results']}")
    print(f"RESULT IDENTITY  : {result_identity}")

    print("=" * 80)
    print("PRODUCTION DB REAL SCHEMA")
    print("=" * 80)

    production_info = inspect_production_db(
        artifact.get("production_db")
    )

    print(f"Exists   : {production_info['exists']}")
    print(f"Keys     : {production_info['keys']}")
    print(f"Evidence : {production_info['evidence']}")

    for key, value in production_info["values"].items():
        print(f"{key} = {value}")

    print("=" * 80)
    print("SAFETY REAL SCHEMA")
    print("=" * 80)

    safety_info = inspect_safety(
        artifact.get("safety")
    )

    print(f"Exists : {safety_info['exists']}")
    print(f"Keys   : {safety_info['keys']}")

    for key, value in safety_info["values"].items():
        print(f"{key} = {value}")

    print("=" * 80)
    print("SEMANTIC SAFETY")
    print("=" * 80)

    print(
        "production_db_modified = NONE/false :",
        safety_info["semantic_no_write"],
    )

    print(
        "order_execution = NONE/false        :",
        safety_info["semantic_no_order"],
    )

    print(
        "synthetic_data = NONE/false         :",
        safety_info["semantic_no_synthetic"],
    )

    safety_contract = all([
        safety_info["semantic_no_write"],
        safety_info["semantic_no_order"],
        safety_info["semantic_no_synthetic"],
    ])

    print(f"REAL SAFETY CONTRACT : {safety_contract}")

    print("=" * 80)
    print("CORE RUNTIME IDENTITY")
    print("=" * 80)

    snapshot_ok = (
        artifact.get("snapshot_id") == EXPECTED_SNAPSHOT
    )

    rows_ok = (
        artifact.get("rows") == EXPECTED_ROWS
    )

    eligible_ok = (
        artifact.get("eligible_rows") == 0
    )

    no_trade_ok = (
        artifact.get("no_trade_rows") == EXPECTED_ROWS
    )

    decision_ok = (
        normalized(artifact.get("decision")) == "NO_TRADE"
    )

    reasons_ok = (
        "CONFIDENCE_BELOW_GATE" in rows["reasons"]
        and "WEAK_SIGNAL" in rows["reasons"]
    )

    print(f"Snapshot identity : {snapshot_ok}")
    print(f"Rows identity     : {rows_ok}")
    print(f"Eligible rows     : {eligible_ok}")
    print(f"No-trade rows     : {no_trade_ok}")
    print(f"Decision          : {decision_ok}")
    print(f"Reasons           : {reasons_ok}")

    core_contract = all([
        snapshot_ok,
        rows_ok,
        eligible_ok,
        no_trade_ok,
        result_identity,
        decision_ok,
        reasons_ok,
    ])

    print(f"CORE CONTRACT : {core_contract}")

    print("=" * 80)
    print("FINAL DETERMINISTIC VERDICT")
    print("=" * 80)

    if core_contract and production_info["evidence"] and safety_contract:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_REAL_SCHEMA_CONTRACT_VERIFIED"
        )
    elif core_contract and not production_info["evidence"]:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_PRODUCTION_DB_SCHEMA_MAPPING_REQUIRED"
        )
    elif core_contract and production_info["evidence"] and not safety_contract:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_SAFETY_SCHEMA_MAPPING_REQUIRED"
        )
    else:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_REAL_SCHEMA_CONTRACT_FAILED"
        )

    print(
        "HISTORICAL ELIGIBILITY RUNTIME EVIDENCE :",
        verdict,
    )

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "producer": str(PRODUCER),
        "artifact": str(ARTIFACT),
        "producer_sha256": producer_hash,
        "artifact_sha256": artifact_hash,
        "producer_syntax_valid": producer_syntax,
        "artifact_is_object": isinstance(artifact, dict),
        "top_level_keys": top_keys,
        "row_schema": rows,
        "result_identity": result_identity,
        "production_db": production_info,
        "safety": safety_info,
        "checks": {
            "snapshot_identity": snapshot_ok,
            "rows_identity": rows_ok,
            "eligible_rows": eligible_ok,
            "no_trade_rows": no_trade_ok,
            "result_identity": result_identity,
            "decision_identity": decision_ok,
            "reason_evidence": reasons_ok,
            "core_contract": core_contract,
            "production_db_evidence": production_info["evidence"],
            "safety_contract": safety_contract,
        },
        "verdict": verdict,
        "safety_boundary": {
            "producer_executed": False,
            "producer_imported": False,
            "artifact_modified": False,
            "artifact_deleted": False,
            "production_db_writes": "NONE",
            "network_access": "NONE",
        },
    }

    with REPORT.open("w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"FORENSIC REPORT : {REPORT}")


if __name__ == "__main__":
    main()