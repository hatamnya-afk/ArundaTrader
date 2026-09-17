import ast
import os
import sqlite3
import time
import traceback
from collections import defaultdict


# ============================================================
# ARUNDA TRADER
# DOWNSTREAM CONSUMER ENTRYPOINT RESOLUTION
# FORENSIC AUDIT v0.2
# ============================================================
#
# PURPOSE
# -------
# Resolve the REAL downstream production consumer of market_data.
#
# IMPORTANT:
#
# market_data_engine.py / save_analysis()
# is NOT a downstream consumer.
#
# It is part of the producer / persistence path.
#
# This audit therefore:
#
#   1. Scans production Python files.
#   2. Excludes forensic / audit / diagnostic artifacts.
#   3. Excludes the market_data producer itself.
#   4. Detects REAL market_data READ consumers.
#   5. Builds a static call graph.
#   6. Scores consumer candidates.
#   7. Resolves the strongest production downstream candidate.
#
# SAFETY
# ------
# READ ONLY
# NO production execution
# NO database writes
# NO CREATE
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO DROP
#
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

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

PRODUCER_FILES = {
    "market_data_engine.py",
}

PRODUCER_FUNCTIONS = {
    "save_analysis",
    "calculate_analysis",
    "connect_database",
    "ensure_schema",
}

# ------------------------------------------------------------
# Anything containing one of these tokens is considered
# forensic / audit / diagnostic / test infrastructure.
# ------------------------------------------------------------

EXCLUDED_NAME_TOKENS = (
    "FORENSIC",
    "AUDIT",
    "DIAGNOSTIC",
    "DISCOVERY",
    "TRACE",
    "REPAIR",
    "TEST",
    "DEBUG",
    "CHECK",
    "VERIFY",
    "VERIFICATION",
    "VALIDATION",
    "PROBE",
    "INSPECT",
    "INSPECTION",
    "ANALYSIS_AUDIT",
    "RUNTIME",
    "SNAPSHOT_AUDIT",
)

EXCLUDED_EXACT_FILES = {
    os.path.basename(__file__).lower(),
}

# Directories that should never participate in production
# consumer resolution.

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    "env",
    ".env",
    "tests",
    "test",
}


# ============================================================
# GLOBAL STATE
# ============================================================

files_scanned = 0
files_parsed = 0
parse_errors = []

functions = {}
function_nodes = {}

market_data_references = []
consumer_candidates = []

call_graph = defaultdict(set)

excluded_files = []

database_target_reads = {}

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


def safe_repr(value, limit=1200):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


# ============================================================
# PATH / FILE CLASSIFICATION
# ============================================================

def is_python_file(path):
    return (
        os.path.isfile(path)
        and path.lower().endswith(".py")
    )


def is_excluded_directory(path):
    parts = {
        part.lower()
        for part in os.path.normpath(path).split(os.sep)
    }

    return bool(
        parts.intersection(
            {
                x.lower()
                for x in EXCLUDED_DIR_NAMES
            }
        )
    )


def is_excluded_filename(path):
    basename = os.path.basename(path)

    if basename.lower() in EXCLUDED_EXACT_FILES:
        return True

    upper_name = basename.upper()

    for token in EXCLUDED_NAME_TOKENS:
        if token in upper_name:
            return True

    return False


def is_excluded_file(path):
    return (
        is_excluded_directory(path)
        or is_excluded_filename(path)
    )


# ============================================================
# SOURCE DISCOVERY
# ============================================================

def discover_python_files():

    global files_scanned

    result = []

    for root, dirs, filenames in os.walk(
        PROJECT_DIR
    ):

        # Remove excluded directories in-place.
        dirs[:] = [
            d
            for d in dirs
            if d.lower()
            not in {
                x.lower()
                for x in EXCLUDED_DIR_NAMES
            }
        ]

        for filename in filenames:

            path = os.path.join(
                root,
                filename
            )

            if not is_python_file(path):
                continue

            files_scanned += 1

            if is_excluded_file(path):

                excluded_files.append(
                    path
                )

                continue

            result.append(
                os.path.abspath(path)
            )

    return sorted(
        set(result)
    )


# ============================================================
# AST HELPERS
# ============================================================

