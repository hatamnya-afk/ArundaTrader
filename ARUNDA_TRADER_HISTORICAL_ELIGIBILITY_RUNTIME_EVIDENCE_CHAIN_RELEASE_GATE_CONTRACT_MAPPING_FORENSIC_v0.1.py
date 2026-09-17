from pathlib import Path
import ast
import hashlib
import json
import re
import sys
from datetime import datetime, timezone


# =============================================================================
# ARUNDA TRADER
# HISTORICAL ELIGIBILITY RUNTIME EVIDENCE CHAIN
# RELEASE GATE CONTRACT MAPPING FORENSIC v0.1
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

SEAL_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_SEAL_FORENSIC_REPORT.json"
)

RELEASE_GATE_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_RELEASE_GATE_CONTRACT_MAPPING_FORENSIC_REPORT.json"
)

RELEASE_GATE_VERIFIER = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_RELEASE_GATE_FORENSIC_v0.1.py"
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


# =============================================================================
# SAFETY
# =============================================================================

PRODUCER_EXECUTION = False
PRODUCER_IMPORT = False
ARTIFACT_WRITE = False
ARTIFACT_DELETE = False
PRODUCTION_DB_WRITE = False
NETWORK_ACCESS = False


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
        ast.parse(source)
        return True
    except Exception:
        return False


def is_sha256(value):
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None
    )


def flatten_json(obj, prefix=""):
    """
    Deterministic recursive discovery of scalar JSON values.
    """
    found = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)

            if isinstance(value, (dict, list)):
                found.extend(flatten_json(value, path))
            else:
                found.append(
                    {
                        "path": path,
                        "key": str(key),
                        "value": value,
                        "type": type(value).__name__,
                    }
                )

    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            path = f"{prefix}[{index}]"

            if isinstance(value, (dict, list)):
                found.extend(flatten_json(value, path))
            else:
                found.append(
                    {
                        "path": path,
                        "key": str(index),
                        "value": value,
                        "type": type(value).__name__,
                    }
                )

    return found


def find_semantic_candidates(obj):
    """
    Find likely chain-hash / verification fields without assuming
    the schema used by the release gate.
    """
    candidates = []

    for item in flatten_json(obj):
        key = item["key"].lower()
        value = item["value"]

        score = 0
        reasons = []

        if any(
            token in key
            for token in (
                "chain",
                "seal",
                "hash",
                "sha",
                "fingerprint",
            )
        ):
            score += 2
            reasons.append("hash/seal semantic")

        if any(
            token in key
            for token in (
                "verified",
                "valid",
                "match",
                "sealed",
                "contract",
            )
        ):
            score += 2
            reasons.append("verification semantic")

        if is_sha256(value):
            score += 4
            reasons.append("64-char SHA256")

        if isinstance(value, bool):
            score += 1
            reasons.append("boolean")

        if score > 0:
            candidates.append(
                {
                    "path": item["path"],
                    "key": item["key"],
                    "value": value,
                    "type": item["type"],
                    "score": score,
                    "reasons": reasons,
                }
            )

    candidates.sort(
        key=lambda x: (-x["score"], x["path"])
    )

    return candidates


def find_expected_hash_occurrences(source: str):
    """
    Locate how the release gate verifier refers to the expected chain hash.
    """
    lines = source.splitlines()

    matches = []

    for index, line in enumerate(lines, start=1):
        lowered = line.lower()

        if (
            "expected_chain" in lowered
            or "chain_sha" in lowered
            or "chain_hash" in lowered
            or "expected seal" in lowered
            or "sealed chain" in lowered
        ):
            start = max(1, index - 3)
            end = min(len(lines), index + 3)

            matches.append(
                {
                    "line": index,
                    "text": "\n".join(
                        lines[start - 1:end]
                    ),
                }
            )

    return matches


