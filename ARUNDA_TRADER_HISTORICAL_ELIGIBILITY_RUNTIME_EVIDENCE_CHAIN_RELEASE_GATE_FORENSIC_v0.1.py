from pathlib import Path
import hashlib
import json
import ast
import sys
from datetime import datetime, timezone


# =============================================================================
# ARUNDA TRADER
# HISTORICAL ELIGIBILITY RUNTIME EVIDENCE CHAIN RELEASE GATE FORENSIC v0.1
# =============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

ARTIFACT = PROJECT_ROOT / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

SEAL_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_SEAL_FORENSIC_REPORT.json"
)

REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_RELEASE_GATE_FORENSIC_REPORT.json"
)

EXPECTED_PRODUCER_SHA256 = (
    "71ff6dcdd5c49ef6ce06c6085794ceeaf22376e5e0f9dd97d906711e4cc4bdf0"
)

EXPECTED_ARTIFACT_SHA256 = (
    "f77c1b1cc98982b8edcb89c923a7c2ef52e40a654ba5e705a4a0be95490b5417"
)

EXPECTED_CHAIN_SHA256 = (
    "d32d35d36485090bc1ead1d90d03ca91b2fb34bea6f915a124c3e7388e3e54b4"
)

EXPECTED_ARTIFACT = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

