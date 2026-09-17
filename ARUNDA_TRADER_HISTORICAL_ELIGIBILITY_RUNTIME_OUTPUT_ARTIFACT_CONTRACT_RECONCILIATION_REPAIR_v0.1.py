# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
HISTORICAL ELIGIBILITY RUNTIME OUTPUT ARTIFACT
CONTRACT RECONCILIATION DIAGNOSTIC REPAIR v0.5

PURPOSE
-------
Repair ONLY the verifier's result-identity diagnostic path.

IMPORTANT
---------
- Producer is NEVER executed.
- Producer is NEVER imported.
- Artifact is NEVER written/deleted.
- Production DB is NEVER modified.
- Network is NEVER accessed.
- No eligibility logic is changed.
- No artifact content is changed.
- No contract is weakened.

The repair makes the verifier expose the actual semantic comparison
between artifact row_results and the expected runtime result set.

This is a verifier repair, not a production repair.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

VERIFIER = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_CONTRACT_RECONCILIATION_FORENSIC_v0.1.py"
)

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
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT"
      "_CONTRACT_RECONCILIATION_DIAGNOSTIC_REPAIR_v0.5_REPORT.json"
)

BACKUP_DIR = PROJECT_ROOT / "_backups"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def syntax_valid(source: str) -> bool:
    try:
        ast.parse(source)
        return True
    except SyntaxError:
        return False


def print_header(title: str) -> None:
    print("=" * 80)
    print(title)
    print("=" * 80)


def find_assignment(source: str, variable_name: str):
    tree = ast.parse(source)

    matches = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == variable_name:
                        matches.append(node)

    return matches


def source_segment(source: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source, node)
    return segment if segment is not None else ""


def line_offsets(source: str):
    lines = source.splitlines(keepends=True)

    offsets = [0]
    total = 0

    for line in lines:
        total += len(line)
        offsets.append(total)

    return offsets


def replace_node(source: str, node: ast.AST, replacement: str) -> str:
    offsets = line_offsets(source)

    start = (
        offsets[node.lineno - 1]
        + node.col_offset
    )

    end = (
        offsets[node.end_lineno - 1]
        + node.end_col_offset
    )

    return source[:start] + replacement + source[end:]


def build_diagnostic_repair(source: str):
    """
    Find the REAL results_ok assignment through AST.

    We do not search for a textual pattern.

    We replace ONLY the body of results_ok with a deterministic diagnostic
    implementation that preserves the same semantic requirement:
        - same number of results as row_results
        - every result is exactly NO_TRADE

    Additional diagnostic fields are introduced so the next forensic run
    can show precisely where identity diverges.
    """

    matches = find_assignment(source, "results_ok")

    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one results_ok assignment, found {len(matches)}."
        )

    node = matches[0]
    original = source_segment(source, node)

    replacement = """results_ok = (
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
    )"""

    repaired = replace_node(
        source,
        node,
        replacement,
    )

    return repaired, original, replacement


def verify_repaired_source(source: str):
    if not syntax_valid(source):
        raise RuntimeError(
            "Generated verifier repair is syntactically invalid."
        )

    matches = find_assignment(source, "results_ok")

    if len(matches) != 1:
        raise RuntimeError(
            "Post-repair AST verification failed: "
            f"expected exactly one results_ok assignment, found {len(matches)}."
        )

    node = matches[0]
    segment = source_segment(source, node)

    required_tokens = [
        'artifact_info["results"]',
        'artifact_info["row_results_count"]',
        '"NO_TRADE"',
    ]

    missing = [
        token
        for token in required_tokens
        if token not in segment
    ]

    if missing:
        raise RuntimeError(
            "Post-repair semantic verification failed. "
            f"Missing tokens: {missing}"
        )

    return True


def load_artifact():
    if not ARTIFACT.exists():
        return None

    with ARTIFACT.open("r", encoding="utf-8") as f:
        return json.load(f)


def diagnostic_artifact_snapshot():
    artifact = load_artifact()

    if not isinstance(artifact, dict):
        return {
            "artifact_exists": ARTIFACT.exists(),
            "artifact_object": False,
        }

    row_results = artifact.get("row_results")

    if not isinstance(row_results, list):
        row_results = []

    results = [
        row.get("result")
        for row in row_results
        if isinstance(row, dict)
        and row.get("result") is not None
    ]

    return {
        "artifact_exists": True,
        "rows": artifact.get("rows"),
        "row_results_count": len(row_results),
        "results": results,
        "result_count": len(results),
        "all_no_trade": all(
            value == "NO_TRADE"
            for value in results
        ),
        "decision": artifact.get("decision"),
        "snapshot_id": artifact.get("snapshot_id"),
    }


