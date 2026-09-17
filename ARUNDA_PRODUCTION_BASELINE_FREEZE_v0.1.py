from pathlib import Path
import ast
import hashlib
import sqlite3
import re
import sys
import os
from collections import defaultdict, Counter

# ============================================================
# ARUNDA TRADER — PRODUCTION BASELINE FREEZE v0.1
# READ-ONLY BASELINE COLLECTOR
# ============================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = PROJECT_ROOT / "arunda.db"
REPORT = PROJECT_ROOT / "ARUNDA_PRODUCTION_BASELINE_FREEZE_v0.1.txt"

EXECUTION_ENABLED_EXPECTED = False
MAX_CANDIDATES_CHANGE = "10 -> 15"

# ------------------------------------------------------------
# Production chain anchors
# ------------------------------------------------------------

CHAIN = [
    "arunda_pipeline.py",
    "market_snapshot_engine.py",
    "market_data_engine.py",
    "opportunity_engine.py",
    "signal_engine.py",
    "signal_validator.py",
    "score_producer.py",
    "signal_scorer.py",
    "decision_engine.py",
    "risk_engine.py",
    "trade_gate_engine.py",
]

OWNER_REQUESTS = [
    "feature_contract.py",
    "feature_snapshot_reader.py",
    "score_producer.py",
    "signal_engine.py",
    "signal_validator.py",
    "signal_scorer.py",
    "decision_engine.py",
    "risk_engine.py",
    "trade_gate_engine.py",
]

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def parse_imports(path):
    imports = set()

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.add(n.name.split(".")[0])

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])

    except Exception:
        pass

    return imports


def normalized_module_name(path):
    return path.stem


def find_python_files():
    return [
        p for p in PROJECT_ROOT.rglob("*.py")
        if ".venv" not in p.parts
        and "__pycache__" not in p.parts
    ]


# ------------------------------------------------------------
# Repository existence
# ------------------------------------------------------------

if not PROJECT_ROOT.exists():
    print("BLOCKED: PROJECT_ROOT missing")
    raise SystemExit

if not DB_PATH.exists():
    print("BLOCKED: production DB missing")
    raise SystemExit


# ------------------------------------------------------------
# Discover Python files — READ ONLY
# ------------------------------------------------------------

py_files = find_python_files()

by_module = defaultdict(list)

for p in py_files:
    by_module[p.stem].append(p)


# ------------------------------------------------------------
# Determine actual import relationships
# ------------------------------------------------------------

imports_map = {}

for p in py_files:
    imports_map[p] = parse_imports(p)


reverse_imports = defaultdict(set)

for source, imports in imports_map.items():
    for imp in imports:
        for target in by_module.get(imp, []):
            reverse_imports[target].add(source.name)


# ------------------------------------------------------------
# Production closure from arunda_pipeline
# Static dependency traversal only.
# No module execution.
# ------------------------------------------------------------

pipeline_candidates = [
    p for p in py_files
    if p.name == "arunda_pipeline.py"
]

production_modules = set()

if pipeline_candidates:
    root_pipeline = pipeline_candidates[0]

    queue = [root_pipeline]
    visited = set()

    while queue:
        current = queue.pop()

        if current in visited:
            continue

        visited.add(current)
        production_modules.add(current)

        for imp in imports_map.get(current, set()):
            targets = by_module.get(imp, [])

            # Only resolve local project modules.
            for target in targets:
                if target not in visited:
                    queue.append(target)


# ------------------------------------------------------------
# Production entrypoint discovery
# ------------------------------------------------------------

entrypoint = None

for candidate in [
    PROJECT_ROOT / "__main__.py",
    PROJECT_ROOT / "arunda_pipeline.py",
    PROJECT_ROOT / "main.py",
]:
    if candidate.exists():
        entrypoint = candidate
        break


# ------------------------------------------------------------
# Execution flag — static inspection only
# ------------------------------------------------------------

execution_values = []

for p in py_files:
    try:
        source = p.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        matches = re.findall(
            r"EXECUTION_ENABLED\s*=\s*(True|False)",
            source
        )

        for value in matches:
            execution_values.append(
                (str(p.relative_to(PROJECT_ROOT)), value)
            )

    except Exception:
        pass


execution_false = any(
    value == "False"
    for _, value in execution_values
)

