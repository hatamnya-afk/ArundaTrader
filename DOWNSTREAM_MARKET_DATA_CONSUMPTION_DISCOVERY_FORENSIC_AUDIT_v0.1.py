import ast
import os
import re
import sqlite3
import time
import traceback
from collections import defaultdict


# ============================================================
# ARUNDA
# DOWNSTREAM MARKET_DATA CONSUMPTION
# FORENSIC DISCOVERY AUDIT v0.1
# ============================================================
#
# PURPOSE
# -------
# Previous frontier VERIFIED:
#
#     calculate_analysis()
#             |
#             v
#     save_analysis assignment
#             |
#             v
#     stored market_data
#
# Current frontier:
#
#     stored market_data
#             |
#             v
#     downstream consumer
#             |
#             v
#     downstream transformation
#             |
#             v
#     next runtime object
#
# SAFETY
# ------
# READ ONLY
#
# This audit:
#
#   - does NOT execute production main()
#   - does NOT execute production engines
#   - does NOT modify production source
#   - does NOT modify production database
#   - does NOT INSERT
#   - does NOT UPDATE
#   - does NOT DELETE
#   - does NOT ALTER
#   - does NOT CREATE
#   - does NOT DROP
#   - does NOT fabricate runtime values
#   - does NOT reconstruct runtime objects
#
# It only discovers source-level downstream consumers.
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

MAX_SOURCE_FILE_SIZE = (
    5 * 1024 * 1024
)


# ============================================================
# FORENSIC STATE
# ============================================================

python_files = []

parsed_files = []

parse_errors = []

market_data_references = []

sql_consumers = []

function_consumers = []

call_sites = []

write_like_references = []

database_reads = []

production_execution = False

production_write = False


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


def safe_repr(value, limit=1600):

    try:
        text = repr(value)

    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        text = (
            text[:limit]
            + "...<TRUNCATED>"
        )

    return text


# ============================================================
# PATH SAFETY
# ============================================================

def verify_paths():

    section(
        "STEP 1 — PATH SAFETY"
    )

    print(
        "PROJECT PATH              : "
        + PROJECT_DIR
    )

    print(
        "DATABASE PATH             : "
        + DB_FILE
    )

    print(
        "DATABASE EXISTS           : "
        + str(os.path.isfile(DB_FILE))
    )

    if not os.path.isdir(PROJECT_DIR):

        raise FileNotFoundError(
            PROJECT_DIR
        )

    if not os.path.isfile(DB_FILE):

        raise FileNotFoundError(
            DB_FILE
        )

    print(
        "PRODUCTION EXECUTION      : DISABLED"
    )

    print(
        "DATABASE WRITE            : DISABLED"
    )

    print(
        "SOURCE MODIFICATION       : DISABLED"
    )


# ============================================================
# SOURCE INVENTORY
# ============================================================

def inventory_python_files():

    section(
        "STEP 2 — PYTHON SOURCE INVENTORY"
    )

    current_file = os.path.basename(
        __file__
    )

    for root, dirs, files in os.walk(
        PROJECT_DIR
    ):

        dirs[:] = [
            directory
            for directory in dirs
            if directory != "__pycache__"
            and not directory.startswith(".")
        ]

        for filename in files:

            if not filename.endswith(".py"):
                continue

            if filename == current_file:
                continue

            full_path = os.path.join(
                root,
                filename
            )

            try:
                size = os.path.getsize(
                    full_path
                )
            except OSError:
                continue

            if size > MAX_SOURCE_FILE_SIZE:

                print(
                    "[SKIP LARGE FILE] "
                    + os.path.relpath(
                        full_path,
                        PROJECT_DIR
                    )
                )

                continue

            python_files.append(
                full_path
            )

    python_files.sort()

    print(
        "PYTHON FILES FOUND       : "
        + str(len(python_files))
    )

    for path in python_files:

        relative_path = os.path.relpath(
            path,
            PROJECT_DIR
        )

        print(
            "  "
            + relative_path
        )


# ============================================================
# SOURCE PARSING
# ============================================================

