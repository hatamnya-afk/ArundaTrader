import ast
import os
import sqlite3
import sys
import time
import traceback
import importlib.util
from collections import defaultdict


# ============================================================
# ARUNDA
# SIGNAL OUTCOME PRODUCTION CALLER RESOLUTION
# FORENSIC AUDIT v0.1
# ============================================================
#
# PURPOSE
# -------
# Resolve the actual production caller chain reaching:
#
#     signal_outcome_engine.py
#             |
#             v
#       create_outcome()
#             |
#             v
#       find_future_price()
#
# CURRENT FRONTIER
# ----------------
#
# Previous forensic stage established:
#
#     find_future_price()
#         <- create_outcome()
#
# This audit now resolves the production caller of
# create_outcome().
#
# SAFETY
# ------
# READ ONLY
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO CREATE
# NO DROP
#
# Production functions are NOT executed.
# Production main() is NOT executed.
# Database is opened read-only.
#
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

TARGET_FILE = os.path.join(
    PROJECT_DIR,
    "signal_outcome_engine.py"
)

TARGET_FUNCTION = "create_outcome"

DOWNSTREAM_FUNCTION = "find_future_price"

DB_FILE = os.path.join(
    PROJECT_DIR,
    "arunda.db"
)

TARGETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]


# ============================================================
# EXCLUSION RULES
# ============================================================

EXCLUDED_NAME_PARTS = (
    "FORENSIC",
    "AUDIT",
    "DIAGNOSTIC",
    "DISCOVERY",
    "TRACE",
    "REPAIR",
    "TEST",
    "DEBUG",
    "EXPERIMENT",
    "BACKUP",
    "TEMP",
    "TMP",
)

EXCLUDED_EXACT_FILES = {
    os.path.basename(__file__).upper(),
}


# ============================================================
# FORENSIC STATE
# ============================================================

python_files_scanned = 0
files_parsed = 0
parse_errors = []

functions_discovered = []

call_graph_edges = []

target_references = []

caller_candidates = []

selected_candidates = []

static_write_references = []

database_target_reads = []

runtime_events = []

runtime_exceptions = []

blocked_writes = []


# ============================================================
# OUTPUT HELPERS
# ============================================================

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


def safe_repr(value, limit=1500):

    try:
        text = repr(value)

    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return (
            text[:limit]
            + "...<TRUNCATED>"
        )

    return text


# ============================================================
# FILE FILTERING
# ============================================================

def should_exclude_file(path):

    basename = os.path.basename(
        path
    )

    upper_name = basename.upper()

    if upper_name in EXCLUDED_EXACT_FILES:
        return True

    for part in EXCLUDED_NAME_PARTS:

        if part in upper_name:
            return True

    return False


def is_python_file(path):

    return (
        os.path.isfile(path)
        and path.lower().endswith(".py")
    )


def discover_python_files():

    files = []

    for root, dirs, filenames in os.walk(
        PROJECT_DIR
    ):

        dirs[:] = [
            directory
            for directory in dirs
            if not should_exclude_file(
                os.path.join(
                    root,
                    directory
                )
            )
        ]

        for filename in filenames:

            path = os.path.join(
                root,
                filename
            )

            if not is_python_file(path):
                continue

            if should_exclude_file(path):
                continue

            files.append(
                os.path.abspath(path)
            )

    return sorted(
        set(files)
    )


# ============================================================
# SOURCE PARSING
# ============================================================

