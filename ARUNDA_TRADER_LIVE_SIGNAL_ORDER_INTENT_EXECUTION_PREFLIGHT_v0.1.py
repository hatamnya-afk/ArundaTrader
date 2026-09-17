from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

UPSTREAM_GATE = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_EXECUTION_GATE_REPORT.json"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_EXECUTION_PREFLIGHT_REPORT.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Upstream report not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise TypeError("Upstream report root must be a JSON object.")

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


def require_bool(
    parent: dict[str, Any],
    key: str,
    expected: bool | None = None,
) -> bool:
    value = parent.get(key)

    if not isinstance(value, bool):
        raise TypeError(
            f"Contract field '{key}' must be bool, "
            f"got {type(value).__name__}."
        )

    if expected is not None and value is not expected:
        raise ValueError(
            f"Contract field '{key}' expected {expected}, got {value}."
        )

    return value


def require_int(
    parent: dict[str, Any],
    key: str,
) -> int:
    value = parent.get(key)

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            f"Contract field '{key}' must be int, "
            f"got {type(value).__name__}."
        )

    return value


def validate_gate(
    report: dict[str, Any],
) -> dict[str, Any]:

    safety = require_dict(report, "safety")
    runtime_contract = require_dict(report, "runtime_contract")
    artifact_contract = require_dict(report, "artifact_contract")
    execution_gate = require_dict(
        report,
        "execution_gate",
    )

    require_bool(
        runtime_contract,
        "contract",
        True,
    )

    require_bool(
        runtime_contract,
        "runtime_ready",
        True,
    )

    require_bool(
        runtime_contract,
        "upstream_verified",
        True,
    )

    require_bool(
        runtime_contract,
        "artifact_verified",
        True,
    )

    require_bool(
        runtime_contract,
        "operational_safety",
        True,
    )

    require_bool(
        artifact_contract,
        "contract",
        True,
    )

    require_bool(
        artifact_contract,
        "verified",
        True,
    )

    execution_allowed = execution_gate.get(
        "execution_allowed"
    )

    if not isinstance(execution_allowed, bool):
        raise TypeError(
            "execution_gate.execution_allowed must be bool."
        )

    if execution_allowed is not False:
        raise ValueError(
            "Execution preflight requires "
            "execution_allowed=False."
        )

    order_intents = execution_gate.get(
        "order_intents"
    )

    if isinstance(order_intents, list):
        intent_count = len(order_intents)
    else:
        intent_count = execution_gate.get(
            "order_intents_count",
            0,
        )

        if (
            isinstance(intent_count, bool)
            or not isinstance(intent_count, int)
        ):
            raise TypeError(
                "execution_gate.order_intents_count "
                "must be int."
            )

    network_access = require_bool(
        safety,
        "network_access",
        False,
    )

    order_creation = require_bool(
        safety,
        "order_creation",
        False,
    )

    order_submission = require_bool(
        safety,
        "order_submission",
        False,
    )

    order_execution = require_bool(
        safety,
        "order_execution",
        False,
    )

    production_db_write = require_bool(
        safety,
        "production_db_write",
        False,
    )

    if intent_count == 0:
        status = "READY_NO_ORDER_INTENTS"
        verdict = "LIVE_SIGNAL_ORDER_INTENT_EXECUTION_PREFLIGHT_READY"
        next_stage = "WAIT_FOR_ELIGIBLE_SIGNAL"
    else:
        status = "BLOCKED_EXECUTION_DISABLED"
        verdict = "LIVE_SIGNAL_ORDER_INTENT_EXECUTION_PREFLIGHT_BLOCKED"
        next_stage = "EXECUTION_REMAINS_DISABLED"

    return {
        "status": status,
        "verdict": verdict,
        "next_stage": next_stage,
        "runtime_contract": {
            "contract": True,
            "runtime_ready": True,
            "upstream_verified": True,
            "artifact_verified": True,
            "operational_safety": True,
        },
        "artifact_contract": {
            "contract": True,
            "verified": True,
            "rows": artifact_contract.get("rows", 0),
            "eligible_rows": artifact_contract.get(
                "eligible_rows",
                0,
            ),
            "no_trade_rows": artifact_contract.get(
                "no_trade_rows",
                0,
            ),
            "decision": artifact_contract.get(
                "decision"
            ),
            "snapshot_id": artifact_contract.get(
                "snapshot_id"
            ),
        },
        "execution_gate": {
            "contract": True,
            "execution_allowed": False,
            "order_intents": intent_count,
        },
        "safety": {
            "network_access": network_access,
            "order_creation": order_creation,
            "order_submission": order_submission,
            "order_execution": order_execution,
            "production_db_write": production_db_write,
        },
    }


def build_report(
    gate: dict[str, Any],
    gate_sha256: str,
) -> dict[str, Any]:

    intent_count = gate["execution_gate"]["order_intents"]

    return {
        "project": "ARUNDA TRADER",
        "component": (
            "LIVE SIGNAL ORDER-INTENT EXECUTION PREFLIGHT"
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
            "operational_safety": True,
        },

        "source": {
            "execution_gate": str(UPSTREAM_GATE),
            "execution_gate_sha256": gate_sha256,
        },

        "runtime_contract": gate["runtime_contract"],

        "artifact_contract": gate["artifact_contract"],

        "execution_gate": {
            "contract": True,
            "verified": True,
            "execution_allowed": False,
            "order_intents": intent_count,
        },

        "preflight": {
            "status": gate["status"],
            "execution_allowed": False,
            "network_access": False,
            "order_creation": False,
            "order_submission": False,
            "order_execution": False,
            "production_db_write": False,
            "order_intents": intent_count,
        },

        "execution": {
            "executed": False,
            "orders_created": 0,
            "orders_submitted": 0,
        },

        "final_verdict": gate["verdict"],

        "next_stage": gate["next_stage"],
    }


