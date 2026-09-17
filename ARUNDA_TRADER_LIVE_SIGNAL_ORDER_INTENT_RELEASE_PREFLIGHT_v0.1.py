from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

GATE_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_EXECUTION_GATE_REPORT.json"
)

PREFLIGHT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_EXECUTION_PREFLIGHT_REPORT.json"
)

REPLAY_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_VERIFICATION_REPORT.json"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_RELEASE_PREFLIGHT_REPORT.json"
)


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


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


def validate_gate(
    report: dict[str, Any],
) -> dict[str, Any]:

    runtime = get_dict(
        report,
        "runtime_contract",
    )

    artifact = get_dict(
        report,
        "artifact_contract",
    )

    safety = get_dict(
        report,
        "safety",
    )

    gate = get_dict(
        report,
        "order_intent_execution_gate",
    )

    execution = get_dict(
        report,
        "execution",
    )

    if runtime is None:
        raise ValueError(
            "GATE_RUNTIME_CONTRACT_MISSING"
        )

    if artifact is None:
        raise ValueError(
            "GATE_ARTIFACT_CONTRACT_MISSING"
        )

    if safety is None:
        raise ValueError(
            "GATE_SAFETY_SECTION_MISSING"
        )

    if gate is None:
        gate = {}

    if execution is None:
        execution = {}

    runtime_contract = (
        runtime.get("contract") is True
        and runtime.get("runtime_ready") is True
        and runtime.get("upstream_verified") is True
        and runtime.get("artifact_verified") is True
        and runtime.get("operational_safety") is True
    )

    artifact_contract = (
        artifact.get("contract") is True
        and artifact.get("verified") is True
    )

    safety_contract = (
        safety.get("operational_safety") is True
        and safety.get("network_access") is False
        and safety.get("order_creation") is False
        and safety.get("order_submission") is False
        and safety.get("order_execution") is False
        and safety.get("production_db_write") is False
    )

    execution_allowed = gate.get(
        "execution_allowed",
        False,
    )

    if execution_allowed is not False:
        raise ValueError(
            "EXECUTION_GATE_SAFETY_VIOLATION"
        )

    order_intents = get_int(
        gate,
        "order_intents",
        0,
    )

    return {
        "runtime_contract": runtime,
        "artifact_contract": artifact,
        "safety": safety,
        "gate": gate,
        "execution": execution,
        "runtime_contract_valid": runtime_contract,
        "artifact_contract_valid": artifact_contract,
        "safety_contract_valid": safety_contract,
        "execution_allowed": False,
        "order_intents": order_intents,
    }


def validate_preflight(
    report: dict[str, Any],
) -> dict[str, Any]:

    runtime = get_dict(
        report,
        "runtime_contract",
    )

    artifact = get_dict(
        report,
        "artifact_contract",
    )

    gate = get_dict(
        report,
        "execution_gate",
    )

    safety = get_dict(
        report,
        "safety",
    )

    if runtime is None:
        raise ValueError(
            "PREFLIGHT_RUNTIME_CONTRACT_MISSING"
        )

    if artifact is None:
        raise ValueError(
            "PREFLIGHT_ARTIFACT_CONTRACT_MISSING"
        )

    if gate is None:
        gate = {}

    if safety is None:
        safety = {}

    runtime_valid = (
        runtime.get("contract") is True
        and runtime.get("runtime_ready") is True
        and runtime.get("upstream_verified") is True
        and runtime.get("artifact_verified") is True
        and runtime.get("operational_safety") is True
    )

    artifact_valid = (
        artifact.get("contract") is True
        and artifact.get("verified") is True
    )

    execution_allowed = gate.get(
        "execution_allowed",
        False,
    )

    order_intents = get_int(
        gate,
        "order_intents",
        0,
    )

    safety_valid = (
        safety.get("network_access") is False
        and safety.get("order_creation") is False
        and safety.get("order_submission") is False
        and safety.get("order_execution") is False
        and safety.get("production_db_write") is False
    )

    return {
        "runtime_valid": runtime_valid,
        "artifact_valid": artifact_valid,
        "execution_allowed": execution_allowed,
        "order_intents": order_intents,
        "safety_valid": safety_valid,
    }


