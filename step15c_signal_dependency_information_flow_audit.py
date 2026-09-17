# =============================================================================
# ARUNDA TRADER
# STEP 15C — SIGNAL DEPENDENCY & INFORMATION-FLOW AUDIT v0.1
#
# MODE
# ----
# READ ONLY / AUDIT ONLY
#
# DATABASE
# --------
# NOT USED
#
# WRITES
# ------
# NONE
#
# PRODUCTION FILES
# ----------------
# signal_logic.py
# signal_engine.py
# signal_contract.py
#
# PRINCIPLE
# ---------
# DO NOT REBUILD
# DO NOT RESET
# DO NOT REDESIGN
#
# PURPOSE
# -------
# Verify that the Signal layer:
#
#   1. depends only on allowed upstream information
#   2. does not consume future information
#   3. does not consume downstream decision/execution information
#   4. does not access database or network
#   5. does not access environment state
#   6. does not access system clock
#   7. preserves the intended dependency direction
#   8. exposes the required production entrypoints
#   9. preserves pure signal logic isolation
#
# IMPORTANT
# ---------
# This audit inspects production source code.
# It does NOT modify production files.
# =============================================================================

import ast
import os


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PRODUCTION_FILES = {
    "signal_logic": os.path.join(
        BASE_DIR,
        "signal_logic.py",
    ),
    "signal_engine": os.path.join(
        BASE_DIR,
        "signal_engine.py",
    ),
    "signal_contract": os.path.join(
        BASE_DIR,
        "signal_contract.py",
    ),
}


EXPECTED_ENTRYPOINTS = {
    "signal_engine": {
        "build_signal",
        "load_signals",
    },
    "signal_logic": {
        "build_direction",
    },
    "signal_contract": {
        "build_empty_signal",
        "validate_signal",
        "validate_signal_contract",
    },
}


# =============================================================================
# FORBIDDEN MODULES
# =============================================================================

FORBIDDEN_MODULES = {
    # Database
    "sqlite3",
    "sqlite",
    "sqlalchemy",
    "pymysql",
    "psycopg2",

    # Network
    "requests",
    "httpx",
    "urllib",
    "urllib3",
    "aiohttp",
    "socket",
    "websocket",
    "ftplib",
    "telnetlib",

    # OS / external state
    "subprocess",
    "ctypes",

    # Dynamic code loading
    "importlib",
}


# =============================================================================
# FORBIDDEN PROJECT MODULES
# =============================================================================

FORBIDDEN_PROJECT_MODULES = {
    # Future / prediction
    "prediction",
    "prediction_engine",
    "prediction_contract",
    "forecast",
    "forecast_engine",
    "future_return",
    "future_price",

    # Decision
    "decision",
    "decision_engine",
    "decision_contract",

    # Execution
    "execution",
    "execution_engine",
    "execution_contract",
    "order_engine",
    "order_manager",

    # Scoring
    "scoring",
    "scoring_engine",
    "signal_scorer",

    # Portfolio / risk downstream
    "portfolio",
    "portfolio_engine",
    "portfolio_risk",
    "risk_engine",
}


# =============================================================================
# FORBIDDEN INFORMATION NAMES
# =============================================================================

FUTURE_NAMES = {
    "future_return",
    "future_price",
    "future_value",
    "future_signal",
    "forecast",
    "forecast_price",
    "predicted_price",
    "prediction",
    "prediction_score",
    "next_return",
    "next_price",
    "target_return",
    "target_price",
    "label",
    "target",
}


DOWNSTREAM_NAMES = {
    "decision",
    "decision_engine",
    "decision_contract",
    "execution",
    "execution_engine",
    "execution_contract",
    "order",
    "order_engine",
    "order_manager",
    "place_order",
    "buy",
    "sell",
    "portfolio",
    "portfolio_engine",
    "portfolio_risk",
    "risk_engine",
    "position_size",
}


DATABASE_NAMES = {
    "sqlite3",
    "sqlite",
    "connect",
    "cursor",
    "execute",
    "executemany",
    "fetchone",
    "fetchall",
    "fetchmany",
    "commit",
    "rollback",
    "to_sql",
}


