import ast
import os
import re
import sqlite3
import time
from pathlib import Path


# =============================================================================
# ARUNDA
# INDICATOR PRODUCTION ENTRYPOINT RUNTIME PATH
# FORENSIC AUDIT v0.1
# =============================================================================
#
# PURPOSE
# -------
# Identify the REAL production entry point that eventually reaches:
#
#     calculate_analysis(rows)
#
# and map:
#
#     ENTRY POINT
#         |
#         v
#     CALLER CHAIN
#         |
#         v
#     ROWS CONSTRUCTION
#         |
#         v
#     calculate_analysis(rows)
#         |
#         v
#     RESULT TRANSFORMATION
#         |
#         v
#     SQL ASSIGNMENT
#
# SAFETY
# ------
# STATIC / READ ONLY
#
# NO:
#   INSERT
#   UPDATE
#   DELETE
#   ALTER
#   CREATE
#   DROP
#   REPLACE
#   production execution
#
# This script intentionally DOES NOT execute the production entry point.
#
# =============================================================================


BASE_DIR = Path(
    r"C:\Users\ASUS\ArundaTrader"
)

ENGINE_PATH = (
    BASE_DIR / "market_data_engine.py"
)

DATABASE_PATH = (
    BASE_DIR / "arunda.db"
)

TARGET_SYMBOLS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

START = time.perf_counter()


# =============================================================================
# OUTPUT
# =============================================================================

def line(char="=", width=100):
    print(char * width)


def section(title):
    print()
    line("=")
    print(title)
    line("=")


def subsection(title):
    print()
    line("-")
    print(title)
    line("-")


def safe_source(source, node):
    try:
        return ast.get_source_segment(
            source,
            node,
        )
    except Exception:
        return None


# =============================================================================
# HEADER
# =============================================================================

section(
    "ARUNDA INDICATOR PRODUCTION ENTRYPOINT "
    "RUNTIME PATH FORENSIC AUDIT v0.1"
)

print(
    "MODE                         : READ ONLY"
)

print(
    "DATABASE WRITE               : NONE"
)

print(
    "ENGINE WRITE                 : NONE"
)

print(
    "PRODUCTION EXECUTION         : NONE"
)

print(
    "PURPOSE                      : IDENTIFY ACTUAL PRODUCTION ENTRY POINT"
)

print(
    "TARGET                       : calculate_analysis(rows)"
)


# =============================================================================
# PATH
# =============================================================================

section(
    "STEP 1 — PATH RESOLUTION"
)

print(
    "BASE DIR                     :",
    BASE_DIR,
)

print(
    "ENGINE PATH                  :",
    ENGINE_PATH,
)

print(
    "ENGINE FOUND                 :",
    ENGINE_PATH.exists(),
)

print(
    "DATABASE PATH                :",
    DATABASE_PATH,
)

print(
    "DATABASE FOUND               :",
    DATABASE_PATH.exists(),
)

if not ENGINE_PATH.exists():
    print(
        "[FATAL] market_data_engine.py NOT FOUND"
    )
    raise SystemExit(1)


# =============================================================================
# SOURCE INVENTORY
# =============================================================================

section(
    "STEP 2 — PROJECT PYTHON SOURCE INVENTORY"
)

python_files = []

for path in sorted(
    BASE_DIR.glob("*.py")
):

    if path.name.startswith(
        "INDICATOR_"
    ):
        continue

    python_files.append(
        path
    )

print(
    "PYTHON FILES DISCOVERED       :",
    len(python_files),
)

for path in python_files:
    print(
        "[PY]",
        path.name,
    )


# =============================================================================
# AST PARSE
# =============================================================================

section(
    "STEP 3 — AST PARSE ALL PRODUCTION PYTHON FILES"
)

parsed_files = {}