def node_name(node):

    if isinstance(
        node,
        ast.Name
    ):
        return node.id

    if isinstance(
        node,
        ast.Attribute
    ):
        return node.attr

    return None


def dotted_name(node):

    if isinstance(
        node,
        ast.Name
    ):
        return node.id

    if isinstance(
        node,
        ast.Attribute
    ):

        left = dotted_name(
            node.value
        )

        if left:
            return (
                left
                + "."
                + node.attr
            )

        return node.attr

    return None


def contains_market_data_text(node):

    try:
        text = ast.unparse(node)
    except Exception:
        return False

    return (
        "market_data" in text
    )


def call_contains_market_data(node):

    if not isinstance(
        node,
        ast.Call
    ):
        return False

    try:
        text = ast.unparse(node)
    except Exception:
        return False

    normalized = (
        text.lower()
    )

    return (
        "market_data" in normalized
    )


# ============================================================
# FUNCTION REGISTRATION
# ============================================================

def register_functions(
    tree,
    file_path
):

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):
            continue

        key = (
            file_path,
            node.name,
        )

        functions[key] = {
            "file": file_path,
            "function": node.name,
            "line": node.lineno,
            "node": node,
        }

        function_nodes[key] = node


# ============================================================
# MARKET_DATA REFERENCE DETECTION
# ============================================================

def detect_market_data_references(
    tree,
    file_path
):

    references = []

    current_function = None

    class Visitor(
        ast.NodeVisitor
    ):

        def visit_FunctionDef(
            self,
            node
        ):

            nonlocal current_function

            previous = current_function

            current_function = node.name

            self.generic_visit(
                node
            )

            current_function = previous

        def visit_AsyncFunctionDef(
            self,
            node
        ):

            nonlocal current_function

            previous = current_function

            current_function = node.name

            self.generic_visit(
                node
            )

            current_function = previous

        def visit_Name(
            self,
            node
        ):

            if (
                node.id == "market_data"
            ):

                references.append(
                    {
                        "file": file_path,
                        "function": current_function,
                        "line": node.lineno,
                        "kind": "name",
                    }
                )

            self.generic_visit(
                node
            )

        def visit_Attribute(
            self,
            node
        ):

            if (
                node.attr
                == "market_data"
            ):

                references.append(
                    {
                        "file": file_path,
                        "function": current_function,
                        "line": node.lineno,
                        "kind": "attribute",
                    }
                )

            self.generic_visit(
                node
            )

        def visit_Subscript(
            self,
            node
        ):

            try:
                text = ast.unparse(
                    node
                )
            except Exception:
                text = ""

            if (
                "market_data"
                in text.lower()
            ):

                references.append(
                    {
                        "file": file_path,
                        "function": current_function,
                        "line": node.lineno,
                        "kind": "subscript",
                        "expression": text,
                    }
                )

            self.generic_visit(
                node
            )

    Visitor().visit(
        tree
    )

    return references


# ============================================================
# SQL market_data READ DETECTION
# ============================================================

def is_market_data_read_sql(
    text
):

    normalized = (
        text.lower()
        .replace("\n", " ")
        .replace("\t", " ")
    )

    if (
        "market_data"
        not in normalized
    ):
        return False

    if "select" not in normalized:
        return False

    return True


def detect_sql_consumption(
    tree,
    file_path
):

    results = []

    current_function = None

    class Visitor(
        ast.NodeVisitor
    ):

        def visit_FunctionDef(
            self,
            node
        ):

            nonlocal current_function

            previous = current_function
            current_function = node.name

            self.generic_visit(
                node
            )

            current_function = previous

        def visit_AsyncFunctionDef(
            self,
            node
        ):

            nonlocal current_function

            previous = current_function
            current_function = node.name

            self.generic_visit(
                node
            )

            current_function = previous

        def visit_Call(
            self,
            node
        ):

            try:
                text = ast.unparse(
                    node
                )
            except Exception:
                text = ""

            if is_market_data_read_sql(
                text
            ):

                results.append(
                    {
                        "file": file_path,
                        "function": current_function,
                        "line": node.lineno,
                        "expression": text,
                    }
                )

            self.generic_visit(
                node
            )

    Visitor().visit(
        tree
    )

    return results


