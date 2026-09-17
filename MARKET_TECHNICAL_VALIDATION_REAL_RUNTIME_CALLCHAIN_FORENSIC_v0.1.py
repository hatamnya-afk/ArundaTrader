import ast
import hashlib
import re
import sqlite3
from pathlib import Path


# =============================================================================
# ARUNDA TRADER
# MARKET_TECHNICAL_VALIDATION_REAL_RUNTIME_CALLCHAIN_FORENSIC v0.1
# =============================================================================
#
# MODE:
#   READ ONLY
#
# PURPOSE:
#   Resolve the REAL runtime call chain responsible for technical validation
#   fields persisted in market_technical.
#
# GUARANTEES:
#   - No INSERT
#   - No UPDATE
#   - No DELETE
#   - No ALTER
#   - No CREATE
#   - No DROP
#   - No production source modification
#   - No DB mutation
#   - No synthetic data
#   - No interpolation
#   - No forward fill
#   - No back fill
#
# SPECIAL:
#   Production files containing UTF-8 BOM / U+FEFF are read using
#   utf-8-sig ONLY for forensic parsing.
#
# =============================================================================


PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "arunda.db"

TARGET_TABLE = "market_technical"

VALIDATION_FIELDS = {
    "technical_available",
    "available",
    "technical_validation_score",
    "technical_validation_status",
    "technical_validation_flags",
    "technical_validation_version",
    "technical_validated_at",
    "technical_completeness",
    "technical_version",
}

VALIDATION_TOKENS = (
    "technical_validation",
    "technical_available",
    "technical_completeness",
    "validation_status",
    "validation_score",
    "validation_flags",
    "validated_at",
)

WRITE_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|ALTER|CREATE|DROP|REPLACE)\b",
    re.IGNORECASE,
)

TECHNICAL_TABLE_RE = re.compile(
    r"\bmarket_technical\b",
    re.IGNORECASE,
)


# =============================================================================
# BASIC UTILS
# =============================================================================

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def safe(value):
    if value is None:
        return "NULL"
    return str(value)


def print_kv(key, value):
    print(f"{key:<42}: {value}")


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def read_source(path):
    """
    READ ONLY.

    utf-8-sig removes a possible UTF-8 BOM from the in-memory string only.
    The actual file is never rewritten.
    """
    return path.read_text(
        encoding="utf-8-sig",
        errors="strict",
    )


def connect_read_only():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA query_only = ON")

    return conn


def verify_read_only(conn):
    row = conn.execute(
        "PRAGMA query_only"
    ).fetchone()

    if row is None or int(row[0]) != 1:
        raise RuntimeError(
            "READ-ONLY CONTRACT FAILED"
        )


# =============================================================================
# DATABASE FORENSIC
# =============================================================================

