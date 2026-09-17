from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

ARTIFACT_REPORT = (
    PROJECT_ROOT / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
)

GENERATION_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_GENERATION_REPORT.json"
)

VALIDATION_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_VALIDATION_REPORT.json"
)

EXECUTION_GATE_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_EXECUTION_GATE_REPORT.json"
)

REPLAY_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_VERIFICATION_REPORT.json"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_CONTRACT_REPAIR_REPORT.json"
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise TypeError(f"JSON root must be dict: {path}")

    return data


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def get_dict(
    report: dict[str, Any],
    key: str,
) -> dict[str, Any] | None:
    value = report.get(key)

    if isinstance(value, dict):
        return value

    return None


def validate_artifact(
    artifact: dict[str, Any],
) -> dict[str, Any]:
    """
    Supports both known artifact layouts.

    Layout A:
        artifact_contract: {...}

    Layout B:
        artifact_contract may be absent while the same
        information exists at the root level.

    No data is modified.
    """

    contract = get_dict(
        artifact,
        "artifact_contract",
    )

    if contract is None:
        contract = artifact

    rows = contract.get(
        "rows",
        artifact.get("rows", 0),
    )

    eligible_rows = contract.get(
        "eligible_rows",
        artifact.get("eligible_rows", 0),
    )

    no_trade_rows = contract.get(
        "no_trade_rows",
        artifact.get("no_trade_rows", 0),
    )

    decision = contract.get(
        "decision",
        artifact.get("decision"),
    )

    snapshot_id = contract.get(
        "snapshot_id",
        artifact.get("snapshot_id"),
    )

    valid_types = (
        isinstance(rows, int)
        and isinstance(eligible_rows, int)
        and isinstance(no_trade_rows, int)
        and (
            isinstance(decision, str)
            or decision is None
        )
        and (
            isinstance(snapshot_id, str)
            or snapshot_id is None
        )
    )

    arithmetic_valid = (
        valid_types
        and rows >= 0
        and eligible_rows >= 0
        and no_trade_rows >= 0
        and eligible_rows + no_trade_rows == rows
    )

    return {
        "contract": arithmetic_valid,
        "verified": arithmetic_valid,
        "reason": (
            "ARTIFACT_CONTRACT_VERIFIED"
            if arithmetic_valid
            else "ARTIFACT_CONTRACT_INVALID"
        ),
        "rows": rows,
        "eligible_rows": eligible_rows,
        "no_trade_rows": no_trade_rows,
        "decision": decision,
        "snapshot_id": snapshot_id,
    }


def validate_generation(
    generation: dict[str, Any],
) -> dict[str, Any]:

    section = get_dict(
        generation,
        "order_intent_generation",
    )

    if section is None:
        return {
            "contract": False,
            "verified": False,
            "reason": "GENERATION_CONTRACT_SECTION_MISSING",
            "status": None,
            "intents_count": 0,
        }

    intents = section.get("intents")

    if intents is None:
        intents = []

    if not isinstance(intents, list):
        return {
            "contract": False,
            "verified": False,
            "reason": "GENERATION_INTENTS_NOT_LIST",
            "status": section.get("status"),
            "intents_count": 0,
        }

    status = section.get("status")

    return {
        "contract": True,
        "verified": True,
        "reason": "GENERATION_CONTRACT_VERIFIED",
        "status": status,
        "intents_count": len(intents),
    }


def validate_validation(
    validation: dict[str, Any],
) -> dict[str, Any]:

    section = get_dict(
        validation,
        "order_intent_generation",
    )

    if section is None:
        return {
            "contract": False,
            "verified": False,
            "reason": "VALIDATION_GENERATION_SECTION_MISSING",
        }

    return {
        "contract": True,
        "verified": True,
        "reason": "VALIDATION_CONTRACT_VERIFIED",
    }


def validate_execution_gate(
    gate: dict[str, Any],
) -> dict[str, Any]:

    runtime = get_dict(
        gate,
        "runtime_contract",
    )

    artifact = get_dict(
        gate,
        "artifact_contract",
    )

    safety = get_dict(
        gate,
        "safety",
    )

    if runtime is None:
        return {
            "contract": False,
            "verified": False,
            "reason": "EXECUTION_GATE_RUNTIME_CONTRACT_MISSING",
        }

    if artifact is None:
        return {
            "contract": False,
            "verified": False,
            "reason": "EXECUTION_GATE_ARTIFACT_CONTRACT_MISSING",
        }

    if safety is None:
        return {
            "contract": False,
            "verified": False,
            "reason": "EXECUTION_GATE_SAFETY_CONTRACT_MISSING",
        }

    runtime_valid = (
        runtime.get("contract") is True
        and runtime.get("runtime_ready") is True
    )

    artifact_valid = (
        artifact.get("contract") is True
        and artifact.get("verified") is True
    )

    safety_valid = (
        safety.get("network_access") is False
        and safety.get("order_execution") is False
        and safety.get("order_creation") is False
        and safety.get("order_submission") is False
        and safety.get("production_db_write") is False
    )

    valid = (
        runtime_valid
        and artifact_valid
        and safety_valid
    )

    return {
        "contract": valid,
        "verified": valid,
        "reason": (
            "EXECUTION_GATE_CONTRACT_VERIFIED"
            if valid
            else "EXECUTION_GATE_CONTRACT_INVALID"
        ),
    }


