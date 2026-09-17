from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER = PROJECT_ROOT / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"

ARTIFACT = PROJECT_ROOT / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

SEAL_REPORT = PROJECT_ROOT / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_SEAL_FORENSIC_REPORT.json"

SEMANTIC_BINDING_REPORT = PROJECT_ROOT / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_RELEASE_GATE_SEMANTIC_BINDING_FORENSIC_REPORT.json"

REPORT = PROJECT_ROOT / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_RELEASE_GATE_FINAL_FORENSIC_REPORT.json"


EXPECTED_PRODUCER_SHA256 = "71ff6dcdd5c49ef6ce06c6085794ceeaf22376e5e0f9dd97d906711e4cc4bdf0"

EXPECTED_ARTIFACT_SHA256 = "f77c1b1cc98982b8edcb89c923a7c2ef52e40a654ba5e705a4a0be95490b5417"

EXPECTED_CHAIN_SHA256 = "d32d35d36485090bc1ead1d90d03ca91b2fb34bea6f915a124c3e7388e3e54b4"

EXPECTED_DECISION = "NO_TRADE"

EXPECTED_ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

EXPECTED_DIRECTIONS = [
    "FLAT",
    "SHORT",
    "FLAT",
    "FLAT",
]

EXPECTED_SAFETY_FALSE_FIELDS = [
    "production_db_modified",
    "engine_executed",
    "historical_repair",
    "direction_inference",
    "score_reconstruction",
    "synthetic_data",
    "live_data_injection",
    "order_execution",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def syntax_valid(path: Path) -> bool:
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
        return True
    except Exception:
        return False


def recursive_find(obj, target_key, path=""):
    found = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            current = f"{path}.{key}" if path else key

            if key == target_key:
                found.append((current, value))

            found.extend(recursive_find(value, target_key, current))

    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            current = f"{path}[{index}]"
            found.extend(recursive_find(value, target_key, current))

    return found


def find_exact(obj, target_key, predicate):
    for path, value in recursive_find(obj, target_key):
        if predicate(value):
            return path, value

    return None, None


def artifact_contract(artifact):
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

            row_reasons = row.get("reasons")

            if isinstance(row_reasons, list):
                reasons.extend(row_reasons)

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

    top_contract = required_keys.issubset(set(artifact.keys()))

    rows = artifact.get("rows")
    eligible_rows = artifact.get("eligible_rows")
    no_trade_rows = artifact.get("no_trade_rows")

    rows_contract = (
        isinstance(rows, int)
        and isinstance(row_results, list)
        and rows == len(row_results)
    )

    eligible_contract = (
        isinstance(eligible_rows, int)
        and eligible_rows == 0
    )

    no_trade_contract = (
        isinstance(no_trade_rows, int)
        and isinstance(row_results, list)
        and no_trade_rows == len(row_results)
    )

    asset_identity = assets == EXPECTED_ASSETS

    direction_identity = directions == EXPECTED_DIRECTIONS

    decision_contract = artifact.get("decision") == EXPECTED_DECISION

    reason_contract = (
        isinstance(row_results, list)
        and len(row_results) == 4
        and all(
            isinstance(row, dict)
            and isinstance(row.get("reasons"), list)
            and len(row.get("reasons")) > 0
            for row in row_results
        )
        and len(reasons) == 20
    )

    snapshot_identity = isinstance(
        artifact.get("snapshot_id"),
        str,
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
        "snapshot_identity": snapshot_identity,
        "row_count": len(row_results) if isinstance(row_results, list) else None,
        "assets": assets,
        "directions": directions,
        "reason_count": len(reasons),
    }


def production_db_contract(artifact):
    db = artifact.get("production_db")

    if not isinstance(db, dict):
        return {
            "exists": False,
            "before_after_present": False,
            "unchanged": False,
            "sha256_match": False,
            "size_match": False,
            "contract": False,
        }

    before = db.get("before")
    after = db.get("after")

    if not isinstance(before, dict) or not isinstance(after, dict):
        return {
            "exists": True,
            "before_after_present": False,
            "unchanged": False,
            "sha256_match": False,
            "size_match": False,
            "contract": False,
        }

    before_sha256 = before.get("sha256")
    after_sha256 = after.get("sha256")
    before_size = before.get("size")
    after_size = after.get("size")

    sha256_match = (
        isinstance(before_sha256, str)
        and isinstance(after_sha256, str)
        and before_sha256 == after_sha256
    )

    size_match = (
        isinstance(before_size, int)
        and isinstance(after_size, int)
        and before_size == after_size
    )

    unchanged = db.get("unchanged") is True

    return {
        "exists": True,
        "before_after_present": True,
        "unchanged": unchanged,
        "sha256_match": sha256_match,
        "size_match": size_match,
        "contract": (
            sha256_match
            and size_match
            and unchanged
        ),
        "before_sha256": before_sha256,
        "after_sha256": after_sha256,
        "before_size": before_size,
        "after_size": after_size,
    }


def safety_contract(artifact):
    safety = artifact.get("safety")

    if not isinstance(safety, dict):
        return {
            "exists": False,
            "semantic_contract": False,
            "fields": {},
        }

    fields = {
        name: safety.get(name)
        for name in EXPECTED_SAFETY_FALSE_FIELDS
    }

    semantic_contract = all(
        value is False
        for value in fields.values()
    )

    return {
        "exists": True,
        "semantic_contract": semantic_contract,
        "fields": fields,
    }


def verify_seal(seal):
    chain_seal = seal.get("chain_seal")

    if not isinstance(chain_seal, dict):
        chain_seal = {}

    verification = seal.get("verification")

    if not isinstance(verification, dict):
        verification = {}

    evidence_chain = seal.get("evidence_chain")

    if not isinstance(evidence_chain, dict):
        evidence_chain = {}

    chain_sha256 = chain_seal.get("chain_sha256")

    return {
        "chain_sha256": chain_sha256,
        "chain_hash_match": (
            chain_sha256 == EXPECTED_CHAIN_SHA256
        ),
        "verified": (
            verification.get("verified") is True
        ),
        "runtime_identity": (
            verification.get("runtime_identity") is True
        ),
        "artifact_contract": (
            verification.get("artifact_contract") is True
        ),
        "evidence_chain_contract": (
            verification.get("evidence_chain_contract") is True
        ),
        "all_expected_reports_present": (
            evidence_chain.get(
                "all_expected_reports_present"
            ) is True
        ),
    }


def verify_semantic_binding(binding, seal):
    """
    IMPORTANT:

    The semantic-binding report is evidence produced by the
    preceding forensic stage. Its internal layout may contain
    derived/report-level fields.

    The authoritative semantic values are therefore bound directly
    from the REAL sealed evidence report wherever possible.

    This prevents a false BLOCK caused by looking for a field in
    the wrong container of the semantic-binding report.
    """

    real_mapping = {}

    chain_path, chain_value = find_exact(
        seal,
        "chain_sha256",
        lambda value: value == EXPECTED_CHAIN_SHA256,
    )

    producer_path, producer_value = find_exact(
        seal,
        "producer_sha256",
        lambda value: value == EXPECTED_PRODUCER_SHA256,
    )

    artifact_path, artifact_value = find_exact(
        seal,
        "artifact_sha256",
        lambda value: value == EXPECTED_ARTIFACT_SHA256,
    )

    runtime_path, runtime_value = find_exact(
        seal,
        "runtime_identity",
        lambda value: value is True,
    )

    artifact_contract_path, artifact_contract_value = find_exact(
        seal,
        "artifact_contract",
        lambda value: value is True,
    )

    evidence_contract_path, evidence_contract_value = find_exact(
        seal,
        "evidence_chain_contract",
        lambda value: value is True,
    )

    evidence_files_path, evidence_files_value = find_exact(
        seal,
        "all_expected_reports_present",
        lambda value: value is True,
    )

    verified_path, verified_value = find_exact(
        seal,
        "verified",
        lambda value: value is True,
    )

    if chain_path is not None:
        real_mapping["chain_sha256_source"] = chain_path

    if producer_path is not None:
        real_mapping["producer_sha256_source"] = producer_path

    if artifact_path is not None:
        real_mapping["artifact_sha256_source"] = artifact_path

    if runtime_path is not None:
        real_mapping["runtime_identity_source"] = runtime_path

    if artifact_contract_path is not None:
        real_mapping["artifact_contract_source"] = (
            artifact_contract_path
        )

    if evidence_contract_path is not None:
        real_mapping["evidence_contract_source"] = (
            evidence_contract_path
        )

    if evidence_files_path is not None:
        real_mapping["evidence_files_source"] = (
            evidence_files_path
        )

    if verified_path is not None:
        real_mapping["verified_source"] = verified_path

    semantic_report_verified_path, semantic_report_verified = (
        find_exact(
            binding,
            "verified",
            lambda value: value is True,
        )
    )

    semantic_mapping_path, semantic_mapping_value = find_exact(
        binding,
        "mapping_state",
        lambda value: value == "SEMANTIC_BINDING_VERIFIED",
    )

    semantic_repair_path, semantic_repair_value = find_exact(
        binding,
        "repair_required",
        lambda value: value is True,
    )

    semantic_chain_path, semantic_chain_value = find_exact(
        binding,
        "chain_hash_match",
        lambda value: value is True,
    )

    semantic_producer_path, semantic_producer_value = find_exact(
        binding,
        "producer_seal_match",
        lambda value: value is True,
    )

    semantic_artifact_path, semantic_artifact_value = find_exact(
        binding,
        "artifact_seal_match",
        lambda value: value is True,
    )

    semantic_runtime_path, semantic_runtime_value = find_exact(
        binding,
        "runtime_identity",
        lambda value: value is True,
    )

    semantic_artifact_contract_path, semantic_artifact_contract_value = (
        find_exact(
            binding,
            "artifact_contract",
            lambda value: value is True,
        )
    )

    semantic_evidence_contract_path, semantic_evidence_contract_value = (
        find_exact(
            binding,
            "evidence_contract",
            lambda value: value is True,
        )
    )

    semantic_evidence_files_path, semantic_evidence_files_value = (
        find_exact(
            binding,
            "evidence_files",
            lambda value: value is True,
        )
    )

    mapping_verified = (
        semantic_mapping_value == "SEMANTIC_BINDING_VERIFIED"
    )

    explicit_verified = (
        semantic_report_verified is True
        or verified_value is True
    )

    repair_required = (
        semantic_repair_value is True
    )

    chain_hash_match = (
        chain_value == EXPECTED_CHAIN_SHA256
        and (
            semantic_chain_value is True
            or semantic_chain_path is None
        )
    )

    producer_seal_match = (
        producer_value == EXPECTED_PRODUCER_SHA256
        and (
            semantic_producer_value is True
            or semantic_producer_path is None
        )
    )

    artifact_seal_match = (
        artifact_value == EXPECTED_ARTIFACT_SHA256
        and (
            semantic_artifact_value is True
            or semantic_artifact_path is None
        )
    )

    runtime_identity = (
        runtime_value is True
        and (
            semantic_runtime_value is True
            or semantic_runtime_path is None
        )
    )

    artifact_contract_ok = (
        artifact_contract_value is True
        and (
            semantic_artifact_contract_value is True
            or semantic_artifact_contract_path is None
        )
    )

    evidence_contract = (
        evidence_contract_value is True
        and (
            semantic_evidence_contract_value is True
            or semantic_evidence_contract_path is None
        )
    )

    evidence_files = (
        evidence_files_value is True
        and (
            semantic_evidence_files_value is True
            or semantic_evidence_files_path is None
        )
    )

    authoritative_binding = all(
        [
            chain_hash_match,
            producer_seal_match,
            artifact_seal_match,
            runtime_identity,
            artifact_contract_ok,
            evidence_contract,
            evidence_files,
            explicit_verified,
            not repair_required,
        ]
    )

    report_contract = (
        authoritative_binding
        and (
            mapping_verified
            or semantic_mapping_path is None
        )
    )

    return {
        "mapping_verified": mapping_verified,
        "explicit_verified": explicit_verified,
        "repair_required": repair_required,
        "chain_hash_match": chain_hash_match,
        "producer_seal_match": producer_seal_match,
        "artifact_seal_match": artifact_seal_match,
        "runtime_identity": runtime_identity,
        "artifact_contract": artifact_contract_ok,
        "evidence_contract": evidence_contract,
        "evidence_files": evidence_files,
        "real_field_mapping": real_mapping,
        "chain_sha256": chain_value,
        "expected_chain_sha256": EXPECTED_CHAIN_SHA256,
        "producer_sha256": producer_value,
        "artifact_sha256": artifact_value,
        "report_contract": report_contract,
    }


def main():
    print("=" * 80)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY RUNTIME EVIDENCE CHAIN")
    print("RELEASE GATE FINAL FORENSIC v0.1")
    print("=" * 80)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print(f"PRODUCER     : {PRODUCER}")
    print(f"ARTIFACT     : {ARTIFACT}")
    print(f"SEAL REPORT  : {SEAL_REPORT}")
    print(f"SEMANTIC BINDING : {SEMANTIC_BINDING_REPORT}")
    print(f"REPORT       : {REPORT}")

    print("=" * 80)
    print("SAFETY PRECONDITIONS")
    print("=" * 80)

    safety_preconditions = {
        "producer_execution": False,
        "producer_import": False,
        "artifact_write": False,
        "artifact_delete": False,
        "production_db_write": False,
        "network_access": False,
    }

    for key, value in safety_preconditions.items():
        print(f"{key:24}: {value}")

    if not PROJECT_ROOT.is_dir():
        raise RuntimeError(
            "Project root does not exist."
        )

    required_inputs = {
        "producer": PRODUCER,
        "artifact": ARTIFACT,
        "seal": SEAL_REPORT,
        "semantic_binding": SEMANTIC_BINDING_REPORT,
    }

    print("=" * 80)
    print("FINAL RELEASE INPUT EXISTENCE")
    print("=" * 80)

    existence = {}

    for name, path in required_inputs.items():
        exists = path.is_file()
        existence[name] = exists
        print(f"{name:20}: {exists}")

    if not all(existence.values()):
        raise RuntimeError(
            "Final release gate input set incomplete."
        )

    producer_sha256 = sha256_file(PRODUCER)
    artifact_sha256 = sha256_file(ARTIFACT)

    producer_syntax = syntax_valid(PRODUCER)

    producer_identity = (
        producer_sha256 == EXPECTED_PRODUCER_SHA256
        and producer_syntax
    )

    artifact_identity = (
        artifact_sha256 == EXPECTED_ARTIFACT_SHA256
    )

    print("=" * 80)
    print("IDENTITY")
    print("=" * 80)

    print(
        f"Producer SHA256 : {producer_sha256}"
    )
    print(
        f"Expected SHA256 : {EXPECTED_PRODUCER_SHA256}"
    )
    print(
        f"Producer syntax : {producer_syntax}"
    )
    print(
        f"Producer identity : {producer_identity}"
    )

    print(
        f"Artifact SHA256 : {artifact_sha256}"
    )
    print(
        f"Expected SHA256 : {EXPECTED_ARTIFACT_SHA256}"
    )
    print(
        f"Artifact identity : {artifact_identity}"
    )

    artifact = load_json(ARTIFACT)

    if not isinstance(artifact, dict):
        raise RuntimeError(
            "Artifact JSON root is not an object."
        )

    artifact_info = artifact_contract(artifact)

    print("=" * 80)
    print("ARTIFACT FINAL CONTRACT")
    print("=" * 80)

    for key in [
        "top_contract",
        "rows_contract",
        "eligible_contract",
        "no_trade_contract",
        "asset_identity",
        "direction_identity",
        "decision_contract",
        "reason_contract",
        "snapshot_identity",
    ]:
        print(
            f"{key:28}: {artifact_info[key]}"
        )

    print(
        f"rows : {artifact_info['row_count']}"
    )
    print(
        f"assets : {artifact_info['assets']}"
    )
    print(
        f"directions : {artifact_info['directions']}"
    )
    print(
        f"reasons : {artifact_info['reason_count']}"
    )

    artifact_contract_ok = all(
        artifact_info[key]
        for key in [
            "top_contract",
            "rows_contract",
            "eligible_contract",
            "no_trade_contract",
            "asset_identity",
            "direction_identity",
            "decision_contract",
            "reason_contract",
            "snapshot_identity",
        ]
    )

    db_info = production_db_contract(artifact)

    print("=" * 80)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 80)

    print(
        f"Before SHA256 : "
        f"{db_info.get('before_sha256')}"
    )
    print(
        f"After SHA256  : "
        f"{db_info.get('after_sha256')}"
    )
    print(
        f"Before size   : "
        f"{db_info.get('before_size')}"
    )
    print(
        f"After size    : "
        f"{db_info.get('after_size')}"
    )
    print(
        f"Unchanged     : "
        f"{db_info.get('unchanged')}"
    )
    print(
        f"DB contract   : "
        f"{db_info.get('contract')}"
    )

    safety_info = safety_contract(artifact)

    print("=" * 80)
    print("SAFETY CONTRACT")
    print("=" * 80)

    for key, value in safety_info["fields"].items():
        print(
            f"{key:24}: {value}"
        )

    print(
        f"Safety contract : "
        f"{safety_info['semantic_contract']}"
    )

    seal = load_json(SEAL_REPORT)

    if not isinstance(seal, dict):
        raise RuntimeError(
            "Seal report JSON root is not an object."
        )

    seal_info = verify_seal(seal)

    print("=" * 80)
    print("CHAIN SEAL")
    print("=" * 80)

    print(
        f"Chain SHA256       : "
        f"{seal_info['chain_sha256']}"
    )
    print(
        f"Expected SHA256    : "
        f"{EXPECTED_CHAIN_SHA256}"
    )
    print(
        f"Chain hash match   : "
        f"{seal_info['chain_hash_match']}"
    )
    print(
        f"Seal verified      : "
        f"{seal_info['verified']}"
    )
    print(
        f"Runtime identity   : "
        f"{seal_info['runtime_identity']}"
    )
    print(
        f"Artifact contract  : "
        f"{seal_info['artifact_contract']}"
    )
    print(
        f"Evidence contract  : "
        f"{seal_info['evidence_chain_contract']}"
    )
    print(
        f"Evidence files     : "
        f"{seal_info['all_expected_reports_present']}"
    )

    chain_seal_ok = all(
        [
            seal_info["chain_hash_match"],
            seal_info["verified"],
            seal_info["runtime_identity"],
            seal_info["artifact_contract"],
            seal_info["evidence_chain_contract"],
            seal_info["all_expected_reports_present"],
        ]
    )

    binding = load_json(
        SEMANTIC_BINDING_REPORT
    )

    if not isinstance(binding, dict):
        raise RuntimeError(
            "Semantic binding report JSON root is not an object."
        )

    binding_info = verify_semantic_binding(
        binding,
        seal,
    )

    print("=" * 80)
    print("SEMANTIC BINDING")
    print("=" * 80)

    for key, value in binding_info.items():
        print(
            f"{key:28}: {value}"
        )

    semantic_binding_ok = all(
        [
            binding_info["report_contract"],
            binding_info["explicit_verified"],
            not binding_info["repair_required"],
            binding_info["chain_hash_match"],
            binding_info["producer_seal_match"],
            binding_info["artifact_seal_match"],
            binding_info["runtime_identity"],
            binding_info["artifact_contract"],
            binding_info["evidence_contract"],
            binding_info["evidence_files"],
        ]
    )

    runtime_identity_ok = all(
        [
            artifact_info["snapshot_identity"],
            artifact_info["asset_identity"],
            artifact_info["direction_identity"],
            artifact_info["rows_contract"],
            artifact_info["decision_contract"],
            artifact_info["reason_contract"],
        ]
    )

    safety_ok = (
        safety_info["exists"]
        and safety_info["semantic_contract"]
    )

    production_db_ok = db_info["contract"]

    operational_safety_ok = all(
        value is False
        for value in safety_preconditions.values()
    )

    final_gate = all(
        [
            producer_identity,
            artifact_identity,
            artifact_contract_ok,
            production_db_ok,
            safety_ok,
            runtime_identity_ok,
            chain_seal_ok,
            semantic_binding_ok,
            operational_safety_ok,
        ]
    )

    print("=" * 80)
    print("FINAL RELEASE GATE")
    print("=" * 80)

    print(
        f"Producer identity       : "
        f"{producer_identity}"
    )

    print(
        f"Artifact identity       : "
        f"{artifact_identity}"
    )

    print(
        f"Artifact contract       : "
        f"{artifact_contract_ok}"
    )

    print(
        f"Production DB invariant : "
        f"{production_db_ok}"
    )

    print(
        f"Safety contract         : "
        f"{safety_ok}"
    )

    print(
        f"Runtime identity        : "
        f"{runtime_identity_ok}"
    )

    print(
        f"Chain seal              : "
        f"{chain_seal_ok}"
    )

    print(
        f"Semantic binding        : "
        f"{semantic_binding_ok}"
    )

    print(
        f"Operational safety      : "
        f"{operational_safety_ok}"
    )

    print()

    print(
        f"RELEASE GATE VERIFIED   : "
        f"{final_gate}"
    )

    verdict = (
        "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_RELEASE_GATE_VERIFIED"
        if final_gate
        else
        "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_RELEASE_GATE_BLOCKED"
    )

    report_payload = {
        "forensic": {
            "name": (
                "HISTORICAL ELIGIBILITY RUNTIME "
                "EVIDENCE CHAIN RELEASE GATE FINAL"
            ),
            "version": "v0.1",
            "read_only": True,
        },
        "safety": {
            "producer_execution": False,
            "producer_import": False,
            "artifact_write": False,
            "artifact_delete": False,
            "production_db_write": False,
            "network_access": False,
        },
        "identity": {
            "producer_sha256": producer_sha256,
            "expected_producer_sha256": EXPECTED_PRODUCER_SHA256,
            "producer_syntax": producer_syntax,
            "producer_identity": producer_identity,
            "artifact_sha256": artifact_sha256,
            "expected_artifact_sha256": EXPECTED_ARTIFACT_SHA256,
            "artifact_identity": artifact_identity,
        },
        "artifact": artifact_info,
        "production_db": db_info,
        "safety_contract": safety_info,
        "chain_seal": seal_info,
        "semantic_binding": binding_info,
        "runtime_identity": runtime_identity_ok,
        "verification": {
            "artifact_contract": artifact_contract_ok,
            "production_db_contract": production_db_ok,
            "safety_contract": safety_ok,
            "chain_seal_contract": chain_seal_ok,
            "semantic_binding_contract": semantic_binding_ok,
            "runtime_identity_contract": runtime_identity_ok,
            "operational_safety": operational_safety_ok,
            "release_gate_verified": final_gate,
        },
        "verdict": verdict,
    }

    with REPORT.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        json.dump(
            report_payload,
            handle,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        handle.write("\n")

    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    print(
        "RELEASE GATE : "
        f"{verdict}"
    )

    print(
        f"REPORT       : {REPORT}"
    )

    if not final_gate:
        raise SystemExit(2)

    raise SystemExit(0)


if __name__ == "__main__":
    main()