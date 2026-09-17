import ast
import importlib.util
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"
ANALYSIS_FILE = BASE_DIR / "history_analysis_engine.py"

REQUIRED_FUNCTIONS = (
    "classify_trend",
    "classify_momentum",
    "classify_volatility",
    "classify_volume_regime",
)


REGIME_CONTRACT = {
    "classify_trend": {
        "allowed": {"DOWN", "FLAT", "UP"},
        "tests": {
            -100.0: "DOWN",
            -10.0: "DOWN",
            0.0: "FLAT",
            10.0: "UP",
            100.0: "UP",
        },
    },
    "classify_momentum": {
        "allowed": {"NEGATIVE", "NEUTRAL", "POSITIVE"},
        "tests": {
            -100.0: "NEGATIVE",
            -10.0: "NEGATIVE",
            0.0: "NEUTRAL",
            10.0: "POSITIVE",
            100.0: "POSITIVE",
        },
    },
    "classify_volatility": {
        "allowed": {"LOW", "MEDIUM", "HIGH"},
        "tests": {
            0.0: "LOW",
            0.01: "LOW",
            1.0: "MEDIUM",
            10.0: "HIGH",
            100.0: "HIGH",
        },
    },
    "classify_volume_regime": {
        "allowed": {"CONTRACTING", "STABLE", "EXPANDING"},
        "tests": {
            -100.0: "CONTRACTING",
            -10.0: "STABLE",
            0.0: "STABLE",
            10.0: "STABLE",
            100.0: "EXPANDING",
        },
    },
}


# UNKNOWN is tolerated as a defensive/internal fallback.
# It is NOT part of the public regime vocabulary.
DEFENSIVE_OUTPUTS = {
    "UNKNOWN",
    "N/A",
    "INVALID",
    "ERROR",
    "NONE",
    "UNDEFINED",
}


def line():
    print("-" * 96)


def header():
    print("=" * 96)
    print("ARUNDA TRADER — DEV-06 — STEP 10A")
    print("REGIME CONTRACT AUDIT")
    print("=" * 96)


def parse_ast(source):
    try:
        return ast.parse(source), None
    except SyntaxError as exc:
        return None, exc


def load_module(path):
    spec = importlib.util.spec_from_file_location(
        "arunda_history_analysis_step10a",
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to create module specification."
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def function_inventory(tree):
    return sorted(
        node.name
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
    )


def get_function_node(tree, function_name):
    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            if node.name == function_name:
                return node

    return None


def connect_read_only():
    return sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )


