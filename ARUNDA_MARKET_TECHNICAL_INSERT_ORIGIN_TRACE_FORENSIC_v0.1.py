import ast
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SELF = os.path.basename(__file__)

SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "env",
    "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES"
}

SKIP_WORDS = (
    "FORENSIC",
    "AUDIT",
    "DISCOVERY",
    "VALIDATION",
    "RECONCILIATION",
    "LOCATOR",
    "TRACE",
)

TARGET = "market_technical"

WRITE_WORDS = (
    "INSERT",
    "REPLACE",
    "UPDATE",
)

EXEC_CALLS = {
    "execute",
    "executemany",
    "executescript",
}

TABLE_RE = re.compile(
    r"\b(?:INSERT\s+(?:OR\s+\w+\s+)?INTO|REPLACE\s+INTO|UPDATE)"
    r"\s+[`'\"]?market_technical[`'\"]?",
    re.I,
)


def source_text(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    if isinstance(node, ast.JoinedStr):
        parts = []
        for x in node.values:
            if isinstance(x, ast.Constant):
                parts.append(str(x.value))
            else:
                parts.append("{EXPR}")
        return "".join(parts)

    return None


def clean_sql(text):
    return " ".join(text.split())


def get_function_map(tree):
    result = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.append(
                (
                    node.lineno,
                    getattr(node, "end_lineno", node.lineno),
                    node.name,
                )
            )

    return result


def function_at(functions, line):
    matches = [
        x for x in functions
        if x[0] <= line <= x[1]
    ]

    if not matches:
        return "GLOBAL"

    return min(
        matches,
        key=lambda x: x[1] - x[0]
    )[2]


def line_context(lines, line, radius=4):
    start = max(1, line - radius)
    end = min(len(lines), line + radius)

    return "\n".join(
        f"{i}: {lines[i - 1]}"
        for i in range(start, end + 1)
    )


def is_target_sql(text):
    if not text:
        return False

    return bool(TABLE_RE.search(text))


def scan_file(path):
    try:
        with open(path, "rb") as f:
            raw = f.read()

        source = raw.decode("utf-8-sig")
        tree = ast.parse(source, filename=path)

    except Exception as e:
        return {
            "error": str(e),
            "hits": [],
        }

    lines = source.splitlines()
    functions = get_function_map(tree)
    hits = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Attribute):
            call_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            call_name = node.func.id
        else:
            continue

        if call_name not in EXEC_CALLS:
            continue

        sql_candidates = []

        for arg in node.args:
            text = source_text(arg)
            if text:
                sql_candidates.append(text)

        for kw in node.keywords:
            text = source_text(kw.value)
            if text:
                sql_candidates.append(text)

        for sql in sql_candidates:
            if is_target_sql(sql):

                line = node.lineno

                hits.append({
                    "file": path,
                    "line": line,
                    "function": function_at(functions, line),
                    "call": call_name,
                    "sql": clean_sql(sql),
                    "context": line_context(lines, line),
                })

    return {
        "error": None,
        "hits": hits,
    }


def scan_dynamic_strings(path):
    """
    Second pass:
    Finds variables/constants containing market_technical,
    then shows nearby execute/executemany usage.
    """

    try:
        with open(path, "rb") as f:
            raw = f.read()

        source = raw.decode("utf-8-sig")
        tree = ast.parse(source, filename=path)

    except Exception:
        return []

    lines = source.splitlines()
    functions = get_function_map(tree)

    target_assignments = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.Assign, ast.AnnAssign, ast.AugAssign)
        ):

            text = None

            if isinstance(node, ast.Assign):
                for value in [node.value]:
                    text = source_text(value)

            elif isinstance(node, ast.AnnAssign):
                text = source_text(node.value)

            elif isinstance(node, ast.AugAssign):
                text = source_text(node.value)

            if text and TARGET.lower() in text.lower():

                target_assignments.append({
                    "line": node.lineno,
                    "text": clean_sql(text),
                    "function": function_at(
                        functions,
                        node.lineno
                    ),
                })

    return target_assignments


