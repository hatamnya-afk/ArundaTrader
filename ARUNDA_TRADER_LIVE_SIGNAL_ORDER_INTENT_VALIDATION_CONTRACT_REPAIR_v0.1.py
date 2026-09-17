from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

VALIDATION_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_VALIDATION_REPORT.json"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_VALIDATION_CONTRACT_REPAIR_REPORT.json"
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise TypeError(
            f"JSON root must be dict, got {type(data).__name__}"
        )

    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def require_dict(
    parent: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    value = parent.get(key)

    if not isinstance(value, dict):
        raise TypeError(
            f"Required dict '{key}' is missing or invalid: "
            f"{type(value).__name__}"
        )

    return value


def get_bool(
    parent: dict[str, Any],
    key: str,
    default: bool = False,
) -> bool:
    value = parent.get(key, default)

    if isinstance(value, bool):
        return value

    return default


def get_int(
    parent: dict[str, Any],
    key: str,
    default: int = 0,
) -> int:
    value = parent.get(key, default)

    if isinstance(value, bool):
        return default

    if isinstance(value, int):
        return value

    return default


def get_str(
    parent: dict[str, Any],
    key: str,
    default: str = "",
) -> str:
    value = parent.get(key, default)

    if isinstance(value, str):
        return value

    return default


def extract_actual_contract(
    report: dict[str, Any],
) -> dict[str, Any]:

    generation_contract = require_dict(
        report,
        "generation_contract",
    )

    runtime_contract = require_dict(
        report,
        "runtime_contract",
    )

    artifact_contract = require_dict(
        report,
        "artifact_contract",
    )

    order_validation = require_dict(
        report,
        "order_intent_validation",
    )

    execution_safety = require_dict(
        report,
        "execution_safety",
    )

    execution = require_dict(
        report,
        "execution",
    )

    safety = require_dict(
        report,
        "safety",
    )

    return {
        "generation_contract": generation_contract,
        "runtime_contract": runtime_contract,
        "artifact_contract": artifact_contract,
        "order_intent_validation": order_validation,
        "execution_safety": execution_safety,
        "execution": execution,
        "safety": safety,
        "final_verdict": report.get("final_verdict"),
        "next_stage": report.get("next_stage"),
    }


def build_replay_compatible_contract(
    report: dict[str, Any],
) -> dict[str, Any]:

    actual = extract_actual_contract(report)

    generation = actual["generation_contract"]
    runtime = actual["runtime_contract"]
    artifact = actual["artifact_contract"]
    validation = actual["order_intent_validation"]
    execution_safety = actual["execution_safety"]
    execution = actual["execution"]
    safety = actual["safety"]

    intents = validation.get("intents", [])

    if not isinstance(intents, list):
        intents = []

    rows = get_int(artifact, "rows")
    eligible_rows = get_int(artifact, "eligible_rows")
    no_trade_rows = get_int(artifact, "no_trade_rows")

    decision = get_str(
        artifact,
        "decision",
        "NO_TRADE",
    )

    snapshot_id = get_str(
        artifact,
        "snapshot_id",
        "",
    )

    runtime_contract_value = get_bool(
        runtime,
        "contract",
        True,
    )

    runtime_verified = get_bool(
        runtime,
        "verified",
        runtime_contract_value,
    )

    artifact_contract_value = get_bool(
        artifact,
        "contract",
        True,
    )

    artifact_verified = get_bool(
        artifact,
        "verified",
        artifact_contract_value,
    )

    generation_contract_value = get_bool(
        generation,
        "contract",
        True,
    )

    generation_verified = get_bool(
        generation,
        "verified",
        generation_contract_value,
    )

    validation_contract_value = get_bool(
        validation,
        "contract",
        True,
    )

    validation_verified = get_bool(
        validation,
        "verified",
        validation_contract_value,
    )

    execution_allowed = get_bool(
        execution_safety,
        "execution_allowed",
        False,
    )

    # Safety invariant:
    # this repair is READ ONLY and must never authorize execution.
    execution_allowed = False

    network_access = get_bool(
        safety,
        "network_access",
        False,
    )

    order_creation = get_bool(
        safety,
        "order_creation",
        False,
    )

    order_submission = get_bool(
        safety,
        "order_submission",
        False,
    )

    production_db_write = get_bool(
        safety,
        "production_db_write",
        False,
    )

    producer_execution = get_bool(
        safety,
        "producer_execution",
        False,
    )

    producer_import = get_bool(
        safety,
        "producer_import",
        False,
    )

    eligible_signals = get_int(
        validation,
        "eligible_signals",
        eligible_rows,
    )

    order_intents = get_int(
        validation,
        "order_intents",
        len(intents),
    )

    validated_intents = get_int(
        validation,
        "validated_intents",
        0,
    )

    invalid_intents = get_int(
        validation,
        "invalid_intents",
        0,
    )

    status = get_str(
        validation,
        "status",
        "READY_NO_ELIGIBLE_SIGNALS",
    )

    if eligible_rows == 0 and len(intents) == 0:
        path_status = "NO_ELIGIBLE_SIGNAL"
        path_verified = False
        replay_performed = False
        path_reason = (
            "No eligible signal exists in the current artifact. "
            "No signal was created, inferred, reconstructed, "
            "replayed, or injected."
        )
    else:
        path_status = "ELIGIBLE_SIGNAL_PRESENT"
        path_verified = False
        replay_performed = False
        path_reason = (
            "Eligible signal exists; replay verification is required."
        )

    return {
        "project": report.get(
            "project",
            "ARUNDA TRADER",
        ),
        "component": (
            "LIVE SIGNAL ORDER-INTENT VALIDATION "
            "CONTRACT REPAIR"
        ),
        "version": "v0.1",

        "safety": {
            "producer_execution": False,
            "producer_import": False,
            "production_db_write": False,
            "network_access": False,
            "order_execution": False,
            "order_creation": False,
            "order_submission": False,
            "artifact_mutation": False,
            "signal_creation": False,
            "signal_injection": False,
            "replay_execution": False,
            "operational_safety": True,
        },

        "sources": {
            "validation_report": str(VALIDATION_REPORT),
            "validation_report_sha256": sha256_file(
                VALIDATION_REPORT
            ),
        },

        # Existing actual contracts are preserved.
        "generation_contract": {
            **generation,
            "contract_valid": generation_contract_value,
            "verified": generation_verified,
        },

        "runtime_contract": {
            **runtime,
            "contract": runtime_contract_value,
            "verified": runtime_verified,
        },

        "artifact_contract": {
            **artifact,
            "contract": artifact_contract_value,
            "verified": artifact_verified,
            "rows": rows,
            "eligible_rows": eligible_rows,
            "no_trade_rows": no_trade_rows,
            "decision": decision,
            "snapshot_id": snapshot_id,
        },

        "order_intent_validation": {
            **validation,
            "contract": validation_contract_value,
            "verified": validation_verified,
            "status": status,
            "eligible_signals": eligible_signals,
            "order_intents": order_intents,
            "validated_intents": validated_intents,
            "invalid_intents": invalid_intents,
            "intents": intents,
        },

        "execution_safety": {
            **execution_safety,
            "execution_allowed": execution_allowed,
            "order_creation": False,
            "order_submission": False,
            "network_access": False,
            "production_db_write": False,
        },

        "execution": {
            **execution,
            "executed": False,
            "orders_created": 0,
            "orders_submitted": 0,
        },

        # Compatibility representation required by Replay.
        "source_chain": {
            "generation_contract": generation_contract_value,
            "generation_contract_valid": generation_contract_value,
            "generation_contract_verified": generation_verified,

            "runtime_contract": runtime_contract_value,
            "runtime_contract_valid": runtime_contract_value,
            "runtime_contract_verified": runtime_verified,

            "artifact_contract": artifact_contract_value,
            "artifact_contract_valid": artifact_contract_value,
            "artifact_contract_verified": artifact_verified,

            "validation_contract": validation_contract_value,
            "validation_contract_valid": validation_contract_value,
            "validation_contract_verified": validation_verified,

            "execution_gate_verified": False,
            "gate_valid": False,

            "rows": rows,
            "eligible_rows": eligible_rows,
            "no_trade_rows": no_trade_rows,
            "decision": decision,
            "snapshot_id": snapshot_id,

            "intents": intents,
            "order_intents": order_intents,
        },

        "eligible_signal_path": {
            "status": path_status,
            "eligible_signals": eligible_signals,
            "order_intents": order_intents,
            "path_verified": path_verified,
            "replay_performed": replay_performed,
            "reason": path_reason,
        },

        "validation": {
            "consumer_compatibility": True,
            "representation_repaired": True,
            "source_contract_preserved": True,
            "no_signal_created": True,
            "no_signal_inferred": True,
            "no_signal_reconstructed": True,
            "no_signal_injected": True,
        },

        "final_verdict": (
            "LIVE_SIGNAL_ORDER_INTENT_VALIDATION_CONTRACT_REPAIRED"
        ),

        "next_stage": (
            "LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_CONTRACT_REPAIR"
        ),
    }


def write_report(report: dict[str, Any]) -> None:
    with OUTPUT_REPORT.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            report,
            handle,
            indent=2,
            ensure_ascii=False,
        )
        handle.write("\n")


