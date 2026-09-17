from pathlib import Path
import ast
import re

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGETS = [
    "market_data_engine.py",
    "coinalyze_positioning.py",
    "news_adapter.py",
    "catalyst_engine.py",
    "market_news_engine.py",
]

print("=" * 100)
print("ARUNDA FUSION PRODUCTION INPUT CONTRACT RESOLUTION v0.1")
print("=" * 100)

for filename in TARGETS:

    path = ROOT / filename

    print()
    print("=" * 100)
    print("FILE:", path)
    print("=" * 100)

    if not path.exists():
        print("STATUS=FILE_NOT_FOUND")
        continue

    source = path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    print("SIZE=", len(source), "bytes")

    try:
        tree = ast.parse(
            source,
            filename=str(path)
        )
    except Exception as exc:
        print(
            "AST_PARSE=FAIL",
            type(exc).__name__,
            str(exc)
        )
        continue

    functions = []

    for node in tree.body:

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            functions.append(node)

    print()
    print("TOP_LEVEL_FUNCTIONS:")

    for fn in functions:

        print(
            f"  {fn.name}{ast.unparse(fn.args) if hasattr(ast, 'unparse') else ''}"
        )

    print()
    print("RELEVANT_FUNCTIONS:")

    for fn in functions:

        lname = fn.name.lower()

        if any(
            token in lname
            for token in (
                "score",
                "market",
                "technical",
                "position",
                "news",
                "signal",
                "fetch",
                "collect",
                "build",
                "produce",
                "adapt",
                "normalize",
            )
        ):

            try:
                signature = ast.unparse(
                    fn.args
                )
            except Exception:
                signature = "UNKNOWN"

            print(
                f"  {fn.name} | args={signature}"
            )

    print()
    print("RETURN / SCORE / SOURCE EVIDENCE:")

    lines = source.splitlines()

    for i, line in enumerate(lines, 1):

        low = line.lower()

        if any(
            token in low
            for token in (
                "technical_score",
                "market_score",
                "positioning_score",
                "news_score",
                "source",
                "timeframe",
                "insert into",
                "sqlite3.connect",
                "commit(",
                "arunda.db",
            )
        ):

            print(
                f"{i:5d}: {line[:220]}"
            )

print()
print("=" * 100)
print("SAFETY")
print("=" * 100)
print("PRODUCTION_DB_TOUCHED=FALSE")
print("DB_WRITES=0")
print("PRODUCERS_EXECUTED=FALSE")
print("FUSION_EXECUTED=FALSE")
print("SCORE=OFF")
print("DECISION=OFF")
print("ORDER_INTENTS=0")
print("EXECUTION=OFF")
print("FABRIC_MODIFIED=FALSE")
print()
print("=" * 100)
print("RESOLUTION COMPLETE")
print("=" * 100)