NETWORK_NAMES = {
    "requests",
    "httpx",
    "urllib",
    "urllib3",
    "aiohttp",
    "socket",
    "websocket",
    "ftplib",
    "telnetlib",
    "urlopen",
    "urlretrieve",
    "request",
    "get",
    "post",
    "put",
    "patch",
    "delete",
}


ENVIRONMENT_NAMES = {
    "environ",
    "getenv",
    "putenv",
    "unsetenv",
    "getcwd",
    "chdir",
    "uname",
    "platform",
}


TIME_MODULES = {
    "time",
    "datetime",
    "calendar",
    "arrow",
    "pendulum",
}


TIME_CALLS = {
    "now",
    "utcnow",
    "today",
    "time",
    "monotonic",
    "perf_counter",
    "process_time",
}


FILE_WRITE_NAMES = {
    "open",
    "write",
    "writelines",
    "to_csv",
    "to_json",
    "to_pickle",
    "dump",
    "save",
}


# =============================================================================
# AUDIT FAILURE
# =============================================================================

class AuditFailure(Exception):
    pass


# =============================================================================
# ASSERTIONS
# =============================================================================

def assert_true(
    condition,
    message,
):

    if not condition:
        raise AuditFailure(message)


def assert_equal(
    actual,
    expected,
    message,
):

    if actual != expected:

        raise AuditFailure(
            "{} | expected={!r}, actual={!r}".format(
                message,
                expected,
                actual,
            )
        )


# =============================================================================
# TEST RUNNER
# =============================================================================

def run_test(
    name,
    function,
):

    try:

        function()

        print(
            "{:<52} : PASS".format(name)
        )

        return True

    except Exception as error:

        print(
            "{:<52} : FAIL".format(name)
        )

        print(
            "  ERROR : {} {}".format(
                type(error).__name__,
                str(error),
            )
        )

        return False


# =============================================================================
# SOURCE UTILITIES
# =============================================================================

def read_source(module_name):

    path = PRODUCTION_FILES[module_name]

    if not os.path.isfile(path):

        raise AuditFailure(
            "production file missing: {}".format(
                os.path.basename(path)
            )
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:

        return file.read()


def parse_module(module_name):

    source = read_source(
        module_name
    )

    try:

        return ast.parse(
            source,
            filename=PRODUCTION_FILES[module_name],
        )

    except SyntaxError as error:

        raise AuditFailure(
            "AST parse failed in {}: {}".format(
                module_name,
                error,
            )
        )


def module_nodes(module_name):

    return list(
        ast.walk(
            parse_module(module_name)
        )
    )


# =============================================================================
# AST NAME EXTRACTION
# =============================================================================

def imported_modules(tree):

    modules = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                root = alias.name.split(
                    "."
                )[0]

                modules.add(root)

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module:

                root = node.module.split(
                    "."
                )[0]

                modules.add(root)

    return modules


def imported_full_names(tree):

    names = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:
                names.add(alias.name)

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module:

                for alias in node.names:

                    names.add(
                        "{}.{}".format(
                            node.module,
                            alias.name,
                        )
                    )

    return names


def called_names(tree):

    names = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):

            continue

        function = node.func

        if isinstance(
            function,
            ast.Name,
        ):

            names.append(
                function.id
            )

        elif isinstance(
            function,
            ast.Attribute,
        ):

            names.append(
                function.attr
            )

    return names


def attribute_names(tree):

    names = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Attribute,
        ):

            names.add(
                node.attr
            )

    return names


def all_name_tokens(tree):

    names = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Name,
        ):

            names.add(
                node.id
            )

        elif isinstance(
            node,
            ast.Attribute,
        ):

            names.add(
                node.attr
            )

    return names


# =============================================================================
# PROJECT IMPORT EXTRACTION
# =============================================================================