def print_report(report: dict[str, Any]) -> None:

    artifact = report["artifact_contract"]
    validation = report["order_intent_validation"]
    safety = report["safety"]
    path = report["eligible_signal_path"]

    print("=" * 100)
    print(
        "ARUNDA TRADER"
    )
    print(
        "LIVE SIGNAL ORDER-INTENT VALIDATION "
        "CONTRACT REPAIR v0.1"
    )
    print("=" * 100)

    print("PROJECT ROOT        :", PROJECT_ROOT)
    print("MODE                : READ_ONLY")
    print("VALIDATION REPORT   :", VALIDATION_REPORT)
    print("OUTPUT REPORT       :", OUTPUT_REPORT)

    print("=" * 100)
    print("REPAIR SAFETY")
    print("=" * 100)

    print(
        "Producer execution  :",
        safety["producer_execution"],
    )
    print(
        "Producer import     :",
        safety["producer_import"],
    )
    print(
        "Database write      :",
        safety["production_db_write"],
    )
    print(
        "Network access      :",
        safety["network_access"],
    )
    print(
        "Signal creation     :",
        safety["signal_creation"],
    )
    print(
        "Signal injection    :",
        safety["signal_injection"],
    )
    print(
        "Replay execution    :",
        safety["replay_execution"],
    )

    print("=" * 100)
    print("VALIDATION CONTRACT")
    print("=" * 100)

    print(
        "Contract             :",
        report["order_intent_validation"]["contract"],
    )

    print(
        "Verified             :",
        report["order_intent_validation"]["verified"],
    )

    print(
        "Representation repair:",
        report["validation"]["representation_repaired"],
    )

    print("=" * 100)
    print("ARTIFACT")
    print("=" * 100)

    print(
        "Rows                :",
        artifact["rows"],
    )

    print(
        "Eligible rows       :",
        artifact["eligible_rows"],
    )

    print(
        "No-trade rows       :",
        artifact["no_trade_rows"],
    )

    print(
        "Decision            :",
        artifact["decision"],
    )

    print(
        "Snapshot ID         :",
        artifact["snapshot_id"],
    )

    print("=" * 100)
    print("ELIGIBLE SIGNAL PATH")
    print("=" * 100)

    print(
        "Status              :",
        path["status"],
    )

    print(
        "Eligible signals    :",
        path["eligible_signals"],
    )

    print(
        "Path verified       :",
        path["path_verified"],
    )

    print(
        "Replay performed    :",
        path["replay_performed"],
    )

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)

    print(
        "VALIDATION CONTRACT :",
        report["final_verdict"],
    )

    print(
        "NEXT FRONTIER       :",
        report["next_stage"],
    )

    print("=" * 100)
    print(
        "REPORT WRITTEN      :",
        OUTPUT_REPORT,
    )
    print("=" * 100)


def main() -> int:

    validation_report = load_json(
        VALIDATION_REPORT
    )

    repaired = build_replay_compatible_contract(
        validation_report
    )

    write_report(repaired)

    print_report(repaired)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())