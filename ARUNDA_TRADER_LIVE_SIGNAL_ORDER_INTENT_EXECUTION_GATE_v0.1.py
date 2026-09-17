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
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_EXECUTION_GATE_REPORT.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Validation report not found: {path}"
        )

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise TypeError(
            "Validation report root must be a JSON object."
        )

    return data


def require_dict(
    parent: dict[str, Any],
    key: str,
) -> dict[str, Any]:

    value = parent.get(key)

    if not isinstance(value, dict):
        raise TypeError(
            f"Contract field '{key}' must be a dict, "
            f"got {type(value).__name__}."
        )

    return value


def require_false(
    parent: dict[str, Any],
    key: str,
) -> None:

    value = parent.get(key)

    if value is not False:
        raise ValueError(
            f"Execution gate safety violation: "
            f"{key} must be False."
        )


def get_generation_contract(
    report: dict[str, Any],
) -> dict[str, Any]:

    generation = report.get(
        "order_intent_generation"
    )

    if isinstance(generation, dict):
        return generation

    return {
        "status": "READY_NO_ELIGIBLE_SIGNALS",
        "intents": [],
        "intents_count": 0,
        "contract_valid": True,
    }


def validate_report(
    report: dict[str, Any],
) -> dict[str, Any]:

    runtime = require_dict(
        report,
        "runtime_contract",
    )

    artifact = require_dict(
        report,
        "artifact_contract",
    )

    execution_safety = require_dict(
        report,
        "execution_safety",
    )

    execution = require_dict(
        report,
        "execution",
    )

    generation = get_generation_contract(
        report
    )

    if runtime.get("contract") is not True:
        raise ValueError(
            "Runtime contract is not verified."
        )

    if runtime.get("runtime_ready") is not True:
        raise ValueError(
            "Runtime is not ready."
        )

    if runtime.get("upstream_verified") is not True:
        raise ValueError(
            "Runtime upstream is not verified."
        )

    if runtime.get("artifact_verified") is not True:
        raise ValueError(
            "Runtime artifact is not verified."
        )

    if runtime.get("operational_safety") is not True:
        raise ValueError(
            "Runtime operational safety is not verified."
        )

    if artifact.get("contract") is not True:
        raise ValueError(
            "Artifact contract is not verified."
        )

    if artifact.get("verified") is not True:
        raise ValueError(
            "Artifact verification is not true."
        )

    intents = generation.get(
        "intents",
        [],
    )

    if not isinstance(intents, list):
        raise TypeError(
            "order_intent_generation.intents "
            "must be a list."
        )

    status = generation.get(
        "status",
        "READY_NO_ELIGIBLE_SIGNALS",
    )

    if not isinstance(status, str):
        raise TypeError(
            "order_intent_generation.status "
            "must be a string."
        )

    require_false(
        execution_safety,
        "network_access",
    )

    require_false(
        execution_safety,
        "order_creation",
    )

    require_false(
        execution_safety,
        "order_submission",
    )

    require_false(
        execution_safety,
        "order_execution",
    )

    require_false(
        execution_safety,
        "production_db_write",
    )

    execution_allowed = execution_safety.get(
        "execution_allowed",
        False,
    )

    if execution_allowed is not False:
        raise ValueError(
            "Execution gate safety violation: "
            "execution_allowed must be False."
        )

    executed = execution.get(
        "executed",
        False,
    )

    if executed is not False:
        raise ValueError(
            "Execution gate safety violation: "
            "executed must be False."
        )

    orders_created = execution.get(
        "orders_created",
        0,
    )

    if orders_created != 0:
        raise ValueError(
            "Execution gate safety violation: "
            "orders_created must be 0."
        )

    orders_submitted = execution.get(
        "orders_submitted",
        0,
    )

    if orders_submitted != 0:
        raise ValueError(
            "Execution gate safety violation: "
            "orders_submitted must be 0."
        )

    if len(intents) == 0:

        gate_status = (
            "READY_NO_ORDER_INTENTS"
        )

        final_verdict = (
            "LIVE_SIGNAL_ORDER_INTENT_EXECUTION_GATE_READY"
        )

        next_stage = (
            "WAIT_FOR_ELIGIBLE_SIGNAL"
        )

    else:

        gate_status = (
            "ORDER_INTENTS_PRESENT_EXECUTION_BLOCKED"
        )

        final_verdict = (
            "LIVE_SIGNAL_ORDER_INTENT_EXECUTION_GATE_READY"
        )

        next_stage = (
            "ORDER_INTENT_EXECUTION_DRY_RUN"
        )

    return {
        "runtime": runtime,
        "artifact": artifact,
        "generation": generation,
        "execution_safety": execution_safety,
        "execution": execution,
        "intents": intents,
        "status": status,
        "gate_status": gate_status,
        "final_verdict": final_verdict,
        "next_stage": next_stage,
    }


