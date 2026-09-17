# -*- coding: utf-8 -*-

"""
ARUNDA TECHNICAL DOWNSTREAM FORENSIC v0.1

PURPOSE
-------
Discover the exact production downstream path after:

    validate_row(row, columns)
        ->
    (score, status, flags)
        ->
    eligible / rejected / reason

CRITICAL RULES
--------------
READ ONLY.

Production modules are NOT imported.
Production main() is NOT executed.
Database is opened SQLite mode=ro.
No database write operation is allowed.

This version performs AST forensic discovery first.

It does NOT guess the downstream function name.

It searches the REAL production source for:

    1. validate_row(...) calls
    2. assignments from validate_row(...)
    3. tuple unpacking
    4. variables carrying:
           score
           status
           flags
    5. conditions involving those variables
    6. eligible / rejected / reason variables
    7. return values containing those concepts
    8. function boundaries containing the downstream logic

Only after the exact downstream boundary is resolved should
runtime execution be added.
"""

import ast
import hashlib
import sqlite3
import sys
import traceback
from pathlib import Path


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_DIR = Path(__file__).resolve().parent

ENGINE_FILE = (
    PROJECT_DIR /
    "market_technical_engine.py"
)

DATABASE_FILE = (
    PROJECT_DIR /
    "arunda.db"
)

TARGET_TABLE = "market_technical"

VALIDATOR_SYMBOL = "validate_row"

CONTRACT_TECHNICAL_VERSION = "TECHNICAL_v0.5"
CONTRACT_ENGINE_VERSION = "TECHNICAL_v0.5"
CONTRACT_SOURCE = "REAL_MARKET_HISTORY"

EXPECTED_CONTRACT_ROWS = 987


# =============================================================================
# OUTPUT
# =============================================================================

def banner(title):

    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def kv(key, value):

    print(
        f"{key:<60} {value}"
    )


def passed(message):

    print(
        f"[PASS] {message}"
    )


def failed(message):

    raise RuntimeError(
        message
    )


# =============================================================================
# HASH
# =============================================================================

def sha256_file(path):

    h = hashlib.sha256()

    with open(
        path,
        "rb"
    ) as f:

        while True:

            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            h.update(
                chunk
            )

    return h.hexdigest()


def semantic_hash(node):

    payload = ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


# =============================================================================
# SOURCE
# =============================================================================

def read_source():

    if not ENGINE_FILE.exists():

        failed(
            f"Production engine not found: "
            f"{ENGINE_FILE}"
        )

    return ENGINE_FILE.read_text(
        encoding="utf-8-sig",
        errors="strict",
    )


def parse_source(source):

    try:

        return ast.parse(
            source,
            filename=str(
                ENGINE_FILE
            ),
        )

    except SyntaxError as exc:

        failed(
            f"Production AST parse failed: {exc}"
        )


# =============================================================================
# FUNCTION INDEX
# =============================================================================

def index_functions(tree):

    functions = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            functions.append(
                node
            )

    return functions


def function_name(node):

    return node.name


def node_end(node):

    return getattr(
        node,
        "end_lineno",
        node.lineno,
    )


def enclosing_function(
    node,
    functions,
):

    candidates = []

    if not hasattr(
        node,
        "lineno",
    ):

        return None

    line = node.lineno

    for function in functions:

        start = function.lineno
        end = node_end(function)

        if start <= line <= end:

            candidates.append(
                function
            )

    if not candidates:

        return None

    return max(
        candidates,
        key=lambda item: item.lineno,
    )


# =============================================================================
# VALIDATE_ROW CALL DISCOVERY
# =============================================================================

def discover_validate_row_calls(
    tree,
    functions,
):

    matches = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):

            continue

        if not isinstance(
            node.func,
            ast.Name,
        ):

            continue

        if node.func.id != VALIDATOR_SYMBOL:

            continue

        owner = enclosing_function(
            node,
            functions,
        )

        matches.append(
            {
                "node": node,
                "function": (
                    owner.name
                    if owner
                    else "<MODULE>"
                ),
                "line": node.lineno,
                "col": node.col_offset,
            }
        )

    return matches


# =============================================================================
# ASSIGNMENT DISCOVERY
# =============================================================================

def assignment_target_names(target):

    names = []

    for node in ast.walk(
        target
    ):

        if isinstance(
            node,
            ast.Name,
        ):

            names.append(
                node.id
            )

    return names


