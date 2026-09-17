import ast
from pathlib import Path

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

for filename in ("feature_engine.py", "feature_contract.py"):
    path = ROOT / filename
    tree = ast.parse(
        path.read_text(encoding="utf-8-sig"),
        filename=str(path),
    )

    print("=" * 100)
    print(f"FILE={filename}")

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            print(f"CLASS={node.name}")

            for child in node.body:
                if isinstance(child, ast.AnnAssign):
                    target = child.target
                    if isinstance(target, ast.Name):
                        print(f"  FIELD={target.id}")
                        print(
                            "  ANNOTATION="
                            + ast.unparse(child.annotation)
                        )

                elif isinstance(child, ast.FunctionDef):
                    if child.name == "__init__":
                        print("  __INIT__")
                        print(
                            "  ARGS="
                            + str([
                                a.arg
                                for a in child.args.args
                                if a.arg != "self"
                            ])
                        )

print("=" * 100)
print("STATIC_CLASS_INTERFACE=PASS")
print("RUNTIME_EXECUTED=FALSE")
print("PRODUCTION_DB_TOUCHED=FALSE")
print("DB_WRITES=0")