def discover_verifier_field_access(source: str):
    """
    AST-level discovery of expressions reading the seal report.
    """
    tree = ast.parse(source)

    results = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            try:
                text = ast.unparse(node)
            except Exception:
                text = "<unparse-failed>"

            lowered = text.lower()

            if any(
                token in lowered
                for token in (
                    "seal",
                    "chain",
                    "verified",
                    "sha256",
                    "hash",
                )
            ):
                results.append(
                    {
                        "line": getattr(node, "lineno", None),
                        "expression": text,
                    }
                )

        elif isinstance(node, ast.Attribute):
            try:
                text = ast.unparse(node)
            except Exception:
                text = "<unparse-failed>"

            lowered = text.lower()

            if any(
                token in lowered
                for token in (
                    "seal",
                    "chain",
                    "verified",
                    "sha256",
                    "hash",
                )
            ):
                results.append(
                    {
                        "line": getattr(node, "lineno", None),
                        "expression": text,
                    }
                )

    unique = []
    seen = set()

    for item in results:
        key = (
            item["line"],
            item["expression"],
        )

        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


# =============================================================================
# MAIN FORENSIC
# =============================================================================

def main():
    print("=" * 80)
    print(
        "ARUNDA TRADER"
    )
    print(
        "HISTORICAL ELIGIBILITY RUNTIME EVIDENCE CHAIN"
    )
    print(
        "RELEASE GATE CONTRACT MAPPING FORENSIC v0.1"
    )
    print("=" * 80)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print(f"PRODUCER     : {PRODUCER}")
    print(f"ARTIFACT     : {ARTIFACT}")
    print(f"SEAL REPORT  : {SEAL_REPORT}")
    print(f"RELEASE GATE : {RELEASE_GATE_VERIFIER}")

    print("=" * 80)
    print("SAFETY PRECONDITIONS")
    print("=" * 80)

    print(f"Producer execution : {PRODUCER_EXECUTION}")
    print(f"Producer import    : {PRODUCER_IMPORT}")
    print(f"Artifact write     : {ARTIFACT_WRITE}")
    print(f"Artifact delete    : {ARTIFACT_DELETE}")
    print(f"Production DB write: {PRODUCTION_DB_WRITE}")
    print(f"Network access     : {NETWORK_ACCESS}")

    if any(
        (
            PRODUCER_EXECUTION,
            PRODUCER_IMPORT,
            ARTIFACT_WRITE,
            ARTIFACT_DELETE,
            PRODUCTION_DB_WRITE,
            NETWORK_ACCESS,
        )
    ):
        raise RuntimeError(
            "Unsafe forensic configuration."
        )

    # -------------------------------------------------------------------------
    # IDENTITY
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("IDENTITY")
    print("=" * 80)

    producer_exists = PRODUCER.exists()
    artifact_exists = ARTIFACT.exists()
    seal_exists = SEAL_REPORT.exists()
    verifier_exists = RELEASE_GATE_VERIFIER.exists()

    if not producer_exists:
        raise FileNotFoundError(PRODUCER)

    if not artifact_exists:
        raise FileNotFoundError(ARTIFACT)

    if not seal_exists:
        raise FileNotFoundError(SEAL_REPORT)

    if not verifier_exists:
        raise FileNotFoundError(RELEASE_GATE_VERIFIER)

    producer_sha = sha256_file(PRODUCER)
    artifact_sha = sha256_file(ARTIFACT)
    seal_sha = sha256_file(SEAL_REPORT)
    verifier_sha = sha256_file(RELEASE_GATE_VERIFIER)

    print(f"Producer SHA256 : {producer_sha}")
    print(f"Expected SHA256 : {EXPECTED_PRODUCER_SHA256}")
    print(
        f"Producer identity : "
        f"{producer_sha == EXPECTED_PRODUCER_SHA256}"
    )

    print(f"Artifact SHA256 : {artifact_sha}")
    print(f"Expected SHA256 : {EXPECTED_ARTIFACT_SHA256}")
    print(
        f"Artifact identity : "
        f"{artifact_sha == EXPECTED_ARTIFACT_SHA256}"
    )

    print(f"Seal report SHA256 : {seal_sha}")
    print(f"Release verifier SHA256 : {verifier_sha}")

    # -------------------------------------------------------------------------
    # LOAD SEAL
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("REAL SEAL REPORT SCHEMA")
    print("=" * 80)

    seal = load_json(SEAL_REPORT)

    print(
        f"Seal top-level type : "
        f"{type(seal).__name__}"
    )

    if not isinstance(seal, dict):
        raise RuntimeError(
            "Seal report top-level object is not a dict."
        )

    print(
        f"Top-level keys : {list(seal.keys())}"
    )

    # -------------------------------------------------------------------------
    # SEMANTIC DISCOVERY
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("SEAL SEMANTIC FIELD DISCOVERY")
    print("=" * 80)

    candidates = find_semantic_candidates(seal)

    print(
        f"Semantic candidates : {len(candidates)}"
    )

    for candidate in candidates:
        print(
            f"score={candidate['score']} "
            f"path={candidate['path']} "
            f"type={candidate['type']} "
            f"value={candidate['value']!r}"
        )
        print(
            f"  reasons={candidate['reasons']}"
        )

    # -------------------------------------------------------------------------
    # EXPECTED CHAIN MATCH
    # -------------------------------------------------------------------------

    chain_hash_candidates = [
        c
        for c in candidates
        if c["value"] == EXPECTED_CHAIN_SHA256
    ]

    print("=" * 80)
    print("EXPECTED CHAIN SHA256 DISCOVERY")
    print("=" * 80)

    print(
        f"Expected chain SHA256 : "
        f"{EXPECTED_CHAIN_SHA256}"
    )

    print(
        f"Matching fields       : "
        f"{len(chain_hash_candidates)}"
    )

    for candidate in chain_hash_candidates:
        print(
            f"FOUND "
            f"path={candidate['path']} "
            f"key={candidate['key']} "
            f"value={candidate['value']}"
        )

    chain_hash_present = bool(
        chain_hash_candidates
    )

    # -------------------------------------------------------------------------
    # VERIFIED FLAG DISCOVERY
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("SEAL VERIFICATION FLAG DISCOVERY")
    print("=" * 80)

    boolean_candidates = [
        c
        for c in candidates
        if isinstance(c["value"], bool)
    ]

    for candidate in boolean_candidates:
        print(
            f"path={candidate['path']} "
            f"key={candidate['key']} "
            f"value={candidate['value']}"
        )

    verified_candidates = [
        c
        for c in boolean_candidates
        if (
            "verified" in c["key"].lower()
            or "valid" in c["key"].lower()
            or "sealed" in c["key"].lower()
        )
    ]

    true_verified_candidates = [
        c
        for c in verified_candidates
        if c["value"] is True
    ]

    print(
        f"Verification candidates : "
        f"{len(verified_candidates)}"
    )

    print(
        f"True verification candidates : "
        f"{len(true_verified_candidates)}"
    )

    # -------------------------------------------------------------------------
    # RELEASE GATE EXPECTATIONS
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("RELEASE GATE VERIFIER FIELD ACCESS")
    print("=" * 80)

    verifier_source = (
        RELEASE_GATE_VERIFIER.read_text(
            encoding="utf-8"
        )
    )

    print(
        f"Verifier syntax : "
        f"{syntax_valid(RELEASE_GATE_VERIFIER)}"
    )

    field_access = discover_verifier_field_access(
        verifier_source
    )

    print(
        f"Relevant AST field accesses : "
        f"{len(field_access)}"
    )

    for item in field_access:
        print(
            f"line={item['line']} "
            f"{item['expression']}"
        )

    print("=" * 80)
    print("CHAIN MAPPING DIAGNOSTIC")
    print("=" * 80)

    print(
        f"Expected chain hash : "
        f"{EXPECTED_CHAIN_SHA256}"
    )

    print(
        f"Actual matching field count : "
        f"{len(chain_hash_candidates)}"
    )

    print(
        f"Verified flag candidates : "
        f"{len(true_verified_candidates)}"
    )

    # -------------------------------------------------------------------------
    # DETERMINISTIC CLASSIFICATION
    # -------------------------------------------------------------------------

    if chain_hash_present and true_verified_candidates:
        mapping_state = (
            "SEAL_SCHEMA_MAPPING_PRESENT"
        )

    elif chain_hash_present and not true_verified_candidates:
        mapping_state = (
            "SEAL_VERIFICATION_FLAG_MAPPING_MISMATCH"
        )

    elif not chain_hash_present and true_verified_candidates:
        mapping_state = (
            "SEAL_CHAIN_HASH_MAPPING_MISMATCH"
        )

    else:
        mapping_state = (
            "SEAL_CHAIN_AND_VERIFICATION_MAPPING_MISMATCH"
        )

    print(
        f"Mapping state : {mapping_state}"
    )

    # -------------------------------------------------------------------------
    # IMPORTANT: DO NOT MODIFY ANY SOURCE
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("SOURCE MODIFICATION")
    print("=" * 80)

    print("Producer modified : NO")
    print("Artifact modified : NO")
    print("Seal report modified : NO")
    print("Release verifier modified : NO")
    print("Production DB modified : NO")

    # -------------------------------------------------------------------------
    # REPORT
    # -------------------------------------------------------------------------

    report = {
        "forensic_version": "v0.1",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "mode": "READ_ONLY_CONTRACT_MAPPING_FORENSIC",

        "safety": {
            "producer_execution": False,
            "producer_import": False,
            "artifact_write": False,
            "artifact_delete": False,
            "production_db_write": False,
            "network_access": False,
            "producer_modified": False,
            "artifact_modified": False,
            "seal_modified": False,
            "release_verifier_modified": False,
        },

        "identity": {
            "producer_sha256": producer_sha,
            "expected_producer_sha256":
                EXPECTED_PRODUCER_SHA256,
            "producer_identity":
                producer_sha == EXPECTED_PRODUCER_SHA256,

            "artifact_sha256": artifact_sha,
            "expected_artifact_sha256":
                EXPECTED_ARTIFACT_SHA256,
            "artifact_identity":
                artifact_sha == EXPECTED_ARTIFACT_SHA256,

            "seal_report_sha256": seal_sha,
            "release_verifier_sha256":
                verifier_sha,
        },

        "seal": {
            "expected_chain_sha256":
                EXPECTED_CHAIN_SHA256,

            "matching_chain_fields":
                chain_hash_candidates,

            "verification_candidates":
                verified_candidates,

            "true_verification_candidates":
                true_verified_candidates,

            "chain_hash_present":
                chain_hash_present,

            "verified_flag_present":
                bool(true_verified_candidates),
        },

        "release_gate": {
            "verifier_syntax_valid":
                syntax_valid(RELEASE_GATE_VERIFIER),

            "relevant_field_access":
                field_access,
        },

        "mapping_state": mapping_state,

        "repair_required": (
            mapping_state
            != "SEAL_SCHEMA_MAPPING_PRESENT"
        ),

        "final_verdict": (
            "SEAL_RELEASE_GATE_MAPPING_READY"
            if mapping_state
            == "SEAL_SCHEMA_MAPPING_PRESENT"
            else "SEAL_RELEASE_GATE_MAPPING_MISMATCH_CONFIRMED"
        ),
    }

    with RELEASE_GATE_REPORT.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    print("=" * 80)
    print("FINAL DETERMINISTIC VERDICT")
    print("=" * 80)

    print(
        f"Mapping state : {mapping_state}"
    )

    print(
        f"Repair required : "
        f"{report['repair_required']}"
    )

    print(
        f"REPORT : {RELEASE_GATE_REPORT}"
    )


if __name__ == "__main__":
    main()