def parse_python_file(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as handle:

            source = handle.read()

        tree = ast.parse(
            source,
            filename=path
        )

        return source, tree, None

    except Exception as exc:

        return (
            None,
            None,
            {
                "file": path,
                "exception": repr(exc),
                "traceback": traceback.format_exc(),
            },
        )


# ============================================================
# FUNCTION IDENTIFICATION
# ============================================================

def function_qualname(node):

    names = []

    current = node

    while current is not None:

        if isinstance(
            current,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            names.append(
                current.name
            )

        current = None

    return ".".join(
        reversed(names)
    )


def collect_functions(
    tree,
    path
):

    found = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            record = {
                "file": path,
                "function": node.name,
                "line": node.lineno,
                "end_line": getattr(
                    node,
                    "end_lineno",
                    node.lineno,
                ),
            }

            found.append(
                record
            )

    return found


# ============================================================
# CALL NAME RESOLUTION
# ============================================================

def get_call_name(node):

    if isinstance(
        node,
        ast.Name
    ):

        return node.id

    if isinstance(
        node,
        ast.Attribute
    ):

        parts = []

        current = node

        while isinstance(
            current,
            ast.Attribute
        ):

            parts.append(
                current.attr
            )

            current = current.value

        if isinstance(
            current,
            ast.Name
        ):

            parts.append(
                current.id
            )

        return ".".join(
            reversed(parts)
        )

    return None


# ============================================================
# CALL GRAPH EXTRACTION
# ============================================================

def collect_call_edges(
    tree,
    path
):

    edges = []

    function_stack = []

    class Visitor(ast.NodeVisitor):

        def visit_FunctionDef(
            self,
            node
        ):

            function_stack.append(
                node.name
            )

            self.generic_visit(
                node
            )

            function_stack.pop()

        def visit_AsyncFunctionDef(
            self,
            node
        ):

            function_stack.append(
                node.name
            )

            self.generic_visit(
                node
            )

            function_stack.pop()

        def visit_Call(
            self,
            node
        ):

            called_name = get_call_name(
                node.func
            )

            if called_name:

                caller = (
                    function_stack[-1]
                    if function_stack
                    else "<module>"
                )

                edges.append(
                    {
                        "file": path,
                        "caller": caller,
                        "callee": called_name,
                        "line": node.lineno,
                    }
                )

            self.generic_visit(
                node
            )

    Visitor().visit(tree)

    return edges


# ============================================================
# STATIC WRITE DETECTION
# ============================================================

WRITE_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "CREATE",
    "DROP",
    "REPLACE",
    "VACUUM",
    "REINDEX",
    "ATTACH",
    "DETACH",
)


def detect_write_references(
    tree,
    path
):

    records = []

    source_sql_nodes = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Constant
        ):

            if isinstance(
                node.value,
                str
            ):

                source_sql_nodes.append(
                    node
                )

    for node in source_sql_nodes:

        normalized = (
            " ".join(
                node.value
                .upper()
                .split()
            )
        )

        for keyword in WRITE_KEYWORDS:

            if normalized.startswith(
                keyword
            ):

                records.append(
                    {
                        "file": path,
                        "line": node.lineno,
                        "keyword": keyword,
                        "sql": node.value,
                    }
                )

                break

    return records


# ============================================================
# TARGET REFERENCE DETECTION
# ============================================================

def collect_target_references(
    tree,
    path,
    target_name
):

    records = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Name
        ):

            if node.id == target_name:

                records.append(
                    {
                        "file": path,
                        "line": node.lineno,
                        "reference": node.id,
                        "kind": "Name",
                    }
                )

        elif isinstance(
            node,
            ast.Attribute
        ):

            if node.attr == target_name:

                records.append(
                    {
                        "file": path,
                        "line": node.lineno,
                        "reference": node.attr,
                        "kind": "Attribute",
                    }
                )

    return records


# ============================================================
# CALLER CANDIDATE RESOLUTION
# ============================================================

def resolve_direct_callers(
    edges,
    target_name
):

    candidates = []

    for edge in edges:

        callee = edge["callee"]

        if callee == target_name:

            candidates.append(
                {
                    "file": edge["file"],
                    "caller": edge["caller"],
                    "line": edge["line"],
                    "callee": target_name,
                }
            )

        elif callee.endswith(
            "." + target_name
        ):

            candidates.append(
                {
                    "file": edge["file"],
                    "caller": edge["caller"],
                    "line": edge["line"],
                    "callee": callee,
                }
            )

    return candidates


# ============================================================
# TARGET FILE VERIFICATION
# ============================================================