# ============================================================
# WRITE DETECTION
# ============================================================

WRITE_WORDS = (
    "insert",
    "update",
    "delete",
    "alter",
    "create",
    "drop",
    "replace",
    "vacuum",
    "reindex",
)


def detect_write_references(
    tree,
    file_path
):

    results = []

    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            ast.Call
        ):
            continue

        try:
            text = ast.unparse(
                node
            )
        except Exception:
            continue

        normalized = (
            text.lower()
        )

        if (
            "execute"
            not in normalized
            and "executemany"
            not in normalized
        ):
            continue

        if any(
            word in normalized
            for word in WRITE_WORDS
        ):

            results.append(
                {
                    "file": file_path,
                    "line": node.lineno,
                    "expression": text,
                }
            )

    return results


# ============================================================
# CALL GRAPH
# ============================================================

def detect_call_graph_edges(
    tree,
    file_path
):

    edges = []

    current_function = None

    class Visitor(
        ast.NodeVisitor
    ):

        def visit_FunctionDef(
            self,
            node
        ):

            nonlocal current_function

            previous = current_function
            current_function = node.name

            self.generic_visit(
                node
            )

            current_function = previous

        def visit_AsyncFunctionDef(
            self,
            node
        ):

            nonlocal current_function

            previous = current_function
            current_function = node.name

            self.generic_visit(
                node
            )

            current_function = previous

        def visit_Call(
            self,
            node
        ):

            if current_function is None:
                self.generic_visit(
                    node
                )
                return

            called = dotted_name(
                node.func
            )

            if called:

                edges.append(
                    {
                        "file": file_path,
                        "caller":
                            current_function,
                        "callee":
                            called,
                        "line":
                            node.lineno,
                    }
                )

            self.generic_visit(
                node
            )

    Visitor().visit(
        tree
    )

    return edges


# ============================================================
# PRODUCTION CONSUMER FILTER
# ============================================================

def is_producer_file(
    file_path
):

    basename = (
        os.path.basename(
            file_path
        ).lower()
    )

    return basename in {
        x.lower()
        for x in PRODUCER_FILES
    }


def is_producer_function(
    function_name
):

    if not function_name:
        return False

    return (
        function_name
        in PRODUCER_FUNCTIONS
    )


def looks_like_consumer_reference(
    reference
):

    file_path = reference["file"]
    function = reference["function"]

    # --------------------------------------------------------
    # Never select the producer.
    # --------------------------------------------------------

    if is_producer_file(
        file_path
    ):
        return False

    if is_producer_function(
        function
    ):
        return False

    # --------------------------------------------------------
    # Must have a function.
    # --------------------------------------------------------

    if not function:
        return False

    return True


# ============================================================
# CONSUMER SCORING
# ============================================================

def score_candidate(
    candidate,
    sql_reads
):

    score = 0
    reasons = []

    file_path = candidate["file"]
    function = candidate["function"]

    # --------------------------------------------------------
    # Direct market_data reference
    # --------------------------------------------------------

    score += 20
    reasons.append(
        "DIRECT_MARKET_DATA_REFERENCE"
    )

    # --------------------------------------------------------
    # SQL SELECT against market_data
    # --------------------------------------------------------

    matching_sql = [
        item
        for item in sql_reads
        if (
            item["file"]
            == file_path
            and item["function"]
            == function
        )
    ]

    if matching_sql:

        score += 100

        reasons.append(
            "DIRECT_MARKET_DATA_SQL_READ"
        )

    # --------------------------------------------------------
    # Strong consumer-like function names
    # --------------------------------------------------------

    function_lower = (
        function.lower()
    )

    strong_tokens = (
        "analy",
        "signal",
        "strategy",
        "predict",
        "score",
        "screen",
        "filter",
        "select",
        "rank",
        "feature",
        "model",
        "decision",
        "portfolio",
        "risk",
        "trade",
        "hunter",
        "pattern",
        "indicator",
    )

    for token in strong_tokens:

        if token in function_lower:

            score += 15

            reasons.append(
                "FUNCTION_NAME:"
                + token
            )

            break

    # --------------------------------------------------------
    # Explicit consumer-ish file names
    # --------------------------------------------------------

    file_lower = (
        os.path.basename(
            file_path
        ).lower()
    )

    file_tokens = (
        "analysis",
        "signal",
        "strategy",
        "scoring",
        "prediction",
        "pattern",
        "portfolio",
        "risk",
        "hunter",
        "feature",
        "model",
        "decision",
    )

    for token in file_tokens:

        if token in file_lower:

            score += 20

            reasons.append(
                "FILE_NAME:"
                + token
            )

            break

    # --------------------------------------------------------
    # Penalize obvious persistence/helper functions.
    # --------------------------------------------------------

    persistence_tokens = (
        "save",
        "store",
        "write",
        "insert",
        "persist",
        "cache",
        "load_schema",
        "ensure_schema",
    )

    for token in persistence_tokens:

        if token in function_lower:

            score -= 150

            reasons.append(
                "PERSISTENCE_PENALTY:"
                + token
            )

            break

    return (
        score,
        reasons,
    )