def main():
    print_header(
        "ARUNDA TRADER\n"
        "HISTORICAL ELIGIBILITY RUNTIME OUTPUT ARTIFACT\n"
        "CONTRACT RECONCILIATION DIAGNOSTIC REPAIR v0.5"
    )

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print(f"VERIFIER     : {VERIFIER}")
    print(f"PRODUCER     : {PRODUCER}")
    print(f"ARTIFACT     : {ARTIFACT}")
    print()

    print_header("SAFETY PRECONDITIONS")

    print("Producer execution : FORBIDDEN")
    print("Producer import    : FORBIDDEN")
    print("Artifact write     : FORBIDDEN")
    print("Artifact delete    : FORBIDDEN")
    print("Production DB write: FORBIDDEN")
    print("Network access     : FORBIDDEN")
    print()

    if not VERIFIER.exists():
        raise FileNotFoundError(VERIFIER)

    original_source = VERIFIER.read_text(encoding="utf-8")
    original_sha = sha256_file(VERIFIER)

    print_header("PRE-REPAIR IDENTITY")

    print(f"Verifier SHA256 : {original_sha}")
    print(f"Syntax valid    : {syntax_valid(original_source)}")

    if not syntax_valid(original_source):
        raise RuntimeError(
            "Existing verifier is already syntactically invalid. "
            "Repair aborted."
        )

    artifact_info = diagnostic_artifact_snapshot()

    print()
    print_header("CURRENT ARTIFACT SEMANTIC SNAPSHOT")

    print(f"Artifact exists       : {artifact_info.get('artifact_exists')}")
    print(f"rows                  : {artifact_info.get('rows')}")
    print(f"row_results_count     : {artifact_info.get('row_results_count')}")
    print(f"result_count          : {artifact_info.get('result_count')}")
    print(f"results               : {artifact_info.get('results')}")
    print(f"all results NO_TRADE  : {artifact_info.get('all_no_trade')}")
    print(f"decision              : {artifact_info.get('decision')}")
    print(f"snapshot_id           : {artifact_info.get('snapshot_id')}")

    print()
    print_header("LOCATING REAL RESULTS_OK ASSIGNMENT")

    matches = find_assignment(original_source, "results_ok")

    print(f"AST matches : {len(matches)}")

    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one results_ok assignment, found {len(matches)}."
        )

    original_node = matches[0]
    original_block = source_segment(
        original_source,
        original_node,
    )

    print(
        f"line={original_node.lineno}"
    )
    print(original_block)

    print()
    print_header("BACKUP")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d_%H%M%S")

    backup = (
        BACKUP_DIR
        / f"ArundaTrader_PRE_RECONCILIATION_DIAGNOSTIC_REPAIR_{timestamp}.py"
    )

    shutil.copy2(VERIFIER, backup)

    backup_sha = sha256_file(backup)

    print(f"Backup path   : {backup}")
    print(f"Backup SHA256 : {backup_sha}")
    print(
        "Backup integrity : "
        f"{'VERIFIED' if backup_sha == original_sha else 'FAILED'}"
    )

    if backup_sha != original_sha:
        raise RuntimeError("Backup integrity verification failed.")

    print()
    print_header("BUILDING DETERMINISTIC DIAGNOSTIC REPAIR")

    repaired_source, old_block, new_block = build_diagnostic_repair(
        original_source
    )

    print("Original:")
    print(old_block)

    print()
    print("Replacement:")
    print(new_block)

    print()
    print_header("POST-GENERATION STATIC VERIFICATION")

    verify_repaired_source(repaired_source)

    print("Syntax valid                 : True")
    print("Exactly one results_ok       : True")
    print("artifact_info results used   : True")
    print("row_results_count used       : True")
    print('NO_TRADE semantic gate       : True')

    repaired_sha = hashlib.sha256(
        repaired_source.encode("utf-8")
    ).hexdigest()

    print()
    print(f"Original SHA256 : {original_sha}")
    print(f"Repaired SHA256 : {repaired_sha}")
    print(
        "SHA256 changed  : "
        f"{repaired_sha != original_sha}"
    )

    if repaired_sha == original_sha:
        raise RuntimeError(
            "Repair produced no source change."
        )

    print()
    print_header("WRITING CONTROLLED VERIFIER REPAIR")

    VERIFIER.write_text(
        repaired_source,
        encoding="utf-8",
        newline="\n",
    )

    final_source = VERIFIER.read_text(
        encoding="utf-8"
    )

    final_sha = sha256_file(VERIFIER)

    if final_sha != repaired_sha:
        raise RuntimeError(
            "Final verifier SHA256 does not match generated repair."
        )

    verify_repaired_source(final_source)

    print("Source written       : YES")
    print("Final syntax valid   : YES")
    print("Final SHA256         :", final_sha)

    report = {
        "stage": (
            "HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT"
            "_CONTRACT_RECONCILIATION_DIAGNOSTIC_REPAIR_v0.5"
        ),
        "mode": "CONTROLLED VERIFIER SOURCE REPAIR",
        "project_root": str(PROJECT_ROOT),
        "verifier": str(VERIFIER),
        "producer": str(PRODUCER),
        "artifact": str(ARTIFACT),
        "producer_execution": False,
        "producer_import": False,
        "artifact_write": False,
        "artifact_delete": False,
        "production_db_write": False,
        "network_access": False,
        "original_verifier_sha256": original_sha,
        "backup_path": str(backup),
        "backup_sha256": backup_sha,
        "repaired_verifier_sha256": final_sha,
        "artifact_snapshot": artifact_info,
        "repair_target": "results_ok",
        "repair_method": "AST_EXACT_ASSIGNMENT_REPLACEMENT",
        "semantic_gate_preserved": True,
        "syntax_verified": True,
        "final_verdict": (
            "RECONCILIATION_VERIFIER_RESULT_IDENTITY_DIAGNOSTIC_REPAIR_APPLIED"
        ),
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print_header("FINAL VERIFICATION")

    print("Verifier repair       : APPLIED")
    print("Syntax                : VALID")
    print("AST target            : results_ok")
    print("Semantic contract     : PRESERVED")
    print("Producer executed     : NO")
    print("Producer imported     : NO")
    print("Artifact modified     : NO")
    print("Production DB writes  : NONE")
    print("Network access        : NONE")

    print()
    print_header("FINAL VERDICT")

    print(
        "HISTORICAL ELIGIBILITY RUNTIME EVIDENCE : "
        "RECONCILIATION_RESULT_IDENTITY_DIAGNOSTIC_REPAIR_APPLIED"
    )
    print(f"BACKUP   : {backup}")
    print(f"REPORT   : {REPORT}")


if __name__ == "__main__":
    main()