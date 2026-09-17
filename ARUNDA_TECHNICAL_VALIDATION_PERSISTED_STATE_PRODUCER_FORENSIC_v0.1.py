import ast
import hashlib
import re
from pathlib import Path
from collections import defaultdict


# =============================================================================
# ARUNDA
# TECHNICAL VALIDATION PERSISTED STATE PRODUCER FORENSIC v0.1
# =============================================================================
#
# FILE:
#     ARUNDA_TECHNICAL_VALIDATION_PERSISTED_STATE_PRODUCER_FORENSIC_v0.1.py
#
# MODE:
#     READ ONLY / AST DISCOVERY
#
# PURPOSE:
#     Discover the exact source-level producer(s) responsible for:
#
#         technical_validation_score
#         technical_validation_status
#         technical_validation_flags
#         technical_validation_version
#         technical_validated_at
#
#     with special forensic focus on persisted state:
#
#         version = 0.5.0
#         INVALID_REGIME
#         INVALID_VOLATILITY
#
# IMPORTANT:
#
#     This forensic:
#
#         DOES NOT import production modules.
#         DOES NOT execute production main().
#         DOES NOT execute arbitrary production functions.
#         DOES NOT connect to SQLite.
#         DOES NOT modify database.
#
#     It performs SOURCE / AST discovery only.
#
# NO:
#     INSERT
#     UPDATE
#     DELETE
#     ALTER
#     CREATE
#     DROP
#     REPLACE
#     COMMIT
#     ROLLBACK
#
# NO SYNTHETIC DATA.
#
# =============================================================================


PROJECT_DIR = Path(__file__).resolve().parent

PRODUCTION_ENGINE = (
    PROJECT_DIR / "market_technical_engine.py"
)

TARGET_TABLE = "market_technical"

TARGET_FIELDS = [
    "technical_validation_score",
    "technical_validation_status",
    "technical_validation_flags",
    "technical_validation_version",
    "technical_validated_at",
]

TARGET_VERSION = "0.5.0"

TARGET_FLAGS = [
    "INVALID_REGIME",
    "INVALID_VOLATILITY",
]

TARGET_STATUSES = [
    "VALID",
    "PARTIAL",
    "INVALID",
    "UNAVAILABLE",
]

SOURCE_EXTENSIONS = {
    ".py",
}

IGNORE_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

MAX_CONTEXT_LINES = 12


# =============================================================================
# OUTPUT
# =============================================================================

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def kv(key, value):
    print(f"{key:<55}: {value}")


def safe(value):
    if value is None:
        return "NULL"
    return str(value)


# =============================================================================
# FILE HASH
# =============================================================================

def sha256_file(path):

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(chunk)

    return h.hexdigest()


# =============================================================================
# SOURCE DISCOVERY
# =============================================================================

def discover_python_files():

    files = []

    for path in PROJECT_DIR.rglob("*.py"):

        relative_parts = path.relative_to(
            PROJECT_DIR
        ).parts

        if any(
            part in IGNORE_DIRS
            for part in relative_parts
        ):
            continue

        files.append(path)

    return sorted(
        set(files)
    )


# =============================================================================
# AST HELPERS
# =============================================================================

def get_function_name_stack(tree):

    parents = {}

    for parent in ast.walk(tree):

        for child in ast.iter_child_nodes(parent):

            parents[child] = parent

    return parents


def resolve_function(node, parents):

    current = node
    names = []

    while current in parents:

        current = parents[current]

        if isinstance(
            current,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):
            names.append(
                current.name
            )

        elif isinstance(
            current,
            ast.ClassDef
        ):
            names.append(
                current.name
            )

    if names:
        return ".".join(
            reversed(names)
        )

    return "<MODULE>"


def source_segment(source, node):

    try:

        segment = ast.get_source_segment(
            source,
            node
        )

        if segment:
            return segment.strip()

    except Exception:
        pass

    return ""


def line_context(
    source_lines,
    line_number,
    radius=MAX_CONTEXT_LINES
):

    start = max(
        1,
        line_number - radius
    )

    end = min(
        len(source_lines),
        line_number + radius
    )

    output = []

    for number in range(
        start,
        end + 1
    ):

        output.append(
            f"{number:5d}: "
            f"{source_lines[number - 1]}"
        )

    return output


# =============================================================================
# SEARCH RESULT STORAGE
# =============================================================================

class Finding:

    def __init__(
        self,
        path,
        line,
        category,
        token,
        function,
        source
    ):

        self.path = path
        self.line = line
        self.category = category
        self.token = token
        self.function = function
        self.source = source