def validate_replay(
    report: dict[str, Any],
) -> dict[str, Any]:

    artifact = get_dict(
        report,
        "artifact_contract",
    )

    path = get_dict(
        report,
        "eligible_signal_path",
    )

    safety = get_dict(
        report,
        "execution_safety",
    )

    if artifact is None:
        raise ValueError(
            "REPLAY_ARTIFACT_CONTRACT_MISSING"
        )

    if path is None:
        raise ValueError(
            "REPLAY_ELIGIBLE_SIGNAL_PATH_MISSING"
        )

    if safety is None:
        raise ValueError(
            "REPLAY_EXECUTION_SAFETY_MISSING"
        )

    artifact_valid = (
        artifact.get("contract") is True
        and artifact.get("verified") is True
    )

    eligible_signals = get_int(
        path,
        "eligible_signals",
        0,
    )

    order_intents = get_int(
        path,
        "order_intents",
        0,
    )

    path_verified = (
        path.get("path_verified") is True
    )

    replay_performed = (
        path.get("replay_performed") is True
    )

    safety_valid = (
        safety.get("execution_allowed") is False
        and safety.get("order_creation") is False
        and safety.get("order_submission") is False
        and safety.get("order_execution") is False
        and safety.get("network_access") is False
        and safety.get("production_db_write") is False
    )

    return {
        "artifact_valid": artifact_valid,
        "eligible_signals": eligible_signals,
        "order_intents": order_intents,
        "path_verified": path_verified,
        "replay_performed": replay_performed,
        "safety_valid": safety_valid,
    }


def build_report(
    gate: dict[str, Any],
    preflight: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:

    eligible_signals = replay[
        "eligible_signals"
    ]

    order_intents = gate[
        "order_intents"
    ]

    no_eligible_signal = (
        eligible_signals == 0
    )

    no_order_intents = (
        order_intents == 0
    )

    gate_ready = (
        gate["runtime_contract_valid"]
        and gate["artifact_contract_valid"]
        and gate["safety_contract_valid"]
        and gate["execution_allowed"] is False
    )

    preflight_ready = (
        preflight["runtime_valid"]
        and preflight["artifact_valid"]
        and preflight["safety_valid"]
        and preflight["execution_allowed"] is False
    )

    replay_ready = (
        replay["artifact_valid"]
        and replay["safety_valid"]
    )

    if (
        gate_ready
        and preflight_ready
        and replay_ready
        and no_eligible_signal
        and no_order_intents
    ):
        status = "READY_NO_ELIGIBLE_SIGNALS"
        verdict = (
            "LIVE_SIGNAL_ORDER_INTENT_RELEASE_PREFLIGHT_READY"
        )
        next_stage = "WAIT_FOR_ELIGIBLE_SIGNAL"

    elif (
        gate_ready
        and preflight_ready
        and replay_ready
        and not no_eligible_signal
    ):
        status = "ELIGIBLE_SIGNAL_PRESENT"
        verdict = (
            "LIVE_SIGNAL_ORDER_INTENT_RELEASE_PREFLIGHT_BLOCKED"
        )
        next_stage = (
            "ELIGIBLE_SIGNAL_ORDER_INTENT_RELEASE_VALIDATION"
        )

    else:
        status = "BLOCKED_CONTRACT"
        verdict = (
            "LIVE_SIGNAL_ORDER_INTENT_RELEASE_PREFLIGHT_BLOCKED"
        )
        next_stage = "REPAIR_UPSTREAM_CONTRACT"

    return {
        "project": "ARUNDA TRADER",

        "component": (
            "LIVE SIGNAL ORDER-INTENT "
            "RELEASE PREFLIGHT"
        ),

        "version": "v0.1",

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
            "replay_execution": False,
            "operational_safety": True,
        },

        "sources": {
            "gate": str(GATE_REPORT),
            "gate_sha256": sha256_file(GATE_REPORT),
            "preflight": str(PREFLIGHT_REPORT),
            "preflight_sha256": sha256_file(
                PREFLIGHT_REPORT
            ),
            "replay": str(REPLAY_REPORT),
            "replay_sha256": sha256_file(
                REPLAY_REPORT
            ),
        },

        "gate_contract": {
            "contract": gate[
                "runtime_contract_valid"
            ]
            and gate[
                "artifact_contract_valid"
            ],
            "runtime_contract": gate[
                "runtime_contract_valid"
            ],
            "artifact_contract": gate[
                "artifact_contract_valid"
            ],
            "safety_contract": gate[
                "safety_contract_valid"
            ],
            "execution_allowed": False,
            "order_intents": order_intents,
        },

        "preflight_contract": {
            "contract": (
                preflight["runtime_valid"]
                and preflight["artifact_valid"]
                and preflight["safety_valid"]
            ),
            "runtime_contract": preflight[
                "runtime_valid"
            ],
            "artifact_contract": preflight[
                "artifact_valid"
            ],
            "safety_contract": preflight[
                "safety_valid"
            ],
            "execution_allowed": False,
            "order_intents": preflight[
                "order_intents"
            ],
        },

        "replay_contract": {
            "contract": replay[
                "artifact_valid"
            ],
            "artifact_contract": replay[
                "artifact_valid"
            ],
            "eligible_signals": eligible_signals,
            "order_intents": replay[
                "order_intents"
            ],
            "path_verified": replay[
                "path_verified"
            ],
            "replay_performed": replay[
                "replay_performed"
            ],
            "safety_contract": replay[
                "safety_valid"
            ],
        },

        "release_preflight": {
            "status": status,
            "eligible_signals": eligible_signals,
            "order_intents": order_intents,
            "release_allowed": False,
            "execution_allowed": False,
            "order_creation_allowed": False,
            "order_submission_allowed": False,
            "network_access": False,
            "production_db_write": False,
        },

        "execution": {
            "executed": False,
            "orders_created": 0,
            "orders_submitted": 0,
        },

        "final_verdict": verdict,

        "next_stage": next_stage,
    }


