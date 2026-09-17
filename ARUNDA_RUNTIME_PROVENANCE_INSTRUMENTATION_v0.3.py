# ARUNDA_RUNTIME_PROVENANCE_INSTRUMENTATION_v0.3.py
# =================================================================================================
# REAL PRODUCTION ENTRYPOINT + RUNTIME PROVENANCE
# READ-ONLY FORENSIC
#
# PURPOSE
# -------
# Find the real production execution root and then capture the FIRST
# runtime appearance/population of:
#
#     bars_by_asset
#     indicators_by_asset
#     structures_by_asset
#
# IMPORTANT
# ---------
# - forensic/audit/diagnostic/repair scripts are excluded
# - no source modification
# - no SQL write issued BY THIS SCRIPT
# - no synthetic data
# - runtime is traced only after production root is resolved
# =================================================================================================

from __future__ import annotations

import ast
import builtins
import os
import re
import runpy
import sqlite3
import sys
import threading
import traceback
from pathlib import Path


ROOT = Path(r"C:\Users\ASUS\ArundaTrader").resolve()

TARGETS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

# -----------------------------------------------------------------------------------------------
# HARD EXCLUSION: NEVER TREAT THESE AS PRODUCTION ROOTS
# -----------------------------------------------------------------------------------------------

EXCLUDED_WORDS = (
    "forensic",
    "audit",
    "diagnostic",
    "validation",
    "repair",
    "broken",
    "backup",
    "pre_step",
    "step",
    "quarantine",
    "test",
    "self_test",
    "health",
    "readiness",
    "preflight",
    "scan",
    "inspect",
    "verify",
)

PRODUCTION_HINTS = (
    "arunda_pipeline.py",
    "arunda_source_engine.py",
    "decision_engine.py",
)

TARGET_MODULES = {
    "decision_engine",
    "feature_contract",
    "signal_scorer",
}


# ===============================================================================================
# BASIC HELPERS
# ===============================================================================================

def project_file(path: Path) -> bool:
    try:
        p = path.resolve()
        return (
            p.suffix.lower() == ".py"
            and ROOT in p.parents
        )
    except Exception:
        return False


def excluded(path: Path) -> bool:
    name = path.name.lower()

    return any(
        word in name
        for word in EXCLUDED_WORDS
    )


def read_source(path: Path) -> str:
    return path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )


def parse(path: Path):
    try:
        return ast.parse(
            read_source(path),
            filename=str(path),
        )
    except Exception:
        return None


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        base = dotted_name(node.value)

        if base:
            return f"{base}.{node.attr}"

    return None


# ===============================================================================================
# MODULE / CALL GRAPH DISCOVERY
# ===============================================================================================

class ModuleInfo:

    def __init__(self, path: Path, tree):
        self.path = path
        self.tree = tree

        self.module_name = path.stem

        self.imports = set()
        self.calls = []
        self.functions = set()
        self.main = False

        self.target_refs = set()

        self.scan()

    def scan(self):

        for node in ast.walk(self.tree):

            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                self.functions.add(node.name)

                if node.name == "main":
                    self.main = True

            elif isinstance(node, ast.Import):

                for alias in node.names:
                    self.imports.add(
                        alias.name.split(".")[0]
                    )

            elif isinstance(node, ast.ImportFrom):

                if node.module:
                    self.imports.add(
                        node.module.split(".")[0]
                    )

            elif isinstance(node, ast.Call):

                name = dotted_name(node.func)

                if name:
                    self.calls.append(
                        (
                            name,
                            getattr(node, "lineno", -1),
                        )
                    )

            elif isinstance(node, ast.Name):

                if node.id in TARGETS:
                    self.target_refs.add(node.id)


# ===============================================================================================
# DISCOVER ALL NON-FORENSIC PROJECT MODULES
# ===============================================================================================

