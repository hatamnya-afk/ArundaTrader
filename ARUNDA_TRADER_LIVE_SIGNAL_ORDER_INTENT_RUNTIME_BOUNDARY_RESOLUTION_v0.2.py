# -*- coding: utf-8 -*-

from pathlib import Path
import ast
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

print("=" * 100)
print("ARUNDA TRADER LIVE SIGNAL ORDER INTENT RUNTIME BOUNDARY RESOLUTION v0.2")
print("=" * 100)
print("Started UTC :", datetime.now(timezone.utc).isoformat())
print("ROOT        :", ROOT)
print("MODE        : READ ONLY FORENSIC")
print("WRITES      : NONE")
print("=" * 100)


# ============================================================
# TARGET TERMS
# ============================================================

TERMS = [
    "order_intent",
    "order-intent",
    "order intent",
    "validation",
    "validator",
    "execution_gate",
    "execution_preflight",
    "execution",
    "live_signal",
    "trade_plan",
    "signal_execution",
]


def hit(line):
    x = line.lower()
    return any(t in x for t in TERMS)


# ============================================================
# FILES
# ============================================================

files = sorted(ROOT.glob("*.py"))

print("\n" + "-" * 100)
print("1. TARGET FILE DISCOVERY")
print("-" * 100)

target_files = []

for p in files:
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    if any(t in text.lower() for t in TERMS):
        target_files.append(p)

        print(p.name)

print("\nTARGET FILE COUNT :", len(target_files))


# ============================================================
# FUNCTION INDEX
# ============================================================

print("\n" + "-" * 100)
print("2. FUNCTION / CLASS INDEX")
print("-" * 100)

function_index = {}

for p in files:

    try:
        source = p.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(p))
    except Exception:
        continue

    funcs = []

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

            funcs.append({
                "name": node.name,
                "line": node.lineno,
                "args": [
                    a.arg for a in node.args.args
                ],
            })

    if funcs:
        function_index[p.name] = funcs

    for f in funcs:

        lname = f["name"].lower()

        if any(t.replace("-", "_").replace(" ", "_") in lname
               for t in TERMS):

            print(
                f"{p.name:70} "
                f"LINE {f['line']:6} "
                f"FUNCTION {f['name']} "
                f"ARGS={f['args']}"
            )


# ============================================================
# EXACT REFERENCES
# ============================================================

print("\n" + "-" * 100)
print("3. EXACT SOURCE REFERENCES")
print("-" * 100)

references = []

for p in files:

    try:
        lines = p.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines()
    except Exception:
        continue

    for i, line in enumerate(lines, 1):

        if hit(line):

            references.append(
                (p.name, i, line.strip())
            )

for filename, lineno, line in references:

    print(
        f"{filename:70} "
        f"LINE {lineno:6} : {line}"
    )

print("\nREFERENCE COUNT :", len(references))


# ============================================================
# AST CALL GRAPH
# ============================================================

print("\n" + "-" * 100)
print("4. CALL GRAPH CANDIDATES")
print("-" * 100)

call_records = []

for p in files:

    try:
        source = p.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        tree = ast.parse(source, filename=str(p))

    except Exception:
        continue

    current_function = "<MODULE>"

    nodes = []

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nodes.append(node)

    for fn in nodes:

        current_function = fn.name

        for node in ast.walk(fn):

            if not isinstance(node, ast.Call):
                continue

            called = None

            if isinstance(node.func, ast.Name):
                called = node.func.id

            elif isinstance(node.func, ast.Attribute):
                called = node.func.attr

            if called is None:
                continue

            lname = called.lower()

            if any(
                t.replace("-", "_").replace(" ", "_") in lname
                for t in TERMS
            ):

                call_records.append(
                    (
                        p.name,
                        fn.name,
                        node.lineno,
                        called
                    )
                )

for r in call_records:

    print(
        f"FILE={r[0]:65} "
        f"FUNCTION={r[1]:35} "
        f"LINE={r[2]:6} "
        f"CALL={r[3]}"
    )

print("\nCALL RECORD COUNT :", len(call_records))


# ============================================================
# IMPORT GRAPH
# ============================================================

print("\n" + "-" * 100)
print("5. IMPORT GRAPH")
print("-" * 100)

imports = []

for p in files:

    try:
        tree = ast.parse(
            p.read_text(
                encoding="utf-8",
                errors="ignore"
            ),
            filename=str(p)
        )
    except Exception:
        continue

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                lname = alias.name.lower()

                if any(
                    t.replace("-", "_").replace(" ", "_") in lname
                    for t in TERMS
                ):

                    imports.append(
                        (
                            p.name,
                            node.lineno,
                            "import",
                            alias.name
                        )
                    )

        elif isinstance(node, ast.ImportFrom):

            module = node.module or ""

            if any(
                t.replace("-", "_").replace(" ", "_")
                in module.lower()
                for t in TERMS
            ):

                imports.append(
                    (
                        p.name,
                        node.lineno,
                        "from",
                        module
                    )
                )

            for alias in node.names:

                lname = alias.name.lower()

                if any(
                    t.replace("-", "_").replace(" ", "_") in lname
                    for t in TERMS
                ):

                    imports.append(
                        (
                            p.name,
                            node.lineno,
                            "from-name",
                            alias.name
                        )
                    )