def print_report(
    report: dict[str, Any],
) -> None:

    print("=" * 100)
    print(
        "ARUNDA TRADER"
    )
    print(
        "LIVE SIGNAL ORDER-INTENT EXECUTION PREFLIGHT v0.1"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT        : {PROJECT_ROOT}"
    )
    print(
        f"UPSTREAM GATE       : {UPSTREAM_GATE}"
    )
    print(
        f"OUTPUT REPORT       : {OUTPUT_REPORT}"
    )

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)

    safety = report["safety"]

    print(
        f"producer_execution     : "
        f"{safety['producer_execution']}"
    )
    print(
        f"producer_import        : "
        f"{safety['producer_import']}"
    )
    print(
        f"production_db_write    : "
        f"{safety['production_db_write']}"
    )
    print(
        f"network_access         : "
        f"{safety['network_access']}"
    )
    print(
        f"order_execution        : "
        f"{safety['order_execution']}"
    )
    print(
        f"order_creation         : "
        f"{safety['order_creation']}"
    )
    print(
        f"order_submission       : "
        f"{safety['order_submission']}"
    )
    print(
        f"artifact_mutation      : "
        f"{safety['artifact_mutation']}"
    )
    print(
        f"operational_safety     : "
        f"{safety['operational_safety']}"
    )

    print("=" * 100)
    print("RUNTIME CONTRACT")
    print("=" * 100)

    runtime = report["runtime_contract"]

    print(
        f"contract                : "
        f"{runtime['contract']}"
    )
    print(
        f"runtime_ready           : "
        f"{runtime['runtime_ready']}"
    )
    print(
        f"upstream_verified       : "
        f"{runtime['upstream_verified']}"
    )
    print(
        f"artifact_verified       : "
        f"{runtime['artifact_verified']}"
    )
    print(
        f"operational_safety      : "
        f"{runtime['operational_safety']}"
    )

    print("=" * 100)
    print("ARTIFACT CONTRACT")
    print("=" * 100)

    artifact = report["artifact_contract"]

    print(
        f"contract                : "
        f"{artifact['contract']}"
    )
    print(
        f"verified                : "
        f"{artifact['verified']}"
    )
    print(
        f"rows                    : "
        f"{artifact['rows']}"
    )
    print(
        f"eligible_rows           : "
        f"{artifact['eligible_rows']}"
    )
    print(
        f"no_trade_rows           : "
        f"{artifact['no_trade_rows']}"
    )
    print(
        f"decision                : "
        f"{artifact['decision']}"
    )
    print(
        f"snapshot_id             : "
        f"{artifact['snapshot_id']}"
    )

    print("=" * 100)
    print("EXECUTION GATE")
    print("=" * 100)

    execution_gate = report["execution_gate"]

    print(
        f"execution_allowed       : "
        f"{execution_gate['execution_allowed']}"
    )
    print(
        f"order_intents           : "
        f"{execution_gate['order_intents']}"
    )

    print("=" * 100)
    print("EXECUTION PREFLIGHT")
    print("=" * 100)

    preflight = report["preflight"]

    print(
        f"STATUS                  : "
        f"{preflight['status']}"
    )
    print(
        f"ORDER INTENTS           : "
        f"{preflight['order_intents']}"
    )
    print(
        f"EXECUTION ALLOWED       : "
        f"{preflight['execution_allowed']}"
    )
    print(
        f"ORDER CREATION          : "
        f"{preflight['order_creation']}"
    )
    print(
        f"ORDER SUBMISSION        : "
        f"{preflight['order_submission']}"
    )
    print(
        f"NETWORK ACCESS          : "
        f"{preflight['network_access']}"
    )
    print(
        f"PRODUCTION DB WRITE     : "
        f"{preflight['production_db_write']}"
    )

    print("=" * 100)
    print("FINAL PREFLIGHT VERDICT")
    print("=" * 100)

    print(
        f"EXECUTION PREFLIGHT     : "
        f"{report['final_verdict']}"
    )
    print(
        f"EXECUTION               : "
        f"{report['execution']['executed']}"
    )
    print(
        f"ORDERS CREATED          : "
        f"{report['execution']['orders_created']}"
    )
    print(
        f"ORDERS SUBMITTED        : "
        f"{report['execution']['orders_submitted']}"
    )
    print(
        f"NEXT STAGE              : "
        f"{report['next_stage']}"
    )

    print("=" * 100)
    print(
        f"REPORT WRITTEN          : "
        f"{OUTPUT_REPORT}"
    )
    print("=" * 100)


def main() -> int:

    try:
        gate_report = load_json(UPSTREAM_GATE)

        gate = validate_gate(gate_report)

        gate_sha256 = sha256_file(UPSTREAM_GATE)

        report = build_report(
            gate,
            gate_sha256,
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

    except Exception as exc:

        print("=" * 100)
        print(
            "ARUNDA TRADER"
        )
        print(
            "LIVE SIGNAL ORDER-INTENT EXECUTION PREFLIGHT v0.1"
        )
        print("=" * 100)
        print(
            "STATUS : CONTRACT_INVALID"
        )
        print(
            f"ERROR  : {exc}"
        )
        print("=" * 100)

        return 1


if __name__ == "__main__":
    raise SystemExit(main())