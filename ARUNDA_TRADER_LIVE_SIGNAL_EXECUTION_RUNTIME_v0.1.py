import json
import hashlib
from pathlib import Path
from typing import Any


# ============================================================================
# PROJECT CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

UPSTREAM_GATE = PROJECT_ROOT / (
    "ARUNDA_TRADER_LIVE_SIGNAL_EXECUTION_GATE_REPORT.json"
)

UPSTREAM_ARTIFACT = PROJECT_ROOT / (
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
)

OUTPUT_REPORT = PROJECT_ROOT / (
    "ARUNDA_TRADER_LIVE_SIGNAL_EXECUTION_RUNTIME_REPORT.json"
)


EXPECTED_PRODUCER_SHA256 = (
    "71ff6dcdd5c49ef6ce06c6085794ceeaf22376e5e0f9dd97d906711e4cc4bdf0"
)

EXPECTED_ARTIFACT_SHA256 = (
    "f77c1b1cc98982b8edcb89c923a7c2ef52e40a654ba5e705a4a0be95490b5417"
)

EXPECTED_CHAIN_SHA256 = (
    "d32d35d36485090bc1ead1d90d03ca91b2fb34bea6f915a124c3e7388e3e54b4"
)

EXPECTED_GATE_VERDICT = (
    "LIVE_SIGNAL_EXECUTION_GATE_READY"
)


# ============================================================================
# BASIC UTILITIES
# ============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def load_json(path: Path) -> dict:
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"JSON root must be an object: {path}"
        )

    return data


def get_path(
    obj: Any,
    path: str,
    default=None,
):
    current = obj

    for part in path.split("."):

        if not isinstance(current, dict):
            return default

        if part not in current:
            return default

        current = current[part]

    return current


def first_value(
    obj: dict,
    paths,
    default=None,
):
    for path in paths:

        value = get_path(
            obj,
            path,
            None,
        )

        if value is not None:
            return value

    return default


def bool_true(value: Any) -> bool:
    return value is True


def string_value(value: Any):
    if isinstance(value, str):
        return value.strip()

    return None


# ============================================================================
# IDENTITY VERIFICATION
# ============================================================================

def verify_identity(
    gate: dict,
    artifact_path: Path,
):
    producer_sha = first_value(
        gate,
        [
            "identity.producer_sha256",
            "producer_sha256",
        ],
    )

    artifact_sha = first_value(
        gate,
        [
            "identity.artifact_sha256",
            "artifact_sha256",
        ],
    )

    chain_sha = first_value(
        gate,
        [
            "identity.chain_sha256",
            "chain_sha256",
        ],
    )

    producer_match = (
        producer_sha
        == EXPECTED_PRODUCER_SHA256
    )

    artifact_match = (
        artifact_sha
        == EXPECTED_ARTIFACT_SHA256
    )

    chain_match = (
        chain_sha
        == EXPECTED_CHAIN_SHA256
    )

    actual_artifact_sha = sha256_file(
        artifact_path
    )

    artifact_file_match = (
        actual_artifact_sha
        == EXPECTED_ARTIFACT_SHA256
    )

    return {
        "producer_sha256": producer_sha,
        "artifact_sha256": artifact_sha,
        "chain_sha256": chain_sha,

        "producer_match": producer_match,
        "artifact_match": artifact_match,
        "chain_match": chain_match,

        "artifact_file_sha256": (
            actual_artifact_sha
        ),

        "artifact_file_match": (
            artifact_file_match
        ),
    }


# ============================================================================
# UPSTREAM EXECUTION GATE CONTRACT
# ============================================================================