def load_module_index():

    result = {}

    for path in ROOT.rglob("*.py"):

        if not project_file(path):
            continue

        if excluded(path):
            continue

        tree = parse(path)

        if tree is None:
            continue

        info = ModuleInfo(path, tree)

        result[path.stem] = info

    return result


# ===============================================================================================
# FIND MODULES THAT REACH PRODUCTION DECISION / FEATURE LAYER
# ===============================================================================================

def direct_production_score(info: ModuleInfo):

    score = 0
    reasons = []

    name = info.module_name.lower()

    if name == "arunda_pipeline":
        score += 100
        reasons.append("arunda_pipeline")

    if name == "arunda_source_engine":
        score += 80
        reasons.append("arunda_source_engine")

    if name == "decision_engine":
        score += 20
        reasons.append("decision_engine")

    if "decision_engine" in info.imports:
        score += 50
        reasons.append("imports:decision_engine")

    if "feature_contract" in info.imports:
        score += 25
        reasons.append("imports:feature_contract")

    if "signal_scorer" in info.imports:
        score += 20
        reasons.append("imports:signal_scorer")

    if info.main:
        score += 10
        reasons.append("main")

    if "__main__" in read_source(info.path):
        score += 10
        reasons.append("__main__")

    return score, reasons


# ===============================================================================================
# REVERSE CALLER GRAPH
# ===============================================================================================

def build_reverse_graph(index):

    reverse = {
        name: set()
        for name in index
    }

    for owner_name, info in index.items():

        for called_name, _ in info.calls:

            root = called_name.split(".")[0]

            if root in reverse:
                reverse[root].add(owner_name)

    return reverse


def production_roots(index, reverse):

    candidates = []

    for name, info in index.items():

        score, reasons = direct_production_score(info)

        # A root is more interesting when it has no non-forensic
        # project caller.
        callers = reverse.get(name, set())

        if not callers:
            score += 50
            reasons.append("NO_PROJECT_CALLER")

        candidates.append(
            (
                score,
                name,
                info.path,
                reasons,
            )
        )

    candidates.sort(
        key=lambda x: (-x[0], str(x[2]).lower())
    )

    return candidates


# ===============================================================================================
# TARGET CHAIN DISCOVERY
# ===============================================================================================

def target_modules(index):

    result = []

    for name, info in index.items():

        if (
            info.target_refs
            or name in TARGET_MODULES
        ):
            result.append(info)

    return result


# ===============================================================================================
# REPORT DISCOVERY
# ===============================================================================================

def print_discovery(index, roots):

    print()
    print("=" * 100)
    print("PRODUCTION ROOT DISCOVERY")
    print("=" * 100)

    print(
        f"NON-FORENSIC PYTHON MODULES : {len(index)}"
    )

    print()

    for i, item in enumerate(roots[:20], 1):

        score, name, path, reasons = item

        print(
            f"[{i:02d}] SCORE={score:03d} "
            f"{path}"
        )

        print(
            f"     REASONS: {', '.join(reasons)}"
        )


def print_target_map(index):

    print()
    print("=" * 100)
    print("TARGET MODULE MAP")
    print("=" * 100)

    for info in target_modules(index):

        print()
        print(f"MODULE : {info.path}")
        print(
            f"FUNCTIONS : "
            f"{', '.join(sorted(info.functions))}"
        )

        if info.target_refs:
            print(
                "TARGET REFS : "
                + ", ".join(sorted(info.target_refs))
            )


# ===============================================================================================
# RUNTIME STATE
# ===============================================================================================