def parse_python_sources():

    section(
        "STEP 3 — AST SOURCE PARSING"
    )

    for path in python_files:

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

            parsed_files.append(
                {
                    "path": path,
                    "source": source,
                    "tree": tree,
                }
            )

        except Exception as exc:

            parse_errors.append(
                {
                    "path": path,
                    "exception": repr(exc),
                    "traceback": traceback.format_exc(),
                }
            )

    print(
        "PARSED FILES             : "
        + str(len(parsed_files))
    )

    print(
        "PARSE ERRORS             : "
        + str(len(parse_errors))
    )

    for error in parse_errors:

        print()

        print(
            "[PARSE ERROR]"
        )

        print(
            "FILE  : "
            + error["path"]
        )

        print(
            "ERROR : "
            + error["exception"]
        )


# ============================================================
# AST SOURCE TEXT
# ============================================================

def node_text(
    source,
    node
):

    try:

        return ast.get_source_segment(
            source,
            node
        )

    except Exception:

        return None


# ============================================================
# SQL CLASSIFICATION
# ============================================================

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


def normalize_sql(
    text
):

    return " ".join(
        str(text)
        .strip()
        .upper()
        .split()
    )


def classify_write_like(
    text
):

    normalized = normalize_sql(
        text
    )

    if not normalized:
        return False

    return normalized.startswith(
        WRITE_PREFIXES
    )


# ============================================================
# SQL MARKET_DATA DETECTION
# ============================================================

def detect_sql_consumers(
    path,
    source,
    tree
):

    for node in ast.walk(tree):

        candidate = None

        if isinstance(
            node,
            ast.Constant
        ):

            if isinstance(
                node.value,
                str
            ):

                candidate = node.value

        elif isinstance(
            node,
            ast.JoinedStr
        ):

            candidate = node_text(
                source,
                node
            )

        if candidate is None:
            continue

        if "market_data" not in candidate.lower():
            continue

        upper_candidate = candidate.upper()

        sql_keywords = (
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "CREATE",
            "ALTER",
            "DROP",
        )

        has_sql_keyword = any(
            keyword in upper_candidate
            for keyword in sql_keywords
        )

        if not has_sql_keyword:
            continue

        write_like = classify_write_like(
            candidate
        )

        event = {
            "file": path,
            "line": getattr(
                node,
                "lineno",
                None
            ),
            "sql": candidate,
            "write_like": write_like,
        }

        sql_consumers.append(
            event
        )

        if write_like:

            write_like_references.append(
                event
            )


# ============================================================
# FUNCTION CONSUMER DETECTION
# ============================================================

def detect_function_consumers(
    path,
    source,
    tree
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

        function_source = (
            node_text(
                source,
                node
            )
            or ""
        )

        if (
            "market_data"
            not in function_source.lower()
        ):

            continue

        function_consumers.append(
            {
                "file": path,
                "line": node.lineno,
                "end_line": getattr(
                    node,
                    "end_lineno",
                    None
                ),
                "function": node.name,
                "source": function_source,
            }
        )


# ============================================================
# CALL SITE DETECTION
# ============================================================

def detect_call_sites(
    path,
    source,
    tree
):

    consumer_names = {
        item["function"]
        for item in function_consumers
    }

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call
        ):

            continue

        function_name = None

        if isinstance(
            node.func,
            ast.Name
        ):

            function_name = node.func.id

        elif isinstance(
            node.func,
            ast.Attribute
        ):

            function_name = node.func.attr

        if (
            function_name
            not in consumer_names
        ):

            continue

        call_sites.append(
            {
                "file": path,
                "line": node.lineno,
                "function": function_name,
                "call": node_text(
                    source,
                    node
                ),
            }
        )


# ============================================================
# GENERIC MARKET_DATA REFERENCE DETECTION
# ============================================================

def detect_generic_references(
    path,
    source,
    tree
):

    for node in ast.walk(tree):

        text = node_text(
            source,
            node
        )

        if not text:
            continue

        if (
            "market_data"
            not in text.lower()
        ):

            continue

        node_types = (
            ast.Name,
            ast.Attribute,
            ast.Constant,
            ast.Call,
            ast.Subscript,
        )

        if not isinstance(
            node,
            node_types
        ):

            continue

        market_data_references.append(
            {
                "file": path,
                "line": getattr(
                    node,
                    "lineno",
                    None
                ),
                "node_type":
                    type(node).__name__,
                "text": text[:1000],
            }
        )


