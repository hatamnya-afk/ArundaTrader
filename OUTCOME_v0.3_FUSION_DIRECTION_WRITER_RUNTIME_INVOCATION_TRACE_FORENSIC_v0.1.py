# ==============================================================================================
# ARUNDA TRADER
# OUTCOME_v0.3 FUSION DIRECTION WRITER RUNTIME INVOCATION TRACE FORENSIC v0.1
#
# PURPOSE:
#   Prove the runtime relationship between:
#
#       fusion_engine.main()
#           ->
#       direction construction
#           ->
#       fusion_signals INSERT
#           ->
#       direction parameter binding
#           ->
#       actual fusion_signals row identity
#
# SAFETY:
#   READ ONLY
#   Production source is NOT modified.
#   Production DB is NOT modified.
#   No production engine execution.
#   No INSERT / UPDATE / DELETE / ALTER / CREATE.
#   No direction reconstruction.
#   No score-based inference.
#   No synthetic data.
#   No interpolation.
#   No forward fill.
#   No back fill.
#
# IMPORTANT:
#   This forensic script statically reconstructs the runtime boundary from
#   production source code and correlates it against existing DB rows.
#
# ==============================================================================================

from __future__ import annotations

import ast
import hashlib
import re
import sqlite3
from pathlib import Path
from collections import defaultdict


# ==============================================================================================
# CONFIGURATION
# ==============================================================================================

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "arunda.db"

FUSION_ENGINE = PROJECT_ROOT / "fusion_engine.py"
OUTCOME_ENGINE = PROJECT_ROOT / "signal_outcome_engine.py"

EXPECTED_OUTCOME_VERSION = "OUTCOME_v0.3.2"

VALID_DIRECTIONS = {"LONG", "SHORT", "FLAT"}


# ==============================================================================================
# OUTPUT HELPERS
# ==============================================================================================

def print_rule(char="=", width=110):
    print(char * width)


def print_section(title):
    print()
    print_rule("=")
    print(title)
    print_rule("=")


def print_subheader(title):
    print()
    print_rule("-")
    print(title)
    print_rule("-")


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


# ==============================================================================================
# AST UTILITIES
# ==============================================================================================

def node_line(node):
    return getattr(node, "lineno", None)


def node_end_line(node):
    return getattr(node, "end_lineno", node_line(node))


def get_source_segment(source, node):
    try:
        return ast.get_source_segment(source, node) or ""
    except Exception:
        return ""


def function_name_for_node(tree, target_lineno):
    result = None

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            start = node.lineno
            end = node.end_lineno or node.lineno

            if start <= target_lineno <= end:
                result = node.name

    return result


def parent_function_map(tree):
    mapping = {}

    def visit(node, current_function=None):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            current_function = node.name

        for child in ast.iter_child_nodes(node):
            if hasattr(child, "lineno"):
                mapping[id(child)] = current_function

            visit(child, current_function)

    visit(tree)
    return mapping


# ==============================================================================================
# DATABASE SAFETY
# ==============================================================================================

def assert_read_only_connection(conn):
    """
    This connection is opened in SQLite read-only URI mode.
    """

    conn.execute("PRAGMA query_only = ON")

    value = conn.execute("PRAGMA query_only").fetchone()[0]

    if value != 1:
        raise RuntimeError(
            "SAFETY FAILURE: SQLite query_only could not be enabled."
        )


def open_read_only_db():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    assert_read_only_connection(conn)

    return conn


# ==============================================================================================
# DATABASE STRUCTURE
# ==============================================================================================

def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def table_columns(conn, table_name):
    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row["name"] for row in rows]


def database_structure_check(conn):
    print_section("DATABASE STRUCTURE CHECK")

    required = [
        "fusion_signals",
        "signal_outcomes",
    ]

    for table in required:
        status = "FOUND" if table_exists(conn, table) else "MISSING"
        print(f"{table:<30} | {status}")


# ==============================================================================================
# CURRENT FUSION POPULATION
# ==============================================================================================