for r in imports:

    print(
        f"{r[0]:70} "
        f"LINE {r[1]:6} "
        f"{r[2]:12} "
        f"{r[3]}"
    )

print("\nIMPORT RECORD COUNT :", len(imports))


# ============================================================
# ENTRYPOINTS
# ============================================================

print("\n" + "-" * 100)
print("6. ENTRYPOINT / MAIN CANDIDATES")
print("-" * 100)

entrypoints = []

for p in files:

    try:
        source = p.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        tree = ast.parse(source, filename=str(p))

    except Exception:
        continue

    main_functions = []
    main_guards = []

    for node in ast.walk(tree):

        if isinstance(node, ast.FunctionDef):

            if node.name == "main":
                main_functions.append(node.lineno)

        if isinstance(node, ast.If):

            try:

                text = ast.unparse(node.test)

                if "__name__" in text and "__main__" in text:
                    main_guards.append(node.lineno)

            except Exception:
                pass

    if main_functions or main_guards:

        entrypoints.append(
            (
                p.name,
                main_functions,
                main_guards
            )
        )

        print(
            f"{p.name:70} "
            f"main={main_functions} "
            f"guard={main_guards}"
        )


# ============================================================
# MAIN CALLS TO TARGET FUNCTIONS
# ============================================================

print("\n" + "-" * 100)
print("7. MAIN -> TARGET CALL CHAINS")
print("-" * 100)

for p in files:

    try:
        source = p.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        tree = ast.parse(source, filename=str(p))

    except Exception:
        continue

    mains = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef)
        and n.name == "main"
    ]

    for main in mains:

        for node in ast.walk(main):

            if not isinstance(node, ast.Call):
                continue

            called = None

            if isinstance(node.func, ast.Name):
                called = node.func.id

            elif isinstance(node.func, ast.Attribute):
                called = node.func.attr

            if called and (
                any(
                    t.replace("-", "_").replace(" ", "_")
                    in called.lower()
                    for t in TERMS
                )
            ):

                print(
                    f"{p.name:70} "
                    f"main() LINE {node.lineno:6} "
                    f"-> {called}"
                )


# ============================================================
# SOURCE WINDOWS
# ============================================================

print("\n" + "-" * 100)
print("8. SOURCE WINDOWS — TARGET REFERENCES")
print("-" * 100)

for p in target_files:

    try:
        lines = p.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines()
    except Exception:
        continue

    positions = []

    for i, line in enumerate(lines):

        if hit(line):
            positions.append(i)

    if not positions:
        continue

    print("\n" + "=" * 100)
    print("FILE :", p.name)
    print("=" * 100)

    shown = set()

    for pos in positions:

        start = max(0, pos - 5)
        end = min(len(lines), pos + 8)

        key = (start, end)

        if key in shown:
            continue

        shown.add(key)

        print(
            f"\n--- SOURCE LINES {start + 1}-{end} ---"
        )

        for j in range(start, end):

            print(
                f"{j + 1:6}: {lines[j]}"
            )


# ============================================================
# CONTRACT FIELD FLOW
# ============================================================

print("\n" + "-" * 100)
print("9. CONTRACT FIELD FLOW REFERENCES")
print("-" * 100)

FIELD_TERMS = [
    "asset",
    "direction",
    "entry_price",
    "fused_score",
    "confidence",
    "signal_strength",
    "engine_version",
    "snapshot_id",
]

for p in target_files:

    try:
        lines = p.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines()
    except Exception:
        continue

    matches = []

    for i, line in enumerate(lines, 1):

        lower = line.lower()

        if any(
            f in lower
            for f in FIELD_TERMS
        ):

            if any(
                t in lower
                for t in [
                    "order",
                    "intent",
                    "valid",
                    "execution",
                    "gate",
                    "preflight",
                    "signal",
                ]
            ):

                matches.append((i, line.strip()))

    if matches:

        print("\nFILE :", p.name)

        for i, line in matches:

            print(
                f"{i:6}: {line}"
            )


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 100)
print("RESOLUTION STATUS")
print("=" * 100)

print("""
A) REAL PRODUCTION/RUNTIME CONSUMER
   -> MUST BE RESOLVED FROM IMPORT/CALL/ENTRYPOINT EVIDENCE

B) EXACT CALL SITE
   -> MUST BE RESOLVED

C) EXACT INPUT OBJECT / ROW
   -> MUST BE RESOLVED

D) EXACT VALIDATION FUNCTION
   -> MUST BE RESOLVED

E) EXACT VALIDATION OUTPUT
   -> MUST BE RESOLVED

F) EXACT DOWNSTREAM EXECUTION CONSUMER
   -> MUST BE RESOLVED

G) FIRST CONTRACT MISMATCH
   -> MUST BE LOCALIZED BEFORE ANY REPAIR

NO SOURCE MODIFICATION
NO DATABASE MODIFICATION
NO REPAIR
NO EXECUTION
""")

print("=" * 100)
print("END OF FORENSIC")
print("=" * 100)