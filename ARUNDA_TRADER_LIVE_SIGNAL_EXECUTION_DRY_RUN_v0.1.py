import json
import hashlib
from pathlib import Path
from typing import Any


# =============================================================================
# ARUNDA TRADER
# LIVE SIGNAL EXECUTION DRY-RUN / ORDER-INTENT LAYER v0.2
# =============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

UPSTREAM_RUNTIME = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_EXECUTION_RUNTIME_REPORT.json"
)

UPSTREAM_ARTIFACT = (
    PROJECT_ROOT
    / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_EXECUTION_DRY_RUN_REPORT.json"
)

EXPECTED_ARTIFACT_SHA256 = (
    "f77c1b1cc98982b8edcb89c923a7c2ef52e40a654ba5e705a4a0be95490b5417"
)


# =============================================================================
# SAFETY CONTRACT
# =============================================================================

SAFETY = {
    "producer_execution": False,
    "producer_import": False,
    "production_db_write": False,
    "network_access": False,
    "order_execution": False,
    "order_creation": False,
    "order_submission": False,
    "artifact_mutation": False,
}


# =============================================================================
# BASIC UTILITIES
# =============================================================================

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"JSON root must be an object: {path}"
        )

    return data


def require_key(
    obj: dict,
    key: str,
    expected_type: type,
):
    if key not in obj:
        raise ValueError(
            f"Missing required contract field: {key}"
        )

    value = obj[key]

    if not isinstance(value, expected_type):
        raise ValueError(
            f"Invalid type for '{key}': "
            f"expected {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )

    return value


# =============================================================================
# RUNTIME CONTRACT
# =============================================================================

def verify_runtime(runtime: dict) -> dict:
    runtime_section = runtime.get("runtime")

    if not isinstance(runtime_section, dict):
        raise ValueError(
            "Runtime contract missing: 'runtime'"
        )

    runtime_ready = (
        runtime_section.get("runtime_ready") is True
    )

    operational_safety = (
        runtime_section.get("operational_safety") is True
    )

    upstream_verified = (
        runtime_section.get("upstream_verified") is True
    )

    artifact_verified = (
        runtime_section.get("artifact_verified") is True
    )

    execution_allowed = (
        runtime_section.get("execution_allowed") is True
    )

    verdict = runtime.get("final_verdict")

    verdict_verified = (
        verdict == "LIVE_SIGNAL_EXECUTION_RUNTIME_READY"
    )

    runtime_verified = all(
        [
            runtime_ready,
            operational_safety,
            upstream_verified,
            artifact_verified,
            verdict_verified,
        ]
    )

    return {
        "runtime_ready": runtime_ready,
        "operational_safety": operational_safety,
        "upstream_verified": upstream_verified,
        "artifact_verified": artifact_verified,
        "execution_allowed": execution_allowed,
        "verdict_verified": verdict_verified,
        "runtime_verified": runtime_verified,
        "verdict": verdict,
    }


# =============================================================================
# REAL PRODUCER CONTRACT
#
# Verified by:
# ARUNDA_TRADER_ARTIFACT_PRODUCER_CONTRACT_FORENSICS_REPORT.json
#
# ROOT:
#   frontier
#   timestamp_utc
#   production_db
#   capture_db
#   engine
#   snapshot_id
#   gate_configuration
#   rows
#   eligible_rows
#   no_trade_rows
#   decision
#   row_results
#   safety
#
# ROWS:
#   id
#   asset
#   timestamp
#   direction
#   confidence
#   regime
#   signal_strength
#   data_quality
#   entry_price
#   available_weight
#   missing_arm_penalty
#   market_available
#   positioning_available
#   news_available
#   status
#   eligible
#   reasons
# =============================================================================

def verify_artifact(artifact: dict) -> dict:
    # -------------------------------------------------------------------------
    # Root contract
    # -------------------------------------------------------------------------

    frontier = require_key(
        artifact,
        "frontier",
        str,
    )

    timestamp_utc = require_key(
        artifact,
        "timestamp_utc",
        str,
    )

    snapshot_id = require_key(
        artifact,
        "snapshot_id",
        str,
    )

    rows = require_key(
        artifact,
        "rows",
        int,
    )

    eligible_rows = require_key(
        artifact,
        "eligible_rows",
        int,
    )

    no_trade_rows = require_key(
        artifact,
        "no_trade_rows",
        int,
    )

    decision = require_key(
        artifact,
        "decision",
        str,
    )

    row_results = require_key(
        artifact,
        "row_results",
        list,
    )

    # -------------------------------------------------------------------------
    # Root counters
    # -------------------------------------------------------------------------

    if rows != len(row_results):
        return {
            "contract": False,
            "verified": False,
            "reason": "ROOT_ROWS_COUNT_MISMATCH",
            "rows": rows,
            "eligible_rows": eligible_rows,
            "no_trade_rows": no_trade_rows,
            "decision": decision,
            "assets": [],
            "directions": [],
            "snapshot_id": snapshot_id,
            "source_shape": "ROOT_ROW_RESULTS",
            "artifact_identity": False,
        }

    # -------------------------------------------------------------------------
    # Validate every real Producer row
    # -------------------------------------------------------------------------

    normalized_rows = []

    for index, row in enumerate(row_results):

        if not isinstance(row, dict):
            return {
                "contract": False,
                "verified": False,
                "reason": f"ROW_{index}_NOT_OBJECT",
                "rows": rows,
                "eligible_rows": eligible_rows,
                "no_trade_rows": no_trade_rows,
                "decision": decision,
                "assets": [],
                "directions": [],
                "snapshot_id": snapshot_id,
                "source_shape": "ROOT_ROW_RESULTS",
                "artifact_identity": False,
            }

        row_id = require_key(
            row,
            "id",
            int,
        )

        asset = require_key(
            row,
            "asset",
            str,
        )

        row_timestamp = require_key(
            row,
            "timestamp",
            str,
        )

        direction = require_key(
            row,
            "direction",
            str,
        )

        eligible = require_key(
            row,
            "eligible",
            bool,
        )

        status = require_key(
            row,
            "status",
            str,
        )

        reasons = require_key(
            row,
            "reasons",
            list,
        )

        confidence = require_key(
            row,
            "confidence",
            (int, float),
        )

        entry_price = require_key(
            row,
            "entry_price",
            (int, float),
        )

        normalized_rows.append(
            {
                "id": row_id,
                "asset": asset,
                "timestamp": row_timestamp,
                "direction": direction,
                "eligible": eligible,
                "status": status,
                "reasons": reasons,
                "confidence": confidence,
                "entry_price": entry_price,
            }
        )

    # -------------------------------------------------------------------------
    # Derive values ONLY from actual row_results
    # -------------------------------------------------------------------------

    assets = [
        row["asset"]
        for row in normalized_rows
    ]

    directions = [
        row["direction"]
        for row in normalized_rows
    ]

    calculated_eligible_rows = sum(
        1
        for row in normalized_rows
        if row["eligible"] is True
    )

    calculated_no_trade_rows = sum(
        1
        for row in normalized_rows
        if row["status"] == "NO_TRADE"
    )

    # -------------------------------------------------------------------------
    # Counter consistency
    # -------------------------------------------------------------------------

    if eligible_rows != calculated_eligible_rows:
        return {
            "contract": False,
            "verified": False,
            "reason": "ELIGIBLE_ROW_COUNT_MISMATCH",
            "rows": rows,
            "eligible_rows": eligible_rows,
            "no_trade_rows": no_trade_rows,
            "decision": decision,
            "assets": assets,
            "directions": directions,
            "snapshot_id": snapshot_id,
            "source_shape": "ROOT_ROW_RESULTS",
            "artifact_identity": True,
        }

    if no_trade_rows != calculated_no_trade_rows:
        return {
            "contract": False,
            "verified": False,
            "reason": "NO_TRADE_ROW_COUNT_MISMATCH",
            "rows": rows,
            "eligible_rows": eligible_rows,
            "no_trade_rows": no_trade_rows,
            "decision": decision,
            "assets": assets,
            "directions": directions,
            "snapshot_id": snapshot_id,
            "source_shape": "ROOT_ROW_RESULTS",
            "artifact_identity": True,
        }

    # -------------------------------------------------------------------------
    # Decision consistency
    # -------------------------------------------------------------------------

    if eligible_rows == 0:
        if decision != "NO_TRADE":
            return {
                "contract": False,
                "verified": False,
                "reason": "DECISION_ELIGIBILITY_MISMATCH",
                "rows": rows,
                "eligible_rows": eligible_rows,
                "no_trade_rows": no_trade_rows,
                "decision": decision,
                "assets": assets,
                "directions": directions,
                "snapshot_id": snapshot_id,
                "source_shape": "ROOT_ROW_RESULTS",
                "artifact_identity": True,
            }

    # -------------------------------------------------------------------------
    # Current artifact-specific verification
    #
    # We do NOT require this for all future eligible artifacts.
    # It simply verifies that the current artifact's NO_TRADE state is coherent.
    # -------------------------------------------------------------------------

    if decision == "NO_TRADE":

        if no_trade_rows != rows:
            return {
                "contract": False,
                "verified": False,
                "reason": "NO_TRADE_DECISION_ROW_MISMATCH",
                "rows": rows,
                "eligible_rows": eligible_rows,
                "no_trade_rows": no_trade_rows,
                "decision": decision,
                "assets": assets,
                "directions": directions,
                "snapshot_id": snapshot_id,
                "source_shape": "ROOT_ROW_RESULTS",
                "artifact_identity": True,
            }

        if eligible_rows != 0:
            return {
                "contract": False,
                "verified": False,
                "reason": "NO_TRADE_WITH_ELIGIBLE_ROWS",
                "rows": rows,
                "eligible_rows": eligible_rows,
                "no_trade_rows": no_trade_rows,
                "decision": decision,
                "assets": assets,
                "directions": directions,
                "snapshot_id": snapshot_id,
                "source_shape": "ROOT_ROW_RESULTS",
                "artifact_identity": True,
            }

    # -------------------------------------------------------------------------
    # Artifact identity
    #
    # Identity means that the actual Producer row data exists and is internally
    # coherent. No invented asset/direction fields are used.
    # -------------------------------------------------------------------------

    artifact_identity = (
        len(normalized_rows) == rows
        and len(assets) == rows
        and len(directions) == rows
        and all(
            isinstance(asset, str) and asset.strip()
            for asset in assets
        )
        and all(
            isinstance(direction, str) and direction.strip()
            for direction in directions
        )
    )

    contract = (
        artifact_identity
        and rows >= 0
        and eligible_rows >= 0
        and no_trade_rows >= 0
    )

    verified = contract

    return {
        "contract": contract,
        "verified": verified,
        "rows": rows,
        "eligible_rows": eligible_rows,
        "no_trade_rows": no_trade_rows,
        "decision": decision,
        "assets": assets,
        "directions": directions,
        "snapshot_id": snapshot_id,
        "source_shape": "ROOT_ROW_RESULTS",
        "artifact_identity": artifact_identity,
        "frontier": frontier,
        "timestamp_utc": timestamp_utc,
        "row_results": normalized_rows,
    }


# =============================================================================
# ORDER INTENT VALIDATION
# =============================================================================

def validate_order_intent(row: dict) -> tuple[bool, str]:
    if row["eligible"] is not True:
        return False, "SIGNAL_NOT_ELIGIBLE"

    if row["status"] != "ELIGIBLE":
        return False, "STATUS_NOT_ELIGIBLE"

    if row["direction"] not in ("LONG", "SHORT"):
        return False, "INVALID_EXECUTION_DIRECTION"

    if not isinstance(row["asset"], str) or not row["asset"].strip():
        return False, "INVALID_ASSET"

    if not isinstance(row["entry_price"], (int, float)):
        return False, "INVALID_ENTRY_PRICE"

    if row["entry_price"] <= 0:
        return False, "INVALID_ENTRY_PRICE"

    return True, "VALID"


def build_order_intents(
    artifact_info: dict,
) -> dict:

    if artifact_info["contract"] is not True:
        return {
            "status": "BLOCKED",
            "order_intents": [],
            "validated_intents": 0,
            "invalid_intents": 0,
        }

    intents = []
    invalid_intents = 0

    for row in artifact_info["row_results"]:

        if row["eligible"] is not True:
            continue

        valid, reason = validate_order_intent(row)

        intent = {
            "asset": row["asset"],
            "direction": row["direction"],
            "entry_price": row["entry_price"],
            "timestamp": row["timestamp"],
            "source_row_id": row["id"],
            "snapshot_id": artifact_info["snapshot_id"],
            "dry_run": True,
            "network_access": False,
            "order_creation": False,
            "order_submission": False,
            "order_execution": False,
            "validated": valid,
            "validation_reason": reason,
        }

        intents.append(intent)

        if not valid:
            invalid_intents += 1

    validated_intents = sum(
        1
        for intent in intents
        if intent["validated"] is True
    )

    return {
        "status": "READY",
        "order_intents": intents,
        "validated_intents": validated_intents,
        "invalid_intents": invalid_intents,
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 80)
    print("ARUNDA TRADER")
    print("LIVE SIGNAL EXECUTION DRY-RUN / ORDER-INTENT LAYER v0.2")
    print("=" * 80)

    print(f"PROJECT ROOT    : {PROJECT_ROOT}")
    print(f"UPSTREAM RUNTIME: {UPSTREAM_RUNTIME}")
    print(f"UPSTREAM ARTIFACT: {UPSTREAM_ARTIFACT}")
    print(f"OUTPUT REPORT   : {OUTPUT_REPORT}")

    print("=" * 80)
    print("SAFETY")
    print("=" * 80)

    print(
        f"producer_execution     : "
        f"{SAFETY['producer_execution']}"
    )
    print(
        f"producer_import        : "
        f"{SAFETY['producer_import']}"
    )
    print(
        f"production_db_write    : "
        f"{SAFETY['production_db_write']}"
    )
    print(
        f"network_access         : "
        f"{SAFETY['network_access']}"
    )
    print(
        f"order_execution        : "
        f"{SAFETY['order_execution']}"
    )
    print(
        f"order_creation         : "
        f"{SAFETY['order_creation']}"
    )
    print(
        f"order_submission       : "
        f"{SAFETY['order_submission']}"
    )
    print(
        f"artifact_mutation      : "
        f"{SAFETY['artifact_mutation']}"
    )

    # -------------------------------------------------------------------------
    # File existence
    # -------------------------------------------------------------------------

    if not UPSTREAM_RUNTIME.exists():
        raise FileNotFoundError(
            f"Missing upstream runtime: {UPSTREAM_RUNTIME}"
        )

    if not UPSTREAM_ARTIFACT.exists():
        raise FileNotFoundError(
            f"Missing upstream artifact: {UPSTREAM_ARTIFACT}"
        )

    # -------------------------------------------------------------------------
    # Load
    # -------------------------------------------------------------------------

    runtime = load_json(
        UPSTREAM_RUNTIME
    )

    artifact = load_json(
        UPSTREAM_ARTIFACT
    )

    # -------------------------------------------------------------------------
    # Runtime verification
    # -------------------------------------------------------------------------

    runtime_info = verify_runtime(
        runtime
    )

    # -------------------------------------------------------------------------
    # Artifact file identity
    # -------------------------------------------------------------------------

    actual_artifact_sha256 = sha256_file(
        UPSTREAM_ARTIFACT
    )

    artifact_file_match = (
        actual_artifact_sha256
        == EXPECTED_ARTIFACT_SHA256
    )

    # -------------------------------------------------------------------------
    # Artifact contract
    # -------------------------------------------------------------------------

    try:
        artifact_info = verify_artifact(
            artifact
        )

    except (ValueError, TypeError) as exc:

        artifact_info = {
            "contract": False,
            "verified": False,
            "rows": 0,
            "eligible_rows": 0,
            "no_trade_rows": 0,
            "decision": None,
            "assets": [],
            "directions": [],
            "snapshot_id": None,
            "source_shape": "ROOT_ROW_RESULTS",
            "artifact_identity": False,
            "reason": str(exc),
            "row_results": [],
        }

    artifact_info["artifact_file_match"] = (
        artifact_file_match
    )

    # -------------------------------------------------------------------------
    # Dry-run
    # -------------------------------------------------------------------------

    order_result = build_order_intents(
        artifact_info
    )

    dry_run_ready = (
        runtime_info["runtime_verified"]
        and artifact_info["contract"]
        and artifact_info["verified"]
        and artifact_file_match
        and SAFETY["network_access"] is False
        and SAFETY["order_submission"] is False
        and SAFETY["order_execution"] is False
    )

    # -------------------------------------------------------------------------
    # IMPORTANT:
    #
    # runtime can be READY while execution remains forbidden.
    #
    # Current artifact has zero eligible rows, therefore zero order intents.
    # -------------------------------------------------------------------------

    if artifact_info["eligible_rows"] == 0:

        dry_run_status = (
            "READY_NO_ELIGIBLE_SIGNALS"
            if dry_run_ready
            else "BLOCKED"
        )

    else:

        dry_run_status = (
            "READY"
            if dry_run_ready
            else "BLOCKED"
        )

    execution_performed = False
    orders_created = 0
    orders_submitted = 0

    if dry_run_ready:
        final_verdict = (
            "LIVE_SIGNAL_EXECUTION_DRY_RUN_READY"
        )
        next_stage = (
            "LIVE_SIGNAL_EXECUTION_ORDER_INTENT_VALIDATION"
        )
    else:
        final_verdict = (
            "LIVE_SIGNAL_EXECUTION_DRY_RUN_BLOCKED"
        )
        next_stage = (
            "ARTIFACT_PRODUCER_CONSUMER_CONTRACT_REPAIR"
        )

    # -------------------------------------------------------------------------
    # Terminal output
    # -------------------------------------------------------------------------

    print("=" * 80)
    print("UPSTREAM RUNTIME")
    print("=" * 80)

    print(
        f"runtime_ready       : "
        f"{runtime_info['runtime_ready']}"
    )

    print(
        f"operational_safety  : "
        f"{runtime_info['operational_safety']}"
    )

    print(
        f"upstream_verified   : "
        f"{runtime_info['upstream_verified']}"
    )

    print(
        f"artifact_verified   : "
        f"{runtime_info['artifact_verified']}"
    )

    print(
        f"verdict_verified    : "
        f"{runtime_info['verdict_verified']}"
    )

    print(
        f"runtime_verified    : "
        f"{runtime_info['runtime_verified']}"
    )

    print(
        f"verdict             : "
        f"{runtime_info['verdict']}"
    )

    print("=" * 80)
    print("ARTIFACT")
    print("=" * 80)

    print(
        f"contract            : "
        f"{artifact_info['contract']}"
    )

    print(
        f"verified            : "
        f"{artifact_info['verified']}"
    )

    print(
        f"rows                : "
        f"{artifact_info['rows']}"
    )

    print(
        f"eligible_rows       : "
        f"{artifact_info['eligible_rows']}"
    )

    print(
        f"no_trade_rows       : "
        f"{artifact_info['no_trade_rows']}"
    )

    print(
        f"decision            : "
        f"{artifact_info['decision']}"
    )

    print(
        f"assets              : "
        f"{artifact_info['assets']}"
    )

    print(
        f"directions          : "
        f"{artifact_info['directions']}"
    )

    print(
        f"snapshot_id         : "
        f"{artifact_info['snapshot_id']}"
    )

    print(
        f"source_shape        : "
        f"{artifact_info['source_shape']}"
    )

    print(
        f"artifact_identity   : "
        f"{artifact_info['artifact_identity']}"
    )

    print(
        f"artifact_file_match : "
        f"{artifact_info['artifact_file_match']}"
    )

    if "reason" in artifact_info:
        print(
            f"reason              : "
            f"{artifact_info['reason']}"
        )

    print("=" * 80)
    print("BUILDING ORDER-INTENT DRY-RUN")
    print("=" * 80)

    print(
        f"RUNTIME CONTRACT    : "
        f"{'VERIFIED' if runtime_info['runtime_verified'] else 'BLOCKED'}"
    )

    print(
        f"ARTIFACT CONTRACT   : "
        f"{'VERIFIED' if artifact_info['contract'] else 'BLOCKED'}"
    )

    print(
        f"DRY-RUN STATUS      : "
        f"{dry_run_status}"
    )

    print(
        f"ORDER INTENTS       : "
        f"{len(order_result['order_intents'])}"
    )

    print(
        f"VALIDATED INTENTS   : "
        f"{order_result['validated_intents']}"
    )

    print(
        f"INVALID INTENTS     : "
        f"{order_result['invalid_intents']}"
    )

    print("=" * 80)
    print("ORDER-INTENT SAFETY")
    print("=" * 80)

    print(
        f"Network access      : "
        f"{SAFETY['network_access']}"
    )

    print(
        f"Order creation      : "
        f"{SAFETY['order_creation']}"
    )

    print(
        f"Order submission    : "
        f"{SAFETY['order_submission']}"
    )

    print(
        f"Order execution     : "
        f"{SAFETY['order_execution']}"
    )

    print(
        f"Production DB write : "
        f"{SAFETY['production_db_write']}"
    )

    print("=" * 80)
    print("ORDER-INTENT DETAILS")
    print("=" * 80)

    if not artifact_info["contract"]:

        print(
            "Order-intent generation blocked because "
            "artifact contract is invalid."
        )

    elif artifact_info["eligible_rows"] == 0:

        print(
            "No eligible signal exists in the current artifact."
        )

        print(
            "No order intent was generated."
        )

    else:

        for intent in order_result["order_intents"]:

            print(
                f"ASSET={intent['asset']} "
                f"DIRECTION={intent['direction']} "
                f"ENTRY={intent['entry_price']} "
                f"VALIDATED={intent['validated']} "
                f"REASON={intent['validation_reason']}"
            )

    print("=" * 80)
    print("FINAL DRY-RUN VERDICT")
    print("=" * 80)

    print(
        f"DRY-RUN VERDICT : "
        f"{final_verdict}"
    )

    print(
        f"EXECUTION        : "
        f"{'EXECUTED' if execution_performed else 'NOT_EXECUTED'}"
    )

    print(
        f"ORDERS CREATED   : "
        f"{orders_created}"
    )

    print(
        f"ORDERS SUBMITTED : "
        f"{orders_submitted}"
    )

    print(
        f"NEXT STAGE       : "
        f"{next_stage}"
    )

    # -------------------------------------------------------------------------
    # Report
    # -------------------------------------------------------------------------

    report = {
        "project": "ARUNDA TRADER",
        "component": (
            "LIVE SIGNAL EXECUTION DRY-RUN / "
            "ORDER-INTENT LAYER"
        ),
        "version": "v0.2",

        "safety": SAFETY,

        "upstream_runtime": {
            "path": str(UPSTREAM_RUNTIME),
            **runtime_info,
        },

        "artifact": {
            "path": str(UPSTREAM_ARTIFACT),
            "sha256": actual_artifact_sha256,
            "expected_sha256": EXPECTED_ARTIFACT_SHA256,
            **artifact_info,
        },

        "order_intent": {
            "status": order_result["status"],
            "order_intents": order_result["order_intents"],
            "validated_intents": order_result["validated_intents"],
            "invalid_intents": order_result["invalid_intents"],
        },

        "execution": {
            "executed": execution_performed,
            "orders_created": orders_created,
            "orders_submitted": orders_submitted,
        },

        "dry_run": {
            "ready": dry_run_ready,
            "status": dry_run_status,
            "network_access": False,
            "order_creation": False,
            "order_submission": False,
            "order_execution": False,
            "production_db_write": False,
        },

        "final_verdict": final_verdict,
        "next_stage": next_stage,
    }

    OUTPUT_REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("=" * 80)
    print(
        f"OUTPUT : {OUTPUT_REPORT}"
    )

    print(
        f"REPORT WRITTEN : {OUTPUT_REPORT}"
    )


if __name__ == "__main__":
    main()