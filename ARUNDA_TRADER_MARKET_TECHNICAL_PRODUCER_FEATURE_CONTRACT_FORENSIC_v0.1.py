import ast
import os
import re
import sqlite3
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "arunda.db")

TARGET_TABLE = "market_technical"

WRITE_PATTERNS = [
    r"\bINSERT\s+(?:OR\s+\w+\s+)?INTO\s+market_technical\b",
    r"\bUPDATE\s+market_technical\b",
    r"\bALTER\s+TABLE\s+market_technical\b",
    r"\bDELETE\s+FROM\s+market_technical\b",
    r"\bREPLACE\s+INTO\s+market_technical\b",
]

TECHNICAL_FEATURES = [
    "price",
    "close",
    "open",
    "high",
    "low",
    "volume",
    "history_points",
    "rsi14",
    "rsi_14",
    "atr14",
    "atr_14",
    "ema20",
    "ema_20",
    "sma20",
    "sma_20",
    "volatility",
    "volatility_5",
    "volatility_10",
    "volatility_20",
    "bb_width",
    "cloud_thickness",
    "trend",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "volume_score",
    "range_score",
    "breakout_score",
    "breakout_20",
    "volume_ratio",
    "fib_available",
    "fib_236",
    "fib_382",
    "fib_500",
    "fib_618",
    "fib_786",
    "ichimoku_available",
    "tenkan",
    "kijun",
    "senkou_a",
    "senkou_b",
    "technical_available",
    "available",
    "technical_completeness",
    "completeness",
]

PREREQUISITE_TERMS = [
    "history",
    "history_points",
    "market_history",
    "market_data",
    "ohlcv",
    "candles",
    "candle",
    "price",
    "volume",
    "timestamp",
    "time",
    "close",
    "open",
    "high",
    "low",
]

VALIDATION_TERMS = [
    "validate",
    "validation",
    "technical_validation",
    "technical_validated",
    "is_valid",
    "contract",
    "completeness",
    "quality",
]

PRODUCER_TERMS = [
    "market_technical",
    "technical",
    "rsi",
    "atr",
    "ema",
    "sma",
    "bollinger",
    "bb_width",
    "ichimoku",
    "fibonacci",
    "breakout",
    "momentum",
    "volatility",
    "trend",
    "volume_ratio",
]