# =============================================================================
# AST DISCOVERY
# =============================================================================

def inspect_file(path):

    findings = []

    try:

        source = path.read_text(
            encoding="utf-8-sig",
            errors="strict"
        )

    except Exception as exc:

        print(
            f"[READ ERROR] {path}: {exc}"
        )

        return findings

    try:

        tree = ast.parse(
            source,
            filename=str(path)
        )

    except Exception as exc:

        print(
            f"[AST ERROR] {path}: {exc}"
        )

        return findings

    parents = get_function_name_stack(
        tree
    )

    lines = source.splitlines()

    # -------------------------------------------------------------------------
    # CONSTANT / STRING LITERALS
    # -------------------------------------------------------------------------

    for node in ast.walk(tree):

        function = resolve_function(
            node,
            parents
        )

        # Literal strings
        if isinstance(
            node,
            ast.Constant
        ) and isinstance(
            node.value,
            str
        ):

            value = node.value

            for target in TARGET_FIELDS:

                if target in value:

                    findings.append(
                        Finding(
                            path,
                            node.lineno,
                            "FIELD_LITERAL",
                            target,
                            function,
                            source_segment(
                                source,
                                node
                            )
                        )
                    )

            if TARGET_VERSION in value:

                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "VERSION_LITERAL",
                        TARGET_VERSION,
                        function,
                        source_segment(
                            source,
                            node
                        )
                    )
                )

            for flag in TARGET_FLAGS:

                if flag in value:

                    findings.append(
                        Finding(
                            path,
                            node.lineno,
                            "FLAG_LITERAL",
                            flag,
                            function,
                            source_segment(
                                source,
                                node
                            )
                        )
                    )

        # ---------------------------------------------------------------------
        # NAME REFERENCES
        # ---------------------------------------------------------------------

        if isinstance(
            node,
            ast.Name
        ):

            if node.id in TARGET_FIELDS:

                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "FIELD_REFERENCE",
                        node.id,
                        function,
                        source_segment(
                            source,
                            node
                        )
                    )
                )

        # ---------------------------------------------------------------------
        # ATTRIBUTE REFERENCES
        # ---------------------------------------------------------------------

        if isinstance(
            node,
            ast.Attribute
        ):

            if node.attr in TARGET_FIELDS:

                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "FIELD_ATTRIBUTE",
                        node.attr,
                        function,
                        source_segment(
                            source,
                            node
                        )
                    )
                )

        # ---------------------------------------------------------------------
        # SQL STRING / UPDATE DETECTION
        # ---------------------------------------------------------------------

        if isinstance(
            node,
            ast.Constant
        ) and isinstance(
            node.value,
            str
        ):

            upper = node.value.upper()

            if (
                "UPDATE " in upper
                or "INSERT INTO" in upper
                or "REPLACE INTO" in upper
            ):

                for field in TARGET_FIELDS:

                    if field in node.value:

                        findings.append(
                            Finding(
                                path,
                                node.lineno,
                                "SQL_WRITE_FIELD",
                                field,
                                function,
                                node.value.strip()
                            )
                        )

    # -------------------------------------------------------------------------
    # CALLS
    # -------------------------------------------------------------------------

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call
        ):
            continue

        function = resolve_function(
            node,
            parents
        )

        call_name = ""

        if isinstance(
            node.func,
            ast.Name
        ):

            call_name = node.func.id

        elif isinstance(
            node.func,
            ast.Attribute
        ):

            call_name = node.func.attr

        if call_name in {
            "execute",
            "executemany",
            "executescript",
            "commit",
            "rollback",
        }:

            segment = source_segment(
                source,
                node
            )

            if any(
                field in segment
                for field in TARGET_FIELDS
            ):

                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "DB_CALL_TARGET",
                        call_name,
                        function,
                        segment
                    )
                )

    return findings


# =============================================================================
# WRITE BOUNDARY DISCOVERY
# =============================================================================