def database_forensic(conn):
    banner("DATABASE READ-ONLY FORENSIC")

    print_kv("Database", str(DB_PATH))
    print_kv("Target Table", TARGET_TABLE)

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        """,
        (TARGET_TABLE,),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            f"Required table not found: {TARGET_TABLE}"
        )

    print_kv("Target Table Exists", "YES")

    total = conn.execute(
        f'SELECT COUNT(*) FROM "{TARGET_TABLE}"'
    ).fetchone()[0]

    print_kv("Target Rows", total)

    q = conn.execute(
        "PRAGMA query_only"
    ).fetchone()[0]

    print_kv("SQLite query_only", q)

    if int(q) != 1:
        raise RuntimeError(
            "SQLite query_only is not enabled"
        )


# =============================================================================
# SCHEMA
# =============================================================================

def get_columns(conn):
    rows = conn.execute(
        f'PRAGMA table_info("{TARGET_TABLE}")'
    ).fetchall()

    columns = [row["name"] for row in rows]

    banner("MARKET_TECHNICAL SCHEMA")

    for i, column in enumerate(rows, 1):
        print(
            f"{i:03d}. "
            f"{column['name']:<36} "
            f"type={column['type']:<15} "
            f"notnull={column['notnull']} "
            f"pk={column['pk']}"
        )

    return columns


# =============================================================================
# PERSISTED VALIDATION STATE
# =============================================================================

def persisted_validation_state(conn, columns):
    banner("PERSISTED VALIDATION STATE")

    total = conn.execute(
        f'SELECT COUNT(*) FROM "{TARGET_TABLE}"'
    ).fetchone()[0]

    print_kv("Total Rows", total)

    for field in sorted(VALIDATION_FIELDS):
        if field not in columns:
            print_kv(field, "NOT PRESENT")
            continue

        row = conn.execute(
            f'''
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN "{field}" IS NOT NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS nonnull
            FROM "{TARGET_TABLE}"
            '''
        ).fetchone()

        nonnull = row["nonnull"] or 0

        print(
            f"{field:<42}: "
            f"nonnull={nonnull:<8} "
            f"null={total - nonnull:<8}"
        )


# =============================================================================
# SOURCE INVENTORY
# =============================================================================

def source_inventory():
    banner("PRODUCTION SOURCE INVENTORY")

    files = sorted(
        PROJECT_DIR.glob("*.py"),
        key=lambda p: p.name.lower(),
    )

    print_kv("Python Files", len(files))

    return files


# =============================================================================
# SOURCE FILE ANALYSIS
# =============================================================================

def analyze_source_file(path):
    result = {
        "path": path,
        "sha256": None,
        "bom": False,
        "parse_ok": False,
        "parse_error": None,
        "validation_hits": [],
        "functions": [],
        "classes": [],
        "writes": [],
        "technical_writes": [],
        "calls": [],
        "assignments": [],
    }

    try:
        raw = path.read_bytes()
        result["bom"] = raw.startswith(b"\xef\xbb\xbf")
        result["sha256"] = hashlib.sha256(raw).hexdigest()
    except Exception as exc:
        result["parse_error"] = (
            f"binary read failed: {exc}"
        )
        return result

    try:
        text = read_source(path)
    except Exception as exc:
        result["parse_error"] = (
            f"text read failed: {exc}"
        )
        return result

    lines = text.splitlines()

    # -------------------------------------------------------------------------
    # Keyword discovery
    # -------------------------------------------------------------------------

    for line_no, line in enumerate(lines, 1):
        lower = line.lower()

        hits = [
            token
            for token in VALIDATION_TOKENS
            if token.lower() in lower
        ]

        if hits:
            result["validation_hits"].append(
                (line_no, line.rstrip(), sorted(set(hits)))
            )

        if WRITE_SQL.search(line):
            result["writes"].append(
                (line_no, line.rstrip())
            )

            if TECHNICAL_TABLE_RE.search(line):
                result["technical_writes"].append(
                    (line_no, line.rstrip())
                )

    # -------------------------------------------------------------------------
    # AST
    # -------------------------------------------------------------------------

    try:
        tree = ast.parse(
            text,
            filename=str(path),
        )

        result["parse_ok"] = True

    except SyntaxError as exc:
        result["parse_error"] = (
            f"SyntaxError: {exc.msg} "
            f"(line {exc.lineno}, offset {exc.offset})"
        )
        return result

    except Exception as exc:
        result["parse_error"] = (
            f"{type(exc).__name__}: {exc}"
        )
        return result

    # -------------------------------------------------------------------------
    # Functions / classes
    # -------------------------------------------------------------------------

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            result["functions"].append(
                (
                    node.name,
                    node.lineno,
                    node.end_lineno,
                )
            )

        elif isinstance(node, ast.ClassDef):
            result["classes"].append(
                (
                    node.name,
                    node.lineno,
                    node.end_lineno,
                )
            )

    # -------------------------------------------------------------------------
    # Function calls
    # -------------------------------------------------------------------------

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            name = None

            if isinstance(node.func, ast.Name):
                name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            if name:
                if (
                    "valid" in name.lower()
                    or "technical" in name.lower()
                    or "quality" in name.lower()
                    or "indicator" in name.lower()
                    or "feature" in name.lower()
                ):
                    result["calls"].append(
                        (
                            name,
                            node.lineno,
                        )
                    )

    # -------------------------------------------------------------------------
    # Validation assignments
    # -------------------------------------------------------------------------

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign,
            ),
        ):
            try:
                source_segment = ast.get_source_segment(
                    text,
                    node,
                )
            except Exception:
                source_segment = None

            if source_segment:
                lower = source_segment.lower()

                if any(
                    token.lower() in lower
                    for token in VALIDATION_TOKENS
                ):
                    result["assignments"].append(
                        (
                            node.lineno,
                            source_segment.strip(),
                        )
                    )

    return result


# =============================================================================
# PRODUCER CANDIDATE RANKING
# =============================================================================

def rank_candidates(results):
    banner("VALIDATION PRODUCER CANDIDATE RANKING")

    scored = []

    for result in results:

        score = 0

        if result["validation_hits"]:
            score += min(
                len(result["validation_hits"]),
                20,
            )

        if result["assignments"]:
            score += 20

        if result["technical_writes"]:
            score += 30

        if result["calls"]:
            score += min(
                len(result["calls"]) * 2,
                20,
            )

        if result["parse_ok"]:
            score += 5

        if result["bom"]:
            score += 0

        if score:
            scored.append(
                (
                    score,
                    result,
                )
            )

    scored.sort(
        key=lambda x: (
            -x[0],
            x[1]["path"].name.lower(),
        )
    )

    print(
        f"{'SCORE':<8}"
        f"{'FILE':<65}"
        f"{'PARSE':<10}"
        f"{'BOM':<8}"
        f"{'VAL HITS':<10}"
        f"{'ASSIGN':<10}"
        f"{'TECH WRITE':<12}"
    )

    print("-" * 125)

    for score, result in scored:
        print(
            f"{score:<8}"
            f"{result['path'].name[:64]:<65}"
            f"{'YES' if result['parse_ok'] else 'NO':<10}"
            f"{'YES' if result['bom'] else 'NO':<8}"
            f"{len(result['validation_hits']):<10}"
            f"{len(result['assignments']):<10}"
            f"{len(result['technical_writes']):<12}"
        )

    return scored


# =============================================================================
# DETAILED CANDIDATE FORENSIC
# =============================================================================

def candidate_detail(scored, maximum=12):
    banner("VALIDATION CANDIDATE DETAIL")

    for rank, (score, result) in enumerate(
        scored[:maximum],
        1,
    ):

        path = result["path"]

        print()
        print("=" * 100)
        print(
            f"RANK {rank} | SCORE {score} | "
            f"FILE {path.name}"
        )
        print("=" * 100)

        print_kv("Absolute Path", str(path))
        print_kv("SHA256", result["sha256"])
        print_kv(
            "UTF-8 BOM",
            "YES" if result["bom"] else "NO",
        )
        print_kv(
            "AST Parse",
            "YES" if result["parse_ok"] else "NO",
        )

        if result["parse_error"]:
            print_kv(
                "AST Error",
                result["parse_error"],
            )

        if result["technical_writes"]:
            print()
            print("TECHNICAL TABLE WRITE REFERENCES")

            for line_no, line in result[
                "technical_writes"
            ][:30]:
                print(
                    f"  line={line_no:<6} "
                    f"{line[:180]}"
                )

        if result["assignments"]:
            print()
            print("VALIDATION ASSIGNMENTS")

            for line_no, source in result[
                "assignments"
            ][:40]:
                print()
                print(
                    f"  line={line_no}"
                )
                print(
                    f"    {source[:500]}"
                )

        if result["calls"]:
            print()
            print("VALIDATION / TECHNICAL CALLS")

            seen = set()

            for name, line_no in result[
                "calls"
            ]:

                key = (name, line_no)

                if key in seen:
                    continue

                seen.add(key)

                print(
                    f"  line={line_no:<6} "
                    f"call={name}"
                )

        if result["validation_hits"]:
            print()
            print("VALIDATION SOURCE REFERENCES")

            for line_no, line, hits in result[
                "validation_hits"
            ][:40]:

                print(
                    f"  line={line_no:<6} "
                    f"[{', '.join(hits)}]"
                )
                print(
                    f"    {line[:220]}"
                )


# =============================================================================
# FUNCTION-LEVEL CALL GRAPH
# =============================================================================

def function_level_forensic(scored):
    banner("FUNCTION-LEVEL VALIDATION CALL GRAPH FORENSIC")

    for score, result in scored:

        if not result["parse_ok"]:
            continue

        path = result["path"]

        try:
            text = read_source(path)
            tree = ast.parse(
                text,
                filename=str(path),
            )
        except Exception:
            continue

        lines = text.splitlines()

        relevant_functions = []

        for node in ast.walk(tree):

            if not isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                continue

            segment = "\n".join(
                lines[
                    node.lineno - 1:
                    node.end_lineno
                ]
            ).lower()

            relevance = False

            if any(
                token.lower() in segment
                for token in VALIDATION_TOKENS
            ):
                relevance = True

            if "market_technical" in segment:
                relevance = True

            if any(
                word in node.name.lower()
                for word in (
                    "valid",
                    "technical",
                    "quality",
                    "feature",
                    "indicator",
                )
            ):
                relevance = True

            if relevance:
                relevant_functions.append(node)

        if not relevant_functions:
            continue

        print()
        print("-" * 100)
        print(f"FILE : {path.name}")
        print("-" * 100)

        for node in sorted(
            relevant_functions,
            key=lambda n: n.lineno,
        ):

            print()
            print(
                f"FUNCTION : {node.name}"
            )
            print(
                f"LINES    : "
                f"{node.lineno}-{node.end_lineno}"
            )

            calls = []

            for child in ast.walk(node):

                if isinstance(child, ast.Call):

                    name = None

                    if isinstance(
                        child.func,
                        ast.Name,
                    ):
                        name = child.func.id

                    elif isinstance(
                        child.func,
                        ast.Attribute,
                    ):
                        name = child.func.attr

                    if name:
                        calls.append(
                            (name, child.lineno)
                        )

            if calls:

                unique = []

                seen = set()

                for item in calls:
                    if item not in seen:
                        seen.add(item)
                        unique.append(item)

                for name, line_no in unique:
                    print(
                        f"  CALL "
                        f"line={line_no:<6} "
                        f"{name}"
                    )


# =============================================================================
# WRITE BOUNDARY DETAILS
# =============================================================================

def write_boundary_forensic(scored):
    banner("MARKET_TECHNICAL WRITE-BOUNDARY FORENSIC")

    for score, result in scored:

        if not result["technical_writes"]:
            continue

        path = result["path"]

        print()
        print(f"FILE : {path.name}")

        for line_no, line in result[
            "technical_writes"
        ]:

            print(
                f"  line={line_no:<6} "
                f"{line[:220]}"
            )

        print(
            f"  TOTAL TECHNICAL WRITE REFERENCES : "
            f"{len(result['technical_writes'])}"
        )


# =============================================================================
# DIRECT SQL VALIDATION FIELD WRITE SEARCH
# =============================================================================

def direct_validation_sql_search():
    banner("DIRECT VALIDATION-FIELD SQL WRITE SEARCH")

    found = []

    for path in PROJECT_DIR.glob("*.py"):

        try:
            text = read_source(path)
        except Exception:
            continue

        lines = text.splitlines()

        for line_no, line in enumerate(
            lines,
            1,
        ):

            lower = line.lower()

            if (
                "market_technical" in lower
                and any(
                    field.lower() in lower
                    for field in VALIDATION_FIELDS
                )
            ):
                found.append(
                    (
                        path.name,
                        line_no,
                        line.strip(),
                    )
                )

    if not found:
        print(
            "No direct source-line intersection found."
        )
        return

    for filename, line_no, line in found:
        print()
        print(
            f"FILE={filename} "
            f"LINE={line_no}"
        )
        print(
            f"  {line[:300]}"
        )

    print()
    print_kv(
        "Direct intersections",
        len(found),
    )


# =============================================================================
# DATABASE OBJECTS
# =============================================================================

def database_objects(conn):
    banner("DATABASE TRIGGER / VIEW FORENSIC")

    rows = conn.execute(
        """
        SELECT
            type,
            name,
            sql
        FROM sqlite_master
        WHERE type IN ('trigger', 'view')
        ORDER BY type, name
        """
    ).fetchall()

    if not rows:
        print("No triggers/views found.")
        return

    for row in rows:

        print()
        print(
            f"TYPE : {row['type']}"
        )
        print(
            f"NAME : {row['name']}"
        )
        print(
            f"SQL  : {safe(row['sql'])[:1500]}"
        )


# =============================================================================
# FINAL CONTRACT
# =============================================================================

def final_contract(
    conn,
    results,
    scored,
):
    banner(
        "MARKET_TECHNICAL VALIDATION "
        "REAL RUNTIME CALLCHAIN FORENSIC CONTRACT"
    )

    total = conn.execute(
        f'SELECT COUNT(*) FROM "{TARGET_TABLE}"'
    ).fetchone()[0]

    print_kv(
        "Rows Inspected",
        total,
    )

    print_kv(
        "Python Sources Inspected",
        len(results),
    )

    print_kv(
        "Validation Candidates",
        len(scored),
    )

    parse_errors = sum(
        1
        for result in results
        if result["parse_error"]
    )

    bom_files = sum(
        1
        for result in results
        if result["bom"]
    )

    print_kv(
        "AST Parse Errors",
        parse_errors,
    )

    print_kv(
        "UTF-8 BOM Files",
        bom_files,
    )

    technical_writer_files = sum(
        1
        for result in results
        if result["technical_writes"]
    )

    print_kv(
        "Files Referencing market_technical Writes",
        technical_writer_files,
    )

    print()
    print_kv("READ ONLY", "YES")
    print_kv("SQLite mode", "mode=ro")
    print_kv("query_only", "1")
    print_kv("INSERT", "NONE")
    print_kv("UPDATE", "NONE")
    print_kv("DELETE", "NONE")
    print_kv("ALTER", "NONE")
    print_kv("CREATE", "NONE")
    print_kv("DROP", "NONE")
    print_kv("REPLACE", "NONE")
    print_kv("SOURCE MODIFICATION", "NONE")
    print_kv("SYNTHETIC DATA", "NONE")
    print_kv("INTERPOLATION", "NONE")
    print_kv("FORWARD FILL", "NONE")
    print_kv("BACK FILL", "NONE")

    print()
    print(
        "FORENSIC STATUS : COMPLETE"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This forensic resolves source-level candidates and "
        "function-level runtime relationships only."
    )

    print(
        "It does NOT claim that a source path executed in "
        "production merely because the source contains SQL."
    )

    print(
        "Runtime execution proof requires instrumentation "
        "of the actual production entrypoint; this script "
        "does not modify or execute production business logic."
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA MARKET_TECHNICAL_VALIDATION "
        "REAL_RUNTIME_CALLCHAIN FORENSIC v0.1"
    )

    print_kv(
        "Project",
        str(PROJECT_DIR),
    )

    print_kv(
        "Database",
        str(DB_PATH),
    )

    print_kv(
        "Mode",
        "READ ONLY",
    )

    print_kv(
        "Target",
        TARGET_TABLE,
    )

    conn = None

    try:

        conn = connect_read_only()

        verify_read_only(conn)

        database_forensic(conn)

        columns = get_columns(conn)

        persisted_validation_state(
            conn,
            columns,
        )

        source_inventory()

        results = []

        for path in sorted(
            PROJECT_DIR.glob("*.py"),
            key=lambda p: p.name.lower(),
        ):

            if path.name == Path(__file__).name:
                continue

            result = analyze_source_file(path)

            results.append(result)

        scored = rank_candidates(
            results
        )

        candidate_detail(
            scored,
            maximum=15,
        )

        function_level_forensic(
            scored
        )

        write_boundary_forensic(
            scored
        )

        direct_validation_sql_search()

        database_objects(
            conn
        )

        final_contract(
            conn,
            results,
            scored,
        )

    except Exception as exc:

        banner(
            "FORENSIC ERROR"
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        raise

    finally:

        if conn is not None:
            conn.close()

    print()
    print("=" * 100)
    print(
        "ARUNDA MARKET_TECHNICAL_VALIDATION "
        "REAL_RUNTIME_CALLCHAIN FORENSIC v0.1 COMPLETE"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()