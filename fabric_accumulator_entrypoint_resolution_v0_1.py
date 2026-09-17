from pathlib import Path
import ast

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

files = [
    p for p in ROOT.glob("*.py")
    if any(
        x in p.name.lower()
        for x in ["accumul", "canonical", "fabric", "rolling"]
    )
]

print("=" * 100)
print("ARUNDA FABRIC ACCUMULATOR ENTRYPOINT RESOLUTION v0.1")
print("=" * 100)

for path in sorted(files):

    print()
    print("=" * 100)
    print("FILE:", path.name)
    print("SIZE:", path.stat().st_size)
    print("=" * 100)

    try:
        source = path.read_text(
            encoding="utf-8-sig",
            errors="ignore"
        )
        tree = ast.parse(source, filename=str(path))
    except Exception as e:
        print(
            "AST_PARSE=FAIL",
            type(e).__name__,
            str(e)
        )
        continue

    funcs = []

    for node in tree.body:
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            funcs.append(node.name)

    print("TOP_LEVEL_FUNCTIONS:")
    for name in funcs:
        print(" ", name)

    print()
    print("ACCUMULATOR_RELEVANT_LINES:")

    lines = source.splitlines()

    keywords = [
        "insert_candle",
        "canonical_ohlcv",
        "KUCOIN",
        "SOURCE_ID",
        "SOURCE_TYPE",
        "TIMEFRAME",
        "TARGET_DEPTH",
        "MIN_REAL_BARS",
        "fetch",
        "run(",
        "main(",
    ]

    for i, line in enumerate(lines, 1):
        if any(k.lower() in line.lower() for k in keywords):
            print(f"{i:5}: {line}")

print()
print("=" * 100)
print("SAFETY")
print("=" * 100)
print("SOURCE_INSPECTION_ONLY=TRUE")
print("FILES_EXECUTED=FALSE")
print("FABRIC_MODIFIED=FALSE")
print("PRODUCTION_DB_TOUCHED=FALSE")
print("DB_WRITES=0")
print("SIGNAL_CHAIN_EXECUTED=FALSE")
print("FUSION_EXECUTED=FALSE")
print("ORDER_INTENTS=0")
print("EXECUTION=OFF")
print("=" * 100)