def discover_write_boundaries(
    path
):

    results = []

    try:

        source = path.read_text(
            encoding="utf-8-sig",
            errors="strict"
        )

        tree = ast.parse(
            source,
            filename=str(path)
        )

    except Exception:
        return results

    parents = get_function_name_stack(
        tree
    )

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call
        ):
            continue

        call_name = None

        if isinstance(
            node.func,
            ast.Attribute
        ):
            call_name = node.func.attr

        elif isinstance(
            node.func,
            ast.Name
        ):
            call_name = node.func.id

        if call_name not in {
            "execute",
            "executemany",
            "executescript",
            "commit",
            "rollback",
        }:
            continue

        segment = source_segment(
            source,
            node
        )

        upper = segment.upper()

        if (
            "UPDATE " in upper
            or "INSERT INTO" in upper
            or "REPLACE INTO" in upper
            or "TECHNICAL_VALIDATION_" in upper
        ):

            results.append(
                (
                    node.lineno,
                    call_name,
                    resolve_function(
                        node,
                        parents
                    ),
                    segment
                )
            )

    return results


# =============================================================================
# EXACT FIELD ASSIGNMENT DISCOVERY
# =============================================================================

def discover_field_assignments(
    path
):

    results = []

    try:

        source = path.read_text(
            encoding="utf-8-sig",
            errors="strict"
        )

        tree = ast.parse(
            source,
            filename=str(path)
        )

    except Exception:
        return results

    parents = get_function_name_stack(
        tree
    )

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
                ast.AugAssign
            )
        ):
            continue

        segment = source_segment(
            source,
            node
        )

        if any(
            field in segment
            for field in TARGET_FIELDS
        ):

            results.append(
                (
                    node.lineno,
                    resolve_function(
                        node,
                        parents
                    ),
                    segment
                )
            )

    return results


# =============================================================================
# VERSION / FLAG PRODUCER DISCOVERY
# =============================================================================

def discover_version_and_flag_context(
    path
):

    results = []

    try:

        source = path.read_text(
            encoding="utf-8-sig",
            errors="strict"
        )

        tree = ast.parse(
            source,
            filename=str(path)
        )

    except Exception:
        return results

    parents = get_function_name_stack(
        tree
    )

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Constant
        ):
            continue

        if not isinstance(
            node.value,
            str
        ):
            continue

        value = node.value

        matched = []

        if TARGET_VERSION in value:
            matched.append(
                f"VERSION={TARGET_VERSION}"
            )

        for flag in TARGET_FLAGS:

            if flag in value:
                matched.append(
                    f"FLAG={flag}"
                )

        if matched:

            results.append(
                (
                    node.lineno,
                    resolve_function(
                        node,
                        parents
                    ),
                    matched,
                    value.strip()
                )
            )

    return results


# =============================================================================
# REPORT
# =============================================================================

def print_findings(
    findings
):

    banner(
        "TARGET FIELD AST DISCOVERY"
    )

    if not findings:

        print(
            "NO TARGET FIELD REFERENCES FOUND."
        )

        return

    grouped = defaultdict(list)

    for finding in findings:

        grouped[
            finding.path
        ].append(
            finding
        )

    for path in sorted(grouped):

        print()
        print(
            f"FILE: {path}"
        )

        for finding in sorted(
            grouped[path],
            key=lambda x: (
                x.line,
                x.category,
                x.token
            )
        ):

            print(
                f"  line={finding.line:<6} "
                f"category={finding.category:<22} "
                f"token={finding.token:<35} "
                f"function={finding.function}"
            )


def print_version_flag_findings(
    reports
):

    banner(
        "PERSISTED VERSION / FLAG PRODUCER DISCOVERY"
    )

    if not reports:

        print(
            "NO 0.5.0 / INVALID_REGIME / "
            "INVALID_VOLATILITY literals found."
        )

        return

    for path, results in reports:

        if not results:
            continue

        print()
        print(
            f"FILE: {path}"
        )

        for (
            line,
            function,
            matched,
            value
        ) in results:

            print(
                f"  line={line:<6} "
                f"function={function:<35} "
                f"{', '.join(matched)}"
            )

            print(
                f"      literal={value[:240]}"
            )


def print_write_boundaries(
    reports
):

    banner(
        "TECHNICAL VALIDATION WRITE-BOUNDARY DISCOVERY"
    )

    found = False

    for path, results in reports:

        if not results:
            continue

        found = True

        print()
        print(
            f"FILE: {path}"
        )

        for (
            line,
            call_name,
            function,
            segment
        ) in results:

            print(
                f"  line={line:<6} "
                f"call={call_name:<15} "
                f"function={function}"
            )

            print(
                f"      {segment[:500]}"
            )

    if not found:

        print(
            "NO TECHNICAL VALIDATION WRITE BOUNDARY FOUND."
        )