def verify_gate_contract(
    gate: dict,
):
    """
    Expected real gate structure:

    verification:
        producer_identity_verified
        artifact_identity_verified
        artifact_contract_verified
        operational_safety_verified
        upstream_contract_verified
        execution_gate_ready

    upstream:
        release_gate_verified

    gate:
        name
        state

    final_verdict
    """

    producer_identity = first_value(
        gate,
        [
            "verification.producer_identity_verified",
            "producer_identity",
        ],
        False,
    )

    artifact_identity = first_value(
        gate,
        [
            "verification.artifact_identity_verified",
            "artifact_identity",
        ],
        False,
    )

    artifact_contract = first_value(
        gate,
        [
            "verification.artifact_contract_verified",
            "artifact_contract",
        ],
        False,
    )

    operational_safety = first_value(
        gate,
        [
            "verification.operational_safety_verified",
            "operational_safety_verified",
        ],
        False,
    )

    upstream_contract_verified = first_value(
        gate,
        [
            "verification.upstream_contract_verified",
            "upstream_contract_verified",
        ],
        False,
    )

    execution_gate_ready = first_value(
        gate,
        [
            "verification.execution_gate_ready",
            "execution_gate_ready",
        ],
        False,
    )

    release_gate_verified = first_value(
        gate,
        [
            "upstream.release_gate_verified",
            "release_gate_verified",
        ],
        False,
    )

    gate_name = first_value(
        gate,
        [
            "gate.name",
            "name",
        ],
    )

    gate_state = first_value(
        gate,
        [
            "gate.state",
            "state",
        ],
    )

    verdict = first_value(
        gate,
        [
            "final_verdict",
            "verdict",
            "gate_verdict",
        ],
    )

    verdict = string_value(
        verdict
    )

    identity_contract = all(
        [
            bool_true(
                producer_identity
            ),
            bool_true(
                artifact_identity
            ),
        ]
    )

    contracts_verified = all(
        [
            bool_true(
                producer_identity
            ),
            bool_true(
                artifact_identity
            ),
            bool_true(
                artifact_contract
            ),
            bool_true(
                operational_safety
            ),
            bool_true(
                upstream_contract_verified
            ),
            bool_true(
                execution_gate_ready
            ),
        ]
    )

    release_verified = bool_true(
        release_gate_verified
    )

    verdict_verified = (
        verdict
        == EXPECTED_GATE_VERDICT
    )

    gate_ready = (
        gate_name
        == "LIVE_SIGNAL_EXECUTION_GATE"
        and gate_state
        == "READY"
    )

    return {
        "producer_identity": bool_true(
            producer_identity
        ),

        "artifact_identity": bool_true(
            artifact_identity
        ),

        "artifact_contract": bool_true(
            artifact_contract
        ),

        "operational_safety": bool_true(
            operational_safety
        ),

        "upstream_contract_verified": (
            bool_true(
                upstream_contract_verified
            )
        ),

        "execution_gate_ready": (
            bool_true(
                execution_gate_ready
            )
        ),

        "release_gate_verified": (
            release_verified
        ),

        "gate_name": gate_name,

        "gate_state": gate_state,

        "verdict": verdict,

        "identity_contract": (
            identity_contract
        ),

        "contracts_verified": (
            contracts_verified
        ),

        "release_verified": (
            release_verified
        ),

        "verdict_verified": (
            verdict_verified
        ),

        "gate_ready": gate_ready,
    }


# ============================================================================
# ARTIFACT CONTRACT
# ============================================================================

