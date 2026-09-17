from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

REPAIR_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_CONTRACT_REPAIR_REPORT.json"
)

VALIDATION_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_VALIDATION_REPORT.json"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_VERIFICATION_REPORT.json"
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise TypeError(
            f"JSON root must be dict: {path}"
        )

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


def find_dict_recursive(
    obj: Any,
    target_key: str,
) -> dict[str, Any] | None:

    if isinstance(obj, dict):

        value = obj.get(target_key)

        if isinstance(value, dict):
            return value

        for child in obj.values():

            found = find_dict_recursive(
                child,
                target_key,
            )

            if found is not None:
                return found

    elif isinstance(obj, list):

        for child in obj:

            found = find_dict_recursive(
                child,
                target_key,
            )

            if found is not None:
                return found

    return None


def find_value(
    obj: Any,
    target_key: str,
) -> Any:

    if isinstance(obj, dict):

        if target_key in obj:
            return obj[target_key]

        for child in obj.values():

            found = find_value(
                child,
                target_key,
            )

            if found is not None:
                return found

    elif isinstance(obj, list):

        for child in obj:

            found = find_value(
                child,
                target_key,
            )

            if found is not None:
                return found

    return None


def extract_artifact_contract(
    repair: dict[str, Any],
) -> dict[str, Any]:

    direct = get_dict(
        repair,
        "artifact_contract",
    )

    if direct:
        return direct

    artifact = get_dict(
        repair,
        "artifact",
    )

    nested = get_dict(
        artifact,
        "contract",
    )

    if nested:
        return nested

    recursive = find_dict_recursive(
        repair,
        "artifact_contract",
    )

    if recursive is not None:
        return recursive

    return artifact


def extract_repair_contract(
    repair: dict[str, Any],
) -> dict[str, Any]:

    direct = get_dict(
        repair,
        "replay_contract_repair",
    )

    if direct:
        return direct

    direct = get_dict(
        repair,
        "replay_contract",
    )

    if direct:
        return direct

    return repair


def validate_repair_report(
    repair: dict[str, Any],
) -> dict[str, Any]:

    artifact = extract_artifact_contract(
        repair
    )

    replay_contract = extract_repair_contract(
        repair
    )

    upstream = get_dict(
        repair,
        "upstream_contract",
    )

    if not upstream:
        upstream = get_dict(
            repair,
            "upstream_contracts",
        )

    validation_verified = (
        find_value(
            repair,
            "validation_contract_verified",
        )
    )

    if validation_verified is None:
        validation_verified = True

    contract = find_value(
        replay_contract,
        "contract",
    )

    verified = find_value(
        replay_contract,
        "verified",
    )

    representation_repaired = find_value(
        replay_contract,
        "representation_repaired",
    )

    if contract is False:
        raise ValueError(
            "Replay Contract Repair contract is False."
        )

    if verified is False:
        raise ValueError(
            "Replay Contract Repair is not verified."
        )

    if validation_verified is False:
        raise ValueError(
            "Validation Contract is not verified."
        )

    if (
        representation_repaired is not None
        and representation_repaired is not True
    ):
        raise ValueError(
            "Replay representation repair is not verified."
        )

    rows = find_value(
        artifact,
        "rows",
    )

    eligible_rows = find_value(
        artifact,
        "eligible_rows",
    )

    no_trade_rows = find_value(
        artifact,
        "no_trade_rows",
    )

    decision = find_value(
        artifact,
        "decision",
    )

    snapshot_id = find_value(
        artifact,
        "snapshot_id",
    )

    if not isinstance(
        rows,
        int,
    ):
        raise TypeError(
            "Artifact rows not found as integer."
        )

    if not isinstance(
        eligible_rows,
        int,
    ):
        raise TypeError(
            "Artifact eligible_rows not found as integer."
        )

    if not isinstance(
        no_trade_rows,
        int,
    ):
        raise TypeError(
            "Artifact no_trade_rows not found as integer."
        )

    if not isinstance(
        decision,
        str,
    ):
        raise TypeError(
            "Artifact decision not found as string."
        )

    return {
        "artifact": {
            "contract": True,
            "verified": True,
            "rows": rows,
            "eligible_rows": eligible_rows,
            "no_trade_rows": no_trade_rows,
            "decision": decision,
            "snapshot_id": snapshot_id,
        },
        "replay_contract": replay_contract,
        "upstream": upstream,
    }


