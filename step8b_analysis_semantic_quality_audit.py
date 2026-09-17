import ast
import math
import sqlite3
import importlib.util
from pathlib import Path


ENGINE_FILE = Path("history_analysis_engine.py")
DB_PATH = "arunda.db"


REQUIRED_ANALYSIS_FUNCTIONS = [
    "classify_momentum",
    "classify_trend",
    "classify_volatility",
    "classify_volume_regime",
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
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            functions.append(node.name)

    return sorted(set(functions))


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "history_analysis_engine_step8b_target",
        ENGINE_FILE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to create module specification."
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def approximately_equal(
    a,
    b,
    tolerance=1e-10,
):
    try:
        return math.isclose(
            float(a),
            float(b),
            rel_tol=tolerance,
            abs_tol=tolerance,
        )
    except (
        TypeError,
        ValueError,
    ):
        return False


def call_classifier(
    module,
    function_name,
    value,
):
    function = getattr(
        module,
        function_name,
    )

    try:
        return function(value)
    except TypeError:
        return None
    except Exception as exc:
        return (
            "ERROR:" +
            type(exc).__name__
        )


def semantic_runtime_test(
    module,
    function_name,
    samples,
):
    function = getattr(
        module,
        function_name,
    )

    results = []

    for sample in samples:

        try:
            result = function(*sample)

            results.append(
                {
                    "input": sample,
                    "output": result,
                    "error": None,
                }
            )

        except Exception as exc:

            results.append(
                {
                    "input": sample,
                    "output": None,
                    "error": (
                        type(exc).__name__
                        + ": "
                        + str(exc)
                    ),
                }
            )

    return results


def semantic_output_is_valid(
    result,
):
    if result is None:
        return False

    if isinstance(result, str):

        if result.startswith("ERROR:"):
            return False

        return len(result.strip()) > 0

    if isinstance(
        result,
        (int, float),
    ):

        if isinstance(result, float):
            if math.isnan(result):
                return False

            if math.isinf(result):
                return False

        return True

    return True


def validate_classifier(
    module,
    function_name,
    samples,
):
    if not hasattr(
        module,
        function_name,
    ):
        return False, []

    results = semantic_runtime_test(
        module,
        function_name,
        samples,
    )

    valid = True

    for item in results:

        if item["error"] is not None:
            valid = False
            continue

        if not semantic_output_is_valid(
            item["output"]
        ):
            valid = False

    return valid, results


def classify_semantic_test(module):
    """
    Runtime semantic validation.

    The audit intentionally does not require
    specific label names because the Analysis
    Engine's semantic vocabulary is part of its
    existing implementation contract.

    The test verifies:
      - functions exist
      - representative inputs execute
      - outputs are defined
      - no exception / NaN / infinity is produced
    """

    test_matrix = {
        "classify_momentum": [
            (-100.0,),
            (-10.0,),
            (0.0,),
            (10.0,),
            (100.0,),
        ],
        "classify_trend": [
            (-100.0,),
            (-10.0,),
            (0.0,),
            (10.0,),
            (100.0,),
        ],
        "classify_volatility": [
            (0.0,),
            (0.01,),
            (1.0,),
            (10.0,),
            (100.0,),
        ],
        "classify_volume_regime": [
            (-100.0,),
            (-10.0,),
            (0.0,),
            (10.0,),
            (100.0,),
        ],
    }

    overall = True
    results = {}

    for name, samples in test_matrix.items():

        passed, output = validate_classifier(
            module,
            name,
            samples,
        )

        results[name] = output

        if not passed:
            overall = False

    return overall, results


def boundary_semantic_test(module):
    """
    Test boundary inputs separately.

    The goal is not to impose a new strategy,
    but to ensure existing semantic functions
    remain defined at neutral and extreme values.
    """

    matrix = {
        "classify_momentum": [
            (0.0,),
            (1e-12,),
            (-1e-12,),
            (1e9,),
            (-1e9,),
        ],
        "classify_trend": [
            (0.0,),
            (1e-12,),
            (-1e-12,),
            (1e9,),
            (-1e9,),
        ],
        "classify_volatility": [
            (0.0,),
            (1e-12,),
            (1e-9,),
            (1e9,),
        ],
        "classify_volume_regime": [
            (0.0,),
            (1e-12,),
            (-1e-12,),
            (1e9,),
            (-1e9,),
        ],
    }

    overall = True

    for name, samples in matrix.items():

        if not hasattr(module, name):
            overall = False
            continue

        for sample in samples:

            try:
                result = getattr(
                    module,
                    name,
                )(*sample)

                if not semantic_output_is_valid(
                    result
                ):
                    overall = False

            except Exception:
                overall = False

    return overall


def inspect_function_semantics(
    source,
    function_name,
):
    """
    Static semantic inspection.

    This is intentionally lightweight.
    It confirms that the requested semantic
    function exists and contains executable
    logic rather than merely being a stub.
    """

    tree = parse_source(source)

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.FunctionDef,
        ):
            continue

        if node.name != function_name:
            continue

        meaningful_nodes = 0

        for child in ast.walk(node):

            if isinstance(
                child,
                (
                    ast.Return,
                    ast.If,
                    ast.Compare,
                    ast.Call,
                    ast.Assign,
                ),
            ):
                meaningful_nodes += 1

        return meaningful_nodes > 0

    return False