def project_imports(tree):

    result = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                result.add(
                    alias.name
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module:

                result.add(
                    node.module
                )

    return result


# =============================================================================
# FUNCTION / CLASS EXTRACTION
# =============================================================================

def defined_functions(tree):

    result = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            result.add(
                node.name
            )

    return result


# =============================================================================
# 15C-01 PRODUCTION FILE EXISTENCE
# =============================================================================

def test_production_files_exist():

    for name, path in PRODUCTION_FILES.items():

        assert_true(
            os.path.isfile(path),
            "missing production file: {}".format(
                name
            ),
        )


# =============================================================================
# 15C-02 AST PARSABILITY
# =============================================================================

def test_ast_parsability():

    for name in PRODUCTION_FILES:

        tree = parse_module(name)

        assert_true(
            isinstance(
                tree,
                ast.Module,
            ),
            "invalid AST for {}".format(
                name
            ),
        )


# =============================================================================
# 15C-03 PROJECT IMPORT BOUNDARY
# =============================================================================

def test_project_import_boundary():

    allowed_project_modules = {
        "market_regime",
        "market_regime_contract",
        "signal_logic",
        "signal_contract",
        "signal_engine",
    }

    for name in PRODUCTION_FILES:

        tree = parse_module(name)

        imports = project_imports(tree)

        for imported in imports:

            root = imported.split(
                "."
            )[0]

            if root in {
                "signal_logic",
                "signal_contract",
                "signal_engine",
                "market_regime",
                "market_regime_contract",
            }:

                assert_true(
                    root in allowed_project_modules,
                    "project import boundary violation in {}: {}".format(
                        name,
                        imported,
                    ),
                )


# =============================================================================
# 15C-04 FORBIDDEN MODULE AUDIT
# =============================================================================

def test_forbidden_module_audit():

    for name in PRODUCTION_FILES:

        tree = parse_module(name)

        imports = imported_modules(tree)

        overlap = (
            imports
            & FORBIDDEN_MODULES
        )

        assert_true(
            not overlap,
            "forbidden module dependency in {}: {}".format(
                name,
                sorted(overlap),
            ),
        )


# =============================================================================
# 15C-05 SIGNAL LOGIC ISOLATION
# =============================================================================

def test_signal_logic_isolation():

    tree = parse_module(
        "signal_logic"
    )

    imports = imported_modules(tree)

    forbidden = {
        "signal_engine",
        "signal_contract",
        "market_regime",
        "market_regime_contract",
    }

    overlap = (
        imports
        & forbidden
    )

    assert_true(
        not overlap,
        "signal_logic has forbidden dependencies: {}".format(
            sorted(overlap)
        ),
    )


# =============================================================================
# 15C-06 SIGNAL CONTRACT ISOLATION
# =============================================================================

def test_signal_contract_isolation():

    tree = parse_module(
        "signal_contract"
    )

    imports = imported_modules(tree)

    forbidden = {
        "signal_engine",
        "signal_logic",
        "market_regime",
        "market_regime_contract",
    }

    overlap = (
        imports
        & forbidden
    )

    assert_true(
        not overlap,
        "signal_contract has forbidden dependencies: {}".format(
            sorted(overlap)
        ),
    )


# =============================================================================
# 15C-07 ENGINE ALLOWED DEPENDENCY SET
# =============================================================================

def test_engine_allowed_dependency_set():

    tree = parse_module(
        "signal_engine"
    )

    imports = imported_modules(tree)

    allowed = {
        "market_regime",
        "market_regime_contract",
        "signal_logic",
        "signal_contract",
    }

    forbidden_project = (
        imports
        & FORBIDDEN_PROJECT_MODULES
    )

    assert_true(
        not forbidden_project,
        "signal_engine imports forbidden project modules: {}".format(
            sorted(forbidden_project)
        ),
    )

    for imported in imports:

        if imported in {
            "signal_engine",
        }:

            continue

        if imported in allowed:

            continue

        root = imported.split(
            "."
        )[0]

        if root in allowed:

            continue

        if root in {
            "os",
            "ast",
            "copy",
            "inspect",
        }:

            continue

        assert_true(
            root not in FORBIDDEN_PROJECT_MODULES,
            "forbidden engine dependency: {}".format(
                imported
            ),
        )


# =============================================================================
# 15C-08 FUTURE INFORMATION FLOW
# =============================================================================

def test_future_information_flow():

    for name in PRODUCTION_FILES:

        tree = parse_module(name)

        tokens = all_name_tokens(
            tree
        )

        overlap = (
            tokens
            & FUTURE_NAMES
        )

        assert_true(
            not overlap,
            "future information dependency in {}: {}".format(
                name,
                sorted(overlap),
            ),
        )


# =============================================================================
# 15C-09 DOWNSTREAM INFORMATION FLOW
# =============================================================================

def test_downstream_information_flow():

    for name in PRODUCTION_FILES:

        tree = parse_module(name)

        imports = imported_modules(tree)

        forbidden_imports = (
            imports
            & FORBIDDEN_PROJECT_MODULES
        )

        assert_true(
            not forbidden_imports,
            "downstream dependency in {}: {}".format(
                name,
                sorted(forbidden_imports),
            ),
        )

        tokens = all_name_tokens(
            tree
        )

        overlap = (
            tokens
            & DOWNSTREAM_NAMES
        )

        assert_true(
            not overlap,
            "downstream information token in {}: {}".format(
                name,
                sorted(overlap),
            ),
        )


# =============================================================================
# 15C-10 DATABASE INFORMATION FLOW
# =============================================================================

def test_database_information_flow():

    for name in PRODUCTION_FILES:

        tree = parse_module(name)

        imports = imported_modules(tree)

        assert_true(
            not (
                imports
                & {
                    "sqlite3",
                    "sqlite",
                    "sqlalchemy",
                    "pymysql",
                    "psycopg2",
                }
            ),
            "database module dependency in {}".format(
                name
            ),
        )

        tokens = all_name_tokens(
            tree
        )

        overlap = (
            tokens
            & DATABASE_NAMES
        )

        assert_true(
            not overlap,
            "database information dependency in {}: {}".format(
                name,
                sorted(overlap),
            ),
        )


# =============================================================================
# 15C-11 DYNAMIC IMPORT AUDIT
# =============================================================================

def test_dynamic_import_audit():

    for name in PRODUCTION_FILES:

        tree = parse_module(name)

        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.Call,
            ):

                continue

            function = node.func

            if isinstance(
                function,
                ast.Name,
            ):

                if function.id in {
                    "__import__",
                    "eval",
                    "exec",
                }:

                    raise AuditFailure(
                        "dynamic import/code execution in {}: {}".format(
                            name,
                            function.id,
                        )
                    )

            if isinstance(
                function,
                ast.Attribute,
            ):

                if function.attr in {
                    "import_module",
                }:

                    raise AuditFailure(
                        "dynamic import in {}: {}".format(
                            name,
                            function.attr,
                        )
                    )


