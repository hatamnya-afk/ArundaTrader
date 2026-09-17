import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

RUNTIME_PATH = PROJECT_ROOT / (
    "ARUNDA_TRADER_LIVE_SIGNAL_EXECUTION_RUNTIME_REPORT.json"
)

ARTIFACT_PATH = PROJECT_ROOT / (
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
)

OUTPUT_PATH = PROJECT_ROOT / (
    "ARUNDA_TRADER_LIVE_SIGNAL_EXECUTION_ORDER_INTENT_VALIDATION_REPORT.json"
)


# ============================================================================
# SAFETY — ABSOLUTE READ ONLY
# ============================================================================

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


def sha256_file(path: Path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def is_bool(value):
    return isinstance(value, bool)


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def is_list(value):
    return isinstance(value, list)


def validate_runtime_contract(runtime):
    """
    REAL CONTRACT PATHS CONFIRMED BY FORENSICS:

        $.safety
        $.upstream_gate
        $.identity
        $.artifact
        $.runtime
        $.execution
        $.final_verdict
        $.next_stage
    """

    if not isinstance(runtime, dict):
        return False, "RUNTIME_ROOT_NOT_DICT"

    required_sections = [
        "safety",
        "upstream_gate",
        "identity",
        "artifact",
        "runtime",
        "execution",
        "final_verdict",
        "next_stage",
    ]

    for section in required_sections:
        if section not in runtime:
            return False, f"RUNTIME_SECTION_MISSING:{section}"

    safety = runtime["safety"]
    gate = runtime["upstream_gate"]
    identity = runtime["identity"]
    artifact = runtime["artifact"]
    runtime_section = runtime["runtime"]
    execution = runtime["execution"]

    if not isinstance(safety, dict):
        return False, "SAFETY_SECTION_INVALID"

    if not isinstance(gate, dict):
        return False, "UPSTREAM_GATE_SECTION_INVALID"

    if not isinstance(identity, dict):
        return False, "IDENTITY_SECTION_INVALID"

    if not isinstance(artifact, dict):
        return False, "ARTIFACT_SECTION_INVALID"

    if not isinstance(runtime_section, dict):
        return False, "RUNTIME_SECTION_INVALID"

    if not isinstance(execution, dict):
        return False, "EXECUTION_SECTION_INVALID"

    # ------------------------------------------------------------------------
    # REAL upstream_gate contract
    # ------------------------------------------------------------------------

    required_gate_keys = [
        "producer_identity",
        "artifact_identity",
        "artifact_contract",
        "operational_safety",
        "upstream_contract_verified",
        "execution_gate_ready",
        "release_gate_verified",
        "gate_name",
        "gate_state",
        "verdict",
        "identity_contract",
        "contracts_verified",
        "release_verified",
        "verdict_verified",
        "gate_ready",
    ]

    for key in required_gate_keys:
        if key not in gate:
            return False, f"UPSTREAM_GATE_KEY_MISSING:{key}"

    if gate["gate_name"] != "LIVE_SIGNAL_EXECUTION_GATE":
        return False, "INVALID_GATE_NAME"

    if gate["gate_state"] != "READY":
        return False, "UPSTREAM_GATE_NOT_READY"

    if gate["verdict"] != "LIVE_SIGNAL_EXECUTION_GATE_READY":
        return False, "UPSTREAM_GATE_VERDICT_INVALID"

    bool_gate_keys = [
        "producer_identity",
        "artifact_identity",
        "artifact_contract",
        "operational_safety",
        "upstream_contract_verified",
        "execution_gate_ready",
        "release_gate_verified",
        "identity_contract",
        "contracts_verified",
        "release_verified",
        "verdict_verified",
        "gate_ready",
    ]

    for key in bool_gate_keys:
        if gate[key] is not True:
            return False, f"UPSTREAM_GATE_NOT_VERIFIED:{key}"

    # ------------------------------------------------------------------------
    # REAL identity contract
    # ------------------------------------------------------------------------

    identity_keys = [
        "producer_match",
        "artifact_match",
        "chain_match",
        "artifact_file_match",
    ]

    for key in identity_keys:
        if identity.get(key) is not True:
            return False, f"IDENTITY_NOT_VERIFIED:{key}"

    # ------------------------------------------------------------------------
    # REAL artifact contract
    # ------------------------------------------------------------------------

    artifact_required = [
        "path",
        "contract",
        "verified",
        "rows",
        "eligible_rows",
        "no_trade_rows",
        "decision",
        "assets",
        "directions",
        "snapshot_id",
        "row_count_contract",
        "decision_contract",
        "identity_contract",
        "snapshot_contract",
        "verified_contract",
        "upstream_artifact_contract",
        "upstream_artifact_identity",
    ]

    for key in artifact_required:
        if key not in artifact:
            return False, f"ARTIFACT_KEY_MISSING:{key}"

    artifact_bool_keys = [
        "contract",
        "verified",
        "row_count_contract",
        "decision_contract",
        "identity_contract",
        "snapshot_contract",
        "verified_contract",
        "upstream_artifact_contract",
        "upstream_artifact_identity",
    ]

    for key in artifact_bool_keys:
        if artifact[key] is not True:
            return False, f"ARTIFACT_CONTRACT_FAILED:{key}"

    if not is_int(artifact["rows"]):
        return False, "ARTIFACT_ROWS_INVALID"

    if not is_int(artifact["eligible_rows"]):
        return False, "ARTIFACT_ELIGIBLE_ROWS_INVALID"

    if not is_int(artifact["no_trade_rows"]):
        return False, "ARTIFACT_NO_TRADE_ROWS_INVALID"

    if artifact["rows"] != (
        artifact["eligible_rows"] + artifact["no_trade_rows"]
    ):
        return False, "ARTIFACT_ROW_COUNT_MISMATCH"

    if not is_list(artifact["assets"]):
        return False, "ARTIFACT_ASSETS_INVALID"

    if not is_list(artifact["directions"]):
        return False, "ARTIFACT_DIRECTIONS_INVALID"

    if len(artifact["assets"]) != artifact["rows"]:
        return False, "ARTIFACT_ASSET_COUNT_MISMATCH"

    if len(artifact["directions"]) != artifact["rows"]:
        return False, "ARTIFACT_DIRECTION_COUNT_MISMATCH"

    if not artifact["snapshot_id"]:
        return False, "ARTIFACT_SNAPSHOT_ID_MISSING"

    # ------------------------------------------------------------------------
    # REAL runtime contract
    # ------------------------------------------------------------------------

    runtime_required = [
        "upstream_verified",
        "artifact_verified",
        "operational_safety",
        "runtime_ready",
        "execution_allowed",
        "execution",
        "orders_created",
        "orders_submitted",
    ]

    for key in runtime_required:
        if key not in runtime_section:
            return False, f"RUNTIME_KEY_MISSING:{key}"

    if runtime_section["upstream_verified"] is not True:
        return False, "UPSTREAM_RUNTIME_NOT_VERIFIED"

    if runtime_section["artifact_verified"] is not True:
        return False, "ARTIFACT_RUNTIME_NOT_VERIFIED"

    if runtime_section["operational_safety"] is not True:
        return False, "RUNTIME_OPERATIONAL_SAFETY_FAILED"

    if runtime_section["runtime_ready"] is not True:
        return False, "RUNTIME_NOT_READY"

    if runtime_section["execution_allowed"] is not False:
        return False, "EXECUTION_ALLOWED_MUST_REMAIN_FALSE"

    if runtime_section["execution"] != "NOT_EXECUTED":
        return False, "RUNTIME_EXECUTION_STATE_INVALID"

    if runtime_section["orders_created"] != 0:
        return False, "RUNTIME_ORDERS_CREATED_NOT_ZERO"

    if runtime_section["orders_submitted"] != 0:
        return False, "RUNTIME_ORDERS_SUBMITTED_NOT_ZERO"

    # ------------------------------------------------------------------------
    # REAL execution contract
    # ------------------------------------------------------------------------

    if execution.get("executed") is not False:
        return False, "EXECUTION_EXECUTED_FLAG_INVALID"

    if execution.get("orders_created") != 0:
        return False, "EXECUTION_ORDERS_CREATED_NOT_ZERO"

    if execution.get("orders_submitted") != 0:
        return False, "EXECUTION_ORDERS_SUBMITTED_NOT_ZERO"

    if runtime["final_verdict"] != "LIVE_SIGNAL_EXECUTION_RUNTIME_READY":
        return False, "FINAL_RUNTIME_VERDICT_INVALID"

    return True, "RUNTIME_CONTRACT_VERIFIED"


def validate_artifact_contract(artifact):
    if not isinstance(artifact, dict):
        return False, "ARTIFACT_ROOT_NOT_DICT", {}

    required = [
        "snapshot_id",
        "rows",
        "eligible_rows",
        "no_trade_rows",
        "decision",
        "row_results",
    ]

    for key in required:
        if key not in artifact:
            return False, f"ARTIFACT_ROOT_KEY_MISSING:{key}", {}

    rows = artifact["rows"]
    eligible_rows = artifact["eligible_rows"]
    no_trade_rows = artifact["no_trade_rows"]
    row_results = artifact["row_results"]

    if not is_int(rows):
        return False, "ROWS_INVALID", {}

    if not is_int(eligible_rows):
        return False, "ELIGIBLE_ROWS_INVALID", {}

    if not is_int(no_trade_rows):
        return False, "NO_TRADE_ROWS_INVALID", {}

    if not isinstance(row_results, list):
        return False, "ROW_RESULTS_INVALID", {}

    if len(row_results) != rows:
        return False, "ROW_RESULTS_COUNT_MISMATCH", {}

    if rows != eligible_rows + no_trade_rows:
        return False, "ROW_COUNT_CONTRACT_FAILED", {}

    assets = []
    directions = []
    eligible = []

    required_row_keys = [
        "id",
        "asset",
        "timestamp",
        "direction",
        "confidence",
        "regime",
        "signal_strength",
        "data_quality",
        "entry_price",
        "available_weight",
        "missing_arm_penalty",
        "market_available",
        "positioning_available",
        "news_available",
        "status",
        "eligible",
        "reasons",
    ]

    for row in row_results:
        if not isinstance(row, dict):
            return False, "ROW_NOT_DICT", {}

        for key in required_row_keys:
            if key not in row:
                return False, f"ROW_KEY_MISSING:{key}", {}

        assets.append(row["asset"])
        directions.append(row["direction"])
        eligible.append(row["eligible"])

    actual_eligible = sum(1 for x in eligible if x is True)

    if actual_eligible != eligible_rows:
        return False, "ELIGIBLE_ROW_COUNT_MISMATCH", {}

    actual_no_trade = sum(1 for x in eligible if x is False)

    if actual_no_trade != no_trade_rows:
        return False, "NO_TRADE_ROW_COUNT_MISMATCH", {}

    if artifact["decision"] not in {"NO_TRADE", "TRADE"}:
        return False, "INVALID_DECISION", {}

    if eligible_rows == 0 and artifact["decision"] != "NO_TRADE":
        return False, "DECISION_MISMATCH_NO_ELIGIBLE", {}

    if eligible_rows > 0 and artifact["decision"] != "TRADE":
        return False, "DECISION_MISMATCH_ELIGIBLE_ROWS", {}

    return True, "ARTIFACT_CONTRACT_VERIFIED", {
        "rows": rows,
        "eligible_rows": eligible_rows,
        "no_trade_rows": no_trade_rows,
        "decision": artifact["decision"],
        "assets": assets,
        "directions": directions,
        "snapshot_id": artifact["snapshot_id"],
        "eligible_rows_data": [
            row for row in row_results if row.get("eligible") is True
        ],
    }


def build_order_intent(row, snapshot_id):
    """
    Creates an in-memory Order Intent only.
    It NEVER creates an exchange order.
    """

    direction = str(row["direction"]).upper()

    intent = {
        "intent_id": (
            f"DRYRUN-{snapshot_id}-{row['asset']}-{row['id']}"
        ),
        "asset": row["asset"],
        "direction": direction,
        "entry_price": row["entry_price"],
        "signal_confidence": row["confidence"],
        "regime": row["regime"],
        "signal_strength": row["signal_strength"],
        "data_quality": row["data_quality"],
        "timestamp": row["timestamp"],
        "source_row_id": row["id"],
        "snapshot_id": snapshot_id,
        "execution_mode": "DRY_RUN",
        "network_access": False,
        "order_creation": False,
        "order_submission": False,
        "order_execution": False,
    }

    return intent


def validate_order_intent(intent):
    errors = []

    if not intent["asset"]:
        errors.append("ASSET_MISSING")

    if intent["direction"] not in {"LONG", "SHORT"}:
        errors.append("INVALID_EXECUTION_DIRECTION")

    if not isinstance(intent["entry_price"], (int, float)):
        errors.append("ENTRY_PRICE_INVALID")

    if intent["entry_price"] <= 0:
        errors.append("ENTRY_PRICE_NON_POSITIVE")

    if intent["execution_mode"] != "DRY_RUN":
        errors.append("INVALID_EXECUTION_MODE")

    if intent["network_access"] is not False:
        errors.append("NETWORK_ACCESS_VIOLATION")

    if intent["order_creation"] is not False:
        errors.append("ORDER_CREATION_VIOLATION")

    if intent["order_submission"] is not False:
        errors.append("ORDER_SUBMISSION_VIOLATION")

    if intent["order_execution"] is not False:
        errors.append("ORDER_EXECUTION_VIOLATION")

    return len(errors) == 0, errors


def main():

    started = datetime.now(timezone.utc).isoformat()

    runtime_exists = RUNTIME_PATH.exists()
    artifact_exists = ARTIFACT_PATH.exists()

    runtime = None
    artifact = None

    runtime_contract = False
    runtime_reason = "RUNTIME_NOT_LOADED"

    artifact_contract = False
    artifact_reason = "ARTIFACT_NOT_LOADED"
    artifact_data = {}

    if runtime_exists:
        try:
            runtime = load_json(RUNTIME_PATH)
            runtime_contract, runtime_reason = validate_runtime_contract(runtime)
        except Exception as exc:
            runtime_reason = f"RUNTIME_LOAD_ERROR:{type(exc).__name__}"

    if artifact_exists:
        try:
            artifact = load_json(ARTIFACT_PATH)
            (
                artifact_contract,
                artifact_reason,
                artifact_data,
            ) = validate_artifact_contract(artifact)
        except Exception as exc:
            artifact_reason = f"ARTIFACT_LOAD_ERROR:{type(exc).__name__}"

    # ========================================================================
    # ORDER-INTENT VALIDATION
    # ========================================================================

    order_intents = []
    validated_intents = []
    invalid_intents = []

    if runtime_contract and artifact_contract:

        eligible_rows = artifact_data.get(
            "eligible_rows_data",
            []
        )

        for row in eligible_rows:

            intent = build_order_intent(
                row,
                artifact_data["snapshot_id"]
            )

            order_intents.append(intent)

            valid, errors = validate_order_intent(intent)

            if valid:
                validated_intents.append(intent)
            else:
                invalid_intents.append(
                    {
                        "intent": intent,
                        "errors": errors,
                    }
                )

        if len(eligible_rows) == 0:
            validation_status = "READY_NO_ELIGIBLE_SIGNALS"
            final_verdict = "LIVE_SIGNAL_ORDER_INTENT_VALIDATION_READY"
            next_stage = "WAIT_FOR_ELIGIBLE_SIGNAL"

        elif len(invalid_intents) > 0:
            validation_status = "INTENTS_VALIDATION_FAILED"
            final_verdict = "LIVE_SIGNAL_ORDER_INTENT_VALIDATION_FAILED"
            next_stage = "ORDER_INTENT_REVIEW"

        else:
            validation_status = "READY_VALIDATED_INTENTS"
            final_verdict = "LIVE_SIGNAL_ORDER_INTENT_VALIDATION_READY"
            next_stage = "ORDER_INTENT_EXECUTION_GATE"

    else:

        validation_status = "BLOCKED_CONTRACT"

        final_verdict = "LIVE_SIGNAL_ORDER_INTENT_VALIDATION_BLOCKED"

        if not runtime_contract:
            next_stage = "RUNTIME_CONTRACT_REPAIR"

        else:
            next_stage = "ARTIFACT_CONTRACT_REPAIR"

    report = {
        "project": "ARUNDA TRADER",
        "component": "LIVE SIGNAL EXECUTION ORDER-INTENT VALIDATION",
        "version": "v0.3",

        "timestamp_utc": started,

        "safety": {
            **SAFETY,
            "operational_safety": True,
        },

        "project_paths": {
            "runtime": str(RUNTIME_PATH),
            "artifact": str(ARTIFACT_PATH),
            "output": str(OUTPUT_PATH),
        },

        "runtime_contract": {
            "contract": runtime_contract,
            "runtime_ready": (
                runtime.get("runtime", {}).get("runtime_ready")
                if isinstance(runtime, dict)
                else False
            ),
            "operational_safety": (
                runtime.get("runtime", {}).get("operational_safety")
                if isinstance(runtime, dict)
                else False
            ),
            "upstream_verified": (
                runtime.get("runtime", {}).get("upstream_verified")
                if isinstance(runtime, dict)
                else False
            ),
            "artifact_verified": (
                runtime.get("runtime", {}).get("artifact_verified")
                if isinstance(runtime, dict)
                else False
            ),
            "verdict_verified": (
                runtime.get("upstream_gate", {}).get("verdict_verified")
                if isinstance(runtime, dict)
                else False
            ),
            "verdict": (
                runtime.get("final_verdict")
                if isinstance(runtime, dict)
                else None
            ),
            "reason": runtime_reason,
        },

        "artifact_contract": {
            "contract": artifact_contract,
            "verified": artifact_contract,
            "rows": artifact_data.get("rows", 0),
            "eligible_rows": artifact_data.get("eligible_rows", 0),
            "no_trade_rows": artifact_data.get("no_trade_rows", 0),
            "decision": artifact_data.get("decision"),
            "assets": artifact_data.get("assets", []),
            "directions": artifact_data.get("directions", []),
            "snapshot_id": artifact_data.get("snapshot_id"),
            "reason": artifact_reason,
        },

        "order_intent_validation": {
            "status": validation_status,
            "eligible_signals": artifact_data.get(
                "eligible_rows",
                0
            ),
            "order_intents": len(order_intents),
            "validated_intents": len(validated_intents),
            "invalid_intents": len(invalid_intents),
            "intents": validated_intents,
            "invalid_details": invalid_intents,
        },

        "order_intent_safety": {
            "network_access": False,
            "order_creation": False,
            "order_submission": False,
            "order_execution": False,
            "production_db_write": False,
        },

        "execution": {
            "executed": False,
            "orders_created": 0,
            "orders_submitted": 0,
        },

        "final_verdict": final_verdict,
        "next_stage": next_stage,

        "forensic_basis": {
            "runtime_contract_source": "RUNTIME_CONTRACT_FORENSICS_v0.1",
            "runtime_root_paths": [
                "$.safety",
                "$.upstream_gate",
                "$.identity",
                "$.artifact",
                "$.runtime",
                "$.execution",
                "$.final_verdict",
                "$.next_stage",
            ],
            "automatic_runtime_repair": False,
            "automatic_contract_selection": False,
        },
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ========================================================================
    # TERMINAL OUTPUT
    # ========================================================================

    print("=" * 80)
    print("ARUNDA TRADER")
    print("LIVE SIGNAL EXECUTION ORDER-INTENT VALIDATION v0.3")
    print("=" * 80)

    print("PROJECT ROOT            :", PROJECT_ROOT)
    print("UPSTREAM RUNTIME        :", RUNTIME_PATH)
    print("UPSTREAM ARTIFACT       :", ARTIFACT_PATH)
    print("OUTPUT REPORT           :", OUTPUT_PATH)

    print("=" * 80)
    print("SAFETY")
    print("=" * 80)

    for key, value in SAFETY.items():
        print(f"{key:<25}: {value}")

    print("=" * 80)
    print("RUNTIME CONTRACT")
    print("=" * 80)

    print("contract                :", runtime_contract)
    print("runtime_ready           :", report["runtime_contract"]["runtime_ready"])
    print(
        "operational_safety      :",
        report["runtime_contract"]["operational_safety"]
    )
    print(
        "upstream_verified       :",
        report["runtime_contract"]["upstream_verified"]
    )
    print(
        "artifact_verified       :",
        report["runtime_contract"]["artifact_verified"]
    )
    print(
        "verdict_verified        :",
        report["runtime_contract"]["verdict_verified"]
    )
    print("verdict                 :", report["runtime_contract"]["verdict"])
    print("reason                  :", runtime_reason)

    print("=" * 80)
    print("ARTIFACT CONTRACT")
    print("=" * 80)

    print("contract                :", artifact_contract)
    print("verified                :", artifact_contract)
    print("rows                    :", artifact_data.get("rows", 0))
    print("eligible_rows           :", artifact_data.get("eligible_rows", 0))
    print("no_trade_rows           :", artifact_data.get("no_trade_rows", 0))
    print("decision                :", artifact_data.get("decision"))
    print("assets                  :", artifact_data.get("assets", []))
    print("directions              :", artifact_data.get("directions", []))
    print("snapshot_id             :", artifact_data.get("snapshot_id"))

    print("=" * 80)
    print("ORDER-INTENT VALIDATION")
    print("=" * 80)

    print("VALIDATION STATUS       :", validation_status)
    print(
        "ELIGIBLE SIGNALS        :",
        artifact_data.get("eligible_rows", 0)
    )
    print("ORDER INTENTS           :", len(order_intents))
    print("VALIDATED INTENTS       :", len(validated_intents))
    print("INVALID INTENTS         :", len(invalid_intents))

    print("=" * 80)
    print("ORDER-INTENT SAFETY")
    print("=" * 80)

    print("Network access          : False")
    print("Order creation          : False")
    print("Order submission        : False")
    print("Order execution         : False")
    print("Production DB write     : False")

    print("=" * 80)
    print("ORDER-INTENT DETAILS")
    print("=" * 80)

    if not runtime_contract:
        print("Order-intent validation blocked by runtime contract.")
        print("Reason:", runtime_reason)

    elif not artifact_contract:
        print("Order-intent validation blocked by artifact contract.")
        print("Reason:", artifact_reason)

    elif len(order_intents) == 0:
        print("No eligible signal exists in the current artifact.")
        print("No order intent was generated.")

    else:
        for intent in validated_intents:
            print(
                f"VALID INTENT | "
                f"{intent['asset']} | "
                f"{intent['direction']} | "
                f"{intent['entry_price']}"
            )

        for item in invalid_intents:
            print(
                f"INVALID INTENT | "
                f"{item['intent']['asset']} | "
                f"{item['errors']}"
            )

    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    print(
        "ORDER-INTENT VALIDATION :",
        final_verdict
    )
    print("EXECUTION               : NOT_EXECUTED")
    print("ORDERS CREATED          : 0")
    print("ORDERS SUBMITTED        : 0")
    print("NEXT STAGE              :", next_stage)

    print("=" * 80)
    print("OUTPUT :", OUTPUT_PATH)
    print("=" * 80)

    print("REPORT WRITTEN :", OUTPUT_PATH)


if __name__ == "__main__":
    main()