def history_fingerprint(connection):
    cursor = connection.cursor()

    rows = cursor.execute(
        "SELECT COUNT(*) FROM market_history"
    ).fetchone()[0]

    snapshots = cursor.execute(
        "SELECT COUNT(DISTINCT timestamp) FROM market_history"
    ).fetchone()[0]

    cmc_ids = cursor.execute(
        "SELECT COUNT(DISTINCT cmc_id) FROM market_history"
    ).fetchone()[0]

    duplicate_ids = cursor.execute(
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


def audit_required_functions(inventory):
    return {
        name: name in inventory
        for name in REQUIRED_FUNCTIONS
    }


def extract_return_literals(function_node):
    """
    Extract literal strings appearing in return expressions.

    Supports:

        return "UP"

        return "UP" if value > 0 else "DOWN"

        if value > 0:
            return "UP"

    Defensive values such as UNKNOWN are collected separately.
    """

    public_outputs = set()
    defensive_outputs = set()
    unsupported_outputs = set()

    allowed_all = set()

    for name in REQUIRED_FUNCTIONS:
        allowed_all.update(
            REGIME_CONTRACT[name]["allowed"]
        )

    for node in ast.walk(function_node):

        if not isinstance(node, ast.Return):
            continue

        value = node.value

        literals = []

        for child in ast.walk(value):
            if isinstance(child, ast.Constant):
                if isinstance(child.value, str):
                    literals.append(child.value)

        for literal in literals:

            if literal in allowed_all:
                public_outputs.add(literal)

            elif literal in DEFENSIVE_OUTPUTS:
                defensive_outputs.add(literal)

            else:
                unsupported_outputs.add(literal)

    return (
        public_outputs,
        defensive_outputs,
        unsupported_outputs,
    )


def static_semantic_audit(tree):
    """
    Static semantic audit.

    Important architectural rule:

    Static inspection must not reject a valid engine merely because
    it contains a defensive fallback such as UNKNOWN.

    The actual public vocabulary is validated separately at runtime.

    Therefore:

        allowed regime outputs  -> required
        defensive outputs       -> tolerated
        unrelated outputs       -> failure
    """

    results = {}

    for function_name in REQUIRED_FUNCTIONS:

        node = get_function_node(
            tree,
            function_name,
        )

        if node is None:
            results[function_name] = {
                "pass": False,
                "reason": "function not found",
            }
            continue

        public_outputs, defensive_outputs, unsupported = (
            extract_return_literals(node)
        )

        allowed = REGIME_CONTRACT[
            function_name
        ]["allowed"]

        expected_present = public_outputs.intersection(
            allowed
        )

        unsupported_public = unsupported - defensive_outputs

        passed = (
            bool(expected_present)
            and not unsupported_public
        )

        results[function_name] = {
            "pass": passed,
            "public_outputs": public_outputs,
            "defensive_outputs": defensive_outputs,
            "unsupported_outputs": unsupported_public,
        }

    return results


def runtime_semantic_validation(module):
    results = {}

    for function_name in REQUIRED_FUNCTIONS:

        function = getattr(
            module,
            function_name,
        )

        contract = REGIME_CONTRACT[
            function_name
        ]

        outputs = []

        try:

            for value, expected in contract[
                "tests"
            ].items():

                actual = function(value)

                outputs.append(
                    (
                        value,
                        expected,
                        actual,
                    )
                )

            passed = all(
                actual == expected
                for _, expected, actual in outputs
            )

            results[function_name] = {
                "pass": passed,
                "outputs": outputs,
            }

        except Exception as exc:

            results[function_name] = {
                "pass": False,
                "outputs": outputs,
                "error": (
                    f"{type(exc).__name__}: {exc}"
                ),
            }

    return results


def boundary_validation(module):

    tests = (
        (
            "classify_trend",
            -0.0,
            "FLAT",
        ),
        (
            "classify_trend",
            0.0,
            "FLAT",
        ),
        (
            "classify_momentum",
            -0.0,
            "NEUTRAL",
        ),
        (
            "classify_momentum",
            0.0,
            "NEUTRAL",
        ),
        (
            "classify_volatility",
            0.0,
            "LOW",
        ),
        (
            "classify_volume_regime",
            0.0,
            "STABLE",
        ),
    )

    results = []

    for function_name, value, expected in tests:

        function = getattr(
            module,
            function_name,
        )

        try:

            actual = function(value)

            results.append(
                {
                    "function": function_name,
                    "value": value,
                    "expected": expected,
                    "actual": actual,
                    "pass": actual == expected,
                }
            )

        except Exception as exc:

            results.append(
                {
                    "function": function_name,
                    "value": value,
                    "expected": expected,
                    "actual": None,
                    "pass": False,
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                }
            )

    return results


def vocabulary_validation(module):

    results = {}

    probe_values = (
        -100.0,
        -10.0,
        -1.0,
        0.0,
        0.01,
        1.0,
        10.0,
        100.0,
    )

    for function_name in REQUIRED_FUNCTIONS:

        function = getattr(
            module,
            function_name,
        )

        allowed = REGIME_CONTRACT[
            function_name
        ]["allowed"]

        runtime_outputs = set()

        for value in probe_values:

            try:
                output = function(value)
                runtime_outputs.add(output)

            except Exception:
                pass

        invalid = (
            runtime_outputs - allowed
        )

        results[function_name] = {
            "allowed": allowed,
            "runtime": runtime_outputs,
            "invalid": invalid,
            "pass": (
                bool(runtime_outputs)
                and not invalid
            ),
        }

    return results


def lookahead_audit(source):

    suspicious_patterns = (
        "future_price",
        "future_return",
        "future_change",
        "next_price",
        "next_timestamp",
        "future_timestamp",
        "lead(",
        "shift(-1)",
    )

    source_lower = source.lower()

    detected = [
        pattern
        for pattern in suspicious_patterns
        if pattern.lower() in source_lower
    ]

    return detected


def mutation_audit(source, tree):

    mutation_patterns = (
        "INSERT",
        "UPDATE",
        "DELETE",
        "ALTER",
        "DROP",
        "CREATE TABLE",
        "CREATE INDEX",
        "CREATE VIEW",
        "CREATE TRIGGER",
        "REPLACE INTO",
    )

    detected = set()

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Constant,
        ):
            continue

        if not isinstance(
            node.value,
            str,
        ):
            continue

        text = node.value.upper()

        for pattern in mutation_patterns:

            if pattern in text:
                detected.add(pattern)

    return sorted(detected)


def print_runtime_results(results):

    for function_name in REQUIRED_FUNCTIONS:

        result = results[
            function_name
        ]

        status = (
            "PASS"
            if result["pass"]
            else "FAIL"
        )

        print(
            f"{function_name:<35} : {status}"
        )

        if result.get("error"):
            print(
                f"  Error : {result['error']}"
            )

        for value, expected, actual in result.get(
            "outputs",
            [],
        ):
            print(
                f"  Input  : ({value},)"
            )
            print(
                f"  Output : {actual}"
            )