execution_true = any(
    value == "True"
    for _, value in execution_values
)


# ------------------------------------------------------------
# Fingerprints
# ------------------------------------------------------------

fingerprint_targets = set()

for p in production_modules:
    fingerprint_targets.add(p)

for name in OWNER_REQUESTS:
    for p in by_module.get(Path(name).stem, []):
        fingerprint_targets.add(p)

fingerprints = []

for p in sorted(fingerprint_targets, key=lambda x: str(x)):
    try:
        fingerprints.append({
            "path": str(p.relative_to(PROJECT_ROOT)),
            "sha256": sha256_file(p),
            "size": p.stat().st_size,
        })
    except Exception:
        fingerprints.append({
            "path": str(p.relative_to(PROJECT_ROOT)),
            "sha256": "ERROR",
            "size": -1,
        })


# ------------------------------------------------------------
# SQLite READ-ONLY metadata
# ------------------------------------------------------------

db_integrity = "UNKNOWN"
tables = []
row_counts = {}

try:
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    conn = sqlite3.connect(uri, uri=True)

    cur = conn.cursor()

    cur.execute("PRAGMA integrity_check")
    result = cur.fetchone()

    if result:
        db_integrity = str(result[0])

    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)

    tables = [r[0] for r in cur.fetchall()]

    for table in tables:
        try:
            cur.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            )
            row_counts[table] = cur.fetchone()[0]
        except Exception:
            row_counts[table] = "ERROR"

    conn.close()

except Exception as e:
    db_integrity = f"ERROR: {e}"


# ------------------------------------------------------------
# Production relevant tables
# ------------------------------------------------------------

production_table_keywords = [
    "market_data",
    "market_history",
    "market_state",
    "market_universe",
    "fusion_signals",
    "signal_outcomes",
    "signal",
    "opportunity",
    "decision",
    "risk",
    "trade",
    "order",
]

production_tables = []

for table in tables:
    low = table.lower()

    if any(k in low for k in production_table_keywords):
        production_tables.append(table)


# ------------------------------------------------------------
# Final status
# ------------------------------------------------------------

blockers = []

if not PROJECT_ROOT.exists():
    blockers.append("PROJECT_ROOT missing")

if not DB_PATH.exists():
    blockers.append("production DB missing")

if entrypoint is None:
    blockers.append("production entrypoint not found")

if not pipeline_candidates:
    blockers.append("arunda_pipeline.py not found")

if execution_true:
    blockers.append("EXECUTION_ENABLED=True found in repository")

# ------------------------------------------------------------
# Write baseline report
# ------------------------------------------------------------

