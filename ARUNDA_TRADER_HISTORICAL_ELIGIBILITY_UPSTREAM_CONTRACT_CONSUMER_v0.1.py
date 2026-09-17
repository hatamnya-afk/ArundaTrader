from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

RELEASE_GATE_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_RELEASE_GATE_FINAL_FORENSIC_REPORT.json"
)

ARTIFACT = (
    PROJECT_ROOT
    / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
)

OUTPUT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_UPSTREAM_CONTRACT_CONSUMER_REPORT.json"
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

EXPECTED_DECISION = "NO_TRADE"

EXPECTED_ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

EXPECTED_DIRECTIONS = [
    "FLAT",
    "SHORT",
    "FLAT",
    "FLAT",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require_file(path: Path, name: str):
    if not path.is_file():
        raise RuntimeError(
            f"Required upstream file is missing: {name}: {path}"
        )


def verify_release_gate(report: dict) -> dict:
    verification = report.get("verification")

    if not isinstance(verification, dict):
        verification = {}

    producer_identity = (
        verification.get("producer_identity")
        if "producer_identity" in verification
        else report.get("identity", {}).get("producer_identity")
    )

    artifact_identity = (
        verification.get("artifact_identity")
        if "artifact_identity" in verification
        else report.get("identity", {}).get("artifact_identity")
    )

    artifact_contract = verification.get(
        "artifact_contract"
    )

    production_db_contract = verification.get(
        "production_db_contract"
    )

    safety_contract = verification.get(
        "safety_contract"
    )

    chain_seal_contract = verification.get(
        "chain_seal_contract"
    )

    semantic_binding_contract = verification.get(
        "semantic_binding_contract"
    )

    runtime_identity_contract = verification.get(
        "runtime_identity_contract"
    )

    operational_safety = verification.get(
        "operational_safety"
    )

    release_gate_verified = verification.get(
        "release_gate_verified"
    )

    verdict = report.get("verdict")

    return {
        "producer_identity": producer_identity is True,
        "artifact_identity": artifact_identity is True,
        "artifact_contract": artifact_contract is True,
        "production_db_contract": production_db_contract is True,
        "safety_contract": safety_contract is True,
        "chain_seal_contract": chain_seal_contract is True,
        "semantic_binding_contract": semantic_binding_contract is True,
        "runtime_identity_contract": runtime_identity_contract is True,
        "operational_safety": operational_safety is True,
        "release_gate_verified": release_gate_verified is True,
        "verdict": verdict,
    }


def verify_release_gate_identity(report: dict) -> dict:
    identity = report.get("identity")

    if not isinstance(identity, dict):
        identity = {}

    producer_sha256 = identity.get(
        "producer_sha256"
    )

    artifact_sha256 = identity.get(
        "artifact_sha256"
    )

    chain_seal = report.get("chain_seal")

    if not isinstance(chain_seal, dict):
        chain_seal = {}

    chain_sha256 = chain_seal.get(
        "chain_sha256"
    )

    return {
        "producer_sha256": producer_sha256,
        "artifact_sha256": artifact_sha256,
        "chain_sha256": chain_sha256,
        "producer_hash_match": (
            producer_sha256 == EXPECTED_PRODUCER_SHA256
        ),
        "artifact_hash_match": (
            artifact_sha256 == EXPECTED_ARTIFACT_SHA256
        ),
        "chain_hash_match": (
            chain_sha256 == EXPECTED_CHAIN_SHA256
        ),
    }


def validate_artifact(artifact: dict) -> dict:
    row_results = artifact.get("row_results")

    if not isinstance(row_results, list):
        raise RuntimeError(
            "Artifact row_results is missing or invalid."
        )

    assets = []
    directions = []
    launch_rows = []

    for row in row_results:
        if not isinstance(row, dict):
            raise RuntimeError(
                "Artifact contains a non-object row."
            )

        asset = row.get("asset")
        direction = row.get("direction")
        reasons = row.get("reasons")

        if not isinstance(asset, str):
            raise RuntimeError(
                "Artifact row contains invalid asset."
            )

        if not isinstance(direction, str):
            raise RuntimeError(
                "Artifact row contains invalid direction."
            )

        if not isinstance(reasons, list):
            raise RuntimeError(
                "Artifact row contains invalid reasons."
            )

        assets.append(asset)
        directions.append(direction)

        launch_rows.append(
            {
                "asset": asset,
                "direction": direction,
                "eligible": False,
                "decision": EXPECTED_DECISION,
                "reasons": list(reasons),
            }
        )

    rows = artifact.get("rows")
    eligible_rows = artifact.get("eligible_rows")
    no_trade_rows = artifact.get("no_trade_rows")
    decision = artifact.get("decision")

    rows_contract = (
        isinstance(rows, int)
        and rows == len(row_results)
    )

    eligible_contract = (
        isinstance(eligible_rows, int)
        and eligible_rows == 0
    )

    no_trade_contract = (
        isinstance(no_trade_rows, int)
        and no_trade_rows == len(row_results)
    )

    decision_contract = (
        decision == EXPECTED_DECISION
    )

    asset_identity = (
        assets == EXPECTED_ASSETS
    )

    direction_identity = (
        directions == EXPECTED_DIRECTIONS
    )

    snapshot_identity = isinstance(
        artifact.get("snapshot_id"),
        str,
    )

    contract = all(
        [
            rows_contract,
            eligible_contract,
            no_trade_contract,
            decision_contract,
            asset_identity,
            direction_identity,
            snapshot_identity,
        ]
    )

    return {
        "contract": contract,
        "rows": len(row_results),
        "assets": assets,
        "directions": directions,
        "decision": decision,
        "snapshot_id": artifact.get("snapshot_id"),
        "launch_rows": launch_rows,
        "rows_contract": rows_contract,
        "eligible_contract": eligible_contract,
        "no_trade_contract": no_trade_contract,
        "decision_contract": decision_contract,
        "asset_identity": asset_identity,
        "direction_identity": direction_identity,
        "snapshot_identity": snapshot_identity,
    }


def build_upstream_contract(
    release_gate: dict,
    gate_identity: dict,
    artifact_info: dict,
    artifact_sha256: str,
) -> dict:

    return {
        "contract_name": (
            "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_UPSTREAM_CONTRACT"
        ),
        "contract_version": "v0.1",
        "status": "VERIFIED",
        "source": {
            "release_gate_report": str(
                RELEASE_GATE_REPORT
            ),
            "artifact": str(
                ARTIFACT
            ),
        },
        "identity": {
            "producer_sha256": gate_identity[
                "producer_sha256"
            ],
            "artifact_sha256": artifact_sha256,
            "chain_sha256": gate_identity[
                "chain_sha256"
            ],
        },
        "release_gate": release_gate,
        "eligibility": {
            "decision": artifact_info["decision"],
            "rows": artifact_info["rows"],
            "eligible_rows": 0,
            "no_trade_rows": artifact_info["rows"],
            "assets": artifact_info["assets"],
            "directions": artifact_info["directions"],
            "snapshot_id": artifact_info[
                "snapshot_id"
            ],
        },
        "downstream_contract": {
            "upstream_verified": True,
            "historical_evidence_verified": True,
            "decision_locked": True,
            "asset_identity_locked": True,
            "direction_identity_locked": True,
            "snapshot_identity_locked": True,
            "no_trade_execution_allowed": True,
            "production_db_write_allowed": False,
            "producer_execution_allowed": False,
            "producer_import_allowed": False,
            "network_access_required": False,
        },
        "launch_rows": artifact_info[
            "launch_rows"
        ],
    }


def main():
    print("=" * 80)
    print("ARUNDA TRADER")
    print(
        "HISTORICAL ELIGIBILITY "
        "UPSTREAM CONTRACT CONSUMER v0.1"
    )
    print("=" * 80)

    print(
        "PURPOSE:"
    )
    print(
        "Consume the VERIFIED Historical Eligibility "
        "Runtime Evidence Chain as an upstream contract."
    )

    print()
    print(
        "MODE                    : "
        "UPSTREAM CONTRACT CONSUMPTION"
    )
    print(
        "PRODUCER EXECUTION      : FORBIDDEN"
    )
    print(
        "PRODUCER IMPORT         : FORBIDDEN"
    )
    print(
        "PRODUCTION DB WRITE     : FORBIDDEN"
    )
    print(
        "NETWORK ACCESS          : FORBIDDEN"
    )
    print(
        "ORDER EXECUTION         : FORBIDDEN"
    )

    print("=" * 80)
    print("INPUTS")
    print("=" * 80)

    require_file(
        RELEASE_GATE_REPORT,
        "release gate report",
    )

    require_file(
        ARTIFACT,
        "eligibility artifact",
    )

    print(
        f"Release gate : {RELEASE_GATE_REPORT}"
    )

    print(
        f"Artifact     : {ARTIFACT}"
    )

    release_gate_report = load_json(
        RELEASE_GATE_REPORT
    )

    artifact = load_json(
        ARTIFACT
    )

    if not isinstance(
        release_gate_report,
        dict,
    ):
        raise RuntimeError(
            "Release gate report root is invalid."
        )

    if not isinstance(
        artifact,
        dict,
    ):
        raise RuntimeError(
            "Eligibility artifact root is invalid."
        )

    print("=" * 80)
    print("RELEASE GATE UPSTREAM CONTRACT")
    print("=" * 80)

    release_gate = verify_release_gate(
        release_gate_report
    )

    for key, value in release_gate.items():
        print(
            f"{key:32}: {value}"
        )

    print("=" * 80)
    print("RELEASE GATE IDENTITY")
    print("=" * 80)

    artifact_sha256 = sha256_file(
        ARTIFACT
    )

    gate_identity = verify_release_gate_identity(
        release_gate_report
    )

    print(
        "Producer SHA256 : "
        f"{gate_identity['producer_sha256']}"
    )

    print(
        "Expected        : "
        f"{EXPECTED_PRODUCER_SHA256}"
    )

    print(
        "Producer match  : "
        f"{gate_identity['producer_hash_match']}"
    )

    print(
        "Artifact SHA256 : "
        f"{artifact_sha256}"
    )

    print(
        "Expected        : "
        f"{EXPECTED_ARTIFACT_SHA256}"
    )

    print(
        "Artifact match  : "
        f"{artifact_sha256 == EXPECTED_ARTIFACT_SHA256}"
    )

    print(
        "Chain SHA256    : "
        f"{gate_identity['chain_sha256']}"
    )

    print(
        "Expected        : "
        f"{EXPECTED_CHAIN_SHA256}"
    )

    print(
        "Chain match     : "
        f"{gate_identity['chain_hash_match']}"
    )

    release_gate_identity_ok = all(
        [
            gate_identity["producer_hash_match"],
            gate_identity["artifact_hash_match"],
            gate_identity["chain_hash_match"],
        ]
    )

    print("=" * 80)
    print("ARTIFACT UPSTREAM CONTRACT")
    print("=" * 80)

    artifact_info = validate_artifact(
        artifact
    )

    for key in [
        "contract",
        "rows",
        "eligible_contract",
        "no_trade_contract",
        "decision_contract",
        "asset_identity",
        "direction_identity",
        "snapshot_identity",
    ]:
        if key in artifact_info:
            print(
                f"{key:28}: "
                f"{artifact_info[key]}"
            )

    print(
        f"assets     : {artifact_info['assets']}"
    )

    print(
        f"directions : {artifact_info['directions']}"
    )

    print(
        f"decision   : {artifact_info['decision']}"
    )

    upstream_gate_ok = all(
        [
            release_gate["release_gate_verified"],
            release_gate["producer_identity"],
            release_gate["artifact_identity"],
            release_gate["artifact_contract"],
            release_gate["production_db_contract"],
            release_gate["safety_contract"],
            release_gate["chain_seal_contract"],
            release_gate["semantic_binding_contract"],
            release_gate["runtime_identity_contract"],
            release_gate["operational_safety"],
            release_gate_identity_ok,
            artifact_info["contract"],
        ]
    )

    if not upstream_gate_ok:
        raise RuntimeError(
            "VERIFIED upstream contract rejected. "
            "Downstream launch package was not created."
        )

    print("=" * 80)
    print("BUILDING DOWNSTREAM LAUNCH CONTRACT")
    print("=" * 80)

    launch_contract = build_upstream_contract(
        release_gate,
        gate_identity,
        artifact_info,
        artifact_sha256,
    )

    launch_contract["status"] = (
        "VERIFIED_UPSTREAM_CONTRACT_READY"
    )

    launch_contract["next_stage"] = (
        "LIVE_SIGNAL_EXECUTION_GATE"
    )

    launch_contract["execution_state"] = (
        "NOT_EXECUTED"
    )

    launch_contract["orders_created"] = 0
    launch_contract["orders_submitted"] = 0

    with OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as handle:

        json.dump(
            launch_contract,
            handle,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )

        handle.write("\n")

    print()
    print(
        "UPSTREAM CONTRACT : VERIFIED"
    )

    print(
        "DOWNSTREAM PACKAGE: READY"
    )

    print(
        "EXECUTION         : NOT EXECUTED"
    )

    print(
        "ORDERS CREATED    : 0"
    )

    print(
        "ORDERS SUBMITTED  : 0"
    )

    print()
    print(
        f"OUTPUT : {OUTPUT}"
    )

    print("=" * 80)
    print("FINAL BUILD VERDICT")
    print("=" * 80)

    print(
        "HISTORICAL_ELIGIBILITY_UPSTREAM_CONTRACT : VERIFIED"
    )

    print(
        "LIVE_SIGNAL_DOWNSTREAM_CONTRACT          : READY"
    )

    print(
        "NEXT STAGE                               : "
        "LIVE_SIGNAL_EXECUTION_GATE"
    )


if __name__ == "__main__":
    main()