from pathlib import Path
import ast

FILE = Path(r"C:\Users\ASUS\ArundaTrader\arunda_pipeline.py")

print("=" * 100)
print("ARUNDA PIPELINE API DISCOVERY v0.1")
print("=" * 100)
print(f"FILE={FILE}")
print("MODE=READ_ONLY")
print("FILES_MODIFIED=0")
print()

if not FILE.exists():
    raise RuntimeError(f"FILE_NOT_FOUND={FILE}")

source = FILE.read_text(
    encoding="utf-8",
    errors="replace",
)

tree = ast.parse(source)

keywords = (
    "decision",
    "risk",
    "budget",
    "position",
    "sizing",
    "trade_gate",
    "opportunity",
    "score",
)

functions = []

for node in ast.walk(tree):

    if isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef),
    ):

        name = node.name.lower()

        if any(
            keyword in name
            for keyword in keywords
        ):

            functions.append(
                (
                    node.lineno,
                    node.name,
                    len(node.args.args),
                )
            )

print("DISCOVERED_RELEVANT_FUNCTIONS")
print("-" * 100)

for lineno, name, argc in sorted(functions):

    print(
        f"LINE={lineno:<6} "
        f"ARGS={argc:<3} "
        f"FUNCTION={name}"
    )

print()
print("MODULE_IMPORTS")
print("-" * 100)

for node in tree.body:

    if isinstance(node, ast.Import):

        for alias in node.names:
            print(
                f"IMPORT={alias.name}"
            )

    elif isinstance(node, ast.ImportFrom):

        module = node.module or ""

        print(
            f"FROM={module}"
        )

        for alias in node.names:
            print(
                f"  NAME={alias.name}"
            )

print()
print("TRADE_GATE_REFERENCES")
print("-" * 100)

lines = source.splitlines()

for i, line in enumerate(lines, start=1):

    lower = line.lower()

    if (
        "trade_gate" in lower
        or "risk_budget" in lower
        or "position_siz" in lower
        or "risk_stage" in lower
        or "decision" in lower
    ):

        print(
            f"{i:>6}: {line.rstrip()}"
        )

print()
print("=" * 100)
print("DISCOVERY_COMPLETE")
print("DB_WRITES=0")
print("FILES_MODIFIED=0")
print("=" * 100)