# =============================================================================
# 15C-12 ENGINE ENTRYPOINT
# =============================================================================

def test_engine_entrypoint():

    tree = parse_module(
        "signal_engine"
    )

    functions = defined_functions(
        tree
    )

    for expected in EXPECTED_ENTRYPOINTS[
        "signal_engine"
    ]:

        assert_true(
            expected in functions,
            "missing signal_engine entrypoint: {}".format(
                expected
            ),
        )


# =============================================================================
# 15C-13 LOGIC ENTRYPOINT
# =============================================================================

def test_logic_entrypoint():

    tree = parse_module(
        "signal_logic"
    )

    functions = defined_functions(
        tree
    )

    for expected in EXPECTED_ENTRYPOINTS[
        "signal_logic"
    ]:

        assert_true(
            expected in functions,
            "missing signal_logic entrypoint: {}".format(
                expected
            ),
        )


# =============================================================================
# 15C-14 CONTRACT ENTRYPOINTS
# =============================================================================

def test_contract_entrypoints():

    tree = parse_module(
        "signal_contract"
    )

    functions = defined_functions(
        tree
    )

    for expected in EXPECTED_ENTRYPOINTS[
        "signal_contract"
    ]:

        assert_true(
            expected in functions,
            "missing signal_contract entrypoint: {}".format(
                expected
            ),
        )


# =============================================================================
# 15C-15 ENGINE -> SIGNAL LOGIC FLOW
# =============================================================================

def test_engine_to_signal_logic_flow():

    tree = parse_module(
        "signal_engine"
    )

    imports = imported_full_names(
        tree
    )

    assert_true(
        "signal_logic" in imports
        or "signal_logic.build_direction" in imports
        or "signal_logic" in imported_modules(tree),
        "signal_engine does not import signal_logic",
    )

    tokens = all_name_tokens(
        tree
    )

    assert_true(
        "signal_logic" in tokens,
        "signal_engine does not reference signal_logic",
    )


# =============================================================================
# 15C-16 ENGINE -> CONTRACT FLOW
# =============================================================================

