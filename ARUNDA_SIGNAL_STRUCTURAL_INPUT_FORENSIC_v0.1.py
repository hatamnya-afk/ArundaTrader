from pathlib import Path
import ast
import json

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

SIGNAL_LOGIC = PROJECT_ROOT / "signal_logic.py"
SIGNAL_ENGINE = PROJECT_ROOT / "signal_engine.py"

FORENSIC_NAME = "ARUNDA SIGNAL STRUCTURAL INPUT FORENSIC v0.1"


def read_source(path):
    return path.read_text(encoding="utf-8")


def parse_source(path):
    return ast.parse(read_source(path), filename=str(path))


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return node
    return None


def extract_expected_fields():
    tree = parse_source(SIGNAL_LOGIC)

    expected = None
    validate_node = find_function(tree, "validate_structure")

    if validate_node is None:
        return None, None

    for node in ast.walk(validate_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "EXPECTED_FIELDS":
                    try:
                        expected = ast.literal_eval(node.value)
                    except Exception:
                        pass

    # EXPECTED_FIELDS may be module-level rather than local.
    if expected is None:
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "EXPECTED_FIELDS":
                        try:
                            expected = ast.literal_eval(node.value)
                        except Exception:
                            pass

    return expected, validate_node


def extract_validation_contract():
    tree = parse_source(SIGNAL_LOGIC)

    node = find_function(tree, "validate_structure")

    if node is None:
        return {
            "function_found": False,
            "expected_fields_reference": False,
            "key_set_comparison": False,
        }

    key_set_comparison = False
    expected_reference = False

    for item in ast.walk(node):
        if isinstance(item, ast.Compare):
            text = ast.dump(item)

            if "EXPECTED_FIELDS" in text and "keys" in text:
                key_set_comparison = True

        if isinstance(item, ast.Name):
            if item.id == "EXPECTED_FIELDS":
                expected_reference = True

    return {
        "function_found": True,
        "expected_fields_reference": expected_reference,
        "key_set_comparison": key_set_comparison,
    }


def inspect_signal_engine():
    tree = parse_source(SIGNAL_ENGINE)

    findings = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                name = node.func.id

                if name in {
                    "load_structural_state",
                    "build_signal",
                    "validate_structure",
                }:
                    findings.append(
                        (
                            getattr(node, "lineno", None),
                            name,
                        )
                    )

            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

                if name in {
                    "load_structural_state",
                    "build_signal",
                    "validate_structure",
                }:
                    findings.append(
                        (
                            getattr(node, "lineno", None),
                            name,
                        )
                    )

    return sorted(findings)


def scan_json_artifacts():
    """
    READ ONLY.

    Searches existing JSON artifacts for structural dictionaries.
    Does not create, modify, or delete anything.
    """

    results = []

    for path in PROJECT_ROOT.glob("*.json"):
        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            continue

        def walk(obj, location="root"):
            if isinstance(obj, dict):
                keys = set(obj.keys())

                structural_score = len(
                    keys.intersection(
                        {
                            "structure",
                            "structural_state",
                            "structural_data",
                            "direction",
                            "regime",
                            "trend",
                            "support",
                            "resistance",
                        }
                    )
                )

                if structural_score >= 2:
                    results.append(
                        {
                            "file": str(path),
                            "location": location,
                            "keys": sorted(keys),
                        }
                    )

                for key, value in obj.items():
                    walk(
                        value,
                        f"{location}.{key}",
                    )

            elif isinstance(obj, list):
                for index, value in enumerate(obj):
                    walk(
                        value,
                        f"{location}[{index}]",
                    )

        walk(data)

    return results


def main():
    print("=" * 100)
    print(
        "ARUNDA TRADER — "
        "SIGNAL STRUCTURAL INPUT FORENSIC v0.1"
    )
    print("=" * 100)

    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print(f"TARGET       : {SIGNAL_LOGIC}")
    print("MODE         : READ ONLY")
    print("PRODUCTION EXECUTION : NONE")
    print("DATABASE ACCESS       : NONE")
    print("DATABASE WRITE        : NONE")
    print("JSON WRITE            : NONE")
    print("ARTIFACT CREATION     : NONE")
    print("NETWORK ACCESS       : NONE")

    print()
    print("=" * 100)
    print("A) STRUCTURAL VALIDATION CONTRACT")
    print("=" * 100)

    expected, validate_node = extract_expected_fields()

    if validate_node is None:
        print("validate_structure() : NOT FOUND")
    else:
        print(
            "validate_structure() : FOUND"
        )
        print(
            f"LINE                  : "
            f"{validate_node.lineno}"
        )

    if expected is None:
        print(
            "EXPECTED_FIELDS       : "
            "NOT STATICALLY RESOLVED"
        )
    else:
        print(
            "EXPECTED_FIELDS       : "
            f"{sorted(expected)}"
        )
        print(
            f"EXPECTED FIELD COUNT  : "
            f"{len(expected)}"
        )

    contract = extract_validation_contract()

    print()
    print(
        "EXPECTED_FIELDS REFERENCE : "
        f"{contract['expected_fields_reference']}"
    )

    print(
        "KEY-SET VALIDATION        : "
        f"{contract['key_set_comparison']}"
    )

    print()
    print("=" * 100)
    print("B) SIGNAL ENGINE STRUCTURAL PATH")
    print("=" * 100)

    calls = inspect_signal_engine()

    if not calls:
        print("NO STRUCTURAL CALLS FOUND")
    else:
        for line, name in calls:
            print(
                f"LINE={line:<5} CALL={name}"
            )

    print()
    print("=" * 100)
    print("C) EXISTING ARTIFACT STRUCTURAL INPUT DISCOVERY")
    print("=" * 100)

    artifacts = scan_json_artifacts()

    print(
        f"STRUCTURAL CANDIDATES : "
        f"{len(artifacts)}"
    )

    for item in artifacts[:100]:
        print()
        print(
            f"FILE     : {item['file']}"
        )
        print(
            f"LOCATION : {item['location']}"
        )
        print(
            f"KEYS     : {item['keys']}"
        )

    print()
    print("=" * 100)
    print("D) STATIC SCHEMA COMPARISON")
    print("=" * 100)

    if expected is None:
        print(
            "VERDICT : "
            "EXPECTED_SCHEMA_NOT_RESOLVED"
        )
    elif not artifacts:
        print(
            "VERDICT : "
            "NO_EXISTING_STRUCTURAL_ARTIFACT_FOUND"
        )
    else:
        expected_set = set(expected)

        mismatch_count = 0

        for item in artifacts:
            actual_set = set(item["keys"])

            missing = sorted(
                expected_set - actual_set
            )

            extra = sorted(
                actual_set - expected_set
            )

            if missing or extra:
                mismatch_count += 1

                print()
                print(
                    f"FILE     : {item['file']}"
                )
                print(
                    f"LOCATION : {item['location']}"
                )
                print(
                    f"MISSING  : {missing}"
                )
                print(
                    f"EXTRA    : {extra}"
                )

        print()
        print(
            f"SCHEMA MISMATCH CANDIDATES : "
            f"{mismatch_count}"
        )

    print()
    print("=" * 100)
    print("E) FINAL FORENSIC DECISION")
    print("=" * 100)

    if expected is None:
        verdict = (
            "STRUCTURAL_SCHEMA_NOT_RESOLVED"
        )
    elif not artifacts:
        verdict = (
            "RUNTIME_STRUCTURAL_INPUT_NOT_PRESENT_IN_ARTIFACTS"
        )
    else:
        verdict = (
            "STATIC_STRUCTURAL_INPUT_SCHEMA_COMPARISON_COMPLETE"
        )

    print(
        f"VERDICT : {verdict}"
    )

    print()
    print("=" * 100)
    print("F) IMPORTANT LIMITATION")
    print("=" * 100)

    print(
        "This forensic performs static "
        "source/artifact inspection only."
    )
    print(
        "It does NOT execute signal_engine.py."
    )
    print(
        "It does NOT execute signal_logic.py."
    )
    print(
        "It does NOT inspect runtime memory."
    )
    print(
        "It does NOT access the database."
    )
    print(
        "It does NOT generate a signal."
    )
    print(
        "It does NOT modify structural objects."
    )
    print(
        "It does NOT modify production source."
    )

    print()
    print("=" * 100)
    print("G) SAFETY ASSERTION")
    print("=" * 100)

    print("PYTHON PRODUCTION EXECUTION : False")
    print("DATABASE READ              : False")
    print("DATABASE WRITE             : False")
    print("JSON WRITE                 : False")
    print("ARTIFACT CREATION          : False")
    print("SIGNAL CREATION            : False")
    print("ORDER CREATION             : False")
    print("ORDER SUBMISSION           : False")
    print("NETWORK ACCESS             : False")
    print("SOURCE MUTATION            : False")
    print("=" * 100)


if __name__ == "__main__":
    main()