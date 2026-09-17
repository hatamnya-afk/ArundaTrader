import json
import hashlib
from pathlib import Path
from typing import Any


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

EXPECTED_GATE_VERDICT = "LIVE_SIGNAL_EXECUTION_GATE_READY"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"JSON root must be an object: {path}"
        )

    return data


def recursive_find(
    obj: Any,
    key: str,
    default=None,
):
    if isinstance(obj, dict):

        if key in obj:
            return obj[key]

        for value in obj.values():
            result = recursive_find(
                value,
                key,
                default,
            )

            if result is not default:
                return result

    elif isinstance(obj, list):

        for item in obj:
            result = recursive_find(
                item,
                key,
                default,
            )

            if result is not default:
                return result

    return default


def string_value(value: Any):
    if isinstance(value, str):
        return value.strip()

    return None


def bool_value(value: Any) -> bool:
    return value is True


def verify_identity(
    gate: dict,
    artifact_path: Path,
):
    producer_sha = recursive_find(
        gate,
        "producer_sha256",
        None,
    )

    artifact_sha = recursive_find(
        gate,
        "artifact_sha256",
        None,
    )

    chain_sha = recursive_find(
        gate,
        "chain_sha256",
        None,
    )

    producer_match = (
        producer_sha == EXPECTED_PRODUCER_SHA256
    )

    artifact_match = (
        artifact_sha == EXPECTED_ARTIFACT_SHA256
    )

    chain_match = (
        chain_sha == EXPECTED_CHAIN_SHA256
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
        "artifact_file_sha256": actual_artifact_sha,
        "artifact_file_match": artifact_file_match,
    }


def verify_gate_contract(gate: dict):
    producer_identity = recursive_find(
        gate,
        "producer_identity",
        None,
    )

    artifact_identity = recursive_find(
        gate,
        "artifact_identity",
        None,
    )

    artifact_contract = recursive_find(
        gate,
        "artifact_contract",
        None,
    )

    production_db_contract = recursive_find(
        gate,
        "production_db_contract",
        None,
    )

    safety_contract = recursive_find(
        gate,
        "safety_contract",
        None,
    )

    chain_seal_contract = recursive_find(
        gate,
        "chain_seal_contract",
        None,
    )

    semantic_binding_contract = recursive_find(
        gate,
        "semantic_binding_contract",
        None,
    )

    runtime_identity_contract = recursive_find(
        gate,
        "runtime_identity_contract",
        None,
    )

    operational_safety = recursive_find(
        gate,
        "operational_safety",
        None,
    )

    release_gate_verified = recursive_find(
        gate,
        "release_gate_verified",
        None,
    )

    verdict = recursive_find(
        gate,
        "final_verdict",
        None,
    )

    if verdict is None:
        verdict = recursive_find(
            gate,
            "verdict",
            None,
        )

    if release_gate_verified is None:
        release_gate_verified = recursive_find(
            gate,
            "verification",
            None,
        )

        if isinstance(release_gate_verified, dict):
            release_gate_verified = (
                release_gate_verified.get(
                    "execution_gate_ready"
                )
            )

    if producer_identity is None:
        producer_identity = recursive_find(
            gate,
            "producer_identity",
            False,
        )

    if artifact_identity is None:
        artifact_identity = recursive_find(
            gate,
            "artifact_identity",
            False,
        )

    if artifact_contract is None:
        artifact_contract = recursive_find(
            gate,
            "artifact_contract",
            False,
        )

    if production_db_contract is None:
        production_db_contract = recursive_find(
            gate,
            "production_db_contract",
            False,
        )

    if safety_contract is None:
        safety_contract = recursive_find(
            gate,
            "contract",
            False,
        )

    if chain_seal_contract is None:
        chain_seal_contract = recursive_find(
            gate,
            "chain_identity",
            False,
        )

    if semantic_binding_contract is None:
        semantic_binding_contract = recursive_find(
            gate,
            "upstream_contract_verified",
            False,
        )

    if runtime_identity_contract is None:
        runtime_identity_contract = recursive_find(
            gate,
            "artifact_identity_verified",
            False,
        )

    if operational_safety is None:
        operational_safety = recursive_find(
            gate,
            "operational_safety_verified",
            False,
        )

    producer_identity = bool_value(
        producer_identity
    )

    artifact_identity = bool_value(
        artifact_identity
    )

    artifact_contract = bool_value(
        artifact_contract
    )

    production_db_contract = bool_value(
        production_db_contract
    )

    safety_contract = bool_value(
        safety_contract
    )

    chain_seal_contract = bool_value(
        chain_seal_contract
    )

    semantic_binding_contract = bool_value(
        semantic_binding_contract
    )

    runtime_identity_contract = bool_value(
        runtime_identity_contract
    )

    operational_safety = bool_value(
        operational_safety
    )

    release_gate_verified = bool_value(
        release_gate_verified
    )

    verdict = string_value(verdict)

    identity_contract = all(
        [
            producer_identity,
            artifact_identity,
        ]
    )

    contracts_verified = all(
        [
            producer_identity,
            artifact_identity,
            artifact_contract,
            production_db_contract,
            safety_contract,
            chain_seal_contract,
            semantic_binding_contract,
            runtime_identity_contract,
            operational_safety,
        ]
    )

    release_verified = release_gate_verified

    verdict_verified = (
        verdict == EXPECTED_GATE_VERDICT
    )

    return {
        "producer_identity": producer_identity,
        "artifact_identity": artifact_identity,
        "artifact_contract": artifact_contract,
        "production_db_contract":
            production_db_contract,
        "safety_contract":
            safety_contract,
        "chain_seal_contract":
            chain_seal_contract,
        "semantic_binding_contract":
            semantic_binding_contract,
        "runtime_identity_contract":
            runtime_identity_contract,
        "operational_safety":
            operational_safety,
        "release_gate_verified":
            release_gate_verified,
        "verdict": verdict,
        "identity_contract":
            identity_contract,
        "contracts_verified":
            contracts_verified,
        "release_verified":
            release_verified,
        "verdict_verified":
            verdict_verified,
    }


