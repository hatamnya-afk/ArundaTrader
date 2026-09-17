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
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise TypeError(f"JSON root must be dict: {path}")

    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def get_dict(
    parent: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    value = parent.get(key)

    if isinstance(value, dict):
        return value

    return {}


def find_value(
    obj: Any,
    key: str,
) -> Any:

    if isinstance(obj, dict):

        if key in obj:
            return obj[key]

        for value in obj.values():

            found = find_value(
                value,
                key,
            )

            if found is not None:
                return found

    elif isinstance(obj, list):

        for item in obj:

            found = find_value(
                item,
                key,
            )

            if found is not None:
                return found

    return None


def bool_value(
    obj: Any,
    key: str,
    default: bool = False,
) -> bool:

    value = find_value(
        obj,
        key,
    )

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

    if not runtime:
        raise ValueError(
            "Execution Gate runtime_contract missing."
        )

    if not artifact:
        raise ValueError(
            "Execution Gate artifact_contract missing."
        )

    if runtime.get("contract") is not True:
        raise ValueError(
            "Execution Gate runtime contract is not VERIFIED."
        )

    if artifact.get("contract") is not True:
        raise ValueError(
            "Execution Gate artifact contract is not VERIFIED."
        )

    safety = get_dict(
        report,
        "execution_safety",
    )

    execution_allowed = bool_value(
        report,
        "execution_allowed",
        False,
    )

    order_creation = bool_value(
        report,
        "order_creation",
        False,
    )

    order_submission = bool_value(
        report,
        "order_submission",
        False,
    )

    network_access = bool_value(
        report,
        "network_access",
        False,
    )

    production_db_write = bool_value(
        report,
        "production_db_write",
        False,
    )

    if execution_allowed:
        raise ValueError(
            "Execution Gate safety violation: "
            "execution_allowed must be False."
        )

    if order_creation:
        raise ValueError(
            "Execution Gate safety violation: "
            "order_creation must be False."
        )

    if order_submission:
        raise ValueError(
            "Execution Gate safety violation: "
            "order_submission must be False."
        )

    if network_access:
        raise ValueError(
            "Execution Gate safety violation: "
            "network_access must be False."
        )

    if production_db_write:
        raise ValueError(
            "Execution Gate safety violation: "
            "production_db_write must be False."
        )

    return {
        "runtime_contract": runtime,
        "artifact_contract": artifact,
        "execution_safety": safety,
        "execution_allowed": execution_allowed,
        "order_creation": order_creation,
        "order_submission": order_submission,
        "network_access": network_access,
        "production_db_write": production_db_write,
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

    if not runtime:
        raise ValueError(
            "Execution Preflight runtime_contract missing."
        )

    if not artifact:
        raise ValueError(
            "Execution Preflight artifact_contract missing."
        )

    if runtime.get("contract") is not True:
        raise ValueError(
            "Execution Preflight runtime contract is not VERIFIED."
        )

    if artifact.get("contract") is not True:
        raise ValueError(
            "Execution Preflight artifact contract is not VERIFIED."
        )

    execution_gate = get_dict(
        report,
        "execution_gate",
    )

    execution_allowed = bool_value(
        report,
        "execution_allowed",
        False,
    )

    order_creation = bool_value(
        report,
        "order_creation",
        False,
    )

    order_submission = bool_value(
        report,
        "order_submission",
        False,
    )

    network_access = bool_value(
        report,
        "network_access",
        False,
    )

    production_db_write = bool_value(
        report,
        "production_db_write",
        False,
    )

    if execution_allowed:
        raise ValueError(
            "Execution Preflight safety violation: "
            "execution_allowed must be False."
        )

    if order_creation:
        raise ValueError(
            "Execution Preflight safety violation: "
            "order_creation must be False."
        )

    if order_submission:
        raise ValueError(
            "Execution Preflight safety violation: "
            "order_submission must be False."
        )

    if network_access:
        raise ValueError(
            "Execution Preflight safety violation: "
            "network_access must be False."
        )

    if production_db_write:
        raise ValueError(
            "Execution Preflight safety violation: "
            "production_db_write must be False."
        )

    return {
        "runtime_contract": runtime,
        "artifact_contract": artifact,
        "execution_gate": execution_gate,
        "execution_allowed": execution_allowed,
        "order_creation": order_creation,
        "order_submission": order_submission,
        "network_access": network_access,
        "production_db_write": production_db_write,
    }


def validate_replay(
    report: dict[str, Any],
) -> dict[str, Any]:

    artifact = get_dict(
        report,
        "artifact_contract",
    )

    replay_path = get_dict(
        report,
        "eligible_signal_path",
    )

    replay_verification = get_dict(
        report,
        "replay_verification",
    )

    if not artifact:
        raise ValueError(
            "Replay Verification artifact_contract missing."
        )

    if not replay_path:
        raise ValueError(
            "Replay Verification eligible_signal_path missing."
        )

    if not replay_verification:
        raise ValueError(
            "Replay Verification replay_verification missing."
        )

    if artifact.get("contract") is not True:
        raise ValueError(
            "Replay artifact contract is not VERIFIED."
        )

    if artifact.get("verified") is not True:
        raise ValueError(
            "Replay artifact is not VERIFIED."
        )

    replay_verified = replay_verification.get(
        "verified"
    )

    if replay_verified is not True:
        raise ValueError(
            "Replay verification is not VERIFIED."
        )

    eligible_rows = artifact.get(
        "eligible_rows"
    )

    eligible_signals = replay_path.get(
        "eligible_signals"
    )

    order_intents = replay_path.get(
        "order_intents"
    )

    if not isinstance(
        eligible_rows,
        int,
    ):
        raise TypeError(
            "Replay eligible_rows must be int."
        )

    if not isinstance(
        eligible_signals,
        int,
    ):
        raise TypeError(
            "Replay eligible_signals must be int."
        )

    if not isinstance(
        order_intents,
        int,
    ):
        raise TypeError(
            "Replay order_intents must be int."
        )

    if eligible_rows != eligible_signals:
        raise ValueError(
            "Replay eligible count mismatch."
        )

    if eligible_rows == 0 and order_intents != 0:
        raise ValueError(
            "Zero eligible rows cannot have order intents."
        )

    return {
        "artifact_contract": artifact,
        "eligible_signal_path": replay_path,
        "replay_verification": replay_verification,

        # These remain validation outputs only.
        "eligible_rows": eligible_rows,
        "eligible_signals": eligible_signals,
        "order_intents": order_intents,
    }


def compare_artifacts(
    gate: dict[str, Any],
    preflight: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, bool]:

    gate_artifact = gate[
        "artifact_contract"
    ]

    preflight_artifact = preflight[
        "artifact_contract"
    ]

    replay_artifact = replay[
        "artifact_contract"
    ]

    checks = {
        "rows": (
            gate_artifact.get("rows")
            == preflight_artifact.get("rows")
            == replay_artifact.get("rows")
        ),

        "eligible_rows": (
            gate_artifact.get("eligible_rows")
            == preflight_artifact.get("eligible_rows")
            == replay_artifact.get("eligible_rows")
        ),

        "no_trade_rows": (
            gate_artifact.get("no_trade_rows")
            == preflight_artifact.get("no_trade_rows")
            == replay_artifact.get("no_trade_rows")
        ),

        "decision": (
            gate_artifact.get("decision")
            == preflight_artifact.get("decision")
            == replay_artifact.get("decision")
        ),

        "snapshot_id": (
            gate_artifact.get("snapshot_id")
            == preflight_artifact.get("snapshot_id")
            == replay_artifact.get("snapshot_id")
        ),
    }

    return checks


def build_report(
    gate: dict[str, Any],
    preflight: dict[str, Any],
    replay: dict[str, Any],
    artifact_checks: dict[str, bool],
) -> dict[str, Any]:

    # ==================================================================
    # CANONICAL DECISION BINDING
    # ==================================================================
    #
    # Release decision MUST bind to the canonical replay artifact.
    #
    # eligible_signal_path is validation-only and must NOT become the
    # decision source.
    #
    # ==================================================================

    artifact = replay[
        "artifact_contract"
    ]

    eligible_rows = artifact.get(
        "eligible_rows"
    )

    if not isinstance(
        eligible_rows,
        int,
    ):
        raise TypeError(
            "Canonical replay artifact eligible_rows must be int."
        )

    # order_intents is intentionally NOT invented from another field.
    #
    # The current canonical artifact contract does not expose
    # order_intents, therefore release preflight derives the zero-intent
    # state from the canonical eligible_rows state.
    #
    # This preserves the invariant:
    #
    #     eligible_rows == 0
    #     =>
    #     no eligible signal
    #     =>
    #     no order intent
    #
    # The replay path remains independently validated above.

    canonical_order_intents = (
        0
        if eligible_rows == 0
        else None
    )

    eligible_signals = eligible_rows

    order_intents = canonical_order_intents

    # ==================================================================
    # SAFETY
    # ==================================================================

    safety_ok = (
        gate["execution_allowed"] is False
        and gate["order_creation"] is False
        and gate["order_submission"] is False
        and gate["network_access"] is False
        and gate["production_db_write"] is False
        and preflight["execution_allowed"] is False
        and preflight["order_creation"] is False
        and preflight["order_submission"] is False
        and preflight["network_access"] is False
        and preflight["production_db_write"] is False
    )

    # ==================================================================
    # UPSTREAM CONTRACTS
    # ==================================================================

    upstream_ok = (
        gate["runtime_contract"].get("contract")
        is True

        and gate["artifact_contract"].get("contract")
        is True

        and preflight["runtime_contract"].get("contract")
        is True

        and preflight["artifact_contract"].get("contract")
        is True

        and replay["artifact_contract"].get("contract")
        is True

        and replay["artifact_contract"].get("verified")
        is True

        and replay["replay_verification"].get("verified")
        is True
    )

    # ==================================================================
    # ARTIFACT CHAIN
    # ==================================================================

    artifacts_match = all(
        artifact_checks.values()
    )

    # ==================================================================
    # CANONICAL ZERO-INTENT STATE
    # ==================================================================

    zero_intent_state = (
        eligible_rows == 0
        and canonical_order_intents == 0
    )

    release_allowed = False

    ready = (
        safety_ok
        and upstream_ok
        and artifacts_match
        and zero_intent_state
    )

    if ready:

        status = (
            "READY_NO_ORDER_INTENTS"
        )

        verdict = (
            "LIVE_SIGNAL_ORDER_INTENT_RELEASE_PREFLIGHT_READY"
        )

        next_stage = (
            "WAIT_FOR_ELIGIBLE_SIGNAL"
        )

    else:

        status = (
            "BLOCKED_CONTRACT"
        )

        verdict = (
            "LIVE_SIGNAL_ORDER_INTENT_RELEASE_PREFLIGHT_BLOCKED"
        )

        next_stage = (
            "REPAIR_UPSTREAM_CONTRACT"
        )

    return {
        "project": "ARUNDA TRADER",

        "component": (
            "LIVE SIGNAL ORDER-INTENT RELEASE PREFLIGHT"
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
        },

        "upstream_contracts": {
            "gate_runtime_contract": (
                gate["runtime_contract"].get("contract")
                is True
            ),

            "gate_artifact_contract": (
                gate["artifact_contract"].get("contract")
                is True
            ),

            "gate_safety_contract": safety_ok,

            "preflight_runtime_contract": (
                preflight["runtime_contract"].get("contract")
                is True
            ),

            "preflight_artifact_contract": (
                preflight["artifact_contract"].get("contract")
                is True
            ),

            "preflight_safety_contract": safety_ok,

            "replay_artifact_contract": (
                replay["artifact_contract"].get("contract")
                is True
                and replay["artifact_contract"].get("verified")
                is True
            ),

            "replay_verification": (
                replay["replay_verification"].get("verified")
                is True
            ),
        },

        # ==============================================================
        # CANONICAL ARTIFACT
        # ==============================================================

        "artifact_contract": {
            "contract": artifact.get(
                "contract"
            ),

            "verified": artifact.get(
                "verified"
            ),

            "rows": artifact.get(
                "rows"
            ),

            "eligible_rows": artifact.get(
                "eligible_rows"
            ),

            "no_trade_rows": artifact.get(
                "no_trade_rows"
            ),

            "decision": artifact.get(
                "decision"
            ),

            "snapshot_id": artifact.get(
                "snapshot_id"
            ),
        },

        # ==============================================================
        # RELEASE PREFLIGHT
        # ==============================================================

        "release_preflight": {
            "status": status,

            # IMPORTANT:
            # These values are bound to canonical artifact state.
            "eligible_signals": eligible_signals,

            "order_intents": order_intents,

            "release_allowed": release_allowed,

            "execution_allowed": False,

            "order_creation": False,

            "order_submission": False,

            "network_access": False,

            "production_db_write": False,

            "safety_verified": safety_ok,

            "upstream_verified": upstream_ok,

            "artifact_chain_match": artifacts_match,

            "canonical_binding": {
                "source": (
                    "replay.artifact_contract"
                ),

                "eligible_signals_source": (
                    "replay.artifact_contract.eligible_rows"
                ),

                "order_intents_source": (
                    "canonical_zero_eligible_state"
                ),

                "decision_source": (
                    "replay.artifact_contract"
                ),
            },
        },

        "artifact_consistency": artifact_checks,

        "execution": {
            "executed": False,
            "orders_created": 0,
            "orders_submitted": 0,
        },

        "final_verdict": verdict,

        "next_stage": next_stage,

        "sources": {
            "gate_report": str(
                GATE_REPORT
            ),

            "gate_report_sha256": sha256_file(
                GATE_REPORT
            ),

            "preflight_report": str(
                PREFLIGHT_REPORT
            ),

            "preflight_report_sha256": sha256_file(
                PREFLIGHT_REPORT
            ),

            "replay_report": str(
                REPLAY_REPORT
            ),

            "replay_report_sha256": sha256_file(
                REPLAY_REPORT
            ),
        },
    }


def main() -> int:

    print("=" * 100)
    print("ARUNDA TRADER")
    print(
        "LIVE SIGNAL ORDER-INTENT RELEASE PREFLIGHT v0.2"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )

    print(
        f"UPSTREAM GATE : {GATE_REPORT}"
    )

    print(
        f"UPSTREAM PREFLIGHT : {PREFLIGHT_REPORT}"
    )

    print(
        f"UPSTREAM REPLAY : {REPLAY_REPORT}"
    )

    print(
        f"OUTPUT REPORT : {OUTPUT_REPORT}"
    )

    print("=" * 100)

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

    artifact_checks = compare_artifacts(
        gate,
        preflight,
        replay,
    )

    report = build_report(
        gate,
        preflight,
        replay,
        artifact_checks,
    )

    with OUTPUT_REPORT.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

        f.write("\n")

    artifact = report[
        "artifact_contract"
    ]

    release = report[
        "release_preflight"
    ]

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)

    print(
        "producer_execution     : False"
    )

    print(
        "producer_import       : False"
    )

    print(
        "production_db_write   : False"
    )

    print(
        "network_access        : False"
    )

    print(
        "order_execution       : False"
    )

    print(
        "order_creation        : False"
    )

    print(
        "order_submission      : False"
    )

    print(
        "artifact_mutation     : False"
    )

    print("=" * 100)
    print("UPSTREAM CONTRACTS")
    print("=" * 100)

    print(
        "Gate runtime contract  : "
        f"{report['upstream_contracts']['gate_runtime_contract']}"
    )

    print(
        "Gate artifact contract : "
        f"{report['upstream_contracts']['gate_artifact_contract']}"
    )

    print(
        "Gate safety contract   : "
        f"{report['upstream_contracts']['gate_safety_contract']}"
    )

    print(
        "Preflight runtime      : "
        f"{report['upstream_contracts']['preflight_runtime_contract']}"
    )

    print(
        "Preflight artifact     : "
        f"{report['upstream_contracts']['preflight_artifact_contract']}"
    )

    print(
        "Preflight safety       : "
        f"{report['upstream_contracts']['preflight_safety_contract']}"
    )

    print(
        "Replay artifact        : "
        f"{report['upstream_contracts']['replay_artifact_contract']}"
    )

    print(
        "Replay verification    : "
        f"{report['upstream_contracts']['replay_verification']}"
    )

    print("=" * 100)
    print("CANONICAL ARTIFACT BINDING")
    print("=" * 100)

    print(
        "Decision source        : "
        "replay.artifact_contract"
    )

    print(
        "Eligible source        : "
        "replay.artifact_contract.eligible_rows"
    )

    print(
        "Order-intent source    : "
        "canonical_zero_eligible_state"
    )

    print("=" * 100)
    print("ARTIFACT")
    print("=" * 100)

    print(
        f"Rows                : "
        f"{artifact['rows']}"
    )

    print(
        f"Eligible rows       : "
        f"{artifact['eligible_rows']}"
    )

    print(
        f"No-trade rows       : "
        f"{artifact['no_trade_rows']}"
    )

    print(
        f"Decision            : "
        f"{artifact['decision']}"
    )

    print(
        f"Snapshot ID         : "
        f"{artifact['snapshot_id']}"
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
        f"RELEASE ALLOWED         : "
        f"{release['release_allowed']}"
    )

    print(
        f"EXECUTION ALLOWED       : "
        f"{release['execution_allowed']}"
    )

    print(
        f"ORDER CREATION          : "
        f"{release['order_creation']}"
    )

    print(
        f"ORDER SUBMISSION        : "
        f"{release['order_submission']}"
    )

    print(
        f"NETWORK ACCESS          : "
        f"{release['network_access']}"
    )

    print(
        f"PRODUCTION DB WRITE     : "
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
        f"{report['execution']['executed']}"
    )

    print(
        f"ORDERS CREATED         : "
        f"{report['execution']['orders_created']}"
    )

    print(
        f"ORDERS SUBMITTED       : "
        f"{report['execution']['orders_submitted']}"
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())