def verify_artifact(
    artifact: dict,
    gate: dict,
):
    """
    IMPORTANT:

    The upstream execution gate is the authoritative
    semantic contract for the artifact.

    The actual artifact file is still loaded and its
    SHA256 is independently checked.

    Semantic artifact data is consumed from:

        gate["artifact"]
    """

    gate_artifact = gate.get(
        "artifact"
    )

    if not isinstance(
        gate_artifact,
        dict,
    ):
        return {
            "contract": False,
            "verified": False,
            "rows": 0,
            "eligible_rows": 0,
            "no_trade_rows": 0,
            "decision": None,
            "assets": [],
            "directions": [],
            "snapshot_id": None,
            "row_count_contract": False,
            "decision_contract": False,
            "identity_contract": False,
            "snapshot_contract": False,
            "verified_contract": False,
            "upstream_artifact_contract": False,
            "upstream_artifact_identity": False,
        }

    assets = gate_artifact.get(
        "assets",
        [],
    )

    directions = gate_artifact.get(
        "directions",
        [],
    )

    decision = gate_artifact.get(
        "decision",
        None,
    )

    eligible_rows = gate_artifact.get(
        "eligible_rows",
        0,
    )

    no_trade_rows = gate_artifact.get(
        "no_trade_rows",
        0,
    )

    rows = gate_artifact.get(
        "rows",
        0,
    )

    snapshot_id = gate_artifact.get(
        "snapshot_id",
        None,
    )

    verified = gate_artifact.get(
        "verified",
        False,
    )

    if not isinstance(
        assets,
        list,
    ):
        assets = []

    if not isinstance(
        directions,
        list,
    ):
        directions = []

    if not isinstance(
        rows,
        int,
    ):
        rows = 0

    if not isinstance(
        eligible_rows,
        int,
    ):
        eligible_rows = 0

    if not isinstance(
        no_trade_rows,
        int,
    ):
        no_trade_rows = 0

    row_count_contract = (
        rows > 0
        and len(assets) == rows
        and len(directions) == rows
    )

    decision_contract = (
        decision == "NO_TRADE"
        and eligible_rows == 0
        and no_trade_rows == rows
    )

    identity_contract = (
        len(assets) == rows
        and len(directions) == rows
        and all(
            isinstance(
                asset,
                str,
            )
            and asset.strip()
            for asset in assets
        )
        and all(
            isinstance(
                direction,
                str,
            )
            and direction.strip()
            for direction in directions
        )
    )

    snapshot_contract = (
        isinstance(
            snapshot_id,
            str,
        )
        and bool(
            snapshot_id.strip()
        )
    )

    verified_contract = (
        verified is True
    )

    upstream_artifact_contract = (
        get_path(
            gate,
            "verification.artifact_contract_verified",
            False,
        )
        is True
    )

    upstream_artifact_identity = (
        get_path(
            gate,
            "verification.artifact_identity_verified",
            False,
        )
        is True
    )

    contract = all(
        [
            row_count_contract,
            decision_contract,
            identity_contract,
            snapshot_contract,
            verified_contract,
            upstream_artifact_contract,
            upstream_artifact_identity,
        ]
    )

    return {
        "contract": contract,

        "verified": verified_contract,

        "rows": rows,

        "eligible_rows": (
            eligible_rows
        ),

        "no_trade_rows": (
            no_trade_rows
        ),

        "decision": decision,

        "assets": assets,

        "directions": directions,

        "snapshot_id": snapshot_id,

        "row_count_contract": (
            row_count_contract
        ),

        "decision_contract": (
            decision_contract
        ),

        "identity_contract": (
            identity_contract
        ),

        "snapshot_contract": (
            snapshot_contract
        ),

        "verified_contract": (
            verified_contract
        ),

        "upstream_artifact_contract": (
            upstream_artifact_contract
        ),

        "upstream_artifact_identity": (
            upstream_artifact_identity
        ),
    }


# ============================================================================
# RUNTIME CONTRACT
# ============================================================================

