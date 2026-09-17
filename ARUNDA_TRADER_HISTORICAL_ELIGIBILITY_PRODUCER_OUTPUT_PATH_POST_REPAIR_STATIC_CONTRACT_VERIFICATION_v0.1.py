import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER_NAME = (
    "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

TARGET_REPORT = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

PRODUCER_PATH = PROJECT_ROOT / PRODUCER_NAME

FORENSIC_REPORT_PATH = (
    PROJECT_ROOT
    / "HISTORICAL_ELIGIBILITY_PRODUCER_OUTPUT_PATH_POST_REPAIR_STATIC_CONTRACT_VERIFICATION_REPORT.json"
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def syntax_check(source):
    try:
        tree = ast.parse(
            source,
            filename=str(PRODUCER_PATH),
        )
        return True, tree, None

    except SyntaxError as exc:
        return (
            False,
            None,
            {
                "line": exc.lineno,
                "column": exc.offset,
                "message": exc.msg,
                "text": exc.text,
            },
        )


def get_report_path_assignments(tree):
    assignments = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:

            if not isinstance(target, ast.Name):
                continue

            if target.id != "report_path":
                continue

            assignments.append(
                {
                    "line": node.lineno,
                    "end_line": getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                    "target": target.id,
                    "value_ast": node.value,
                    "expression": ast.unparse(node),
                }
            )

    assignments.sort(
        key=lambda x: (
            x["line"],
            x["end_line"],
        )
    )

    return assignments


def is_expected_deterministic_expression(value_ast):
    """
    Semantic AST verification.

    Expected:

        PROJECT_ROOT / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

    Quote style is intentionally ignored.
    """

    if not isinstance(value_ast, ast.BinOp):
        return False

    if not isinstance(value_ast.op, ast.Div):
        return False

    if not isinstance(value_ast.left, ast.Name):
        return False

    if value_ast.left.id != "PROJECT_ROOT":
        return False

    if not isinstance(value_ast.right, ast.Constant):
        return False

    if value_ast.right.value != TARGET_REPORT:
        return False

    return True


def find_target_literal_references(tree):
    references = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Constant):
            continue

        if node.value != TARGET_REPORT:
            continue

        references.append(
            {
                "line": node.lineno,
                "column": node.col_offset,
                "value": node.value,
            }
        )

    return references


def find_capture_dir_report_path_usage(assignments):
    suspicious = []

    for item in assignments:

        expression = item["expression"]

        if "capture_dir" in expression:
            suspicious.append(
                {
                    "line": item["line"],
                    "expression": expression,
                }
            )

    return suspicious


def verify_contract(
    producer_exists,
    syntax_valid,
    assignments,
    target_references,
    suspicious_assignments,
):
    reasons = []

    if not producer_exists:
        reasons.append("Producer file does not exist.")

    if not syntax_valid:
        reasons.append("Producer syntax is invalid.")

    if len(assignments) != 1:
        reasons.append(
            "Expected exactly one report_path assignment, "
            f"found {len(assignments)}."
        )

    deterministic = False
    project_root_reference = False
    target_value_correct = False
    operator_correct = False

    if len(assignments) == 1:

        value_ast = assignments[0]["value_ast"]

        deterministic = is_expected_deterministic_expression(
            value_ast
        )

        if isinstance(value_ast, ast.BinOp):

            operator_correct = isinstance(
                value_ast.op,
                ast.Div,
            )

            if isinstance(
                value_ast.left,
                ast.Name,
            ):
                project_root_reference = (
                    value_ast.left.id
                    == "PROJECT_ROOT"
                )

            if isinstance(
                value_ast.right,
                ast.Constant,
            ):
                target_value_correct = (
                    value_ast.right.value
                    == TARGET_REPORT
                )

        if not deterministic:
            reasons.append(
                "report_path is not the expected "
                "PROJECT_ROOT / TARGET_REPORT expression."
            )

    no_capture_dependency = (
        len(suspicious_assignments) == 0
    )

    if not no_capture_dependency:
        reasons.append(
            "report_path still depends on capture_dir."
        )

    if TARGET_REPORT not in [
        item["value"]
        for item in target_references
    ]:
        reasons.append(
            "Target report literal not found."
        )

    verified = (
        producer_exists
        and syntax_valid
        and len(assignments) == 1
        and deterministic
        and project_root_reference
        and target_value_correct
        and operator_correct
        and no_capture_dependency
    )

    return {
        "verified": verified,
        "deterministic": deterministic,
        "project_root_reference": project_root_reference,
        "target_value_correct": target_value_correct,
        "operator_correct": operator_correct,
        "capture_dir_dependency_removed": no_capture_dependency,
        "reasons": reasons,
    }


def main():

    print("=" * 100)
    print("ARUNDA TRADER")
    print(
        "HISTORICAL ELIGIBILITY PRODUCER OUTPUT PATH "
        "POST-REPAIR STATIC CONTRACT VERIFICATION v0.1"
    )
    print("=" * 100)

    print(
        "MODE                         : "
        "READ-ONLY STATIC CONTRACT VERIFICATION"
    )

    print(
        f"PROJECT ROOT                 : {PROJECT_ROOT}"
    )

    print(
        f"PRODUCER                     : {PRODUCER_NAME}"
    )

    print(
        f"TARGET REPORT                : {TARGET_REPORT}"
    )

    print("=" * 100)
    print("FILESYSTEM")
    print("=" * 100)

    producer_exists = PRODUCER_PATH.exists()

    print(
        f"Producer exists              : "
        f"{producer_exists}"
    )

    if not producer_exists:
        raise FileNotFoundError(
            f"Producer not found: {PRODUCER_PATH}"
        )

    source = PRODUCER_PATH.read_text(
        encoding="utf-8"
    )

    source_hash = sha256_file(
        PRODUCER_PATH
    )

    print(
        f"Producer SHA256              : "
        f"{source_hash}"
    )

    print("=" * 100)
    print("SYNTAX VERIFICATION")
    print("=" * 100)

    syntax_valid, tree, syntax_error = syntax_check(
        source
    )

    print(
        f"Syntax valid                 : "
        f"{syntax_valid}"
    )

    if not syntax_valid:
        raise RuntimeError(
            f"Syntax error: {syntax_error}"
        )

    print("=" * 100)
    print("REPORT_PATH STATIC CONTRACT")
    print("=" * 100)

    assignments = get_report_path_assignments(
        tree
    )

    print(
        f"report_path assignments       : "
        f"{len(assignments)}"
    )

    for item in assignments:
        print(
            f"  line={item['line']} | "
            f"{item['expression']}"
        )

    print("=" * 100)
    print("TARGET REFERENCES")
    print("=" * 100)

    target_references = (
        find_target_literal_references(tree)
    )

    print(
        f"Target literal references    : "
        f"{len(target_references)}"
    )

    for item in target_references:
        print(
            f"  line={item['line']} | "
            f"{item['value']}"
        )

    print("=" * 100)
    print("CAPTURE_DIR DEPENDENCY CHECK")
    print("=" * 100)

    suspicious_assignments = (
        find_capture_dir_report_path_usage(
            assignments
        )
    )

    print(
        f"Suspicious report_path usages : "
        f"{len(suspicious_assignments)}"
    )

    for item in suspicious_assignments:
        print(
            f"  line={item['line']} | "
            f"{item['expression']}"
        )

    print("=" * 100)
    print("SEMANTIC DETERMINISTIC CONTRACT")
    print("=" * 100)

    verification = verify_contract(
        producer_exists=producer_exists,
        syntax_valid=syntax_valid,
        assignments=assignments,
        target_references=target_references,
        suspicious_assignments=suspicious_assignments,
    )

    print(
        f"Deterministic expression     : "
        f"{verification['deterministic']}"
    )

    print(
        f"PROJECT_ROOT reference       : "
        f"{verification['project_root_reference']}"
    )

    print(
        f"Target filename correct      : "
        f"{verification['target_value_correct']}"
    )

    print(
        f"Division/path operator       : "
        f"{verification['operator_correct']}"
    )

    print(
        f"capture_dir dependency removed: "
        f"{verification['capture_dir_dependency_removed']}"
    )

    print("=" * 100)
    print("FINAL STATIC CONTRACT")
    print("=" * 100)

    print(
        f"STATIC CONTRACT VERIFIED      : "
        f"{verification['verified']}"
    )

    if verification["reasons"]:

        print()
        print("VERIFICATION NOTES:")

        for reason in verification["reasons"]:
            print(
                f"  - {reason}"
            )

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)

    print(
        "Producer executed            : NO"
    )

    print(
        "Producer imported            : NO"
    )

    print(
        "Eligibility executed         : NO"
    )

    print(
        "Eligibility rebuilt          : NO"
    )

    print(
        "Report regenerated           : NO"
    )

    print(
        "Synthetic artifact           : NO"
    )

    print(
        "Production DB writes         : NONE"
    )

    print(
        "Network access               : NONE"
    )

    print(
        "Source modified              : NO"
    )

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)

    if verification["verified"]:

        verdict = (
            "POST_REPAIR_STATIC_OUTPUT_PATH_CONTRACT_VERIFIED"
        )

        print(
            "HISTORICAL ELIGIBILITY OUTPUT PATH : "
            "POST_REPAIR_STATIC_OUTPUT_PATH_CONTRACT_VERIFIED"
        )

    else:

        verdict = (
            "POST_REPAIR_STATIC_OUTPUT_PATH_CONTRACT_VERIFICATION_FAILED"
        )

        print(
            "HISTORICAL ELIGIBILITY OUTPUT PATH : "
            "POST_REPAIR_STATIC_OUTPUT_PATH_CONTRACT_VERIFICATION_FAILED"
        )

    report = {
        "artifact": (
            "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_"
            "PRODUCER_OUTPUT_PATH_POST_REPAIR_STATIC_CONTRACT_VERIFICATION_v0.1"
        ),
        "timestamp_utc": utc_now(),
        "mode": "READ-ONLY STATIC CONTRACT VERIFICATION",
        "project_root": str(PROJECT_ROOT),
        "producer": str(PRODUCER_PATH),
        "target_report": TARGET_REPORT,
        "producer_sha256": source_hash,
        "verification": verification,
        "report_path_assignments": [
            {
                "line": item["line"],
                "end_line": item["end_line"],
                "expression": item["expression"],
                "semantic_ast": item["value_ast"].__class__.__name__,
            }
            for item in assignments
        ],
        "target_references": target_references,
        "suspicious_assignments": suspicious_assignments,
        "safety": {
            "producer_executed": False,
            "producer_imported": False,
            "eligibility_executed": False,
            "eligibility_rebuilt": False,
            "report_regenerated": False,
            "synthetic_artifact": False,
            "production_db_writes": "NONE",
            "network_access": "NONE",
            "source_modified": False,
        },
        "verdict": verdict,
    }

    FORENSIC_REPORT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"FORENSIC REPORT              : "
        f"{FORENSIC_REPORT_PATH}"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()