# ============================================================
# SOURCE ANALYSIS
# ============================================================

def analyze_sources():

    section(
        "STEP 4 — DOWNSTREAM market_data CONSUMER DETECTION"
    )

    for item in parsed_files:

        path = item["path"]
        source = item["source"]
        tree = item["tree"]

        detect_sql_consumers(
            path,
            source,
            tree
        )

        detect_function_consumers(
            path,
            source,
            tree
        )

        detect_generic_references(
            path,
            source,
            tree
        )

    for item in parsed_files:

        detect_call_sites(
            item["path"],
            item["source"],
            item["tree"]
        )

    print(
        "SQL market_data REFERENCES : "
        + str(len(sql_consumers))
    )

    print(
        "FUNCTION CONSUMERS         : "
        + str(len(function_consumers))
    )

    print(
        "CALL SITES                 : "
        + str(len(call_sites))
    )

    print(
        "GENERIC REFERENCES         : "
        + str(len(market_data_references))
    )

    print(
        "WRITE-LIKE REFERENCES     : "
        + str(len(write_like_references))
    )


# ============================================================
# SQL REPORT
# ============================================================

def report_sql_consumers():

    subsection(
        "SQL CONSUMERS OF market_data"
    )

    if not sql_consumers:

        print(
            "NO SQL CONSUMER FOUND"
        )

        return

    for index, event in enumerate(
        sql_consumers,
        start=1
    ):

        relative_path = os.path.relpath(
            event["file"],
            PROJECT_DIR
        )

        print()

        print(
            "[SQL CONSUMER #"
            + str(index)
            + "]"
        )

        print(
            "FILE       : "
            + relative_path
        )

        print(
            "LINE       : "
            + str(event["line"])
        )

        print(
            "WRITE-LIKE : "
            + str(event["write_like"])
        )

        sql = (
            event["sql"]
            .replace("\n", " ")
            .replace("\r", " ")
        )

        print(
            "SQL        : "
            + sql[:1600]
        )


# ============================================================
# FUNCTION REPORT
# ============================================================

def report_function_consumers():

    subsection(
        "FUNCTIONS CONSUMING market_data"
    )

    if not function_consumers:

        print(
            "NO FUNCTION CONSUMER FOUND"
        )

        return

    for index, event in enumerate(
        function_consumers,
        start=1
    ):

        relative_path = os.path.relpath(
            event["file"],
            PROJECT_DIR
        )

        print()

        print(
            "[FUNCTION CONSUMER #"
            + str(index)
            + "]"
        )

        print(
            "FILE      : "
            + relative_path
        )

        print(
            "FUNCTION  : "
            + event["function"]
        )

        print(
            "LINE      : "
            + str(event["line"])
        )

        print(
            "END LINE  : "
            + str(event["end_line"])
        )


# ============================================================
# CALL SITE REPORT
# ============================================================

def report_call_sites():

    subsection(
        "DOWNSTREAM CONSUMER CALL SITES"
    )

    if not call_sites:

        print(
            "NO CALL SITE FOUND"
        )

        return

    for index, event in enumerate(
        call_sites,
        start=1
    ):

        relative_path = os.path.relpath(
            event["file"],
            PROJECT_DIR
        )

        print()

        print(
            "[CALL SITE #"
            + str(index)
            + "]"
        )

        print(
            "FILE     : "
            + relative_path
        )

        print(
            "LINE     : "
            + str(event["line"])
        )

        print(
            "FUNCTION : "
            + event["function"]
        )

        call_text = (
            event["call"]
            or "<SOURCE UNAVAILABLE>"
        )

        print(
            "CALL     : "
            + call_text[:1600]
        )


# ============================================================
# TARGET REFERENCE REPORT
# ============================================================

def report_target_references():

    subsection(
        "TARGET SYMBOL REFERENCE OBSERVATION"
    )

    target_hits = defaultdict(list)

    for item in market_data_references:

        text = item["text"]
        upper_text = text.upper()

        for symbol in TARGETS:

            pattern = (
                r"\b"
                + re.escape(symbol)
                + r"\b"
            )

            if re.search(
                pattern,
                upper_text
            ):

                target_hits[
                    symbol
                ].append(
                    item
                )

    for symbol in TARGETS:

        hits = target_hits.get(
            symbol,
            []
        )

        print(
            "{:<6} | REFERENCES={}".format(
                symbol,
                len(hits)
            )
        )


