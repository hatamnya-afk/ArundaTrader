from pathlib import Path
import ast

files = [
    Path("historical_fabric_depth_accumulator_v0_2.py"),
    Path("public_market_data_kucoin.py"),
    Path("local_canonical_store_v0.1.py"),
]

print("=" * 100)
print("ARUNDA MARKET ARM — KUCOIN FETCH API RESOLUTION v0.1")
print("=" * 100)

for path in files:
    print()
    print("=" * 100)
    print("FILE:", path.name)
    print("=" * 100)

    source = path.read_text(
        encoding="utf-8-sig",
        errors="ignore"
    )
    tree = ast.parse(source, filename=str(path))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in {
                "fetch_kucoin",
                "fetch_bitget",
                "validate_candle",
                "build_canonical_candle",
                "insert_candle",
                "normalize",
                "validate_candle",
            }:
                print()
                print("-" * 80)
                print("FUNCTION:", node.name)
                print("-" * 80)

                start = node.lineno
                end = getattr(node, "end_lineno", start)

                lines = source.splitlines()
                for i in range(start, min(end, len(lines)) + 1):
                    print(f"{i:5}: {lines[i-1]}")

print()
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
