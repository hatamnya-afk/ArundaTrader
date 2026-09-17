from pathlib import Path
import ast

path = Path("market_arm_contiguous_history_accumulation_v0_1.py")

print("=" * 100)
print("ARUNDA MARKET ARM — EXISTING CONTIGUOUS ACCUMULATOR INSPECTION v0.1")
print("=" * 100)
print("FILE:", path)
print()

source = path.read_text(
    encoding="utf-8-sig",
    errors="ignore"
)

tree = ast.parse(source, filename=str(path))
lines = source.splitlines()

for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        print("-" * 100)
        print("FUNCTION:", node.name)
        print("-" * 100)

        start = node.lineno
        end = getattr(node, "end_lineno", start)

        for i in range(start, min(end, len(lines)) + 1):
            print(f"{i:5}: {lines[i-1]}")

print()
print("=" * 100)
print("TOP_LEVEL_CONSTANTS")
print("=" * 100)

for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                if name.isupper():
                    try:
                        value = ast.literal_eval(node.value)
                    except Exception:
                        value = "<NON_LITERAL>"
                    print(f"{name} = {value!r}")

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
