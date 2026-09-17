from __future__ import annotations

import hashlib
import json
import ast
from pathlib import Path
from datetime import datetime, timezone


# =============================================================================
# ARUNDA TRADER
# HISTORICAL ELIGIBILITY RUNTIME EVIDENCE CHAIN SEAL FORENSIC v0.1
# =============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

ARTIFACT = (
    PROJECT_ROOT
    / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
)

REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_SEAL_FORENSIC_REPORT.json"
)

EXPECTED_SNAPSHOT = (
    "FUSION-20260824T153800744724+0000-b4f75221aa02defa"
)

EXPECTED_ASSETS = ["BTC", "ETH", "SOL", "XRP"]

EXPECTED_DIRECTIONS = [
    "FLAT",
    "SHORT",
    "FLAT",
    "FLAT",
]

EXPECTED_DECISION = "NO_TRADE"

EXPECTED_PRODUCER_SHA256 = (
    "71ff6dcdd5c49ef6ce06c6085794ceeaf22376e5e0f9dd97d906711e4cc4bdf0"
)

EXPECTED_ARTIFACT_SHA256 = (
    "f77c1b1cc98982b8edcb89c923a7c2ef52e40a654ba5e705a4a0be95490b5417"
)

EXPECTED_DB_SHA256 = (
    "3e4e64aa87e80d36f2987992b7eb365b449cabb36413314b2af739424bd28eb7"
)

EXPECTED_DB_SIZE = 521883648

EVIDENCE_REPORTS = [
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_PRODUCER_RUNTIME_OUTPUT_ARTIFACT_GENERATION_RETRY_FORENSIC_REPORT.json",

    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_CONTENT_FORENSIC_REPORT.json",

    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_REAL_SCHEMA_CONTRACT_FORENSIC_REPORT.json",

    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_REAL_SCHEMA_RESULT_CONTRACT_FORENSIC_REPORT.json",

    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_RUNTIME_EXECUTION_RECONCILIATION_FORENSIC_REPORT.json",
]


# =============================================================================
# UTILITIES
# =============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def syntax_valid(path: Path) -> bool:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return True
    except Exception:
        return False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def section(title: str):
    print("=" * 80)
    print(title)


# =============================================================================
# ARTIFACT CONTRACT
# =============================================================================

