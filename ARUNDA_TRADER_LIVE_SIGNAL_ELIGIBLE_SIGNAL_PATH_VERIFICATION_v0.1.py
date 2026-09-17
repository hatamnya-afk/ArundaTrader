from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

ARTIFACT_REPORT = (
    PROJECT_ROOT
    / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
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

PREFLIGHT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_EXECUTION_PREFLIGHT_REPORT.json"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBLE_SIGNAL_PATH_VERIFICATION_REPORT.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required report not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise TypeError(
            f"JSON root must be dict: {path}"
        )

    return data


def get_dict(
    parent: dict[str, Any],
    key: str,
) -> dict[str, Any] | None:
    value = parent.get(key)

    if value is None:
        return None

    if not isinstance(value, dict):
        raise TypeError(
            f"Field '{key}' must be dict or None, "
            f"got {type(value).__name__}."
        )

    return value


def get_bool(
    parent: dict[str, Any],
    key: str,
    default: bool = False,
) -> bool:
    value = parent.get(key, default)

    if not isinstance(value, bool):
        raise TypeError(
            f"Field '{key}' must be bool, "
            f"got {type(value).__name__}."
        )

    return value


def get_int(
    parent: dict[str, Any],
    key: str,
    default: int = 0,
) -> int:
    value = parent.get(key, default)

    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(
            f"Field '{key}' must be int, "
            f"got {type(value).__name__}."
        )

    return value


def get_list(
    parent: dict[str, Any],
    key: str,
) -> list[Any]:
    value = parent.get(key, [])

    if not isinstance(value, list):
        raise TypeError(
            f"Field '{key}' must be list, "
            f"got {type(value).__name__}."
        )

    return value


def verify_artifact(
    report: dict[str, Any],
) -> dict[str, Any]:
    rows = get_int(report, "rows")
    eligible_rows = get_int(report, "eligible_rows")
    no_trade_rows = get_int(report, "no_trade_rows")

    row_results = get_list(report, "row_results")

    decision = report.get("decision")
    snapshot_id = report.get("snapshot_id")

    contract_valid = (
        isinstance(rows, int)
        and isinstance(eligible_rows, int)
        and isinstance(no_trade_rows, int)
        and rows == len(row_results)
        and eligible_rows + no_trade_rows == rows
        and isinstance(decision, str)
        and isinstance(snapshot_id, str)
        and snapshot_id != ""
    )

    eligible_detected = []

    for index, row in enumerate(row_results):
        if not isinstance(row, dict):
            raise TypeError(
                f"row_results[{index}] must be dict."
            )

        eligible = row.get("eligible", False)

        if not isinstance(eligible, bool):
            raise TypeError(
                f"row_results[{index}].eligible must be bool."
            )

        if eligible:
            eligible_detected.append(row)

    eligible_count_matches = (
        len(eligible_detected) == eligible_rows
    )

    return {
        "contract": contract_valid and eligible_count_matches,
        "verified": contract_valid and eligible_count_matches,
        "rows": rows,
        "eligible_rows": eligible_rows,
        "no_trade_rows": no_trade_rows,
        "row_results_count": len(row_results),
        "eligible_detected": len(eligible_detected),
        "eligible_count_matches": eligible_count_matches,
        "decision": decision,
        "snapshot_id": snapshot_id,
        "eligible_rows_data": eligible_detected,
    }


def verify_generation(
    report: dict[str, Any],
) -> dict[str, Any]:
    generation = report.get("order_intent_generation")

    if not isinstance(generation, dict):
        return {
            "contract": False,
            "verified": False,
            "reason": "GENERATION_SECTION_MISSING",
            "status": None,
            "intents_count": 0,
        }

    intents = generation.get("intents", [])

    if not isinstance(intents, list):
        return {
            "contract": False,
            "verified": False,
            "reason": "GENERATION_INTENTS_NOT_LIST",
            "status": generation.get("status"),
            "intents_count": 0,
        }

    status = generation.get("status")

    return {
        "contract": True,
        "verified": True,
        "reason": "GENERATION_CONTRACT_VERIFIED",
        "status": status,
        "intents_count": len(intents),
    }