def discover_validator_assignments(
    tree,
    functions,
):

    matches = []

    for node in ast.walk(tree):

        value = None

        if isinstance(
            node,
            ast.Assign,
        ):

            value = node.value
            targets = node.targets

        elif isinstance(
            node,
            ast.AnnAssign,
        ):

            value = node.value
            targets = [node.target]

        else:

            continue

        if not isinstance(
            value,
            ast.Call,
        ):

            continue

        if not isinstance(
            value.func,
            ast.Name,
        ):

            continue

        if value.func.id != VALIDATOR_SYMBOL:

            continue

        target_names = []

        for target in targets:

            target_names.extend(
                assignment_target_names(
                    target
                )
            )

        owner = enclosing_function(
            node,
            functions,
        )

        matches.append(
            {
                "line": node.lineno,
                "function": (
                    owner.name
                    if owner
                    else "<MODULE>"
                ),
                "targets": target_names,
                "node": node,
            }
        )

    return matches


# =============================================================================
# DATAFLOW VARIABLE DISCOVERY
# =============================================================================

def discover_score_status_flags(
    tree,
    functions,
):

    keywords = {
        "score",
        "status",
        "flags",
        "eligible",
        "rejected",
        "reason",
        "decision",
    }

    findings = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Name,
        ):

            continue

        if node.id not in keywords:

            continue

        owner = enclosing_function(
            node,
            functions,
        )

        context = type(
            node.parent
        ).__name__ if hasattr(
            node,
            "parent"
        ) else None

        findings.append(
            {
                "name": node.id,
                "line": node.lineno,
                "context": context,
                "function": (
                    owner.name
                    if owner
                    else "<MODULE>"
                ),
            }
        )

    return findings


# =============================================================================
# PARENT POINTERS
# =============================================================================

def attach_parents(tree):

    for parent in ast.walk(
        tree
    ):

        for child in ast.iter_child_nodes(
            parent
        ):

            child.parent = parent


# =============================================================================
# CONDITIONAL DISCOVERY
# =============================================================================

def expression_names(node):

    names = []

    for child in ast.walk(
        node
    ):

        if isinstance(
            child,
            ast.Name,
        ):

            names.append(
                child.id
            )

    return sorted(
        set(names)
    )


def discover_relevant_conditions(
    tree,
    functions,
):

    keywords = {
        "score",
        "status",
        "flags",
        "eligible",
        "rejected",
        "reason",
        "decision",
    }

    findings = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.If,
                ast.IfExp,
                ast.While,
                ast.Assert,
            ),
        ):

            continue

        names = set(
            expression_names(
                node.test
            )
        )

        relevant = (
            names & keywords
        )

        if not relevant:

            continue

        owner = enclosing_function(
            node,
            functions,
        )

        findings.append(
            {
                "line": node.lineno,
                "function": (
                    owner.name
                    if owner
                    else "<MODULE>"
                ),
                "names": sorted(
                    relevant
                ),
                "test": ast.unparse(
                    node.test
                ),
                "node": node,
            }
        )

    return findings


# =============================================================================
# RETURN DISCOVERY
# =============================================================================

def discover_relevant_returns(
    tree,
    functions,
):

    keywords = {
        "score",
        "status",
        "flags",
        "eligible",
        "rejected",
        "reason",
        "decision",
    }

    findings = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Return,
        ):

            continue

        if node.value is None:

            continue

        names = set(
            expression_names(
                node.value
            )
        )

        relevant = (
            names & keywords
        )

        if not relevant:

            continue

        owner = enclosing_function(
            node,
            functions,
        )

        findings.append(
            {
                "line": node.lineno,
                "function": (
                    owner.name
                    if owner
                    else "<MODULE>"
                ),
                "names": sorted(
                    relevant
                ),
                "return": ast.unparse(
                    node.value
                ),
            }
        )

    return findings


# =============================================================================
# SOURCE WINDOW
# =============================================================================

def print_source_window(
    source,
    start_line,
    end_line,
    title,
):

    banner(
        title
    )

    lines = source.splitlines()

    start = max(
        1,
        start_line - 15
    )

    end = min(
        len(lines),
        end_line + 15
    )

    for number in range(
        start,
        end + 1
    ):

        print(
            f"{number:6d}: "
            f"{lines[number - 1]}"
        )


# =============================================================================
# DATABASE READ-ONLY
# =============================================================================

def connect_read_only():

    uri = (
        "file:"
        + str(
            DATABASE_FILE.resolve()
        ).replace(
            "\\",
            "/"
        )
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA query_only = 1"
    )

    value = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    if value != 1:

        conn.close()

        failed(
            "SQLite query_only != 1"
        )

    return conn


