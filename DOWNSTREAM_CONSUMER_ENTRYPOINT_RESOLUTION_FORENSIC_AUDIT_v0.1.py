import ast
import os
import sqlite3
import time
import traceback
from collections import defaultdict


# ============================================================
# ARUNDA
# DOWNSTREAM CONSUMER ENTRYPOINT RESOLUTION
# FORENSIC AUDIT v0.1
# ============================================================
#
# PURPOSE
# -------
# Resolve the strongest production downstream consumer
# candidate after market_data.
#
# VERIFIED PREVIOUS FRONTIER
# --------------------------
#
# calculate_analysis
#        ↓
# save_analysis assignment
#        ↓
# stored market_data
#        ↓
# THIS AUDIT
#        ↓
# downstream consumer
#        ↓
# future runtime trace
#
#
# SAFETY
# ------
#
# READ-ONLY STATIC / DATABASE DISCOVERY
#
# NO production main()
# NO production function execution
# NO imports of production modules
# NO INSERT
# NO UPDATE
# NO DELETE
# NO ALTER
# NO CREATE
# NO DROP
# NO VACUUM
#
# Database is opened with SQLite mode=ro only.
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

OUTPUT_LIMIT = 30

TARGET_SYMBOLS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

MARKET_DATA_TOKEN = "market_data"

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "site-packages",
    "dist",
    "build",
    "backups",
    "backup",
}

IGNORED_FILES = {
    os.path.basename(__file__),
}

ENTRYPOINT_NAMES = {
    "main",
    "run",
    "start",
    "execute",
    "pipeline",
    "run_pipeline",
    "main_loop",
    "start_engine",
}

