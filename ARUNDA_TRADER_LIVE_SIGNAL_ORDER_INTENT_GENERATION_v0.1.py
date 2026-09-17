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

VALIDATION_PATH = PROJECT_ROOT / (
    "ARUNDA_TRADER_LIVE_SIGNAL_EXECUTION_ORDER_INTENT_VALIDATION_REPORT.json"
)

OUTPUT_PATH = PROJECT_ROOT / (
    "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_GENERATION_REPORT.json"
)


# ============================================================================
# SAFETY
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


# ============================================================================
# IO
# ============================================================================

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


# ============================================================================
# RUNTIME CONTRACT
# ============================================================================

def verify_runtime_contract(runtime):
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

    gate = runtime["upstream_gate"]
    runtime_state = runtime["runtime"]
    execution = runtime["execution"]

    if not isinstance(gate, dict):
        return False, "UPSTREAM_GATE_NOT_DICT"

    if not isinstance(runtime_state, dict):
        return False, "RUNTIME_SECTION_NOT_DICT"

    if not isinstance(execution, dict):
        return False, "EXECUTION_SECTION_NOT_DICT"

    required_gate = [
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

    for key in required_gate:
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

    if runtime_state.get("upstream_verified") is not True:
        return False, "RUNTIME_UPSTREAM_NOT_VERIFIED"

    if runtime_state.get("artifact_verified") is not True:
        return False, "RUNTIME_ARTIFACT_NOT_VERIFIED"

    if runtime_state.get("operational_safety") is not True:
        return False, "RUNTIME_OPERATIONAL_SAFETY_FAILED"

    if runtime_state.get("runtime_ready") is not True:
        return False, "RUNTIME_NOT_READY"

    if runtime_state.get("execution_allowed") is not False:
        return False, "EXECUTION_ALLOWED_NOT_FALSE"

    if runtime_state.get("execution") != "NOT_EXECUTED":
        return False, "RUNTIME_EXECUTION_STATE_INVALID"

    if runtime_state.get("orders_created") != 0:
        return False, "RUNTIME_ORDERS_CREATED_NOT_ZERO"

    if runtime_state.get("orders_submitted") != 0:
        return False, "RUNTIME_ORDERS_SUBMITTED_NOT_ZERO"

    if execution.get("executed") is not False:
        return False, "EXECUTION_FLAG_NOT_FALSE"

    if execution.get("orders_created") != 0:
        return False, "EXECUTION_ORDERS_CREATED_NOT_ZERO"

    if execution.get("orders_submitted") != 0:
        return False, "EXECUTION_ORDERS_SUBMITTED_NOT_ZERO"

    if runtime["final_verdict"] != "LIVE_SIGNAL_EXECUTION_RUNTIME_READY":
        return False, "RUNTIME_FINAL_VERDICT_INVALID"

    return True, "RUNTIME_CONTRACT_VERIFIED"


# ============================================================================
# ARTIFACT CONTRACT
# ============================================================================

def verify_artifact_contract(artifact):
    if not isinstance(artifact, dict):
        return False, "ARTIFACT_ROOT_NOT_DICT"

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
            return False, f"ARTIFACT_KEY_MISSING:{key}"

    rows = artifact["rows"]
    eligible_rows = artifact["eligible_rows"]
    no_trade_rows = artifact["no_trade_rows"]
    row_results = artifact["row_results"]

    if not isinstance(rows, int):
        return False, "ROWS_INVALID"

    if not isinstance(eligible_rows, int):
        return False, "ELIGIBLE_ROWS_INVALID"

    if not isinstance(no_trade_rows, int):
        return False, "NO_TRADE_ROWS_INVALID"

    if not isinstance(row_results, list):
        return False, "ROW_RESULTS_NOT_LIST"

    if len(row_results) != rows:
        return False, "ROW_RESULTS_COUNT_MISMATCH"

    if rows != eligible_rows + no_trade_rows:
        return False, "ROW_COUNT_CONTRACT_FAILED"

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
            return False, "ROW_NOT_DICT"

        for key in required_row_keys:
            if key not in row:
                return False, f"ROW_KEY_MISSING:{key}"

    actual_eligible = sum(
        1
        for row in row_results
        if row["eligible"] is True
    )

    actual_no_trade = sum(
        1
        for row in row_results
        if row["eligible"] is False
    )

    if actual_eligible != eligible_rows:
        return False, "ELIGIBLE_ROWS_MISMATCH"

    if actual_no_trade != no_trade_rows:
        return False, "NO_TRADE_ROWS_MISMATCH"

    if eligible_rows == 0 and artifact["decision"] != "NO_TRADE":
        return False, "DECISION_MISMATCH"

    if eligible_rows > 0 and artifact["decision"] != "TRADE":
        return False, "DECISION_MISMATCH"

    if not artifact["snapshot_id"]:
        return False, "SNAPSHOT_ID_MISSING"

    return True, "ARTIFACT_CONTRACT_VERIFIED"


# ============================================================================
# ORDER INTENT GENERATION
# ============================================================================

def generate_order_intent(row, snapshot_id):
    """
    Pure in-memory representation.

    This function:
        DOES NOT connect to exchange.
        DOES NOT create an exchange order.
        DOES NOT submit an order.
        DOES NOT write to production DB.
    """

    direction = str(row["direction"]).upper()

    intent = {
        "intent_id": (
            f"OI-{snapshot_id}-{row['asset']}-{row['id']}"
        ),

        "asset": row["asset"],
        "direction": direction,

        "timestamp": row["timestamp"],
        "snapshot_id": snapshot_id,
        "source_row_id": row["id"],

        "entry_price": row["entry_price"],

        "signal": {
            "confidence": row["confidence"],
            "regime": row["regime"],
            "signal_strength": row["signal_strength"],
            "data_quality": row["data_quality"],
        },

        "availability": {
            "available_weight": row["available_weight"],
            "missing_arm_penalty": row["missing_arm_penalty"],
            "market_available": row["market_available"],
            "positioning_available": row["positioning_available"],
            "news_available": row["news_available"],
        },

        "execution": {
            "mode": "DRY_RUN",
            "network_access": False,
            "order_creation": False,
            "order_submission": False,
            "order_execution": False,
        },

        "status": "GENERATED",
    }

    return intent


# ============================================================================
# INTENT VALIDATION
# ============================================================================

def validate_intent(intent):
    errors = []

    if not intent.get("intent_id"):
        errors.append("INTENT_ID_MISSING")

    if not intent.get("asset"):
        errors.append("ASSET_MISSING")

    if intent.get("direction") not in {"LONG", "SHORT"}:
        errors.append("INVALID_EXECUTION_DIRECTION")

    entry_price = intent.get("entry_price")

    if not isinstance(entry_price, (int, float)):
        errors.append("ENTRY_PRICE_INVALID")
    elif entry_price <= 0:
        errors.append("ENTRY_PRICE_NON_POSITIVE")

    if intent.get("execution", {}).get("mode") != "DRY_RUN":
        errors.append("INVALID_EXECUTION_MODE")

    execution = intent.get("execution", {})

    if execution.get("network_access") is not False:
        errors.append("NETWORK_ACCESS_VIOLATION")

    if execution.get("order_creation") is not False:
        errors.append("ORDER_CREATION_VIOLATION")

    if execution.get("order_submission") is not False:
        errors.append("ORDER_SUBMISSION_VIOLATION")

    if execution.get("order_execution") is not False:
        errors.append("ORDER_EXECUTION_VIOLATION")

    return len(errors) == 0, errors


# ============================================================================
# MAIN
# ============================================================================

def main():

    timestamp = datetime.now(timezone.utc).isoformat()

    runtime = None
    artifact = None

    runtime_contract = False
    runtime_reason = "RUNTIME_NOT_LOADED"

    artifact_contract = False
    artifact_reason = "ARTIFACT_NOT_LOADED"

    if not RUNTIME_PATH.exists():
        runtime_reason = "RUNTIME_FILE_MISSING"
    else:
        try:
            runtime = load_json(RUNTIME_PATH)
            runtime_contract, runtime_reason = verify_runtime_contract(runtime)
        except Exception as exc:
            runtime_reason = (
                f"RUNTIME_LOAD_ERROR:{type(exc).__name__}"
            )

    if not ARTIFACT_PATH.exists():
        artifact_reason = "ARTIFACT_FILE_MISSING"
    else:
        try:
            artifact = load_json(ARTIFACT_PATH)
            artifact_contract, artifact_reason = (
                verify_artifact_contract(artifact)
            )
        except Exception as exc:
            artifact_reason = (
                f"ARTIFACT_LOAD_ERROR:{type(exc).__name__}"
            )

    eligible_rows = []

    if artifact_contract:
        eligible_rows = [
            row
            for row in artifact["row_results"]
            if row.get("eligible") is True
        ]

    generated_intents = []
    validated_intents = []
    invalid_intents = []

    generation_allowed = (
        runtime_contract
        and artifact_contract
    )

    if generation_allowed:

        for row in eligible_rows:

            intent = generate_order_intent(
                row,
                artifact["snapshot_id"],
            )

            generated_intents.append(intent)

            valid, errors = validate_intent(intent)

            if valid:
                intent["status"] = "VALIDATED"
                validated_intents.append(intent)

            else:
                intent["status"] = "INVALID"
                invalid_intents.append(
                    {
                        "intent": intent,
                        "errors": errors,
                    }
                )

    # ========================================================================
    # FINAL STATE
    # ========================================================================

    if not runtime_contract:
        generation_status = "BLOCKED_RUNTIME_CONTRACT"
        final_verdict = "LIVE_SIGNAL_ORDER_INTENT_GENERATION_BLOCKED"
        next_stage = "RUNTIME_CONTRACT_REPAIR"

    elif not artifact_contract:
        generation_status = "BLOCKED_ARTIFACT_CONTRACT"
        final_verdict = "LIVE_SIGNAL_ORDER_INTENT_GENERATION_BLOCKED"
        next_stage = "ARTIFACT_CONTRACT_REPAIR"

    elif len(eligible_rows) == 0:
        generation_status = "READY_NO_ELIGIBLE_SIGNALS"
        final_verdict = "LIVE_SIGNAL_ORDER_INTENT_GENERATION_READY"
        next_stage = "WAIT_FOR_ELIGIBLE_SIGNAL"

    elif len(invalid_intents) > 0:
        generation_status = "GENERATION_VALIDATION_FAILED"
        final_verdict = "LIVE_SIGNAL_ORDER_INTENT_GENERATION_FAILED"
        next_stage = "ORDER_INTENT_VALIDATION_REVIEW"

    else:
        generation_status = "READY_INTENTS_GENERATED"
        final_verdict = "LIVE_SIGNAL_ORDER_INTENT_GENERATION_READY"
        next_stage = "ORDER_INTENT_VALIDATION"

    # ========================================================================
    # REPORT
    # ========================================================================

    report = {
        "project": "ARUNDA TRADER",

        "component": (
            "LIVE SIGNAL ORDER-INTENT GENERATION"
        ),

        "version": "v0.1",

        "timestamp_utc": timestamp,

        "safety": {
            **SAFETY,
            "operational_safety": True,
        },

        "sources": {
            "runtime": str(RUNTIME_PATH),
            "artifact": str(ARTIFACT_PATH),
            "validation": str(VALIDATION_PATH),
        },

        "runtime_contract": {
            "contract": runtime_contract,
            "reason": runtime_reason,
            "runtime_ready": (
                runtime.get("runtime", {}).get("runtime_ready", False)
                if isinstance(runtime, dict)
                else False
            ),
            "upstream_verified": (
                runtime.get("runtime", {}).get(
                    "upstream_verified",
                    False,
                )
                if isinstance(runtime, dict)
                else False
            ),
            "artifact_verified": (
                runtime.get("runtime", {}).get(
                    "artifact_verified",
                    False,
                )
                if isinstance(runtime, dict)
                else False
            ),
            "operational_safety": (
                runtime.get("runtime", {}).get(
                    "operational_safety",
                    False,
                )
                if isinstance(runtime, dict)
                else False
            ),
            "verdict": (
                runtime.get("final_verdict")
                if isinstance(runtime, dict)
                else None
            ),
        },

        "artifact_contract": {
            "contract": artifact_contract,
            "reason": artifact_reason,
            "rows": (
                artifact.get("rows", 0)
                if isinstance(artifact, dict)
                else 0
            ),
            "eligible_rows": (
                artifact.get("eligible_rows", 0)
                if isinstance(artifact, dict)
                else 0
            ),
            "no_trade_rows": (
                artifact.get("no_trade_rows", 0)
                if isinstance(artifact, dict)
                else 0
            ),
            "decision": (
                artifact.get("decision")
                if isinstance(artifact, dict)
                else None
            ),
            "snapshot_id": (
                artifact.get("snapshot_id")
                if isinstance(artifact, dict)
                else None
            ),
        },

        "order_intent_generation": {
            "status": generation_status,
            "eligible_signals": len(eligible_rows),
            "order_intents_generated": len(generated_intents),
            "validated_intents": len(validated_intents),
            "invalid_intents": len(invalid_intents),

            "intents": generated_intents,

            "invalid_details": invalid_intents,
        },

        "execution_safety": {
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
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ========================================================================
    # TERMINAL
    # ========================================================================

    print("=" * 80)
    print("ARUNDA TRADER")
    print("LIVE SIGNAL ORDER-INTENT GENERATION v0.1")
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
    print("upstream_verified       :", report["runtime_contract"]["upstream_verified"])
    print("artifact_verified       :", report["runtime_contract"]["artifact_verified"])
    print("operational_safety      :", report["runtime_contract"]["operational_safety"])
    print("verdict                 :", report["runtime_contract"]["verdict"])
    print("reason                  :", runtime_reason)

    print("=" * 80)
    print("ARTIFACT CONTRACT")
    print("=" * 80)

    print("contract                :", artifact_contract)
    print("verified                :", artifact_contract)
    print("rows                    :", report["artifact_contract"]["rows"])
    print("eligible_rows           :", report["artifact_contract"]["eligible_rows"])
    print("no_trade_rows           :", report["artifact_contract"]["no_trade_rows"])
    print("decision                :", report["artifact_contract"]["decision"])
    print("snapshot_id             :", report["artifact_contract"]["snapshot_id"])

    print("=" * 80)
    print("ORDER-INTENT GENERATION")
    print("=" * 80)

    print("GENERATION STATUS       :", generation_status)
    print("ELIGIBLE SIGNALS        :", len(eligible_rows))
    print("ORDER INTENTS GENERATED :", len(generated_intents))
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
        print("Generation blocked by runtime contract.")
        print("Reason:", runtime_reason)

    elif not artifact_contract:
        print("Generation blocked by artifact contract.")
        print("Reason:", artifact_reason)

    elif len(generated_intents) == 0:
        print("No eligible signal exists in the current artifact.")
        print("No order intent was generated.")

    else:
        for intent in validated_intents:
            print(
                "VALID INTENT | "
                f"{intent['intent_id']} | "
                f"{intent['asset']} | "
                f"{intent['direction']} | "
                f"{intent['entry_price']}"
            )

        for item in invalid_intents:
            print(
                "INVALID INTENT | "
                f"{item['intent'].get('intent_id')} | "
                f"{item['errors']}"
            )

    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    print(
        "ORDER-INTENT GENERATION :",
        final_verdict,
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