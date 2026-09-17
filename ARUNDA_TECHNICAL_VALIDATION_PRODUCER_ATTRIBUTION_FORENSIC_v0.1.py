import ast
import hashlib
import sqlite3
from pathlib import Path

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB = ROOT / "arunda.db"
TARGET_ID = 6909

FILES = list(ROOT.glob("*.py"))

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ro_conn():
    uri = f"file:{DB.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA query_only=1")
    q = conn.execute("PRAGMA query_only").fetchone()[0]
    if q != 1:
        conn.close()
        raise RuntimeError("SQLite query_only could not be enabled")
    conn.row_factory = sqlite3.Row
    return conn

print("=" * 100)
print("ARUNDA TECHNICAL VALIDATION PRODUCER ATTRIBUTION FORENSIC v0.1")
print("=" * 100)
print("MODE                         : READ ONLY")
print("TARGET TABLE                : market_technical")
print(f"TARGET ROW                  : id={TARGET_ID}")
print("PRODUCTION EXECUTION        : NO")
print("DATABASE WRITE              : NO")

before = {p: sha256(p) for p in FILES}

conn = ro_conn()

print(f"SQLite query_only           : {conn.execute('PRAGMA query_only').fetchone()[0]}")

# ------------------------------------------------------------
# TARGET ROW
# ------------------------------------------------------------

row = conn.execute(
    """
    SELECT *
    FROM market_technical
    WHERE id=?
    """,
    (TARGET_ID,)
).fetchone()

if row is None:
    raise RuntimeError(f"Target row {TARGET_ID} not found")

print()
print("=" * 100)
print("PERSISTED STATE")
print("=" * 100)

for field in [
    "id",
    "symbol",
    "timestamp",
    "technical_validation_score",
    "technical_validation_status",
    "technical_validation_flags",
    "technical_validation_version",
    "technical_validated_at",
    "technical_version",
    "engine_version",
    "source",
]:
    if field in row.keys():
        print(f"{field:<40}: {row[field]}")

# ------------------------------------------------------------
# AST PRODUCER SEARCH
# ------------------------------------------------------------

print()
print("=" * 100)
print("AST PRODUCER ATTRIBUTION")
print("=" * 100)

targets = {
    "technical_validation_score",
    "technical_validation_status",
    "technical_validation_flags",
    "technical_validation_version",
    "technical_validated_at",
}

hits = []

for path in FILES:

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace"
        )
        tree = ast.parse(text)
    except Exception:
        continue

    lines = text.splitlines()

    for node in ast.walk(tree):

        if isinstance(node, ast.Assign):

            segment = ast.get_source_segment(text, node) or ""

            if any(x in segment for x in targets):
                hits.append(
                    (
                        path.name,
                        node.lineno,
                        "ASSIGN",
                        " ".join(segment.split())[:500]
                    )
                )

        elif isinstance(node, ast.AugAssign):

            segment = ast.get_source_segment(text, node) or ""

            if any(x in segment for x in targets):
                hits.append(
                    (
                        path.name,
                        node.lineno,
                        "AUGASSIGN",
                        " ".join(segment.split())[:500]
                    )
                )

        elif isinstance(node, ast.Call):

            segment = ast.get_source_segment(text, node) or ""

            upper = segment.upper()

            if (
                "MARKET_TECHNICAL" in upper
                and any(
                    x.upper() in upper
                    for x in [
                        "TECHNICAL_VALIDATION_SCORE",
                        "TECHNICAL_VALIDATION_STATUS",
                        "TECHNICAL_VALIDATION_FLAGS",
                        "TECHNICAL_VALIDATION_VERSION",
                    ]
                )
            ):
                hits.append(
                    (
                        path.name,
                        node.lineno,
                        "DB_CALL",
                        " ".join(segment.split())[:700]
                    )
                )

for hit in hits:
    print()
    print(
        f"FILE={hit[0]} "
        f"LINE={hit[1]} "
        f"KIND={hit[2]}"
    )
    print(f"SOURCE={hit[3]}")

# ------------------------------------------------------------
# VERSION / FLAG LITERAL SEARCH
# ------------------------------------------------------------

print()
print("=" * 100)
print("VERSION / FLAG LITERALS")
print("=" * 100)

literals = {
    "0.5.0",
    "INVALID_REGIME",
    "INVALID_VOLATILITY",
}

for path in FILES:

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace"
        )
    except Exception:
        continue

    for literal in literals:

        if literal in text:
            for i, line in enumerate(text.splitlines(), 1):

                if literal in line:
                    print(
                        f"{path.name:<65} "
                        f"line={i:<6} "
                        f"{line.strip()[:300]}"
                    )

# ------------------------------------------------------------
# SOURCE INTEGRITY
# ------------------------------------------------------------

conn.close()

after = {p: sha256(p) for p in FILES}

changed = [
    str(p)
    for p in FILES
    if before.get(p) != after.get(p)
]

print()
print("=" * 100)
print("FINAL FORENSIC STATUS")
print("=" * 100)

print(f"Target row                         : {TARGET_ID}")
print("Production execution               : NO")
print("Database write                      : NO")
print("Source modification                 : NONE" if not changed else changed)

print()
print("PRODUCER ATTRIBUTION FORENSIC      : COMPLETE")
print("=" * 100)