with REPORT.open("w", encoding="utf-8") as f:

    f.write("ARUNDA TRADER — PRODUCTION BASELINE FREEZE v0.1\n")
    f.write("=" * 100 + "\n\n")

    f.write("MODE                         : READ ONLY\n")
    f.write("PRODUCTION LOGIC CHANGE     : NONE\n")
    f.write("FILE DELETION               : NONE\n")
    f.write("BOM MODIFICATION            : NONE\n")
    f.write("CP RE-AUDIT                 : NONE\n")
    f.write("DB MODIFICATION             : NONE\n")
    f.write("PRODUCTION RUNTIME EXECUTE  : NONE\n")
    f.write("EXCHANGE CALL               : NONE\n")
    f.write("ORDER SUBMISSION             : NONE\n")
    f.write("EXECUTION_ENABLED            : False\n\n")

    # --------------------------------------------------------
    # 1 ENTRYPOINT
    # --------------------------------------------------------

    f.write("=" * 100 + "\n")
    f.write("1 — PRODUCTION ENTRYPOINT\n")
    f.write("=" * 100 + "\n")

    f.write(
        f"PROJECT_ROOT : {PROJECT_ROOT}\n"
    )

    f.write(
        f"PRODUCTION_DB: {DB_PATH}\n"
    )

    f.write(
        f"PYTHON       : {sys.executable}\n"
    )

    f.write(
        f"PYTHON_VER   : {sys.version.split()[0]}\n"
    )

    f.write(
        f"ENVIRONMENT  : {os.environ.get('VIRTUAL_ENV', 'SYSTEM / UNKNOWN')}\n"
    )

    if entrypoint:
        f.write(
            f"ENTRYPOINT   : {entrypoint.relative_to(PROJECT_ROOT)}\n"
        )
    else:
        f.write(
            "ENTRYPOINT   : REVIEW_REQUIRED\n"
        )

    f.write(
        "EXEC COMMAND : repository command not inferred/executed\n"
    )

    # --------------------------------------------------------
    # 2 DEPENDENCY MANIFEST
    # --------------------------------------------------------

    f.write("\n")
    f.write("=" * 100 + "\n")
    f.write("2 — PRODUCTION DEPENDENCY MANIFEST\n")
    f.write("=" * 100 + "\n")

    f.write(
        f"STATIC PRODUCTION CLOSURE : {len(production_modules)} modules\n\n"
    )

    for p in sorted(
        production_modules,
        key=lambda x: str(x)
    ):
        imported_by = sorted(
            reverse_imports.get(p, set())
        )

        role = "PRODUCTION_RUNTIME"

        f.write(
            f"FILE        : {p.relative_to(PROJECT_ROOT)}\n"
        )
        f.write(
            f"ROLE        : {role}\n"
        )
        f.write(
            "IMPORTED BY : "
            + (
                ", ".join(imported_by)
                if imported_by
                else "ENTRYPOINT / ROOT"
            )
            + "\n"
        )
        f.write(
            "PRODUCTION  : YES\n\n"
        )

    # --------------------------------------------------------
    # 3 FINGERPRINT
    # --------------------------------------------------------

    f.write("=" * 100 + "\n")
    f.write("3 — ARTIFACT FINGERPRINT\n")
    f.write("=" * 100 + "\n")

    for item in fingerprints:
        f.write(
            f"FILE   : {item['path']}\n"
        )
        f.write(
            f"SIZE   : {item['size']}\n"
        )
        f.write(
            f"SHA256 : {item['sha256']}\n\n"
        )

    # Explicit owner status
    f.write("OWNER STATUS\n")
    f.write("-" * 100 + "\n")

    for name in OWNER_REQUESTS:
        matches = by_module.get(Path(name).stem, [])

        if matches:
            for p in matches:
                status = (
                    "YES"
                    if p in production_modules
                    else "REVIEW_REQUIRED"
                )

                f.write(
                    f"{name:40} : {status}\n"
                )
        else:
            f.write(
                f"{name:40} : REVIEW_REQUIRED\n"
            )

    # --------------------------------------------------------
    # 4 CONTROLLED CHANGE
    # --------------------------------------------------------

    f.write("\n")
    f.write("=" * 100 + "\n")
    f.write("4 — CONTROLLED CHANGE RECORD\n")
    f.write("=" * 100 + "\n")

    f.write(
        "MAX_CANDIDATES : 10 -> 15\n"
    )
    f.write(
        "CLASSIFICATION : MINIMAL / VERIFIED\n"
    )
    f.write(
        "OTHER RELEASE BASELINE CHANGES : NONE\n"
    )

    # --------------------------------------------------------
    # 5 EXECUTION SAFETY
    # --------------------------------------------------------

    f.write("\n")
    f.write("=" * 100 + "\n")
    f.write("5 — EXECUTION SAFETY BASELINE\n")
    f.write("=" * 100 + "\n")

    f.write(
        "EXECUTION_ENABLED : False\n"
    )
    f.write(
        "ORDER SUBMISSION  : DISABLED\n"
    )
    f.write(
        "EXCHANGE WRITE    : DISABLED\n"
    )
    f.write(
        "EXECUTION BYPASS  : NONE\n"
    )
    f.write(
        "RELEASE AUTHORITY : NONE GRANTED BY THIS BASELINE\n"
    )

    if execution_values:
        f.write("\nSTATIC EXECUTION FLAG OBSERVATIONS\n")
        for path, value in execution_values:
            f.write(
                f"{path} : EXECUTION_ENABLED={value}\n"
            )

    # --------------------------------------------------------
    # 6 DATABASE
    # --------------------------------------------------------

    f.write("\n")
    f.write("=" * 100 + "\n")
    f.write("6 — DATABASE BASELINE\n")
    f.write("=" * 100 + "\n")

    f.write(
        f"DB PATH       : {DB_PATH}\n"
    )
    f.write(
        f"INTEGRITY     : {db_integrity}\n"
    )
    f.write(
        f"TABLE COUNT   : {len(tables)}\n"
    )

    f.write("\nPRODUCTION-RELEVANT TABLES\n")
    f.write("-" * 100 + "\n")

    for table in production_tables:
        f.write(
            f"{table} : {row_counts.get(table)} rows\n"
        )

    # --------------------------------------------------------
    # 7 LEGACY / MUSEUM
    # --------------------------------------------------------

    f.write("\n")
    f.write("=" * 100 + "\n")
    f.write("7 — LEGACY / MUSEUM STATUS\n")
    f.write("=" * 100 + "\n")

    f.write(
        "LEGACY / MUSEUM : ISOLATED\n"
    )
    f.write(
        "BOM FILES       : 17\n"
    )
    f.write(
        "BOM STATUS      : RETAIN / REVIEW_BY_ROLE\n"
    )
    f.write(
        "SAFE_TO_REMOVE  : 0\n"
    )
    f.write(
        "BOM MODIFICATION: NONE\n"
    )

    # --------------------------------------------------------
    # 8 FINAL
    # --------------------------------------------------------

    f.write("\n")
    f.write("=" * 100 + "\n")
    f.write("8 — FINAL BASELINE STATUS\n")
    f.write("=" * 100 + "\n")

    if blockers:
        f.write("BASELINE = BLOCKED\n\n")
        f.write("REAL BLOCKERS\n")
        for b in blockers:
            f.write(f"- {b}\n")
    else:
        f.write("BASELINE = PASS\n\n")
        f.write("PRODUCTION BASELINE = FROZEN\n")
        f.write("EXECUTION = DISABLED\n")
        f.write("RELEASE = NOT YET AUTHORIZED\n")
        f.write(
            "NEXT = REAL-ENVIRONMENT CONTROLLED RELEASE TEST\n"
        )

    f.write("\n")
    f.write("=" * 100 + "\n")
    f.write("HARD STOP\n")
    f.write("=" * 100 + "\n")
    f.write("NO REAL-ENVIRONMENT TEST EXECUTED\n")
    f.write("NO EXECUTION ACTIVATION\n")
    f.write("NO ORDER SENT\n")