for path in python_files:

    try:

        source = path.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

        parsed_files[path] = (
            source,
            tree,
        )

        print(
            "[AST SUCCESS]",
            path.name,
        )

    except Exception as exc:

        print(
            "[AST FAILED]",
            path.name,
            "|",
            repr(exc),
        )


# =============================================================================
# FUNCTION INVENTORY
# =============================================================================

section(
    "STEP 4 — FUNCTION INVENTORY"
)

functions = {}

for path, (
    source,
    tree,
) in parsed_files.items():

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            functions.setdefault(
                node.name,
                [],
            ).append(
                {
                    "path": path,
                    "source": source,
                    "node": node,
                }
            )

            print(
                f"[FUNCTION] {node.name:<40} "
                f"{path.name}:"
                f"{node.lineno}-"
                f"{getattr(node, 'end_lineno', '?')}"
            )


# =============================================================================
# CALCULATE_ANALYSIS DEFINITIONS
# =============================================================================

section(
    "STEP 5 — calculate_analysis DEFINITIONS"
)

calculate_defs = functions.get(
    "calculate_analysis",
    [],
)

print(
    "DEFINITIONS FOUND             :",
    len(calculate_defs),
)

for item in calculate_defs:

    node = item["node"]

    print()
    print(
        "[FOUND]",
        item["path"].name,
    )

    print(
        "LINE                         :",
        f"{node.lineno}-"
        f"{getattr(node, 'end_lineno', '?')}",
    )

    print(
        "SIGNATURE                    :",
        ast.unparse(node.args),
    )


if not calculate_defs:

    print(
        "[FATAL] calculate_analysis definition not found"
    )

    raise SystemExit(1)


# =============================================================================
# CALL-SITE DISCOVERY
# =============================================================================

section(
    "STEP 6 — ALL calculate_analysis CALL SITES"
)

call_sites = []

for path, (
    source,
    tree,
) in parsed_files.items():

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        function_name = None

        if isinstance(
            node.func,
            ast.Name,
        ):

            function_name = (
                node.func.id
            )

        elif isinstance(
            node.func,
            ast.Attribute,
        ):

            function_name = (
                node.func.attr
            )

        if function_name != (
            "calculate_analysis"
        ):
            continue

        call_sites.append(
            {
                "path": path,
                "source": source,
                "node": node,
            }
        )

        print()
        print(
            "[CALL SITE]",
            path.name,
        )

        print(
            "LINE                         :",
            node.lineno,
        )

        print(
            "SOURCE                       :",
            safe_source(
                source,
                node,
            ),
        )

        print(
            "ARGUMENT COUNT               :",
            len(node.args),
        )

        for index, arg in enumerate(
            node.args
        ):

            print(
                f"ARG {index}                      :",
                ast.dump(
                    arg,
                    include_attributes=False,
                ),
            )


print()
print(
    "TOTAL calculate_analysis CALLS:",
    len(call_sites),
)


# =============================================================================
# CALLER FUNCTION IDENTIFICATION
# =============================================================================

section(
    "STEP 7 — CALLER FUNCTION IDENTIFICATION"
)

caller_functions = []