# ============================================================
# DATABASE VERIFICATION
# ============================================================

def verify_database():

    section(
        "STEP 5 — READ-ONLY market_data DATABASE VERIFICATION"
    )

    if not os.path.isfile(
        DB_FILE
    ):

        print(
            "DATABASE FOUND : False"
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

        exists = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name='market_data'
            """
        ).fetchone()

        found = (
            exists is not None
        )

        print(
            f"MARKET_DATA TABLE FOUND : "
            f"{found}"
        )

        if not found:
            return

        total = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM market_data
            """
        ).fetchone()["n"]

        print(
            f"MARKET_DATA TOTAL ROWS   : "
            f"{total}"
        )

        for symbol in TARGETS:

            row = conn.execute(
                """
                SELECT COUNT(*) AS n
                FROM market_data
                WHERE symbol = ?
                """,
                (symbol,)
            ).fetchone()

            count = row["n"]

            database_target_reads[
                symbol
            ] = count

            print(
                f"{symbol:<6} | ROWS={count}"
            )

    finally:

        conn.close()


# ============================================================
# STATIC SCAN
# ============================================================

def scan_production_sources():

    global files_parsed

    section(
        "STEP 3 — PRODUCTION SOURCE SCAN"
    )

    paths = discover_python_files()

    print(
        f"PRODUCTION PYTHON FILES "
        f"ELIGIBLE : {len(paths)}"
    )

    for path in paths:

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

            files_parsed += 1

            register_functions(
                tree,
                path
            )

            refs = (
                detect_market_data_references(
                    tree,
                    path
                )
            )

            market_data_references.extend(
                refs
            )

            sql_reads = (
                detect_sql_consumption(
                    tree,
                    path
                )
            )

            for item in sql_reads:

                market_data_references.append(
                    {
                        "file":
                            item["file"],
                        "function":
                            item["function"],
                        "line":
                            item["line"],
                        "kind":
                            "SQL_SELECT",
                        "expression":
                            item["expression"],
                    }
                )

            edges = (
                detect_call_graph_edges(
                    tree,
                    path
                )
            )

            for edge in edges:

                call_graph[
                    (
                        edge["file"],
                        edge["caller"],
                    )
                ].add(
                    edge["callee"]
                )

        except Exception as exc:

            parse_errors.append(
                {
                    "file": path,
                    "exception":
                        repr(exc),
                    "traceback":
                        traceback.format_exc(),
                }
            )


# ============================================================
# CANDIDATE BUILD
# ============================================================

