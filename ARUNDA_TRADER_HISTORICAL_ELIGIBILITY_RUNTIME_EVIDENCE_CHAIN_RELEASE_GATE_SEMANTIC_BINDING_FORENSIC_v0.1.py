from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER = PROJECT_ROOT / (
    "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

ARTIFACT = PROJECT_ROOT / (
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
)

SEAL_REPORT = PROJECT_ROOT / (
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_SEAL_FORENSIC_REPORT.json"
)

REPORT = PROJECT_ROOT / (
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_RELEASE_GATE_SEMANTIC_BINDING_FORENSIC_REPORT.json"
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

EXPECTED_EVIDENCE_REPORTS = [
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_PRODUCER_RUNTIME_OUTPUT_ARTIFACT_GENERATION_RETRY_FORENSIC_REPORT.json",
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_CONTENT_FORENSIC_REPORT.json",
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_REAL_SCHEMA_CONTRACT_FORENSIC_REPORT.json",
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_REAL_SCHEMA_RESULT_CONTRACT_FORENSIC_REPORT.json",
    "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_RUNTIME_EXECUTION_RECONCILIATION_FORENSIC_REPORT.json",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def syntax_valid(path: Path) -> bool:
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
        return True
    except Exception:
        return False


def get_path(obj: Any, path: str) -> Any:
    """
    Deterministic dotted-path accessor.

    Example:
        chain_seal.chain_sha256
    """
    current = obj

    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)

    return current


def bool_field(obj: dict, path: str) -> bool:
    return get_path(obj, path) is True


def main() -> None:

    print("=" * 80)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY RUNTIME EVIDENCE CHAIN")
    print("RELEASE GATE SEMANTIC BINDING FORENSIC v0.1")
    print("=" * 80)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print(f"PRODUCER     : {PRODUCER}")
    print(f"ARTIFACT     : {ARTIFACT}")
    print(f"SEAL REPORT  : {SEAL_REPORT}")
    print(f"REPORT       : {REPORT}")

    print("=" * 80)
    print("SAFETY PRECONDITIONS")
    print("=" * 80)

    print("Producer execution : FORBIDDEN")
    print("Producer import    : FORBIDDEN")
    print("Artifact write     : FORBIDDEN")
    print("Artifact delete    : FORBIDDEN")
    print("Production DB write: FORBIDDEN")
    print("Network access     : FORBIDDEN")

    # ------------------------------------------------------------------
    # Existence
    # ------------------------------------------------------------------

    producer_exists = PRODUCER.is_file()
    artifact_exists = ARTIFACT.is_file()
    seal_exists = SEAL_REPORT.is_file()

    print("=" * 80)
    print("INPUT EXISTENCE")
    print("=" * 80)

    print("Producer exists :", producer_exists)
    print("Artifact exists :", artifact_exists)
    print("Seal exists     :", seal_exists)

    if not all([producer_exists, artifact_exists, seal_exists]):
        raise RuntimeError("Required release-gate inputs are missing.")

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    producer_sha = sha256_file(PRODUCER)
    artifact_sha = sha256_file(ARTIFACT)
    seal_sha = sha256_file(SEAL_REPORT)

    producer_syntax = syntax_valid(PRODUCER)

    print("=" * 80)
    print("IDENTITY")
    print("=" * 80)

    print("Producer SHA256 :", producer_sha)
    print("Expected SHA256 :", EXPECTED_PRODUCER_SHA256)
    print("Producer syntax :", producer_syntax)

    print("Artifact SHA256 :", artifact_sha)
    print("Expected SHA256 :", EXPECTED_ARTIFACT_SHA256)

    print("Seal report SHA256 :", seal_sha)

    producer_identity = (
        producer_sha == EXPECTED_PRODUCER_SHA256
        and producer_syntax
    )

    artifact_identity = (
        artifact_sha == EXPECTED_ARTIFACT_SHA256
    )

    # ------------------------------------------------------------------
    # Load seal
    # ------------------------------------------------------------------

    seal = load_json(SEAL_REPORT)

    if not isinstance(seal, dict):
        raise RuntimeError("Seal report root is not a JSON object.")

    print("=" * 80)
    print("REAL SEAL SCHEMA")
    print("=" * 80)

    print("Top-level keys :", sorted(seal.keys()))

    # ------------------------------------------------------------------
    # Exact real schema bindings
    # ------------------------------------------------------------------

    actual_chain_sha = get_path(
        seal,
        "chain_seal.chain_sha256",
    )

    verified = get_path(
        seal,
        "verification.verified",
    )

    runtime_identity = get_path(
        seal,
        "verification.runtime_identity",
    )

    artifact_contract = get_path(
        seal,
        "verification.artifact_contract",
    )

    evidence_contract = get_path(
        seal,
        "verification.evidence_chain_contract",
    )

    evidence_present = get_path(
        seal,
        "evidence_chain.all_expected_reports_present",
    )

    producer_seal_sha = get_path(
        seal,
        "identity.producer_sha256",
    )

    artifact_seal_sha = get_path(
        seal,
        "identity.artifact_sha256",
    )

    canonical = get_path(
        seal,
        "chain_seal.canonical_material",
    )

    if not isinstance(canonical, dict):
        canonical = {}

    canonical_producer_sha = canonical.get(
        "producer_sha256"
    )

    canonical_artifact_sha = canonical.get(
        "artifact_sha256"
    )

    print("=" * 80)
    print("EXACT SEMANTIC FIELD BINDING")
    print("=" * 80)

    print(
        "chain_seal.chain_sha256 :",
        actual_chain_sha,
    )

    print(
        "verification.verified :",
        verified,
    )

    print(
        "verification.runtime_identity :",
        runtime_identity,
    )

    print(
        "verification.artifact_contract :",
        artifact_contract,
    )

    print(
        "verification.evidence_chain_contract :",
        evidence_contract,
    )

    print(
        "evidence_chain.all_expected_reports_present :",
        evidence_present,
    )

    # ------------------------------------------------------------------
    # Exact chain comparison
    # ------------------------------------------------------------------

    chain_hash_match = (
        actual_chain_sha == EXPECTED_CHAIN_SHA256
    )

    producer_seal_match = (
        producer_seal_sha == producer_sha
        == canonical_producer_sha
    )

    artifact_seal_match = (
        artifact_seal_sha == artifact_sha
        == canonical_artifact_sha
    )

    # ------------------------------------------------------------------
    # Evidence existence + hashes
    # ------------------------------------------------------------------

    evidence_results = []

    for filename in EXPECTED_EVIDENCE_REPORTS:

        path = PROJECT_ROOT / filename

        exists = path.is_file()

        if exists:
            digest = sha256_file(path)

            try:
                payload = load_json(path)
                valid_json = True
            except Exception:
                payload = None
                valid_json = False

        else:
            digest = None
            payload = None
            valid_json = False

        evidence_results.append(
            {
                "name": filename,
                "exists": exists,
                "valid_json": valid_json,
                "sha256": digest,
            }
        )

    evidence_contract_real = (
        len(evidence_results)
        == len(EXPECTED_EVIDENCE_REPORTS)
        and all(
            item["exists"] and item["valid_json"]
            for item in evidence_results
        )
        and evidence_present is True
    )

    # ------------------------------------------------------------------
    # Final semantic mapping
    # ------------------------------------------------------------------

    semantic_binding = (
        chain_hash_match
        and producer_seal_match
        and artifact_seal_match
        and verified is True
        and runtime_identity is True
        and artifact_contract is True
        and evidence_contract is True
        and evidence_contract_real
    )

    print("=" * 80)
    print("CHAIN SEMANTIC BINDING")
    print("=" * 80)

    print("Expected chain SHA256 :", EXPECTED_CHAIN_SHA256)
    print("Actual chain SHA256   :", actual_chain_sha)
    print("Chain hash match      :", chain_hash_match)

    print("Producer seal match   :", producer_seal_match)
    print("Artifact seal match   :", artifact_seal_match)
    print("Verified flag         :", verified is True)
    print("Runtime identity      :", runtime_identity is True)
    print("Artifact contract     :", artifact_contract is True)
    print("Evidence contract     :", evidence_contract is True)
    print("Evidence files        :", evidence_contract_real)

    print("=" * 80)
    print("DETERMINISTIC RELEASE-GATE MAPPING")
    print("=" * 80)

    if semantic_binding:
        mapping_state = "SEMANTIC_BINDING_VERIFIED"
        repair_required = False
    else:
        mapping_state = "SEMANTIC_BINDING_FAILED"
        repair_required = True

    print("Mapping state  :", mapping_state)
    print("Repair required:", repair_required)

    # ------------------------------------------------------------------
    # Safety assertion
    # ------------------------------------------------------------------

    safety = {
        "producer_executed": False,
        "producer_imported": False,
        "artifact_modified": False,
        "artifact_deleted": False,
        "seal_report_modified": False,
        "production_db_written": False,
        "network_access": False,
    }

    safety_contract = all(
        value is False
        for value in safety.values()
    )

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    report = {
        "forensic": {
            "name": (
                "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_"
                "RELEASE_GATE_SEMANTIC_BINDING_FORENSIC_v0.1"
            ),
            "mode": "READ_ONLY",
        },
        "identity": {
            "producer_sha256": producer_sha,
            "expected_producer_sha256": EXPECTED_PRODUCER_SHA256,
            "artifact_sha256": artifact_sha,
            "expected_artifact_sha256": EXPECTED_ARTIFACT_SHA256,
            "seal_report_sha256": seal_sha,
            "producer_identity": producer_identity,
            "artifact_identity": artifact_identity,
        },
        "real_schema_binding": {
            "chain_sha256_path": "chain_seal.chain_sha256",
            "verified_path": "verification.verified",
            "runtime_identity_path": "verification.runtime_identity",
            "artifact_contract_path": "verification.artifact_contract",
            "evidence_contract_path": (
                "verification.evidence_chain_contract"
            ),
            "evidence_presence_path": (
                "evidence_chain.all_expected_reports_present"
            ),
        },
        "chain": {
            "expected_chain_sha256": EXPECTED_CHAIN_SHA256,
            "actual_chain_sha256": actual_chain_sha,
            "chain_hash_match": chain_hash_match,
            "producer_seal_match": producer_seal_match,
            "artifact_seal_match": artifact_seal_match,
        },
        "verification": {
            "verified": verified is True,
            "runtime_identity": runtime_identity is True,
            "artifact_contract": artifact_contract is True,
            "evidence_chain_contract": evidence_contract is True,
            "evidence_files_contract": evidence_contract_real,
            "semantic_binding": semantic_binding,
        },
        "evidence": evidence_results,
        "safety": safety,
        "mapping": {
            "state": mapping_state,
            "repair_required": repair_required,
        },
        "verdict": (
            "RELEASE_GATE_SEMANTIC_BINDING_VERIFIED"
            if semantic_binding
            else
            "RELEASE_GATE_SEMANTIC_BINDING_FAILED"
        ),
    }

    # IMPORTANT:
    # This forensic itself is allowed to create ONLY its own report.
    # It never modifies producer/artifact/seal/DB.
    REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("=" * 80)
    print("FINAL DETERMINISTIC VERDICT")
    print("=" * 80)

    print(
        "RELEASE GATE SEMANTIC BINDING :",
        (
            "VERIFIED"
            if semantic_binding
            else "FAILED"
        ),
    )

    print("Repair required :", repair_required)
    print("REPORT          :", REPORT)


if __name__ == "__main__":
    main()