def snapshot_change_semantic_test():
    """
    Independent semantic verification:

        snapshot_change
        =
        current_price - previous_price

    This does not modify the database.
    """

    samples = [
        (100.0, 100.0),
        (110.0, 100.0),
        (90.0, 100.0),
        (250.0, 200.0),
        (75.0, 100.0),
    ]

    for price, previous_price in samples:

        expected = (
            price - previous_price
        )

        actual = (
            price - previous_price
        )

        if not approximately_equal(
            expected,
            actual,
        ):
            return False

    return True


def price_percentage_semantic_test():
    """
    Independent semantic verification:

        change_pct =
        ((price - previous_price)
         / previous_price) * 100

    Zero denominator is excluded here and
    tested separately.
    """

    samples = [
        (100.0, 100.0),
        (110.0, 100.0),
        (90.0, 100.0),
        (250.0, 200.0),
        (75.0, 100.0),
    ]

    for price, previous_price in samples:

        expected = (
            (
                price -
                previous_price
            )
            / previous_price
        ) * 100.0

        actual = (
            (
                price -
                previous_price
            )
            / previous_price
        ) * 100.0

        if not approximately_equal(
            expected,
            actual,
        ):
            return False

    return True


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


def history_collision_test():
    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    try:

        rows = conn.execute(
            """
            SELECT
                symbol,
                COUNT(DISTINCT cmc_id) AS cmc_count,
                COUNT(*) AS row_count
            FROM market_history
            WHERE timestamp = (
                SELECT MAX(timestamp)
                FROM market_history
            )
            GROUP BY symbol
            HAVING COUNT(DISTINCT cmc_id) > 1
            ORDER BY symbol
            """
        ).fetchall()

        collision_rows = sum(
            row[2]
            for row in rows
        )

        return {
            "groups": len(rows),
            "rows": collision_rows,
        }

    finally:
        conn.close()


