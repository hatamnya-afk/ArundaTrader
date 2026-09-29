"""CP49 static integration-order test. No runtime, DB, or exchange access."""

from __future__ import annotations

import ast
from pathlib import Path


PIPELINE = Path(__file__).resolve().parent / "arunda_pipeline.py"


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def main() -> None:
    tree = ast.parse(PIPELINE.read_text(encoding="utf-8-sig"))

    main_nodes = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    ]
    assert len(main_nodes) == 1

    calls: list[str] = []
    for node in ast.walk(main_nodes[0]):
        if isinstance(node, ast.Call):
            name = _call_name(node)
            if name in {
                "determine_decision",
                "issue_canonical_decision_id",
                "build_birth_identity_record",
                "require_production_decision_birth",
            }:
                calls.append(name)

    producer_path = Path(__file__).resolve().parent / (
        "cp49_production_decision_birth_producer_v0_1.py"
    )
    producer_tree = ast.parse(
        producer_path.read_text(encoding="utf-8-sig")
    )
    producer_calls = [
        _call_name(node)
        for node in ast.walk(producer_tree)
        if isinstance(node, ast.Call)
    ]

    assert "determine_decision" in calls
    assert "issue_canonical_decision_id" in calls
    assert calls.index("determine_decision") < calls.index(
        "issue_canonical_decision_id"
    )
    assert calls.index("issue_canonical_decision_id") < calls.index(
        "build_birth_identity_record"
    )
    assert calls.index("build_birth_identity_record") < calls.index(
        "require_production_decision_birth"
    )
    assert "persist_authoritative_birth" in producer_calls
    assert "persist_authoritative_birth" not in calls

    print("CP49_BIRTH_INTEGRATION_ORDER=PASS")
    print("SEMANTIC_DECISION_BEFORE_ID_ISSUANCE=PASS")
    print("ID_ISSUANCE_BEFORE_BIRTH_BINDING=PASS")
    print("BIRTH_PERSISTENCE_BEFORE_DOWNSTREAM_PROPAGATION=PASS")
    print("RUNTIME_EXECUTED=FALSE")
    print("PRODUCTION_DB_TOUCHED=FALSE")


if __name__ == "__main__":
    main()