def current_fusion_population(conn):
    print_section("CURRENT FUSION SIGNAL POPULATION")

    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            COUNT(DISTINCT id) AS distinct_ids,
            SUM(
                CASE
                    WHEN direction IN ('LONG', 'SHORT', 'FLAT')
                    THEN 1
                    ELSE 0
                END
            ) AS valid_direction,
            SUM(
                CASE
                    WHEN direction IS NULL
                    THEN 1
                    ELSE 0
                END
            ) AS null_direction
        FROM fusion_signals
        """
    ).fetchone()

    print(f"Total fusion_signals rows : {row['total']}")
    print(f"Distinct signal IDs       : {row['distinct_ids']}")
    print(f"Valid direction rows      : {row['valid_direction']}")
    print(f"NULL direction rows       : {row['null_direction']}")

    print()
    print("Direction distribution:")

    rows = conn.execute(
        """
        SELECT
            direction,
            COUNT(*) AS count
        FROM fusion_signals
        GROUP BY direction
        ORDER BY
            CASE
                WHEN direction IS NULL THEN 0
                ELSE 1
            END,
            direction
        """
    ).fetchall()

    for row in rows:
        print(
            f"  {str(row['direction']):<12} | {row['count']}"
        )


# ==============================================================================================
# NULL ROW IDENTITIES
# ==============================================================================================

def get_null_direction_rows(conn):
    return conn.execute(
        """
        SELECT
            id,
            timestamp,
            asset,
            fused_score,
            confidence,
            regime,
            snapshot_id,
            engine_version,
            entry_price,
            direction
        FROM fusion_signals
        WHERE direction IS NULL
        ORDER BY id ASC
        """
    ).fetchall()


def print_null_direction_rows(conn):
    rows = get_null_direction_rows(conn)

    print_section("NULL DIRECTION ROW IDENTITIES")

    print(f"NULL direction rows : {len(rows)}")
    print()

    for row in rows:
        print(
            f"Signal #{row['id']:<5} | "
            f"{str(row['asset']):<8} | "
            f"timestamp={row['timestamp']} | "
            f"fused_score={row['fused_score']} | "
            f"engine={row['engine_version']} | "
            f"snapshot={row['snapshot_id']}"
        )


# ==============================================================================================
# SOURCE PARSING
# ==============================================================================================

def parse_source(path):
    source = safe_read(path)

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise RuntimeError(
            f"Could not parse {path}: {exc}"
        )

    return source, tree


# ==============================================================================================
# INSERT DISCOVERY
# ==============================================================================================

def discover_fusion_inserts(source, tree):
    results = []
    function_map = parent_function_map(tree)

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Attribute):
            continue

        if node.func.attr not in {
            "execute",
            "executemany",
        }:
            continue

        if not node.args:
            continue

        sql = get_source_segment(source, node.args[0])

        normalized = re.sub(
            r"\s+",
            " ",
            sql,
        ).strip()

        if re.search(
            r"\bINSERT\s+INTO\s+fusion_signals\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            results.append(
                {
                    "line": node.lineno,
                    "end_line": node.end_lineno,
                    "function": function_map.get(id(node)),
                    "sql": normalized,
                    "node": node,
                }
            )

    return results


# ==============================================================================================
# DIRECTION REFERENCES
# ==============================================================================================

def discover_direction_references(source, tree):
    results = []
    function_map = parent_function_map(tree)

    for node in ast.walk(tree):

        if not isinstance(node, ast.Name):
            continue

        if node.id != "direction":
            continue

        results.append(
            {
                "line": node.lineno,
                "column": node.col_offset,
                "context": type(node.ctx).__name__,
                "function": function_map.get(id(node)),
            }
        )

    return results


# ==============================================================================================
# DETERMINE_DIRECTION DISCOVERY
# ==============================================================================================

def discover_determine_direction(source, tree):
    results = []
    function_map = parent_function_map(tree)

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            if node.name == "determine_direction":

                results.append(
                    {
                        "line": node.lineno,
                        "end_line": node.end_lineno,
                        "function": node.name,
                        "source": get_source_segment(
                            source,
                            node,
                        ),
                    }
                )

        elif isinstance(node, ast.Call):

            if isinstance(node.func, ast.Name):
                if node.func.id == "determine_direction":

                    results.append(
                        {
                            "line": node.lineno,
                            "end_line": node.end_lineno,
                            "function": function_map.get(
                                id(node)
                            ),
                            "call": True,
                            "source": get_source_segment(
                                source,
                                node,
                            ),
                        }
                    )

    return results


# ==============================================================================================
# INSERT COLUMN / VALUE ANALYSIS
# ==============================================================================================

def extract_insert_column_value_mapping(source, insert):
    """
    Best-effort static reconstruction of:
        INSERT INTO fusion_signals (columns...)
        VALUES (...)
    """

    sql = insert["sql"]

    pattern = re.compile(
        r"""
        INSERT\s+INTO\s+fusion_signals
        \s*
        \(
            (?P<columns>.*?)
        \)
        \s*
        VALUES
        \s*
        \(
            (?P<values>.*?)
        \)
        """,
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    )

    match = pattern.search(sql)

    if not match:
        return None

    columns_raw = match.group("columns")
    values_raw = match.group("values")

    columns = [
        item.strip().strip('"').strip("'").strip("`")
        for item in columns_raw.split(",")
    ]

    values = [
        item.strip()
        for item in values_raw.split(",")
    ]

    mapping = []

    for index, column in enumerate(columns):

        value = (
            values[index]
            if index < len(values)
            else "<MISSING>"
        )

        mapping.append(
            (
                column,
                value,
            )
        )

    return mapping


# ==============================================================================================
# SOURCE CONTEXT
# ==============================================================================================

def source_context(source, start_line, end_line, radius=8):
    lines = source.splitlines()

    start = max(
        1,
        start_line - radius,
    )

    end = min(
        len(lines),
        end_line + radius,
    )

    result = []

    for line_no in range(start, end + 1):

        marker = ">>" if (
            start_line <= line_no <= end_line
        ) else "  "

        result.append(
            f"{marker} {line_no:5d} | {lines[line_no - 1]}"
        )

    return result


# ==============================================================================================
# WRITER STATIC BOUNDARY
# ==============================================================================================

def writer_static_boundary(source, tree):
    print_section(
        "STATIC RUNTIME WRITER BOUNDARY RECONSTRUCTION"
    )

    inserts = discover_fusion_inserts(
        source,
        tree,
    )

    directions = discover_direction_references(
        source,
        tree,
    )

    determine = discover_determine_direction(
        source,
        tree,
    )

    print(
        f"fusion_signals INSERT statements : {len(inserts)}"
    )

    print(
        f"direction references              : {len(directions)}"
    )

    print(
        f"determine_direction references    : {len(determine)}"
    )

    if not inserts:
        print(
            "\nNO direct fusion_signals INSERT "
            "was statically identified."
        )

        return inserts

    for index, insert in enumerate(inserts, 1):

        print_subheader(
            f"FUSION INSERT [{index}]"
        )

        print(
            f"Line      : {insert['line']}"
        )

        print(
            f"Function  : {insert['function']}"
        )

        mapping = extract_insert_column_value_mapping(
            source,
            insert,
        )

        if mapping:

            print()
            print(
                "INSERT COLUMN -> VALUE MAPPING"
            )

            for column, value in mapping:

                if column.lower() == "direction":

                    print(
                        f"  >>> {column:<20} = {value}"
                    )

                else:

                    print(
                        f"      {column:<20} = {value}"
                    )

        print()
        print("SOURCE CONTEXT")

        for line in source_context(
            source,
            insert["line"],
            insert["end_line"],
            radius=10,
        ):
            print(line)

    print_subheader(
        "determine_direction REFERENCES"
    )

    for item in determine:

        print(
            f"Line={item['line']} | "
            f"Function={item.get('function')} | "
            f"Definition={not item.get('call', False)}"
        )

        if item.get("source"):
            compact = re.sub(
                r"\s+",
                " ",
                item["source"],
            )

            print(
                f"  {compact[:500]}"
            )


    print_subheader(
        "direction REFERENCES NEAR FUSION INSERT"
    )

    insert_lines = {
        insert["line"]
        for insert in inserts
    }

    nearby = [
        item
        for item in directions
        if any(
            abs(item["line"] - line) <= 60
            for line in insert_lines
        )
    ]

    for item in nearby:

        print(
            f"Line={item['line']} | "
            f"Context={item['context']} | "
            f"Function={item['function']}"
        )

    return inserts


# ==============================================================================================
# RUNTIME TRACE MODEL
# ==============================================================================================

def build_runtime_trace_model(source, tree, inserts):
    """
    This does NOT execute production code.

    It constructs a conservative static runtime graph.
    """

    print_section(
        "RUNTIME INVOCATION TRACE MODEL"
    )

    print(
        "Production execution : NOT PERFORMED"
    )

    print(
        "Trace method          : READ-ONLY STATIC RUNTIME MODEL"
    )

    print()

    main_functions = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            if node.name == "main":
                main_functions.append(node)

    if not main_functions:

        print(
            "main() function : NOT FOUND"
        )

    else:

        for node in main_functions:

            print(
                f"main()           : FOUND at line {node.lineno}"
            )

            if inserts:

                same_function_insert = [
                    item
                    for item in inserts
                    if item["function"] == "main"
                ]

                print(
                    "INSERT in main() : "
                    f"{len(same_function_insert)}"
                )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This model does not claim that main() was "
        "executed during this forensic run."
    )

    print(
        "It only establishes whether the source-level "
        "runtime path can connect direction construction "
        "to the fusion_signals INSERT."
    )


# ==============================================================================================
# AST DATAFLOW ANALYSIS
# ==============================================================================================

def assignment_summary(tree):
    assignments = []

    function_map = parent_function_map(tree)

    for node in ast.walk(tree):

        if isinstance(node, ast.Assign):

            target_names = []

            for target in node.targets:

                if isinstance(target, ast.Name):
                    target_names.append(
                        target.id
                    )

            if "direction" in target_names:

                assignments.append(
                    {
                        "line": node.lineno,
                        "function": function_map.get(
                            id(node)
                        ),
                        "source": get_source_segment(
                            source_global,
                            node,
                        ),
                    }
                )

    return assignments


source_global = ""


def direction_assignment_trace(source, tree):
    global source_global

    source_global = source

    print_section(
        "DIRECTION VALUE CONSTRUCTION TRACE"
    )

    assignments = assignment_summary(tree)

    if not assignments:

        print(
            "No direct assignment to local "
            "variable 'direction' found."
        )

        return

    print(
        f"Direct direction assignments : {len(assignments)}"
    )

    for item in assignments:

        print()
        print(
            f"Line={item['line']} | "
            f"Function={item['function']}"
        )

        print(
            f"  {item['source']}"
        )


# ==============================================================================================
# INSERT BINDING ANALYSIS
# ==============================================================================================

def direction_binding_analysis(source, inserts):
    print_section(
        "DIRECTION INSERT PARAMETER BINDING ANALYSIS"
    )

    for index, insert in enumerate(inserts, 1):

        print_subheader(
            f"INSERT [{index}]"
        )

        mapping = extract_insert_column_value_mapping(
            source,
            insert,
        )

        if not mapping:

            print(
                "Could not reconstruct INSERT mapping."
            )

            continue

        direction_mapping = [
            pair
            for pair in mapping
            if pair[0].lower() == "direction"
        ]

        if not direction_mapping:

            print(
                "direction column : NOT FOUND"
            )

            continue

        for column, value in direction_mapping:

            print(
                f"direction column : {column}"
            )

            print(
                f"bound expression : {value}"
            )

            normalized = value.lower()

            if normalized in {
                "?",
                ":direction",
                "direction",
            } or "direction" in normalized:

                print(
                    "Binding status   : "
                    "DIRECTION VARIABLE / PARAMETER RELATED"
                )

            elif normalized in {
                "null",
                "none",
            }:

                print(
                    "Binding status   : "
                    "EXPLICIT NULL-LIKE VALUE"
                )

            else:

                print(
                    "Binding status   : "
                    "NON-DIRECT / REQUIRES MANUAL TRACE"
                )


# ==============================================================================================
# ACTUAL ROW CORRELATION
# ==============================================================================================

def correlate_null_rows(conn):
    print_section(
        "ACTUAL DATABASE ROW CORRELATION"
    )

    rows = get_null_direction_rows(conn)

    print(
        "This section uses existing production DB rows "
        "ONLY for identity correlation."
    )

    print()

    by_engine = defaultdict(list)
    by_snapshot = defaultdict(list)

    for row in rows:

        by_engine[
            row["engine_version"]
        ].append(row)

        by_snapshot[
            row["snapshot_id"]
        ].append(row)

    print("NULL direction rows by engine_version:")

    for engine, items in sorted(
        by_engine.items(),
        key=lambda x: str(x[0]),
    ):

        print(
            f"  {str(engine):<35} | {len(items)}"
        )

    print()

    print("NULL direction rows by snapshot_id:")

    for snapshot, items in sorted(
        by_snapshot.items(),
        key=lambda x: str(x[0]),
    ):

        print(
            f"  {str(snapshot):<40} | {len(items)}"
        )


# ==============================================================================================
# TEMPORAL GROUPING
# ==============================================================================================

def temporal_writer_pattern(conn):
    print_section(
        "NULL DIRECTION TEMPORAL WRITER PATTERN"
    )

    rows = conn.execute(
        """
        SELECT
            timestamp,
            COUNT(*) AS rows_count,
            SUM(
                CASE
                    WHEN direction IS NULL THEN 1
                    ELSE 0
                END
            ) AS null_count,
            SUM(
                CASE
                    WHEN direction IN ('LONG','SHORT','FLAT')
                    THEN 1
                    ELSE 0
                END
            ) AS valid_count
        FROM fusion_signals
        GROUP BY timestamp
        ORDER BY timestamp ASC
        """
    ).fetchall()

    for row in rows:

        print(
            f"{row['timestamp']} | "
            f"rows={row['rows_count']:<3} | "
            f"valid={row['valid_count']:<3} | "
            f"NULL={row['null_count']:<3}"
        )


# ==============================================================================================
# PRODUCTION FINGERPRINT
# ==============================================================================================

def production_fingerprint():
    print_section(
        "PRODUCTION SOURCE FINGERPRINT"
    )

    for path in [
        FUSION_ENGINE,
        OUTCOME_ENGINE,
    ]:

        if path.exists():

            print(
                f"{path.name:<35} | "
                f"SHA256={sha256_file(path)}"
            )

        else:

            print(
                f"{path.name:<35} | MISSING"
            )


# ==============================================================================================
# SAFETY CHECK
# ==============================================================================================

def source_write_scan(source):
    forbidden = [
        r"\bINSERT\s+INTO",
        r"\bUPDATE\b",
        r"\bDELETE\s+FROM",
        r"\bALTER\s+TABLE",
        r"\bCREATE\s+TABLE",
        r"\bDROP\s+TABLE",
    ]

    results = []

    for pattern in forbidden:

        if re.search(
            pattern,
            source,
            flags=re.IGNORECASE,
        ):
            results.append(pattern)

    return results


def forensic_self_safety_check():
    print_section(
        "FORENSIC SCRIPT SAFETY CHECK"
    )

    current_source = safe_read(
        Path(__file__)
    )

    write_patterns = source_write_scan(
        current_source
    )

    print(
        "Production DB connection : READ ONLY"
    )

    print(
        "Production engine run    : NO"
    )

    print(
        "Production source write  : NO"
    )

    print(
        "Direction reconstruction : NO"
    )

    print(
        "Synthetic data            : NO"
    )

    print(
        "Interpolation             : NO"
    )

    print(
        "Forward fill              : NO"
    )

    print(
        "Back fill                 : NO"
    )

    print()

    if write_patterns:

        print(
            "NOTE:"
        )

        print(
            "SQL-like write keywords "
            "may appear in source-analysis strings."
        )

        print(
            "They are NOT executed."
        )


# ==============================================================================================
# FINAL VERDICT
# ==============================================================================================

def final_verdict(
    inserts,
    conn,
):
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN direction IS NULL THEN 1
                    ELSE 0
                END
            ) AS null_count,
            SUM(
                CASE
                    WHEN direction IN ('LONG','SHORT','FLAT')
                    THEN 1
                    ELSE 0
                END
            ) AS valid_count
        FROM fusion_signals
        """
    ).fetchone()

    print_section(
        "FINAL SAFETY VERDICT"
    )

    print(
        "Database writes       : NONE"
    )

    print(
        "INSERT                : NONE EXECUTED"
    )

    print(
        "UPDATE                : NONE EXECUTED"
    )

    print(
        "DELETE                : NONE EXECUTED"
    )

    print(
        "ALTER                 : NONE EXECUTED"
    )

    print(
        "CREATE                : NONE EXECUTED"
    )

    print(
        "Production DB         : UNMODIFIED"
    )

    print(
        "Production source     : UNMODIFIED"
    )

    print(
        "Direction inferred    : NO"
    )

    print(
        "Direction repaired    : NO"
    )

    print(
        "Tolerance modified    : NO"
    )

    print(
        "Synthetic data        : NOT USED"
    )

    print(
        "Interpolation         : NOT USED"
    )

    print(
        "Forward fill          : NOT USED"
    )

    print(
        "Back fill             : NOT USED"
    )

    print()

    print_rule("=")

    print(
        "FORENSIC CONCLUSION"
    )

    print_rule("=")

    print(
        f"Current fusion rows       : {row['total']}"
    )

    print(
        f"Valid directional rows    : {row['valid_count']}"
    )

    print(
        f"NULL directional rows     : {row['null_count']}"
    )

    print(
        f"Direct INSERT boundaries  : {len(inserts)}"
    )

    print()

    if inserts:

        print(
            "STATIC INSERT BOUNDARY:"
        )

        for item in inserts:

            print(
                f"  fusion_signals INSERT "
                f"at line {item['line']} "
                f"in function {item['function']}"
            )

    print()

    print(
        "RUNTIME PROOF STATUS:"
    )

    print(
        "  Production execution of fusion_engine.py : NOT PERFORMED"
    )

    print(
        "  Runtime invocation observed              : NOT CLAIMED"
    )

    print(
        "  Actual INSERT parameter value observed   : NOT CLAIMED"
    )

    print(
        "  Actual NULL row causal identity          : NOT CLAIMED"
    )

    print()

    print(
        "NEXT ACTION:"
    )

    print(
        "Perform an isolated runtime instrumentation "
        "trace of the production writer boundary."
    )

    print()

    print(
        "Required chain:"
    )

    print(
        "    fusion_engine.main()"
    )

    print(
        "        -> determine_direction()"
    )

    print(
        "        -> direction value"
    )

    print(
        "        -> INSERT parameter binding"
    )

    print(
        "        -> generated signal identity"
    )

    print(
        "        -> fusion_signals row"
    )

    print(
        "        -> NULL direction identity"
    )

    print()

    print(
        "NO eligibility repair is authorized."
    )

    print(
        "NO direction reconstruction is authorized."
    )

    print(
        "NO score-based direction inference is authorized."
    )

    print()

    print(
        "FORENSIC COMPLETE."
    )

    print_rule("=")