def print_header(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def safe_read(path):
    try:
        with open(path, "rb") as f:
            raw = f.read()

        bom = raw.startswith(b"\xef\xbb\xbf")

        if bom:
            raw = raw[3:]

        return raw.decode("utf-8"), bom

    except Exception:
        return None, False


def iter_python_files():
    excluded_dirs = {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "node_modules",
    }

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [
            d for d in dirs
            if d not in excluded_dirs
        ]

        for filename in files:
            if not filename.endswith(".py"):
                continue

            path = os.path.join(root, filename)

            if os.path.abspath(path) == os.path.abspath(__file__):
                continue

            yield path


def get_line_number(source, offset):
    return source.count("\n", 0, offset) + 1


def normalize_identifier(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def collect_ast_functions(tree):
    functions = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            functions.append(node)

    return functions


def collect_ast_calls(tree):
    calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            calls.append(node)

    return calls


def get_call_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parts = []

        current = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return ""


def source_context(source, line, radius=2):
    lines = source.splitlines()

    start = max(0, line - 1 - radius)
    end = min(len(lines), line + radius)

    return "\n".join(
        f"{i + 1:6}: {lines[i]}"
        for i in range(start, end)
    )


def scan_source(path):
    source, bom = safe_read(path)

    if source is None:
        return {
            "path": path,
            "source": None,
            "bom": False,
            "parse_error": None,
            "functions": [],
            "technical_hits": [],
            "producer_hits": [],
            "validation_hits": [],
            "prerequisite_hits": [],
            "write_hits": [],
        }

    parse_error = None
    tree = None

    try:
        tree = ast.parse(source, filename=path)

    except SyntaxError as exc:
        parse_error = str(exc)

    functions = []
    technical_hits = []
    producer_hits = []
    validation_hits = []
    prerequisite_hits = []
    write_hits = []

    lower_source = source.lower()

    if tree is not None:
        functions = collect_ast_functions(tree)

    for term in TECHNICAL_FEATURES:
        pattern = re.compile(
            r"\b" + re.escape(term.lower()) + r"\b"
        )

        for match in pattern.finditer(lower_source):
            line = get_line_number(source, match.start())

            technical_hits.append(
                {
                    "term": term,
                    "line": line,
                }
            )

    for term in PRODUCER_TERMS:
        if term.lower() in lower_source:
            for match in re.finditer(
                re.escape(term.lower()),
                lower_source,
            ):
                line = get_line_number(source, match.start())

                producer_hits.append(
                    {
                        "term": term,
                        "line": line,
                    }
                )

    for term in VALIDATION_TERMS:
        if term.lower() in lower_source:
            for match in re.finditer(
                re.escape(term.lower()),
                lower_source,
            ):
                line = get_line_number(source, match.start())

                validation_hits.append(
                    {
                        "term": term,
                        "line": line,
                    }
                )

    for term in PREREQUISITE_TERMS:
        if term.lower() in lower_source:
            for match in re.finditer(
                re.escape(term.lower()),
                lower_source,
            ):
                line = get_line_number(source, match.start())

                prerequisite_hits.append(
                    {
                        "term": term,
                        "line": line,
                    }
                )

    for pattern in WRITE_PATTERNS:
        for match in re.finditer(
            pattern,
            source,
            flags=re.IGNORECASE,
        ):
            line = get_line_number(
                source,
                match.start(),
            )

            write_hits.append(
                {
                    "pattern": pattern,
                    "line": line,
                    "text": match.group(0),
                }
            )

    return {
        "path": path,
        "source": source,
        "bom": bom,
        "parse_error": parse_error,
        "functions": functions,
        "technical_hits": technical_hits,
        "producer_hits": producer_hits,
        "validation_hits": validation_hits,
        "prerequisite_hits": prerequisite_hits,
        "write_hits": write_hits,
    }


def inspect_database():
    result = {
        "connected": False,
        "error": None,
        "mode": None,
        "query_only": None,
        "table_exists": False,
        "columns": [],
        "row_count": 0,
        "non_null": defaultdict(int),
        "distinct_counts": {},
    }

    conn = None

    try:
        uri = (
            "file:"
            + DB_PATH.replace("\\", "/")
            + "?mode=ro"
        )

        conn = sqlite3.connect(
            uri,
            uri=True,
        )

        conn.execute(
            "PRAGMA query_only = ON"
        )

        result["connected"] = True
        result["mode"] = conn.execute(
            "PRAGMA journal_mode"
        ).fetchone()[0]

        result["query_only"] = conn.execute(
            "PRAGMA query_only"
        ).fetchone()[0]

        exists = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name=?
            """,
            (TARGET_TABLE,),
        ).fetchone()

        result["table_exists"] = exists is not None

        if not result["table_exists"]:
            return result

        columns = conn.execute(
            f'PRAGMA table_info("{TARGET_TABLE}")'
        ).fetchall()

        result["columns"] = [
            {
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "notnull": row[3],
                "default": row[4],
                "pk": row[5],
            }
            for row in columns
        ]

        result["row_count"] = conn.execute(
            f'SELECT COUNT(*) FROM "{TARGET_TABLE}"'
        ).fetchone()[0]

        column_names = {
            row[1]
            for row in columns
        }

        for feature in TECHNICAL_FEATURES:
            if feature not in column_names:
                continue

            value = conn.execute(
                f'''
                SELECT COUNT(*)
                FROM "{TARGET_TABLE}"
                WHERE "{feature}" IS NOT NULL
                '''
            ).fetchone()[0]

            result["non_null"][feature] = value

        for feature in [
            "technical_validation_status",
            "technical_validation_version",
            "technical_available",
            "available",
            "fib_available",
            "ichimoku_available",
        ]:
            if feature not in column_names:
                continue

            rows = conn.execute(
                f'''
                SELECT "{feature}", COUNT(*)
                FROM "{TARGET_TABLE}"
                GROUP BY "{feature}"
                ORDER BY COUNT(*) DESC
                LIMIT 20
                '''
            ).fetchall()

            result["distinct_counts"][feature] = rows

    except Exception as exc:
        result["error"] = (
            f"{type(exc).__name__}: {exc}"
        )

    finally:
        if conn is not None:
            conn.close()

    return result


def find_function_for_line(functions, line):
    candidates = []

    for fn in functions:
        start = getattr(fn, "lineno", 0)
        end = getattr(
            fn,
            "end_lineno",
            start,
        )

        if start <= line <= end:
            candidates.append(fn)

    if not candidates:
        return None

    return sorted(
        candidates,
        key=lambda x: (
            x.end_lineno - x.lineno,
            x.lineno,
        ),
    )[0]


def summarize_files(scans):
    technical_files = []
    producer_files = []
    validation_files = []
    prerequisite_files = []
    write_files = []

    for item in scans:
        if item["technical_hits"]:
            technical_files.append(item)

        if item["producer_hits"]:
            producer_files.append(item)

        if item["validation_hits"]:
            validation_files.append(item)

        if item["prerequisite_hits"]:
            prerequisite_files.append(item)

        if item["write_hits"]:
            write_files.append(item)

    return (
        technical_files,
        producer_files,
        validation_files,
        prerequisite_files,
        write_files,
    )


def print_database_contract(db):
    print_header(
        "PERSISTED MARKET_TECHNICAL CONTRACT"
    )

    print(
        f"Database Path                 : {DB_PATH}"
    )

    print(
        f"Database Connected             : "
        f"{'YES' if db['connected'] else 'NO'}"
    )

    if db["error"]:
        print(
            f"Database Error                 : "
            f"{db['error']}"
        )
        return

    print(
        f"SQLite Query Only              : "
        f"{db['query_only']}"
    )

    print(
        f"market_technical Exists        : "
        f"{'YES' if db['table_exists'] else 'NO'}"
    )

    if not db["table_exists"]:
        return

    print(
        f"Persisted Rows                 : "
        f"{db['row_count']}"
    )

    print()
    print(
        "COLUMNS"
    )
    print("-" * 100)

    for column in db["columns"]:
        print(
            f"{column['cid']:>4}  "
            f"{column['name']:<34} "
            f"{column['type']:<12} "
            f"NOTNULL={column['notnull']} "
            f"PK={column['pk']}"
        )

    print()
    print(
        "FEATURE POPULATION"
    )
    print("-" * 100)

    for feature in TECHNICAL_FEATURES:
        if feature not in db["non_null"]:
            continue

        count = db["non_null"][feature]

        print(
            f"{feature:<32} "
            f"{count:>10} / {db['row_count']}"
        )

    print()
    print(
        "IMPORTANT DISTRIBUTIONS"
    )
    print("-" * 100)

    for feature, rows in db[
        "distinct_counts"
    ].items():

        print()
        print(
            f"{feature}"
        )

        for value, count in rows:
            print(
                f"    {str(value):<30} "
                f"{count}"
            )


def print_write_contract(write_files):
    print_header(
        "MARKET_TECHNICAL WRITE REFERENCES"
    )

    total = sum(
        len(item["write_hits"])
        for item in write_files
    )

    print(
        f"Files With Technical Writes      : "
        f"{len(write_files)}"
    )

    print(
        f"Technical Write References       : "
        f"{total}"
    )

    if not write_files:
        print(
            "No market_technical write references found."
        )
        return

    for item in write_files:
        print()
        print(
            f"FILE : "
            f"{os.path.relpath(item['path'], BASE_DIR)}"
        )

        for hit in item["write_hits"]:
            print(
                f"  line={hit['line']:<6} "
                f"{hit['text']}"
            )

            print(
                source_context(
                    item["source"],
                    hit["line"],
                    radius=1,
                )
            )


def print_producer_contract(
    producer_files,
    technical_files,
    prerequisite_files,
    validation_files,
):
    print_header(
        "PRODUCER → FEATURE → PREREQUISITE → VALIDATION CONTRACT"
    )

    print(
        f"Producer Feature Files           : "
        f"{len(producer_files)}"
    )

    print(
        f"Technical Feature Files          : "
        f"{len(technical_files)}"
    )

    print(
        f"Prerequisite Reference Files     : "
        f"{len(prerequisite_files)}"
    )

    print(
        f"Validation Reference Files       : "
        f"{len(validation_files)}"
    )

    print()
    print(
        "TOP PRODUCER / FEATURE FILES"
    )
    print("-" * 100)

    ranked = []

    for item in producer_files:
        feature_terms = sorted(
            {
                hit["term"]
                for hit in item["technical_hits"]
            }
        )

        producer_terms = sorted(
            {
                hit["term"]
                for hit in item["producer_hits"]
            }
        )

        prerequisite_terms = sorted(
            {
                hit["term"]
                for hit in item["prerequisite_hits"]
            }
        )

        validation_terms = sorted(
            {
                hit["term"]
                for hit in item["validation_hits"]
            }
        )

        score = (
            len(feature_terms) * 3
            + len(producer_terms) * 2
            + len(prerequisite_terms)
            + len(validation_terms) * 2
        )

        ranked.append(
            (
                score,
                item,
                feature_terms,
                producer_terms,
                prerequisite_terms,
                validation_terms,
            )
        )

    ranked.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    for (
        score,
        item,
        feature_terms,
        producer_terms,
        prerequisite_terms,
        validation_terms,
    ) in ranked[:80]:

        rel = os.path.relpath(
            item["path"],
            BASE_DIR,
        )

        print()
        print(
            f"[SCORE {score:>4}] {rel}"
        )

        print(
            "  FEATURES      : "
            + (
                ", ".join(feature_terms)
                if feature_terms
                else "NONE"
            )
        )

        print(
            "  PRODUCER TERMS: "
            + (
                ", ".join(producer_terms)
                if producer_terms
                else "NONE"
            )
        )

        print(
            "  PREREQUISITES : "
            + (
                ", ".join(prerequisite_terms)
                if prerequisite_terms
                else "NONE"
            )
        )

        print(
            "  VALIDATION    : "
            + (
                ", ".join(validation_terms)
                if validation_terms
                else "NONE"
            )
        )


def print_validation_function_map(scans):
    print_header(
        "VALIDATION FUNCTION MAP"
    )

    found = 0

    for item in scans:
        if item["source"] is None:
            continue

        if not item["validation_hits"]:
            continue

        for hit in item["validation_hits"]:

            fn = find_function_for_line(
                item["functions"],
                hit["line"],
            )

            if fn is None:
                continue

            found += 1

            print()
            print(
                f"FILE : "
                f"{os.path.relpath(item['path'], BASE_DIR)}"
            )

            print(
                f"  line={hit['line']:<6} "
                f"term={hit['term']}"
            )

            print(
                f"  FUNCTION : {fn.name}()"
            )

            print(
                f"  RANGE    : "
                f"{fn.lineno}-{fn.end_lineno}"
            )

    print()
    print(
        f"Validation Function Relationships : {found}"
    )


def print_ast_errors(scans):
    errors = [
        item
        for item in scans
        if item["parse_error"]
    ]

    print_header(
        "AST PARSE ERROR FORENSIC"
    )

    print(
        f"AST Parse Errors : {len(errors)}"
    )

    for item in errors:
        print()
        print(
            os.path.relpath(
                item["path"],
                BASE_DIR,
            )
        )
        print(
            item["parse_error"]
        )


def print_target_feature_contract(db):
    print_header(
        "TARGET FEATURE CONTRACT"
    )

    if not db["table_exists"]:
        print(
            "market_technical table unavailable."
        )
        return

    persisted_columns = {
        column["name"]
        for column in db["columns"]
    }

    for feature in TECHNICAL_FEATURES:

        if feature not in persisted_columns:
            continue

        population = db["non_null"].get(
            feature,
            0,
        )

        ratio = 0.0

        if db["row_count"] > 0:
            ratio = (
                population
                / db["row_count"]
            )

        print(
            f"{feature:<32} "
            f"population={population:>8} "
            f"ratio={ratio:>8.3f}"
        )


def main():
    print("=" * 100)
    print(
        "ARUNDA TRADER MARKET TECHNICAL "
        "PRODUCER FEATURE CONTRACT FORENSIC v0.1"
    )
    print("=" * 100)

    print(
        f"BASE DIR : {BASE_DIR}"
    )

    print(
        f"DB PATH  : {DB_PATH}"
    )

    print(
        "MODE     : READ ONLY"
    )

    scans = []

    for path in iter_python_files():
        scans.append(
            scan_source(path)
        )

    db = inspect_database()

    (
        technical_files,
        producer_files,
        validation_files,
        prerequisite_files,
        write_files,
    ) = summarize_files(scans)

    python_sources = len(scans)

    validation_candidates = sum(
        1
        for item in scans
        if item["validation_hits"]
        or item["producer_hits"]
        or item["technical_hits"]
    )

    bom_files = sum(
        1
        for item in scans
        if item["bom"]
    )

    parse_errors = sum(
        1
        for item in scans
        if item["parse_error"]
    )

    print_header(
        "DISCOVERY SUMMARY"
    )

    print(
        f"Python Sources Inspected        : "
        f"{python_sources}"
    )

    print(
        f"Validation Candidates           : "
        f"{validation_candidates}"
    )

    print(
        f"AST Parse Errors                : "
        f"{parse_errors}"
    )

    print(
        f"UTF-8 BOM Files                 : "
        f"{bom_files}"
    )

    print(
        f"Producer Feature Files          : "
        f"{len(producer_files)}"
    )

    print(
        f"Technical Feature Files         : "
        f"{len(technical_files)}"
    )

    print(
        f"Prerequisite Files              : "
        f"{len(prerequisite_files)}"
    )

    print(
        f"Validation Reference Files      : "
        f"{len(validation_files)}"
    )

    print_write_contract(
        write_files
    )

    print_database_contract(
        db
    )

    print_target_feature_contract(
        db
    )

    print_producer_contract(
        producer_files,
        technical_files,
        prerequisite_files,
        validation_files,
    )

    print_validation_function_map(
        scans
    )

    print_ast_errors(
        scans
    )

    print_header(
        "FINAL PRODUCER FEATURE CONTRACT"
    )

    print(
        f"Python Sources Inspected        : "
        f"{python_sources}"
    )

    print(
        f"Producer Feature Files          : "
        f"{len(producer_files)}"
    )

    print(
        f"Technical Feature Files         : "
        f"{len(technical_files)}"
    )

    print(
        f"Prerequisite Files              : "
        f"{len(prerequisite_files)}"
    )

    print(
        f"Validation Reference Files      : "
        f"{len(validation_files)}"
    )

    print(
        f"Files With Technical Writes     : "
        f"{len(write_files)}"
    )

    print(
        "READ ONLY                       : YES"
    )

    print(
        "SQLite mode                     : mode=ro"
    )

    print(
        "query_only                      : 1"
    )

    print(
        "INSERT                          : NONE"
    )

    print(
        "UPDATE                          : NONE"
    )

    print(
        "DELETE                          : NONE"
    )

    print(
        "ALTER                           : NONE"
    )

    print(
        "CREATE                          : NONE"
    )

    print(
        "DROP                            : NONE"
    )

    print(
        "REPLACE                         : NONE"
    )

    print(
        "COMMIT                          : NONE"
    )

    print(
        "SOURCE MODIFICATION             : NONE"
    )

    print(
        "SYNTHETIC DATA                  : NONE"
    )

    print(
        "INTERPOLATION                   : NONE"
    )

    print(
        "FORWARD FILL                    : NONE"
    )

    print(
        "BACK FILL                       : NONE"
    )

    print()
    print(
        "FORENSIC STATUS : COMPLETE"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This script is strictly read-only."
    )

    print(
        "It discovers producer references, "
        "technical feature references, "
        "prerequisite references, "
        "validation functions, "
        "SQL write references and persisted schema/population."
    )

    print(
        "It does NOT execute market_technical_engine."
    )

    print(
        "It does NOT modify the production database."
    )

    print(
        "It does NOT repair production state."
    )

    print(
        "It does NOT generate synthetic data."
    )

    print("=" * 100)
    print(
        "ARUNDA TRADER MARKET TECHNICAL "
        "PRODUCER FEATURE CONTRACT FORENSIC v0.1 COMPLETE"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()