def build_output(
    validation: dict[str, Any],
) -> dict[str, Any]:

    runtime = validation["runtime"]
    artifact = validation["artifact"]
    generation = validation["generation"]

    intents = validation["intents"]

    return {
        "project": "ARUNDA TRADER",

        "component": (
            "LIVE SIGNAL ORDER-INTENT EXECUTION GATE"
        ),

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

        "source": {
            "validation_report": str(
                VALIDATION_REPORT
            ),
            "validation_report_sha256": sha256_file(
                VALIDATION_REPORT
            ),
        },

        "runtime_contract": {
            "contract": True,
            "runtime_ready": runtime.get(
                "runtime_ready",
                True,
            ),
            "upstream_verified": runtime.get(
                "upstream_verified",
                True,
            ),
            "artifact_verified": runtime.get(
                "artifact_verified",
                True,
            ),
            "operational_safety": runtime.get(
                "operational_safety",
                True,
            ),
            "verdict": runtime.get(
                "verdict"
            ),
        },

        "artifact_contract": {
            "contract": True,
            "verified": True,
            "rows": artifact.get(
                "rows",
                0,
            ),
            "eligible_rows": artifact.get(
                "eligible_rows",
                0,
            ),
            "no_trade_rows": artifact.get(
                "no_trade_rows",
                0,
            ),
            "decision": artifact.get(
                "decision"
            ),
            "snapshot_id": artifact.get(
                "snapshot_id"
            ),
        },

        "generation_contract": {
            "contract": True,
            "verified": True,
            "status": generation.get(
                "status",
                "READY_NO_ELIGIBLE_SIGNALS",
            ),
            "order_intents": len(intents),
            "validated_intents": generation.get(
                "validated_intents",
                0,
            ),
            "invalid_intents": generation.get(
                "invalid_intents",
                0,
            ),
        },

        "execution_gate": {
            "status": validation[
                "gate_status"
            ],
            "contract": True,
            "verified": True,

            "execution_allowed": False,
            "order_creation_allowed": False,
            "order_submission_allowed": False,
            "network_access_allowed": False,
            "production_db_write_allowed": False,
        },

        "execution": {
            "executed": False,
            "orders_created": 0,
            "orders_submitted": 0,
        },

        "final_verdict": validation[
            "final_verdict"
        ],

        "next_stage": validation[
            "next_stage"
        ],
    }


def print_report(
    output: dict[str, Any],
) -> None:

    runtime = output[
        "runtime_contract"
    ]

    artifact = output[
        "artifact_contract"
    ]

    generation = output[
        "generation_contract"
    ]

    gate = output[
        "execution_gate"
    ]

    execution = output[
        "execution"
    ]

    print("=" * 100)
    print("ARUNDA TRADER")
    print(
        "LIVE SIGNAL ORDER-INTENT EXECUTION GATE v0.2"
    )
    print("=" * 100)

    print("PROJECT ROOT        :", PROJECT_ROOT)
    print(
        "UPSTREAM VALIDATION :",
        VALIDATION_REPORT,
    )
    print(
        "OUTPUT REPORT       :",
        OUTPUT_REPORT,
    )

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)

    print(
        "producer_execution     : False"
    )
    print(
        "producer_import        : False"
    )
    print(
        "production_db_write    : False"
    )
    print(
        "network_access         : False"
    )
    print(
        "order_execution        : False"
    )
    print(
        "order_creation         : False"
    )
    print(
        "order_submission       : False"
    )
    print(
        "artifact_mutation      : False"
    )
    print(
        "operational_safety     : True"
    )

    print("=" * 100)
    print("RUNTIME CONTRACT")
    print("=" * 100)

    print(
        "contract                :",
        runtime["contract"],
    )

    print(
        "runtime_ready           :",
        runtime["runtime_ready"],
    )

    print(
        "upstream_verified       :",
        runtime["upstream_verified"],
    )

    print(
        "artifact_verified       :",
        runtime["artifact_verified"],
    )

    print(
        "operational_safety      :",
        runtime["operational_safety"],
    )

    print(
        "verdict                 :",
        runtime["verdict"],
    )

    print("=" * 100)
    print("ARTIFACT CONTRACT")
    print("=" * 100)

    print(
        "contract                :",
        artifact["contract"],
    )

    print(
        "verified                :",
        artifact["verified"],
    )

    print(
        "rows                    :",
        artifact["rows"],
    )

    print(
        "eligible_rows           :",
        artifact["eligible_rows"],
    )

    print(
        "no_trade_rows           :",
        artifact["no_trade_rows"],
    )

    print(
        "decision                :",
        artifact["decision"],
    )

    print(
        "snapshot_id             :",
        artifact["snapshot_id"],
    )

    print("=" * 100)
    print("ORDER-INTENT EXECUTION GATE")
    print("=" * 100)

    print(
        "STATUS                  :",
        gate["status"],
    )

    print(
        "ORDER INTENTS           :",
        generation["order_intents"],
    )

    print(
        "EXECUTION ALLOWED       :",
        gate["execution_allowed"],
    )

    print(
        "ORDER CREATION          :",
        gate["order_creation_allowed"],
    )

    print(
        "ORDER SUBMISSION        :",
        gate["order_submission_allowed"],
    )

    print(
        "NETWORK ACCESS          :",
        gate["network_access_allowed"],
    )

    print(
        "PRODUCTION DB WRITE     :",
        gate["production_db_write_allowed"],
    )

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)

    print(
        "EXECUTION GATE          :",
        output["final_verdict"],
    )

    print(
        "EXECUTION               :",
        "EXECUTED"
        if execution["executed"]
        else "NOT_EXECUTED",
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
        output["next_stage"],
    )

    print("=" * 100)
    print(
        "REPORT WRITTEN          :",
        OUTPUT_REPORT,
    )
    print("=" * 100)


def main() -> int:

    report = load_json(
        VALIDATION_REPORT
    )

    validation = validate_report(
        report
    )

    output = build_output(
        validation
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

    print_report(
        output
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )