from __future__ import annotations

import ast
import os
from pathlib import Path


# =============================================================================
# ARUNDA PROJECT — PIPELINE REAL ENTRYPOINT FORENSIC v0.1
# =============================================================================
#
# PURPOSE:
#   Resolve, statically and read-only, which project Python files can actually
#   execute arunda_pipeline.py.
#
# TARGET:
#   arunda_pipeline.py
#
# IMPORTANT:
#   - String references are NOT execution.
#   - Comments are NOT execution.
#   - print("arunda_pipeline.py") is NOT execution.
#   - This artifact does NOT execute project code.
#   - This artifact does NOT import project modules.
#   - This artifact does NOT access SQLite/database.
#   - This artifact does NOT access network.
#   - This artifact does NOT modify project files.
#
# EXECUTABLE RELATION TYPES:
#   1. import arunda_pipeline
#   2. from arunda_pipeline import ...
#   3. subprocess / os.system / os.popen / spawn / exec with a statically
#      identifiable target of arunda_pipeline.py
#   4. runpy.run_path("arunda_pipeline.py")
#   5. runpy.run_module("arunda_pipeline")
#
# DYNAMIC / UNKNOWN:
#   If execution target is held in a variable or constructed dynamically and
#   cannot be resolved statically, report it separately.
#
# SELF EXCLUSION:
#   This forensic artifact and other ARUNDA_PROJECT_* forensic artifacts are
#   excluded from caller classification unless they contain a genuine
#   executable relation.
#
# =============================================================================


PROJECT_DIR = Path(__file__).resolve().parent
TARGET_NAME = "arunda_pipeline.py"
TARGET_MODULE = "arunda_pipeline"
TARGET_PATH = PROJECT_DIR / TARGET_NAME


FORENSIC_PREFIX = "ARUNDA_PROJECT_"


# =============================================================================
# AST HELPERS
# =============================================================================

def safe_read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig")
        except Exception:
            return None
    except Exception:
        return None


def parse_ast(path: Path) -> ast.AST | None:
    text = safe_read(path)

    if text is None:
        return None

    try:
        return ast.parse(text, filename=str(path))
    except Exception:
        return None


def constant_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    return None


def dotted_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    return None


def line_of(node: ast.AST) -> int:
    return getattr(node, "lineno", -1)


def source_segment(source: str, node: ast.AST) -> str:
    try:
        return ast.get_source_segment(source, node) or ""
    except Exception:
        return ""


# =============================================================================
# TARGET MATCHING
# =============================================================================

def matches_target_string(value: str) -> bool:
    normalized = value.replace("\\", "/").strip()

    basename = Path(normalized).name.lower()

    if basename == TARGET_NAME.lower():
        return True

    if normalized.lower() == TARGET_MODULE.lower():
        return True

    if normalized.lower().endswith("/" + TARGET_NAME.lower()):
        return True

    return False


# =============================================================================
# IMPORT ANALYSIS
# =============================================================================

def analyze_import(node: ast.AST) -> dict | None:

    if isinstance(node, ast.Import):

        for alias in node.names:

            if alias.name == TARGET_MODULE:
                return {
                    "type": "DIRECT_IMPORT",
                    "line": line_of(node),
                    "target": TARGET_NAME,
                    "detail": f"import {alias.name}",
                }

            if alias.name.endswith("." + TARGET_MODULE):
                return {
                    "type": "DIRECT_IMPORT",
                    "line": line_of(node),
                    "target": TARGET_NAME,
                    "detail": f"import {alias.name}",
                }

    if isinstance(node, ast.ImportFrom):

        module = node.module or ""

        if module == TARGET_MODULE or module.endswith("." + TARGET_MODULE):

            return {
                "type": "FROM_IMPORT",
                "line": line_of(node),
                "target": TARGET_NAME,
                "detail": f"from {module} import ...",
            }

    return None


# =============================================================================
# SUBPROCESS / OS EXECUTION ANALYSIS
# =============================================================================

EXEC_CALL_NAMES = {
    "subprocess.run",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "os.spawnl",
    "os.spawnle",
    "os.spawnlp",
    "os.spawnlpe",
    "os.spawnv",
    "os.spawnve",
    "os.spawnvp",
    "os.spawnvpe",
}


RUNPY_CALL_NAMES = {
    "runpy.run_path",
    "runpy.run_module",
}