def print_report(
    report: dict[str, Any],
) -> None:

    release = report[
        "release_preflight"
    ]

    gate = report[
        "gate_contract"
    ]

    preflight = report[
        "preflight_contract"
    ]

    replay = report[
        "replay_contract"
    ]

    execution = report[
        "execution"
    ]

    print("=" * 100)
    print("ARUNDA TRADER")
    print(
        "LIVE SIGNAL ORDER-INTENT "
        "RELEASE PREFLIGHT v0.1"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT        : {PROJECT_ROOT}"
    )

    print(
        f"UPSTREAM GATE       : {GATE_REPORT}"
    )

    print(
        f"UPSTREAM PREFLIGHT  : {PREFLIGHT_REPORT}"
    )

    print(
        f"UPSTREAM REPLAY     : {REPLAY_REPORT}"
    )

    print(
        f"OUTPUT REPORT       : {OUTPUT_REPORT}"
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

    print("=" * 100)
    print("UPSTREAM CONTRACTS")
    print("=" * 100)

    print(
        f"Gate runtime contract  : "
        f"{gate['runtime_contract']}"
    )

    print(
        f"Gate artifact contract : "
        f"{gate['artifact_contract']}"
    )

    print(
        f"Gate safety contract   : "
        f"{gate['safety_contract']}"
    )

    print(
        f"Preflight runtime      : "
        f"{preflight['runtime_contract']}"
    )

    print(
        f"Preflight artifact     : "
        f"{preflight['artifact_contract']}"
    )

    print(
        f"Preflight safety       : "
        f"{preflight['safety_contract']}"
    )

    print(
        f"Replay artifact        : "
        f"{replay['artifact_contract']}"
    )

    print(
        f"Replay safety          : "
        f"{replay['safety_contract']}"
    )

    print("=" * 100)
    print("RELEASE PREFLIGHT")
    print("=" * 100)

    print(
        f"STATUS                  : "
        f"{release['status']}"
    )

    print(
        f"ELIGIBLE SIGNALS        : "
        f"{release['eligible_signals']}"
    )

    print(
        f"ORDER INTENTS           : "
        f"{release['order_intents']}"
    )

    print(
        f"RELEASE ALLOWED        : "
        f"{release['release_allowed']}"
    )

    print(
        f"EXECUTION ALLOWED      : "
        f"{release['execution_allowed']}"
    )

    print(
        f"ORDER CREATION         : "
        f"{release['order_creation_allowed']}"
    )

    print(
        f"ORDER SUBMISSION       : "
        f"{release['order_submission_allowed']}"
    )

    print(
        f"NETWORK ACCESS         : "
        f"{release['network_access']}"
    )

    print(
        f"PRODUCTION DB WRITE    : "
        f"{release['production_db_write']}"
    )

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)

    print(
        f"RELEASE PREFLIGHT      : "
        f"{report['final_verdict']}"
    )

    print(
        f"EXECUTION              : "
        f"{execution['executed']}"
    )

    print(
        f"ORDERS CREATED         : "
        f"{execution['orders_created']}"
    )

    print(
        f"ORDERS SUBMITTED       : "
        f"{execution['orders_submitted']}"
    )

    print(
        f"NEXT STAGE             : "
        f"{report['next_stage']}"
    )

    print("=" * 100)

    print(
        f"REPORT WRITTEN         : "
        f"{OUTPUT_REPORT}"
    )

    print("=" * 100)


def main() -> int:

    gate_report = load_json(
        GATE_REPORT
    )

    preflight_report = load_json(
        PREFLIGHT_REPORT
    )

    replay_report = load_json(
        REPLAY_REPORT
    )

    gate = validate_gate(
        gate_report
    )

    preflight = validate_preflight(
        preflight_report
    )

    replay = validate_replay(
        replay_report
    )

    report = build_report(
        gate,
        preflight,
        replay,
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