def verify_artifact(
    artifact: dict,
):
    """
    Supports the actual artifact contract:

    {
        "artifact": {
            "assets": [...],
            "decision": "NO_TRADE",
            "directions": [...],
            "eligible_rows": 0,
            "no_trade_rows": 4,
            "rows": 4,
            "snapshot_id": "...",
            "verified": true
        }
    }
    """

    artifact_section = artifact.get(
        "artifact"
    )

    if not isinstance(
        artifact_section,
        dict,
    ):
        artifact_section = artifact

    rows = artifact_section.get(
        "rows",
        0,
    )

    eligible_rows = artifact_section.get(
        "eligible_rows",
        0,
    )

    no_trade_rows = artifact_section.get(
        "no_trade_rows",
        0,
    )

    decision = artifact_section.get(
        "decision"
    )

    assets = artifact_section.get(
        "assets",
        [],
    )

    directions = artifact_section.get(
        "directions",
        [],
    )

    snapshot_id = artifact_section.get(
        "snapshot_id"
    )

    verified = artifact_section.get(
        "verified"
    )

    if not isinstance(rows, int):
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

    structural_contract = all(
        [
            rows > 0,
            len(assets) == rows,
            len(directions) == rows,
            eligible_rows >= 0,
            no_trade_rows >= 0,
            eligible_rows + no_trade_rows == rows,
            decision in (
                "NO_TRADE",
                "TRADE",
                "EXECUTE",
            ),
            snapshot_id is not None,
        ]
    )

    explicit_contract = (
        verified is True
    )

    no_trade_contract = (
        decision == "NO_TRADE"
        and eligible_rows == 0
        and no_trade_rows == rows
    )

    contract = (
        explicit_contract
        and structural_contract
        and no_trade_contract
    )

    return {
        "contract": contract,
        "verified": explicit_contract,
        "rows": rows,
        "eligible_rows": eligible_rows,
        "no_trade_rows": no_trade_rows,
        "decision": decision,
        "assets": assets,
        "directions": directions,
        "snapshot_id": snapshot_id,
        "raw_artifact_contract": True,
        "structural_contract": structural_contract,
        "no_trade_contract": no_trade_contract,
    }


