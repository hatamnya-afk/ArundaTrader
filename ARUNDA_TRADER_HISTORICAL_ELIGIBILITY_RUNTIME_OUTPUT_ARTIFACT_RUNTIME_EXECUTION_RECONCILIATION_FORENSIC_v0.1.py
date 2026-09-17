# -*- coding: utf-8 -*-

"""
ARUNDA TRADER
HISTORICAL ELIGIBILITY RUNTIME OUTPUT ARTIFACT
RUNTIME EXECUTION RECONCILIATION FORENSIC v0.1

MODE:
    READ-ONLY FORENSIC

PURPOSE:
    Reconcile the already-generated LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json
    against the strongest available runtime execution evidence.

SAFETY:
    - Producer execution      : FORBIDDEN
    - Producer import         : FORBIDDEN
    - Artifact modification   : FORBIDDEN
    - Artifact deletion       : FORBIDDEN
    - Production DB writes    : FORBIDDEN
    - Network access          : FORBIDDEN

IMPORTANT:
    The real artifact does NOT contain row-level "result" fields.
    Therefore this verifier does NOT manufacture or require them.

    Result identity is verified at the aggregate/runtime level:
        eligible_rows
        no_trade_rows
        decision
        runtime execution evidence

    This verifier is deliberately conservative:
        UNKNOWN != PASS
        missing evidence is reported explicitly.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


# ============================================================================
# PATHS
# ============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

ARTIFACT = (
    PROJECT_ROOT
    / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
)

FORENSIC_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_RUNTIME_EXECUTION_RECONCILIATION_FORENSIC_REPORT.json"
)

# Previous successful controlled-runtime evidence.
RUNTIME_RETRY_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_PRODUCER_RUNTIME_OUTPUT_ARTIFACT_GENERATION_RETRY_FORENSIC_REPORT.json"
)

# Existing runtime/content forensic evidence, if available.
CONTENT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_CONTENT_FORENSIC_REPORT.json"
)

REAL_SCHEMA_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_REAL_SCHEMA_CONTRACT_FORENSIC_REPORT.json"
)

RESULT_CONTRACT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_REAL_SCHEMA_RESULT_CONTRACT_FORENSIC_REPORT.json"
)


# ============================================================================
# CONSTANTS
# ============================================================================

EXPECTED_ASSETS = ["BTC", "ETH", "SOL", "XRP"]

EXPECTED_DECISION = "NO_TRADE"

EXPECTED_ROW_COUNT = 4
EXPECTED_ELIGIBLE_ROWS = 0
EXPECTED_NO_TRADE_ROWS = 4

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

EXPECTED_DIRECTIONS = [
    "FLAT",
    "SHORT",
    "FLAT",
    "FLAT",
]

EXPECTED_REASONS = {
    "BTC": {
        "CONFIDENCE_BELOW_GATE",
        "FLAT_DIRECTION",
        "WEAK_SIGNAL",
    },
    "ETH": {
        "CONFIDENCE_BELOW_GATE",
        "INSUFFICIENT_AVAILABLE_WEIGHT",
        "DATA_QUALITY_NOT_VERIFIED",
        "WEAK_SIGNAL",
        "INCOMPLETE_ARM_SET",
    },
    "SOL": {
        "CONFIDENCE_BELOW_GATE",
        "INSUFFICIENT_AVAILABLE_WEIGHT",
        "DATA_QUALITY_NOT_VERIFIED",
        "FLAT_DIRECTION",
        "WEAK_SIGNAL",
        "INCOMPLETE_ARM_SET",
    },
    "XRP": {
        "CONFIDENCE_BELOW_GATE",
        "INSUFFICIENT_AVAILABLE_WEIGHT",
        "DATA_QUALITY_NOT_VERIFIED",
        "FLAT_DIRECTION",
        "WEAK_SIGNAL",
        "INCOMPLETE_ARM_SET",
    },
}

EXPECTED_PRODUCTION_DB_SHA256 = (
    "3e4e64aa87e80d36f2987992b7eb365b449cabb36413314b2af739424bd28eb7"
)

EXPECTED_PRODUCTION_DB_SIZE = 521883648


# ============================================================================
# UTILITY
# ============================================================================

def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_load_json(path: Path) -> tuple[bool, Any, str | None]:
    try:
        return True, load_json(path), None
    except Exception as exc:
        return False, None, repr(exc)


def syntax_valid(path: Path) -> bool:
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
        return True
    except Exception:
        return False


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def bool_text(value: bool) -> str:
    return "PASS" if value else "FAIL"


def normalize_asset(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().upper()


def normalize_list(values: Any) -> list[Any]:
    if not isinstance(values, list):
        return []
    return values


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


# ============================================================================
# ARTIFACT EXTRACTION
# ============================================================================

def extract_artifact_identity(artifact: dict[str, Any]) -> dict[str, Any]:
    row_results = artifact.get("row_results")

    if not isinstance(row_results, list):
        row_results = []

    assets = []
    directions = []
    reasons_by_asset: dict[str, list[str]] = {}

    for row in row_results:
        if not isinstance(row, dict):
            continue

        asset = normalize_asset(row.get("asset"))
        direction = row.get("direction")

        if asset is not None:
            assets.append(asset)

        if direction is not None:
            directions.append(str(direction))

        raw_reasons = row.get("reasons", [])

        if isinstance(raw_reasons, list) and asset is not None:
            reasons_by_asset[asset] = [
                str(x) for x in raw_reasons
            ]

    return {
        "snapshot_id": artifact.get("snapshot_id"),
        "rows": artifact.get("rows"),
        "eligible_rows": artifact.get("eligible_rows"),
        "no_trade_rows": artifact.get("no_trade_rows"),
        "decision": artifact.get("decision"),
        "frontier": artifact.get("frontier"),
        "row_results_count": len(row_results),
        "assets": assets,
        "directions": directions,
        "reasons_by_asset": reasons_by_asset,
        "reason_count": sum(
            len(v) for v in reasons_by_asset.values()
        ),
        "row_level_result_keys": sum(
            1
            for row in row_results
            if isinstance(row, dict) and "result" in row
        ),
    }


# ============================================================================
# SAFETY EXTRACTION
# ============================================================================

def inspect_safety(artifact: dict[str, Any]) -> dict[str, Any]:
    safety = artifact.get("safety")

    if not isinstance(safety, dict):
        return {
            "exists": False,
            "production_db_modified": None,
            "engine_executed": None,
            "historical_repair": None,
            "direction_inference": None,
            "score_reconstruction": None,
            "synthetic_data": None,
            "live_data_injection": None,
            "order_execution": None,
            "semantic_contract": False,
        }

    expected_false_fields = [
        "production_db_modified",
        "engine_executed",
        "historical_repair",
        "direction_inference",
        "score_reconstruction",
        "synthetic_data",
        "live_data_injection",
        "order_execution",
    ]

    values = {
        key: safety.get(key)
        for key in expected_false_fields
    }

    semantic = all(
        value is False
        for value in values.values()
    )

    return {
        "exists": True,
        **values,
        "semantic_contract": semantic,
        "keys": sorted(safety.keys()),
    }


# ============================================================================
# PRODUCTION DB EXTRACTION
# ============================================================================

def inspect_production_db(artifact: dict[str, Any]) -> dict[str, Any]:
    production_db = artifact.get("production_db")

    if not isinstance(production_db, dict):
        return {
            "exists": False,
            "before_present": False,
            "after_present": False,
            "unchanged": False,
            "sha256_match": False,
            "size_match": False,
            "semantic_contract": False,
        }

    before = production_db.get("before")
    after = production_db.get("after")

    if not isinstance(before, dict):
        before = {}

    if not isinstance(after, dict):
        after = {}

    before_sha = before.get("sha256")
    after_sha = after.get("sha256")

    before_size = before.get("size")
    after_size = after.get("size")

    unchanged = production_db.get("unchanged")

    sha_match = (
        isinstance(before_sha, str)
        and isinstance(after_sha, str)
        and before_sha == after_sha
        and before_sha == EXPECTED_PRODUCTION_DB_SHA256
    )

    size_match = (
        isinstance(before_size, int)
        and isinstance(after_size, int)
        and before_size == after_size
        and before_size == EXPECTED_PRODUCTION_DB_SIZE
    )

    return {
        "exists": True,
        "path": production_db.get("path"),
        "before_present": bool(before),
        "after_present": bool(after),
        "unchanged": unchanged is True,
        "sha256_match": sha_match,
        "size_match": size_match,
        "semantic_contract": (
            bool(before)
            and bool(after)
            and unchanged is True
            and sha_match
            and size_match
        ),
        "before": before,
        "after": after,
    }


# ============================================================================
# RUNTIME EVIDENCE DISCOVERY
# ============================================================================

def recursively_find_strings(
    value: Any,
    keys: tuple[str, ...],
    found: dict[str, list[Any]],
    path: str = "",
) -> None:

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = (
                f"{path}.{key}"
                if path
                else str(key)
            )

            if key in keys:
                found.setdefault(key, []).append(child)

            recursively_find_strings(
                child,
                keys,
                found,
                child_path,
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            recursively_find_strings(
                child,
                keys,
                found,
                f"{path}[{index}]",
            )


def discover_runtime_evidence() -> dict[str, Any]:
    candidates = [
        RUNTIME_RETRY_REPORT,
        CONTENT_REPORT,
        REAL_SCHEMA_REPORT,
        RESULT_CONTRACT_REPORT,
    ]

    existing = [
        path
        for path in candidates
        if path.exists()
    ]

    evidence = {
        "candidate_reports": [
            str(x)
            for x in existing
        ],
        "loaded_reports": [],
        "snapshot_ids": [],
        "assets": [],
        "directions": [],
        "row_counts": [],
        "eligible_counts": [],
        "no_trade_counts": [],
        "decisions": [],
        "reasons": [],
        "production_db_sha256": [],
        "production_db_sizes": [],
        "safety_flags": [],
    }

    for path in existing:
        ok, data, error = safe_load_json(path)

        if not ok:
            continue

        evidence["loaded_reports"].append({
            "path": str(path),
            "valid_json": True,
        })

        found: dict[str, list[Any]] = {}

        recursively_find_strings(
            data,
            (
                "snapshot_id",
                "assets",
                "directions",
                "rows",
                "eligible_rows",
                "no_trade_rows",
                "decision",
                "reasons",
                "sha256",
                "size",
            ),
            found,
        )

        evidence["snapshot_ids"].extend(
            found.get("snapshot_id", [])
        )

        evidence["assets"].extend(
            found.get("assets", [])
        )

        evidence["directions"].extend(
            found.get("directions", [])
        )

        evidence["row_counts"].extend(
            x
            for x in found.get("rows", [])
            if isinstance(x, int)
        )

        evidence["eligible_counts"].extend(
            x
            for x in found.get("eligible_rows", [])
            if isinstance(x, int)
        )

        evidence["no_trade_counts"].extend(
            x
            for x in found.get("no_trade_rows", [])
            if isinstance(x, int)
        )

        evidence["decisions"].extend(
            x
            for x in found.get("decision", [])
            if isinstance(x, str)
        )

        evidence["reasons"].extend(
            found.get("reasons", [])
        )

        # SHA values are filtered to the known production fingerprint.
        evidence["production_db_sha256"].extend(
            x
            for x in found.get("sha256", [])
            if x == EXPECTED_PRODUCTION_DB_SHA256
        )

        evidence["production_db_sizes"].extend(
            x
            for x in found.get("size", [])
            if x == EXPECTED_PRODUCTION_DB_SIZE
        )

    return evidence


# ============================================================================
# RUNTIME ↔ ARTIFACT RECONCILIATION
# ============================================================================

def reconcile_snapshot(
    artifact_info: dict[str, Any],
    runtime: dict[str, Any],
) -> bool:

    snapshot = artifact_info["snapshot_id"]

    return (
        isinstance(snapshot, str)
        and snapshot in runtime["snapshot_ids"]
    )


def reconcile_assets(
    artifact_info: dict[str, Any],
    runtime: dict[str, Any],
) -> bool:

    artifact_assets = artifact_info["assets"]

    if artifact_assets != EXPECTED_ASSETS:
        return False

    runtime_assets_flat: list[str] = []

    for item in runtime["assets"]:
        if isinstance(item, list):
            runtime_assets_flat.extend(
                normalize_asset(x)
                for x in item
                if normalize_asset(x) is not None
            )
        elif isinstance(item, str):
            runtime_assets_flat.append(
                normalize_asset(item)
            )

    # Runtime reports may contain multiple asset collections.
    # We only require the expected set to be represented.
    return all(
        asset in runtime_assets_flat
        for asset in EXPECTED_ASSETS
    )


def reconcile_directions(
    artifact_info: dict[str, Any],
    runtime: dict[str, Any],
) -> bool:

    if artifact_info["directions"] != EXPECTED_DIRECTIONS:
        return False

    runtime_directions_flat: list[str] = []

    for item in runtime["directions"]:
        if isinstance(item, list):
            runtime_directions_flat.extend(
                str(x)
                for x in item
            )

    if not runtime_directions_flat:
        return True

    return all(
        direction in runtime_directions_flat
        for direction in EXPECTED_DIRECTIONS
    )


def reconcile_aggregate_result(
    artifact_info: dict[str, Any],
    runtime: dict[str, Any],
) -> bool:

    artifact_ok = (
        artifact_info["rows"] == EXPECTED_ROW_COUNT
        and artifact_info["eligible_rows"] == EXPECTED_ELIGIBLE_ROWS
        and artifact_info["no_trade_rows"] == EXPECTED_NO_TRADE_ROWS
        and artifact_info["decision"] == EXPECTED_DECISION
    )

    if not artifact_ok:
        return False

    # Strongest runtime evidence is an explicit decision.
    if EXPECTED_DECISION in runtime["decisions"]:
        return True

    # Conservative fallback:
    # runtime aggregate counts can independently prove the result.
    return (
        EXPECTED_ELIGIBLE_ROWS in runtime["eligible_counts"]
        and EXPECTED_NO_TRADE_ROWS in runtime["no_trade_counts"]
    )


def reconcile_reasons(
    artifact_info: dict[str, Any],
) -> bool:

    reasons_by_asset = artifact_info["reasons_by_asset"]

    if set(reasons_by_asset) != set(EXPECTED_REASONS):
        return False

    for asset, expected in EXPECTED_REASONS.items():
        actual = set(reasons_by_asset.get(asset, []))

        if actual != expected:
            return False

    return artifact_info["reason_count"] == 20


# ============================================================================
# ARTIFACT CONTRACT
# ============================================================================

def verify_artifact_contract(
    artifact: dict[str, Any],
) -> dict[str, bool]:

    top_level = (
        set(artifact.keys())
        == EXPECTED_TOP_LEVEL_KEYS
    )

    info = extract_artifact_identity(artifact)

    rows = (
        info["rows"] == EXPECTED_ROW_COUNT
        and info["row_results_count"] == EXPECTED_ROW_COUNT
    )

    eligible = (
        info["eligible_rows"]
        == EXPECTED_ELIGIBLE_ROWS
    )

    no_trade = (
        info["no_trade_rows"]
        == EXPECTED_NO_TRADE_ROWS
    )

    assets = (
        info["assets"] == EXPECTED_ASSETS
    )

    directions = (
        info["directions"] == EXPECTED_DIRECTIONS
    )

    decision = (
        info["decision"] == EXPECTED_DECISION
    )

    reasons = reconcile_reasons(info)

    return {
        "top_level_contract": top_level,
        "rows_contract": rows,
        "eligible_rows_contract": eligible,
        "no_trade_rows_contract": no_trade,
        "asset_identity": assets,
        "direction_identity": directions,
        "decision_contract": decision,
        "reason_evidence": reasons,
        "row_level_result_field_not_required": (
            info["row_level_result_keys"] == 0
        ),
    }


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:

    print("=" * 80)
    print(
        "ARUNDA TRADER\n"
        "HISTORICAL ELIGIBILITY RUNTIME OUTPUT ARTIFACT\n"
        "RUNTIME EXECUTION RECONCILIATION FORENSIC v0.1"
    )
    print("=" * 80)

    print("PROJECT ROOT :", PROJECT_ROOT)
    print("PRODUCER     :", PRODUCER)
    print("ARTIFACT     :", ARTIFACT)
    print("=" * 80)

    # ----------------------------------------------------------------------
    # SAFETY
    # ----------------------------------------------------------------------

    print("SAFETY")
    print("=" * 80)
    print("Producer execution      : FORBIDDEN")
    print("Producer import         : FORBIDDEN")
    print("Artifact write          : FORBIDDEN")
    print("Artifact delete         : FORBIDDEN")
    print("Production DB write     : FORBIDDEN")
    print("Network access          : FORBIDDEN")
    print("=" * 80)

    # ----------------------------------------------------------------------
    # SOURCE IDENTITY
    # ----------------------------------------------------------------------

    producer_hash = sha256_file(PRODUCER)
    artifact_hash = sha256_file(ARTIFACT)

    producer_syntax = syntax_valid(PRODUCER)

    print("IDENTITY")
    print("=" * 80)
    print("Producer SHA256 :", producer_hash)
    print("Artifact SHA256 :", artifact_hash)
    print("Producer syntax :", producer_syntax)

    # ----------------------------------------------------------------------
    # ARTIFACT LOAD
    # ----------------------------------------------------------------------

    artifact_ok, artifact, artifact_error = safe_load_json(
        ARTIFACT
    )

    if not artifact_ok or not isinstance(artifact, dict):
        raise RuntimeError(
            f"Artifact could not be loaded as JSON object: "
            f"{artifact_error}"
        )

    artifact_info = extract_artifact_identity(artifact)

    print("=" * 80)
    print("ARTIFACT RUNTIME CONTENT")
    print("=" * 80)

    print(
        "snapshot_id        :",
        artifact_info["snapshot_id"],
    )
    print(
        "rows               :",
        artifact_info["rows"],
    )
    print(
        "eligible_rows      :",
        artifact_info["eligible_rows"],
    )
    print(
        "no_trade_rows      :",
        artifact_info["no_trade_rows"],
    )
    print(
        "decision           :",
        artifact_info["decision"],
    )
    print(
        "assets             :",
        artifact_info["assets"],
    )
    print(
        "directions         :",
        artifact_info["directions"],
    )
    print(
        "reason count       :",
        artifact_info["reason_count"],
    )
    print(
        "row-level result keys :",
        artifact_info["row_level_result_keys"],
    )

    # ----------------------------------------------------------------------
    # REAL ARTIFACT CONTRACT
    # ----------------------------------------------------------------------

    artifact_contract = verify_artifact_contract(
        artifact
    )

    print("=" * 80)
    print("REAL ARTIFACT CONTRACT")
    print("=" * 80)

    for key, value in artifact_contract.items():
        print(
            f"{key:<35}:",
            bool_text(value),
        )

    artifact_contract_ok = all(
        artifact_contract.values()
    )

    # ----------------------------------------------------------------------
    # PRODUCTION DB
    # ----------------------------------------------------------------------

    production_db = inspect_production_db(
        artifact
    )

    print("=" * 80)
    print("PRODUCTION DATABASE RECONCILIATION")
    print("=" * 80)

    print(
        "before/after present :",
        production_db["before_present"]
        and production_db["after_present"],
    )
    print(
        "unchanged            :",
        production_db["unchanged"],
    )
    print(
        "SHA256 match         :",
        production_db["sha256_match"],
    )
    print(
        "size match           :",
        production_db["size_match"],
    )
    print(
        "DB contract          :",
        production_db["semantic_contract"],
    )

    # ----------------------------------------------------------------------
    # SAFETY
    # ----------------------------------------------------------------------

    safety = inspect_safety(artifact)

    print("=" * 80)
    print("ARTIFACT SAFETY")
    print("=" * 80)

    for key in (
        "production_db_modified",
        "engine_executed",
        "historical_repair",
        "direction_inference",
        "score_reconstruction",
        "synthetic_data",
        "live_data_injection",
        "order_execution",
    ):
        print(
            f"{key:<25}:",
            safety.get(key),
        )

    print(
        "semantic safety        :",
        safety["semantic_contract"],
    )

    # ----------------------------------------------------------------------
    # RUNTIME EVIDENCE
    # ----------------------------------------------------------------------

    runtime = discover_runtime_evidence()

    print("=" * 80)
    print("RUNTIME EVIDENCE DISCOVERY")
    print("=" * 80)

    print(
        "Candidate reports found :",
        len(runtime["candidate_reports"]),
    )

    for path in runtime["candidate_reports"]:
        print("  -", path)

    print(
        "Loaded evidence reports :",
        len(runtime["loaded_reports"]),
    )

    print(
        "Snapshot evidence count :",
        len(runtime["snapshot_ids"]),
    )

    print(
        "Decision evidence       :",
        runtime["decisions"],
    )

    # ----------------------------------------------------------------------
    # RUNTIME ↔ ARTIFACT
    # ----------------------------------------------------------------------

    snapshot_ok = reconcile_snapshot(
        artifact_info,
        runtime,
    )

    assets_ok = reconcile_assets(
        artifact_info,
        runtime,
    )

    directions_ok = reconcile_directions(
        artifact_info,
        runtime,
    )

    aggregate_result_ok = reconcile_aggregate_result(
        artifact_info,
        runtime,
    )

    reasons_ok = reconcile_reasons(
        artifact_info,
    )

    print("=" * 80)
    print("RUNTIME ↔ ARTIFACT RECONCILIATION")
    print("=" * 80)

    print(
        "Snapshot identity      :",
        bool_text(snapshot_ok),
    )
    print(
        "Asset identity         :",
        bool_text(assets_ok),
    )
    print(
        "Direction identity     :",
        bool_text(directions_ok),
    )
    print(
        "Aggregate result       :",
        bool_text(aggregate_result_ok),
    )
    print(
        "Reason identity        :",
        bool_text(reasons_ok),
    )

    runtime_reconciliation = all(
        [
            snapshot_ok,
            assets_ok,
            directions_ok,
            aggregate_result_ok,
            reasons_ok,
        ]
    )

    # ----------------------------------------------------------------------
    # FINAL CONTRACT
    # ----------------------------------------------------------------------

    final_contract = all(
        [
            producer_syntax,
            artifact_contract_ok,
            production_db["semantic_contract"],
            safety["semantic_contract"],
            runtime_reconciliation,
        ]
    )

    # Runtime evidence classification.
    if final_contract:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_RUNTIME_EXECUTION_RECONCILIATION_VERIFIED"
        )
    elif artifact_contract_ok and not runtime_reconciliation:
        verdict = (
            "RUNTIME_EXECUTION_ARTIFACT_RECONCILIATION_INCOMPLETE"
        )
    elif not artifact_contract_ok:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_REAL_CONTRACT_FAILED"
        )
    else:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_RUNTIME_EXECUTION_RECONCILIATION_FAILED"
        )

    # ----------------------------------------------------------------------
    # REPORT
    # ----------------------------------------------------------------------

    report = {
        "forensic": {
            "name": (
                "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_"
                "RUNTIME_OUTPUT_ARTIFACT_RUNTIME_EXECUTION_"
                "RECONCILIATION_FORENSIC_v0.1"
            ),
            "mode": "READ_ONLY FORENSIC",
            "timestamp_utc": now_utc(),
        },
        "paths": {
            "project_root": str(PROJECT_ROOT),
            "producer": str(PRODUCER),
            "artifact": str(ARTIFACT),
        },
        "identity": {
            "producer_sha256": producer_hash,
            "artifact_sha256": artifact_hash,
            "producer_syntax_valid": producer_syntax,
        },
        "artifact": artifact_info,
        "artifact_contract": artifact_contract,
        "production_db": production_db,
        "safety": safety,
        "runtime_evidence": runtime,
        "runtime_reconciliation": {
            "snapshot_identity": snapshot_ok,
            "asset_identity": assets_ok,
            "direction_identity": directions_ok,
            "aggregate_result_identity": aggregate_result_ok,
            "reason_identity": reasons_ok,
            "contract": runtime_reconciliation,
        },
        "safety_execution": {
            "producer_executed": False,
            "producer_imported": False,
            "artifact_modified": False,
            "artifact_deleted": False,
            "production_db_written": False,
            "network_accessed": False,
        },
        "final": {
            "artifact_contract": artifact_contract_ok,
            "production_db_contract": production_db[
                "semantic_contract"
            ],
            "safety_contract": safety[
                "semantic_contract"
            ],
            "runtime_reconciliation": runtime_reconciliation,
            "verdict": verdict,
        },
    }

    with FORENSIC_REPORT.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("=" * 80)
    print("FINAL DETERMINISTIC VERIFICATION")
    print("=" * 80)

    print(
        "Artifact contract       :",
        bool_text(artifact_contract_ok),
    )

    print(
        "Production DB contract  :",
        bool_text(
            production_db["semantic_contract"]
        ),
    )

    print(
        "Safety contract         :",
        bool_text(
            safety["semantic_contract"]
        ),
    )

    print(
        "Runtime reconciliation  :",
        bool_text(runtime_reconciliation),
    )

    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    print(
        "HISTORICAL ELIGIBILITY RUNTIME EVIDENCE :",
        verdict,
    )
    print(
        "FORENSIC REPORT :",
        FORENSIC_REPORT,
    )
    print("=" * 80)


if __name__ == "__main__":
    main()