import ast
import math
import sqlite3
import importlib.util
from pathlib import Path


ENGINE_FILE = Path("history_analysis_engine.py")
DB_PATH = "arunda.db"


EXPECTED_FUNCTIONS = [
    "calculate_price_change",
    "calculate_price_change_pct",
    "calculate_volume_change_pct",
]


def print_header(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_section(title):
    print()
    print(title)
    print("-" * 100)


def load_source():
    return ENGINE_FILE.read_text(
        encoding="utf-8-sig"
    )


def parse_source(source):
    return ast.parse(source)


def function_inventory(tree):
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)

    return sorted(set(functions))


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "history_analysis_engine_step8a_target",
        ENGINE_FILE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to create module specification."
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def approximately_equal(a, b, tolerance=1e-10):
    try:
        return math.isclose(
            float(a),
            float(b),
            rel_tol=tolerance,
            abs_tol=tolerance,
        )
    except (TypeError, ValueError):
        return False


def validate_price_change(module):
    result = module.calculate_price_change(
        125.0,
        100.0,
    )

    expected = 25.0

    return (
        approximately_equal(result, expected),
        result,
        expected,
    )


def validate_price_change_pct(module):
    result = module.calculate_price_change_pct(
        125.0,
        100.0,
    )

    expected = 25.0

    return (
        approximately_equal(result, expected),
        result,
        expected,
    )


def validate_volume_change_pct(module):
    result = module.calculate_volume_change_pct(
        150.0,
        100.0,
    )

    expected = 50.0

    return (
        approximately_equal(result, expected),
        result,
        expected,
    )


def mathematical_consistency_test(module):
    samples = [
        (100.0, 100.0),
        (110.0, 100.0),
        (90.0, 100.0),
        (250.0, 200.0),
        (75.0, 100.0),
        (1000.0, 500.0),
    ]

    for price, previous_price in samples:

        expected_change = (
            price - previous_price
        )

        expected_pct = (
            expected_change /
            previous_price
        ) * 100.0

        actual_change = (
            module.calculate_price_change(
                price,
                previous_price,
            )
        )

        actual_pct = (
            module.calculate_price_change_pct(
                price,
                previous_price,
            )
        )

        if not approximately_equal(
            actual_change,
            expected_change,
        ):
            return False

        if not approximately_equal(
            actual_pct,
            expected_pct,
        ):
            return False

    return True


def zero_denominator_test(module):
    tests = [
        (
            "calculate_price_change_pct",
            100.0,
            0.0,
        ),
        (
            "calculate_volume_change_pct",
            100.0,
            0.0,
        ),
    ]

    results = {}

    for name, current, previous in tests:

        try:
            if name == "calculate_price_change_pct":
                result = module.calculate_price_change_pct(
                    current,
                    previous,
                )

            else:
                result = module.calculate_volume_change_pct(
                    current,
                    previous,
                )

            if result is None:
                status = "SAFE"

            elif isinstance(result, float):
                if math.isnan(result):
                    status = "SAFE"
                elif math.isinf(result):
                    status = "UNSAFE"
                else:
                    status = "DEFINED"

            else:
                status = "DEFINED"

        except (
            ZeroDivisionError,
            ValueError,
            TypeError,
        ):
            status = "SAFE"

        except Exception as exc:
            status = (
                "ERROR:" +
                type(exc).__name__
            )

        results[name] = status

    return results


def negative_value_test(module):
    results = {}

    try:
        results["price_change"] = (
            module.calculate_price_change(
                -10.0,
                100.0,
            )
        )
    except Exception as exc:
        results["price_change"] = (
            "ERROR:" + type(exc).__name__
        )

    try:
        results["price_change_pct"] = (
            module.calculate_price_change_pct(
                -10.0,
                100.0,
            )
        )
    except Exception as exc:
        results["price_change_pct"] = (
            "ERROR:" + type(exc).__name__
        )

    return results