def build_runtime(
    gate_info: dict,
    identity: dict,
    artifact_info: dict,
):
    upstream_verified = all(
        [
            gate_info["contracts_verified"],
            gate_info["release_verified"],
            gate_info["verdict_verified"],
            gate_info["identity_contract"],
            identity["producer_match"],
            identity["artifact_match"],
            identity["chain_match"],
            identity["artifact_file_match"],
        ]
    )

    artifact_verified = (
        artifact_info["contract"]
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
        and artifact_info["eligible_rows"] > 0
        and artifact_info["decision"]
        not in (
            "NO_TRADE",
            None,
        )
    )

    orders_created = 0
    orders_submitted = 0

    if runtime_ready:
        execution = "NOT_EXECUTED"

        if (
            artifact_info["decision"]
            == "NO_TRADE"
        ):
            execution_reason = (
                "VALIDATED_NO_TRADE"
            )
        elif not execution_allowed:
            execution_reason = (
                "NO_ELIGIBLE_ROWS"
            )
        else:
            execution_reason = (
                "EXECUTION_NOT_ENABLED_IN_V0_1"
            )

    else:
        execution = "NOT_EXECUTED"

        execution_reason = (
            "UPSTREAM_OR_ARTIFACT_CONTRACT_INVALID"
        )

    return {
        "upstream_verified":
            upstream_verified,

        "artifact_verified":
            artifact_verified,

        "operational_safety":
            operational_safety,

        "runtime_ready":
            runtime_ready,

        "execution_allowed":
            execution_allowed,

        "execution":
            execution,

        "execution_reason":
            execution_reason,

        "orders_created":
            orders_created,

        "orders_submitted":
            orders_submitted,
    }


def main():
    print("=" * 80)
    print("ARUNDA TRADER")
    print("LIVE SIGNAL EXECUTION RUNTIME v0.1")
    print("=" * 80)

    print(
        f"PROJECT ROOT     : {PROJECT_ROOT}"
    )

    print(
        f"UPSTREAM GATE    : {UPSTREAM_GATE}"
    )

    print(
        f"UPSTREAM ARTIFACT: {UPSTREAM_ARTIFACT}"
    )

    print(
        f"OUTPUT REPORT    : {OUTPUT_REPORT}"
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
            f"Missing upstream gate: {UPSTREAM_GATE}"
        )

    if not UPSTREAM_ARTIFACT.exists():
        raise FileNotFoundError(
            f"Missing artifact: {UPSTREAM_ARTIFACT}"
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
        artifact
    )

    runtime = build_runtime(
        gate_info,
        identity,
        artifact_info,
    )

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

    print("=" * 80)
    print("BUILDING LIVE SIGNAL EXECUTION RUNTIME")
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

    if runtime["runtime_ready"]:
        final_verdict = (
            "LIVE_SIGNAL_EXECUTION_RUNTIME_READY"
        )

        next_stage = (
            "LIVE_SIGNAL_EXECUTION_RUNTIME_OPERATIONAL"
        )

    else:
        final_verdict = (
            "LIVE_SIGNAL_EXECUTION_RUNTIME_BLOCKED"
        )

        next_stage = (
            "UPSTREAM_CONTRACT_REPAIR"
        )

    report = {
        "project":
            "ARUNDA TRADER",

        "component":
            "LIVE SIGNAL EXECUTION RUNTIME",

        "version":
            "v0.1",

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
            "path":
                str(UPSTREAM_GATE),
            **gate_info,
        },

        "identity":
            identity,

        "artifact": {
            "path":
                str(UPSTREAM_ARTIFACT),
            **artifact_info,
        },

        "runtime":
            runtime,

        "execution": {
            "executed": False,
            "execution_allowed":
                runtime["execution_allowed"],
            "execution_reason":
                runtime["execution_reason"],
            "orders_created": 0,
            "orders_submitted": 0,
        },

        "final_verdict":
            final_verdict,

        "next_stage":
            next_stage,
    }

    OUTPUT_REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

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


if __name__ == "__main__":
    main()