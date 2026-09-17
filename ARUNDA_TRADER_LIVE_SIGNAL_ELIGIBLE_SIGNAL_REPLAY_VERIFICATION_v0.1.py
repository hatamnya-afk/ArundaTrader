from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

GENERATION_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_GENERATION_REPORT.json"
)

VALIDATION_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_VALIDATION_REPORT.json"
)

GATE_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_EXECUTION_GATE_REPORT.json"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_VERIFICATION_REPORT.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required report not found: {path}"
        )

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise TypeError(
            f"JSON root must be a dict: {path}"
        )

    return data


def get_dict(
    parent: dict[str, Any],
    key: str,
) -> dict[str, Any] | None:

    value = parent.get(key)

    if isinstance(value, dict):
        return value

    return None


def get_int(
    parent: dict[str, Any],
    key: str,
    default: int = 0,
) -> int:

    value = parent.get(key)

    if isinstance(value, int):
        return value

    return default


def get_bool(
    parent: dict[str, Any],
    key: str,
    default: bool = False,
) -> bool:

    value = parent.get(key)

    if isinstance(value, bool):
        return value

    return default


def extract_artifact_contract(
    generation: dict[str, Any],
) -> dict[str, Any]:

    artifact = get_dict(
        generation,
        "artifact_contract",
    )

    if artifact is None:
        raise ValueError(
            "GENERATION_ARTIFACT_CONTRACT_MISSING"
        )

    return artifact


def extract_generation_contract(
    generation: dict[str, Any],
) -> dict[str, Any]:

    order_generation = get_dict(
        generation,
        "order_intent_generation",
    )

    if order_generation is None:
        raise ValueError(
            "ORDER_INTENT_GENERATION_SECTION_MISSING"
        )

    return order_generation


def extract_runtime_contract(
    generation: dict[str, Any],
) -> dict[str, Any]:

    runtime = get_dict(
        generation,
        "runtime_contract",
    )

    if runtime is None:
        raise ValueError(
            "RUNTIME_CONTRACT_SECTION_MISSING"
        )

    return runtime


def validate_source_chain() -> dict[str, Any]:

    generation = load_json(
        GENERATION_REPORT
    )

    validation = load_json(
        VALIDATION_REPORT
    )

    gate = load_json(
        GATE_REPORT
    )

    artifact_contract = extract_artifact_contract(
        generation
    )

    generation_contract = extract_generation_contract(
        generation
    )

    runtime_contract = extract_runtime_contract(
        generation
    )

    generation_contract_valid = (
        generation_contract.get("contract_valid") is True
        or generation_contract.get("status")
        == "READY_NO_ELIGIBLE_SIGNALS"
    )

    runtime_contract_valid = (
        runtime_contract.get("contract") is True
    )

    artifact_contract_valid = (
        artifact_contract.get("contract") is True
        and artifact_contract.get("verified") is True
    )

    validation_final = get_dict(
        validation,
        "final_verdict",
    )

    validation_runtime = get_dict(
        validation,
        "runtime_contract",
    )

    validation_artifact = get_dict(
        validation,
        "artifact_contract",
    )

    gate_runtime = get_dict(
        gate,
        "runtime_contract",
    )

    gate_artifact = get_dict(
        gate,
        "artifact_contract",
    )

    gate_status = gate.get(
        "final_verdict"
    )

    validation_valid = (
        isinstance(validation_final, dict)
        and validation_final.get("contract") is True
    )

    gate_valid = (
        isinstance(gate_runtime, dict)
        and gate_runtime.get("contract") is True
        and isinstance(gate_artifact, dict)
        and gate_artifact.get("contract") is True
    )

    intents = generation_contract.get(
        "intents",
        [],
    )

    if not isinstance(intents, list):
        raise TypeError(
            "order_intent_generation.intents must be a list."
        )

    eligible_rows = get_int(
        artifact_contract,
        "eligible_rows",
        0,
    )

    no_trade_rows = get_int(
        artifact_contract,
        "no_trade_rows",
        0,
    )

    rows = get_int(
        artifact_contract,
        "rows",
        0,
    )

    decision = artifact_contract.get(
        "decision"
    )

    snapshot_id = artifact_contract.get(
        "snapshot_id"
    )

    return {
        "generation": generation,
        "validation": validation,
        "gate": gate,
        "artifact_contract": artifact_contract,
        "generation_contract": generation_contract,
        "runtime_contract": runtime_contract,
        "intents": intents,
        "rows": rows,
        "eligible_rows": eligible_rows,
        "no_trade_rows": no_trade_rows,
        "decision": decision,
        "snapshot_id": snapshot_id,
        "generation_contract_valid": generation_contract_valid,
        "runtime_contract_valid": runtime_contract_valid,
        "artifact_contract_valid": artifact_contract_valid,
        "validation_valid": validation_valid,
        "gate_valid": gate_valid,
        "gate_status": gate_status,
        "validation_runtime": validation_runtime,
        "validation_artifact": validation_artifact,
    }


