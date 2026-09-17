# -*- coding: utf-8 -*-

import os
import ast
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB = ROOT / "arunda.db"

TARGET_TERMS = [
    "order_intent",
    "order intent",
    "validate_order",
    "validation",
    "execution_gate",
    "execution_preflight",
    "signal_execution",
    "live_signal",
]

print("=" * 100)
print("ARUNDA ORDER INTENT RUNTIME CONSUMER + CONTRACT BOUNDARY RESOLUTION v0.1")
print("=" * 100)
print(f"Started UTC : {datetime.now(timezone.utc).isoformat()}")
print(f"Project     : {ROOT}")
print(f"Database    : {DB}")
print("Mode        : READ ONLY FORENSIC")
print("Writes      : NONE")
print("=" * 100)

# ---------------------------------------------------------------------
# 1. FILE INVENTORY
# ---------------------------------------------------------------------

py_files = sorted(ROOT.glob("*.py"))

print("\n" + "-" * 100)
print("1. ORDER-INTENT / VALIDATION RELATED FILES")
print("-" * 100)

related_files = []

for p in py_files:
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    lower = text.lower()

    hits = [term for term in TARGET_TERMS if term.lower() in lower]

    if hits:
        related_files.append((p, hits))

        print(f"\nFILE : {p.name}")
        print("HITS :", ", ".join(hits))

print(f"\nRelated files found : {len(related_files)}")


# ---------------------------------------------------------------------
# 2. STATIC CALL / IMPORT DISCOVERY
# ---------------------------------------------------------------------

print("\n" + "-" * 100)
print("2. STATIC IMPORT / CALL / REFERENCE DISCOVERY")
print("-" * 100)

records = []

for p in py_files:
    try:
        source = p.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(p))
    except Exception:
        continue

    for node in ast.walk(tree):

        # imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.lower()

                if any(term.lower().replace(" ", "_") in name for term in TARGET_TERMS):
                    records.append(
                        ("IMPORT", p.name, node.lineno, alias.name)
                    )

        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").lower()

            if any(term.lower().replace(" ", "_") in module for term in TARGET_TERMS):
                records.append(
                    ("FROM_IMPORT", p.name, node.lineno, node.module)
                )

            for alias in node.names:
                name = alias.name.lower()

                if any(term.lower().replace(" ", "_") in name for term in TARGET_TERMS):
                    records.append(
                        ("FROM_IMPORT_NAME", p.name, node.lineno, alias.name)
                    )

        # function calls
        elif isinstance(node, ast.Call):

            name = None

            if isinstance(node.func, ast.Name):
                name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            if name:
                lname = name.lower()

                if any(term.lower().replace(" ", "_") in lname
                       for term in TARGET_TERMS):
                    records.append(
                        ("CALL", p.name, node.lineno, name)
                    )

        # function definitions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

            lname = node.name.lower()

            if any(term.lower().replace(" ", "_") in lname
                   for term in TARGET_TERMS):

                records.append(
                    ("FUNCTION", p.name, node.lineno, node.name)
                )


if records:
    for r in records:
        print(f"{r[0]:20} {r[1]:65} LINE {r[2]:6} -> {r[3]}")
else:
    print("No static import/call/function references found.")


# ---------------------------------------------------------------------
# 3. MAIN / ENTRYPOINT CANDIDATES
# ---------------------------------------------------------------------

print("\n" + "-" * 100)
print("3. MAIN / ENTRYPOINT CANDIDATES")
print("-" * 100)

entrypoints = []

for p in py_files:

    try:
        source = p.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(p))
    except Exception:
        continue

    has_main = False
    has_guard = False

    for node in ast.walk(tree):

        if isinstance(node, ast.FunctionDef) and node.name == "main":
            has_main = True

        if isinstance(node, ast.If):
            try:
                if (
                    isinstance(node.test, ast.Compare)
                    and isinstance(node.test.left, ast.Name)
                    and node.test.left.id == "__name__"
                ):
                    has_guard = True
            except Exception:
                pass

    if has_main or has_guard:
        entrypoints.append((p.name, has_main, has_guard))

for name, main, guard in entrypoints:
    print(
        f"{name:70} "
        f"main={main} "
        f"main_guard={guard}"
    )

print(f"\nEntrypoint candidates : {len(entrypoints)}")


# ---------------------------------------------------------------------
# 4. RUNTIME-RELEVANT FILE CONTENT WINDOWS
# ---------------------------------------------------------------------

print("\n" + "-" * 100)
print("4. EXACT SOURCE WINDOWS AROUND ORDER-INTENT / VALIDATION REFERENCES")
print("-" * 100)

for p, hits in related_files:

    try:
        lines = p.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines()
    except Exception:
        continue

    interesting = []

    for i, line in enumerate(lines):

        lower = line.lower()

        if any(term.lower() in lower for term in TARGET_TERMS):
            interesting.append(i)

    if not interesting:
        continue

    print("\n" + "=" * 100)
    print(f"FILE : {p.name}")
    print("=" * 100)

    shown = set()

    for idx in interesting:

        start = max(0, idx - 4)
        end = min(len(lines), idx + 7)

        key = (start, end)

        if key in shown:
            continue

        shown.add(key)

        print(f"\n--- lines {start + 1}-{end} ---")

        for j in range(start, end):
            print(f"{j + 1:6}: {lines[j]}")


# ---------------------------------------------------------------------
# 5. DB TABLE / SCHEMA CHECK
# ---------------------------------------------------------------------

print("\n" + "-" * 100)
print("5. DATABASE CONTRACT BOUNDARY CHECK")
print("-" * 100)

if DB.exists():

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    try:

        tables = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """).fetchall()

        for (table,) in tables:

            lname = table.lower()

            if any(
                term.lower().replace(" ", "_") in lname
                for term in [
                    "order_intent",
                    "validation",
                    "execution",
                    "signal",
                    "fusion"
                ]
            ):

                print(f"\nTABLE : {table}")

                cols = conn.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()

                for col in cols:
                    print(
                        f"   {col[1]:35} "
                        f"type={col[2]} "
                        f"notnull={col[3]} "
                        f"pk={col[5]}"
                    )

    finally:
        conn.close()

else:
    print("DATABASE NOT FOUND")


# ---------------------------------------------------------------------
# 6. FINAL RESOLUTION SUMMARY
# ---------------------------------------------------------------------

print("\n" + "=" * 100)
print("FORENSIC RESOLUTION OUTPUT")
print("=" * 100)

print("""
This script performs discovery only.

It does NOT:
- modify production source
- modify database
- create tables
- repair contracts
- execute order intent
- execute trades

Required next determination:

A) REAL PRODUCTION/RUNTIME CONSUMER
B) EXACT CALL SITE
C) EXACT INPUT OBJECT / ROW
D) EXACT VALIDATION FUNCTION
E) EXACT VALIDATION OUTPUT
F) EXACT DOWNSTREAM EXECUTION CONSUMER
G) FIRST CONTRACT MISMATCH, IF ANY

No repair is authorized until A-G are concretely resolved.
""")

print("=" * 100)
print("DATABASE CONNECTION : CLOSED")
print("=" * 100)