def analyze_execution_call(
    node: ast.Call,
    source: str,
) -> dict | None:

    function_name = dotted_name(node.func)

    if function_name in RUNPY_CALL_NAMES:

        for arg in node.args:

            value = constant_string(arg)

            if value is None:
                continue

            if matches_target_string(value):

                return {
                    "type": "RUNPY_EXECUTION",
                    "line": line_of(node),
                    "target": TARGET_NAME,
                    "detail": source_segment(source, node),
                }

    if function_name in EXEC_CALL_NAMES:

        # -------------------------------------------------------------
        # Static string arguments
        # -------------------------------------------------------------

        for arg in node.args:

            value = constant_string(arg)

            if value is not None and matches_target_string(value):

                return {
                    "type": "SUBPROCESS_EXECUTION",
                    "line": line_of(node),
                    "target": TARGET_NAME,
                    "detail": source_segment(source, node),
                }

        # -------------------------------------------------------------
        # List / tuple command:
        #
        # subprocess.run(["python", "arunda_pipeline.py"])
        # -------------------------------------------------------------

        for arg in node.args:

            if isinstance(arg, (ast.List, ast.Tuple)):

                for element in arg.elts:

                    value = constant_string(element)

                    if value is not None and matches_target_string(value):

                        return {
                            "type": "SUBPROCESS_EXECUTION",
                            "line": line_of(node),
                            "target": TARGET_NAME,
                            "detail": source_segment(source, node),
                        }

        # -------------------------------------------------------------
        # Keyword arguments such as:
        #
        # subprocess.run(args=["python", "arunda_pipeline.py"])
        # -------------------------------------------------------------

        for keyword in node.keywords:

            value = constant_string(keyword.value)

            if value is not None and matches_target_string(value):

                return {
                    "type": "SUBPROCESS_EXECUTION",
                    "line": line_of(node),
                    "target": TARGET_NAME,
                    "detail": source_segment(source, node),
                }

            if isinstance(keyword.value, (ast.List, ast.Tuple)):

                for element in keyword.value.elts:

                    value = constant_string(element)

                    if value is not None and matches_target_string(value):

                        return {
                            "type": "SUBPROCESS_EXECUTION",
                            "line": line_of(node),
                            "target": TARGET_NAME,
                            "detail": source_segment(source, node),
                        }

    return None


# =============================================================================
# DYNAMIC EXECUTION DETECTION
# =============================================================================

def is_dynamic_execution_reference(
    node: ast.Call,
    source: str,
) -> dict | None:

    function_name = dotted_name(node.func)

    if function_name not in (
        EXEC_CALL_NAMES
        | RUNPY_CALL_NAMES
    ):
        return None

    static_target_found = False

    for arg in node.args:

        value = constant_string(arg)

        if value is not None and matches_target_string(value):
            static_target_found = True

        if isinstance(arg, (ast.List, ast.Tuple)):

            for element in arg.elts:

                value = constant_string(element)

                if value is not None and matches_target_string(value):
                    static_target_found = True

    for keyword in node.keywords:

        value = constant_string(keyword.value)

        if value is not None and matches_target_string(value):
            static_target_found = True

        if isinstance(keyword.value, (ast.List, ast.Tuple)):

            for element in keyword.value.elts:

                value = constant_string(element)

                if value is not None and matches_target_string(value):
                    static_target_found = True

    if not static_target_found:

        return {
            "type": "DYNAMIC_EXECUTION_UNRESOLVED",
            "line": line_of(node),
            "target": TARGET_NAME,
            "detail": source_segment(source, node),
        }

    return None


# =============================================================================
# FILE ANALYSIS
# =============================================================================

def analyze_file(path: Path) -> dict:

    result = {
        "file": str(path),
        "imports": [],
        "executions": [],
        "dynamic_unresolved": [],
        "parse_error": False,
    }

    source = safe_read(path)

    if source is None:
        result["parse_error"] = True
        return result

    try:
        tree = ast.parse(source, filename=str(path))
    except Exception:
        result["parse_error"] = True
        return result

    for node in ast.walk(tree):

        import_hit = analyze_import(node)

        if import_hit:
            result["imports"].append(import_hit)

        if isinstance(node, ast.Call):

            execution_hit = analyze_execution_call(
                node,
                source,
            )

            if execution_hit:
                result["executions"].append(execution_hit)
                continue

            dynamic_hit = is_dynamic_execution_reference(
                node,
                source,
            )

            if dynamic_hit:
                result["dynamic_unresolved"].append(dynamic_hit)

    return result


# =============================================================================
# PROJECT SCAN
# =============================================================================

def scan_project() -> list[dict]:

    reports = []

    for path in sorted(PROJECT_DIR.glob("*.py")):

        # -------------------------------------------------------------
        # Do not classify the forensic script itself as its own caller.
        # -------------------------------------------------------------

        if path.resolve() == Path(__file__).resolve():
            continue

        report = analyze_file(path)

        reports.append(report)

    return reports


# =============================================================================
# CLASSIFICATION
# =============================================================================