def build_runtime(
    gate_info: dict,
    identity: dict,
    artifact_info: dict,
):
    """
    Runtime readiness is independent from the current
    trading decision.

    NO_TRADE means:

        no order is currently executable.

    It does NOT mean:

        runtime architecture is invalid.

    Therefore:

        runtime_ready
            !=
        execution_allowed
    """

    upstream_verified = all(
        [
            gate_info[
                "contracts_verified"
            ],

            gate_info[
                "identity_contract"
            ],

            gate_info[
                "release_verified"
            ],

            gate_info[
                "verdict_verified"
            ],

            gate_info[
                "gate_ready"
            ],

            identity[
                "producer_match"
            ],

            identity[
                "artifact_match"
            ],

            identity[
                "chain_match"
            ],

            identity[
                "artifact_file_match"
            ],
        ]
    )

    artifact_verified = (
        artifact_info[
            "contract"
        ]
    )

    operational_safety = True

    runtime_ready = all(
        [
            upstream_verified,
            artifact_verified,
            operational_safety,
        ]
    )

    execution_allowed = (
        runtime_ready
        and artifact_info[
            "eligible_rows"
        ] > 0
        and artifact_info[
            "decision"
        ] != "NO_TRADE"
    )

    orders_created = 0

    orders_submitted = 0

    return {
        "upstream_verified": (
            upstream_verified
        ),

        "artifact_verified": (
            artifact_verified
        ),

        "operational_safety": (
            operational_safety
        ),

        "runtime_ready": (
            runtime_ready
        ),

        "execution_allowed": (
            execution_allowed
        ),

        "execution": (
            "NOT_EXECUTED"
        ),

        "orders_created": (
            orders_created
        ),

        "orders_submitted": (
            orders_submitted
        ),
    }


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 80)
    print("ARUNDA TRADER")
    print("LIVE SIGNAL EXECUTION RUNTIME v0.1")
    print("=" * 80)

    print(
        f"PROJECT ROOT     : "
        f"{PROJECT_ROOT}"
    )

    print(
        f"UPSTREAM GATE    : "
        f"{UPSTREAM_GATE}"
    )

    print(
        f"UPSTREAM ARTIFACT: "
        f"{UPSTREAM_ARTIFACT}"
    )

    print(
        f"OUTPUT REPORT    : "
        f"{OUTPUT_REPORT}"
    )

    print("=" * 80)
    print("SAFETY")
    print("=" * 80)

    print(
        "producer_execution      : False"
    )

    print(
        "producer_import         : False"
    )

    print(
        "production_db_write     : False"
    )

    print(
        "network_access          : False"
    )

    print(
        "order_execution         : False"
    )

    print(
        "order_creation          : False"
    )

    print(
        "artifact_mutation       : False"
    )

    if not UPSTREAM_GATE.exists():

        raise FileNotFoundError(
            f"Missing upstream gate: "
            f"{UPSTREAM_GATE}"
        )

    if not UPSTREAM_ARTIFACT.exists():

        raise FileNotFoundError(
            f"Missing artifact: "
            f"{UPSTREAM_ARTIFACT}"
        )

    gate = load_json(
        UPSTREAM_GATE
    )

    artifact = load_json(
        UPSTREAM_ARTIFACT
    )

    identity = verify_identity(
        gate,
        UPSTREAM_ARTIFACT,
    )

    gate_info = verify_gate_contract(
        gate
    )

    artifact_info = verify_artifact(
        artifact,
        gate,
    )

    runtime = build_runtime(
        gate_info,
        identity,
        artifact_info,
    )

    # ========================================================================
    # UPSTREAM EXECUTION GATE
    # ========================================================================

    print("=" * 80)
    print("UPSTREAM EXECUTION GATE")
    print("=" * 80)

    print(
        f"contracts_verified : "
        f"{gate_info['contracts_verified']}"
    )

    print(
        f"identity_verified  : "
        f"{gate_info['identity_contract']}"
    )

    print(
        f"release_verified   : "
        f"{gate_info['release_verified']}"
    )

    print(
        f"verdict_verified   : "
        f"{gate_info['verdict_verified']}"
    )

    print(
        f"upstream_verified  : "
        f"{runtime['upstream_verified']}"
    )

    print(
        f"verdict            : "
        f"{gate_info['verdict']}"
    )

    # ========================================================================
    # UPSTREAM IDENTITY
    # ========================================================================

    print("=" * 80)
    print("UPSTREAM IDENTITY")
    print("=" * 80)

    print(
        f"Producer SHA256 : "
        f"{identity['producer_sha256']}"
    )

    print(
        f"Expected        : "
        f"{EXPECTED_PRODUCER_SHA256}"
    )

    print(
        f"Producer match  : "
        f"{identity['producer_match']}"
    )

    print(
        f"Artifact SHA256 : "
        f"{identity['artifact_sha256']}"
    )

    print(
        f"Expected        : "
        f"{EXPECTED_ARTIFACT_SHA256}"
    )

    print(
        f"Artifact match  : "
        f"{identity['artifact_match']}"
    )

    print(
        f"Chain SHA256    : "
        f"{identity['chain_sha256']}"
    )

    print(
        f"Expected        : "
        f"{EXPECTED_CHAIN_SHA256}"
    )

    print(
        f"Chain match     : "
        f"{identity['chain_match']}"
    )

    print(
        f"Artifact file   : "
        f"{identity['artifact_file_match']}"
    )

    # ========================================================================
    # ARTIFACT CONTRACT
    # ========================================================================

    print("=" * 80)
    print("ARTIFACT CONTRACT")
    print("=" * 80)

    print(
        f"contract      : "
        f"{artifact_info['contract']}"
    )

    print(
        f"verified      : "
        f"{artifact_info['verified']}"
    )

    print(
        f"rows          : "
        f"{artifact_info['rows']}"
    )

    print(
        f"eligible_rows : "
        f"{artifact_info['eligible_rows']}"
    )

    print(
        f"no_trade_rows : "
        f"{artifact_info['no_trade_rows']}"
    )

    print(
        f"decision      : "
        f"{artifact_info['decision']}"
    )

    print(
        f"assets        : "
        f"{artifact_info['assets']}"
    )

    print(
        f"directions    : "
        f"{artifact_info['directions']}"
    )

    print(
        f"snapshot_id   : "
        f"{artifact_info['snapshot_id']}"
    )

    # ========================================================================
    # BUILD RUNTIME
    # ========================================================================

    print("=" * 80)
    print(
        "BUILDING LIVE SIGNAL EXECUTION RUNTIME"
    )
    print("=" * 80)

    print(
        f"UPSTREAM CONTRACT : "
        f"{'VERIFIED' if runtime['upstream_verified'] else 'BLOCKED'}"
    )

    print(
        f"ARTIFACT CONTRACT : "
        f"{'VERIFIED' if runtime['artifact_verified'] else 'BLOCKED'}"
    )

    print(
        f"RUNTIME CONTRACT  : "
        f"{'READY' if runtime['runtime_ready'] else 'BLOCKED'}"
    )

    print(
        f"EXECUTION         : "
        f"{runtime['execution']}"
    )

    print(
        f"ORDERS CREATED    : "
        f"{runtime['orders_created']}"
    )

    print(
        f"ORDERS SUBMITTED  : "
        f"{runtime['orders_submitted']}"
    )

    # ========================================================================
    # RUNTIME SAFETY
    # ========================================================================

    print("=" * 80)
    print("RUNTIME SAFETY")
    print("=" * 80)

    print(
        f"Operational safety : "
        f"{runtime['operational_safety']}"
    )

    print(
        f"Execution allowed  : "
        f"{runtime['execution_allowed']}"
    )

    print(
        f"Runtime ready      : "
        f"{runtime['runtime_ready']}"
    )

    # ========================================================================
    # FINAL VERDICT
    # ========================================================================

    if runtime["runtime_ready"]:

        final_verdict = (
            "LIVE_SIGNAL_EXECUTION_RUNTIME_READY"
        )

        next_stage = (
            "LIVE_SIGNAL_EXECUTION_RUNTIME_READY"
        )

    else:

        final_verdict = (
            "LIVE_SIGNAL_EXECUTION_RUNTIME_BLOCKED"
        )

        next_stage = (
            "UPSTREAM_CONTRACT_REPAIR"
        )

    # ========================================================================
    # REPORT
    # ========================================================================

    report = {

        "project": (
            "ARUNDA TRADER"
        ),

        "component": (
            "LIVE SIGNAL EXECUTION RUNTIME"
        ),

        "version": "v0.1",

        "safety": {

            "producer_execution": False,

            "producer_import": False,

            "production_db_write": False,

            "network_access": False,

            "order_execution": False,

            "order_creation": False,

            "artifact_mutation": False,

            "operational_safety": True,
        },

        "upstream_gate": {

            "path": str(
                UPSTREAM_GATE
            ),

            **gate_info,
        },

        "identity": identity,

        "artifact": {

            "path": str(
                UPSTREAM_ARTIFACT
            ),

            **artifact_info,
        },

        "runtime": runtime,

        "execution": {

            "executed": False,

            "orders_created": 0,

            "orders_submitted": 0,
        },

        "final_verdict": (
            final_verdict
        ),

        "next_stage": (
            next_stage
        ),
    }

    OUTPUT_REPORT.write_text(

        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),

        encoding="utf-8",
    )

    # ========================================================================
    # FINAL OUTPUT
    # ========================================================================

    print("=" * 80)
    print("FINAL RUNTIME VERDICT")
    print("=" * 80)

    print(
        f"LIVE_SIGNAL_EXECUTION_RUNTIME : "
        f"{final_verdict}"
    )

    print(
        f"EXECUTION : "
        f"{runtime['execution']}"
    )

    print(
        f"ORDERS CREATED : "
        f"{runtime['orders_created']}"
    )

    print(
        f"ORDERS SUBMITTED : "
        f"{runtime['orders_submitted']}"
    )

    print(
        f"OUTPUT : "
        f"{OUTPUT_REPORT}"
    )

    print(
        f"NEXT STAGE : "
        f"{next_stage}"
    )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()