def build_candidates():

    section(
        "STEP 6 — REAL DOWNSTREAM CONSUMER CANDIDATE FILTER"
    )

    sql_reads = []

    for ref in market_data_references:

        if (
            ref["kind"]
            == "SQL_SELECT"
        ):

            sql_reads.append(
                ref
            )

    grouped = {}

    for ref in market_data_references:

        if not looks_like_consumer_reference(
            ref
        ):
            continue

        key = (
            ref["file"],
            ref["function"],
        )

        if key not in grouped:

            grouped[key] = {
                "file":
                    ref["file"],
                "function":
                    ref["function"],
                "line":
                    ref["line"],
                "references":
                    0,
                "sql_reads":
                    0,
            }

        grouped[key][
            "references"
        ] += 1

        if (
            ref["kind"]
            == "SQL_SELECT"
        ):

            grouped[key][
                "sql_reads"
            ] += 1

    candidates = []

    for candidate in grouped.values():

        score, reasons = score_candidate(
            candidate,
            sql_reads
        )

        candidate[
            "score"
        ] = score

        candidate[
            "reasons"
        ] = reasons

        candidates.append(
            candidate
        )

    candidates.sort(
        key=lambda item: (
            item["score"],
            item["sql_reads"],
            item["references"],
        ),
        reverse=True
    )

    consumer_candidates.extend(
        candidates
    )

    print(
        f"CONSUMER CANDIDATES : "
        f"{len(candidates)}"
    )

    print()

    print(
        "TOP REAL PRODUCTION CONSUMER CANDIDATES"
    )

    line("-")

    for index, candidate in enumerate(
        candidates[:20],
        start=1
    ):

        relative = os.path.relpath(
            candidate["file"],
            PROJECT_DIR
        )

        print(
            f"{index:02d} | "
            f"SCORE={candidate['score']:<4} | "
            f"SQL_READS={candidate['sql_reads']:<3} | "
            f"REFS={candidate['references']:<3} | "
            f"{relative} :: "
            f"{candidate['function']} "
            f"(line {candidate['line']})"
        )


# ============================================================
# PRODUCER CONTAMINATION CHECK
# ============================================================

def verify_no_producer_selected(
    selected
):

    if selected is None:
        return True

    if is_producer_file(
        selected["file"]
    ):

        return False

    if is_producer_function(
        selected["function"]
    ):

        return False

    function_lower = (
        selected["function"]
        .lower()
    )

    forbidden = (
        "save",
        "store",
        "persist",
        "insert",
        "write",
        "ensure_schema",
    )

    if any(
        token in function_lower
        for token in forbidden
    ):

        return False

    return True


# ============================================================
# RESOLUTION
# ============================================================

def resolve_selected_consumer():

    section(
        "STEP 7 — DOWNSTREAM CONSUMER ENTRYPOINT RESOLUTION"
    )

    if not consumer_candidates:

        print(
            "STATUS : NO_REAL_DOWNSTREAM_CONSUMER_FOUND"
        )

        return None

    valid = []

    for candidate in consumer_candidates:

        if not verify_no_producer_selected(
            candidate
        ):
            continue

        valid.append(
            candidate
        )

    if not valid:

        print(
            "STATUS : NO_VALID_DOWNSTREAM_CONSUMER_FOUND"
        )

        return None

    selected = valid[0]

    relative = os.path.relpath(
        selected["file"],
        PROJECT_DIR
    )

    print(
        f"SELECTED FILE     : {relative}"
    )

    print(
        f"SELECTED FUNCTION : "
        f"{selected['function']}"
    )

    print(
        f"SELECTED LINE     : "
        f"{selected['line']}"
    )

    print(
        f"CONSUMER SCORE    : "
        f"{selected['score']}"
    )

    print(
        f"REFERENCE COUNT   : "
        f"{selected['references']}"
    )

    print(
        f"SQL READ COUNT    : "
        f"{selected['sql_reads']}"
    )

    print()

    print(
        "SELECTION REASONS"
    )

    for reason in selected[
        "reasons"
    ]:

        print(
            f"  - {reason}"
        )

    print()

    print(
        "PRODUCER CONTAMINATION CHECK : "
        "PASS"
    )

    print(
        "SAVE_ANALYSIS SELECTED       : "
        "NO"
    )

    return selected


# ============================================================
# CALL GRAPH CONTEXT
# ============================================================

def print_call_graph_context(
    selected
):

    section(
        "STEP 8 — STATIC CALL GRAPH CONTEXT"
    )

    if selected is None:

        print(
            "No selected consumer."
        )

        return

    key = (
        selected["file"],
        selected["function"],
    )

    callees = sorted(
        call_graph.get(
            key,
            set()
        )
    )

    print(
        f"SELECTED FUNCTION : "
        f"{selected['function']}"
    )

    print(
        f"DIRECT CALLEES    : "
        f"{len(callees)}"
    )

    for callee in callees[:50]:

        print(
            f"  -> {callee}"
        )


# ============================================================
# FINAL SUMMARY
# ============================================================