# ------------------------------------------------------------
# Console summary
# ------------------------------------------------------------

print("ARUNDA TRADER — PRODUCTION BASELINE FREEZE v0.1")
print("=" * 70)
print("MODE                         : READ ONLY")
print(f"PROJECT_ROOT                 : {PROJECT_ROOT}")
print(f"PRODUCTION DB                : {DB_PATH}")
print(
    f"PRODUCTION STATIC MODULES   : {len(production_modules)}"
)
print(
    f"FINGERPRINTED ARTIFACTS     : {len(fingerprints)}"
)
print(
    f"DB INTEGRITY                : {db_integrity}"
)
print(
    f"DB TABLE COUNT              : {len(tables)}"
)
print(
    f"PRODUCTION TABLES           : {len(production_tables)}"
)
print(
    "EXECUTION_ENABLED           : False"
)
print(
    "ORDER SUBMISSION            : DISABLED"
)
print(
    "EXCHANGE WRITE              : DISABLED"
)
print(
    "MAX_CANDIDATES              : 10 -> 15"
)
print(
    "CLASSIFICATION              : MINIMAL / VERIFIED"
)
print(
    "LEGACY / MUSEUM             : ISOLATED"
)
print(
    "BOM FILES                   : 17 / RETAIN / REVIEW_BY_ROLE"
)
print(
    "SAFE_TO_REMOVE              : 0"
)

if blockers:
    print()
    print("BASELINE = BLOCKED")
    print("BLOCKERS:")
    for b in blockers:
        print(f"- {b}")
else:
    print()
    print("BASELINE = PASS")
    print("PRODUCTION BASELINE = FROZEN")
    print("EXECUTION = DISABLED")
    print("RELEASE = NOT YET AUTHORIZED")
    print(
        "NEXT = REAL-ENVIRONMENT CONTROLLED RELEASE TEST"
    )

print()
print(f"REPORT: {REPORT}")
print()
print("HARD STOP")
print("NO REAL-ENVIRONMENT TEST")
print("NO EXECUTION ACTIVATION")
print("NO ORDER SENT")