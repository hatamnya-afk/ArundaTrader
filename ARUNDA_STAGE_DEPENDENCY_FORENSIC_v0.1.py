import ast
import os

FILES = [
    "market_snapshot_engine.py",
    "market_data_engine.py",
    "opportunity_engine.py",
    "decision_engine.py",
    "risk_engine.py",
    "trade_gate_engine.py",
]

print("=" * 90)
print("ARUNDA STAGE DEPENDENCY FORENSIC")
print("=" * 90)
print("MODE : READ ONLY")
print("DATABASE : NOT USED")
print("NETWORK : NOT USED")
print("EXECUTION : NOT PERFORMED")
print("=" * 90)

for filename in FILES:
    print()
    print("-" * 90)
    print("FILE :", filename)

    if not os.path.isfile(filename):
        print("STATUS : MISSING")
        continue

    source = open(filename, "r", encoding="utf-8").read()

    try:
        tree = ast.parse(source, filename=filename)
        print("SYNTAX : PASS")
    except SyntaxError as exc:
        print("SYNTAX : FAIL")
        print("ERROR  :", exc)
        continue

    imports = []
    dangerous_calls = []
    upgrade_refs = []

    for node in ast.walk(tree):

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            text = ast.unparse(node)
            imports.append((node.lineno, text))

            if "upgrade_db" in text.lower():
                upgrade_refs.append((node.lineno, text))

        elif isinstance(node, ast.Call):
            func = ast.unparse(node.func)

            if func in {
                "exec",
                "eval",
                "__import__",
                "os.system",
                "os.popen",
                "subprocess.run",
                "subprocess.call",
                "subprocess.Popen",
                "subprocess.check_call",
                "subprocess.check_output",
                "runpy.run_module",
                "runpy.run_path",
                "importlib.import_module",
            }:
                dangerous_calls.append((node.lineno, func))

            try:
                call_text = ast.unparse(node)
            except Exception:
                call_text = func

            if "upgrade_db" in call_text.lower():
                upgrade_refs.append((node.lineno, call_text))

    for number, line in enumerate(source.splitlines(), 1):
        if "upgrade_db" in line.lower():
            item = (number, line.strip())
            if item not in upgrade_refs:
                upgrade_refs.append(item)

    print()
    print("IMPORTS :")
    if imports:
        for line, text in imports:
            print(f"  LINE {line:4} : {text}")
    else:
        print("  NONE")

    print()
    print("DYNAMIC / PROCESS CALLS :")
    if dangerous_calls:
        for line, func in dangerous_calls:
            print(f"  LINE {line:4} : {func}")
    else:
        print("  NONE")

    print()
    print("UPGRADE_DB REFERENCES :")
    if upgrade_refs:
        seen = set()
        for line, text in upgrade_refs:
            key = (line, text)
            if key not in seen:
                print(f"  LINE {line:4} : {text}")
                seen.add(key)
    else:
        print("  NONE")

print()
print("=" * 90)
print("FORENSIC VERDICT")
print("=" * 90)
print("No stage was executed.")
print("No database was opened.")
print("No SQL was executed.")
print("No network connection was used.")
print("=" * 90)