for item in call_sites:

    call_node = item["node"]

    path = item["path"]

    source = item["source"]

    tree = parsed_files[path][1]

    for parent in ast.walk(tree):

        if not isinstance(
            parent,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        found = False

        for child in ast.walk(parent):

            if child is call_node:

                found = True
                break

        if found:

            caller_record = {
                "path": path,
                "function": parent.name,
                "line": parent.lineno,
                "end_line": getattr(
                    parent,
                    "end_lineno",
                    None,
                ),
                "call_line": call_node.lineno,
                "call_source": safe_source(
                    source,
                    call_node,
                ),
                "node": parent,
            }

            caller_functions.append(
                caller_record
            )

            print()
            print(
                "[CALLER FOUND]"
            )

            print(
                "FILE                         :",
                path.name,
            )

            print(
                "FUNCTION                     :",
                parent.name,
            )

            print(
                "FUNCTION RANGE               :",
                f"{parent.lineno}-"
                f"{getattr(parent, 'end_lineno', '?')}",
            )

            print(
                "calculate_analysis LINE      :",
                call_node.lineno,
            )

            break


# =============================================================================
# ROWS ARGUMENT DATAFLOW
# =============================================================================

section(
    "STEP 8 — calculate_analysis ARGUMENT DATAFLOW"
)

for index, item in enumerate(
    call_sites,
    1,
):

    node = item["node"]

    print()
    print(
        f"[CALL SITE {index}]"
    )

    if not node.args:

        print(
            "ROWS ARGUMENT                : MISSING"
        )

        continue

    rows_arg = node.args[0]

    print(
        "ROWS EXPRESSION              :",
        ast.unparse(rows_arg),
    )

    print(
        "ROWS AST TYPE                :",
        type(rows_arg).__name__,
    )

    # -------------------------------------------------------------------------
    # Name-based upstream variable
    # -------------------------------------------------------------------------

    if isinstance(
        rows_arg,
        ast.Name,
    ):

        rows_name = rows_arg.id

        print(
            "ROWS VARIABLE                :",
            rows_name,
        )

        print(
            "UPSTREAM ASSIGNMENTS:"
        )

        for path, (
            source,
            tree,
        ) in parsed_files.items():

            for assignment in ast.walk(
                tree
            ):

                if not isinstance(
                    assignment,
                    ast.Assign,
                ):
                    continue

                for target in (
                    assignment.targets
                ):

                    if (
                        isinstance(
                            target,
                            ast.Name,
                        )
                        and target.id
                        == rows_name
                    ):

                        print(
                            f"  LINE {assignment.lineno} : "
                            f"{safe_source(source, assignment)}"
                        )

                    elif (
                        isinstance(
                            target,
                            ast.Tuple,
                        )
                    ):

                        names = []

                        for element in (
                            target.elts
                        ):

                            if isinstance(
                                element,
                                ast.Name,
                            ):

                                names.append(
                                    element.id
                                )

                        if rows_name in names:

                            print(
                                f"  LINE {assignment.lineno} : "
                                f"{safe_source(source, assignment)}"
                            )


# =============================================================================
# ROWS CONSTRUCTION PATTERNS
# =============================================================================

section(
    "STEP 9 — RUNTIME ROW CONSTRUCTION PATTERNS"
)

rows_patterns = [
    "fetchall",
    "fetchmany",
    "fetchone",
    "execute",
    "cursor",
    "SELECT",
    "market_data",
    "rows",
    "history",
    "records",
    "candles",
]

for path, (
    source,
    tree,
) in parsed_files.items():

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Call,
        ):

            text = safe_source(
                source,
                node,
            )

            if not text:
                continue

            if any(
                pattern.lower()
                in text.lower()
                for pattern in rows_patterns
            ):

                print(
                    f"[ROW/SQL PATTERN] "
                    f"{path.name}:"
                    f"{node.lineno}"
                )

                print(
                    "  ",
                    text.strip(),
                )


# =============================================================================
# SQL EXECUTION INVENTORY
# =============================================================================

section(
    "STEP 10 — SQL EXECUTION PATH INVENTORY"
)

sql_operations = []

write_keywords = re.compile(
    r"\b("
    r"INSERT|"
    r"UPDATE|"
    r"DELETE|"
    r"ALTER|"
    r"CREATE|"
    r"DROP|"
    r"REPLACE"
    r")\b",
    re.IGNORECASE,
)