EXPECTED_EVIDENCE_REPORTS = [
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_PRODUCER_RUNTIME_OUTPUT_ARTIFACT_GENERATION_RETRY_FORENSIC_REPORT.json",
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_CONTENT_FORENSIC_REPORT.json",
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_REAL_SCHEMA_CONTRACT_FORENSIC_REPORT.json",
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_REAL_SCHEMA_RESULT_CONTRACT_FORENSIC_REPORT.json",
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_RUNTIME_EXECUTION_RECONCILIATION_FORENSIC_REPORT.json",
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
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
        return True
    except Exception:
        return False


def canonical_json_sha256(obj) -> str:
    payload = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def print_header(title: str):
    print("=" * 80)
    print(title)
    print("=" * 80)


# =============================================================================
# MAIN
# =============================================================================

def main():

    started = datetime.now(timezone.utc).isoformat()

    print("=" * 80)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY RUNTIME EVIDENCE CHAIN RELEASE GATE FORENSIC v0.1")
    print("=" * 80)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print(f"PRODUCER     : {PRODUCER}")
    print(f"ARTIFACT     : {ARTIFACT}")
    print(f"SEAL REPORT  : {SEAL_REPORT}")
    print(f"REPORT       : {REPORT}")

    # -------------------------------------------------------------------------
    # SAFETY
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("SAFETY PRECONDITIONS")
    print("=" * 80)

    print("Producer execution : FORBIDDEN")
    print("Producer import    : FORBIDDEN")
    print("Artifact write     : FORBIDDEN")
    print("Artifact delete    : FORBIDDEN")
    print("Production DB write: FORBIDDEN")
    print("Network access     : FORBIDDEN")

    # -------------------------------------------------------------------------
    # EXISTENCE
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("RELEASE INPUT EXISTENCE")
    print("=" * 80)

    producer_exists = PRODUCER.is_file()
    artifact_exists = ARTIFACT.is_file()
    seal_exists = SEAL_REPORT.is_file()

    print(f"Producer exists : {producer_exists}")
    print(f"Artifact exists : {artifact_exists}")
    print(f"Seal exists     : {seal_exists}")

    if not producer_exists:
        raise RuntimeError("Producer missing.")

    if not artifact_exists:
        raise RuntimeError("Artifact missing.")

    if not seal_exists:
        raise RuntimeError("Chain seal report missing.")

    # -------------------------------------------------------------------------
    # PRODUCER IDENTITY
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("PRODUCER IDENTITY")
    print("=" * 80)

    producer_sha = sha256_file(PRODUCER)
    producer_syntax = syntax_valid(PRODUCER)
    producer_identity = (
        producer_sha == EXPECTED_PRODUCER_SHA256
        and producer_syntax
    )

    print(f"Producer SHA256 : {producer_sha}")
    print(f"Expected SHA256 : {EXPECTED_PRODUCER_SHA256}")
    print(f"Producer syntax : {producer_syntax}")
    print(f"Producer identity : {producer_identity}")

    # -------------------------------------------------------------------------
    # ARTIFACT IDENTITY
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("ARTIFACT IDENTITY")
    print("=" * 80)

    artifact_sha = sha256_file(ARTIFACT)

    try:
        artifact = load_json(ARTIFACT)
        artifact_json_valid = True
    except Exception:
        artifact = None
        artifact_json_valid = False

    artifact_identity = (
        artifact_sha == EXPECTED_ARTIFACT_SHA256
        and artifact_json_valid
    )

    print(f"Artifact SHA256 : {artifact_sha}")
    print(f"Expected SHA256 : {EXPECTED_ARTIFACT_SHA256}")
    print(f"Artifact JSON   : {artifact_json_valid}")
    print(f"Artifact identity : {artifact_identity}")

    # -------------------------------------------------------------------------
    # ARTIFACT CONTRACT
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("ARTIFACT CONTRACT")
    print("=" * 80)

    required_keys = {
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

    artifact_top_level_contract = (
        isinstance(artifact, dict)
        and set(artifact.keys()) == required_keys
    )

    row_results = artifact.get("row_results", []) if isinstance(artifact, dict) else []

    assets = [
        row.get("asset")
        for row in row_results
        if isinstance(row, dict)
    ]

    directions = [
        row.get("direction")
        for row in row_results
        if isinstance(row, dict)
    ]

    results = [
        row.get("result")
        for row in row_results
        if isinstance(row, dict)
        and row.get("result") is not None
    ]

    reasons = []

    for row in row_results:
        if isinstance(row, dict):
            row_reasons = row.get("reasons", [])
            if isinstance(row_reasons, list):
                reasons.extend(row_reasons)

    rows_contract = (
        isinstance(artifact.get("rows"), int)
        and artifact["rows"] == len(row_results)
    )

    eligible_contract = (
        isinstance(artifact.get("eligible_rows"), int)
        and artifact["eligible_rows"] == 0
    )

    no_trade_contract = (
        isinstance(artifact.get("no_trade_rows"), int)
        and artifact["no_trade_rows"] == len(row_results)
    )

    asset_identity = assets == ["BTC", "ETH", "SOL", "XRP"]

    direction_identity = directions == [
        "FLAT",
        "SHORT",
        "FLAT",
        "FLAT",
    ]

    aggregate_result_contract = (
        artifact.get("decision") == "NO_TRADE"
        and artifact.get("eligible_rows") == 0
        and artifact.get("no_trade_rows") == len(row_results)
        and len(row_results) == 4
    )

    reason_contract = (
        len(reasons) == 20
        and "CONFIDENCE_BELOW_GATE" in reasons
        and "WEAK_SIGNAL" in reasons
    )

    print(f"Top-level contract : {artifact_top_level_contract}")
    print(f"Rows contract      : {rows_contract}")
    print(f"Eligible rows      : {eligible_contract}")
    print(f"No-trade rows      : {no_trade_contract}")
    print(f"Asset identity     : {asset_identity}")
    print(f"Direction identity : {direction_identity}")
    print(f"Aggregate result   : {aggregate_result_contract}")
    print(f"Reason evidence    : {reason_contract}")

    artifact_contract = all([
        artifact_top_level_contract,
        rows_contract,
        eligible_contract,
        no_trade_contract,
        asset_identity,
        direction_identity,
        aggregate_result_contract,
        reason_contract,
    ])

    # -------------------------------------------------------------------------
    # PRODUCTION DB INVARIANT
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 80)

    production_db = artifact.get("production_db", {})

    before = production_db.get("before", {})
    after = production_db.get("after", {})

    db_before_sha = before.get("sha256")
    db_after_sha = after.get("sha256")

    db_before_size = before.get("size")
    db_after_size = after.get("size")

    db_unchanged = production_db.get("unchanged") is True

    production_db_contract = (
        isinstance(production_db, dict)
        and isinstance(before, dict)
        and isinstance(after, dict)
        and bool(db_before_sha)
        and bool(db_after_sha)
        and db_before_sha == db_after_sha
        and db_before_size == db_after_size
        and db_unchanged
    )

    print(f"Before SHA256 : {db_before_sha}")
    print(f"After SHA256  : {db_after_sha}")
    print(f"Before size   : {db_before_size}")
    print(f"After size    : {db_after_size}")
    print(f"Unchanged     : {db_unchanged}")
    print(f"DB contract   : {production_db_contract}")

    # -------------------------------------------------------------------------
    # SAFETY CONTRACT
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("SAFETY CONTRACT")
    print("=" * 80)

    safety = artifact.get("safety", {})

    safety_expected = {
        "production_db_modified": False,
        "engine_executed": False,
        "historical_repair": False,
        "direction_inference": False,
        "score_reconstruction": False,
        "synthetic_data": False,
        "live_data_injection": False,
        "order_execution": False,
    }

    safety_contract = (
        isinstance(safety, dict)
        and all(
            safety.get(key) is value
            for key, value in safety_expected.items()
        )
    )

    print(f"Safety keys : {sorted(safety.keys()) if isinstance(safety, dict) else []}")

    for key, expected in safety_expected.items():
        print(f"{key} = {safety.get(key)}")

    print(f"Safety contract : {safety_contract}")

    # -------------------------------------------------------------------------
    # EVIDENCE REPORTS
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("SEALED EVIDENCE REPORTS")
    print("=" * 80)

    evidence_status = {}
    evidence_hashes = {}

    for name in EXPECTED_EVIDENCE_REPORTS:

        path = PROJECT_ROOT / name

        exists = path.is_file()
        valid = False
        sha = None
        data = None

        if exists:
            try:
                data = load_json(path)
                valid = True
                sha = sha256_file(path)
            except Exception:
                valid = False

        evidence_status[name] = {
            "exists": exists,
            "valid_json": valid,
            "sha256": sha,
        }

        if sha:
            evidence_hashes[name] = sha

        print(
            f"{name} | "
            f"exists={exists} | "
            f"valid_json={valid} | "
            f"sha256={sha}"
        )

    evidence_chain_contract = all(
        item["exists"] and item["valid_json"]
        for item in evidence_status.values()
    )

    print(f"Evidence chain contract : {evidence_chain_contract}")

    # -------------------------------------------------------------------------
    # SEAL REPORT
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("CHAIN SEAL VALIDATION")
    print("=" * 80)

    seal = load_json(SEAL_REPORT)

    sealed_chain_sha = seal.get("chain_sha256")

    sealed_producer_sha = seal.get("producer_sha256")
    sealed_artifact_sha = seal.get("artifact_sha256")

    sealed_verified = (
        seal.get("chain_verified") is True
        or seal.get("chain_seal", {}).get("chain_verified") is True
        or seal.get("verified") is True
    )

    producer_seal_match = (
        sealed_producer_sha is None
        or sealed_producer_sha == producer_sha
    )

    artifact_seal_match = (
        sealed_artifact_sha is None
        or sealed_artifact_sha == artifact_sha
    )

    chain_hash_match = sealed_chain_sha == EXPECTED_CHAIN_SHA256

    print(f"Sealed chain SHA256 : {sealed_chain_sha}")
    print(f"Expected chain SHA256 : {EXPECTED_CHAIN_SHA256}")
    print(f"Producer seal match : {producer_seal_match}")
    print(f"Artifact seal match : {artifact_seal_match}")
    print(f"Chain hash match    : {chain_hash_match}")
    print(f"Seal verified flag  : {sealed_verified}")

    chain_seal_contract = (
        chain_hash_match
        and producer_seal_match
        and artifact_seal_match
        and sealed_verified
    )

    print(f"Chain seal contract : {chain_seal_contract}")

    # -------------------------------------------------------------------------
    # IMMUTABILITY FINGERPRINT
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("RELEASE BASELINE FINGERPRINT")
    print("=" * 80)

    baseline_payload = {
        "producer_sha256": producer_sha,
        "artifact_sha256": artifact_sha,
        "chain_sha256": sealed_chain_sha,
        "artifact_contract": artifact_contract,
        "production_db_contract": production_db_contract,
        "safety_contract": safety_contract,
        "evidence_chain_contract": evidence_chain_contract,
        "chain_seal_contract": chain_seal_contract,
    }

    release_baseline_sha = canonical_json_sha256(baseline_payload)

    print(f"Release baseline SHA256 : {release_baseline_sha}")

    # -------------------------------------------------------------------------
    # FINAL GATE
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("FINAL RELEASE GATE")
    print("=" * 80)

    release_gate_verified = all([
        producer_identity,
        artifact_identity,
        artifact_contract,
        production_db_contract,
        safety_contract,
        evidence_chain_contract,
        chain_seal_contract,
    ])

    print(f"Producer identity       : {producer_identity}")
    print(f"Artifact identity       : {artifact_identity}")
    print(f"Artifact contract       : {artifact_contract}")
    print(f"Production DB invariant : {production_db_contract}")
    print(f"Safety contract         : {safety_contract}")
    print(f"Evidence chain          : {evidence_chain_contract}")
    print(f"Chain seal              : {chain_seal_contract}")
    print()
    print(f"RELEASE GATE VERIFIED   : {release_gate_verified}")

    verdict = (
        "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_RELEASE_GATE_VERIFIED"
        if release_gate_verified
        else "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_RELEASE_GATE_BLOCKED"
    )

    # -------------------------------------------------------------------------
    # REPORT
    # -------------------------------------------------------------------------

    report_data = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_RELEASE_GATE_FORENSIC",
        "producer": str(PRODUCER),
        "artifact": str(ARTIFACT),
        "seal_report": str(SEAL_REPORT),

        "producer_sha256": producer_sha,
        "expected_producer_sha256": EXPECTED_PRODUCER_SHA256,
        "artifact_sha256": artifact_sha,
        "expected_artifact_sha256": EXPECTED_ARTIFACT_SHA256,

        "chain_sha256": sealed_chain_sha,
        "expected_chain_sha256": EXPECTED_CHAIN_SHA256,

        "artifact_contract": artifact_contract,
        "production_db_contract": production_db_contract,
        "safety_contract": safety_contract,
        "evidence_chain_contract": evidence_chain_contract,
        "chain_seal_contract": chain_seal_contract,

        "release_baseline_sha256": release_baseline_sha,

        "evidence_reports": evidence_status,

        "safety": {
            "producer_execution": False,
            "producer_import": False,
            "artifact_write": False,
            "artifact_delete": False,
            "production_db_write": False,
            "network_access": False,
        },

        "release_gate_verified": release_gate_verified,
        "verdict": verdict,
    }

    # The forensic report itself is the only permitted write.
    REPORT.write_text(
        json.dumps(
            report_data,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    print(f"RELEASE GATE : {verdict}")
    print(f"BASELINE SHA : {release_baseline_sha}")
    print(f"REPORT       : {REPORT}")
    print("=" * 80)

    if not release_gate_verified:
        raise SystemExit(2)


if __name__ == "__main__":
    main()