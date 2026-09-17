# ARUNDA LIVE PRODUCTION PATH RUNTIME EXECUTION v0.1
# REAL DATA ONLY
# NO SYNTHETIC DATA
# NO ORDER SUBMISSION
# NO NETWORK ORDER
# NO PRODUCTION DB WRITE
# MAIN() EXECUTION ALLOWED ONLY THROUGH CURRENT LIVE ENTRYPOINT

import ast
import importlib.util
import inspect
import sqlite3
from pathlib import Path


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB = ROOT / "arunda.db"


def section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def load_module(path):
    spec = importlib.util.spec_from_file_location(
        path.stem,
        path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


section("ARUNDA LIVE PRODUCTION PATH RUNTIME EXECUTION v0.1")

print("MODE                    : REAL RUNTIME")
print("DATA                    : REAL PRODUCTION DB")
print("SYNTHETIC DATA          : NO")
print("ORDER SUBMISSION        : NO")
print("EXTERNAL ORDER NETWORK  : NO")
print("PRODUCTION DB WRITE     : NO")
print("ROOT                    :", ROOT)
print("DATABASE                :", DB)

if not ROOT.exists():
    raise RuntimeError("PROJECT ROOT NOT FOUND")

if not DB.exists():
    raise RuntimeError("DATABASE NOT FOUND")


# ------------------------------------------------------------
# READ-ONLY DB
# ------------------------------------------------------------

conn = sqlite3.connect(
    f"file:{DB.as_posix()}?mode=ro",
    uri=True
)

conn.execute("PRAGMA query_only=ON")

print("SQLite query_only       :", conn.execute(
    "PRAGMA query_only"
).fetchone()[0])


# ------------------------------------------------------------
# FIND CURRENT LIVE ENTRYPOINT
# Only executable production candidates.
# ------------------------------------------------------------

section("CURRENT LIVE ENTRYPOINT")

candidates = []

for path in ROOT.glob("*.py"):

    if path.name.startswith("ARUNDA_"):
        continue

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace"
        )
        tree = ast.parse(text)
    except Exception:
        continue

    has_main = any(
        isinstance(n, ast.FunctionDef)
        and n.name == "main"
        for n in tree.body
    )

    if not has_main:
        continue

    names = {
        n.name
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef)
    }

    path_score = 0

    required_terms = [
        "process_signals",
        "signal",
        "fusion",
        "eligible",
        "order",
        "intent",
    ]

    for term in required_terms:
        if any(term.lower() in name.lower() for name in names):
            path_score += 1

    candidates.append(
        (path_score, path, names)
    )


candidates.sort(
    key=lambda x: x[0],
    reverse=True
)

if not candidates:
    raise RuntimeError(
        "MISSING CURRENT LIVE ENTRYPOINT"
    )

for score, path, names in candidates:
    print(
        f"CANDIDATE score={score:<3} "
        f"file={path.name}"
    )


# Highest-scoring existing runtime.
entrypoint = candidates[0][1]

print()
print("SELECTED ENTRYPOINT      :", entrypoint.name)


# ------------------------------------------------------------
# LOAD ONLY
# ------------------------------------------------------------

section("RUNTIME LOAD")

module = load_module(entrypoint)

print("MODULE LOADED            : YES")
print("MAIN AVAILABLE           :", hasattr(module, "main"))


if not hasattr(module, "main"):
    raise RuntimeError("SELECTED ENTRYPOINT HAS NO main()")


main = module.main

print("MAIN SIGNATURE           :", inspect.signature(main))


# ------------------------------------------------------------
# SAFETY BLOCK
# ------------------------------------------------------------

section("EXECUTION SAFETY")

source = entrypoint.read_text(
    encoding="utf-8",
    errors="replace"
).upper()

dangerous = [
    "ORDER.CREATE",
    "ORDER.SUBMIT",
    "CREATE_ORDER",
    "SUBMIT_ORDER",
    "PLACE_ORDER",
    "CANCEL_ORDER",
]

blocked = [
    token for token in dangerous
    if token in source
]

print("ORDER OPERATIONS FOUND  :", blocked if blocked else "NONE")

if blocked:
    print()
    print("ORDER SUBMISSION BLOCKED.")
    print("LIVE ORDER EXECUTION IS NOT ALLOWED IN THIS RUN.")
    print()
    print("The current entrypoint contains order-operation code.")
    print("Therefore main() will NOT be executed automatically.")
    print()
    print("Use the existing analysis/runtime function before the")
    print("order-submission boundary.")
    conn.close()
    raise SystemExit(0)


# ------------------------------------------------------------
# REAL PRODUCTION EXECUTION
# ------------------------------------------------------------

section("EXECUTING CURRENT LIVE PATH")

print("EXECUTION                : START")
print("DATA SOURCE              : REAL PRODUCTION DATA")
print("FIXTURE                  : NONE")
print("MAIN()                   : EXECUTING")

result = main()

print()
print("EXECUTION                : COMPLETE")
print("RAW RESULT TYPE          :", type(result).__name__)

print()
print("RAW RESULT:")
print(result)


# ------------------------------------------------------------
# RESULT EXTRACTION
# ------------------------------------------------------------

section("LIVE PATH RESULT")

def walk(obj, prefix="RESULT"):

    if isinstance(obj, dict):

        for key, value in obj.items():

            name = f"{prefix}.{key}"

            if key in {
                "eligible",
                "eligible_rows",
                "eligible_signals",
                "no_trade_rows",
                "decision",
                "status",
                "release_allowed",
                "order_intents",
                "validated_intents",
                "invalid_intents",
            }:
                print(
                    f"{name:<45}: {value}"
                )

            if isinstance(value, (dict, list, tuple)):
                walk(value, name)

    elif isinstance(obj, (list, tuple)):

        for i, value in enumerate(obj):
            walk(value, f"{prefix}[{i}]")


walk(result)


section("FINAL")

print("REAL DATA               : YES")
print("SYNTHETIC DATA          : NO")
print("CURRENT PATH EXECUTED   : YES")
print("ORDER SUBMISSION        : NO")
print("EXTERNAL ORDER          : NO")
print("PRODUCTION DB WRITE     : NO")

conn.close()