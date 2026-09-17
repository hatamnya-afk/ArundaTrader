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

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_VALIDATION_REPORT.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Generation report not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise TypeError("Generation report root must be a JSON object.")

    return data


def require_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)

    if not isinstance(value, dict):
        raise TypeError(
            f"Contract field '{key}' must be a dict, "
            f"got {type(value).__name__}"
        )

    return value


def require_bool(
    parent: dict[str, Any],
    key: str,
    expected: bool = True,
) -> bool:
    value = parent.get(key)

    if not isinstance(value, bool):
        raise TypeError(
            f"Contract field '{key}' must be bool, "
            f"got {type(value).__name__}"
        )

    if value is not expected:
        raise ValueError(
            f"Contract field '{key}' expected {expected}, got {value}"
        )

    return value


def validate_generation_report(
    report: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:

    required = [
        "safety",
        "sources",
        "runtime_contract",
        "artifact_contract",
        "order_intent_generation",
        "execution_safety",
        "execution",
        "final_verdict",
        "next_stage",
    ]

    missing = [key for key in required if key not in report]

    if missing:
        raise ValueError(
            "Generation report missing required fields: "
            + ", ".join(missing)
        )

    safety = require_dict(report, "safety")
    sources = require_dict(report, "sources")
    runtime_contract = require_dict(report, "runtime_contract")
    artifact_contract = require_dict(report, "artifact_contract")
    generation = require_dict(report, "order_intent_generation")
    execution_safety = require_dict(report, "execution_safety")

    execution = report.get("execution")

    if not isinstance(execution, dict):
        raise TypeError(
            f"Contract field 'execution' must be a dict, "
            f"got {type(execution).__name__}"
        )

    # IMPORTANT:
    # Producer contract shows next_stage as STRING.
    # It must NOT be forced to dict.
    next_stage = report.get("next_stage")

    if not isinstance(next_stage, str):
        raise TypeError(
            f"Contract field 'next_stage' must be a string, "
            f"got {type(next_stage).__name__}"
        )

    final_verdict = report.get("final_verdict")

    if not isinstance(final_verdict, str):
        raise TypeError(
            f"Contract field 'final_verdict' must be a string, "
            f"got {type(final_verdict).__name__}"
        )

    require_bool(runtime_contract, "contract", True)
    require_bool(artifact_contract, "contract", True)

    intents = generation.get("intents")

    if not isinstance(intents, list):
        raise TypeError(
            "order_intent_generation.intents must be a list."
        )

    status = generation.get("status")

    if not isinstance(status, str):
        raise TypeError(
            "order_intent_generation.status must be a string."
        )

    eligible_signals = generation.get("eligible_signals")

    if not isinstance(eligible_signals, int):
        raise TypeError(
            "order_intent_generation.eligible_signals must be int."
        )

    generated_count = generation.get("order_intents_generated")

    if not isinstance(generated_count, int):
        raise TypeError(
            "order_intent_generation.order_intents_generated must be int."
        )

    validated_intents = generation.get("validated_intents")

    if not isinstance(validated_intents, int):
        raise TypeError(
            "order_intent_generation.validated_intents must be int."
        )

    invalid_intents = generation.get("invalid_intents")

    if not isinstance(invalid_intents, int):
        raise TypeError(
            "order_intent_generation.invalid_intents must be int."
        )

    if generated_count != len(intents):
        raise ValueError(
            "order_intents_generated does not match intents length."
        )

    if len(intents) == 0:
        if eligible_signals != 0:
            raise ValueError(
                "Empty intents require eligible_signals == 0."
            )

        if generated_count != 0:
            raise ValueError(
                "Empty intents require order_intents_generated == 0."
            )

        if status != "READY_NO_ELIGIBLE_SIGNALS":
            raise ValueError(
                "Empty intents require status "
                "'READY_NO_ELIGIBLE_SIGNALS'."
            )

    source_snapshot = {
        "generation_report": str(GENERATION_REPORT),
        "generation_report_sha256": sha256_file(GENERATION_REPORT),
    }

    validation = {
        "contract": True,
        "runtime_contract": {
            "contract": True,
            "runtime_ready": runtime_contract.get(
                "runtime_ready", False
            ),
            "upstream_verified": runtime_contract.get(
                "upstream_verified", False
            ),
            "artifact_verified": runtime_contract.get(
                "artifact_verified", False
            ),
            "operational_safety": runtime_contract.get(
                "operational_safety", False
            ),
            "verdict": runtime_contract.get("verdict"),
        },
        "artifact_contract": {
            "contract": True,
            "verified": True,
            "rows": artifact_contract.get("rows", 0),
            "eligible_rows": artifact_contract.get(
                "eligible_rows", 0
            ),
            "no_trade_rows": artifact_contract.get(
                "no_trade_rows", 0
            ),
            "decision": artifact_contract.get("decision"),
            "snapshot_id": artifact_contract.get(
                "snapshot_id"
            ),
        },
        "generation_contract": {
            "status": status,
            "eligible_signals": eligible_signals,
            "order_intents_generated": generated_count,
            "validated_intents": validated_intents,
            "invalid_intents": invalid_intents,
            "intents_count": len(intents),
            "intents_empty": len(intents) == 0,
        },
        "execution_contract": {
            "is_dict": True,
            "execution": execution,
        },
        "source": source_snapshot,
    }

    if len(intents) == 0:
        validation["final_verdict"] = (
            "LIVE_SIGNAL_ORDER_INTENT_VALIDATION_READY"
        )
        validation["next_stage"] = "WAIT_FOR_ELIGIBLE_SIGNAL"
    else:
        validation["final_verdict"] = (
            "LIVE_SIGNAL_ORDER_INTENT_VALIDATION_READY"
        )
        validation["next_stage"] = (
            "ORDER_INTENT_VALIDATION_COMPLETE"
        )

    source_contract = {
        "safety": safety,
        "sources": sources,
        "runtime_contract": runtime_contract,
        "artifact_contract": artifact_contract,
        "order_intent_generation": generation,
        "execution_safety": execution_safety,
        "execution": execution,
        "final_verdict": final_verdict,
        "next_stage": next_stage,
    }

    return validation, source_contract


def build_output(
    validation: dict[str, Any],
    source_contract: dict[str, Any],
) -> dict[str, Any]:

    generation = source_contract["order_intent_generation"]
    intents = generation["intents"]

    if len(intents) == 0:
        validation_status = "READY_NO_ELIGIBLE_SIGNALS"
        validation_reason = "NO_ORDER_INTENTS_TO_VALIDATE"
    else:
        validation_status = "VALIDATED"
        validation_reason = "ORDER_INTENTS_VALIDATED"

    validated_intents = (
        intents if len(intents) > 0 else []
    )

    invalid_details: list[dict[str, Any]] = []

    execution_result = {
        "executed": False,
        "orders_created": 0,
        "orders_submitted": 0,
    }

    return {
        "project": "ARUNDA TRADER",
        "component": "LIVE SIGNAL ORDER-INTENT VALIDATION",
        "version": "v0.2",

        "safety": {
            "producer_execution": False,
            "producer_import": False,
            "production_db_write": False,
            "network_access": False,
            "order_execution": False,
            "order_creation": False,
            "order_submission": False,
            "artifact_mutation": False,
            "operational_safety": True,
        },

        "sources": {
            "generation": str(GENERATION_REPORT),
            "generation_sha256": validation["source"][
                "generation_report_sha256"
            ],
        },

        "generation_contract": {
            "contract": True,
            "verified": True,
            "status": generation["status"],
            "eligible_signals": generation[
                "eligible_signals"
            ],
            "order_intents_generated": generation[
                "order_intents_generated"
            ],
            "validated_intents": len(validated_intents),
            "invalid_intents": len(invalid_details),
        },

        "runtime_contract": validation[
            "runtime_contract"
        ],

        "artifact_contract": validation[
            "artifact_contract"
        ],

        "order_intent_validation": {
            "status": validation_status,
            "reason": validation_reason,
            "eligible_signals": generation[
                "eligible_signals"
            ],
            "order_intents": len(intents),
            "validated_intents": len(validated_intents),
            "invalid_intents": len(invalid_details),
            "intents": validated_intents,
            "invalid_details": invalid_details,
        },

        "execution_safety": {
            "network_access": False,
            "order_creation": False,
            "order_submission": False,
            "order_execution": False,
            "production_db_write": False,
        },

        "execution": execution_result,

        "final_verdict": (
            "LIVE_SIGNAL_ORDER_INTENT_VALIDATION_READY"
        ),

        "next_stage": (
            "WAIT_FOR_ELIGIBLE_SIGNAL"
            if len(intents) == 0
            else "ORDER_INTENT_VALIDATION_COMPLETE"
        ),
    }


def print_report(report: dict[str, Any]) -> None:

    generation = report["generation_contract"]
    validation = report["order_intent_validation"]
    execution = report["execution"]

    print("=" * 100)
    print(
        "ARUNDA TRADER"
    )
    print(
        "LIVE SIGNAL ORDER-INTENT VALIDATION v0.2"
    )
    print("=" * 100)

    print("PROJECT ROOT            :", PROJECT_ROOT)
    print("UPSTREAM GENERATION     :", GENERATION_REPORT)
    print("OUTPUT REPORT           :", OUTPUT_REPORT)

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)

    print(
        "producer_execution      :",
        report["safety"]["producer_execution"],
    )
    print(
        "producer_import         :",
        report["safety"]["producer_import"],
    )
    print(
        "production_db_write     :",
        report["safety"]["production_db_write"],
    )
    print(
        "network_access          :",
        report["safety"]["network_access"],
    )
    print(
        "order_execution         :",
        report["safety"]["order_execution"],
    )
    print(
        "order_creation          :",
        report["safety"]["order_creation"],
    )
    print(
        "order_submission        :",
        report["safety"]["order_submission"],
    )
    print(
        "artifact_mutation       :",
        report["safety"]["artifact_mutation"],
    )
    print(
        "operational_safety      :",
        report["safety"]["operational_safety"],
    )

    print("=" * 100)
    print("GENERATION CONTRACT")
    print("=" * 100)

    print(
        "contract                :",
        generation["contract"],
    )
    print(
        "verified                :",
        generation["verified"],
    )
    print(
        "status                  :",
        generation["status"],
    )
    print(
        "eligible_signals        :",
        generation["eligible_signals"],
    )
    print(
        "order_intents_generated :",
        generation["order_intents_generated"],
    )
    print(
        "validated_intents       :",
        generation["validated_intents"],
    )
    print(
        "invalid_intents         :",
        generation["invalid_intents"],
    )

    print("=" * 100)
    print("RUNTIME CONTRACT")
    print("=" * 100)

    runtime = report["runtime_contract"]

    print("contract                :", runtime["contract"])
    print("runtime_ready           :", runtime["runtime_ready"])
    print("upstream_verified       :", runtime["upstream_verified"])
    print("artifact_verified       :", runtime["artifact_verified"])
    print("operational_safety      :", runtime["operational_safety"])
    print("verdict                 :", runtime["verdict"])

    print("=" * 100)
    print("ARTIFACT CONTRACT")
    print("=" * 100)

    artifact = report["artifact_contract"]

    print("contract                :", artifact["contract"])
    print("verified                :", artifact["verified"])
    print("rows                    :", artifact["rows"])
    print("eligible_rows           :", artifact["eligible_rows"])
    print("no_trade_rows           :", artifact["no_trade_rows"])
    print("decision                :", artifact["decision"])
    print("snapshot_id             :", artifact["snapshot_id"])

    print("=" * 100)
    print("ORDER-INTENT VALIDATION")
    print("=" * 100)

    print(
        "VALIDATION STATUS       :",
        validation["status"],
    )
    print(
        "ELIGIBLE SIGNALS        :",
        validation["eligible_signals"],
    )
    print(
        "ORDER INTENTS           :",
        validation["order_intents"],
    )
    print(
        "VALIDATED INTENTS       :",
        validation["validated_intents"],
    )
    print(
        "INVALID INTENTS         :",
        validation["invalid_intents"],
    )

    print("=" * 100)
    print("ORDER-INTENT SAFETY")
    print("=" * 100)

    safety = report["execution_safety"]

    print("Network access          :", safety["network_access"])
    print("Order creation          :", safety["order_creation"])
    print("Order submission        :", safety["order_submission"])
    print("Order execution         :", safety["order_execution"])
    print(
        "Production DB write     :",
        safety["production_db_write"],
    )

    print("=" * 100)
    print("ORDER-INTENT DETAILS")
    print("=" * 100)

    if validation["order_intents"] == 0:
        print("No order intent exists in the generation artifact.")
        print("No order intent was generated for validation.")
    else:
        print(
            f"{validation['validated_intents']} "
            "order intent(s) validated."
        )

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)

    print(
        "ORDER-INTENT VALIDATION :",
        report["final_verdict"],
    )
    print(
        "EXECUTION               :",
        "NOT_EXECUTED"
        if not execution["executed"]
        else "EXECUTED",
    )
    print(
        "ORDERS CREATED          :",
        execution["orders_created"],
    )
    print(
        "ORDERS SUBMITTED        :",
        execution["orders_submitted"],
    )
    print(
        "NEXT STAGE              :",
        report["next_stage"],
    )

    print("=" * 100)
    print("OUTPUT                  :", OUTPUT_REPORT)
    print("=" * 100)


def main() -> int:

    try:
        source_report = load_json(GENERATION_REPORT)

        validation, source_contract = validate_generation_report(
            source_report
        )

        output = build_output(
            validation,
            source_contract,
        )

        with OUTPUT_REPORT.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                output,
                handle,
                indent=2,
                ensure_ascii=False,
            )
            handle.write("\n")

        print_report(output)

        return 0

    except Exception as exc:

        print("=" * 100)
        print("ARUNDA TRADER")
        print("LIVE SIGNAL ORDER-INTENT VALIDATION")
        print("=" * 100)
        print("STATUS : CONTRACT_INVALID")
        print("ERROR  :", str(exc))
        print("=" * 100)

        return 1


if __name__ == "__main__":
    raise SystemExit(main())