def print_assignments(
    reports
):

    banner(
        "EXACT TECHNICAL_VALIDATION_* ASSIGNMENT DISCOVERY"
    )

    found = False

    for path, results in reports:

        if not results:
            continue

        found = True

        print()
        print(
            f"FILE: {path}"
        )

        for (
            line,
            function,
            segment
        ) in results:

            print(
                f"  line={line:<6} "
                f"function={function}"
            )

            print(
                f"      {segment[:500]}"
            )

    if not found:

        print(
            "NO DIRECT ASSIGNMENTS FOUND."
        )


# =============================================================================
# MAIN PRODUCTION ENGINE SPECIAL REPORT
# =============================================================================

def production_engine_report():

    banner(
        "PRODUCTION ENGINE SOURCE INTEGRITY"
    )

    if not PRODUCTION_ENGINE.exists():

        kv(
            "Production Engine",
            "NOT FOUND"
        )

        return

    digest = sha256_file(
        PRODUCTION_ENGINE
    )

    kv(
        "Production Engine",
        str(PRODUCTION_ENGINE)
    )

    kv(
        "SHA256",
        digest
    )

    try:

        source = PRODUCTION_ENGINE.read_text(
            encoding="utf-8-sig",
            errors="strict"
        )

        tree = ast.parse(
            source,
            filename=str(
                PRODUCTION_ENGINE
            )
        )

        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef
                )
            )
        ]

        kv(
            "AST Parse",
            "SUCCESS"
        )

        kv(
            "Functions",
            len(functions)
        )

    except Exception as exc:

        kv(
            "AST Parse",
            f"ERROR: {exc}"
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    banner(
        "ARUNDA TECHNICAL VALIDATION PERSISTED STATE PRODUCER FORENSIC v0.1"
    )

    kv(
        "MODE",
        "READ ONLY / AST DISCOVERY"
    )

    kv(
        "Project",
        str(PROJECT_DIR)
    )

    kv(
        "Production Engine",
        str(PRODUCTION_ENGINE)
    )

    kv(
        "Target Table",
        TARGET_TABLE
    )

    kv(
        "Target Version",
        TARGET_VERSION
    )

    kv(
        "Target Flags",
        ", ".join(TARGET_FLAGS)
    )

    print()

    kv(
        "Production main()",
        "NOT EXECUTED"
    )

    kv(
        "Production modules",
        "NOT IMPORTED"
    )

    kv(
        "Database",
        "NOT CONNECTED"
    )

    kv(
        "Database writes",
        "NONE"
    )

    kv(
        "Synthetic data",
        "NONE"
    )

    # -------------------------------------------------------------------------
    # PRODUCTION SOURCE
    # -------------------------------------------------------------------------

    production_engine_report()

    # -------------------------------------------------------------------------
    # PYTHON FILE DISCOVERY
    # -------------------------------------------------------------------------

    banner(
        "PYTHON SOURCE DISCOVERY"
    )

    files = discover_python_files()

    kv(
        "Python files discovered",
        len(files)
    )

    for path in files:

        print(
            f"  {path}"
        )

    # -------------------------------------------------------------------------
    # AST DISCOVERY
    # -------------------------------------------------------------------------

    banner(
        "AST DISCOVERY"
    )

    all_findings = []

    for path in files:

        findings = inspect_file(
            path
        )

        all_findings.extend(
            findings
        )

    kv(
        "Total AST findings",
        len(all_findings)
    )

    # -------------------------------------------------------------------------
    # TARGET FIELD REPORT
    # -------------------------------------------------------------------------

    print_findings(
        all_findings
    )

    # -------------------------------------------------------------------------
    # VERSION / FLAG REPORT
    # -------------------------------------------------------------------------

    version_flag_reports = []

    for path in files:

        results = discover_version_and_flag_context(
            path
        )

        version_flag_reports.append(
            (
                path,
                results
            )
        )

    print_version_flag_findings(
        version_flag_reports
    )

    # -------------------------------------------------------------------------
    # FIELD ASSIGNMENTS
    # -------------------------------------------------------------------------

    assignment_reports = []

    for path in files:

        results = discover_field_assignments(
            path
        )

        assignment_reports.append(
            (
                path,
                results
            )
        )

    print_assignments(
        assignment_reports
    )

    # -------------------------------------------------------------------------
    # WRITE BOUNDARIES
    # -------------------------------------------------------------------------

    write_reports = []

    for path in files:

        results = discover_write_boundaries(
            path
        )

        write_reports.append(
            (
                path,
                results
            )
        )

    print_write_boundaries(
        write_reports
    )

    # -------------------------------------------------------------------------
    # FORENSIC TARGET SUMMARY
    # -------------------------------------------------------------------------

    banner(
        "FORENSIC TARGET SUMMARY"
    )

    field_hits = {
        field: 0
        for field in TARGET_FIELDS
    }

    version_hits = 0

    flag_hits = {
        flag: 0
        for flag in TARGET_FLAGS
    }

    write_hits = 0

    for finding in all_findings:

        if finding.token in field_hits:

            field_hits[
                finding.token
            ] += 1

        if (
            finding.category
            == "VERSION_LITERAL"
        ):

            version_hits += 1

        for flag in TARGET_FLAGS:

            if finding.token == flag:

                flag_hits[
                    flag
                ] += 1

        if (
            finding.category
            == "SQL_WRITE_FIELD"
        ):

            write_hits += 1

    for field, count in field_hits.items():

        kv(
            field,
            count
        )

    kv(
        f"VERSION {TARGET_VERSION} references",
        version_hits
    )

    for flag, count in flag_hits.items():

        kv(
            flag,
            count
        )

    kv(
        "SQL write-field findings",
        write_hits
    )

    # -------------------------------------------------------------------------
    # PROVENANCE HYPOTHESIS
    # -------------------------------------------------------------------------

    banner(
        "PROVENANCE STATUS"
    )

    if version_hits == 0:

        print(
            "PERSISTED VERSION 0.5.0 WAS NOT FOUND "
            "AS A SOURCE LITERAL."
        )

        print(
            "It may be generated indirectly, imported from "
            "configuration, or originate outside discovered Python sources."
        )

    else:

        print(
            f"VERSION {TARGET_VERSION} SOURCE REFERENCES FOUND."
        )

    if any(
        count > 0
        for count in flag_hits.values()
    ):

        print(
            "TARGET INVALID_* FLAGS FOUND IN SOURCE."
        )

    else:

        print(
            "TARGET INVALID_* FLAGS NOT FOUND."
        )

    if write_hits > 0:

        print(
            "TECHNICAL VALIDATION WRITE-RELATED AST REFERENCES FOUND."
        )

    else:

        print(
            "NO DIRECT TECHNICAL VALIDATION SQL WRITE REFERENCE FOUND."
        )

    print()

    print(
        "NEXT FORENSIC STEP:"
    )

    print(
        "Resolve the smallest exact producer function that connects:"
    )

    print()
    print(
        "    validation computation"
    )

    print(
        "          ↓"
    )

    print(
        "    technical_validation_* values"
    )

    print(
        "          ↓"
    )

    print(
        "    UPDATE/INSERT persistence boundary"
    )

    print()

    print(
        "Only after that resolution should the exact producer "
        "function be executed against REAL persisted row id=6909."
    )

    # -------------------------------------------------------------------------
    # CONTRACT
    # -------------------------------------------------------------------------

    banner(
        "FINAL FORENSIC CONTRACT"
    )

    kv(
        "READ ONLY",
        "YES"
    )

    kv(
        "AST ONLY",
        "YES"
    )

    kv(
        "Production main()",
        "NOT EXECUTED"
    )

    kv(
        "Production module import",
        "NONE"
    )

    kv(
        "SQLite connection",
        "NONE"
    )

    kv(
        "INSERT",
        "NONE"
    )

    kv(
        "UPDATE",
        "NONE"
    )

    kv(
        "DELETE",
        "NONE"
    )

    kv(
        "ALTER",
        "NONE"
    )

    kv(
        "CREATE",
        "NONE"
    )

    kv(
        "DROP",
        "NONE"
    )

    kv(
        "REPLACE",
        "NONE"
    )

    kv(
        "COMMIT",
        "NONE"
    )

    kv(
        "ROLLBACK",
        "NONE"
    )

    kv(
        "SOURCE MODIFICATION",
        "NONE"
    )

    kv(
        "SYNTHETIC DATA",
        "NONE"
    )

    kv(
        "INTERPOLATION",
        "NONE"
    )

    kv(
        "FORWARD FILL",
        "NONE"
    )

    kv(
        "BACK FILL",
        "NONE"
    )

    print()

    print(
        "FORENSIC RESULT:"
    )

    print(
        "Source-level persisted-state producer discovery completed."
    )

    print(
        "No production runtime path was executed."
    )

    print(
        "No database state was modified."
    )

    print()

    print(
        "=" * 100
    )

    print(
        "ARUNDA TECHNICAL VALIDATION PERSISTED STATE PRODUCER FORENSIC v0.1 COMPLETE"
    )

    print(
        "=" * 100
    )


if __name__ == "__main__":
    main()