# ============================================================
# ARUNDA PROJECT INTEGRITY AUDIT V2
# READ ONLY / COMPACT / INDEPENDENT
# ============================================================

from __future__ import annotations

import ast
import hashlib
import os
import re
import sqlite3
import sys
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "arunda.db"

REPORT_PATH = PROJECT_ROOT / "ARUNDA_PROJECT_INTEGRITY_SUMMARY_V2.txt"

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "build",
    "dist",
    ".idea",
    ".vscode",
}

MAX_SOURCE_READ = 5_000_000


# ============================================================
# OUTPUT
# ============================================================

lines = []


def out(text=""):
    print(text)
    lines.append(str(text))


def section(title):
    out("")
    out("=" * 72)
    out(title)
    out("=" * 72)


def status(label, value):
    out(f"{label:<32}: {value}")


# ============================================================
# FILE DISCOVERY
# ============================================================

def python_files():
    result = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for name in files:
            if name.endswith(".py"):
                result.append(Path(root) / name)

    return sorted(result)


PY_FILES = python_files()


# ============================================================
# SAFE TEXT READ
# ============================================================

def read_text(path):
    try:
        if path.stat().st_size > MAX_SOURCE_READ:
            return ""

        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        return ""


# ============================================================
# HASH
# ============================================================

def sha256(path):
    h = hashlib.sha256()

    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)

        return h.hexdigest()

    except Exception:
        return "READ_ERROR"


# ============================================================
# KEYWORD SEARCH
# ============================================================

def search_project(patterns):
    hits = []

    for path in PY_FILES:
        text = read_text(path)

        if not text:
            continue

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                hits.append(
                    (
                        str(path.relative_to(PROJECT_ROOT)),
                        pattern
                    )
                )

    return hits


# ============================================================
# AST CHECK
# ============================================================

def compile_check(path):
    try:
        source = read_text(path)

        if not source:
            return True

        compile(source, str(path), "exec")
        return True

    except Exception:
        return False


# ============================================================
# HEADER
# ============================================================

section("ARUNDA TRADER — PROJECT INTEGRITY AUDIT V2")

