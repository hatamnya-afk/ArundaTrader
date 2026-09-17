import ast
from pathlib import Path

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

for filename in ("feature_engine.py", "feature_contract.py"):
    path = ROOT / filename
    print("=" * 100)
    print(f"FILE={filename}")

    tree = ast.parse(
        path.read_text(encoding="utf-8-sig"),
        filename=str(path),
    )

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            print(f"FUNCTION={node.name}")
            print(f"ARGS={args}")

        elif isinstance(node, ast.ClassDef):
            print(f"CLASS={node.name}")
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [a.arg for a in child.args.args]
                    print(f"  METHOD={child.name}")
                    print(f"  ARGS={args}")

    print()

print("=" * 100)
print("STATIC_AST_INSPECTION=PASS")
print("RUNTIME_EXECUTED=FALSE")
print("PRODUCTION_DB_TOUCHED=FALSE")
print("DB_WRITES=0")