def inspect_target_file():

    section(
        "STEP 1 — TARGET PRODUCTION FILE RESOLUTION"
    )

    print(
        f"PROJECT PATH              : {PROJECT_DIR}"
    )

    print(
        f"TARGET FILE               : {TARGET_FILE}"
    )

    print(
        f"TARGET FILE FOUND         : "
        f"{os.path.isfile(TARGET_FILE)}"
    )

    print(
        f"TARGET FUNCTION           : "
        f"{TARGET_FUNCTION}"
    )

    print(
        f"DOWNSTREAM FUNCTION       : "
        f"{DOWNSTREAM_FUNCTION}"
    )

    if not os.path.isfile(
        TARGET_FILE
    ):

        raise FileNotFoundError(
            TARGET_FILE
        )

    source, tree, error = parse_python_file(
        TARGET_FILE
    )

    if error:

        raise RuntimeError(
            "Could not parse target file:\n"
            + safe_repr(error)
        )

    definitions = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            definitions.append(
                node
            )

    target_defs = [
        node
        for node in definitions
        if node.name == TARGET_FUNCTION
    ]

    downstream_defs = [
        node
        for node in definitions
        if node.name == DOWNSTREAM_FUNCTION
    ]

    print(
        f"TARGET DEFINITIONS        : "
        f"{len(target_defs)}"
    )

    print(
        f"DOWNSTREAM DEFINITIONS    : "
        f"{len(downstream_defs)}"
    )

    for node in target_defs:

        print(
            f"TARGET LINE               : "
            f"{node.lineno}"
        )

    for node in downstream_defs:

        print(
            f"DOWNSTREAM LINE           : "
            f"{node.lineno}"
        )

    if not target_defs:

        raise RuntimeError(
            "create_outcome() was not found "
            "in signal_outcome_engine.py"
        )

    return source, tree


# ============================================================
# STATIC PROJECT SCAN
# ============================================================

def perform_static_scan():

    global python_files_scanned
    global files_parsed
    global functions_discovered
    global call_graph_edges
    global target_references
    global static_write_references

    section(
        "STEP 2 — STATIC PRODUCTION CALL GRAPH SCAN"
    )

    files = discover_python_files()

    python_files_scanned = len(
        files
    )

    print(
        f"PYTHON FILES DISCOVERED   : "
        f"{python_files_scanned}"
    )

    for path in files:

        source, tree, error = parse_python_file(
            path
        )

        if error:

            parse_errors.append(
                error
            )

            continue

        files_parsed += 1

        functions = collect_functions(
            tree,
            path
        )

        functions_discovered.extend(
            functions
        )

        edges = collect_call_edges(
            tree,
            path
        )

        call_graph_edges.extend(
            edges
        )

        writes = detect_write_references(
            tree,
            path
        )

        static_write_references.extend(
            writes
        )

        references = collect_target_references(
            tree,
            path,
            TARGET_FUNCTION
        )

        target_references.extend(
            references
        )

    print(
        f"FILES PARSED              : "
        f"{files_parsed}"
    )

    print(
        f"PARSE ERRORS              : "
        f"{len(parse_errors)}"
    )

    print(
        f"FUNCTIONS DISCOVERED      : "
        f"{len(functions_discovered)}"
    )

    print(
        f"CALL GRAPH EDGES          : "
        f"{len(call_graph_edges)}"
    )

    print(
        f"TARGET REFERENCES        : "
        f"{len(target_references)}"
    )

    print(
        f"STATIC WRITE REFERENCES   : "
        f"{len(static_write_references)}"
    )


# ============================================================
# DIRECT CALLER REPORT
# ============================================================

def report_direct_callers():

    global caller_candidates

    section(
        "STEP 3 — create_outcome() DIRECT CALLER RESOLUTION"
    )

    caller_candidates = resolve_direct_callers(
        call_graph_edges,
        TARGET_FUNCTION
    )

    print(
        f"DIRECT CALL SITES         : "
        f"{len(caller_candidates)}"
    )

    if not caller_candidates:

        print(
            "NO DIRECT STATIC CALLER FOUND"
        )

        return

    for index, candidate in enumerate(
        caller_candidates,
        start=1
    ):

        print(
            f"{index:03d} | "
            f"CALLER={candidate['caller']:<35} "
            f"| LINE={candidate['line']:<6} "
            f"| FILE={candidate['file']}"
        )


# ============================================================
# CALLER CHAIN SEARCH
# ============================================================

def find_callers_of_function(
    function_name
):

    results = []

    for edge in call_graph_edges:

        callee = edge["callee"]

        if (
            callee == function_name
            or callee.endswith(
                "." + function_name
            )
        ):

            results.append(
                edge
            )

    return results