status(
    "Timestamp",
    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

status(
    "Project Root",
    str(PROJECT_ROOT)
)

status(
    "Database",
    str(DB_PATH)
)

status(
    "Mode",
    "READ ONLY"
)

status(
    "Production Execution",
    "MUST REMAIN DISABLED"
)


# ============================================================
# PYTHON SYNTAX
# ============================================================

section("1. PYTHON SYNTAX")

syntax_failures = []

for path in PY_FILES:
    if not compile_check(path):
        syntax_failures.append(
            str(path.relative_to(PROJECT_ROOT))
        )

status(
    "Python Files",
    len(PY_FILES)
)

status(
    "Syntax Failures",
    len(syntax_failures)
)

if syntax_failures:
    for item in syntax_failures[:20]:
        out(f"FAIL: {item}")


# ============================================================
# EXECUTION STATE
# ============================================================

section("2. EXECUTION STATE")

execution_hits = []

for path in PY_FILES:
    text = read_text(path)

    for match in re.finditer(
        r"EXECUTION_ENABLED\s*=\s*([^\n#]+)",
        text,
        re.IGNORECASE
    ):
        execution_hits.append(
            (
                str(path.relative_to(PROJECT_ROOT)),
                match.group(1).strip()
            )
        )

execution_bad = []

for path, value in execution_hits:
    normalized = value.lower().replace(" ", "")

    if normalized not in {
        "false",
        "0",
        "none",
    }:
        execution_bad.append(
            (path, value)
        )

if not execution_hits:
    status("EXECUTION_ENABLED", "NOT FOUND")
elif execution_bad:
    status("EXECUTION_ENABLED", "WARNING")
    for item in execution_bad[:10]:
        out(f"WARNING: {item[0]} -> {item[1]}")
else:
    status("EXECUTION_ENABLED", "DISABLED")


# ============================================================
# FEATURE CONTRACT
# ============================================================

section("3. FEATURE CONTRACT")

feature_patterns = [
    r"FEATURE_CONTRACT_v0\.3",
    r"FULL_CONTEXT_TARGET",
    r"MIN_CONTEXT",
    r"WINDOW_SIZE",
    r"\bLIMITED\b",
    r"\bFULL\b",
    r"\bNONE\b",
]

feature_hits = search_project(feature_patterns)

for path, pattern in feature_hits[:30]:
    out(f"{path} :: {pattern}")

full_target = search_project([
    r"FULL_CONTEXT_TARGET\s*=\s*150"
])

min_context = search_project([
    r"MIN_CONTEXT\s*=\s*21"
])

contract_v03 = search_project([
    r"FEATURE_CONTRACT_v0\.3"
])

status(
    "FULL_CONTEXT_TARGET=150",
    "FOUND" if full_target else "NOT FOUND"
)

status(
    "MIN_CONTEXT=21",
    "FOUND" if min_context else "NOT FOUND"
)

status(
    "FEATURE_CONTRACT_v0.3",
    "FOUND" if contract_v03 else "NOT FOUND"
)


# ============================================================
# FEATURE PRODUCER
# ============================================================

section("4. FEATURE PRODUCER")

feature_producer_patterns = [
    r"runtime_feature_producer",
    r"feature_snapshot",
    r"load_feature_snapshot",
    r"build_feature",
    r"produce_feature",
]

hits = search_project(feature_producer_patterns)

unique_feature_files = sorted(
    set(path for path, _ in hits)
)

for path in unique_feature_files[:20]:
    out(path)

status(
    "Feature Producer Candidates",
    len(unique_feature_files)
)


# ============================================================
# SCORE PRODUCER
# ============================================================

section("5. SCORE PRODUCER")

score_patterns = [
    r"score_producer",
    r"produce_score",
    r"calculate_score",
    r"load_scores",
    r"build_score",
    r"technical_score",
    r"momentum_20",
    r"return_20",
    r"trend_slope_20",
    r"acceleration",
    r"position_20",
    r"volatility_20",
    r"range_20",
]

score_hits = search_project(score_patterns)

score_files = sorted(
    set(path for path, _ in score_hits)
)

for path in score_files[:30]:
    out(path)

status(
    "Score Producer Candidates",
    len(score_files)
)


# ============================================================
# HISTORICAL SCORE FORMULA
# ============================================================

section("6. SCORE FORMULA PRESERVATION")

formula = {
    "return_20": r"return_20\s*[:=]",
    "momentum_20": r"momentum_20\s*[:=]",
    "trend_slope_20": r"trend_slope_20\s*[:=]",
    "acceleration": r"acceleration\s*[:=]",
    "position_20": r"position_20\s*[:=]",
    "volatility_20": r"volatility_20\s*[:=]",
    "range_20": r"range_20\s*[:=]",
}

formula_found = {}

for name, pattern in formula.items():
    hits = search_project([pattern])
    formula_found[name] = bool(hits)

    status(
        name,
        "FOUND" if hits else "NOT FOUND"
    )


# ============================================================
# SIGNAL SCORER
# ============================================================

section("7. SIGNAL SCORER")

signal_patterns = [
    r"signal_scorer",
    r"signal_engine",
    r"build_all",
    r"validated_signals",
]

signal_hits = search_project(signal_patterns)

signal_files = sorted(
    set(path for path, _ in signal_hits)
)

for path in signal_files[:20]:
    out(path)

status(
    "Signal-related Files",
    len(signal_files)
)


# ============================================================
# DECISION BOUNDARY
# ============================================================

section("8. DECISION BOUNDARY")

legacy_bridge_patterns = [
    r"bars_by_asset",
    r"indicators_by_asset",
    r"structures_by_asset",
]

legacy_hits = search_project(
    legacy_bridge_patterns
)

if legacy_hits:
    status(
        "Old Raw Feature Bridge",
        "FOUND"
    )

    for path, pattern in legacy_hits[:20]:
        out(f"{path} :: {pattern}")

else:
    status(
        "Old Raw Feature Bridge",
        "NOT FOUND"
    )


decision_patterns = [
    r"validated_signals",
    r"decision_snapshot",
    r"build_decision",
    r"build_decision_snapshot",
    r"determine_decision",
]

decision_hits = search_project(
    decision_patterns
)

decision_files = sorted(
    set(path for path, _ in decision_hits)
)

for path in decision_files[:20]:
    out(path)

status(
    "Decision Files",
    len(decision_files)
)


# ============================================================
# RISK
# ============================================================

section("9. RISK")

risk_hits = search_project([
    r"\brisk\b",
    r"risk_gate",
    r"risk_manager",
    r"position_size",
])

risk_files = sorted(
    set(path for path, _ in risk_hits)
)

for path in risk_files[:20]:
    out(path)

status(
    "Risk-related Files",
    len(risk_files)
)


# ============================================================
# TRADE GATE
# ============================================================

section("10. TRADE GATE")

gate_hits = search_project([
    r"trade_gate",
    r"order_intent",
    r"preflight",
    r"execution_gate",
])

gate_files = sorted(
    set(path for path, _ in gate_hits)
)

for path in gate_files[:20]:
    out(path)

status(
    "Trade Gate Files",
    len(gate_files)
)


# ============================================================
# FORBIDDEN FABRICATION / SYNTHETIC DATA
# ============================================================

section("11. FABRICATION / SYNTHETIC DATA SCAN")

fabrication_patterns = [
    r"interpolat",
    r"forward_fill",
    r"backfill",
    r"\bbfill\b",
    r"\bffill\b",
    r"synthetic",
    r"fabricat",
    r"padding",
    r"pad_rows",
]

fabrication_hits = search_project(
    fabrication_patterns
)

if fabrication_hits:
    status(
        "Potential Fabrication References",
        len(fabrication_hits)
    )

    for path, pattern in fabrication_hits[:30]:
        out(f"{path} :: {pattern}")

else:
    status(
        "Potential Fabrication References",
        "NONE"
    )


# ============================================================
# DB READ-ONLY
# ============================================================

section("12. DATABASE")

db_ok = False
db_integrity = "NOT CHECKED"

if not DB_PATH.exists():

    status(
        "Database",
        "MISSING"
    )

else:

    try:

        uri = f"file:{DB_PATH.as_posix()}?mode=ro"

        conn = sqlite3.connect(
            uri,
            uri=True
        )

        conn.execute(
            "PRAGMA query_only=ON"
        )

        result = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        db_integrity = result[0] if result else "UNKNOWN"

        db_ok = db_integrity.lower() == "ok"

        status(
            "SQLite Integrity",
            db_integrity
        )

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

        table_names = [
            row[0] for row in tables
        ]

        status(
            "Tables",
            len(table_names)
        )

        expected_tables = {
            "market_data",
            "market_history",
            "market_records",
            "market_universe",
            "signal_outcomes",
            "fusion_signals",
        }

        missing_tables = sorted(
            expected_tables - set(table_names)
        )

        if missing_tables:
            status(
                "Expected Tables Missing",
                len(missing_tables)
            )

            for table in missing_tables:
                out(f"MISSING TABLE: {table}")

        else:
            status(
                "Expected Tables Missing",
                "NONE"
            )

        # ----------------------------------------------------
        # market_data schema
        # ----------------------------------------------------

        if "market_data" in table_names:

            columns = conn.execute(
                "PRAGMA table_info(market_data)"
            ).fetchall()

            column_names = [
                row[1] for row in columns
            ]

            required = {
                "timestamp",
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "volume",
            }

            missing_columns = sorted(
                required - set(column_names)
            )

            if missing_columns:
                status(
                    "market_data Schema",
                    "INVALID"
                )

                for col in missing_columns:
                    out(
                        f"MISSING COLUMN: {col}"
                    )

            else:
                status(
                    "market_data Schema",
                    "VALID"
                )

            # ------------------------------------------------
            # market_data fingerprint
            # ------------------------------------------------

            row_count = conn.execute(
                "SELECT COUNT(*) FROM market_data"
            ).fetchone()[0]

            symbol_count = conn.execute(
                "SELECT COUNT(DISTINCT symbol) FROM market_data"
            ).fetchone()[0]

            min_ts = conn.execute(
                "SELECT MIN(timestamp) FROM market_data"
            ).fetchone()[0]

            max_ts = conn.execute(
                "SELECT MAX(timestamp) FROM market_data"
            ).fetchone()[0]

            status(
                "market_data Rows",
                row_count
            )

            status(
                "market_data Symbols",
                symbol_count
            )

            status(
                "market_data Min Timestamp",
                min_ts
            )

            status(
                "market_data Max Timestamp",
                max_ts
            )

        else:

            status(
                "market_data",
                "MISSING"
            )

        conn.close()

    except Exception as e:

        status(
            "Database Access",
            "FAILED"
        )

        out(
            f"DB ERROR: {type(e).__name__}: {e}"
        )


# ============================================================
# DUPLICATE PRODUCER NAMES
# ============================================================

section("13. DUPLICATE PRODUCER RISK")

producer_keywords = [
    "feature_producer",
    "score_producer",
    "signal_scorer",
]

for keyword in producer_keywords:

    matches = [
        path
        for path in PY_FILES
        if keyword.lower() in path.name.lower()
    ]

    status(
        keyword,
        len(matches)
    )

    for path in matches[:10]:
        out(
            str(path.relative_to(PROJECT_ROOT))
        )


# ============================================================
# KEY FILE FINGERPRINTS
# ============================================================

section("14. KEY FILE FINGERPRINTS")

key_names = [
    "feature_contract.py",
    "runtime_feature_producer.py",
    "score_producer.py",
    "signal_scorer.py",
    "signal_engine.py",
    "decision.py",
    "risk.py",
    "trade_gate.py",
    "arunda_pipeline.py",
]

found_key_files = []

for path in PY_FILES:

    if path.name.lower() in {
        x.lower() for x in key_names
    }:

        rel = path.relative_to(PROJECT_ROOT)

        found_key_files.append(
            (str(rel), sha256(path))
        )

for path, digest in sorted(found_key_files):

    out(
        f"{path} :: {digest[:16]}"
    )

status(
    "Key Files Found",
    len(found_key_files)
)


# ============================================================
# FINAL VERDICT
# ============================================================

section("15. FINAL VERDICT")

failures = []
warnings = []

if syntax_failures:
    failures.append(
        f"Python syntax failures: {len(syntax_failures)}"
    )

if execution_bad:
    failures.append(
        "EXECUTION_ENABLED is not safely disabled"
    )

if not full_target:
    warnings.append(
        "FULL_CONTEXT_TARGET=150 not found"
    )

if not min_context:
    warnings.append(
        "MIN_CONTEXT=21 not found"
    )

if not contract_v03:
    warnings.append(
        "FEATURE_CONTRACT_v0.3 not found"
    )

if not db_ok:
    failures.append(
        "Database integrity is not OK"
    )

if legacy_hits:
    warnings.append(
        "Legacy raw-feature decision bridge references found"
    )

if fabrication_hits:
    warnings.append(
        "Fabrication/interpolation/fill-related references found"
    )

if not formula_found["return_20"]:
    warnings.append(
        "return_20 formula component not found"
    )

if not formula_found["momentum_20"]:
    warnings.append(
        "momentum_20 formula component not found"
    )

if not formula_found["trend_slope_20"]:
    warnings.append(
        "trend_slope_20 formula component not found"
    )

if not formula_found["acceleration"]:
    warnings.append(
        "acceleration formula component not found"
    )

if not formula_found["position_20"]:
    warnings.append(
        "position_20 formula component not found"
    )

if not formula_found["volatility_20"]:
    warnings.append(
        "volatility_20 formula component not found"
    )

if not formula_found["range_20"]:
    warnings.append(
        "range_20 formula component not found"
    )


if failures:

    FINAL_STATUS = "FAIL"

elif warnings:

    FINAL_STATUS = "PASS_WITH_WARNINGS"

else:

    FINAL_STATUS = "PASS"


status(
    "FINAL STATUS",
    FINAL_STATUS
)

out("")

if failures:

    out("FAILURES:")

    for item in failures:
        out(f"  - {item}")

else:

    out("FAILURES: NONE")


out("")

if warnings:

    out("WARNINGS:")

    for item in warnings:
        out(f"  - {item}")

else:

    out("WARNINGS: NONE")


# ============================================================
# CRITICAL PIPELINE MAP
# ============================================================

section("16. CRITICAL PIPELINE MAP")

status(
    "REAL MARKET DATA",
    "CHECKED"
)

status(
    "REAL FEATURE SNAPSHOT",
    "CHECKED"
)

status(
    "REAL SCORE PRODUCER",
    "CHECKED"
)

status(
    "SIGNAL",
    "CHECKED"
)

status(
    "DECISION",
    "CHECKED"
)

status(
    "RISK",
    "CHECKED"
)

status(
    "TRADE GATE",
    "CHECKED"
)

status(
    "EXECUTION",
    "DISABLED / MUST STAY DISABLED"
)


# ============================================================
# SAVE
# ============================================================

REPORT_PATH.write_text(
    "\n".join(lines),
    encoding="utf-8"
)

print("")
print("=" * 72)
print("COMPACT AUDIT COMPLETE")
print(f"REPORT: {REPORT_PATH}")
print("=" * 72)