from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

VALIDATION_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_VALIDATION_REPORT.json"
)

REPLAY_CONSUMER = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_VERIFICATION_v0.1.py"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_VALIDATION_CONTRACT_FORENSICS_v0.4_REPORT.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise TypeError(
            f"JSON root must be dict, got {type(data).__name__}"
        )

    return data


def load_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return path.read_text(encoding="utf-8")


def safe_type(value: Any) -> str:
    if value is None:
        return "NoneType"

    if isinstance(value, bool):
        return "bool"

    if isinstance(value, int):
        return "int"

    if isinstance(value, float):
        return "float"

    if isinstance(value, str):
        return "str"

    if isinstance(value, list):
        return "list"

    if isinstance(value, dict):
        return "dict"

    return type(value).__name__


def ast_literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)

        if left:
            return f"{left}.{node.attr}"

        return node.attr

    return None


def extract_literal_contract_accesses(
    source: str,
) -> list[dict[str, Any]]:
    tree = ast.parse(source)

    accesses: list[dict[str, Any]] = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Subscript):
            base = dotted_name(node.value)

            key = None

            if isinstance(node.slice, ast.Constant):
                if isinstance(node.slice.value, str):
                    key = node.slice.value

            if base and key:
                accesses.append(
                    {
                        "kind": "subscript",
                        "base": base,
                        "key": key,
                        "line": node.lineno,
                        "column": node.col_offset,
                    }
                )

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "get":
                    base = dotted_name(node.func.value)

                    if base and node.args:
                        key = ast_literal(node.args[0])

                        if isinstance(key, str):
                            accesses.append(
                                {
                                    "kind": "get",
                                    "base": base,
                                    "key": key,
                                    "line": node.lineno,
                                    "column": node.col_offset,
                                }
                            )

    unique: dict[tuple[str, str, str], dict[str, Any]] = {}

    for item in accesses:
        identity = (
            item["kind"],
            item["base"],
            item["key"],
        )

        unique[identity] = item

    return sorted(
        unique.values(),
        key=lambda item: (
            item["line"],
            item["column"],
            item["kind"],
            item["base"],
            item["key"],
        ),
    )


def extract_required_literal_keys(
    accesses: list[dict[str, Any]],
) -> list[str]:
    keys = {
        item["key"]
        for item in accesses
        if isinstance(item.get("key"), str)
    }

    return sorted(keys)