def build_recursive_caller_chain(
    function_name,
    max_depth=8
):

    chains = []

    visited_states = set()

    def walk(
        current_function,
        chain,
        depth
    ):

        if depth >= max_depth:

            chains.append(
                list(chain)
            )

            return

        callers = find_callers_of_function(
            current_function
        )

        if not callers:

            chains.append(
                list(chain)
            )

            return

        progressed = False

        for caller in callers:

            state = (
                caller["file"],
                caller["caller"],
                caller["callee"],
            )

            if state in visited_states:

                continue

            visited_states.add(
                state
            )

            progressed = True

            chain.append(
                {
                    "function":
                        caller["caller"],
                    "file":
                        caller["file"],
                    "line":
                        caller["line"],
                    "calls":
                        caller["callee"],
                }
            )

            walk(
                caller["caller"],
                chain,
                depth + 1
            )

            chain.pop()

        if not progressed:

            chains.append(
                list(chain)
            )

    walk(
        function_name,
        [
            {
                "function":
                    function_name,
                "file":
                    TARGET_FILE,
                "line":
                    None,
                "calls":
                    None,
            }
        ],
        0
    )

    return chains


# ============================================================
# PRODUCTION FILE FILTER
# ============================================================

def is_likely_production_file(
    path
):

    basename = os.path.basename(
        path
    ).upper()

    for part in EXCLUDED_NAME_PARTS:

        if part in basename:

            return False

    return True


def filter_production_callers(
    candidates
):

    result = []

    for candidate in candidates:

        path = candidate["file"]

        if not is_likely_production_file(
            path
        ):

            continue

        if os.path.abspath(path) == os.path.abspath(
            TARGET_FILE
        ):

            continue

        result.append(
            candidate
        )

    return result


# ============================================================
# DATABASE READ-ONLY VERIFICATION
# ============================================================