def final_summary(
    selected
):

    section(
        "STEP 9 — FINAL FORENSIC SUMMARY"
    )

    print(
        f"PYTHON FILES SCANNED        : "
        f"{files_scanned}"
    )

    print(
        f"FILES PARSED                : "
        f"{files_parsed}"
    )

    print(
        f"PARSE ERRORS                : "
        f"{len(parse_errors)}"
    )

    print(
        f"FUNCTIONS DISCOVERED        : "
        f"{len(functions)}"
    )

    print(
        f"market_data REFERENCES      : "
        f"{len(market_data_references)}"
    )

    print(
        f"CONSUMER CANDIDATES         : "
        f"{len(consumer_candidates)}"
    )

    print(
        f"EXCLUDED FILES              : "
        f"{len(excluded_files)}"
    )

    print()

    print(
        "DATABASE TARGET READS"
    )

    for symbol in TARGETS:

        print(
            f"{symbol:<6} | "
            f"ROWS="
            f"{database_target_reads.get(symbol, 0)}"
        )

    print()

    print(
        "FORENSIC CONCLUSION"
    )

    line("-")

    if selected is None:

        print(
            "STATUS                        : "
            "NO_REAL_DOWNSTREAM_CONSUMER_RESOLVED"
        )

        print(
            "MEANING                       : "
            "No valid downstream production "
            "consumer could be resolved after "
            "excluding the producer and persistence path."
        )

        print(
            "NEXT FRONTIER                 : "
            "Expand static consumer resolution "
            "through the production call graph."
        )

    else:

        relative = os.path.relpath(
            selected["file"],
            PROJECT_DIR
        )

        print(
            "STATUS                        : "
            "PRODUCTION_DOWNSTREAM_CONSUMER_RESOLVED"
        )

        print(
            "MEANING                       : "
            "A real downstream production consumer "
            "was resolved after explicitly excluding "
            "market_data production and persistence "
            "functions."
        )

        print(
            f"SELECTED CONSUMER FILE       : "
            f"{relative}"
        )

        print(
            f"SELECTED CONSUMER FUNCTION   : "
            f"{selected['function']}"
        )

        print(
            "NEXT FRONTIER                 : "
            "Build a dedicated READ-ONLY runtime "
            "consumption trace for this selected "
            "production consumer."
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
        "market_data producer/persistence "
        "functions were excluded from downstream "
        "consumer selection."
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
# MAIN
# ============================================================

def main():

    started = time.perf_counter()

    section(
        "ARUNDA DOWNSTREAM CONSUMER ENTRYPOINT "
        "RESOLUTION FORENSIC AUDIT v0.2"
    )

    print(
        "MODE                         : "
        "READ ONLY STATIC FORENSICS"
    )

    print(
        "PRODUCTION EXECUTION         : "
        "NONE"
    )

    print(
        "DATABASE WRITE               : "
        "BLOCKED"
    )

    print(
        "PRODUCER EXCLUSION           : "
        "ENABLED"
    )

    print(
        "PERSISTENCE EXCLUSION        : "
        "ENABLED"
    )

    print(
        "FORENSIC ARTIFACT EXCLUSION  : "
        "ENABLED"
    )

    try:

        section(
            "STEP 1 — PROJECT PATH SAFETY"
        )

        print(
            f"PROJECT PATH : "
            f"{PROJECT_DIR}"
        )

        print(
            f"DATABASE     : "
            f"{DB_FILE}"
        )

        print(
            f"DATABASE FOUND : "
            f"{os.path.isfile(DB_FILE)}"
        )

        section(
            "STEP 2 — PRODUCER / PERSISTENCE EXCLUSION"
        )

        print(
            "EXCLUDED PRODUCER FILES"
        )

        for item in sorted(
            PRODUCER_FILES
        ):

            print(
                f"  - {item}"
            )

        print()

        print(
            "EXCLUDED PRODUCER FUNCTIONS"
        )

        for item in sorted(
            PRODUCER_FUNCTIONS
        ):

            print(
                f"  - {item}"
            )

        scan_production_sources()

        verify_database()

        build_candidates()

        selected = (
            resolve_selected_consumer()
        )

        print_call_graph_context(
            selected
        )

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

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )