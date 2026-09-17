import ast
from pathlib import Path


ENGINE_VERSION = "v0.1"
ENGINE_FILE = "market_history_engine.py"


TARGET_FIELDS = (
    "symbol",
    "name",
    "timestamp",
    "created_at",
    "source",
    "source_timestamp",
    "engine_version",
)


def safe_unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<UNPARSEABLE>"


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

    return safe_unparse(node)


def main():

    print("=" * 100)
    print("ARUNDA MARKET HISTORY IDENTITY INGESTION SOURCE DIAGNOSTIC v0.1")
    print("READ-ONLY / CODE-PATH ANALYSIS")
    print("=" * 100)
    print(f"Engine File     : {ENGINE_FILE}")
    print("Mode            : READ ONLY")
    print("Database Write  : DISABLED")
    print(f"Diagnostic      : {ENGINE_VERSION}")
    print("=" * 100)

    path = Path(ENGINE_FILE)

    if not path.exists():
        print()
        print("ENGINE FILE     : NOT FOUND")
        print()
        print("=" * 100)
        print("DIAGNOSTIC ABORTED")
        print("=" * 100)
        return

    print()
    print("ENGINE FILE     : FOUND")
    print(f"Path            : {path.resolve()}")

    # UTF-8-SIG safely handles files containing a UTF-8 BOM (U+FEFF)
    source = path.read_text(encoding="utf-8-sig")

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print()
        print("AST PARSE        : FAILED")
        print(f"Line            : {exc.lineno}")
        print(f"Message         : {exc.msg}")
        return

    print("AST PARSE        : SUCCESS")

    print()
    print("=" * 100)
    print("FUNCTION MAP")
    print("=" * 100)

    functions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node)

    functions.sort(key=lambda x: x.lineno)

    print(f"Functions Found  : {len(functions)}")

    for node in functions:
        print(
            f"  {node.name:<40}"
            f" line={node.lineno:<5}"
            f" args={len(node.args.args)}"
        )

    print()
    print("=" * 100)
    print("DATABASE WRITE PATH INSPECTION")
    print("=" * 100)

    write_calls = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        call_name = get_call_name(node.func)
        lowered = call_name.lower()

        if any(
            token in lowered
            for token in (
                "execute",
                "executemany",
                "executescript",
                "insert",
                "upsert",
                "bulk_insert",
            )
        ):
            write_calls.append(
                (
                    node.lineno,
                    call_name,
                    safe_unparse(node),
                )
            )

    if write_calls:

        print(f"Potential DB/Insert Calls : {len(write_calls)}")

        for lineno, call_name, expression in write_calls:

            print()
            print(f"LINE            : {lineno}")
            print(f"CALL            : {call_name}")
            print(f"EXPRESSION      : {expression}")

    else:
        print("Potential DB/Insert Calls : NONE")

    print()
    print("=" * 100)
    print("MARKET_HISTORY INSERT INSPECTION")
    print("=" * 100)

    history_calls = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        expression = safe_unparse(node)

        if "market_history" in expression.lower():

            history_calls.append(
                (
                    node.lineno,
                    get_call_name(node.func),
                    expression,
                )
            )

    if history_calls:

        print(f"market_history References : {len(history_calls)}")

        for lineno, call_name, expression in history_calls:

            print()
            print(f"LINE            : {lineno}")
            print(f"CALL            : {call_name}")
            print(f"EXPRESSION      : {expression}")

    else:
        print("market_history References : NONE")

    print()
    print("=" * 100)
    print("IDENTITY FIELD CONSTRUCTION INSPECTION")
    print("=" * 100)

    field_hits = {
        field: []
        for field in TARGET_FIELDS
    }

    for node in ast.walk(tree):

        if isinstance(node, ast.Assign):

            target_text = safe_unparse(node.targets[0])

            for field in TARGET_FIELDS:

                if field in target_text.lower():

                    field_hits[field].append(
                        (
                            node.lineno,
                            target_text,
                            safe_unparse(node.value),
                        )
                    )

        elif isinstance(node, ast.AnnAssign):

            target_text = safe_unparse(node.target)

            for field in TARGET_FIELDS:

                if field in target_text.lower():

                    field_hits[field].append(
                        (
                            node.lineno,
                            target_text,
                            safe_unparse(node.value),
                        )
                    )

    for field in TARGET_FIELDS:

        print()
        print(f"[{field}]")

        if not field_hits[field]:
            print("  No direct assignment detected.")
            continue

        for lineno, target, value in field_hits[field]:

            print(f"  LINE       : {lineno}")
            print(f"  TARGET     : {target}")
            print(f"  VALUE      : {value}")

    print()
    print("=" * 100)
    print("ASSET SOURCE / COLLECTION INSPECTION")
    print("=" * 100)

    collection_names = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.For,
                ast.AsyncFor,
            ),
        ):

            iterable = safe_unparse(node.iter)

            collection_names.append(
                (
                    node.lineno,
                    iterable,
                    node.target.id
                    if isinstance(node.target, ast.Name)
                    else safe_unparse(node.target),
                )
            )

    if collection_names:

        print(f"Iteration Paths Found : {len(collection_names)}")

        for lineno, iterable, target in collection_names:

            print()
            print(f"LINE            : {lineno}")
            print(f"TARGET          : {target}")
            print(f"ITERABLE        : {iterable}")

    else:
        print("Iteration Paths Found : NONE")

    print()
    print("=" * 100)
    print("HTTP / API SOURCE INSPECTION")
    print("=" * 100)

    api_calls = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        call_name = get_call_name(node.func).lower()

        if any(
            token in call_name
            for token in (
                "get",
                "post",
                "request",
                "fetch",
                "urlopen",
            )
        ):

            expression = safe_unparse(node)

            api_calls.append(
                (
                    node.lineno,
                    get_call_name(node.func),
                    expression,
                )
            )

    if api_calls:

        print(f"Potential API Calls : {len(api_calls)}")

        for lineno, call_name, expression in api_calls:

            print()
            print(f"LINE            : {lineno}")
            print(f"CALL            : {call_name}")
            print(f"EXPRESSION      : {expression}")

    else:
        print("Potential API Calls : NONE")

    print()
    print("=" * 100)
    print("IDENTITY RISK INDICATORS")
    print("=" * 100)

    indicators = []

    source_assignment = field_hits["source"]
    source_timestamp_assignment = field_hits["source_timestamp"]
    engine_assignment = field_hits["engine_version"]

    if not source_assignment:
        indicators.append(
            "SOURCE FIELD HAS NO DIRECT ASSIGNMENT IN ENGINE"
        )

    if not source_timestamp_assignment:
        indicators.append(
            "SOURCE_TIMESTAMP FIELD HAS NO DIRECT ASSIGNMENT IN ENGINE"
        )

    if not engine_assignment:
        indicators.append(
            "ENGINE_VERSION FIELD HAS NO DIRECT ASSIGNMENT IN ENGINE"
        )

    if field_hits["symbol"]:
        indicators.append(
            "SYMBOL IS CONSTRUCTED/ASSIGNED IN ENGINE"
        )

    if field_hits["name"]:
        indicators.append(
            "NAME IS CONSTRUCTED/ASSIGNED IN ENGINE"
        )

    if indicators:

        for indicator in indicators:
            print(f"- {indicator}")

    else:
        print("No direct identity risk indicators detected.")

    print()
    print("=" * 100)
    print("DIAGNOSTIC CONCLUSION")
    print("=" * 100)

    print("Analysis Mode              : READ ONLY")
    print("Database Modification      : NONE")
    print("Engine Modification        : NONE")
    print("Identity Repair            : NONE")
    print()
    print(
        "NO DATABASE OR ENGINE "
        "MODIFICATIONS WERE PERFORMED."
    )

    print("=" * 100)
    print(
        "ARUNDA MARKET HISTORY IDENTITY INGESTION SOURCE "
        f"DIAGNOSTIC {ENGINE_VERSION} COMPLETE"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()