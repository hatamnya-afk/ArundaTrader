import ast
from pathlib import Path

path = Path(r"C:\Users\ASUS\ArundaTrader\score_producer.py")

tree = ast.parse(
    path.read_text(encoding="utf-8-sig"),
    filename=str(path),
)

print("=" * 100)
print("FILE=score_producer.py")

for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        print(f"FUNCTION={node.name}")
        print("ARGS=" + str([a.arg for a in node.args.args]))

    elif isinstance(node, ast.ClassDef):
        print(f"CLASS={node.name}")
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                print(f"  METHOD={child.name}")
                print("  ARGS=" + str([a.arg for a in child.args.args]))

print("=" * 100)
print("STATIC_AST_INSPECTION=PASS")
print("RUNTIME_EXECUTED=FALSE")
print("PRODUCTION_DB_TOUCHED=FALSE")
print("DB_WRITES=0")