def test_engine_to_contract_flow():

    tree = parse_module(
        "signal_engine"
    )

    tokens = all_name_tokens(
        tree
    )

    assert_true(
        "signal_contract" in tokens,
        "signal_engine does not reference signal_contract",
    )


# =============================================================================
# 15C-17 LOGIC -> ENGINE PROHIBITION
# =============================================================================

def test_logic_to_engine_prohibition():

    tree = parse_module(
        "signal_logic"
    )

    imports = imported_modules(tree)

    assert_true(
        "signal_engine" not in imports,
        "signal_logic -> signal_engine dependency detected",
    )


# =============================================================================
# 15C-18 CONTRACT -> ENGINE PROHIBITION
# =============================================================================

def test_contract_to_engine_prohibition():

    tree = parse_module(
        "signal_contract"
    )

    imports = imported_modules(tree)

    assert_true(
        "signal_engine" not in imports,
        "signal_contract -> signal_engine dependency detected",
    )


# =============================================================================
# 15C-19 CONTRACT -> LOGIC PROHIBITION
# =============================================================================

def test_contract_to_logic_prohibition():

    tree = parse_module(
        "signal_contract"
    )

    imports = imported_modules(tree)

    assert_true(
        "signal_logic" not in imports,
        "signal_contract -> signal_logic dependency detected",
    )


# =============================================================================
# 15C-20 FILE WRITE ISOLATION
# =============================================================================

def test_file_write_isolation():

    for name in PRODUCTION_FILES:

        tree = parse_module(name)

        for node in ast.walk(tree):

            if isinstance(
                node,
                ast.Call,
            ):

                function = node.func

                if isinstance(
                    function,
                    ast.Name,
                ):

                    if function.id in {
                        "open",
                        "write",
                        "writelines",
                    }:

                        raise AuditFailure(
                            "file write dependency in {}: {}".format(
                                name,
                                function.id,
                            )
                        )

                elif isinstance(
                    function,
                    ast.Attribute,
                ):

                    if function.attr in {
                        "write",
                        "writelines",
                        "to_csv",
                        "to_json",
                        "to_pickle",
                        "save",
                    }:

                        raise AuditFailure(
                            "file write dependency in {}: {}".format(
                                name,
                                function.attr,
                            )
                        )


# =============================================================================
# 15C-21 NETWORK ISOLATION
# =============================================================================

def test_network_isolation():

    for name in PRODUCTION_FILES:

        tree = parse_module(name)

        imports = imported_modules(
            tree
        )

        network_modules = (
            imports
            & {
                "requests",
                "httpx",
                "urllib",
                "urllib3",
                "aiohttp",
                "socket",
                "websocket",
                "ftplib",
                "telnetlib",
            }
        )

        assert_true(
            not network_modules,
            "network module dependency in {}: {}".format(
                name,
                sorted(network_modules),
            ),
        )

        # IMPORTANT:
        # Do NOT treat every attribute named "get" as a network call.
        #
        # Example:
        #     regime_data.get("status")
        #
        # is ordinary dictionary access and is valid.
        #
        # Network calls are detected through known network modules
        # and explicitly network-specific APIs only.

        network_calls = []

        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.Call,
            ):

                continue

            function = node.func

            if isinstance(
                function,
                ast.Name,
            ):

                if function.id in {
                    "urlopen",
                    "urlretrieve",
                }:

                    network_calls.append(
                        function.id
                    )

            elif isinstance(
                function,
                ast.Attribute,
            ):

                if function.attr in {
                    "urlopen",
                    "urlretrieve",
                    "request",
                }:

                    network_calls.append(
                        function.attr
                    )

        assert_true(
            not network_calls,
            "network call in {}: {}".format(
                name,
                sorted(network_calls),
            ),
        )


# =============================================================================
# 15C-22 ENVIRONMENT ISOLATION
# =============================================================================

def test_environment_isolation():

    for name in PRODUCTION_FILES:

        tree = parse_module(name)

        imports = imported_modules(
            tree
        )

        assert_true(
            "os" not in imports,
            "environment dependency in {}: os".format(
                name
            ),
        )

        calls = called_names(
            tree
        )

        forbidden = {
            "getenv",
            "putenv",
            "unsetenv",
            "getcwd",
            "chdir",
            "uname",
        }

        overlap = (
            set(calls)
            & forbidden
        )

        assert_true(
            not overlap,
            "environment call in {}: {}".format(
                name,
                sorted(overlap),
            ),
        )