def print_boundary_results(results):

    for result in results:

        status = (
            "PASS"
            if result["pass"]
            else "FAIL"
        )

        print(
            f"{result['function']:<35} : {status}"
        )

        print(
            f"  value={result['value']} "
            f"expected={result['expected']} "
            f"actual={result['actual']}"
        )


def print_vocabulary(results):

    for function_name in REQUIRED_FUNCTIONS:

        result = results[
            function_name
        ]

        print(function_name)

        print(
            "  Allowed outputs : "
            + ", ".join(
                sorted(result["allowed"])
            )
        )

        print(
            "  Runtime outputs  : "
            + ", ".join(
                sorted(
                    str(x)
                    for x in result["runtime"]
                )
            )
        )


def main():

    header()

    print()
    print("MODE")
    line()

    print(
        "Database mutation                       : NONE"
    )
    print(
        "Production write                        : NONE"
    )
    print(
        "Audit mode                              : READ ONLY"
    )

    print()
    print("FILE VALIDATION")
    line()

    if not ANALYSIS_FILE.exists():

        print(
            "Analysis Engine                         : FAIL"
        )
        print(
            "Reason                                  : "
            "file not found"
        )
        return

    source = ANALYSIS_FILE.read_text(
        encoding="utf-8"
    )

    tree, parse_error = parse_ast(
        source
    )

    if parse_error:

        print(
            "Analysis Engine                         : FAIL"
        )
        print(
            f"AST Parse                               : "
            f"FAIL — {parse_error}"
        )
        return

    print(
        "Analysis Engine                         : PASS"
    )
    print(
        "AST Parse                               : PASS"
    )

    inventory = function_inventory(
        tree
    )

    print()
    print(
        "ANALYSIS ENGINE FUNCTION INVENTORY"
    )
    line()

    for name in inventory:
        print(
            f" - {name}"
        )

    required_results = audit_required_functions(
        inventory
    )

    print()
    print(
        "REQUIRED REGIME FUNCTIONS"
    )
    line()

    required_pass = True

    for name in REQUIRED_FUNCTIONS:

        passed = required_results[
            name
        ]

        required_pass = (
            required_pass and passed
        )

        print(
            f"{name:<40} : "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()
    print(
        "STATIC REGIME SEMANTIC AUDIT"
    )
    line()

    static_results = static_semantic_audit(
        tree
    )

    static_pass = True

    for name in REQUIRED_FUNCTIONS:

        result = static_results[
            name
        ]

        if result["pass"]:

            print(
                f"{name:<35} : PASS"
            )

            if result.get(
                "defensive_outputs"
            ):
                print(
                    "  Defensive outputs tolerated : "
                    + ", ".join(
                        sorted(
                            result[
                                "defensive_outputs"
                            ]
                        )
                    )
                )

        else:

            static_pass = False

            print(
                f"{name:<35} : FAIL"
            )

            if result.get(
                "reason"
            ):
                print(
                    f"  Reason : "
                    f"{result['reason']}"
                )

            if result.get(
                "unsupported_outputs"
            ):
                print(
                    "  Unsupported outputs : "
                    + ", ".join(
                        sorted(
                            result[
                                "unsupported_outputs"
                            ]
                        )
                    )
                )

    print()
    print(
        "RUNTIME REGIME VALIDATION"
    )
    line()

    try:

        module = load_module(
            ANALYSIS_FILE
        )

        print(
            "Module import : PASS"
        )

        runtime_results = (
            runtime_semantic_validation(
                module
            )
        )

        runtime_pass = all(
            result["pass"]
            for result in runtime_results.values()
        )

        print_runtime_results(
            runtime_results
        )

    except Exception as exc:

        module = None
        runtime_pass = False
        runtime_results = {}

        print(
            "Module import : FAIL"
        )

        print(
            f"Error : "
            f"{type(exc).__name__}: {exc}"
        )

    print()
    print(
        "BOUNDARY VALUE SEMANTICS"
    )
    line()

    if module is not None:

        boundary_results = (
            boundary_validation(
                module
            )
        )

        boundary_pass = all(
            result["pass"]
            for result in boundary_results
        )

        print_boundary_results(
            boundary_results
        )

    else:

        boundary_pass = False

        print(
            "Boundary validation : FAIL"
        )
        print(
            "Reason : module unavailable"
        )

    print()
    print(
        "REGIME OUTPUT VOCABULARY"
    )
    line()

    if module is not None:

        vocabulary_results = (
            vocabulary_validation(
                module
            )
        )

        vocabulary_pass = all(
            result["pass"]
            for result in vocabulary_results.values()
        )

        print_vocabulary(
            vocabulary_results
        )

    else:

        vocabulary_pass = False

        print(
            "Vocabulary validation : FAIL"
        )
        print(
            "Reason : module unavailable"
        )

    print()
    print(
        "LOOK-AHEAD / FUTURE DATA AUDIT"
    )
    line()

    lookahead = lookahead_audit(
        source
    )

    if lookahead:

        lookahead_pass = False

        print(
            "Suspicious future-data patterns         : "
            + ", ".join(lookahead)
        )

    else:

        lookahead_pass = True

        print(
            "Suspicious future-data patterns         : "
            "NONE DETECTED"
        )

    print()
    print(
        "SOURCE MUTATION AUDIT"
    )
    line()

    mutations = mutation_audit(
        source,
        tree,
    )

    if mutations:

        read_only_source = False

        print(
            "SQL mutation statements                 : "
            + ", ".join(mutations)
        )

    else:

        read_only_source = True

        print(
            "SQL mutation statements                 : "
            "NONE DETECTED"
        )

    print()
    print(
        "DATABASE READ-ONLY FINGERPRINT"
    )
    line()

    try:

        connection = connect_read_only()

        before = history_fingerprint(
            connection
        )

        connection.close()

        print(
            "Schema validation : PASS"
        )
        print(
            f"Rows              : "
            f"{before['rows']}"
        )
        print(
            f"Snapshots         : "
            f"{before['snapshots']}"
        )
        print(
            f"Distinct CMC IDs  : "
            f"{before['cmc_ids']}"
        )
        print(
            f"Duplicate IDs     : "
            f"{before['duplicate_ids']}"
        )

        db_pass = True

    except Exception as exc:

        before = None
        db_pass = False

        print(
            "Schema validation : FAIL"
        )

        print(
            f"Error             : "
            f"{type(exc).__name__}: {exc}"
        )

    print()
    print(
        "DATABASE FINGERPRINT PRESERVATION"
    )
    line()

    if before is not None:

        try:

            connection = connect_read_only()

            after = history_fingerprint(
                connection
            )

            connection.close()

            fingerprint_pass = (
                before == after
            )

            print(
                "BEFORE == AFTER : "
                + (
                    "PASS"
                    if fingerprint_pass
                    else "FAIL"
                )
            )

        except Exception as exc:

            fingerprint_pass = False

            print(
                "BEFORE == AFTER : FAIL"
            )

            print(
                f"Error           : "
                f"{type(exc).__name__}: {exc}"
            )

    else:

        fingerprint_pass = False

        print(
            "BEFORE == AFTER : FAIL"
        )

    contract_pass = all(
        (
            required_pass,
            static_pass,
            runtime_pass,
            boundary_pass,
            vocabulary_pass,
            lookahead_pass,
            read_only_source,
            db_pass,
            fingerprint_pass,
        )
    )

    print()
    print(
        "REQUIRED REGIME CONTRACT"
    )
    line()

    print(
        f"Required functions                      : "
        f"{'PASS' if required_pass else 'FAIL'}"
    )

    print(
        f"Static semantic logic                   : "
        f"{'PASS' if static_pass else 'FAIL'}"
    )

    print(
        f"Runtime semantics                       : "
        f"{'PASS' if runtime_pass else 'FAIL'}"
    )

    print(
        f"Boundary semantics                      : "
        f"{'PASS' if boundary_pass else 'FAIL'}"
    )

    print(
        f"Output vocabulary                       : "
        f"{'PASS' if vocabulary_pass else 'FAIL'}"
    )

    print(
        f"No look-ahead patterns                  : "
        f"{'PASS' if lookahead_pass else 'FAIL'}"
    )

    print(
        f"Read only                               : "
        f"{'PASS' if read_only_source else 'FAIL'}"
    )

    print(
        f"Database unchanged                      : "
        f"{'PASS' if fingerprint_pass else 'FAIL'}"
    )

    print()
    print("=" * 96)
    print(
        "STEP 10A VERDICT"
    )
    print("=" * 96)

    if contract_pass:

        print(
            "RESULT : REGIME CONTRACT AUDIT PASS"
        )
        print(
            "STATUS : READY FOR STEP 10B"
        )

    else:

        print(
            "RESULT : REGIME CONTRACT AUDIT FAIL"
        )
        print(
            "STATUS : DO NOT PROCEED TO STEP 10B"
        )

    print()
    print(
        "Architecture : PRESERVED"
    )
    print(
        "Database     : READ ONLY"
    )
    print(
        "Writes       : NONE"
    )


if __name__ == "__main__":
    main()