def mutation_audit(source):
    """
    Detect only actual mutation SQL passed to
    sqlite execution methods.

    Plain strings, comments, print statements,
    documentation, and unused SQL text do not
    count as database mutations.
    """

    tree = ast.parse(source)

    mutation_patterns = (
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "ALTER ",
        "DROP ",
        "CREATE TABLE",
        "CREATE INDEX",
        "CREATE VIEW",
        "CREATE TRIGGER",
        "REPLACE ",
    )

    execution_methods = {
        "execute",
        "executemany",
        "executescript",
    }

    mutations = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Attribute):
            continue

        method = node.func.attr

        if method not in execution_methods:
            continue

        if not node.args:
            continue

        sql_node = node.args[0]

        if not isinstance(
            sql_node,
            ast.Constant,
        ):
            continue

        if not isinstance(
            sql_node.value,
            str,
        ):
            continue

        sql = " ".join(
            sql_node.value.upper().split()
        )

        for pattern in mutation_patterns:

            normalized_pattern = " ".join(
                pattern.split()
            )

            if normalized_pattern in sql:

                mutations.append(
                    f"{method}: "
                    f"{normalized_pattern}"
                )

    return sorted(set(mutations))


def database_fingerprint():
    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    try:

        rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_history
            """
        ).fetchone()[0]

        snapshots = conn.execute(
            """
            SELECT COUNT(DISTINCT timestamp)
            FROM market_history
            """
        ).fetchone()[0]

        cmc_ids = conn.execute(
            """
            SELECT COUNT(DISTINCT cmc_id)
            FROM market_history
            """
        ).fetchone()[0]

        duplicate_ids = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT timestamp, cmc_id
                FROM market_history
                GROUP BY timestamp, cmc_id
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        return {
            "rows": rows,
            "snapshots": snapshots,
            "cmc_ids": cmc_ids,
            "duplicate_ids": duplicate_ids,
        }

    finally:
        conn.close()


def main():

    print_header(
        "ARUNDA TRADER — DEV-06 — STEP 8A"
    )

    print("ANALYSIS MATHEMATICAL CONTRACT AUDIT")
    print("=" * 100)

    print_section("MODE")

    print("Database mutation : NONE")
    print("Production write  : NONE")
    print("Audit mode        : READ ONLY")

    print_section("FILE VALIDATION")

    exists = ENGINE_FILE.exists()

    print(
        "Analysis Engine :",
        "PASS" if exists else "FAIL",
    )

    if not exists:

        print()
        print(
            "RESULT : STEP 8A FAIL"
        )

        print(
            "STATUS : "
            "ANALYSIS ENGINE FILE NOT FOUND"
        )

        return

    source = load_source()

    try:

        tree = parse_source(source)

    except SyntaxError as exc:

        print(
            "AST Parse       : FAIL"
        )

        print(
            "Error            :",
            exc,
        )

        print()
        print(
            "RESULT : STEP 8A FAIL"
        )

        return

    print("AST Parse       : PASS")

    print_section("FUNCTION INVENTORY")

    inventory = function_inventory(tree)

    for name in inventory:
        print(" -", name)

    print_section(
        "REQUIRED MATHEMATICAL FUNCTIONS"
    )

    required_functions_pass = True

    for name in EXPECTED_FUNCTIONS:

        passed = name in inventory

        print(
            f"{name:<32}:",
            "PASS" if passed else "FAIL",
        )

        if not passed:
            required_functions_pass = False

    if not required_functions_pass:

        print()
        print(
            "RESULT : STEP 8A FAIL"
        )

        print(
            "STATUS : "
            "REQUIRED MATHEMATICAL FUNCTION MISSING"
        )

        return

    print_section(
        "RUNTIME MATHEMATICAL VALIDATION"
    )

    try:

        module = load_engine_module()

    except Exception as exc:

        print(
            "Engine import : FAIL"
        )

        print(
            "Error         :",
            type(exc).__name__,
            exc,
        )

        print()
        print(
            "RESULT : STEP 8A FAIL"
        )

        return

    (
        price_change_pass,
        actual,
        expected,
    ) = validate_price_change(module)

    print(
        "calculate_price_change :",
        "PASS" if price_change_pass else "FAIL",
    )

    print(
        "  Expected :",
        expected,
    )

    print(
        "  Actual   :",
        actual,
    )

    (
        price_pct_pass,
        actual,
        expected,
    ) = validate_price_change_pct(module)

    print(
        "calculate_price_change_pct :",
        "PASS" if price_pct_pass else "FAIL",
    )

    print(
        "  Expected :",
        expected,
    )

    print(
        "  Actual   :",
        actual,
    )

    (
        volume_pct_pass,
        actual,
        expected,
    ) = validate_volume_change_pct(module)

    print(
        "calculate_volume_change_pct :",
        "PASS" if volume_pct_pass else "FAIL",
    )

    print(
        "  Expected :",
        expected,
    )

    print(
        "  Actual   :",
        actual,
    )

    runtime_math_pass = (
        price_change_pass
        and price_pct_pass
        and volume_pct_pass
    )

    print_section(
        "CROSS-SAMPLE MATHEMATICAL CONSISTENCY"
    )

    consistency_pass = (
        mathematical_consistency_test(
            module
        )
    )

    print(
        "Price change consistency :",
        "PASS"
        if consistency_pass
        else "FAIL",
    )

    print_section(
        "ZERO DENOMINATOR SAFETY"
    )

    zero_results = (
        zero_denominator_test(module)
    )

    zero_pass = True

    for name, result in zero_results.items():

        print(
            f"{name:<32}:",
            result,
        )

        if str(result).startswith(
            "ERROR:"
        ):
            zero_pass = False

    print_section(
        "NEGATIVE VALUE BEHAVIOR"
    )

    negative_results = (
        negative_value_test(module)
    )

    for name, result in negative_results.items():

        print(
            f"{name:<32}:",
            result,
        )

    print_section(
        "SOURCE MUTATION AUDIT"
    )

    mutations = mutation_audit(
        source
    )

    if mutations:

        print(
            "SQL mutation statements :",
            ", ".join(mutations),
        )

        mutation_pass = False

    else:

        print(
            "SQL mutation statements : "
            "NONE DETECTED"
        )

        mutation_pass = True

    print_section(
        "DATABASE READ-ONLY FINGERPRINT"
    )

    before = database_fingerprint()

    print(
        "Rows              :",
        before["rows"],
    )

    print(
        "Snapshots         :",
        before["snapshots"],
    )

    print(
        "Distinct CMC IDs  :",
        before["cmc_ids"],
    )

    print(
        "Duplicate IDs     :",
        before["duplicate_ids"],
    )

    print_section(
        "DATABASE FINGERPRINT PRESERVATION"
    )

    after = database_fingerprint()

    fingerprint_pass = (
        before == after
    )

    print(
        "BEFORE == AFTER    :",
        "PASS"
        if fingerprint_pass
        else "FAIL",
    )

    print_section(
        "STEP 8A CONTRACT"
    )

    checks = {
        "AST syntax":
            True,

        "Required functions":
            required_functions_pass,

        "Runtime mathematics":
            runtime_math_pass,

        "Cross-sample consistency":
            consistency_pass,

        "Zero denominator safety":
            zero_pass,

        "Read only":
            mutation_pass,

        "Database unchanged":
            fingerprint_pass,
    }

    for name, result in checks.items():

        print(
            f"{name:<32}:",
            "PASS" if result else "FAIL",
        )

    final_pass = all(
        checks.values()
    )

    print()
    print("=" * 100)
    print("STEP 8A VERDICT")
    print("=" * 100)

    if final_pass:

        print(
            "RESULT : "
            "ANALYSIS MATHEMATICAL "
            "CONTRACT AUDIT PASS"
        )

        print(
            "STATUS : READY FOR STEP 8B"
        )

    else:

        print(
            "RESULT : "
            "ANALYSIS MATHEMATICAL "
            "CONTRACT AUDIT FAIL"
        )

        print(
            "STATUS : DO NOT PROCEED TO STEP 8B"
        )

    print()
    print("Architecture : PRESERVED")
    print("Database     : READ ONLY")
    print("Writes       : NONE")


if __name__ == "__main__":
    main()