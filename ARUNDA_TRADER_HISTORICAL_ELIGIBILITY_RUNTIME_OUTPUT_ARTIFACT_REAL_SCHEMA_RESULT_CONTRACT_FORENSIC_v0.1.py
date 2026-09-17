# ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_REAL_SCHEMA_RESULT_CONTRACT_FORENSIC_v0.1.py

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER_PATH = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

ARTIFACT_PATH = (
    PROJECT_ROOT
    / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
)

REPORT_PATH = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_REAL_SCHEMA_RESULT_CONTRACT_FORENSIC_REPORT.json"
)

EXPECTED_ASSETS = ["BTC", "ETH", "SOL", "XRP"]
EXPECTED_RESULTS = ["NO_TRADE"] * 4


# =============================================================================
# SAFETY
# =============================================================================

SAFETY = {
    "producer_execution": False,
    "producer_import": False,
    "artifact_write": False,
    "artifact_delete": False,
    "production_db_write": False,
    "network_access": False,
}


# =============================================================================
# HELPERS
# =============================================================================

def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json_read_only(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, "FILE_NOT_FOUND"

    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def source_syntax(path: Path) -> tuple[bool, ast.AST | None, str | None]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        return True, tree, None
    except Exception as exc:
        return False, None, f"{type(exc).__name__}: {exc}"


def literal_value(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def node_source(source: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source, node)
    return segment if segment is not None else ""


def contains_name(node: ast.AST, names: set[str]) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in names:
            return True
    return False


def contains_string(node: ast.AST, values: set[str]) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Constant):
            if isinstance(child.value, str) and child.value in values:
                return True
    return False


def dict_keys(node: ast.AST) -> list[str]:
    if not isinstance(node, ast.Dict):
        return []

    keys = []

    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.append(key.value)

    return keys


def format_location(node: ast.AST) -> str:
    line = getattr(node, "lineno", "?")
    col = getattr(node, "col_offset", "?")
    return f"line={line}, col={col}"


# =============================================================================
# PRODUCER STATIC RESULT-CONTRACT DISCOVERY
# =============================================================================

def discover_result_contract(
    source: str,
    tree: ast.AST,
) -> dict[str, Any]:

    result_assignments = []
    result_dicts = []
    no_trade_constants = []
    row_result_builders = []
    report_builders = []

    for node in ast.walk(tree):

        # -------------------------------------------------------------
        # Assignments involving result
        # -------------------------------------------------------------
        if isinstance(node, (ast.Assign, ast.AnnAssign)):

            targets = []

            if isinstance(node, ast.Assign):
                for target in node.targets:
                    targets.append(target)

            elif isinstance(node, ast.AnnAssign):
                targets.append(node.target)

            for target in targets:
                if isinstance(target, ast.Name):
                    if target.id in {
                        "result",
                        "results",
                        "row_result",
                        "row_results",
                    }:
                        result_assignments.append(
                            {
                                "variable": target.id,
                                "location": format_location(node),
                                "source": node_source(source, node),
                            }
                        )

            value = (
                node.value
                if isinstance(node, (ast.Assign, ast.AnnAssign))
                else None
            )

            if isinstance(value, ast.Dict):
                keys = dict_keys(value)

                if "result" in keys:
                    result_dicts.append(
                        {
                            "location": format_location(node),
                            "keys": keys,
                            "source": node_source(source, node),
                        }
                    )

                if "row_results" in keys:
                    row_result_builders.append(
                        {
                            "location": format_location(node),
                            "keys": keys,
                            "source": node_source(source, node),
                        }
                    )

                if "no_trade_rows" in keys or "eligible_rows" in keys:
                    report_builders.append(
                        {
                            "location": format_location(node),
                            "keys": keys,
                            "source": node_source(source, node),
                        }
                    )

        # -------------------------------------------------------------
        # Literal NO_TRADE occurrences
        # -------------------------------------------------------------
        if isinstance(node, ast.Constant):
            if node.value == "NO_TRADE":
                no_trade_constants.append(
                    {
                        "location": format_location(node),
                        "source": node_source(source, node),
                    }
                )

    # -------------------------------------------------------------
    # Comparisons / semantic result generation
    # -------------------------------------------------------------
    comparisons = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            if contains_string(node, {"NO_TRADE", "TRADE_ELIGIBLE"}):
                comparisons.append(
                    {
                        "location": format_location(node),
                        "source": node_source(source, node),
                    }
                )

    # -------------------------------------------------------------
    # JSON serialization boundaries
    # -------------------------------------------------------------
    json_writers = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func

            name = None

            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id

            if name in {"dump", "dumps"}:
                json_writers.append(
                    {
                        "location": format_location(node),
                        "function": name,
                        "source": node_source(source, node),
                    }
                )

    return {
        "result_assignments": result_assignments,
        "result_dicts": result_dicts,
        "row_result_builders": row_result_builders,
        "report_builders": report_builders,
        "no_trade_constants": no_trade_constants,
        "comparisons": comparisons,
        "json_writers": json_writers,
    }


# =============================================================================
# REAL ARTIFACT SCHEMA
# =============================================================================

def inspect_artifact(artifact: Any) -> dict[str, Any]:

    info: dict[str, Any] = {
        "is_dict": isinstance(artifact, dict),
        "keys": [],
        "rows": None,
        "eligible_rows": None,
        "no_trade_rows": None,
        "decision": None,
        "snapshot_id": None,
        "row_results": [],
        "row_results_count": 0,
        "assets": [],
        "directions": [],
        "results": [],
        "reasons": [],
        "result_key_presence": [],
        "result_field_values": [],
        "no_trade_reason_count": 0,
        "production_db": None,
        "safety": None,
    }

    if not isinstance(artifact, dict):
        return info

    info["keys"] = sorted(artifact.keys())

    info["rows"] = artifact.get("rows")
    info["eligible_rows"] = artifact.get("eligible_rows")
    info["no_trade_rows"] = artifact.get("no_trade_rows")
    info["decision"] = artifact.get("decision")
    info["snapshot_id"] = artifact.get("snapshot_id")

    row_results = artifact.get("row_results")

    if isinstance(row_results, list):
        info["row_results"] = row_results
        info["row_results_count"] = len(row_results)

        for row in row_results:

            if not isinstance(row, dict):
                info["result_key_presence"].append(False)
                info["result_field_values"].append(None)
                continue

            info["assets"].append(row.get("asset"))
            info["directions"].append(row.get("direction"))

            has_result = "result" in row

            info["result_key_presence"].append(has_result)
            info["result_field_values"].append(row.get("result"))

            if has_result and row.get("result") is not None:
                info["results"].append(row.get("result"))

            reasons = row.get("reasons")

            if isinstance(reasons, list):
                info["reasons"].extend(reasons)

    production_db = artifact.get("production_db")

    if isinstance(production_db, dict):
        info["production_db"] = production_db

    safety = artifact.get("safety")

    if isinstance(safety, dict):
        info["safety"] = safety

    info["no_trade_reason_count"] = sum(
        1 for reason in info["reasons"] if reason == "CONFIDENCE_BELOW_GATE"
    )

    return info


# =============================================================================
# RESULT CONTRACT ANALYSIS
# =============================================================================

def analyze_result_contract(
    artifact_info: dict[str, Any],
    producer_contract: dict[str, Any],
) -> dict[str, Any]:

    row_results = artifact_info["row_results"]

    row_result_dicts = [
        row for row in row_results
        if isinstance(row, dict)
    ]

    result_key_count = sum(
        1 for present in artifact_info["result_key_presence"]
        if present
    )

    explicit_result_count = len(
        [
            value
            for value in artifact_info["result_field_values"]
            if value is not None
        ]
    )

    explicit_no_trade_count = sum(
        1
        for value in artifact_info["result_field_values"]
        if value == "NO_TRADE"
    )

    result_key_missing = [
        index + 1
        for index, present in enumerate(
            artifact_info["result_key_presence"]
        )
        if not present
    ]

    # -------------------------------------------------------------
    # Critical distinction:
    #
    # If artifact has no row-level "result" field but:
    #   decision == NO_TRADE
    #   eligible_rows == 0
    #   no_trade_rows == rows
    #
    # then the artifact uses an aggregate result contract.
    # -------------------------------------------------------------

    aggregate_result_contract = (
        artifact_info["decision"] == "NO_TRADE"
        and artifact_info["eligible_rows"] == 0
        and artifact_info["no_trade_rows"] == artifact_info["rows"]
    )

    row_result_contract = (
        len(row_result_dicts) == artifact_info["row_results_count"]
        and result_key_count == artifact_info["row_results_count"]
        and explicit_result_count == artifact_info["row_results_count"]
        and all(
            value == "NO_TRADE"
            for value in artifact_info["result_field_values"]
        )
    )

    return {
        "row_result_count": len(row_result_dicts),
        "result_key_count": result_key_count,
        "explicit_result_count": explicit_result_count,
        "explicit_no_trade_count": explicit_no_trade_count,
        "missing_result_key_rows": result_key_missing,
        "row_level_result_contract": row_result_contract,
        "aggregate_result_contract": aggregate_result_contract,
        "producer_has_result_dict": bool(
            producer_contract["result_dicts"]
        ),
        "producer_no_trade_literal_count": len(
            producer_contract["no_trade_constants"]
        ),
        "producer_result_assignments": len(
            producer_contract["result_assignments"]
        ),
        "producer_comparisons": len(
            producer_contract["comparisons"]
        ),
    }


# =============================================================================
# CORE RUNTIME CONTRACT
# =============================================================================

def verify_core_runtime_contract(
    artifact_info: dict[str, Any],
) -> dict[str, Any]:

    assets_ok = (
        artifact_info["assets"] == EXPECTED_ASSETS
    )

    rows_ok = (
        artifact_info["rows"] == len(EXPECTED_ASSETS)
        and artifact_info["row_results_count"] == len(EXPECTED_ASSETS)
    )

    eligible_ok = (
        artifact_info["eligible_rows"] == 0
    )

    no_trade_ok = (
        artifact_info["no_trade_rows"] == len(EXPECTED_ASSETS)
    )

    decision_ok = (
        artifact_info["decision"] == "NO_TRADE"
    )

    reasons_ok = (
        "CONFIDENCE_BELOW_GATE" in artifact_info["reasons"]
        and "WEAK_SIGNAL" in artifact_info["reasons"]
    )

    result_contract_ok = (
        artifact_info["decision"] == "NO_TRADE"
        and artifact_info["eligible_rows"] == 0
        and artifact_info["no_trade_rows"] == artifact_info["rows"]
    )

    return {
        "assets": assets_ok,
        "rows": rows_ok,
        "eligible_rows": eligible_ok,
        "no_trade_rows": no_trade_ok,
        "decision": decision_ok,
        "reasons": reasons_ok,
        "aggregate_result_contract": result_contract_ok,
        "core_contract": all(
            [
                assets_ok,
                rows_ok,
                eligible_ok,
                no_trade_ok,
                decision_ok,
                reasons_ok,
                result_contract_ok,
            ]
        ),
    }


# =============================================================================
# PRODUCTION DB CONTRACT
# =============================================================================

def verify_production_db(
    artifact_info: dict[str, Any],
) -> dict[str, Any]:

    production_db = artifact_info["production_db"]

    if not isinstance(production_db, dict):
        return {
            "exists": False,
            "before_after_present": False,
            "unchanged": False,
            "sha256_match": False,
            "contract": False,
        }

    before = production_db.get("before")
    after = production_db.get("after")

    before_ok = isinstance(before, dict)
    after_ok = isinstance(after, dict)

    unchanged = production_db.get("unchanged") is True

    sha_match = (
        before_ok
        and after_ok
        and before.get("sha256") == after.get("sha256")
        and before.get("size") == after.get("size")
        and before.get("rows") == after.get("rows")
    )

    return {
        "exists": True,
        "before_after_present": before_ok and after_ok,
        "unchanged": unchanged,
        "sha256_match": sha_match,
        "contract": (
            before_ok
            and after_ok
            and unchanged
            and sha_match
        ),
    }


# =============================================================================
# SAFETY CONTRACT
# =============================================================================

def verify_safety(
    artifact_info: dict[str, Any],
) -> dict[str, Any]:

    safety = artifact_info["safety"]

    if not isinstance(safety, dict):
        return {
            "exists": False,
            "production_db_modified": False,
            "order_execution": False,
            "synthetic_data": False,
            "engine_executed": False,
            "historical_repair": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "live_data_injection": False,
            "semantic_contract": False,
        }

    expected_false_keys = [
        "production_db_modified",
        "engine_executed",
        "historical_repair",
        "direction_inference",
        "score_reconstruction",
        "synthetic_data",
        "live_data_injection",
        "order_execution",
    ]

    values = {
        key: safety.get(key)
        for key in expected_false_keys
    }

    semantic_contract = all(
        value is False
        for value in values.values()
    )

    return {
        "exists": True,
        **values,
        "semantic_contract": semantic_contract,
    }


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 80)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY RUNTIME OUTPUT ARTIFACT")
    print("REAL SCHEMA / RESULT CONTRACT FORENSIC v0.1")
    print("=" * 80)

    print("PROJECT ROOT :", PROJECT_ROOT)
    print("PRODUCER     :", PRODUCER_PATH)
    print("ARTIFACT     :", ARTIFACT_PATH)

    print("=" * 80)
    print("SAFETY")
    print("=" * 80)

    for key, value in SAFETY.items():
        print(f"{key:22} : {value}")

    # -----------------------------------------------------------------
    # Producer static verification
    # -----------------------------------------------------------------

    producer_sha = sha256_file(PRODUCER_PATH)

    syntax_ok, producer_tree, syntax_error = source_syntax(
        PRODUCER_PATH
    )

    producer_source = (
        PRODUCER_PATH.read_text(encoding="utf-8")
        if PRODUCER_PATH.exists()
        else ""
    )

    producer_contract = {
        "result_assignments": [],
        "result_dicts": [],
        "row_result_builders": [],
        "report_builders": [],
        "no_trade_constants": [],
        "comparisons": [],
        "json_writers": [],
    }

    if syntax_ok and producer_tree is not None:
        producer_contract = discover_result_contract(
            producer_source,
            producer_tree,
        )

    # -----------------------------------------------------------------
    # Artifact
    # -----------------------------------------------------------------

    artifact_sha = sha256_file(ARTIFACT_PATH)

    artifact, artifact_error = load_json_read_only(
        ARTIFACT_PATH
    )

    artifact_info = inspect_artifact(artifact)

    # -----------------------------------------------------------------
    # Output
    # -----------------------------------------------------------------

    print("=" * 80)
    print("IDENTITY")
    print("=" * 80)

    print("Producer SHA256 :", producer_sha)
    print("Artifact SHA256 :", artifact_sha)
    print("Producer syntax :", syntax_ok)
    print("Artifact JSON   :", artifact_error is None)

    print("=" * 80)
    print("REAL ARTIFACT RESULT SCHEMA")
    print("=" * 80)

    print(
        "row_results count :",
        artifact_info["row_results_count"],
    )

    print(
        "result key count  :",
        sum(
            1
            for x in artifact_info["result_key_presence"]
            if x
        ),
    )

    print(
        "result values     :",
        artifact_info["result_field_values"],
    )

    print(
        "assets            :",
        artifact_info["assets"],
    )

    print(
        "directions        :",
        artifact_info["directions"],
    )

    print(
        "reasons           :",
        len(artifact_info["reasons"]),
    )

    print("=" * 80)
    print("PRODUCER RESULT-CONTRACT DISCOVERY")
    print("=" * 80)

    print(
        "result assignments :",
        len(producer_contract["result_assignments"]),
    )

    print(
        "result dicts       :",
        len(producer_contract["result_dicts"]),
    )

    print(
        "NO_TRADE literals  :",
        len(producer_contract["no_trade_constants"]),
    )

    print(
        "result comparisons :",
        len(producer_contract["comparisons"]),
    )

    print(
        "JSON writers       :",
        len(producer_contract["json_writers"]),
    )

    for item in producer_contract["result_dicts"]:
        print(
            f"RESULT DICT | {item['location']} | "
            f"keys={item['keys']}"
        )

    print("=" * 80)
    print("RESULT CONTRACT ANALYSIS")
    print("=" * 80)

    result_contract = analyze_result_contract(
        artifact_info,
        producer_contract,
    )

    for key, value in result_contract.items():
        print(f"{key:34} : {value}")

    print("=" * 80)
    print("CORE RUNTIME CONTRACT")
    print("=" * 80)

    core_contract = verify_core_runtime_contract(
        artifact_info
    )

    for key, value in core_contract.items():
        print(f"{key:34} : {value}")

    print("=" * 80)
    print("PRODUCTION DB CONTRACT")
    print("=" * 80)

    production_db_contract = verify_production_db(
        artifact_info
    )

    for key, value in production_db_contract.items():
        print(f"{key:34} : {value}")

    print("=" * 80)
    print("SAFETY CONTRACT")
    print("=" * 80)

    safety_contract = verify_safety(
        artifact_info
    )

    for key, value in safety_contract.items():
        print(f"{key:34} : {value}")

    # -----------------------------------------------------------------
    # Deterministic verdict
    # -----------------------------------------------------------------

    if not syntax_ok:
        verdict = "PRODUCER_STATIC_SCHEMA_DISCOVERY_FAILED"

    elif artifact_error is not None:
        verdict = "RUNTIME_ARTIFACT_UNREADABLE"

    elif not artifact_info["is_dict"]:
        verdict = "RUNTIME_ARTIFACT_TOP_LEVEL_SCHEMA_INVALID"

    elif (
        core_contract["core_contract"]
        and production_db_contract["contract"]
        and safety_contract["semantic_contract"]
    ):
        if result_contract["row_level_result_contract"]:
            verdict = (
                "RUNTIME_ARTIFACT_ROW_LEVEL_RESULT_CONTRACT_VERIFIED"
            )
        elif result_contract["aggregate_result_contract"]:
            verdict = (
                "RUNTIME_ARTIFACT_AGGREGATE_RESULT_CONTRACT_VERIFIED"
            )
        else:
            verdict = (
                "RUNTIME_ARTIFACT_RESULT_CONTRACT_UNRESOLVED"
            )

    else:
        verdict = (
            "RUNTIME_ARTIFACT_REAL_SCHEMA_RESULT_CONTRACT_FAILED"
        )

    print("=" * 80)
    print("FINAL DETERMINISTIC VERDICT")
    print("=" * 80)

    print(
        "HISTORICAL ELIGIBILITY RUNTIME EVIDENCE :",
        verdict,
    )

    # -----------------------------------------------------------------
    # Report
    #
    # This is the ONLY filesystem write performed by this script.
    # It is a forensic report, not a production artifact.
    # -----------------------------------------------------------------

    report = {
        "mode": "READ_ONLY_REAL_SCHEMA_RESULT_CONTRACT_FORENSIC",
        "project_root": str(PROJECT_ROOT),
        "producer": str(PRODUCER_PATH),
        "artifact": str(ARTIFACT_PATH),
        "producer_sha256": producer_sha,
        "artifact_sha256": artifact_sha,
        "producer_syntax_valid": syntax_ok,
        "artifact_valid_json": artifact_error is None,
        "artifact_error": artifact_error,
        "artifact_info": {
            "rows": artifact_info["rows"],
            "eligible_rows": artifact_info["eligible_rows"],
            "no_trade_rows": artifact_info["no_trade_rows"],
            "decision": artifact_info["decision"],
            "snapshot_id": artifact_info["snapshot_id"],
            "row_results_count": artifact_info["row_results_count"],
            "assets": artifact_info["assets"],
            "directions": artifact_info["directions"],
            "result_key_presence": artifact_info[
                "result_key_presence"
            ],
            "result_field_values": artifact_info[
                "result_field_values"
            ],
            "reason_count": len(artifact_info["reasons"]),
        },
        "producer_contract_discovery": producer_contract,
        "result_contract": result_contract,
        "core_runtime_contract": core_contract,
        "production_db_contract": production_db_contract,
        "safety_contract": safety_contract,
        "safety": SAFETY,
        "verdict": verdict,
    }

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as fh:
        json.dump(
            report,
            fh,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    print(
        "FORENSIC REPORT :",
        REPORT_PATH,
    )

    print("=" * 80)
    print("SAFETY FINAL")
    print("=" * 80)
    print("Producer executed : NO")
    print("Producer imported : NO")
    print("Artifact modified : NO")
    print("Artifact deleted  : NO")
    print("Production DB     : NO WRITE")
    print("Network           : NO")
    print("=" * 80)


if __name__ == "__main__":
    main()