def walk_json(
    value: Any,
    path: str = "$",
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    result.append(
        {
            "path": path,
            "exists": True,
            "type": safe_type(value),
        }
    )

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            result.extend(walk_json(child, child_path))

    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            result.extend(walk_json(child, child_path))

    return result


def find_paths_for_key(
    report: dict[str, Any],
    target_key: str,
) -> list[str]:
    paths: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():

                child_path = (
                    f"{path}.{key}"
                    if path != "$"
                    else f"$.{key}"
                )

                if key == target_key:
                    paths.append(child_path)

                visit(child, child_path)

        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(report, "$")

    return paths


def resolve_key_candidates(
    report: dict[str, Any],
    key: str,
) -> list[dict[str, Any]]:
    paths = find_paths_for_key(report, key)

    results: list[dict[str, Any]] = []

    for path in paths:
        current: Any = report

        try:
            parts = path[2:].split(".")

            for part in parts:
                if "[" in part:
                    name, remainder = part.split("[", 1)

                    if name:
                        current = current[name]

                    index = int(
                        remainder.rstrip("]")
                    )

                    current = current[index]

                else:
                    current = current[part]

            results.append(
                {
                    "path": path,
                    "exists": True,
                    "type": safe_type(current),
                    "value_preview": preview(current),
                }
            )

        except Exception:
            results.append(
                {
                    "path": path,
                    "exists": False,
                    "type": None,
                    "value_preview": None,
                }
            )

    return results


def preview(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: preview(child)
            for key, child in list(value.items())[:20]
        }

    if isinstance(value, list):
        return [
            preview(child)
            for child in value[:5]
        ]

    if isinstance(value, str):
        if len(value) > 200:
            return value[:200] + "..."

        return value

    return value


def classify_access(
    access: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    key = access["key"]

    candidates = resolve_key_candidates(
        report,
        key,
    )

    top_level_exists = key in report

    return {
        **access,
        "top_level_exists": top_level_exists,
        "actual_paths": candidates,
        "actual_path_count": len(candidates),
        "resolved_anywhere": len(candidates) > 0,
    }


def determine_exact_mismatch(
    classified: list[dict[str, Any]],
) -> dict[str, Any]:
    top_level_missing: list[dict[str, Any]] = []
    nested_exists: list[dict[str, Any]] = []
    completely_missing: list[dict[str, Any]] = []

    for item in classified:

        if item["top_level_exists"]:
            continue

        if item["resolved_anywhere"]:
            nested_exists.append(item)
        else:
            completely_missing.append(item)

        top_level_missing.append(item)

    if nested_exists:
        status = "NESTED_VS_TOP_LEVEL_REPRESENTATION_MISMATCH"
    elif completely_missing:
        status = "REQUIRED_FIELD_NOT_PRESENT"
    else:
        status = "NO_LITERAL_KEY_MISMATCH_DETECTED"

    return {
        "status": status,
        "top_level_missing_count": len(top_level_missing),
        "nested_exists_count": len(nested_exists),
        "completely_missing_count": len(completely_missing),
        "top_level_missing": top_level_missing,
        "nested_exists": nested_exists,
        "completely_missing": completely_missing,
    }


def build_report(
    validation: dict[str, Any],
    replay_source: str,
    accesses: list[dict[str, Any]],
) -> dict[str, Any]:

    classified = [
        classify_access(
            access,
            validation,
        )
        for access in accesses
    ]

    mismatch = determine_exact_mismatch(
        classified
    )

    top_level_keys = list(validation.keys())

    actual_structure = {
        "root_type": safe_type(validation),
        "top_level_keys": top_level_keys,
        "tree": walk_json(validation),
    }

    contract = {
        "consumer": str(REPLAY_CONSUMER),
        "consumer_sha256": sha256_file(REPLAY_CONSUMER),
        "literal_access_count": len(accesses),
        "literal_accesses": classified,
        "required_literal_keys": extract_required_literal_keys(
            accesses
        ),
    }

    if mismatch["status"] == "NO_LITERAL_KEY_MISMATCH_DETECTED":
        verdict = "NO_EXACT_LITERAL_MISMATCH"
        next_frontier = (
            "DEEP_REPLAY_CONTRACT_FORENSICS"
        )
    else:
        verdict = "MISMATCH_IDENTIFIED"
        next_frontier = (
            "MINIMUM_TARGETED_VALIDATION_CONTRACT_REPAIR"
        )

    return {
        "project": "ARUNDA TRADER",
        "component": (
            "LIVE SIGNAL ORDER-INTENT "
            "VALIDATION CONTRACT FORENSICS"
        ),
        "version": "v0.4",
        "mode": "READ_ONLY",

        "safety": {
            "database_write": False,
            "network_access": False,
            "producer_execution": False,
            "producer_import": False,
            "signal_creation": False,
            "signal_injection": False,
            "replay_execution": False,
            "artifact_mutation": False,
        },

        "sources": {
            "validation_report": str(
                VALIDATION_REPORT
            ),
            "validation_report_sha256": sha256_file(
                VALIDATION_REPORT
            ),
            "replay_consumer": str(
                REPLAY_CONSUMER
            ),
            "replay_consumer_sha256": sha256_file(
                REPLAY_CONSUMER
            ),
        },

        "actual_validation_report": actual_structure,

        "replay_consumer_contract": contract,

        "exact_contract_comparison": mismatch,

        "repair": {
            "performed": False,
            "minimum_targeted_repair": False,
            "reason": (
                "FORENSICS_ONLY; NO FILE MODIFICATION"
            ),
        },

        "final_verdict": verdict,

        "next_frontier": next_frontier,
    }


def print_report(report: dict[str, Any]) -> None:
    comparison = report[
        "exact_contract_comparison"
    ]

    print("=" * 100)
    print(
        "ARUNDA TRADER"
    )
    print(
        "LIVE SIGNAL ORDER-INTENT "
        "VALIDATION CONTRACT FORENSICS v0.4"
    )
    print("=" * 100)

    print("MODE              : READ_ONLY")
    print(
        f"VALIDATION REPORT : {VALIDATION_REPORT}"
    )
    print(
        f"REPLAY CONSUMER   : {REPLAY_CONSUMER}"
    )

    print("=" * 100)
    print("ACTUAL VALIDATION REPORT")
    print("=" * 100)

    actual = report[
        "actual_validation_report"
    ]

    print(
        f"ROOT TYPE         : {actual['root_type']}"
    )

    print(
        "TOP LEVEL KEYS    : "
        f"{actual['top_level_keys']}"
    )

    print("=" * 100)
    print("REPLAY CONSUMER ACTUAL LITERAL ACCESS")
    print("=" * 100)

    accesses = report[
        "replay_consumer_contract"
    ]["literal_accesses"]

    if not accesses:
        print(
            "NO_LITERAL_DICTIONARY_ACCESS_FOUND"
        )
    else:
        for item in accesses:
            print(
                f"LINE {item['line']:4d} | "
                f"{item['kind']:9s} | "
                f"{item['base']}[{item['key']!r}] | "
                f"TOP_LEVEL={item['top_level_exists']} | "
                f"RESOLVED_ANYWHERE={item['resolved_anywhere']}"
            )

    print("=" * 100)
    print("EXACT CONTRACT COMPARISON")
    print("=" * 100)

    print(
        "STATUS            : "
        f"{comparison['status']}"
    )

    print(
        "TOP LEVEL MISSING : "
        f"{comparison['top_level_missing_count']}"
    )

    print(
        "NESTED EXISTS     : "
        f"{comparison['nested_exists_count']}"
    )

    print(
        "COMPLETELY MISSING: "
        f"{comparison['completely_missing_count']}"
    )

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)

    print("DATABASE WRITE     : False")
    print("NETWORK ACCESS     : False")
    print("PRODUCER EXECUTION : False")
    print("SIGNAL CREATION    : False")
    print("SIGNAL INJECTION   : False")
    print("REPLAY EXECUTION   : False")

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)

    print(
        "VALIDATION CONTRACT FORENSICS : "
        f"{report['final_verdict']}"
    )

    print(
        "NEXT FRONTIER                  : "
        f"{report['next_frontier']}"
    )

    print("=" * 100)
    print(
        f"REPORT WRITTEN : {OUTPUT_REPORT}"
    )
    print("=" * 100)


def main() -> int:
    validation = load_json(
        VALIDATION_REPORT
    )

    replay_source = load_text(
        REPLAY_CONSUMER
    )

    accesses = extract_literal_contract_accesses(
        replay_source
    )

    report = build_report(
        validation,
        replay_source,
        accesses,
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


if __name__ == "__main__":
    raise SystemExit(main())