def build_repaired_replay_contract(
    artifact_contract: dict[str, Any],
    generation_contract: dict[str, Any],
    validation_contract: dict[str, Any],
    gate_contract: dict[str, Any],
) -> dict[str, Any]:

    eligible_rows = artifact_contract.get(
        "eligible_rows",
        0,
    )

    intents_count = generation_contract.get(
        "intents_count",
        0,
    )

    upstream_valid = (
        artifact_contract.get("contract") is True
        and artifact_contract.get("verified") is True
        and generation_contract.get("contract") is True
        and generation_contract.get("verified") is True
        and validation_contract.get("contract") is True
        and validation_contract.get("verified") is True
        and gate_contract.get("contract") is True
        and gate_contract.get("verified") is True
    )

    if not upstream_valid:
        return {
            "contract": False,
            "verified": False,
            "reason": "UPSTREAM_CONTRACT_NOT_VERIFIED",
            "status": "BLOCKED_UPSTREAM_CONTRACT",
            "eligible_signals": eligible_rows,
            "order_intents": intents_count,
            "path_verified": False,
            "replay": False,
            "replay_executed": False,
            "signal_created": False,
            "signal_inferred": False,
            "signal_reconstructed": False,
            "signal_injected": False,
        }

    if (
        eligible_rows == 0
        and intents_count == 0
    ):
        return {
            "contract": True,
            "verified": True,
            "reason": (
                "REPLAY_CONTRACT_REPAIRED_NO_ELIGIBLE_SIGNAL"
            ),
            "status": "NO_ELIGIBLE_SIGNAL",
            "eligible_signals": 0,
            "order_intents": 0,
            "path_verified": False,
            "replay": False,
            "replay_executed": False,
            "signal_created": False,
            "signal_inferred": False,
            "signal_reconstructed": False,
            "signal_injected": False,
            "no_op": True,
        }

    return {
        "contract": False,
        "verified": False,
        "reason": (
            "ELIGIBLE_SIGNAL_REQUIRES_REAL_REPLAY_PATH"
        ),
        "status": "REPLAY_PATH_REQUIRED",
        "eligible_signals": eligible_rows,
        "order_intents": intents_count,
        "path_verified": False,
        "replay": False,
        "replay_executed": False,
        "signal_created": False,
        "signal_inferred": False,
        "signal_reconstructed": False,
        "signal_injected": False,
        "no_op": False,
    }