def classify_reports(reports: list[dict]) -> dict:

    direct_importers = []
    executable_callers = []
    dynamic_unknown = []
    parse_errors = []

    for report in reports:

        if report["parse_error"]:
            parse_errors.append(report)
            continue

        if report["imports"]:
            direct_importers.append(report)

        if report["executions"]:
            executable_callers.append(report)

        if report["dynamic_unresolved"]:
            dynamic_unknown.append(report)

    return {
        "direct_importers": direct_importers,
        "executable_callers": executable_callers,
        "dynamic_unknown": dynamic_unknown,
        "parse_errors": parse_errors,
    }


# =============================================================================
# REPORT
# =============================================================================

def print_header():

    print("=" * 110)
    print("ARUNDA PROJECT — PIPELINE REAL ENTRYPOINT FORENSIC v0.1")
    print("=" * 110)

    print("MODE                : READ ONLY")
    print("STATIC ANALYSIS     : YES")
    print("DATABASE ACCESS     : NO")
    print("NETWORK ACCESS      : NO")
    print("PROJECT EXECUTION   : NO")
    print("FILE MODIFICATION   : NO")

    print()
    print("-" * 110)
    print("TARGET")
    print("-" * 110)

    print(f"PROJECT DIR         : {PROJECT_DIR}")
    print(f"TARGET FILE         : {TARGET_PATH}")
    print(f"TARGET MODULE       : {TARGET_MODULE}")


def print_imports(items: list[dict]):

    print()
    print("-" * 110)
    print("1. DIRECT IMPORTERS")
    print("-" * 110)

    if not items:
        print("NONE")
        return

    for report in items:

        print()
        print(f"FILE : {report['file']}")

        for item in report["imports"]:

            print(f"  LINE : {item['line']}")
            print(f"  TYPE : {item['type']}")
            print(f"  CALL : {item['detail']}")


def print_executions(items: list[dict]):

    print()
    print("-" * 110)
    print("2. REAL EXECUTABLE REFERENCES")
    print("-" * 110)

    if not items:
        print("NONE")
        return

    for report in items:

        print()
        print(f"FILE : {report['file']}")

        for item in report["executions"]:

            print(f"  LINE   : {item['line']}")
            print(f"  TYPE   : {item['type']}")
            print(f"  TARGET : {item['target']}")
            print(f"  CALL   : {item['detail']}")


def print_dynamic(items: list[dict]):

    print()
    print("-" * 110)
    print("3. DYNAMIC EXECUTION REFERENCES — STATICALLY UNRESOLVED")
    print("-" * 110)

    if not items:
        print("NONE")
        return

    for report in items:

        print()
        print(f"FILE : {report['file']}")

        for item in report["dynamic_unresolved"]:

            print(f"  LINE   : {item['line']}")
            print(f"  TYPE   : {item['type']}")
            print(f"  TARGET : {item['target']}")
            print(f"  CALL   : {item['detail']}")


def print_parse_errors(items: list[dict]):

    print()
    print("-" * 110)
    print("4. PARSE ERRORS")
    print("-" * 110)

    if not items:
        print("NONE")
        return

    for report in items:

        print(report["file"])


def print_verdict(classification: dict):

    imports = classification["direct_importers"]
    callers = classification["executable_callers"]
    dynamic = classification["dynamic_unknown"]

    print()
    print("=" * 110)
    print("AUTHORITATIVE STATIC CONCLUSION")
    print("=" * 110)

    if callers:

        print("STATUS : REAL_PIPELINE_CALLER_FOUND")

    elif imports:

        print("STATUS : PIPELINE_IMPORTED_BUT_DIRECT_EXECUTION_NOT_FOUND")

    elif dynamic:

        print("STATUS : PIPELINE_ENTRYPOINT_DYNAMIC_UNRESOLVED")

    else:

        print("STATUS : NO_REAL_PIPELINE_CALLER_FOUND")

    print()
    print("IMPORTANT:")
    print("  String references are NOT treated as execution.")
    print("  print() references are NOT treated as execution.")
    print("  Comments are NOT treated as execution.")
    print("  Forensic artifacts are NOT treated as callers merely because")
    print("  they contain the target filename in report text.")

    print()
    print("TARGET:")
    print("  REAL CALLER")
    print("      -> arunda_pipeline.py")

    print()
    print(f"DIRECT IMPORTERS          : {len(imports)}")
    print(f"REAL EXECUTABLE CALLERS   : {len(callers)}")
    print(f"DYNAMIC UNRESOLVED         : {len(dynamic)}")
    print(
        f"PARSE ERRORS              : "
        f"{len(classification['parse_errors'])}"
    )

    print()
    print("=" * 110)


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header()

    if not TARGET_PATH.exists():

        print()
        print("FATAL : arunda_pipeline.py NOT FOUND")
        return 2

    reports = scan_project()

    classification = classify_reports(reports)

    print_imports(
        classification["direct_importers"]
    )

    print_executions(
        classification["executable_callers"]
    )

    print_dynamic(
        classification["dynamic_unknown"]
    )

    print_parse_errors(
        classification["parse_errors"]
    )

    print_verdict(classification)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())