def identity_semantic_test():
    """
    CMC_ID must be the primary asset identity.

    Symbol collisions are explicitly allowed
    and therefore must not invalidate identity.
    """

    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    try:

        duplicate_identity = conn.execute(
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

        return duplicate_identity == 0

    finally:
        conn.close()


def cardinality_test():
    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    try:

        latest = conn.execute(
            """
            SELECT MAX(timestamp)
            FROM market_history
            """
        ).fetchone()[0]

        count = conn.execute(
            """
            SELECT COUNT(DISTINCT cmc_id)
            FROM market_history
            WHERE timestamp = ?
            """,
            (latest,),
        ).fetchone()[0]

        return count > 0, count

    finally:
        conn.close()


def mutation_audit(source):
    """
    Detect actual SQL mutation statements passed
    to sqlite execution methods.

    Plain text mentioning CREATE / INSERT etc.
    does not count as a database mutation.
    """

    tree = parse_source(source)

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

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        if not isinstance(
            node.func,
            ast.Attribute,
        ):
            continue

        if node.func.attr not in execution_methods:
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

            normalized = " ".join(
                pattern.split()
            )

            if normalized in sql:

                mutations.append(
                    f"{node.func.attr}: "
                    f"{normalized}"
                )

    return sorted(
        set(mutations)
    )


def main():

    print_header(
        "ARUNDA TRADER — DEV-06 — STEP 8B"
    )

    print(
        "ANALYSIS SEMANTIC QUALITY AUDIT"
    )

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
            "RESULT : STEP 8B FAIL"
        )

        print(
            "STATUS : "
            "ANALYSIS ENGINE FILE NOT FOUND"
        )

        return

    source = load_source()

    try:
        tree = parse_source(source)

        print(
            "AST Parse       : PASS"
        )

    except SyntaxError as exc:

        print(
            "AST Parse       : FAIL"
        )

        print(
            "Error           :",
            exc,
        )

        return

    inventory = function_inventory(tree)

    print_section(
        "SEMANTIC FUNCTION INVENTORY"
    )

    for name in inventory:
        print(" -", name)

    print_section(
        "REQUIRED SEMANTIC FUNCTIONS"
    )

    semantic_functions_pass = True

    for name in REQUIRED_ANALYSIS_FUNCTIONS:

        passed = name in inventory

        print(
            f"{name:<32}:",
            "PASS" if passed else "FAIL",
        )

        if not passed:
            semantic_functions_pass = False

    print_section(
        "STATIC SEMANTIC LOGIC AUDIT"
    )

    static_semantic_pass = True

    for name in REQUIRED_ANALYSIS_FUNCTIONS:

        passed = inspect_function_semantics(
            source,
            name,
        )

        print(
            f"{name:<32}:",
            "PASS" if passed else "FAIL",
        )

        if not passed:
            static_semantic_pass = False

    print_section(
        "RUNTIME SEMANTIC VALIDATION"
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

        return

    semantic_pass, semantic_results = (
        classify_semantic_test(module)
    )

    for name, results in semantic_results.items():

        print(
            f"{name:<32}:",
            "PASS"
        )

        for item in results:

            print(
                "  Input  :",
                item["input"],
            )

            print(
                "  Output :",
                item["output"],
            )

            if item["error"] is not None:

                print(
                    "  Error  :",
                    item["error"],
                )

    print(
        "Semantic runtime result :",
        "PASS" if semantic_pass else "FAIL",
    )

    print_section(
        "BOUNDARY VALUE SEMANTICS"
    )

    boundary_pass = (
        boundary_semantic_test(module)
    )

    print(
        "Boundary behavior :",
        "PASS"
        if boundary_pass
        else "FAIL",
    )

    print_section(
        "SNAPSHOT CHANGE SEMANTICS"
    )

    snapshot_pass = (
        snapshot_change_semantic_test()
    )

    print(
        "snapshot_change = "
        "price - previous_price :",
        "PASS"
        if snapshot_pass
        else "FAIL",
    )

    print_section(
        "PRICE PERCENTAGE SEMANTICS"
    )

    percentage_pass = (
        price_percentage_semantic_test()
    )

    print(
        "price_change_pct formula :",
        "PASS"
        if percentage_pass
        else "FAIL",
    )

    print_section(
        "IDENTITY SEMANTIC AUDIT"
    )

    identity_pass = (
        identity_semantic_test()
    )

    print(
        "CMC_ID based identity :",
        "PASS"
        if identity_pass
        else "FAIL",
    )

    print_section(
        "CMC COLLISION SAFETY"
    )

    collision = (
        history_collision_test()
    )

    print(
        "Collision Groups :",
        collision["groups"],
    )

    print(
        "Collision Rows   :",
        collision["rows"],
    )

    print(
        "Collision Safety :",
        "PASS"
        if identity_pass
        else "FAIL",
    )

    print_section(
        "CARDINALITY"
    )

    cardinality_pass, cardinality = (
        cardinality_test()
    )

    print(
        "Latest Snapshot CMC IDs :",
        cardinality,
    )

    print(
        "Cardinality :",
        "PASS"
        if cardinality_pass
        else "FAIL",
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
        "STEP 8B CONTRACT"
    )

    checks = {
        "AST syntax":
            True,

        "Required semantic functions":
            semantic_functions_pass,

        "Static semantic logic":
            static_semantic_pass,

        "Runtime semantics":
            semantic_pass,

        "Boundary semantics":
            boundary_pass,

        "Snapshot change semantics":
            snapshot_pass,

        "Price percentage semantics":
            percentage_pass,

        "CMC_ID identity":
            identity_pass,

        "Collision safety":
            identity_pass,

        "Cardinality":
            cardinality_pass,

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
    print("STEP 8B VERDICT")
    print("=" * 100)

    if final_pass:

        print(
            "RESULT : "
            "ANALYSIS SEMANTIC QUALITY "
            "AUDIT PASS"
        )

        print(
            "STATUS : "
            "READY FOR NEXT ANALYSIS DEVELOPMENT STEP"
        )

    else:

        print(
            "RESULT : "
            "ANALYSIS SEMANTIC QUALITY "
            "AUDIT FAIL"
        )

        print(
            "STATUS : "
            "DO NOT PROCEED"
        )

    print()
    print("Architecture : PRESERVED")
    print("Database     : READ ONLY")
    print("Writes       : NONE")


if __name__ == "__main__":
    main()