def inspect_artifact(artifact: dict) -> dict:

    row_results = artifact.get("row_results")

    assets = []
    directions = []
    reasons = []

    if isinstance(row_results, list):
        for row in row_results:
            if not isinstance(row, dict):
                continue

            assets.append(row.get("asset"))
            directions.append(row.get("direction"))

            row_reasons = row.get("reasons", [])
            if isinstance(row_reasons, list):
                reasons.extend(row_reasons)

    top_keys_expected = {
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

    top_contract = (
        isinstance(artifact, dict)
        and set(artifact.keys()) == top_keys_expected
    )

    rows_contract = (
        isinstance(artifact.get("rows"), int)
        and artifact["rows"] == 4
        and isinstance(row_results, list)
        and len(row_results) == 4
    )

    eligible_contract = (
        isinstance(artifact.get("eligible_rows"), int)
        and artifact["eligible_rows"] == 0
    )

    no_trade_contract = (
        isinstance(artifact.get("no_trade_rows"), int)
        and artifact["no_trade_rows"] == 4
    )

    asset_identity = assets == EXPECTED_ASSETS
    direction_identity = directions == EXPECTED_DIRECTIONS

    decision_contract = (
        artifact.get("decision") == EXPECTED_DECISION
    )

    reason_contract = (
        len(reasons) == 20
        and "CONFIDENCE_BELOW_GATE" in reasons
        and "WEAK_SIGNAL" in reasons
    )

    production_db = artifact.get("production_db")

    db_contract = (
        isinstance(production_db, dict)
        and production_db.get("unchanged") is True
        and isinstance(production_db.get("before"), dict)
        and isinstance(production_db.get("after"), dict)
        and production_db["before"].get("sha256") == EXPECTED_DB_SHA256
        and production_db["after"].get("sha256") == EXPECTED_DB_SHA256
        and production_db["before"].get("size") == EXPECTED_DB_SIZE
        and production_db["after"].get("size") == EXPECTED_DB_SIZE
    )

    safety = artifact.get("safety")

    safety_contract = (
        isinstance(safety, dict)
        and safety.get("production_db_modified") is False
        and safety.get("engine_executed") is False
        and safety.get("historical_repair") is False
        and safety.get("direction_inference") is False
        and safety.get("score_reconstruction") is False
        and safety.get("synthetic_data") is False
        and safety.get("live_data_injection") is False
        and safety.get("order_execution") is False
    )

    return {
        "top_contract": top_contract,
        "rows_contract": rows_contract,
        "eligible_contract": eligible_contract,
        "no_trade_contract": no_trade_contract,
        "asset_identity": asset_identity,
        "direction_identity": direction_identity,
        "decision_contract": decision_contract,
        "reason_contract": reason_contract,
        "production_db_contract": db_contract,
        "safety_contract": safety_contract,
        "snapshot_identity": (
            artifact.get("snapshot_id") == EXPECTED_SNAPSHOT
        ),
        "rows": artifact.get("rows"),
        "eligible_rows": artifact.get("eligible_rows"),
        "no_trade_rows": artifact.get("no_trade_rows"),
        "assets": assets,
        "directions": directions,
        "reason_count": len(reasons),
        "decision": artifact.get("decision"),
        "snapshot_id": artifact.get("snapshot_id"),
    }


# =============================================================================
# EVIDENCE REPORT RECONCILIATION
# =============================================================================

def inspect_evidence_reports() -> dict:

    loaded = []
    missing = []

    for path in EVIDENCE_REPORTS:
        if not path.exists():
            missing.append(str(path))
            continue

        try:
            data = load_json(path)
            loaded.append({
                "path": str(path),
                "sha256": sha256_file(path),
                "json": isinstance(data, (dict, list)),
                "data": data,
            })
        except Exception as exc:
            loaded.append({
                "path": str(path),
                "sha256": None,
                "json": False,
                "data": None,
                "error": repr(exc),
            })

    snapshot_hits = 0
    decision_hits = 0
    safety_hits = 0
    reconciliation_hits = 0

    for item in loaded:
        data = item.get("data")

        if not isinstance(data, dict):
            continue

        text = json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
        )

        if EXPECTED_SNAPSHOT in text:
            snapshot_hits += 1

        if EXPECTED_DECISION in text:
            decision_hits += 1

        if (
            "production_db_modified" in text
            and "order_execution" in text
        ):
            safety_hits += 1

        if "RUNTIME_OUTPUT_ARTIFACT_RUNTIME_EXECUTION_RECONCILIATION_VERIFIED" in text:
            reconciliation_hits += 1

    return {
        "expected_reports": len(EVIDENCE_REPORTS),
        "loaded_reports": len(loaded),
        "missing_reports": missing,
        "snapshot_evidence_hits": snapshot_hits,
        "decision_evidence_hits": decision_hits,
        "safety_evidence_hits": safety_hits,
        "reconciliation_evidence_hits": reconciliation_hits,
        "all_expected_reports_present": (
            len(missing) == 0
        ),
        "loaded": [
            {
                "path": item["path"],
                "sha256": item["sha256"],
                "json": item["json"],
            }
            for item in loaded
        ],
    }


# =============================================================================
# CHAIN SEAL
# =============================================================================