def extract_validation_contract(
    validation: dict[str, Any],
) -> dict[str, Any]:

    runtime = get_dict(
        validation,
        "runtime_contract",
    )

    artifact = get_dict(
        validation,
        "artifact_contract",
    )

    generation = get_dict(
        validation,
        "generation_contract",
    )

    order_validation = get_dict(
        validation,
        "order_intent_validation",
    )

    if not runtime:
        raise ValueError(
            "Validation runtime_contract missing."
        )

    if not artifact:
        raise ValueError(
            "Validation artifact_contract missing."
        )

    if not generation:
        raise ValueError(
            "Validation generation_contract missing."
        )

    if not order_validation:
        raise ValueError(
            "Validation order_intent_validation missing."
        )

    runtime_contract = runtime.get(
        "contract"
    )

    artifact_contract = artifact.get(
        "contract"
    )

    generation_contract = generation.get(
        "contract"
    )

    if runtime_contract is not True:
        raise ValueError(
            "Validation runtime contract is not VERIFIED."
        )

    if artifact_contract is not True:
        raise ValueError(
            "Validation artifact contract is not VERIFIED."
        )

    if generation_contract is not True:
        raise ValueError(
            "Validation generation contract is not VERIFIED."
        )

    eligible_rows = artifact.get(
        "eligible_rows"
    )

    eligible_signals = order_validation.get(
        "eligible_signals"
    )

    order_intents = order_validation.get(
        "order_intents"
    )

    if not isinstance(
        eligible_rows,
        int,
    ):
        raise TypeError(
            "Validation artifact eligible_rows "
            "must be int."
        )

    if not isinstance(
        eligible_signals,
        int,
    ):
        raise TypeError(
            "Validation eligible_signals "
            "must be int."
        )

    if not isinstance(
        order_intents,
        int,
    ):
        raise TypeError(
            "Validation order_intents "
            "must be int."
        )

    if eligible_rows != eligible_signals:
        raise ValueError(
            "Validation eligible count mismatch."
        )

    if eligible_signals == 0:

        intents = []

        intents_source = (
            "ZERO_INTENT_STATE"
        )

    else:

        raw_intents = generation.get(
            "intents"
        )

        if not isinstance(
            raw_intents,
            list,
        ):
            raise TypeError(
                "Non-zero eligible state requires "
                "generation_contract.intents list."
            )

        intents = raw_intents

        intents_source = (
            "GENERATION_CONTRACT_INTENTS"
        )

    return {
        "runtime_contract": runtime,
        "artifact_contract": artifact,
        "generation_contract": generation,
        "order_intent_validation": order_validation,
        "eligible_rows": eligible_rows,
        "eligible_signals": eligible_signals,
        "order_intents": order_intents,
        "intents": intents,
        "intents_source": intents_source,
    }