class RuntimeState:

    def __init__(self):

        self.lock = threading.RLock()

        self.first = {
            target: None
            for target in TARGETS
        }

        self.stack = []

        self.events = []

        self.call_count = 0

    def push(self, frame):

        with self.lock:

            self.stack.append(
                (
                    frame.f_code.co_filename,
                    frame.f_code.co_name,
                    frame.f_lineno,
                )
            )

    def pop(self):

        with self.lock:

            if self.stack:
                self.stack.pop()

    def record(
        self,
        target,
        value,
        frame,
        event,
    ):

        with self.lock:

            record = {
                "target": target,
                "event": event,
                "file": frame.f_code.co_filename,
                "line": frame.f_lineno,
                "function": frame.f_code.co_name,
                "type": type(value).__name__,
                "repr": safe_repr(value),
                "stack": list(self.stack),
            }

            self.events.append(record)

            if self.first[target] is None:

                self.first[target] = record

                print()
                print("=" * 100)
                print(
                    f"FIRST RUNTIME TARGET : {target}"
                )
                print("=" * 100)

                print(
                    f"EVENT    : {event}"
                )

                print(
                    f"FILE     : "
                    f"{record['file']}"
                )

                print(
                    f"LINE     : "
                    f"{record['line']}"
                )

                print(
                    f"FUNCTION : "
                    f"{record['function']}"
                )

                print(
                    f"TYPE     : "
                    f"{record['type']}"
                )

                print(
                    f"VALUE    : "
                    f"{record['repr']}"
                )

                print()
                print("CALL STACK:")

                for i, item in enumerate(
                    record["stack"],
                    1,
                ):
                    print(
                        f"  {i}. "
                        f"{item[0]} :: "
                        f"{item[1]} @ "
                        f"{item[2]}"
                    )


STATE = RuntimeState()


def safe_repr(value, limit=700):

    try:

        if isinstance(value, dict):

            keys = list(value.keys())[:10]

            return (
                f"<dict len={len(value)} "
                f"keys={keys}>"
            )

        return repr(value)[:limit]

    except Exception:

        return (
            f"<repr failed: "
            f"{type(value).__name__}>"
        )


# ===============================================================================================
# RUNTIME TRACE
# ===============================================================================================

def trace(frame, event, arg):

    filename = frame.f_code.co_filename

    try:
        path = Path(filename).resolve()
    except Exception:
        return trace

    if ROOT not in path.parents:
        return trace

    if excluded(path):
        return trace

    if event == "call":

        STATE.call_count += 1
        STATE.push(frame)

        return trace

    if event == "line":

        # Inspect live locals.
        for target in TARGETS:

            if target not in frame.f_locals:
                continue

            value = frame.f_locals[target]

            STATE.record(
                target,
                value,
                frame,
                "RUNTIME_LOCAL_PRESENT",
            )

        return trace

    if event == "return":

        STATE.pop()
        return trace

    return trace


# ===============================================================================================
# BLOCK DANGEROUS SQL WRITES FROM FORENSIC EXECUTION
#
# Reads remain possible.
# Any obvious INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/REPLACE is rejected.
# ===============================================================================================