WRITE_PREFIXES = (
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


# ============================================================
# GLOBAL FORENSIC STATE
# ============================================================

files_scanned = []
parsed_files = []
parse_errors = []

functions = {}
function_nodes = {}

call_edges = defaultdict(set)
reverse_call_edges = defaultdict(set)

market_data_references = []
consumer_candidates = []

database_target_reads = []

static_write_references = []


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
# PATH HELPERS
# ============================================================

def relative_path(path):

    try:
        return os.path.relpath(
            path,
            PROJECT_DIR
        )
    except Exception:
        return path


def should_ignore_directory(name):

    return name in IGNORED_DIRS


def should_ignore_file(name):

    if name in IGNORED_FILES:
        return True

    if not name.endswith(".py"):
        return True

    return False


# ============================================================
# STEP 1 — PATH SAFETY
# ============================================================

def verify_paths():

    section(
        "STEP 1 — PATH SAFETY"
    )

    print(
        f"PROJECT DIRECTORY           : {PROJECT_DIR}"
    )

    print(
        f"DATABASE PATH               : {DB_FILE}"
    )

    print(
        f"DATABASE FOUND              : "
        f"{os.path.isfile(DB_FILE)}"
    )

    if not os.path.isdir(PROJECT_DIR):

        raise RuntimeError(
            "Project directory does not exist."
        )

    if not os.path.isfile(DB_FILE):

        raise FileNotFoundError(
            DB_FILE
        )


# ============================================================
# STEP 2 — PYTHON FILE DISCOVERY
# ============================================================

def discover_python_files():

    section(
        "STEP 2 — PYTHON SOURCE DISCOVERY"
    )

    discovered = []

    for root, dirs, files in os.walk(
        PROJECT_DIR
    ):

        dirs[:] = [
            directory
            for directory in dirs
            if not should_ignore_directory(
                directory
            )
        ]

        for filename in files:

            if should_ignore_file(
                filename
            ):
                continue

            full_path = os.path.join(
                root,
                filename
            )

            discovered.append(
                full_path
            )

    discovered.sort()

    files_scanned.extend(
        discovered
    )

    print(
        f"PYTHON FILES DISCOVERED     : "
        f"{len(discovered)}"
    )

    print()

    for path in discovered[:OUTPUT_LIMIT]:

        print(
            f"  {relative_path(path)}"
        )

    if len(discovered) > OUTPUT_LIMIT:

        print(
            f"  ... "
            f"{len(discovered) - OUTPUT_LIMIT} "
            f"more"
        )

    return discovered


# ============================================================
# AST HELPERS
# ============================================================

def function_qualified_name(
    file_path,
    node,
    class_stack=None
):

    if class_stack is None:
        class_stack = []

    parts = [
        relative_path(file_path)
    ]

    if class_stack:
        parts.extend(
            class_stack
        )

    parts.append(
        node.name
    )

    return "::".join(
        parts
    )


def get_constant_string(node):

    if isinstance(
        node,
        ast.Constant
    ):

        if isinstance(
            node.value,
            str
        ):

            return node.value

    if isinstance(
        node,
        ast.Str
    ):

        return node.s

    return None


def node_contains_market_data_name(
    node
):

    found = []

    for child in ast.walk(node):

        if isinstance(
            child,
            ast.Name
        ):

            if child.id == MARKET_DATA_TOKEN:

                found.append(
                    (
                        "Name",
                        child.id,
                        child.lineno
                    )
                )

        elif isinstance(
            child,
            ast.Attribute
        ):

            if child.attr == MARKET_DATA_TOKEN:

                found.append(
                    (
                        "Attribute",
                        child.attr,
                        child.lineno
                    )
                )

        elif isinstance(
            child,
            ast.Constant
        ):

            if isinstance(
                child.value,
                str
            ):

                if MARKET_DATA_TOKEN in (
                    child.value.lower()
                ):

                    found.append(
                        (
                            "String",
                            child.value,
                            child.lineno
                        )
                    )

    return found


def node_contains_sql_market_data(
    node
):

    references = []

    for child in ast.walk(node):

        if not isinstance(
            child,
            ast.Constant
        ):
            continue

        value = child.value

        if not isinstance(
            value,
            str
        ):
            continue

        normalized = (
            " ".join(
                value.upper().split()
            )
        )

        if MARKET_DATA_TOKEN.upper() in normalized:

            references.append(
                {
                    "line": child.lineno,
                    "sql": value,
                    "write_like":
                        normalized.startswith(
                            WRITE_PREFIXES
                        ),
                }
            )

    return references


# ============================================================
# STEP 3 — STATIC SOURCE PARSING
# ============================================================

class SourceVisitor(
    ast.NodeVisitor
):

    def __init__(
        self,
        file_path
    ):

        self.file_path = file_path

        self.scope_stack = []

        self.class_stack = []

        self.current_function = None

        self.local_functions = []

    def visit_ClassDef(
        self,
        node
    ):

        self.class_stack.append(
            node.name
        )

        self.generic_visit(
            node
        )

        self.class_stack.pop()

    def visit_FunctionDef(
        self,
        node
    ):

        self._visit_function(
            node
        )

    def visit_AsyncFunctionDef(
        self,
        node
    ):

        self._visit_function(
            node
        )

    def _visit_function(
        self,
        node
    ):

        qualified = (
            function_qualified_name(
                self.file_path,
                node,
                self.class_stack
            )
        )

        self.local_functions.append(
            qualified
        )

        functions[
            qualified
        ] = {
            "name": node.name,
            "qualified": qualified,
            "file": self.file_path,
            "relative_file":
                relative_path(
                    self.file_path
                ),
            "line": node.lineno,
            "end_line":
                getattr(
                    node,
                    "end_lineno",
                    node.lineno
                ),
            "class":
                ".".join(
                    self.class_stack
                )
                if self.class_stack
                else None,
            "market_data_refs": [],
            "sql_market_data_refs": [],
            "calls": [],
            "entrypoint_name":
                node.name in ENTRYPOINT_NAMES,
        }

        function_nodes[
            qualified
        ] = node

        previous_function = (
            self.current_function
        )

        self.current_function = qualified

        market_refs = (
            node_contains_market_data_name(
                node
            )
        )

        sql_refs = (
            node_contains_sql_market_data(
                node
            )
        )

        functions[
            qualified
        ][
            "market_data_refs"
        ] = market_refs

        functions[
            qualified
        ][
            "sql_market_data_refs"
        ] = sql_refs

        for ref in market_refs:

            market_data_references.append(
                {
                    "function":
                        qualified,
                    "file":
                        self.file_path,
                    "relative_file":
                        relative_path(
                            self.file_path
                        ),
                    "line":
                        ref[2],
                    "kind":
                        ref[0],
                    "value":
                        ref[1],
                }
            )

        for ref in sql_refs:

            market_data_references.append(
                {
                    "function":
                        qualified,
                    "file":
                        self.file_path,
                    "relative_file":
                        relative_path(
                            self.file_path
                        ),
                    "line":
                        ref["line"],
                    "kind":
                        "SQL",
                    "value":
                        ref["sql"],
                    "write_like":
                        ref["write_like"],
                }
            )

            if ref["write_like"]:

                static_write_references.append(
                    {
                        "function":
                            qualified,
                        "file":
                            self.file_path,
                        "relative_file":
                            relative_path(
                                self.file_path
                            ),
                        "line":
                            ref["line"],
                        "sql":
                            ref["sql"],
                    }
                )

        self._collect_calls(
            node,
            qualified
        )

        self.current_function = (
            previous_function
        )

    def _collect_calls(
        self,
        node,
        caller
    ):

        for child in ast.walk(node):

            if isinstance(
                child,
                ast.Call
            ):

                callee = (
                    self._call_name(
                        child.func
                    )
                )

                if callee is None:
                    continue

                functions[
                    caller
                ][
                    "calls"
                ].append(
                    {
                        "name": callee,
                        "line":
                            child.lineno,
                    }
                )

    def _call_name(
        self,
        node
    ):

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


def parse_source_file(
    path
):

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

        visitor = SourceVisitor(
            path
        )

        visitor.visit(
            tree
        )

        parsed_files.append(
            path
        )

        return tree

    except (
        SyntaxError,
        UnicodeDecodeError,
        OSError,
        ValueError
    ) as exc:

        parse_errors.append(
            {
                "file": path,
                "error": repr(exc),
            }
        )

        return None


def parse_all_sources(
    paths
):

    section(
        "STEP 3 — STATIC SOURCE PARSING"
    )

    for path in paths:

        parse_source_file(
            path
        )

    print(
        f"FILES PARSED                : "
        f"{len(parsed_files)}"
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

    if parse_errors:

        print()

        print(
            "PARSE ERROR SAMPLE"
        )

        for item in parse_errors[:10]:

            print(
                f"  {relative_path(item['file'])}"
            )

            print(
                f"    {item['error']}"
            )


# ============================================================
# STEP 4 — BUILD STATIC CALL GRAPH
# ============================================================

def build_call_graph():

    section(
        "STEP 4 — STATIC CALL GRAPH RESOLUTION"
    )

    by_short_name = defaultdict(
        list
    )

    for qualified, info in functions.items():

        by_short_name[
            info["name"]
        ].append(
            qualified
        )

    edge_count = 0

    unresolved_calls = 0

    for caller, info in functions.items():

        for call in info["calls"]:

            call_name = call["name"]

            short_name = (
                call_name.split(
                    "."
                )[-1]
            )

            candidates = (
                by_short_name.get(
                    short_name,
                    []
                )
            )

            if len(candidates) == 1:

                callee = candidates[0]

                call_edges[
                    caller
                ].add(
                    callee
                )

                reverse_call_edges[
                    callee
                ].add(
                    caller
                )

                edge_count += 1

            else:

                unresolved_calls += 1

    print(
        f"CALL GRAPH EDGES            : "
        f"{edge_count}"
    )

    print(
        f"UNRESOLVED CALL REFERENCES   : "
        f"{unresolved_calls}"
    )


# ============================================================
# DATABASE READ-ONLY VERIFICATION
# ============================================================

def verify_database_read_only():

    section(
        "STEP 5 — READ-ONLY market_data DATABASE VERIFICATION"
    )

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
            WHERE type = 'table'
              AND name = 'market_data'
            LIMIT 1
            """
        ).fetchone()

        found = table is not None

        print(
            f"MARKET_DATA TABLE FOUND    : "
            f"{found}"
        )

        if not found:

            return

        total = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM market_data
            """
        ).fetchone()

        print(
            f"MARKET_DATA TOTAL ROWS      : "
            f"{int(total['count'])}"
        )

        print()

        print(
            "TARGET READ VERIFICATION"
        )

        for symbol in TARGET_SYMBOLS:

            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS count
                FROM market_data
                WHERE symbol = ?
                """,
                (symbol,)
            ).fetchone()

            count = int(
                row["count"]
            )

            database_target_reads.append(
                {
                    "symbol": symbol,
                    "rows": count,
                }
            )

            print(
                f"{symbol:<6} | ROWS={count}"
            )

    finally:

        conn.close()


# ============================================================
# CONSUMER CLASSIFICATION
# ============================================================

def is_production_like_file(
    info
):

    filename = (
        info["relative_file"]
        .lower()
    )

    excluded_fragments = (
        "test",
        "audit",
        "forensic",
        "debug",
        "backup",
        "example",
        "demo",
        "scratch",
        "temp",
    )

    return not any(
        fragment in filename
        for fragment in excluded_fragments
    )


def score_function(
    qualified,
    info
):

    score = 0

    reasons = []

    sql_refs = info[
        "sql_market_data_refs"
    ]

    name_refs = info[
        "market_data_refs"
    ]

    calls = info[
        "calls"
    ]

    # --------------------------------------------------------
    # DIRECT SQL SELECT
    # --------------------------------------------------------

    for ref in sql_refs:

        sql = ref[
            "sql"
        ].upper()

        if "SELECT" in sql:

            score += 40

            reasons.append(
                "DIRECT market_data SELECT +40"
            )

            if (
                "TECHNICAL_SCORE"
                in sql
            ):

                score += 15

                reasons.append(
                    "READS technical_score +15"
                )

            if (
                "RSI14"
                in sql
            ):

                score += 5

                reasons.append(
                    "READS RSI14 +5"
                )

            if (
                "EMA20"
                in sql
            ):

                score += 5

                reasons.append(
                    "READS EMA20 +5"
                )

            if (
                "EMA50"
                in sql
            ):

                score += 5

                reasons.append(
                    "READS EMA50 +5"
                )

            if (
                "MACD"
                in sql
            ):

                score += 5

                reasons.append(
                    "READS MACD +5"
                )

            if (
                "ADX14"
                in sql
            ):

                score += 5

                reasons.append(
                    "READS ADX14 +5"
                )

    # --------------------------------------------------------
    # market_data NAME / TABLE REFERENCE
    # --------------------------------------------------------

    if name_refs:

        score += min(
            len(name_refs) * 2,
            10
        )

        reasons.append(
            f"market_data references "
            f"+{min(len(name_refs) * 2, 10)}"
        )

    # --------------------------------------------------------
    # FUNCTION NAME
    # --------------------------------------------------------

    name = info[
        "name"
    ].lower()

    if any(
        token in name
        for token in (
            "signal",
            "score",
            "analysis",
            "strategy",
            "decision",
            "ranking",
            "rank",
            "candidate",
            "selection",
            "hunter",
            "prediction",
            "portfolio",
        )
    ):

        score += 15

        reasons.append(
            "DOWNSTREAM semantic function name +15"
        )

    # --------------------------------------------------------
    # ENTRYPOINT
    # --------------------------------------------------------

    if info[
        "entrypoint_name"
    ]:

        score += 10

        reasons.append(
            "ENTRYPOINT-LIKE FUNCTION +10"
        )

    # --------------------------------------------------------
    # PRODUCTION FILE
    # --------------------------------------------------------

    if is_production_like_file(
        info
    ):

        score += 5

        reasons.append(
            "PRODUCTION-LIKE SOURCE FILE +5"
        )

    else:

        score -= 25

        reasons.append(
            "NON-PRODUCTION/AUDIT FILE -25"
        )

    # --------------------------------------------------------
    # CALLER COUNT
    # --------------------------------------------------------

    caller_count = len(
        reverse_call_edges.get(
            qualified,
            set()
        )
    )

    if caller_count > 0:

        bonus = min(
            caller_count * 3,
            15
        )

        score += bonus

        reasons.append(
            f"HAS CALLERS +{bonus}"
        )

    # --------------------------------------------------------
    # RETURN / OUTPUT SIGNAL
    # --------------------------------------------------------

    if any(
        token in name
        for token in (
            "signal",
            "decision",
            "candidate",
            "ranking",
            "rank",
            "score",
        )
    ):

        score += 10

        reasons.append(
            "LIKELY DOWNSTREAM OUTPUT +10"
        )

    return score, reasons


# ============================================================
# STEP 6 — CONSUMER CANDIDATE RESOLUTION
# ============================================================

def resolve_consumer_candidates():

    section(
        "STEP 6 — DOWNSTREAM CONSUMER CANDIDATE RESOLUTION"
    )

    candidates = []

    for qualified, info in functions.items():

        if not info[
            "market_data_refs"
        ]:

            continue

        score, reasons = score_function(
            qualified,
            info
        )

        callers = sorted(
            reverse_call_edges.get(
                qualified,
                set()
            )
        )

        callees = sorted(
            call_edges.get(
                qualified,
                set()
            )
        )

        candidate = {
            "qualified":
                qualified,
            "name":
                info["name"],
            "file":
                info["relative_file"],
            "line":
                info["line"],
            "score":
                score,
            "reasons":
                reasons,
            "callers":
                callers,
            "callees":
                callees,
            "sql_refs":
                info["sql_market_data_refs"],
            "market_refs":
                info["market_data_refs"],
            "entrypoint":
                info["entrypoint_name"],
        }

        candidates.append(
            candidate
        )

    candidates.sort(
        key=lambda item: (
            item["score"],
            len(item["callers"]),
            len(item["sql_refs"]),
        ),
        reverse=True
    )

    consumer_candidates.extend(
        candidates
    )

    print(
        f"CONSUMER CANDIDATES         : "
        f"{len(candidates)}"
    )

    print()

    print(
        "TOP DOWNSTREAM CONSUMER CANDIDATES"
    )

    print(
        "-" * 100
    )

    for index, candidate in enumerate(
        candidates[:OUTPUT_LIMIT],
        start=1
    ):

        print(
            f"{index:>2}. "
            f"SCORE={candidate['score']:>4} | "
            f"{candidate['name']:<30} | "
            f"{candidate['file']}:{candidate['line']}"
        )

        if candidate["entrypoint"]:

            print(
                "    ENTRYPOINT-LIKE : YES"
            )

        if candidate["sql_refs"]:

            print(
                f"    SQL REFERENCES  : "
                f"{len(candidate['sql_refs'])}"
            )

        if candidate["callers"]:

            print(
                f"    CALLERS         : "
                f"{len(candidate['callers'])}"
            )

        for reason in candidate[
            "reasons"
        ][:8]:

            print(
                f"    + {reason}"
            )

        print()


# ============================================================
# ENTRYPOINT PATH ANALYSIS
# ============================================================

def reachable_from(
    start,
    max_depth=8
):

    visited = set()

    frontier = [
        (
            start,
            0
        )
    ]

    while frontier:

        current, depth = frontier.pop()

        if current in visited:
            continue

        visited.add(
            current
        )

        if depth >= max_depth:
            continue

        for child in call_edges.get(
            current,
            set()
        ):

            if child not in visited:

                frontier.append(
                    (
                        child,
                        depth + 1
                    )
                )

    return visited


def find_possible_entrypoints():

    entrypoints = []

    for qualified, info in functions.items():

        if info[
            "entrypoint_name"
        ]:

            entrypoints.append(
                qualified
            )

    return sorted(
        entrypoints
    )


def calculate_entrypoint_evidence(
    candidate
):

    candidate_name = (
        candidate["qualified"]
    )

    entrypoints = (
        find_possible_entrypoints()
    )

    evidence = []

    for entrypoint in entrypoints:

        reachable = reachable_from(
            entrypoint,
            max_depth=10
        )

        if candidate_name in reachable:

            evidence.append(
                entrypoint
            )

    return evidence


# ============================================================
# STEP 7 — PRODUCTION ENTRYPOINT RESOLUTION
# ============================================================

def resolve_production_entrypoint():

    section(
        "STEP 7 — PRODUCTION ENTRYPOINT PATH RESOLUTION"
    )

    if not consumer_candidates:

        print(
            "NO CONSUMER CANDIDATES"
        )

        return None

    enriched = []

    for candidate in consumer_candidates:

        entrypoints = (
            calculate_entrypoint_evidence(
                candidate
            )
        )

        item = dict(
            candidate
        )

        item[
            "reachable_entrypoints"
        ] = entrypoints

        if entrypoints:

            item[
                "score"
            ] += min(
                len(entrypoints) * 20,
                40
            )

            item[
                "reasons"
            ] = list(
                candidate[
                    "reasons"
                ]
            )

            item[
                "reasons"
            ].append(
                "REACHABLE FROM PRODUCTION-LIKE ENTRYPOINT "
                f"+{min(len(entrypoints) * 20, 40)}"
            )

        enriched.append(
            item
        )

    enriched.sort(
        key=lambda item: (
            item["score"],
            len(
                item[
                    "reachable_entrypoints"
                ]
            ),
            len(
                item["callers"]
            ),
        ),
        reverse=True
    )

    print(
        "ENTRYPOINT-REACHABLE CANDIDATES"
    )

    print(
        "-" * 100
    )

    for index, candidate in enumerate(
        enriched[:OUTPUT_LIMIT],
        start=1
    ):

        print(
            f"{index:>2}. "
            f"SCORE={candidate['score']:>4} | "
            f"{candidate['name']:<30} | "
            f"{candidate['file']}:{candidate['line']}"
        )

        reachable = candidate[
            "reachable_entrypoints"
        ]

        if reachable:

            print(
                "    REACHABLE FROM:"
            )

            for entrypoint in reachable[
                :10
            ]:

                print(
                    f"      {entrypoint}"
                )

        else:

            print(
                "    REACHABLE FROM: NONE PROVEN"
            )

        print()

    return enriched


# ============================================================
# CONFIDENCE DETERMINATION
# ============================================================

def determine_resolution(
    enriched
):

    if not enriched:

        return {
            "status":
                "NO_CONSUMER_CANDIDATE",
            "selected":
                None,
        }

    top = enriched[0]

    if len(enriched) == 1:

        return {
            "status":
                "SINGLE_CONSUMER_CANDIDATE",
            "selected":
                top,
        }

    second = enriched[1]

    score_gap = (
        top["score"]
        - second["score"]
    )

    top_entrypoints = len(
        top[
            "reachable_entrypoints"
        ]
    )

    if (
        top_entrypoints > 0
        and score_gap >= 15
    ):

        return {
            "status":
                "PRODUCTION_CONSUMER_CANDIDATE_RESOLVED",
            "selected":
                top,
        }

    if (
        top_entrypoints > 0
        and score_gap >= 5
    ):

        return {
            "status":
                "PRODUCTION_CONSUMER_CANDIDATE_STRONG",
            "selected":
                top,
        }

    return {
        "status":
            "AMBIGUOUS_CONSUMER_CANDIDATES",
        "selected":
            None,
    }


# ============================================================
# STEP 8 — RESOLUTION REPORT
# ============================================================

def print_resolution_report(
    resolution
):

    section(
        "STEP 8 — CONSUMER ENTRYPOINT RESOLUTION"
    )

    status = resolution[
        "status"
    ]

    selected = resolution[
        "selected"
    ]

    print(
        f"STATUS                      : "
        f"{status}"
    )

    if selected is None:

        print()

        print(
            "NO CONSUMER WAS SELECTED."
        )

        print(
            "This is intentional."
        )

        print(
            "The audit will not guess between "
            "competing production paths."
        )

        print()

        print(
            "NEXT FRONTIER:"
        )

        print(
            "Resolve the competing candidates "
            "with a narrower source-level audit."
        )

        return

    print()

    print(
        "SELECTED CONSUMER CANDIDATE"
    )

    print(
        "-" * 100
    )

    print(
        f"FUNCTION                    : "
        f"{selected['qualified']}"
    )

    print(
        f"SCORE                       : "
        f"{selected['score']}"
    )

    print(
        f"FILE                        : "
        f"{selected['file']}"
    )

    print(
        f"LINE                        : "
        f"{selected['line']}"
    )

    print(
        f"ENTRYPOINT-LIKE             : "
        f"{selected['entrypoint']}"
    )

    print(
        f"CALLERS                     : "
        f"{len(selected['callers'])}"
    )

    print(
        f"CALLEES                     : "
        f"{len(selected['callees'])}"
    )

    print(
        f"REACHABLE ENTRYPOINTS       : "
        f"{len(selected['reachable_entrypoints'])}"
    )

    print()

    print(
        "EVIDENCE"
    )

    for reason in selected[
        "reasons"
    ]:

        print(
            f"  + {reason}"
        )

    print()

    if selected[
        "callers"
    ]:

        print(
            "CALLERS"
        )

        for caller in selected[
            "callers"
        ][:20]:

            print(
                f"  {caller}"
            )

    print()

    if selected[
        "callees"
    ]:

        print(
            "CALLEES"
        )

        for callee in selected[
            "callees"
        ][:20]:

            print(
                f"  {callee}"
            )

    print()

    if selected[
        "reachable_entrypoints"
    ]:

        print(
            "PRODUCTION ENTRYPOINT PATH"
        )

        for entrypoint in selected[
            "reachable_entrypoints"
        ][:20]:

            print(
                f"  {entrypoint}"
            )


# ============================================================
# STEP 9 — FINAL FORENSIC SUMMARY
# ============================================================

def final_summary(
    resolution
):

    section(
        "STEP 9 — FINAL FORENSIC SUMMARY"
    )

    status = resolution[
        "status"
    ]

    selected = resolution[
        "selected"
    ]

    print(
        f"PYTHON FILES SCANNED        : "
        f"{len(files_scanned)}"
    )

    print(
        f"FILES PARSED                : "
        f"{len(parsed_files)}"
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
        f"CALL GRAPH EDGES            : "
        f"{sum(len(v) for v in call_edges.values())}"
    )

    print(
        f"CONSUMER CANDIDATES         : "
        f"{len(consumer_candidates)}"
    )

    print(
        f"DATABASE TARGET READS       : "
        f"{len(database_target_reads)}"
    )

    print(
        f"STATIC WRITE REFERENCES     : "
        f"{len(static_write_references)}"
    )

    print()

    print(
        "FORENSIC CONCLUSION"
    )

    line("-")

    if status == (
        "PRODUCTION_CONSUMER_CANDIDATE_RESOLVED"
    ):

        print(
            "STATUS                        : "
            "PRODUCTION_CONSUMER_CANDIDATE_RESOLVED"
        )

        print(
            "MEANING                       : "
            "A strongest downstream consumer "
            "candidate was resolved using direct "
            "market_data evidence and static "
            "production-entrypoint reachability."
        )

        print(
            "NEXT FRONTIER                 : "
            "Build a dedicated READ-ONLY runtime "
            "consumption trace for the selected "
            "consumer."
        )

    elif status == (
        "PRODUCTION_CONSUMER_CANDIDATE_STRONG"
    ):

        print(
            "STATUS                        : "
            "PRODUCTION_CONSUMER_CANDIDATE_STRONG"
        )

        print(
            "MEANING                       : "
            "One downstream consumer has substantially "
            "stronger evidence than the alternatives, "
            "but the static proof is not sufficiently "
            "exclusive to declare it final."
        )

        print(
            "NEXT FRONTIER                 : "
            "Narrow the candidate set before runtime "
            "execution."
        )

    elif status == (
        "SINGLE_CONSUMER_CANDIDATE"
    ):

        print(
            "STATUS                        : "
            "SINGLE_CONSUMER_CANDIDATE"
        )

        print(
            "MEANING                       : "
            "Only one relevant consumer candidate "
            "was identified."
        )

        print(
            "NEXT FRONTIER                 : "
            "Perform READ-ONLY runtime consumption "
            "trace."
        )

    elif status == (
        "NO_CONSUMER_CANDIDATE"
    ):

        print(
            "STATUS                        : "
            "NO_CONSUMER_CANDIDATE"
        )

        print(
            "MEANING                       : "
            "No downstream consumer candidate "
            "could be established."
        )

        print(
            "NEXT FRONTIER                 : "
            "Expand source-level discovery."
        )

    else:

        print(
            "STATUS                        : "
            "AMBIGUOUS_CONSUMER_CANDIDATES"
        )

        print(
            "MEANING                       : "
            "Multiple downstream consumers remain "
            "plausible and no production path can "
            "be selected safely."
        )

        print(
            "NEXT FRONTIER                 : "
            "Perform targeted candidate-resolution "
            "forensics; do not execute a guessed "
            "consumer."
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
# MAIN
# ============================================================

def main():

    started = time.perf_counter()

    section(
        "ARUNDA DOWNSTREAM CONSUMER ENTRYPOINT "
        "RESOLUTION FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                        : "
        "READ-ONLY STATIC FORENSICS"
    )

    print(
        "PRODUCTION EXECUTION        : "
        "NONE"
    )

    print(
        "PRODUCTION main()           : "
        "NOT CALLED"
    )

    print(
        "DATABASE                    : "
        "READ ONLY"
    )

    print(
        "TARGETS                     : "
        "BTC / ETH / SOL / XRP"
    )

    print(
        "PURPOSE                     : "
        "RESOLVE DOWNSTREAM CONSUMER"
    )

    try:

        verify_paths()

        paths = (
            discover_python_files()
        )

        parse_all_sources(
            paths
        )

        build_call_graph()

        verify_database_read_only()

        resolve_consumer_candidates()

        enriched = (
            resolve_production_entrypoint()
        )

        if enriched is None:

            enriched = []

        resolution = (
            determine_resolution(
                enriched
            )
        )

        print_resolution_report(
            resolution
        )

        final_summary(
            resolution
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