def build_report(
    chain: dict[str, Any],
) -> dict[str, Any]:

    intents = chain["intents"]
    eligible_rows = chain["eligible_rows"]

    real_eligible_signal_exists = (
        eligible_rows > 0
    )

    if real_eligible_signal_exists:

        status = "ELIGIBLE_SIGNAL_PRESENT"

        path_verified = False

        replay_performed = False

        reason = (
            "A real eligible signal exists in the upstream "
            "artifact. Replay verification is required before "
            "any execution consumer."
        )

        next_stage = (
            "ELIGIBLE_SIGNAL_REPLAY_FIXTURE_VERIFICATION"
        )

    else:

        status = "NO_ELIGIBLE_SIGNAL"

        path_verified = False

        replay_performed = False

        reason = (
            "No eligible signal exists in the current artifact. "
            "No signal was created, inferred, reconstructed, "
            "replayed, or injected."
        )

        next_stage = "WAIT_FOR_ELIGIBLE_SIGNAL"

    return {
        "project": "ARUNDA TRADER",

        "component": (
            "LIVE SIGNAL ELIGIBLE SIGNAL "
            "REPLAY VERIFICATION"
        ),

        "version": "v0.2",

        "mode": "READ_ONLY",

        "safety": {
            "producer_execution": False,
            "producer_import": False,
            "production_db_write": False,
            "network_access": False,
            "exchange_access": False,
            "order_execution": False,
            "order_creation": False,
            "order_submission": False,
            "artifact_mutation": False,
            "signal_injection": False,
            "synthetic_signal": False,
            "signal_reconstruction": False,
            "replay_execution": False,
            "operational_safety": True,
        },

        "sources": {
            "generation_report": str(
                GENERATION_REPORT
            ),
            "generation_report_sha256": sha256_file(
                GENERATION_REPORT
            ),
            "validation_report": str(
                VALIDATION_REPORT
            ),
            "validation_report_sha256": sha256_file(
                VALIDATION_REPORT
            ),
            "gate_report": str(
                GATE_REPORT
            ),
            "gate_report_sha256": sha256_file(
                GATE_REPORT
            ),
        },

        "source_chain": {
            "generation_contract_verified": (
                chain["generation_contract_valid"]
            ),
            "runtime_contract_verified": (
                chain["runtime_contract_valid"]
            ),
            "artifact_contract_verified": (
                chain["artifact_contract_valid"]
            ),
            "validation_contract_verified": (
                chain["validation_valid"]
            ),
            "execution_gate_verified": (
                chain["gate_valid"]
            ),
        },

        "artifact_contract": {
            "contract": chain[
                "artifact_contract_valid"
            ],
            "verified": chain[
                "artifact_contract_valid"
            ],
            "rows": chain["rows"],
            "eligible_rows": chain[
                "eligible_rows"
            ],
            "no_trade_rows": chain[
                "no_trade_rows"
            ],
            "decision": chain["decision"],
            "snapshot_id": chain["snapshot_id"],
        },

        "generation_contract": {
            "contract": chain[
                "generation_contract_valid"
            ],
            "status": chain[
                "generation_contract"
            ].get("status"),
            "intents_count": len(intents),
        },

        "eligible_signal_path": {
            "status": status,
            "eligible_signals": eligible_rows,
            "order_intents": len(intents),
            "path_verified": path_verified,
            "replay_performed": replay_performed,
            "signal_created": False,
            "signal_injected": False,
            "signal_reconstructed": False,
            "reason": reason,
        },

        "execution_safety": {
            "execution_allowed": False,
            "order_creation": False,
            "order_submission": False,
            "order_execution": False,
            "network_access": False,
            "production_db_write": False,
        },

        "execution": {
            "executed": False,
            "orders_created": 0,
            "orders_submitted": 0,
        },

        "final_verdict": (
            "LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_VERIFICATION_READY"
        ),

        "next_stage": next_stage,
    }


