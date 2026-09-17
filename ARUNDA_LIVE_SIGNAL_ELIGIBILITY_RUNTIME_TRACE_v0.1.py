import ast
import hashlib
import importlib.util
import inspect
import sqlite3
from pathlib import Path

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB = ROOT / "arunda.db"

print("=" * 100)
print("ARUNDA LIVE SIGNAL ELIGIBILITY RUNTIME TRACE v0.1")
print("=" * 100)
print("MODE        : READ ONLY / RUNTIME TRACE")
print("TARGET      : REAL POST-LAUNCH DATA")
print("ORDERS      : NONE")
print("NETWORK     : NONE")
print("DB WRITE    : NONE")
print()

if not ROOT.exists():
    raise RuntimeError(f"PROJECT ROOT NOT FOUND: {ROOT}")

if not DB.exists():
    raise RuntimeError(f"DATABASE NOT FOUND: {DB}")

# ------------------------------------------------------------
# READ-ONLY DB
# ------------------------------------------------------------

uri = f"file:{DB.as_posix()}?mode=ro"
conn = sqlite3.connect(uri, uri=True)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA query_only=1")

print("SQLite query_only :", conn.execute("PRAGMA query_only").fetchone()[0])

# ------------------------------------------------------------
# DISCOVER CURRENT PRODUCTION MODULES
# ------------------------------------------------------------

keywords = (
    "signal",
    "fusion",
    "eligib",
    "order_intent",
    "execution_gate",
    "release_preflight",
)

files = []

for p in ROOT.glob("*.py"):
    name = p.name.lower()
    if any(k in name for k in keywords):
        files.append(p)

print()
print("=" * 100)
print("CURRENT PATH CANDIDATES")
print("=" * 100)

for p in sorted(files):
    print(p.name)

# ------------------------------------------------------------
# LOAD MODULES WITHOUT RUNNING main()
# ------------------------------------------------------------

loaded = {}

for path in sorted(files):
    try:
        spec = importlib.util.spec_from_file_location(
            f"_forensic_{path.stem}",
            path
        )

        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        loaded[path.name] = module

    except Exception as e:
        print(f"[LOAD SKIP] {path.name}: {type(e).__name__}: {e}")

print()
print("=" * 100)
print("LOADED MODULES")
print("=" * 100)

for name in loaded:
    print(name)

# ------------------------------------------------------------
# FUNCTION DISCOVERY
# ------------------------------------------------------------

print()
print("=" * 100)
print("CURRENT RUNTIME FUNCTIONS")
print("=" * 100)

targets = [
    "process_signals",
    "generate_signal",
    "generate_signals",
    "build_signal",
    "create_signal",
    "evaluate_signal",
    "check_eligibility",
    "is_eligible",
    "validate_signal",
    "generate_order_intent",
    "build_order_intent",
    "validate_order_intent",
]

found = []

for filename, module in loaded.items():

    for name in targets:

        fn = getattr(module, name, None)

        if callable(fn):

            try:
                sig = inspect.signature(fn)
            except Exception:
                sig = "?"

            found.append((filename, name, sig))

            print(
                f"{filename:<65} "
                f"{name:<30} "
                f"{sig}"
            )

# ------------------------------------------------------------
# DB TABLES
# ------------------------------------------------------------

print()
print("=" * 100)
print("CURRENT PRODUCTION TABLES")
print("=" * 100)

tables = conn.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
    """
).fetchall()

for r in tables:
    n = r["name"].lower()

    if any(
        x in n
        for x in [
            "signal",
            "fusion",
            "order",
            "technical",
            "market"
        ]
    ):
        print(r["name"])

# ------------------------------------------------------------
# LIVE ROW SOURCE
# ------------------------------------------------------------

print()
print("=" * 100)
print("LIVE SIGNAL SOURCE")
print("=" * 100)

signal_tables = [
    r["name"]
    for r in tables
    if "signal" in r["name"].lower()
]

for table in signal_tables:

    try:
        cols = conn.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()

        names = {r["name"] for r in cols}

        if "id" not in names:
            continue

        order = "id DESC"

        rows = conn.execute(
            f'''
            SELECT *
            FROM "{table}"
            ORDER BY {order}
            LIMIT 20
            '''
        ).fetchall()

        print()
        print(f"TABLE : {table}")
        print(f"ROWS  : {len(rows)}")

        for row in rows[:5]:

            vals = []

            for key in [
                "id",
                "symbol",
                "timestamp",
                "signal",
                "signal_type",
                "direction",
                "score",
                "fused_score",
                "eligible",
                "eligibility",
                "status",
            ]:

                if key in row.keys():
                    vals.append(
                        f"{key}={row[key]}"
                    )

            print("  " + " | ".join(vals))

    except Exception as e:
        print(
            f"[READ ERROR] {table}: "
            f"{type(e).__name__}: {e}"
        )

# ------------------------------------------------------------
# STATIC CALL GRAPH — ONLY CURRENT SIGNAL/ELIGIBILITY FILES
# ------------------------------------------------------------

print()
print("=" * 100)
print("CURRENT PATH CALL REFERENCES")
print("=" * 100)

for path in sorted(files):

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace"
        )

        tree = ast.parse(text)

    except Exception:
        continue

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            name = None

            if isinstance(node.func, ast.Name):
                name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            if name in {
                "process_signals",
                "generate_signal",
                "generate_signals",
                "build_signal",
                "create_signal",
                "evaluate_signal",
                "check_eligibility",
                "is_eligible",
                "validate_signal",
                "generate_order_intent",
                "build_order_intent",
                "validate_order_intent",
            }:

                print(
                    f"FILE={path.name} "
                    f"LINE={node.lineno} "
                    f"CALL={name}"
                )

# ------------------------------------------------------------
# HARD SAFETY PROOF
# ------------------------------------------------------------

print()
print("=" * 100)
print("SAFETY CONTRACT")
print("=" * 100)
print("PRODUCTION main()       : NOT EXECUTED")
print("INSERT                  : NONE")
print("UPDATE                  : NONE")
print("DELETE                  : NONE")
print("COMMIT                  : NONE")
print("ORDER CREATION          : NONE")
print("ORDER SUBMISSION        : NONE")
print("NETWORK ORDER           : NONE")
print("REAL TRADE              : NONE")
print()
print("=" * 100)
print("TRACE DISCOVERY COMPLETE")
print("=" * 100)

conn.close()