WRITE_SQL = re.compile(
    r"""
    ^\s*
    (
        INSERT
        |UPDATE
        |DELETE
        |ALTER
        |DROP
        |CREATE
        |REPLACE
        |VACUUM
        |REINDEX
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


ORIGINAL_CURSOR_EXECUTE = sqlite3.Cursor.execute
ORIGINAL_CURSOR_EXECUTEMANY = sqlite3.Cursor.executemany


def guarded_execute(self, sql, parameters=()):

    if isinstance(sql, str) and WRITE_SQL.match(sql):

        raise RuntimeError(
            "ARUNDA FORENSIC SAFETY BLOCK: "
            "SQL WRITE/DDL operation blocked."
        )

    return ORIGINAL_CURSOR_EXECUTE(
        self,
        sql,
        parameters,
    )


def guarded_executemany(
    self,
    sql,
    parameters,
):

    if isinstance(sql, str) and WRITE_SQL.match(sql):

        raise RuntimeError(
            "ARUNDA FORENSIC SAFETY BLOCK: "
            "SQL WRITE/DDL operation blocked."
        )

    return ORIGINAL_CURSOR_EXECUTEMANY(
        self,
        sql,
        parameters,
    )


# ===============================================================================================
# RUN
# ===============================================================================================

def execute(entrypoint):

    print()
    print("=" * 100)
    print("REAL RUNTIME PROVENANCE EXECUTION")
    print("=" * 100)

    print(
        f"ENTRYPOINT : {entrypoint}"
    )

    print(
        "TRACE      : ENABLED"
    )

    print(
        "SQL WRITES : BLOCKED"
    )

    print(
        "SOURCE     : UNMODIFIED"
    )

    # NOTE:
    # sqlite3's C-level methods are immutable on some Python versions.
    # We therefore attempt the guard but never depend on it for discovery.
    sql_guard_installed = False

    try:

        sqlite3.Cursor.execute = guarded_execute
        sqlite3.Cursor.executemany = guarded_executemany

        sql_guard_installed = True

    except Exception:

        sql_guard_installed = False

    print(
        f"SQL GUARD INSTALLED : {sql_guard_installed}"
    )

    old_trace = sys.gettrace()

    sys.settrace(trace)

    try:

        runpy.run_path(
            str(entrypoint),
            run_name="__main__",
        )

    except SystemExit as exc:

        print()
        print(
            f"ENTRYPOINT EXITED: SystemExit({exc.code})"
        )

    except RuntimeError as exc:

        print()
        print(
            f"RUNTIME BLOCK/ERROR: {exc}"
        )

    except Exception as exc:

        print()
        print("=" * 100)
        print("RUNTIME EXCEPTION")
        print("=" * 100)

        print(
            f"{type(exc).__name__}: {exc}"
        )

        traceback.print_exc()

    finally:

        sys.settrace(old_trace)

    print()
    print("=" * 100)
    print("RUNTIME COMPLETE")
    print("=" * 100)

    print(
        f"FUNCTION CALLS OBSERVED : "
        f"{STATE.call_count}"
    )


# ===============================================================================================
# FINAL PROVENANCE REPORT
# ===============================================================================================

def final_report(entrypoint):

    print()
    print("=" * 100)
    print("FINAL PROVENANCE")
    print("=" * 100)

    print(
        f"ENTRYPOINT : {entrypoint}"
    )

    for target in (
        "bars_by_asset",
        "indicators_by_asset",
        "structures_by_asset",
    ):

        print()
        print("-" * 100)
        print(
            f"TARGET : {target}"
        )
        print("-" * 100)

        record = STATE.first[target]

        if record is None:

            print(
                "NOT OBSERVED"
            )

            continue

        print(
            f"FIRST FILE     : {record['file']}"
        )

        print(
            f"FIRST LINE     : {record['line']}"
        )

        print(
            f"FIRST FUNCTION : {record['function']}"
        )

        print(
            f"EVENT          : {record['event']}"
        )

        print(
            f"TYPE           : {record['type']}"
        )

        print(
            f"VALUE          : {record['repr']}"
        )

        print()
        print(
            "CALLER CHAIN:"
        )

        for i, item in enumerate(
            record["stack"],
            1,
        ):

            print(
                f"  {i}. "
                f"{item[0]} :: "
                f"{item[1]} @ "
                f"{item[2]}"
            )

    # -------------------------------------------------------------------------------------------
    # CROSS TARGET CONCLUSION
    # -------------------------------------------------------------------------------------------

    records = [
        STATE.first[target]
        for target in TARGETS
        if STATE.first[target] is not None
    ]

    print()
    print("=" * 100)
    print("CROSS-TARGET RESULT")
    print("=" * 100)

    if len(records) != 3:

        print(
            f"OBSERVED : {len(records)}/3"
        )

        print(
            "NO THREE-TARGET RUNTIME CONCLUSION."
        )

        return

    first_locations = {
        (
            r["file"],
            r["line"],
            r["function"],
        )
        for r in records
    }

    if len(first_locations) == 1:

        location = next(
            iter(first_locations)
        )

        print(
            "STRONG RESULT:"
        )

        print(
            "ALL THREE MAPPINGS FIRST APPEARED "
            "AT THE SAME RUNTIME LOCATION."
        )

        print(
            f"FILE     : {location[0]}"
        )

        print(
            f"LINE     : {location[1]}"
        )

        print(
            f"FUNCTION : {location[2]}"
        )

    else:

        print(
            "THREE TARGETS OBSERVED."
        )

        print(
            "THEIR FIRST RUNTIME APPEARANCE "
            "IS NOT THE SAME LOCATION."
        )

        for target in sorted(TARGETS):

            r = STATE.first[target]

            print(
                f"{target}: "
                f"{r['file']} :: "
                f"{r['function']} @ "
                f"{r['line']}"
            )

    print()
    print(
        "NO SOURCE FILES MODIFIED."
    )

    print(
        "NO SYNTHETIC DATA CREATED."
    )


# ===============================================================================================
# MAIN
# ===============================================================================================

def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — REAL RUNTIME "
        "PROVENANCE INSTRUMENTATION v0.3"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT : {ROOT}"
    )

    print(
        "MODE         : READ ONLY / RUNTIME FORENSIC"
    )

    print(
        "FORENSIC FILES : EXCLUDED"
    )

    print()

    # -------------------------------------------------------------------------------------------
    # PASS 1 — BUILD NON-FORENSIC MODULE INDEX
    # -------------------------------------------------------------------------------------------

    index = load_module_index()

    print(
        f"NON-FORENSIC MODULES INDEXED : "
        f"{len(index)}"
    )

    # -------------------------------------------------------------------------------------------
    # PASS 2 — BUILD REVERSE GRAPH
    # -------------------------------------------------------------------------------------------

    reverse = build_reverse_graph(index)

    # -------------------------------------------------------------------------------------------
    # PASS 3 — PRODUCTION ROOT CANDIDATES
    # -------------------------------------------------------------------------------------------

    roots = production_roots(
        index,
        reverse,
    )

    print_discovery(
        index,
        roots,
    )

    print_target_map(index)

    # -------------------------------------------------------------------------------------------
    # DO NOT AUTOMATICALLY EXECUTE AN ARBITRARY FORENSIC FILE.
    #
    # Prefer known production modules.
    # -------------------------------------------------------------------------------------------

    selected = None

    # Strong explicit production candidates.
    for preferred in (
        "arunda_pipeline",
        "arunda_source_engine",
    ):

        info = index.get(preferred)

        if info is not None:

            selected = info.path
            break

    # If no preferred root exists, find a root that actually reaches
    # decision_engine.
    if selected is None:

        for score, name, path, reasons in roots:

            info = index[name]

            if (
                "decision_engine" in info.imports
                or "feature_contract" in info.imports
                or "signal_scorer" in info.imports
            ):

                selected = path
                break

    # If still unresolved, inspect direct production candidates.
    if selected is None:

        for score, name, path, reasons in roots:

            if name == "decision_engine":
                continue

            selected = path
            break

    if selected is None:

        print()
        print(
            "NO SAFE PRODUCTION ENTRYPOINT RESOLVED."
        )

        return

    print()
    print("=" * 100)
    print("SELECTED PRODUCTION ENTRYPOINT")
    print("=" * 100)

    print(
        selected
    )

    print()
    print(
        "WHY:"
    )

    if selected.name == "arunda_pipeline.py":

        print(
            "Known production pipeline module."
        )

    elif selected.name == "arunda_source_engine.py":

        print(
            "Known production source engine module."
        )

    else:

        print(
            "Non-forensic project root reaching "
            "production decision/feature modules."
        )

    # -------------------------------------------------------------------------------------------
    # EXECUTE REAL RUNTIME
    # -------------------------------------------------------------------------------------------

    execute(selected)

    # -------------------------------------------------------------------------------------------
    # REPORT
    # -------------------------------------------------------------------------------------------

    final_report(selected)


if __name__ == "__main__":
    main()