def build_report(
    artifact: dict[str, Any],
    generation: dict[str, Any],
    validation: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:

    artifact_contract = validate_artifact(
        artifact
    )

    generation_contract = validate_generation(
        generation
    )

    validation_contract = validate_validation(
        validation
    )

    gate_contract = validate_execution_gate(
        gate
    )

    replay_contract = build_repaired_replay_contract(
        artifact_contract,
        generation_contract,
        validation_contract,
        gate_contract,
    )

    repaired = (
        replay_contract["contract"]
        and replay_contract["verified"]
    )

    return {
        "project": "ARUNDA TRADER",

        "component": (
            "LIVE SIGNAL ELIGIBLE SIGNAL "
            "REPLAY CONTRACT REPAIR"
        ),

        "version": "v0.2",

        "mode": "READ_ONLY",

        "safety": {
            "producer_execution": False,
            "producer_import": False,
            "production_db_write": False,
            "network_access": False,
            "order_execution": False,
            "order_creation": False,
            "order_submission": False,
            "artifact_mutation": False,
            "signal_injection": False,
            "synthetic_signal": False,
            "replay_execution": False,
            "operational_safety": True,
        },

        "sources": {
            "artifact": str(ARTIFACT_REPORT),
            "generation": str(GENERATION_REPORT),
            "validation": str(VALIDATION_REPORT),
            "execution_gate": str(EXECUTION_GATE_REPORT),
            "previous_replay": str(REPLAY_REPORT),
        },

        "source_sha256": {
            "artifact": sha256_file(
                ARTIFACT_REPORT
            ),
            "generation": sha256_file(
                GENERATION_REPORT
            ),
            "validation": sha256_file(
                VALIDATION_REPORT
            ),
            "execution_gate": sha256_file(
                EXECUTION_GATE_REPORT
            ),
            "previous_replay": sha256_file(
                REPLAY_REPORT
            ),
        },

        "artifact_contract": artifact_contract,

        "generation_contract": generation_contract,

        "validation_contract": validation_contract,

        "execution_gate_contract": gate_contract,

        "replay_contract": replay_contract,

        "repair": {
            "performed": True,
            "automatic_signal_creation": False,
            "automatic_signal_inference": False,
            "automatic_signal_reconstruction": False,
            "automatic_signal_injection": False,
            "synthetic_signal_created": False,
            "production_mutation": False,
            "database_mutation": False,
        },

        "replay_safety": {
            "replay_allowed": False,
            "execution_allowed": False,
            "order_creation": False,
            "order_submission": False,
            "network_access": False,
            "production_db_write": False,
            "signal_creation": False,
            "signal_inference": False,
            "signal_reconstruction": False,
            "signal_injection": False,
        },

        "final_verdict": (
            "LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_CONTRACT_REPAIRED"
            if repaired
            else
            "LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_CONTRACT_REPAIR_BLOCKED"
        ),

        "next_stage": (
            "WAIT_FOR_ELIGIBLE_SIGNAL"
            if (
                repaired
                and replay_contract["eligible_signals"] == 0
            )
            else
            "LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_VERIFICATION"
        ),
    }


def print_report(
    report: dict[str, Any],
) -> None:

    artifact = report["artifact_contract"]
    generation = report["generation_contract"]
    validation = report["validation_contract"]
    gate = report["execution_gate_contract"]
    replay = report["replay_contract"]

    print("=" * 100)
    print("ARUNDA TRADER")
    print(
        "LIVE SIGNAL ELIGIBLE SIGNAL "
        "REPLAY CONTRACT REPAIR v0.2"
    )
    print("=" * 100)

    print(
        "PROJECT ROOT :",
        PROJECT_ROOT,
    )

    print(
        "MODE         : READ_ONLY"
    )

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)

    print(
        "Producer execution :",
        report["safety"]["producer_execution"],
    )

    print(
        "Producer import    :",
        report["safety"]["producer_import"],
    )

    print(
        "Database write     :",
        report["safety"]["production_db_write"],
    )

    print(
        "Network access     :",
        report["safety"]["network_access"],
    )

    print(
        "Order execution    :",
        report["safety"]["order_execution"],
    )

    print(
        "Signal injection   :",
        report["safety"]["signal_injection"],
    )

    print(
        "Synthetic signal   :",
        report["safety"]["synthetic_signal"],
    )

    print(
        "Replay execution   :",
        report["safety"]["replay_execution"],
    )

    print("=" * 100)
    print("UPSTREAM CONTRACTS")
    print("=" * 100)

    print(
        "Artifact contract   :",
        artifact["contract"],
    )

    print(
        "Generation contract :",
        generation["contract"],
    )

    print(
        "Validation contract :",
        validation["contract"],
    )

    print(
        "Execution gate      :",
        gate["contract"],
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
    print("REPLAY CONTRACT REPAIR")
    print("=" * 100)

    print(
        "STATUS              :",
        replay["status"],
    )

    print(
        "CONTRACT            :",
        replay["contract"],
    )

    print(
        "VERIFIED            :",
        replay["verified"],
    )

    print(
        "ELIGIBLE SIGNALS    :",
        replay["eligible_signals"],
    )

    print(
        "ORDER INTENTS       :",
        replay["order_intents"],
    )

    print(
        "PATH VERIFIED       :",
        replay["path_verified"],
    )

    print(
        "REPLAY              :",
        replay["replay"],
    )

    print("=" * 100)
    print("REPAIR SAFETY")
    print("=" * 100)

    print(
        "Signal created      :",
        replay["signal_created"],
    )

    print(
        "Signal inferred     :",
        replay["signal_inferred"],
    )

    print(
        "Signal reconstructed:",
        replay["signal_reconstructed"],
    )

    print(
        "Signal injected     :",
        replay["signal_injected"],
    )

    print(
        "Production mutation:",
        report["repair"]["production_mutation"],
    )

    print(
        "Database mutation  :",
        report["repair"]["database_mutation"],
    )

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)

    print(
        "VERDICT    :",
        report["final_verdict"],
    )

    print(
        "NEXT STAGE :",
        report["next_stage"],
    )

    print("=" * 100)

    print(
        "REPORT WRITTEN :",
        OUTPUT_REPORT,
    )

    print("=" * 100)


def main() -> int:

    artifact = load_json(
        ARTIFACT_REPORT
    )

    generation = load_json(
        GENERATION_REPORT
    )

    validation = load_json(
        VALIDATION_REPORT
    )

    gate = load_json(
        EXECUTION_GATE_REPORT
    )

    report = build_report(
        artifact,
        generation,
        validation,
        gate,
    )

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

    print_report(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())