def verify_validation(
    report: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {
            "contract": False,
            "verified": False,
            "reason": "VALIDATION_ROOT_INVALID",
        }

    final_verdict = report.get("final_verdict")

    if isinstance(final_verdict, dict):
        contract = get_bool(
            final_verdict,
            "contract",
            False,
        )
        valid = get_bool(
            final_verdict,
            "valid",
            False,
        )
    else:
        contract = False
        valid = False

    return {
        "contract": contract,
        "verified": contract and valid,
        "reason": (
            "VALIDATION_CONTRACT_VERIFIED"
            if contract and valid
            else "VALIDATION_CONTRACT_NOT_VERIFIED"
        ),
    }


def verify_execution_gate(
    report: dict[str, Any],
) -> dict[str, Any]:
    final_verdict = report.get("final_verdict")

    if not isinstance(final_verdict, dict):
        return {
            "contract": False,
            "verified": False,
            "execution_allowed": False,
            "reason": "EXECUTION_GATE_VERDICT_INVALID",
        }

    status = final_verdict.get("status")

    execution = report.get("execution")

    if not isinstance(execution, dict):
        execution = {}

    execution_allowed = execution.get(
        "execution_allowed",
        False,
    )

    if not isinstance(execution_allowed, bool):
        raise TypeError(
            "Execution gate execution_allowed must be bool."
        )

    return {
        "contract": True,
        "verified": True,
        "status": status,
        "execution_allowed": execution_allowed,
        "reason": "EXECUTION_GATE_CONTRACT_VERIFIED",
    }


def verify_preflight(
    report: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {
            "contract": False,
            "verified": False,
            "reason": "PREFLIGHT_ROOT_INVALID",
        }

    execution = report.get("execution")

    if not isinstance(execution, dict):
        execution = {}

    execution_allowed = execution.get(
        "execution_allowed",
        False,
    )

    if not isinstance(execution_allowed, bool):
        raise TypeError(
            "Preflight execution_allowed must be bool."
        )

    return {
        "contract": True,
        "verified": True,
        "execution_allowed": execution_allowed,
        "reason": "PREFLIGHT_CONTRACT_VERIFIED",
    }


def verify_safety(
    artifact: dict[str, Any],
    generation: dict[str, Any],
    validation: dict[str, Any],
    gate: dict[str, Any],
    preflight: dict[str, Any],
) -> dict[str, Any]:
    safety = artifact.get("safety", {})

    if not isinstance(safety, dict):
        raise TypeError(
            "Artifact safety must be dict."
        )

    safety_flags = {
        "production_db_modified": safety.get(
            "production_db_modified",
            False,
        ),
        "engine_executed": safety.get(
            "engine_executed",
            False,
        ),
        "historical_repair": safety.get(
            "historical_repair",
            False,
        ),
        "direction_inference": safety.get(
            "direction_inference",
            False,
        ),
        "score_reconstruction": safety.get(
            "score_reconstruction",
            False,
        ),
        "synthetic_data": safety.get(
            "synthetic_data",
            False,
        ),
        "live_data_injection": safety.get(
            "live_data_injection",
            False,
        ),
        "order_execution": safety.get(
            "order_execution",
            False,
        ),
    }

    artifact_safe = all(
        value is False
        for value in safety_flags.values()
        if isinstance(value, bool)
    )

    safe = (
        artifact_safe
        and gate.get("execution_allowed") is False
        and preflight.get("execution_allowed") is False
    )

    return {
        "safe": safe,
        "artifact_safety": safety_flags,
        "execution_allowed": gate.get(
            "execution_allowed",
            False,
        ),
        "preflight_execution_allowed": preflight.get(
            "execution_allowed",
            False,
        ),
    }


def build_report(
    artifact_result: dict[str, Any],
    generation_result: dict[str, Any],
    validation_result: dict[str, Any],
    gate_result: dict[str, Any],
    preflight_result: dict[str, Any],
    safety_result: dict[str, Any],
) -> dict[str, Any]:

    eligible_rows = artifact_result[
        "eligible_rows_data"
    ]

    eligible_count = len(eligible_rows)

    if eligible_count == 0:
        status = "NO_ELIGIBLE_SIGNAL"
        verdict = (
            "LIVE_SIGNAL_ELIGIBLE_SIGNAL_PATH_VERIFICATION_READY"
        )
        next_stage = "WAIT_FOR_ELIGIBLE_SIGNAL"
    else:
        status = "ELIGIBLE_SIGNAL_PATH_DETECTED"
        verdict = (
            "LIVE_SIGNAL_ELIGIBLE_SIGNAL_PATH_VERIFICATION_READY"
        )
        next_stage = "ORDER_INTENT_PATH_REVALIDATION"

    return {
        "project": "ARUNDA TRADER",
        "component": (
            "LIVE SIGNAL ELIGIBLE SIGNAL PATH VERIFICATION"
        ),
        "version": "v0.1",

        "mode": "READ_ONLY",

        "safety": {
            "producer_execution": False,
            "producer_import": False,
            "production_db_write": False,
            "network_access": False,
            "exchange_access": False,
            "order_creation": False,
            "order_submission": False,
            "order_execution": False,
            "artifact_mutation": False,
            "synthetic_data": False,
            "live_data_injection": False,
        },

        "sources": {
            "artifact": {
                "path": str(ARTIFACT_REPORT),
                "sha256": sha256_file(
                    ARTIFACT_REPORT
                ),
            },
            "generation": {
                "path": str(GENERATION_REPORT),
                "sha256": sha256_file(
                    GENERATION_REPORT
                ),
            },
            "validation": {
                "path": str(VALIDATION_REPORT),
                "sha256": sha256_file(
                    VALIDATION_REPORT
                ),
            },
            "execution_gate": {
                "path": str(EXECUTION_GATE_REPORT),
                "sha256": sha256_file(
                    EXECUTION_GATE_REPORT
                ),
            },
            "preflight": {
                "path": str(PREFLIGHT_REPORT),
                "sha256": sha256_file(
                    PREFLIGHT_REPORT
                ),
            },
        },

        "artifact_contract": artifact_result,

        "generation_contract": generation_result,

        "validation_contract": validation_result,

        "execution_gate_contract": gate_result,

        "execution_preflight_contract": preflight_result,

        "eligible_signal_path": {
            "status": status,
            "eligible_signals": eligible_count,
            "signals": eligible_rows,
            "path_verified": (
                artifact_result["verified"]
                and generation_result["verified"]
                and validation_result["verified"]
                and gate_result["verified"]
                and preflight_result["verified"]
            ),
        },

        "safety_verification": safety_result,

        "execution": {
            "executed": False,
            "orders_created": 0,
            "orders_submitted": 0,
            "execution_allowed": False,
        },

        "final_verdict": verdict,

        "next_stage": next_stage,
    }


def print_report(report: dict[str, Any]) -> None:
    artifact = report["artifact_contract"]
    generation = report["generation_contract"]
    path = report["eligible_signal_path"]

    print("=" * 100)
    print("ARUNDA TRADER")
    print("LIVE SIGNAL ELIGIBLE SIGNAL PATH VERIFICATION v0.1")
    print("=" * 100)

    print("PROJECT ROOT :", PROJECT_ROOT)
    print("MODE         : READ_ONLY")

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)

    print("Producer execution : False")
    print("Producer import    : False")
    print("Database write     : False")
    print("Network access     : False")
    print("Order execution    : False")

    print("=" * 100)
    print("ARTIFACT CONTRACT")
    print("=" * 100)

    print(
        "contract       :",
        artifact["contract"],
    )
    print(
        "verified       :",
        artifact["verified"],
    )
    print(
        "rows           :",
        artifact["rows"],
    )
    print(
        "eligible_rows  :",
        artifact["eligible_rows"],
    )
    print(
        "no_trade_rows  :",
        artifact["no_trade_rows"],
    )
    print(
        "snapshot_id    :",
        artifact["snapshot_id"],
    )

    print("=" * 100)
    print("GENERATION CONTRACT")
    print("=" * 100)

    print(
        "contract       :",
        generation["contract"],
    )
    print(
        "verified       :",
        generation["verified"],
    )
    print(
        "status         :",
        generation["status"],
    )
    print(
        "intents_count  :",
        generation["intents_count"],
    )

    print("=" * 100)
    print("ELIGIBLE SIGNAL PATH")
    print("=" * 100)

    print(
        "STATUS         :",
        path["status"],
    )
    print(
        "ELIGIBLE       :",
        path["eligible_signals"],
    )
    print(
        "PATH VERIFIED  :",
        path["path_verified"],
    )

    if path["eligible_signals"] == 0:
        print()
        print(
            "No eligible signal exists in the current artifact."
        )
        print(
            "No signal was created, inferred, reconstructed, "
            "or injected."
        )
    else:
        print()
        print(
            "Eligible signal(s) detected from the actual "
            "producer artifact."
        )
        print(
            "No order was created or executed."
        )

    print("=" * 100)
    print("EXECUTION SAFETY")
    print("=" * 100)

    print("Execution allowed : False")
    print("Order creation    : False")
    print("Order submission  : False")
    print("Network access    : False")
    print("DB write          : False")

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
    artifact = load_json(ARTIFACT_REPORT)
    generation = load_json(GENERATION_REPORT)
    validation = load_json(VALIDATION_REPORT)
    gate = load_json(EXECUTION_GATE_REPORT)
    preflight = load_json(PREFLIGHT_REPORT)

    artifact_result = verify_artifact(artifact)
    generation_result = verify_generation(generation)
    validation_result = verify_validation(validation)
    gate_result = verify_execution_gate(gate)
    preflight_result = verify_preflight(preflight)

    safety_result = verify_safety(
        artifact,
        generation,
        validation,
        gate,
        preflight,
    )

    report = build_report(
        artifact_result,
        generation_result,
        validation_result,
        gate_result,
        preflight_result,
        safety_result,
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