# =============================================================================
# REAL CONTRACT ROW COUNT
# =============================================================================

def verify_database_contract(
    conn
):

    banner(
        "REAL DATABASE CONTRACT"
    )

    total = conn.execute(
        f'''
        SELECT COUNT(*)
        FROM "{TARGET_TABLE}"
        '''
    ).fetchone()[0]

    contract = conn.execute(
        f'''
        SELECT COUNT(*)
        FROM "{TARGET_TABLE}"
        WHERE technical_version = ?
          AND engine_version = ?
          AND source = ?
        ''',
        (
            CONTRACT_TECHNICAL_VERSION,
            CONTRACT_ENGINE_VERSION,
            CONTRACT_SOURCE,
        ),
    ).fetchone()[0]

    kv(
        "Database Total",
        total
    )

    kv(
        "TECHNICAL_v0.5 Contract",
        contract
    )

    if contract != EXPECTED_CONTRACT_ROWS:

        failed(
            f"Expected {EXPECTED_CONTRACT_ROWS} "
            f"contract rows, got {contract}"
        )

    passed(
        f"REAL contract population = {contract}"
    )


# =============================================================================
# AST REPORT
# =============================================================================

def print_ast_report(
    source,
    tree,
):

    functions = index_functions(
        tree
    )

    calls = discover_validate_row_calls(
        tree,
        functions,
    )

    assignments = (
        discover_validator_assignments(
            tree,
            functions,
        )
    )

    variables = (
        discover_score_status_flags(
            tree,
            functions,
        )
    )

    conditions = (
        discover_relevant_conditions(
            tree,
            functions,
        )
    )

    returns = (
        discover_relevant_returns(
            tree,
            functions,
        )
    )

    # -------------------------------------------------------------------------
    # VALIDATE_ROW CALLS
    # -------------------------------------------------------------------------

    banner(
        "AST VALIDATE_ROW() CALL DISCOVERY"
    )

    kv(
        "validate_row() calls found",
        len(calls)
    )

    if not calls:

        failed(
            "No validate_row() call found."
        )

    for item in calls:

        print()

        kv(
            "Function",
            item["function"]
        )

        kv(
            "Line",
            item["line"]
        )

        kv(
            "Column",
            item["col"]
        )

        passed(
            "validate_row() call found"
        )

    # -------------------------------------------------------------------------
    # DIRECT ASSIGNMENTS
    # -------------------------------------------------------------------------

    banner(
        "AST VALIDATOR OUTPUT ASSIGNMENT DISCOVERY"
    )

    kv(
        "Direct assignments",
        len(assignments)
    )

    for item in assignments:

        print()

        kv(
            "Function",
            item["function"]
        )

        kv(
            "Line",
            item["line"]
        )

        kv(
            "Targets",
            item["targets"]
        )

        source_line = source.splitlines()[
            item["line"] - 1
        ]

        print(
            "SOURCE:"
        )

        print(
            source_line
        )

    if not assignments:

        print(
            "[INFO] No direct assignment found."
        )

    # -------------------------------------------------------------------------
    # KEYWORD VARIABLES
    # -------------------------------------------------------------------------

    banner(
        "AST DOWNSTREAM VARIABLE DISCOVERY"
    )

    grouped = {}

    for item in variables:

        key = item["function"]

        grouped.setdefault(
            key,
            []
        ).append(
            item
        )

    for function_name, items in grouped.items():

        names = sorted(
            set(
                item["name"]
                for item in items
            )
        )

        print()

        kv(
            "Function",
            function_name
        )

        kv(
            "Relevant symbols",
            ", ".join(names)
        )

        for item in items:

            print(
                f"  line={item['line']:<6} "
                f"name={item['name']:<12} "
                f"context={item['context']}"
            )

    # -------------------------------------------------------------------------
    # CONDITIONS
    # -------------------------------------------------------------------------

    banner(
        "AST ELIGIBILITY / REJECTION CONDITION DISCOVERY"
    )

    kv(
        "Relevant conditions",
        len(conditions)
    )

    for item in conditions:

        print()

        kv(
            "Function",
            item["function"]
        )

        kv(
            "Line",
            item["line"]
        )

        kv(
            "Symbols",
            ", ".join(
                item["names"]
            )
        )

        kv(
            "Condition",
            item["test"]
        )

    # -------------------------------------------------------------------------
    # RETURNS
    # -------------------------------------------------------------------------

    banner(
        "AST DOWNSTREAM RETURN DISCOVERY"
    )

    kv(
        "Relevant returns",
        len(returns)
    )

    for item in returns:

        print()

        kv(
            "Function",
            item["function"]
        )

        kv(
            "Line",
            item["line"]
        )

        kv(
            "Symbols",
            ", ".join(
                item["names"]
            )
        )

        kv(
            "Return",
            item["return"]
        )

    # -------------------------------------------------------------------------
    # EXACT SOURCE WINDOWS
    # -------------------------------------------------------------------------

    for item in calls:

        owner = None

        for function in functions:

            if (
                function.name
                == item["function"]
            ):

                owner = function
                break

        if owner is not None:

            print_source_window(
                source,
                owner.lineno,
                node_end(owner),
                (
                    "EXACT DOWNSTREAM CANDIDATE SOURCE: "
                    + owner.name
                ),
            )

    return {
        "functions": functions,
        "calls": calls,
        "assignments": assignments,
        "variables": variables,
        "conditions": conditions,
        "returns": returns,
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL DOWNSTREAM FORENSIC v0.1"
    )

    kv(
        "MODE",
        "READ ONLY / AST DISCOVERY"
    )

    kv(
        "Production Engine",
        ENGINE_FILE
    )

    kv(
        "Database",
        DATABASE_FILE
    )

    kv(
        "Target",
        TARGET_TABLE
    )

    kv(
        "Validator",
        VALIDATOR_SYMBOL
    )

    print()

    print(
        "PRODUCTION main() WILL NOT BE EXECUTED."
    )

    print(
        "PRODUCTION MODULE WILL NOT BE IMPORTED."
    )

    print(
        "NO DATABASE WRITE IS PERMITTED."
    )

    # -------------------------------------------------------------------------
    # SOURCE INTEGRITY
    # -------------------------------------------------------------------------

    production_hash = sha256_file(
        ENGINE_FILE
    )

    banner(
        "PRODUCTION SOURCE INTEGRITY BEFORE"
    )

    kv(
        "Production SHA256",
        production_hash
    )

    # -------------------------------------------------------------------------
    # SOURCE / AST
    # -------------------------------------------------------------------------

    source = read_source()

    tree = parse_source(
        source
    )

    attach_parents(
        tree
    )

    banner(
        "PRODUCTION AST"
    )

    kv(
        "AST Parse",
        "SUCCESS"
    )

    kv(
        "Production Functions",
        len(
            index_functions(tree)
        )
    )

    # -------------------------------------------------------------------------
    # AST DISCOVERY
    # -------------------------------------------------------------------------

    report = print_ast_report(
        source,
        tree,
    )

    # -------------------------------------------------------------------------
    # DATABASE
    # -------------------------------------------------------------------------

    conn = None

    try:

        conn = connect_read_only()

        verify_database_contract(
            conn
        )

    finally:

        if conn is not None:

            conn.close()

    # -------------------------------------------------------------------------
    # SOURCE INTEGRITY AFTER
    # -------------------------------------------------------------------------

    production_hash_after = (
        sha256_file(
            ENGINE_FILE
        )
    )

    banner(
        "PRODUCTION SOURCE INTEGRITY AFTER"
    )

    kv(
        "Production SHA256 BEFORE",
        production_hash
    )

    kv(
        "Production SHA256 AFTER",
        production_hash_after
    )

    if production_hash != production_hash_after:

        failed(
            "PRODUCTION SOURCE CHANGED."
        )

    passed(
        "Production source unchanged."
    )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    banner(
        "FINAL STATUS : PASS"
    )

    print(
        "AST downstream discovery completed."
    )

    print(
        "Exact validate_row() call sites discovered."
    )

    print(
        "Validator-output assignments discovered."
    )

    print(
        "score/status/flags/eligible/rejected/reason/"
        "decision references discovered."
    )

    print(
        "Relevant downstream conditions discovered."
    )

    print(
        "Relevant downstream returns discovered."
    )

    print()

    print(
        "NEXT FORENSIC STEP:"
    )

    print(
        "Resolve the exact downstream function from "
        "the discovered AST call/dataflow boundary, "
        "then execute that exact production function "
        "against REAL persisted contract rows."
    )


# =============================================================================
# ENTRYPOINT
# =============================================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        banner(
            "FINAL STATUS : FAIL"
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print()

        print(
            traceback.format_exc()
        )

        sys.exit(1)