def python_files():
    result = []

    for root, dirs, files in os.walk(BASE_DIR):

        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS
        ]

        for name in files:

            if not name.endswith(".py"):
                continue

            if name == SELF:
                continue

            upper = name.upper()

            if any(word in upper for word in SKIP_WORDS):
                continue

            result.append(
                os.path.join(root, name)
            )

    return sorted(result)


def main():

    print("=" * 100)
    print("ARUNDA MARKET TECHNICAL INSERT ORIGIN TRACE FORENSIC v0.1")
    print("=" * 100)

    print("MODE            : READ ONLY")
    print("EXECUTION       : NO")
    print("DB WRITE        : NO")
    print("SOURCE MODIFY   : NO")
    print(f"TARGET TABLE    : {TARGET}")
    print()

    files = python_files()

    all_hits = []
    dynamic_hits = []
    errors = []

    for path in files:

        result = scan_file(path)

        if result["error"]:
            errors.append(
                (
                    path,
                    result["error"]
                )
            )
            continue

        all_hits.extend(result["hits"])

        for item in scan_dynamic_strings(path):
            dynamic_hits.append(
                {
                    "file": path,
                    **item,
                }
            )

    print("=" * 100)
    print("SCAN SUMMARY")
    print("=" * 100)

    print(
        f"Python Sources Inspected : {len(files)}"
    )

    print(
        f"AST Parse Errors         : {len(errors)}"
    )

    print(
        f"Direct SQL Target Hits   : {len(all_hits)}"
    )

    print(
        f"Dynamic Target Strings   : {len(dynamic_hits)}"
    )

    print()

    print("=" * 100)
    print("DIRECT market_technical WRITE ORIGIN")
    print("=" * 100)

    if not all_hits:
        print("NO DIRECT SQL WRITE FOUND")
    else:

        for i, hit in enumerate(all_hits, 1):

            print()
            print(f"[WRITE {i}]")
            print(
                "FILE     : "
                + os.path.relpath(
                    hit["file"],
                    BASE_DIR
                )
            )
            print(f"LINE     : {hit['line']}")
            print(f"FUNCTION : {hit['function']}")
            print(f"CALL     : {hit['call']}")
            print(f"SQL      : {hit['sql']}")
            print("CONTEXT  :")
            print(hit["context"])

    print()

    print("=" * 100)
    print("DYNAMIC market_technical STRING ORIGIN")
    print("=" * 100)

    if not dynamic_hits:
        print("NO DYNAMIC TARGET STRING FOUND")
    else:

        for i, hit in enumerate(dynamic_hits, 1):

            print()
            print(f"[DYNAMIC {i}]")
            print(
                "FILE     : "
                + os.path.relpath(
                    hit["file"],
                    BASE_DIR
                )
            )
            print(f"LINE     : {hit['line']}")
            print(f"FUNCTION : {hit['function']}")
            print(f"VALUE    : {hit['text']}")

    print()

    print("=" * 100)
    print("POTENTIAL PRODUCER FILES")
    print("=" * 100)

    producer_files = set()

    for hit in all_hits:
        producer_files.add(hit["file"])

    for hit in dynamic_hits:
        producer_files.add(hit["file"])

    if not producer_files:
        print("NONE")
    else:
        for path in sorted(producer_files):
            print(
                os.path.relpath(
                    path,
                    BASE_DIR
                )
            )

    print()

    print("=" * 100)
    print("AST PARSE ERRORS")
    print("=" * 100)

    if not errors:
        print("NONE")
    else:
        for path, error in errors:
            print()
            print(
                os.path.relpath(
                    path,
                    BASE_DIR
                )
            )
            print(error)

    print()

    print("=" * 100)
    print("FORENSIC CONTRACT")
    print("=" * 100)

    print("TARGET                  : market_technical")
    print("READ ONLY               : YES")
    print("EXECUTION               : NONE")
    print("DB MODIFICATION         : NONE")
    print("SOURCE MODIFICATION     : NONE")
    print("SYNTHETIC DATA          : NONE")
    print("INTERPOLATION           : NONE")
    print("FORWARD FILL            : NONE")
    print("BACK FILL               : NONE")

    print()
    print(
        "FORENSIC STATUS : COMPLETE"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()