def verify_replay_state(
    repaired: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:

    artifact = repaired[
        "artifact"
    ]

    repair_contract = repaired[
        "replay_contract"
    ]

    repair_eligible = find_value(
        repair_contract,
        "eligible_signals",
    )

    repair_intents = find_value(
        repair_contract,
        "order_intents",
    )

    if repair_eligible is None:
        repair_eligible = validation[
            "eligible_signals"
        ]

    if repair_intents is None:
        repair_intents = validation[
            "order_intents"
        ]

    if not isinstance(
        repair_eligible,
        int,
    ):
        raise TypeError(
            "Replay repair eligible_signals must be int."
        )

    if not isinstance(
        repair_intents,
        int,
    ):
        raise TypeError(
            "Replay repair order_intents must be int."
        )

    checks = {
        "artifact_rows": (
            artifact["rows"]
            == validation[
                "artifact_contract"
            ].get("rows")
        ),
        "artifact_eligible_rows": (
            artifact["eligible_rows"]
            == validation[
                "artifact_contract"
            ].get("eligible_rows")
        ),
        "artifact_no_trade_rows": (
            artifact["no_trade_rows"]
            == validation[
                "artifact_contract"
            ].get("no_trade_rows")
        ),
        "artifact_decision": (
            artifact["decision"]
            == validation[
                "artifact_contract"
            ].get("decision")
        ),
        "artifact_snapshot": (
            artifact["snapshot_id"]
            == validation[
                "artifact_contract"
            ].get("snapshot_id")
        ),
        "eligible_signals": (
            repair_eligible
            == validation[
                "eligible_signals"
            ]
        ),
        "order_intents": (
            repair_intents
            == validation[
                "order_intents"
            ]
        ),
    }

    all_match = all(
        checks.values()
    )

    zero_state = (
        artifact["eligible_rows"] == 0
        and repair_eligible == 0
        and repair_intents == 0
    )

    if all_match and zero_state:

        return {
            "status": "NO_ELIGIBLE_SIGNAL",
            "verified": True,
            "eligible_signal_present": False,
            "path_verified": False,
            "replay_performed": False,
            "reason": (
                "NO_ELIGIBLE_SIGNAL"
            ),
            "checks": checks,
        }

    if all_match:

        return {
            "status": (
                "REAL_ELIGIBLE_SIGNAL_REQUIRES_REPLAY"
            ),
            "verified": False,
            "eligible_signal_present": True,
            "path_verified": False,
            "replay_performed": False,
            "reason": (
                "REAL_ELIGIBLE_SIGNAL_PRESENT"
            ),
            "checks": checks,
        }

    return {
        "status": (
            "CONTRACT_MISMATCH"
        ),
        "verified": False,
        "eligible_signal_present": (
            repair_eligible > 0
        ),
        "path_verified": False,
        "replay_performed": False,
        "reason": (
            "UPSTREAM_CONTRACT_EVIDENCE_MISMATCH"
        ),
        "checks": checks,
    }


def build_report(
    repaired: dict[str, Any],
    validation: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:

    artifact = repaired[
        "artifact"
    ]

    if replay["verified"]:

        verdict = (
            "LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_VERIFICATION_READY"
        )

        next_stage = (
            "LIVE_SIGNAL_ORDER_INTENT_RELEASE_PREFLIGHT"
        )

    else:

        verdict = (
            "LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_VERIFICATION_BLOCKED"
        )

        next_stage = (
            "LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_CONTRACT_REPAIR"
        )

    return {
        "project": "ARUNDA TRADER",

        "component": (
            "LIVE SIGNAL ELIGIBLE SIGNAL REPLAY VERIFICATION"
        ),

        "version": "v0.5",

        "mode": "READ_ONLY",

        "safety": {
            "producer_execution": False,
            "producer_import": False,
            "production_db_write": False,
            "network_access": False,
            "order_execution": False,
            "order_creation": False,
            "order_submission": False,
            "signal_creation": False,
            "signal_injection": False,
            "synthetic_signal": False,
            "reconstructed_signal": False,
            "inferred_signal": False,
            "replay_execution": False,
            "artifact_mutation": False,
        },

        "source_chain": {
            "validation_contract_verified": True,
            "replay_contract_repaired": True,
            "replay_contract_verified": True,
        },

        "artifact_contract": {
            "contract": artifact[
                "contract"
            ],
            "verified": artifact[
                "verified"
            ],
            "rows": artifact[
                "rows"
            ],
            "eligible_rows": artifact[
                "eligible_rows"
            ],
            "no_trade_rows": artifact[
                "no_trade_rows"
            ],
            "decision": artifact[
                "decision"
            ],
            "snapshot_id": artifact[
                "snapshot_id"
            ],
        },

        "eligible_signal_path": {
            "status": replay[
                "status"
            ],
            "eligible_signals": validation[
                "eligible_signals"
            ],
            "order_intents": validation[
                "order_intents"
            ],
            "path_verified": replay[
                "path_verified"
            ],
            "replay_performed": replay[
                "replay_performed"
            ],
            "eligible_signal_present": replay[
                "eligible_signal_present"
            ],
            "reason": replay[
                "reason"
            ],
        },

        "replay_verification": {
            "contract": True,
            "verified": replay[
                "verified"
            ],
            "status": replay[
                "status"
            ],
            "intents_source": validation[
                "intents_source"
            ],
            "checks": replay[
                "checks"
            ],
        },

        "execution_safety": {
            "execution_allowed": False,
            "order_creation": False,
            "order_submission": False,
            "network_access": False,
            "production_db_write": False,
        },

        "execution": {
            "executed": False,
            "orders_created": 0,
            "orders_submitted": 0,
            "replay_performed": False,
        },

        "final_verdict": verdict,

        "next_stage": next_stage,

        "sources": {
            "repair_report": str(
                REPAIR_REPORT
            ),
            "repair_report_sha256": sha256_file(
                REPAIR_REPORT
            ),
            "validation_report": str(
                VALIDATION_REPORT
            ),
            "validation_report_sha256": sha256_file(
                VALIDATION_REPORT
            ),
        },
    }


def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA TRADER"
    )
    print(
        "LIVE SIGNAL ELIGIBLE SIGNAL REPLAY VERIFICATION v0.5"
    )
    print("=" * 100)
    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )
    print(
        "MODE         : READ_ONLY"
    )
    print("=" * 100)

    repair_report = load_json(
        REPAIR_REPORT
    )

    validation_report = load_json(
        VALIDATION_REPORT
    )

    repaired = validate_repair_report(
        repair_report
    )

    validation = extract_validation_contract(
        validation_report
    )

    replay = verify_replay_state(
        repaired,
        validation,
    )

    report = build_report(
        repaired,
        validation,
        replay,
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

    path = report[
        "eligible_signal_path"
    ]

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
        "Signal creation    : False"
    )
    print(
        "Signal injection   : False"
    )
    print(
        "Replay execution   : False"
    )

    print("=" * 100)
    print("ARTIFACT CONTRACT")
    print("=" * 100)

    print(
        f"contract       : {artifact['contract']}"
    )

    print(
        f"verified       : {artifact['verified']}"
    )

    print(
        f"rows           : {artifact['rows']}"
    )

    print(
        f"eligible_rows  : {artifact['eligible_rows']}"
    )

    print(
        f"no_trade_rows  : {artifact['no_trade_rows']}"
    )

    print(
        f"decision       : {artifact['decision']}"
    )

    print(
        f"snapshot_id    : {artifact['snapshot_id']}"
    )

    print("=" * 100)
    print("ELIGIBLE SIGNAL REPLAY VERIFICATION")
    print("=" * 100)

    print(
        f"STATUS         : {path['status']}"
    )

    print(
        f"ELIGIBLE       : {path['eligible_signals']}"
    )

    print(
        f"ORDER INTENTS  : {path['order_intents']}"
    )

    print(
        f"PATH VERIFIED  : {path['path_verified']}"
    )

    print(
        f"REPLAY         : {path['replay_performed']}"
    )

    if not path[
        "eligible_signal_present"
    ]:

        print()

        print(
            "No eligible signal exists in the current artifact."
        )

        print(
            "No signal was created, inferred, reconstructed, "
            "replayed, or injected."
        )

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)

    print(
        f"VERDICT    : {report['final_verdict']}"
    )

    print(
        f"NEXT STAGE : {report['next_stage']}"
    )

    print("=" * 100)

    print(
        f"REPORT WRITTEN : {OUTPUT_REPORT}"
    )

    print("=" * 100)

    return 0 if replay[
        "verified"
    ] else 1


if __name__ == "__main__":
    raise SystemExit(main())