for path, (
    source,
    tree,
) in parsed_files.items():

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        function_name = None

        if isinstance(
            node.func,
            ast.Attribute,
        ):

            function_name = (
                node.func.attr
            )

        elif isinstance(
            node.func,
            ast.Name,
        ):

            function_name = (
                node.func.id
            )

        if function_name not in {
            "execute",
            "executemany",
            "executescript",
            "connect",
        }:
            continue

        text = safe_source(
            source,
            node,
        )

        if not text:
            continue

        write_like = bool(
            write_keywords.search(
                text
            )
        )

        record = {
            "path": path,
            "line": node.lineno,
            "function": function_name,
            "source": text,
            "write_like": write_like,
        }

        sql_operations.append(
            record
        )

        print()
        print(
            "[SQL OPERATION]"
        )

        print(
            "FILE                         :",
            path.name,
        )

        print(
            "LINE                         :",
            node.lineno,
        )

        print(
            "FUNCTION                     :",
            function_name,
        )

        print(
            "WRITE-LIKE                   :",
            write_like,
        )

        print(
            "SOURCE                       :",
            text,
        )


# =============================================================================
# MAIN / ENTRYPOINT DISCOVERY
# =============================================================================

section(
    "STEP 11 — PRODUCTION ENTRYPOINT DISCOVERY"
)

entrypoints = []

for path, (
    source,
    tree,
) in parsed_files.items():

    # -------------------------------------------------------------------------
    # if __name__ == "__main__"
    # -------------------------------------------------------------------------

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.If,
        ):
            continue

        test = node.test

        if not isinstance(
            test,
            ast.Compare,
        ):
            continue

        if not isinstance(
            test.left,
            ast.Name,
        ):
            continue

        if test.left.id != "__name__":
            continue

        entrypoints.append(
            {
                "type": "MAIN_GUARD",
                "path": path,
                "line": node.lineno,
                "source": safe_source(
                    source,
                    node,
                ),
            }
        )

        print()
        print(
            "[MAIN GUARD]"
        )

        print(
            "FILE                         :",
            path.name,
        )

        print(
            "LINE                         :",
            node.lineno,
        )

        print(
            "SOURCE                       :",
            safe_source(
                source,
                node,
            ),
        )

    # -------------------------------------------------------------------------
    # common entrypoint names
    # -------------------------------------------------------------------------

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        if node.name.lower() in {
            "main",
            "run",
            "start",
            "loop",
            "runtime",
            "worker",
            "collector",
            "pipeline",
            "process",
            "update",
            "snapshot",
        }:

            entrypoints.append(
                {
                    "type": "ENTRY_FUNCTION",
                    "path": path,
                    "line": node.lineno,
                    "name": node.name,
                    "source": safe_source(
                        source,
                        node,
                    ),
                }
            )

            print()
            print(
                "[ENTRY FUNCTION CANDIDATE]"
            )

            print(
                "FILE                         :",
                path.name,
            )

            print(
                "FUNCTION                     :",
                node.name,
            )

            print(
                "LINE                         :",
                node.lineno,
            )


# =============================================================================
# IMPORT DEPENDENCY CHAIN
# =============================================================================

section(
    "STEP 12 — IMPORT / MODULE DEPENDENCY CHAIN"
)

for path, (
    source,
    tree,
) in parsed_files.items():

    imports = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:
                imports.append(
                    alias.name
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            module = (
                node.module
                or ""
            )

            imports.append(
                module
            )

    if imports:

        print()
        print(
            f"[IMPORTS] {path.name}"
        )

        for module in sorted(
            set(imports)
        ):

            print(
                "  ",
                module,
            )


# =============================================================================
# CALL GRAPH AROUND calculate_analysis
# =============================================================================

section(
    "STEP 13 — LOCAL CALL GRAPH AROUND calculate_analysis"
)

for caller in caller_functions:

    function_node = caller["node"]

    print()
    print(
        f"CALLER : {caller['function']}"
    )

    for node in ast.walk(
        function_node
    ):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        text = safe_source(
            parsed_files[
                caller["path"]
            ][0],
            node,
        )

        if text:

            print(
                f"  LINE {node.lineno:<5} "
                f"{text.strip()}"
            )


# =============================================================================
# TARGET SYMBOL FILTERS
# =============================================================================

section(
    "STEP 14 — TARGET SYMBOL / SQL FILTER DISCOVERY"
)

for path, (
    source,
    tree,
) in parsed_files.items():

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Constant,
        ):

            if isinstance(
                node.value,
                str,
            ):

                text = node.value

                if text in TARGET_SYMBOLS:

                    print(
                        f"[TARGET SYMBOL] "
                        f"{path.name}:"
                        f"{node.lineno}"
                        f" -> {text}"
                    )

                if (
                    "market_data"
                    in text
                ):

                    print(
                        f"[MARKET_DATA SQL/TEXT] "
                        f"{path.name}:"
                        f"{node.lineno}"
                    )

                    print(
                        "  ",
                        repr(text),
                    )