def build_chain_seal(
    producer_sha256: str,
    artifact_sha256: str,
    evidence: dict,
    artifact_info: dict,
) -> dict:

    chain_material = {
        "producer_sha256": producer_sha256,
        "artifact_sha256": artifact_sha256,
        "artifact_snapshot": artifact_info["snapshot_id"],
        "artifact_rows": artifact_info["rows"],
        "artifact_eligible_rows": artifact_info["eligible_rows"],
        "artifact_no_trade_rows": artifact_info["no_trade_rows"],
        "artifact_assets": artifact_info["assets"],
        "artifact_directions": artifact_info["directions"],
        "artifact_decision": artifact_info["decision"],
        "production_db_sha256": EXPECTED_DB_SHA256,
        "production_db_size": EXPECTED_DB_SIZE,
        "evidence_report_sha256": [
            item["sha256"]
            for item in evidence["loaded"]
        ],
    }

    canonical = json.dumps(
        chain_material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    chain_sha256 = hashlib.sha256(canonical).hexdigest()

    return {
        "algorithm": "SHA256",
        "canonical_material": chain_material,
        "chain_sha256": chain_sha256,
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    section(
        "ARUNDA TRADER\n"
        "HISTORICAL ELIGIBILITY RUNTIME EVIDENCE CHAIN SEAL FORENSIC v0.1"
    )

    print("PROJECT ROOT :", PROJECT_ROOT)
    print("PRODUCER     :", PRODUCER)
    print("ARTIFACT     :", ARTIFACT)
    print("REPORT       :", REPORT)

    section("SAFETY PRECONDITIONS")

    print("Producer execution : FORBIDDEN")
    print("Producer import    : FORBIDDEN")
    print("Artifact write     : FORBIDDEN")
    print("Artifact delete    : FORBIDDEN")
    print("Production DB write: FORBIDDEN")
    print("Network access     : FORBIDDEN")

    if not PROJECT_ROOT.exists():
        raise RuntimeError("Project root does not exist.")

    if not PRODUCER.exists():
        raise RuntimeError("Producer does not exist.")

    if not ARTIFACT.exists():
        raise RuntimeError("Runtime artifact does not exist.")

    section("IDENTITY")

    producer_sha256 = sha256_file(PRODUCER)
    artifact_sha256 = sha256_file(ARTIFACT)

    producer_syntax = syntax_valid(PRODUCER)

    print("Producer SHA256 :", producer_sha256)
    print("Expected SHA256 :", EXPECTED_PRODUCER_SHA256)
    print("Producer syntax :", producer_syntax)

    print("Artifact SHA256 :", artifact_sha256)
    print("Expected SHA256 :", EXPECTED_ARTIFACT_SHA256)

    producer_identity = (
        producer_sha256 == EXPECTED_PRODUCER_SHA256
        and producer_syntax
    )

    artifact_identity = (
        artifact_sha256 == EXPECTED_ARTIFACT_SHA256
    )

    if not producer_identity:
        raise RuntimeError(
            "Producer identity changed unexpectedly."
        )

    if not artifact_identity:
        raise RuntimeError(
            "Artifact identity changed unexpectedly."
        )

    section("ARTIFACT CONTRACT")

    artifact = load_json(ARTIFACT)

    if not isinstance(artifact, dict):
        raise RuntimeError("Artifact is not a JSON object.")

    artifact_info = inspect_artifact(artifact)

    print("Top-level contract       :", artifact_info["top_contract"])
    print("Rows contract            :", artifact_info["rows_contract"])
    print("Eligible rows contract   :", artifact_info["eligible_contract"])
    print("No-trade rows contract   :", artifact_info["no_trade_contract"])
    print("Asset identity           :", artifact_info["asset_identity"])
    print("Direction identity       :", artifact_info["direction_identity"])
    print("Decision contract        :", artifact_info["decision_contract"])
    print("Reason evidence          :", artifact_info["reason_contract"])
    print("Snapshot identity        :", artifact_info["snapshot_identity"])
    print("Production DB contract   :", artifact_info["production_db_contract"])
    print("Safety contract          :", artifact_info["safety_contract"])

    artifact_contract = all(
        [
            artifact_info["top_contract"],
            artifact_info["rows_contract"],
            artifact_info["eligible_contract"],
            artifact_info["no_trade_contract"],
            artifact_info["asset_identity"],
            artifact_info["direction_identity"],
            artifact_info["decision_contract"],
            artifact_info["reason_contract"],
            artifact_info["snapshot_identity"],
            artifact_info["production_db_contract"],
            artifact_info["safety_contract"],
        ]
    )

    section("EVIDENCE CHAIN DISCOVERY")

    evidence = inspect_evidence_reports()

    print(
        "Expected evidence reports :",
        evidence["expected_reports"],
    )

    print(
        "Loaded evidence reports   :",
        evidence["loaded_reports"],
    )

    print(
        "Missing evidence reports :",
        len(evidence["missing_reports"]),
    )

    print(
        "Snapshot evidence hits   :",
        evidence["snapshot_evidence_hits"],
    )

    print(
        "Decision evidence hits   :",
        evidence["decision_evidence_hits"],
    )

    print(
        "Safety evidence hits     :",
        evidence["safety_evidence_hits"],
    )

    print(
        "Reconciliation hits      :",
        evidence["reconciliation_evidence_hits"],
    )

    evidence_chain_contract = (
        evidence["all_expected_reports_present"]
        and evidence["snapshot_evidence_hits"] >= 1
        and evidence["decision_evidence_hits"] >= 1
        and evidence["safety_evidence_hits"] >= 1
        and evidence["reconciliation_evidence_hits"] >= 1
    )

    section("RUNTIME ↔ ARTIFACT CHAIN")

    runtime_identity = (
        artifact_info["snapshot_identity"]
        and artifact_info["asset_identity"]
        and artifact_info["direction_identity"]
        and artifact_info["rows_contract"]
        and artifact_info["eligible_contract"]
        and artifact_info["no_trade_contract"]
        and artifact_info["decision_contract"]
        and artifact_info["reason_contract"]
    )

    print("Snapshot identity :", artifact_info["snapshot_identity"])
    print("Asset identity    :", artifact_info["asset_identity"])
    print("Direction identity:", artifact_info["direction_identity"])
    print("Rows identity     :", artifact_info["rows_contract"])
    print("Decision identity :", artifact_info["decision_contract"])
    print("Reason identity   :", artifact_info["reason_contract"])
    print("Runtime chain     :", runtime_identity)

    section("CHAIN SEAL")

    seal = build_chain_seal(
        producer_sha256,
        artifact_sha256,
        evidence,
        artifact_info,
    )

    print("Algorithm         :", seal["algorithm"])
    print("CHAIN SHA256      :", seal["chain_sha256"])

    final_verified = (
        producer_identity
        and artifact_identity
        and artifact_contract
        and evidence_chain_contract
        and runtime_identity
    )

    section("FINAL DETERMINISTIC VERIFICATION")

    print("Producer identity       :", producer_identity)
    print("Artifact identity       :", artifact_identity)
    print("Artifact contract       :", artifact_contract)
    print("Evidence chain contract :", evidence_chain_contract)
    print("Runtime identity        :", runtime_identity)

    print()
    print("CHAIN VERIFIED          :", final_verified)

    verdict = (
        "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_SEALED_VERIFIED"
        if final_verified
        else
        "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_SEAL_FAILED"
    )

    report = {
        "forensic": {
            "name": (
                "HISTORICAL ELIGIBILITY RUNTIME "
                "EVIDENCE CHAIN SEAL FORENSIC v0.1"
            ),
            "mode": "READ_ONLY_EVIDENCE_CHAIN_SEAL",
            "timestamp_utc": utc_now(),
        },
        "identity": {
            "project_root": str(PROJECT_ROOT),
            "producer": str(PRODUCER),
            "artifact": str(ARTIFACT),
            "producer_sha256": producer_sha256,
            "artifact_sha256": artifact_sha256,
            "producer_syntax_valid": producer_syntax,
        },
        "artifact": artifact_info,
        "evidence_chain": evidence,
        "chain_seal": seal,
        "verification": {
            "producer_identity": producer_identity,
            "artifact_identity": artifact_identity,
            "artifact_contract": artifact_contract,
            "evidence_chain_contract": evidence_chain_contract,
            "runtime_identity": runtime_identity,
            "verified": final_verified,
        },
        "safety": {
            "producer_executed": False,
            "producer_imported": False,
            "artifact_modified": False,
            "artifact_deleted": False,
            "production_db_written": False,
            "network_access": False,
        },
        "verdict": verdict,
    }

    # The forensic report itself is the only file this script writes.
    REPORT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    section("FINAL VERDICT")

    print("HISTORICAL ELIGIBILITY RUNTIME EVIDENCE")
    print(" :", verdict)
    print("CHAIN SHA256 :", seal["chain_sha256"])
    print("REPORT       :", REPORT)

    if not final_verified:
        raise SystemExit(2)


if __name__ == "__main__":
    main()