def print_report(
    report: dict[str, Any],
) -> None:

    artifact = report[
        "artifact_contract"
    ]

    path = report[
        "eligible_signal_path"
    ]

    safety = report[
        "execution_safety"
    ]

    execution = report[
        "execution"
    ]

    print("=" * 100)

    print("ARUNDA TRADER")

    print(
        "LIVE SIGNAL ELIGIBLE SIGNAL "
        "REPLAY VERIFICATION v0.2"
    )

    print("=" * 100)

    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )

    print(
        "MODE         : READ_ONLY"
    )

    print("=" * 100)

    print("SAFETY")

    print("=" * 100)

    print(
        "Producer execution : False"
    )

    print(
        "Producer import    : False"
    )

    print(
        "Database write     : False"
    )

    print(
        "Network access     : False"
    )

    print(
        "Order execution    : False"
    )

    print(
        "Signal injection   : False"
    )

    print(
        "Synthetic signal   : False"
    )

    print(
        "Replay execution   : False"
    )

    print("=" * 100)

    print("SOURCE CHAIN")

    print("=" * 100)

    chain = report["source_chain"]

    print(
        "Generation contract : "
        f"{chain['generation_contract_verified']}"
    )

    print(
        "Runtime contract    : "
        f"{chain['runtime_contract_verified']}"
    )

    print(
        "Artifact contract   : "
        f"{chain['artifact_contract_verified']}"
    )

    print(
        "Validation contract : "
        f"{chain['validation_contract_verified']}"
    )

    print(
        "Execution gate      : "
        f"{chain['execution_gate_verified']}"
    )

    print("=" * 100)

    print("ARTIFACT CONTRACT")

    print("=" * 100)

    print(
        f"contract       : "
        f"{artifact['contract']}"
    )

    print(
        f"verified       : "
        f"{artifact['verified']}"
    )

    print(
        f"rows           : "
        f"{artifact['rows']}"
    )

    print(
        f"eligible_rows  : "
        f"{artifact['eligible_rows']}"
    )

    print(
        f"no_trade_rows  : "
        f"{artifact['no_trade_rows']}"
    )

    print(
        f"decision       : "
        f"{artifact['decision']}"
    )

    print(
        f"snapshot_id    : "
        f"{artifact['snapshot_id']}"
    )

    print("=" * 100)

    print("ELIGIBLE SIGNAL PATH")

    print("=" * 100)

    print(
        f"STATUS         : "
        f"{path['status']}"
    )

    print(
        f"ELIGIBLE       : "
        f"{path['eligible_signals']}"
    )

    print(
        f"ORDER INTENTS  : "
        f"{path['order_intents']}"
    )

    print(
        f"PATH VERIFIED  : "
        f"{path['path_verified']}"
    )

    print(
        f"REPLAY         : "
        f"{path['replay_performed']}"
    )

    print(
        path["reason"]
    )

    print("=" * 100)

    print("EXECUTION SAFETY")

    print("=" * 100)

    print(
        f"Execution allowed : "
        f"{safety['execution_allowed']}"
    )

    print(
        f"Order creation    : "
        f"{safety['order_creation']}"
    )

    print(
        f"Order submission  : "
        f"{safety['order_submission']}"
    )

    print(
        f"Network access    : "
        f"{safety['network_access']}"
    )

    print(
        f"DB write          : "
        f"{safety['production_db_write']}"
    )

    print("=" * 100)

    print("FINAL VERDICT")

    print("=" * 100)

    print(
        f"VERDICT    : "
        f"{report['final_verdict']}"
    )

    print(
        f"NEXT STAGE : "
        f"{report['next_stage']}"
    )

    print("=" * 100)

    print(
        f"REPORT WRITTEN : "
        f"{OUTPUT_REPORT}"
    )

    print("=" * 100)


def main() -> int:

    chain = validate_source_chain()

    report = build_report(
        chain
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

    print_report(
        report
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())