# ============================================================
# DATABASE READ-ONLY VERIFICATION
# ============================================================

def verify_market_data_database():

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

        schema = conn.execute(
            """
            SELECT
                name,
                type
            FROM sqlite_master
            WHERE name = 'market_data'
            """
        ).fetchall()

        print(
            "MARKET_DATA TABLE FOUND : "
            + str(bool(schema))
        )

        if not schema:
            return

        row = conn.execute(
            """
            SELECT COUNT(*) AS total_rows
            FROM market_data
            """
        ).fetchone()

        total_rows = int(
            row["total_rows"]
        )

        print(
            "MARKET_DATA TOTAL ROWS   : "
            + str(total_rows)
        )

        for symbol in TARGETS:

            row = conn.execute(
                """
                SELECT COUNT(*) AS row_count
                FROM market_data
                WHERE symbol = ?
                """,
                (symbol,)
            ).fetchone()

            count = int(
                row["row_count"]
            )

            database_reads.append(
                {
                    "symbol": symbol,
                    "row_count": count,
                }
            )

            print(
                "{:<6} | ROWS={}".format(
                    symbol,
                    count
                )
            )

        print()

        print(
            "LATEST STORED market_data ROW PER TARGET"
        )

        line("-")

        for symbol in TARGETS:

            row = conn.execute(
                """
                SELECT
                    id,
                    timestamp,
                    symbol,
                    timeframe,
                    close,
                    technical_score,
                    source,
                    source_timestamp,
                    engine_version
                FROM market_data
                WHERE symbol = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (symbol,)
            ).fetchone()

            if row is None:

                print(
                    "{:<6} | NO ROW".format(
                        symbol
                    )
                )

                continue

            print(
                "{:<6} | ID={} | TIMEFRAME={} | "
                "CLOSE={} | SCORE={} | SOURCE={}".format(
                    symbol,
                    row["id"],
                    row["timeframe"],
                    row["close"],
                    row["technical_score"],
                    row["source"]
                )
            )

    finally:

        conn.close()


# ============================================================
# WRITE SAFETY
# ============================================================

def report_write_safety():

    section(
        "STEP 6 — WRITE SAFETY"
    )

    print(
        "PRODUCTION EXECUTION       : NONE"
    )

    print(
        "PRODUCTION main()          : NOT CALLED"
    )

    print(
        "PRODUCTION FUNCTIONS       : NOT EXECUTED"
    )

    print(
        "DATABASE CONNECTION        : READ ONLY"
    )

    print(
        "INSERT                     : NONE"
    )

    print(
        "UPDATE                     : NONE"
    )

    print(
        "DELETE                     : NONE"
    )

    print(
        "ALTER                      : NONE"
    )

    print(
        "CREATE                     : NONE"
    )

    print(
        "DROP                       : NONE"
    )

    print(
        "PRODUCTION DB WRITE        : BLOCKED"
    )

    print(
        "STATIC WRITE-LIKE REFS    : "
        + str(len(write_like_references))
    )

    if write_like_references:

        print()

        print(
            "IMPORTANT:"
        )

        print(
            "Write-like source references "
            "were detected statically."
        )

        print(
            "They were NOT executed."
        )


# ============================================================
# FRONTIER DETERMINATION
# ============================================================

def determine_frontier():

    section(
        "STEP 7 — CURRENT FRONTIER DETERMINATION"
    )

    if not function_consumers:

        status = (
            "DOWNSTREAM_CONSUMER_NOT_IDENTIFIED"
        )

        meaning = (
            "No Python function containing a "
            "market_data reference was identified "
            "by the current static source scan."
        )

        next_frontier = (
            "Expand discovery to indirect database "
            "access, dynamic SQL, imported helpers, "
            "or non-Python consumers."
        )

    elif not sql_consumers:

        status = (
            "DOWNSTREAM_FUNCTION_FOUND_SQL_PATH_UNRESOLVED"
        )

        meaning = (
            "A downstream function references "
            "market_data, but a direct SQL consumer "
            "was not identified."
        )

        next_frontier = (
            "Trace the identified function's exact "
            "database access path."
        )

    else:

        status = (
            "DOWNSTREAM_CONSUMER_CANDIDATES_IDENTIFIED"
        )

        meaning = (
            "Real source-level downstream consumers "
            "of market_data were identified. "
            "Production consumers were not executed."
        )

        next_frontier = (
            "Select the actual production consumer "
            "entrypoint and build a dedicated "
            "READ-ONLY runtime consumption trace."
        )

    print(
        "STATUS       : "
        + status
    )

    print()

    print(
        "MEANING      : "
        + meaning
    )

    print()

    print(
        "NEXT FRONTIER: "
        + next_frontier
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

def final_summary():

    section(
        "STEP 8 — FINAL FORENSIC SUMMARY"
    )

    print(
        "PYTHON FILES SCANNED         : "
        + str(len(python_files))
    )

    print(
        "FILES PARSED                 : "
        + str(len(parsed_files))
    )

    print(
        "PARSE ERRORS                 : "
        + str(len(parse_errors))
    )

    print(
        "market_data SQL REFERENCES   : "
        + str(len(sql_consumers))
    )

    print(
        "DOWNSTREAM FUNCTIONS         : "
        + str(len(function_consumers))
    )

    print(
        "DOWNSTREAM CALL SITES        : "
        + str(len(call_sites))
    )

    print(
        "GENERIC market_data REFS     : "
        + str(len(market_data_references))
    )

    print(
        "WRITE-LIKE REFERENCES        : "
        + str(len(write_like_references))
    )

    print(
        "DATABASE TARGET READS        : "
        + str(len(database_reads))
    )

    print(
        "RUNTIME EXECUTION            : "
        + str(production_execution)
    )

    print(
        "PRODUCTION WRITE             : "
        + str(production_write)
    )

    print()

    print(
        "FORENSIC CONCLUSION"
    )

    line("-")

    if function_consumers:

        print(
            "STATUS                        : "
            "DOWNSTREAM_CONSUMER_CANDIDATES_IDENTIFIED"
        )

        print(
            "MEANING                       : "
            "Real source-level downstream consumers "
            "of market_data were identified without "
            "executing production code."
        )

        print(
            "IMPORTANT                     : "
            "No downstream runtime value was fabricated."
        )

        print(
            "IMPORTANT                     : "
            "No production consumer was executed."
        )

        print(
            "NEXT FRONTIER                 : "
            "Perform READ-ONLY runtime tracing "
            "on the actual selected consumer."
        )

    else:

        print(
            "STATUS                        : "
            "DOWNSTREAM_CONSUMER_NOT_IDENTIFIED"
        )

        print(
            "MEANING                       : "
            "No direct downstream consumer was "
            "identified by the current static search."
        )

        print(
            "NEXT FRONTIER                 : "
            "Expand the discovery path."
        )

    print()

    print(
        "IMPORTANT                     : "
        "Previously verified indicator "
        "calculation was not modified."
    )

    print(
        "IMPORTANT                     : "
        "No production formula was modified."
    )

    print(
        "IMPORTANT                     : "
        "No production database write is permitted."
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
        "ARUNDA DOWNSTREAM market_data CONSUMPTION "
        "DISCOVERY FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                         : "
        "READ-ONLY STATIC FORENSICS"
    )

    print(
        "PRODUCTION EXECUTION         : "
        "DISABLED"
    )

    print(
        "DATABASE WRITE               : "
        "BLOCKED"
    )

    print(
        "CURRENT VERIFIED FRONTIER    : "
        "INDICATOR CALCULATION + PERSISTENCE"
    )

    print(
        "CURRENT TARGET FRONTIER      : "
        "DOWNSTREAM market_data CONSUMPTION"
    )

    print(
        "TARGETS                      : "
        "BTC / ETH / SOL / XRP"
    )

    try:

        verify_paths()

        inventory_python_files()

        parse_python_sources()

        analyze_sources()

        report_sql_consumers()

        report_function_consumers()

        report_call_sites()

        report_target_references()

        verify_market_data_database()

        report_write_safety()

        determine_frontier()

        final_summary()

        elapsed = (
            time.perf_counter()
            - started
        )

        print()

        line("=")

        print(
            "ELAPSED SECONDS              : "
            + "{:.3f}".format(elapsed)
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

        print()

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