# ==============================================================================================
# MAIN
# ==============================================================================================

def main():

    print_rule("=")

    print(
        "OUTCOME_v0.3 FUSION DIRECTION WRITER "
        "RUNTIME INVOCATION TRACE FORENSIC v0.1"
    )

    print_rule("=")

    print(
        f"Database          : {DB_PATH.name}"
    )

    print(
        f"Project root      : {PROJECT_ROOT}"
    )

    print(
        f"Writer target     : {FUSION_ENGINE.name}"
    )

    print(
        "Target table      : fusion_signals"
    )

    print(
        "Target column     : direction"
    )

    print(
        "Mode              : READ ONLY"
    )

    print(
        "Production DB     : UNMODIFIED"
    )

    print(
        "Production source : UNMODIFIED"
    )

    print(
        "Synthetic data    : FORBIDDEN"
    )

    print(
        "Interpolation     : FORBIDDEN"
    )

    print(
        "Forward fill      : FORBIDDEN"
    )

    print(
        "Back fill         : FORBIDDEN"
    )

    print()

    forensic_self_safety_check()

    if not FUSION_ENGINE.exists():

        raise FileNotFoundError(
            f"Production writer not found: {FUSION_ENGINE}"
        )

    source, tree = parse_source(
        FUSION_ENGINE
    )

    conn = open_read_only_db()

    try:

        database_structure_check(
            conn
        )

        current_fusion_population(
            conn
        )

        print_null_direction_rows(
            conn
        )

        inserts = writer_static_boundary(
            source,
            tree
        )

        build_runtime_trace_model(
            source,
            tree,
            inserts
        )

        direction_assignment_trace(
            source,
            tree
        )

        direction_binding_analysis(
            source,
            inserts
        )

        correlate_null_rows(
            conn
        )

        temporal_writer_pattern(
            conn
        )

        production_fingerprint()

        final_verdict(
            inserts,
            conn
        )

    finally:

        conn.close()


# ==============================================================================================
# ENTRY POINT
# ==============================================================================================

if __name__ == "__main__":
    main()