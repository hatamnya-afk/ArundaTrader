import ast
import os
import re
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "arunda.db")
TARGET = "market_technical"


WRITE_RE = re.compile(
    r"\b(?:INSERT\s+(?:OR\s+\w+\s+)?INTO|UPDATE|REPLACE\s+INTO)"
    r"\s+market_technical\b",
    re.I,
)

SQL_CALL_RE = re.compile(
    r"(?:execute|executemany|executescript)\s*\(",
    re.I,
)

SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES",
}

SKIP_FILES = {
    os.path.basename(__file__),
}


def line_of(source, node):
    return source.count("\n", 0, node.lineno - 1) + 1


def function_name(tree, lineno):
    best = None
    best_span = None

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", start)

            if start <= lineno <= end:
                span = end - start
                if best is None or span < best_span:
                    best = node.name
                    best_span = span

    return best or "GLOBAL"


def context_lines(lines, lineno, radius=3):
    start = max(1, lineno - radius)
    end = min(len(lines), lineno + radius)

    return "\n".join(
        f"{i}: {lines[i - 1]}"
        for i in range(start, end + 1)
    )


def sql_text_from_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            else:
                parts.append("{...}")
        return "".join(parts)

    return None


def inspect_file(path):
    try:
        with open(path, "rb") as f:
            raw = f.read()

        bom = raw.startswith(b"\xef\xbb\xbf")
        source = raw.decode("utf-8-sig")

        tree = ast.parse(source, filename=path)

    except Exception as exc:
        return {
            "error": str(exc),
            "path": path,
        }

    lines = source.splitlines()
    hits = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        call_name = None

        if isinstance(node.func, ast.Attribute):
            call_name = node.func.attr

        elif isinstance(node.func, ast.Name):
            call_name = node.func.id

        if not call_name or not SQL_CALL_RE.match(call_name + "("):
            continue

        sql_candidates = []

        for arg in node.args:
            text = sql_text_from_node(arg)
            if text:
                sql_candidates.append(text)

        for kw in node.keywords:
            text = sql_text_from_node(kw.value)
            if text:
                sql_candidates.append(text)

        for sql in sql_candidates:
            if WRITE_RE.search(sql):

                lineno = line_of(source, node)

                hits.append({
                    "path": path,
                    "line": lineno,
                    "function": function_name(tree, lineno),
                    "call": call_name,
                    "sql": " ".join(sql.split()),
                    "context": context_lines(lines, lineno),
                    "bom": bom,
                })

    return {
        "hits": hits,
        "error": None,
        "path": path,
    }


def find_python_files():
    files = []

    for root, dirs, filenames in os.walk(BASE_DIR):

        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS
        ]

        for name in filenames:

            if not name.endswith(".py"):
                continue

            if name in SKIP_FILES:
                continue

            files.append(os.path.join(root, name))

    return sorted(files)


def db_population():
    result = {
        "exists": os.path.exists(DB_PATH),
        "rows": None,
    }

    if not result["exists"]:
        return result

    try:
        conn = sqlite3.connect(
            f"file:{DB_PATH}?mode=ro",
            uri=True
        )

        conn.execute("PRAGMA query_only = ON")

        row = conn.execute(
            "SELECT COUNT(*) FROM market_technical"
        ).fetchone()

        result["rows"] = row[0] if row else 0

        conn.close()

    except Exception as exc:
        result["error"] = str(exc)

    return result


def main():

    print("=" * 100)
    print("ARUNDA MARKET TECHNICAL INSERT CALLER CHAIN FORENSIC v0.1")
    print("=" * 100)

    print("MODE          : READ ONLY")
    print("EXECUTION     : NO")
    print("DB WRITE      : NO")
    print("SOURCE MODIFY : NO")
    print(f"DATABASE      : {DB_PATH}")
    print()

    files = find_python_files()

    parse_errors = []
    all_hits = []

    for path in files:

        result = inspect_file(path)

        if result["error"]:
            parse_errors.append(result)
            continue

        all_hits.extend(result["hits"])

    print("=" * 100)
    print("SCAN SUMMARY")
    print("=" * 100)

    print(f"Python Sources Inspected : {len(files)}")
    print(f"AST Parse Errors         : {len(parse_errors)}")
    print(f"market_technical Writes  : {len(all_hits)}")
    print()

    print("=" * 100)
    print("REAL market_technical WRITE BOUNDARIES")
    print("=" * 100)

    if not all_hits:
        print("NO REAL WRITE BOUNDARY FOUND")
    else:

        for i, hit in enumerate(all_hits, 1):

            print()
            print(f"[WRITE {i}]")
            print(f"FILE     : {os.path.relpath(hit['path'], BASE_DIR)}")
            print(f"LINE     : {hit['line']}")
            print(f"FUNCTION : {hit['function']}")
            print(f"CALL     : {hit['call']}")
            print(f"SQL      : {hit['sql']}")
            print(f"BOM      : {'YES' if hit['bom'] else 'NO'}")
            print("CONTEXT  :")
            print(hit["context"])

    print()
    print("=" * 100)
    print("CALLER CHAIN TARGETS")
    print("=" * 100)

    if all_hits:

        files_seen = set()

        for hit in all_hits:

            rel = os.path.relpath(
                hit["path"],
                BASE_DIR
            )

            key = (rel, hit["function"])

            if key in files_seen:
                continue

            files_seen.add(key)

            print()
            print(f"FILE     : {rel}")
            print(f"FUNCTION : {hit['function']}")
            print(f"WRITE    : {hit['call']}")
            print(f"LINE     : {hit['line']}")

    print()
    print("=" * 100)
    print("PERSISTED MARKET_TECHNICAL")
    print("=" * 100)

    db = db_population()

    print(f"DATABASE EXISTS : {'YES' if db['exists'] else 'NO'}")

    if db.get("rows") is not None:
        print(f"ROWS            : {db['rows']}")

    if db.get("error"):
        print(f"DB ERROR        : {db['error']}")

    print()
    print("=" * 100)
    print("AST PARSE ERRORS")
    print("=" * 100)

    if not parse_errors:
        print("NONE")
    else:
        for item in parse_errors:
            print()
            print(
                f"{os.path.relpath(item['path'], BASE_DIR)}"
            )
            print(item["error"])

    print()
    print("=" * 100)
    print("FINAL CONTRACT")
    print("=" * 100)

    print("Target Table              : market_technical")
    print(f"Python Sources Inspected  : {len(files)}")
    print(f"Real Write References     : {len(all_hits)}")
    print(f"AST Parse Errors          : {len(parse_errors)}")
    print("READ ONLY                 : YES")
    print("EXECUTION                 : NONE")
    print("INSERT                    : NONE")
    print("UPDATE                    : NONE")
    print("DELETE                    : NONE")
    print("ALTER                     : NONE")
    print("CREATE                    : NONE")
    print("DROP                      : NONE")
    print("COMMIT                    : NONE")
    print("SOURCE MODIFICATION      : NONE")
    print("SYNTHETIC DATA           : NONE")
    print("INTERPOLATION            : NONE")
    print("FORWARD FILL             : NONE")
    print("BACK FILL                : NONE")

    print()
    print("=" * 100)
    print("FORENSIC STATUS : COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()