# =============================================================================
# FINAL FRONTIER MAP
# =============================================================================

section(
    "FINAL PRODUCTION ENTRYPOINT FORENSIC MAP"
)

print()
print(
    "calculate_analysis DEFINITIONS :",
    len(calculate_defs),
)

print(
    "calculate_analysis CALL SITES  :",
    len(call_sites),
)

print(
    "CALLER FUNCTIONS               :",
    len(caller_functions),
)

print(
    "SQL OPERATIONS DISCOVERED      :",
    len(sql_operations),
)

print(
    "ENTRYPOINT CANDIDATES          :",
    len(entrypoints),
)


# =============================================================================
# EXACT NEXT ACTION CLASSIFICATION
# =============================================================================

subsection(
    "FRONTIER CLASSIFICATION"
)

if not call_sites:

    status = (
        "CALCULATE_ANALYSIS_CALLSITE_MISSING"
    )

    meaning = (
        "No static calculate_analysis caller was found "
        "in the scanned production Python files."
    )

elif not caller_functions:

    status = (
        "CALLSITE_FOUND_CALLER_SCOPE_UNRESOLVED"
    )

    meaning = (
        "calculate_analysis is called, but its enclosing "
        "production caller could not be resolved."
    )

elif not entrypoints:

    status = (
        "CALLER_RESOLVED_ENTRYPOINT_UNRESOLVED"
    )

    meaning = (
        "The direct caller was located, but the production "
        "entry point that invokes that caller is unresolved."
    )

else:

    status = (
        "PRODUCTION_ENTRYPOINT_CANDIDATES_RESOLVED"
    )

    meaning = (
        "The production entry point candidates and the "
        "calculate_analysis caller path have been statically mapped."
    )


print(
    "STATUS                       :",
    status,
)

print(
    "MEANING                      :",
    meaning,
)

print()
print(
    "IMPORTANT                    : "
    "NO PRODUCTION ENTRYPOINT WAS EXECUTED."
)

print(
    "IMPORTANT                    : "
    "NO DATABASE WRITE WAS POSSIBLE."
)

print(
    "IMPORTANT                    : "
    "NO RUNTIME DATA WAS FABRICATED."
)

print()
print(
    "NEXT FRONTIER                : "
    "Execute ONLY the exact resolved production entry point "
    "under a dedicated runtime sandbox with all SQLite writes "
    "blocked and capture the actual rows object + SQL parameter tuple."
)

print()
print(
    "DATABASE WRITE OPERATIONS    : NONE"
)

print(
    "ENGINE MODIFICATIONS         : NONE"
)

print(
    "INSERT                       : NONE"
)

print(
    "UPDATE                       : NONE"
)

print(
    "DELETE                       : NONE"
)

print(
    "ALTER                        : NONE"
)

print(
    "CREATE                       : NONE"
)

print(
    "DROP                         : NONE"
)

print(
    "PRODUCTION EXECUTION         : NONE"
)

print(
    "SQL MODE                     : NOT EXECUTED"
)

print(
    "ELAPSED SECONDS              :",
    round(
        time.perf_counter() - START,
        3,
    ),
)

print(
    "AUDIT COMPLETE"
)