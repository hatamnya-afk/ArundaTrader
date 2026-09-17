from pathlib import Path
import ast
import sys


# =============================================================================
# ARUNDA PROJECT — PIPELINE EXTERNAL CALLER AND UPGRADE_DB CALLER FORENSIC v0.1
# =============================================================================
#
# PURPOSE:
#
#   Find the external/static callers of:
#
#       1. arunda_pipeline.py
#       2. upgrade_db.py
#
#   WITHOUT executing the project.
#
# TARGET:
#
#   launcher
#       ↓
#   arunda_pipeline.py
#
#   and independently:
#
#   launcher / caller
#       ↓
#   upgrade_db.py
#
# SAFETY:
#
#   READ ONLY
#   STATIC ONLY
#   NO DATABASE
#   NO NETWORK
#   NO PROJECT EXECUTION
#   NO FILE MODIFICATION
#
# =============================================================================


PROJECT_DIR = Path(__file__).resolve().parent

PIPELINE_FILE = "arunda_pipeline.py"
UPGRADE_FILE = "upgrade_db.py"

IGNORED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
}


# =============================================================================
# HELPERS
# =============================================================================

def is_ignored(path: Path) -> bool:
    return any(
        part in IGNORED_DIRS
        for part in path.parts
    )


def read_python(path: Path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return None


def parse_python(path: Path):
    source = read_python(path)

    if source is None:
        return None, None

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
        return source, tree

    except SyntaxError:
        return source, None


def line_text(source, line_number):
    if not source:
        return ""

    lines = source.splitlines()

    if line_number < 1:
        return ""

    if line_number > len(lines):
        return ""

    return lines[line_number - 1]


def call_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        parts = []

        current = node

        while isinstance(
            current,
            ast.Attribute,
        ):

            parts.append(
                current.attr
            )

            current = current.value

        if isinstance(
            current,
            ast.Name,
        ):

            parts.append(
                current.id
            )

            return ".".join(
                reversed(parts)
            )

    return None


def is_target_string(value, target):
    if not isinstance(value, str):
        return False

    normalized = value.replace(
        "\\",
        "/",
    )

    return (
        normalized == target
        or normalized.endswith(
            "/" + target
        )
    )


def string_matches_target(
    node,
    target,
):
    if isinstance(
        node,
        ast.Constant,
    ):

        return is_target_string(
            node.value,
            target,
        )

    return False


# =============================================================================
# PROJECT FILE DISCOVERY
# =============================================================================

def discover_python_files():

    files = []

    for path in PROJECT_DIR.rglob("*.py"):

        if is_ignored(path):
            continue

        files.append(path)

    files.sort(
        key=lambda p: str(p).lower()
    )

    return files


# =============================================================================
# REFERENCE CLASSIFICATION
# =============================================================================

def classify_call(
    call_node,
    target,
):

    name = call_name(
        call_node.func
    )

    # ---------------------------------------------------------
    # Direct module import execution:
    #
    # import upgrade_db
    # from upgrade_db import ...
    # ---------------------------------------------------------

    if name:

        normalized = name.lower()

        target_stem = target[:-3].lower()

        if normalized == target_stem:
            return "DIRECT_MODULE_CALL"

        if normalized.endswith(
            "." + target_stem
        ):
            return "QUALIFIED_MODULE_CALL"

    # ---------------------------------------------------------
    # subprocess / os.system / runpy style references
    # ---------------------------------------------------------

    expression = None

    try:
        expression = ast.unparse(
            call_node
        )
    except Exception:
        expression = ""

    lower = expression.lower()

    target_lower = target.lower()

    if target_lower in lower:

        if (
            "subprocess" in lower
            or "os.system" in lower
            or "runpy" in lower
            or "exec" in lower
        ):

            return "DYNAMIC_EXECUTION_REFERENCE"

        return "CALL_CONTAINS_TARGET"

    return None


# =============================================================================
# ANALYZE ONE FILE
# =============================================================================

def analyze_file(
    path,
    target,
):

    source, tree = parse_python(
        path
    )

    result = {
        "file": path,
        "target": target,
        "parse_ok": tree is not None,
        "string_hits": [],
        "import_hits": [],
        "call_hits": [],
        "subprocess_hits": [],
        "assignment_hits": [],
    }

    if tree is None:
        return result

    # -------------------------------------------------------------------------
    # AST WALK
    # -------------------------------------------------------------------------

    for node in ast.walk(tree):

        line = getattr(
            node,
            "lineno",
            None,
        )

        # =====================================================================
        # IMPORTS
        # =====================================================================

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                if (
                    alias.name == target[:-3]
                    or alias.name.endswith(
                        "." + target[:-3]
                    )
                ):

                    result[
                        "import_hits"
                    ].append(
                        {
                            "line": line,
                            "type": "import",
                            "name": alias.name,
                        }
                    )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            module = node.module or ""

            if (
                module == target[:-3]
                or module.endswith(
                    "." + target[:-3]
                )
            ):

                result[
                    "import_hits"
                ].append(
                    {
                        "line": line,
                        "type": "from_import",
                        "module": module,
                    }
                )

        # =====================================================================
        # CALLS
        # =====================================================================

        elif isinstance(
            node,
            ast.Call,
        ):

            classification = classify_call(
                node,
                target,
            )

            if classification:

                try:
                    expression = ast.unparse(
                        node
                    )
                except Exception:
                    expression = "<UNPARSEABLE>"

                result[
                    "call_hits"
                ].append(
                    {
                        "line": line,
                        "classification": classification,
                        "expression": expression,
                    }
                )

                lower = expression.lower()

                if (
                    "subprocess" in lower
                    and target.lower()
                    in lower
                ):

                    result[
                        "subprocess_hits"
                    ].append(
                        {
                            "line": line,
                            "expression": expression,
                        }
                    )

        # =====================================================================
        # ASSIGNMENTS CONTAINING TARGET
        # =====================================================================

        elif isinstance(
            node,
            ast.Assign,
        ):

            try:
                expression = ast.unparse(
                    node
                )
            except Exception:
                expression = ""

            if target.lower() in expression.lower():

                result[
                    "assignment_hits"
                ].append(
                    {
                        "line": line,
                        "expression": expression,
                    }
                )

    # =========================================================================
    # RAW STRING SCAN
    # =========================================================================

    if source:

        for number, text in enumerate(
            source.splitlines(),
            start=1,
        ):

            if target.lower() in text.lower():

                result[
                    "string_hits"
                ].append(
                    {
                        "line": number,
                        "text": text,
                    }
                )

    return result


# =============================================================================
# PRINT RESULT SECTION
# =============================================================================

def print_target_report(
    target,
    results,
):

    print()
    print("=" * 110)

    print(
        f"TARGET : {target}"
    )

    print("=" * 110)

    direct_importers = []
    dynamic_callers = []
    raw_only = []

    for result in results:

        if result["import_hits"]:
            direct_importers.append(
                result
            )

        if (
            result["call_hits"]
            or result["subprocess_hits"]
        ):
            dynamic_callers.append(
                result
            )

        if (
            result["string_hits"]
            and not result["import_hits"]
            and not result["call_hits"]
            and not result["subprocess_hits"]
        ):
            raw_only.append(
                result
            )

    # =========================================================================
    # DIRECT IMPORTERS
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "1. DIRECT IMPORTERS"
    )

    print("-" * 110)

    if not direct_importers:

        print(
            "NONE"
        )

    else:

        for result in direct_importers:

            print()
            print(
                f"FILE : {result['file']}"
            )

            for item in result[
                "import_hits"
            ]:

                print(
                    f"  LINE {item['line']} : "
                    f"{item}"
                )

    # =========================================================================
    # CALLERS / DYNAMIC EXECUTION
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "2. CALLS / DYNAMIC EXECUTION REFERENCES"
    )

    print("-" * 110)

    if not dynamic_callers:

        print(
            "NONE"
        )

    else:

        for result in dynamic_callers:

            print()
            print(
                f"FILE : {result['file']}"
            )

            for item in result[
                "call_hits"
            ]:

                print(
                    f"  LINE {item['line']}"
                )

                print(
                    f"  TYPE : {item['classification']}"
                )

                print(
                    f"  CALL : {item['expression']}"
                )

    # =========================================================================
    # SUBPROCESS
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "3. SUBPROCESS REFERENCES"
    )

    print("-" * 110)

    found_subprocess = False

    for result in results:

        for item in result[
            "subprocess_hits"
        ]:

            found_subprocess = True

            print()
            print(
                f"FILE : {result['file']}"
            )

            print(
                f"LINE : {item['line']}"
            )

            print(
                f"CALL : {item['expression']}"
            )

    if not found_subprocess:

        print(
            "NONE"
        )

    # =========================================================================
    # RAW TEXT ONLY
    # =========================================================================

    print()
    print("-" * 110)

    print(
        "4. RAW TEXT REFERENCES WITHOUT EXECUTABLE AST RELATION"
    )

    print("-" * 110)

    if not raw_only:

        print(
            "NONE"
        )

    else:

        for result in raw_only:

            print()
            print(
                f"FILE : {result['file']}"
            )

            for item in result[
                "string_hits"
            ]:

                print(
                    f"  LINE {item['line']} : "
                    f"{item['text']}"
                )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 110)
    print(
        "ARUNDA PROJECT — PIPELINE EXTERNAL CALLER AND UPGRADE_DB CALLER FORENSIC v0.1"
    )
    print("=" * 110)

    print(
        "MODE                : READ ONLY"
    )

    print(
        "STATIC ANALYSIS     : YES"
    )

    print(
        "DATABASE ACCESS     : NO"
    )

    print(
        "NETWORK ACCESS      : NO"
    )

    print(
        "PROJECT EXECUTION   : NO"
    )

    print(
        "FILE MODIFICATION   : NO"
    )

    print()
    print("-" * 110)

    print(
        "PROJECT"
    )

    print("-" * 110)

    print(
        f"PROJECT DIR         : {PROJECT_DIR}"
    )

    print(
        f"PIPELINE            : {PIPELINE_FILE}"
    )

    print(
        f"UPGRADE_DB          : {UPGRADE_FILE}"
    )

    # =========================================================================
    # DISCOVER
    # =========================================================================

    files = discover_python_files()

    print()
    print(
        f"PYTHON FILES SCANNED : {len(files)}"
    )

    # =========================================================================
    # ANALYZE PIPELINE
    # =========================================================================

    pipeline_results = []

    for path in files:

        if path.name == PIPELINE_FILE:
            continue

        result = analyze_file(
            path,
            PIPELINE_FILE,
        )

        if (
            result["string_hits"]
            or result["import_hits"]
            or result["call_hits"]
            or result["subprocess_hits"]
        ):

            pipeline_results.append(
                result
            )

    # =========================================================================
    # ANALYZE UPGRADE_DB
    # =========================================================================

    upgrade_results = []

    for path in files:

        if path.name == UPGRADE_FILE:
            continue

        result = analyze_file(
            path,
            UPGRADE_FILE,
        )

        if (
            result["string_hits"]
            or result["import_hits"]
            or result["call_hits"]
            or result["subprocess_hits"]
        ):

            upgrade_results.append(
                result
            )

    # =========================================================================
    # REPORT PIPELINE
    # =========================================================================

    print()
    print("=" * 110)

    print(
        "A. EXTERNAL CALLERS OF arunda_pipeline.py"
    )

    print("=" * 110)

    if not pipeline_results:

        print(
            "NO REFERENCES FOUND OUTSIDE arunda_pipeline.py"
        )

    else:

        print_target_report(
            PIPELINE_FILE,
            pipeline_results,
        )

    # =========================================================================
    # REPORT UPGRADE_DB
    # =========================================================================

    print()
    print("=" * 110)

    print(
        "B. EXTERNAL CALLERS OF upgrade_db.py"
    )

    print("=" * 110)

    if not upgrade_results:

        print(
            "NO REFERENCES FOUND OUTSIDE upgrade_db.py"
        )

    else:

        print_target_report(
            UPGRADE_FILE,
            upgrade_results,
        )

    # =========================================================================
    # CROSS-TARGET RELATION
    # =========================================================================

    print()
    print("=" * 110)

    print(
        "C. CROSS-TARGET RELATION"
    )

    print("=" * 110)

    pipeline_caller_files = {
        str(
            result["file"]
        )
        for result in pipeline_results
        if (
            result["import_hits"]
            or result["call_hits"]
            or result["subprocess_hits"]
        )
    }

    upgrade_caller_files = {
        str(
            result["file"]
        )
        for result in upgrade_results
        if (
            result["import_hits"]
            or result["call_hits"]
            or result["subprocess_hits"]
        )
    }

    common_callers = (
        pipeline_caller_files
        & upgrade_caller_files
    )

    print()
    print(
        "EXECUTABLE CALLER FILES OF PIPELINE:"
    )

    if pipeline_caller_files:

        for item in sorted(
            pipeline_caller_files
        ):

            print(
                f"  {item}"
            )

    else:

        print(
            "  NONE"
        )

    print()
    print(
        "EXECUTABLE CALLER FILES OF UPGRADE_DB:"
    )

    if upgrade_caller_files:

        for item in sorted(
            upgrade_caller_files
        ):

            print(
                f"  {item}"
            )

    else:

        print(
            "  NONE"
        )

    print()
    print(
        "COMMON EXECUTABLE CALLER FILES:"
    )

    if common_callers:

        for item in sorted(
            common_callers
        ):

            print(
                f"  {item}"
            )

    else:

        print(
            "  NONE"
        )

    # =========================================================================
    # AUTHORITATIVE CONCLUSION
    # =========================================================================

    print()
    print("=" * 110)

    print(
        "D. AUTHORITATIVE STATIC CONCLUSION"
    )

    print("=" * 110)

    has_pipeline_executable = bool(
        pipeline_caller_files
    )

    has_upgrade_executable = bool(
        upgrade_caller_files
    )

    if (
        has_pipeline_executable
        and has_upgrade_executable
        and common_callers
    ):

        status = (
            "COMMON_EXTERNAL_CALLER_EXISTS"
        )

    elif (
        has_pipeline_executable
        and has_upgrade_executable
    ):

        status = (
            "PIPELINE_AND_UPGRADE_DB_HAVE_SEPARATE_EXTERNAL_CALLERS"
        )

    elif has_upgrade_executable:

        status = (
            "UPGRADE_DB_EXTERNAL_CALLER_FOUND_PIPELINE_CALLER_NOT_FOUND"
        )

    elif has_pipeline_executable:

        status = (
            "PIPELINE_EXTERNAL_CALLER_FOUND_UPGRADE_DB_CALLER_NOT_FOUND"
        )

    else:

        status = (
            "NO_EXECUTABLE_EXTERNAL_CALLERS_FOUND"
        )

    print()
    print(
        f"STATUS              : {status}"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "RAW STRING REFERENCES ARE NOT TREATED AS EXECUTION."
    )

    print(
        "IMPORTS / CALLS / SUBPROCESS REFERENCES ARE REPORTED SEPARATELY."
    )

    print()
    print(
        "TARGET A:"
    )

    print(
        "launcher -> arunda_pipeline.py"
    )

    print()
    print(
        "TARGET B:"
    )

    print(
        "launcher / external caller -> upgrade_db.py"
    )

    print()
    print(
        "READ ONLY           : YES"
    )

    print(
        "STATIC ONLY         : YES"
    )

    print(
        "DATABASE            : NONE"
    )

    print(
        "NETWORK             : NONE"
    )

    print(
        "PROJECT EXECUTION   : NONE"
    )

    print(
        "FILE MODIFICATION   : NONE"
    )

    print("=" * 110)

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    sys.exit(
        main()
    )