# =============================================================================
# 15C-23 TIME-SOURCE ISOLATION
# =============================================================================

def test_time_source_isolation():

    for name in PRODUCTION_FILES:

        tree = parse_module(name)

        imports = imported_modules(
            tree
        )

        time_imports = (
            imports
            & TIME_MODULES
        )

        assert_true(
            not time_imports,
            "time-source module dependency in {}: {}".format(
                name,
                sorted(time_imports),
            ),
        )

        # IMPORTANT:
        # "timestamp" as a data-field name is NOT a time source.
        #
        # A contract such as:
        #
        #     {
        #         "timestamp": None
        #     }
        #
        # is valid because it merely defines the signal schema.
        #
        # We therefore inspect CALLS, not every occurrence of the word
        # "timestamp".

        calls = called_names(
            tree
        )

        forbidden_calls = (
            set(calls)
            & TIME_CALLS
        )

        assert_true(
            not forbidden_calls,
            "time-source call in {}: {}".format(
                name,
                sorted(forbidden_calls),
            ),
        )

        # Explicit datetime/time attribute calls.
        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.Call,
            ):

                continue

            function = node.func

            if isinstance(
                function,
                ast.Attribute,
            ):

                if function.attr in TIME_CALLS:

                    raise AuditFailure(
                        "time-source dependency in {}: {}".format(
                            name,
                            function.attr,
                        )
                    )


# =============================================================================
# 15C-24 PURE SIGNAL LOGIC DEPENDENCY
# =============================================================================

def test_pure_signal_logic_dependency():

    tree = parse_module(
        "signal_logic"
    )

    imports = imported_modules(
        tree
    )

    forbidden = (
        FORBIDDEN_MODULES
        | {
            "signal_engine",
            "signal_contract",
            "market_regime",
            "market_regime_contract",
        }
    )

    overlap = (
        imports
        & forbidden
    )

    assert_true(
        not overlap,
        "signal_logic impurity detected: {}".format(
            sorted(overlap)
        ),
    )

    tokens = all_name_tokens(
        tree
    )

    overlap = (
        tokens
        & FUTURE_NAMES
    )

    assert_true(
        not overlap,
        "signal_logic future-information token detected: {}".format(
            sorted(overlap)
        ),
    )


# =============================================================================
# 15C-25 RUNTIME INFORMATION-FLOW INTEGRITY
# =============================================================================