def verify_database():

    section(
        "STEP 4 — READ-ONLY DATABASE VERIFICATION"
    )

    print(
        f"DATABASE PATH             : "
        f"{DB_FILE}"
    )

    print(
        f"DATABASE FOUND            : "
        f"{os.path.isfile(DB_FILE)}"
    )

    if not os.path.isfile(
        DB_FILE
    ):

        print(
            "DATABASE NOT FOUND"
        )

        return

    uri = (
        "file:"
        + DB_FILE.replace(
            "\\",
            "/"
        )
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    conn.row_factory = sqlite3.Row

    try:

        table = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name='market_data'
            """
        ).fetchone()

        found = table is not None

        print(
            f"MARKET_DATA TABLE FOUND  : "
            f"{found}"
        )

        if found:

            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM market_data
                """
            ).fetchone()

            total_rows = (
                row["count"]
                if row
                else 0
            )

            print(
                f"MARKET_DATA TOTAL ROWS    : "
                f"{total_rows}"
            )

            for symbol in TARGETS:

                row = conn.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM market_data
                    WHERE symbol = ?
                    """,
                    (symbol,)
                ).fetchone()

                count = (
                    row["count"]
                    if row
                    else 0
                )

                database_target_reads.append(
                    {
                        "symbol": symbol,
                        "rows": count,
                    }
                )

                print(
                    f"{symbol:<6} | "
                    f"ROWS={count}"
                )

    finally:

        conn.close()


# ============================================================
# SELECT STRONGEST PRODUCTION CALLER
# ============================================================

def score_candidate(
    candidate
):

    score = 0

    path = candidate["file"]
    caller = candidate["caller"]

    basename = os.path.basename(
        path
    ).lower()

    caller_lower = caller.lower()

    if is_likely_production_file(
        path
    ):
        score += 50

    if basename.endswith(
        ".py"
    ):
        score += 10

    if caller_lower in (
        "main",
        "run",
        "execute",
        "process",
        "generate",
        "create_signal",
        "evaluate",
        "analyze",
        "pipeline",
    ):
        score += 50

    if (
        "signal" in basename
        or "outcome" in basename
        or "engine" in basename
        or "pipeline" in basename
    ):
        score += 25

    if (
        "forensic" in basename
        or "audit" in basename
        or "trace" in basename
        or "diagnostic" in basename
    ):
        score -= 100

    return score


def resolve_strongest_caller():

    section(
        "STEP 5 — STRONGEST PRODUCTION CALLER RESOLUTION"
    )

    production_candidates = (
        filter_production_callers(
            caller_candidates
        )
    )

    ranked = []

    for candidate in production_candidates:

        score = score_candidate(
            candidate
        )

        item = dict(candidate)

        item["score"] = score

        ranked.append(
            item
        )

    ranked.sort(
        key=lambda item: (
            -item["score"],
            item["file"],
            item["line"],
        )
    )

    selected_candidates.clear()

    selected_candidates.extend(
        ranked
    )

    print(
        f"PRODUCTION CALLER CANDIDATES : "
        f"{len(ranked)}"
    )

    for index, candidate in enumerate(
        ranked[:20],
        start=1
    ):

        print(
            f"{index:03d} | "
            f"SCORE={candidate['score']:<4} | "
            f"CALLER={candidate['caller']:<30} | "
            f"LINE={candidate['line']:<6} | "
            f"FILE={candidate['file']}"
        )

    if not ranked:

        print()
        print(
            "NO PRODUCTION CALLER CANDIDATE "
            "COULD BE RESOLVED."
        )

        return None

    selected = ranked[0]

    print()

    print(
        "SELECTED PRODUCTION CALLER"
    )

    print(
        f"FILE                      : "
        f"{selected['file']}"
    )

    print(
        f"FUNCTION                  : "
        f"{selected['caller']}"
    )

    print(
        f"LINE                      : "
        f"{selected['line']}"
    )

    print(
        f"SCORE                     : "
        f"{selected['score']}"
    )

    return selected


# ============================================================
# CALLER CHAIN REPORT
# ============================================================

def report_call_chain():

    section(
        "STEP 6 — STATIC PRODUCTION CALLER CHAIN"
    )

    chains = build_recursive_caller_chain(
        TARGET_FUNCTION,
        max_depth=8
    )

    if not chains:

        print(
            "NO CALL CHAIN RESOLVED"
        )

        return

    unique_signatures = set()

    displayed = 0

    for chain in chains:

        signature = tuple(
            (
                item["function"],
                item["file"],
                item["line"],
            )
            for item in chain
        )

        if signature in unique_signatures:

            continue

        unique_signatures.add(
            signature
        )

        displayed += 1

        print()

        print(
            f"CHAIN {displayed}"
        )

        for depth, item in enumerate(
            chain
        ):

            indent = "  " * depth

            print(
                f"{indent}-> "
                f"{item['function']} "
                f"| "
                f"{item['file']} "
                f"| "
                f"LINE={item['line']}"
            )

        if displayed >= 20:

            break

    print()

    print(
        f"UNIQUE CHAINS DISPLAYED    : "
        f"{displayed}"
    )


# ============================================================
# RUNTIME SAFETY DECLARATION
# ============================================================

def runtime_safety():

    section(
        "STEP 7 — RUNTIME EXECUTION SAFETY"
    )

    print(
        "PRODUCTION main()          : NOT CALLED"
    )

    print(
        "PRODUCTION FUNCTIONS       : NOT EXECUTED"
    )

    print(
        "RUNTIME CONSUMPTION TRACE  : NOT ATTEMPTED"
    )

    print(
        "DATABASE CONNECTION        : READ ONLY"
    )

    print(
        "DATABASE WRITE             : BLOCKED"
    )

    print(
        "ENGINE MODIFICATION        : NONE"
    )

    print(
        "FORMULA MODIFICATION       : NONE"
    )

    print(
        "RUNTIME VALUE FABRICATION  : NONE"
    )


# ============================================================
# FINAL FRONTIER DETERMINATION
# ============================================================

def determine_frontier(
    selected
):

    if selected is None:

        return (
            "PRODUCTION_CALLER_NOT_RESOLVED",
            "Resolve the actual production caller "
            "that reaches create_outcome()."
        )

    return (
        "PRODUCTION_CALLER_RESOLVED",
        "Build a dedicated READ-ONLY runtime "
        "trace for the selected production caller."
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

def final_summary(
    selected
):

    status, next_frontier = determine_frontier(
        selected
    )

    section(
        "STEP 8 — FINAL FORENSIC SUMMARY"
    )

    print(
        f"TARGET FUNCTION             : "
        f"{TARGET_FUNCTION}"
    )

    print(
        f"TARGET FILE                 : "
        f"{TARGET_FILE}"
    )

    print(
        f"DOWNSTREAM FUNCTION         : "
        f"{DOWNSTREAM_FUNCTION}"
    )

    print(
        f"PYTHON FILES SCANNED        : "
        f"{python_files_scanned}"
    )

    print(
        f"FILES PARSED               : "
        f"{files_parsed}"
    )

    print(
        f"PARSE ERRORS               : "
        f"{len(parse_errors)}"
    )

    print(
        f"FUNCTIONS DISCOVERED       : "
        f"{len(functions_discovered)}"
    )

    print(
        f"CALL GRAPH EDGES           : "
        f"{len(call_graph_edges)}"
    )

    print(
        f"TARGET REFERENCES          : "
        f"{len(target_references)}"
    )

    print(
        f"DIRECT CALL SITES          : "
        f"{len(caller_candidates)}"
    )

    print(
        f"PRODUCTION CALLER CANDIDATES : "
        f"{len(selected_candidates)}"
    )

    print(
        f"STATIC WRITE REFERENCES    : "
        f"{len(static_write_references)}"
    )

    print(
        f"DATABASE TARGET READS      : "
        f"{len(database_target_reads)}"
    )

    print()

    print(
        "FORENSIC CONCLUSION"
    )

    line("-")

    print(
        f"STATUS                        : "
        f"{status}"
    )

    if selected is not None:

        print(
            "MEANING                       : "
            "A real production caller of "
            "create_outcome() was resolved "
            "through static call-graph evidence "
            "after excluding forensic, audit, "
            "diagnostic, discovery, trace, repair "
            "and test artifacts."
        )

        print(
            f"SELECTED CALLER FILE         : "
            f"{selected['file']}"
        )

        print(
            f"SELECTED CALLER FUNCTION     : "
            f"{selected['caller']}"
        )

        print(
            f"SELECTED CALLER LINE         : "
            f"{selected['line']}"
        )

        print(
            f"CALLER SCORE                 : "
            f"{selected['score']}"
        )

    else:

        print(
            "MEANING                       : "
            "No sufficiently reliable production "
            "caller of create_outcome() was resolved."
        )

    print(
        f"NEXT FRONTIER                : "
        f"{next_frontier}"
    )

    print()

    print(
        "IMPORTANT                     : "
        "No production function was executed."
    )

    print(
        "IMPORTANT                     : "
        "No production main() was executed."
    )

    print(
        "IMPORTANT                     : "
        "No runtime value was fabricated."
    )

    print(
        "IMPORTANT                     : "
        "No production formula was modified."
    )

    print(
        "IMPORTANT                     : "
        "The database was opened read-only."
    )

    print()

    print(
        "DATABASE WRITE OPERATIONS     : NONE"
    )

    print(
        "ENGINE MODIFICATIONS          : NONE ON DISK"
    )

    print(
        "INSERT                        : NONE"
    )

    print(
        "UPDATE                        : NONE"
    )

    print(
        "DELETE                        : NONE"
    )

    print(
        "ALTER                         : NONE"
    )

    print(
        "CREATE                        : NONE"
    )

    print(
        "DROP                          : NONE"
    )

    print(
        "PRODUCTION DB WRITE           : BLOCKED"
    )


# ============================================================
# PARSE ERROR REPORT
# ============================================================

def report_parse_errors():

    if not parse_errors:
        return

    section(
        "PARSE ERROR INVENTORY"
    )

    for index, error in enumerate(
        parse_errors[:50],
        start=1
    ):

        print(
            f"{index:03d} | "
            f"{error['file']}"
        )

        print(
            f"      {error['exception']}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    started = time.perf_counter()

    section(
        "ARUNDA SIGNAL OUTCOME PRODUCTION CALLER "
        "RESOLUTION FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                       : "
        "READ ONLY STATIC FORENSICS"
    )

    print(
        "PRODUCTION EXECUTION       : "
        "NONE"
    )

    print(
        "DATABASE WRITE             : "
        "BLOCKED"
    )

    print(
        "TARGET                     : "
        "create_outcome()"
    )

    print(
        "DOWNSTREAM                 : "
        "find_future_price()"
    )

    selected = None

    try:

        inspect_target_file()

        perform_static_scan()

        report_direct_callers()

        verify_database()

        selected = resolve_strongest_caller()

        report_call_chain()

        runtime_safety()

        report_parse_errors()

        final_summary(
            selected
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        print()

        line("=")

        print(
            f"ELAPSED SECONDS              : "
            f"{elapsed:.3f}"
        )

        print(
            "AUDIT COMPLETE"
        )

        line("=")

        return 0

    except Exception as exc:

        print()

        line("=")

        print(
            "FORENSIC AUDIT ERROR"
        )

        line("=")

        print(
            repr(exc)
        )

        print(
            traceback.format_exc()
        )

        print()

        print(
            "DATABASE WRITE OPERATIONS : NONE"
        )

        print(
            "PRODUCTION DB WRITE       : BLOCKED"
        )

        print(
            "PRODUCTION EXECUTION      : NONE"
        )

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )