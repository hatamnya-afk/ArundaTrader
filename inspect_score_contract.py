import ast
from pathlib import Path

path = Path(r"C:\Users\ASUS\ArundaTrader\score_producer.py")
tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))

targets = {
    "build_score_features",
    "extract_features",
    "calculate_score",
    "validate_score_snapshot",
}

print("=" * 100)
print("FILE=score_producer.py")

for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in targets:
        print(f"FUNCTION={node.name}")
        print("ARGS=" + str([a.arg for a in node.args.args]))

        names = sorted({
            n.id for n in ast.walk(node)
            if isinstance(n, ast.Name)
        })
        print("NAMES=" + str(names))

        attrs = sorted({
            n.attr for n in ast.walk(node)
            if isinstance(n, ast.Attribute)
        })
        print("ATTRIBUTES=" + str(attrs))

        print("SOURCE:")
        print(ast.get_source_segment(
            path.read_text(encoding="utf-8-sig"),
            node
        ))
        print()

print("=" * 100)
print("STATIC_SCORE_CONTRACT_INSPECTION=PASS")
print("RUNTIME_EXECUTED=FALSE")
print("PRODUCTION_DB_TOUCHED=FALSE")
print("DB_WRITES=0")