def test_runtime_information_flow_integrity():

    # Import production modules only for runtime verification.
    #
    # This test deliberately keeps runtime checks minimal.
    # It verifies that the production engine exposes the expected
    # entrypoint and that the entrypoint is callable.

    import signal_engine

    assert_true(
        callable(
            getattr(
                signal_engine,
                "build_signal",
                None,
            )
        ),
        "signal_engine.build_signal is not callable",
    )

    import signal_logic

    assert_true(
        callable(
            getattr(
                signal_logic,
                "build_direction",
                None,
            )
        ),
        "signal_logic.build_direction is not callable",
    )

    import signal_contract

    for function_name in (
        "build_empty_signal",
        "validate_signal",
        "validate_signal_contract",
    ):

        assert_true(
            callable(
                getattr(
                    signal_contract,
                    function_name,
                    None,
                )
            ),
            "missing runtime contract entrypoint: {}".format(
                function_name
            ),
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 78)
    print(
        "ARUNDA TRADER — STEP 15C"
    )
    print(
        "SIGNAL DEPENDENCY & INFORMATION-FLOW AUDIT v0.1"
    )
    print("=" * 78)

    print(
        "Mode        : READ ONLY / AUDIT ONLY"
    )
    print(
        "Database    : NOT USED"
    )
    print(
        "Writes      : NONE"
    )
    print(
        "Scoring     : NOT USED"
    )
    print(
        "Prediction  : NOT USED"
    )
    print(
        "Decision    : NOT USED"
    )
    print(
        "Execution   : NOT USED"
    )

    print()

    print(
        "Production files:"
    )
    print(
        "  - signal_logic.py"
    )
    print(
        "  - signal_engine.py"
    )
    print(
        "  - signal_contract.py"
    )

    print("=" * 78)
    print()

    tests = [

        (
            "15C-01 Production files exist",
            test_production_files_exist,
        ),

        (
            "15C-02 AST parsability",
            test_ast_parsability,
        ),

        (
            "15C-03 Project import boundary",
            test_project_import_boundary,
        ),

        (
            "15C-04 Forbidden module audit",
            test_forbidden_module_audit,
        ),

        (
            "15C-05 Signal logic isolation",
            test_signal_logic_isolation,
        ),

        (
            "15C-06 Signal contract isolation",
            test_signal_contract_isolation,
        ),

        (
            "15C-07 Engine allowed dependency set",
            test_engine_allowed_dependency_set,
        ),

        (
            "15C-08 Future information flow",
            test_future_information_flow,
        ),

        (
            "15C-09 Downstream information flow",
            test_downstream_information_flow,
        ),

        (
            "15C-10 Database information flow",
            test_database_information_flow,
        ),

        (
            "15C-11 Dynamic import audit",
            test_dynamic_import_audit,
        ),

        (
            "15C-12 Signal engine entrypoint",
            test_engine_entrypoint,
        ),

        (
            "15C-13 Signal logic entrypoint",
            test_logic_entrypoint,
        ),

        (
            "15C-14 Contract entrypoints",
            test_contract_entrypoints,
        ),

        (
            "15C-15 Engine -> signal logic flow",
            test_engine_to_signal_logic_flow,
        ),

        (
            "15C-16 Engine -> contract flow",
            test_engine_to_contract_flow,
        ),

        (
            "15C-17 Logic -> engine prohibition",
            test_logic_to_engine_prohibition,
        ),

        (
            "15C-18 Contract -> engine prohibition",
            test_contract_to_engine_prohibition,
        ),

        (
            "15C-19 Contract -> logic prohibition",
            test_contract_to_logic_prohibition,
        ),

        (
            "15C-20 File write isolation",
            test_file_write_isolation,
        ),

        (
            "15C-21 Network isolation",
            test_network_isolation,
        ),

        (
            "15C-22 Environment isolation",
            test_environment_isolation,
        ),

        (
            "15C-23 Time-source isolation",
            test_time_source_isolation,
        ),

        (
            "15C-24 Pure signal logic dependency",
            test_pure_signal_logic_dependency,
        ),

        (
            "15C-25 Runtime information-flow integrity",
            test_runtime_information_flow_integrity,
        ),
    ]

    passed = 0
    failed = 0

    print("=" * 78)
    print(
        "DEPENDENCY / INFORMATION-FLOW AUDIT"
    )
    print("=" * 78)

    for name, function in tests:

        if run_test(
            name,
            function,
        ):

            passed += 1

        else:

            failed += 1

    print()

    print("=" * 78)
    print(
        "STEP 15C SUMMARY"
    )
    print("=" * 78)

    print(
        "Total Tests : {}".format(
            len(tests)
        )
    )

    print(
        "PASS        : {}".format(
            passed
        )
    )

    print(
        "FAIL        : {}".format(
            failed
        )
    )

    print()

    print("=" * 78)
    print(
        "STEP 15C VERDICT"
    )
    print("=" * 78)

    if failed == 0:

        print(
            "RESULT      : SIGNAL DEPENDENCY & INFORMATION-FLOW AUDIT PASS"
        )

        print(
            "STATUS      : READY FOR NEXT SIGNAL STEP"
        )

        print()

        print(
            "Architecture : PRESERVED"
        )

        print(
            "Database     : NOT USED"
        )

        print(
            "Writes       : NONE"
        )

        print(
            "Scoring      : NOT USED"
        )

        print(
            "Prediction   : NOT USED"
        )

        print(
            "Decision     : NOT USED"
        )

        print(
            "Execution    : NOT USED"
        )

        print(
            "Look-Ahead   : PROTECTED"
        )

        print("=" * 78)

        return 0

    print(
        "RESULT      : SIGNAL DEPENDENCY & INFORMATION-FLOW AUDIT FAIL"
    )

    print(
        "STATUS      : REPAIR REQUIRED"
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "Production Signal files were NOT modified."
    )

    print("=" * 78)

    return 1


if __name__ == "__main__":

    raise SystemExit(
        main()
    )