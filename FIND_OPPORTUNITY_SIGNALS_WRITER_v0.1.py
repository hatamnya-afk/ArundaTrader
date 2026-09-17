import os
import re


# =============================================================================
# ARUNDA TRADER — FIND OPPORTUNITY SIGNALS WRITER v0.1
# =============================================================================
#
# PURPOSE:
#     Find the REAL production source code that writes to:
#
#         opportunity_signals
#
#     Search is based on actual SQL/write semantics, NOT filename.
#
# MODE:
#     READ ONLY
#
# WRITE:
#     NONE
#
# IMPORTANT:
#     This script does NOT:
#       - modify source files
#       - modify database
#       - execute production code
#       - create fixtures
#       - create synthetic signals
#       - redesign strategy
#
# =============================================================================


PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"

TARGET_TABLE = "opportunity_signals"

SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "_backups",
    "backup",
    "backups",
}

# Files that are clearly forensic/audit/discovery helpers.
# We want the production writer, not another forensic script.
SKIP_FILE_PATTERNS = (
    "forensic",
    "audit",
    "discovery",
    "discover",
    "check_",
    "verify_",
    "reconciliation",
    "reconcile",
    "provenance",
    "boundary",
    "repair",
)


# =============================================================================
# HELPERS
# =============================================================================

def line(char="=", n=100):
    print(char * n)


def is_python_file(filename):
    return filename.lower().endswith(".py")


def should_skip_file(filename):
    lower = filename.lower()

    return any(
        pattern in lower
        for pattern in SKIP_FILE_PATTERNS
    )


def normalize_sql(text):
    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


# =============================================================================
# WRITER DETECTION
# =============================================================================

def find_write_locations(text):

    matches = []

    # -------------------------------------------------------------------------
    # INSERT INTO opportunity_signals
    # -------------------------------------------------------------------------

    insert_pattern = re.compile(
        r"""
        INSERT
        \s+
        (?:OR\s+(?:REPLACE|IGNORE)\s+)?
        INTO
        \s+
        ["'`]?
        opportunity_signals
        ["'`]?
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    for match in insert_pattern.finditer(text):

        matches.append(
            (
                "INSERT",
                match.start(),
                match.group(0),
            )
        )

    # -------------------------------------------------------------------------
    # UPDATE opportunity_signals
    # -------------------------------------------------------------------------

    update_pattern = re.compile(
        r"""
        UPDATE
        \s+
        ["'`]?
        opportunity_signals
        ["'`]?
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    for match in update_pattern.finditer(text):

        matches.append(
            (
                "UPDATE",
                match.start(),
                match.group(0),
            )
        )

    return matches


# =============================================================================
# CONTEXT
# =============================================================================

def print_context(
    lines,
    line_number,
    radius=12,
):

    start = max(
        1,
        line_number - radius
    )

    end = min(
        len(lines),
        line_number + radius
    )

    for number in range(
        start,
        end + 1
    ):

        marker = " >>> " if number == line_number else "     "

        print(
            f"{marker}{number:5d} | {lines[number - 1].rstrip()}"
        )


# =============================================================================
# SCAN
# =============================================================================

def scan_project():

    results = []

    for root, dirs, files in os.walk(
        PROJECT_ROOT
    ):

        dirs[:] = [
            d
            for d in dirs
            if d not in SKIP_DIRS
        ]

        for filename in files:

            if not is_python_file(filename):
                continue

            if should_skip_file(filename):
                continue

            path = os.path.join(
                root,
                filename
            )

            try:

                with open(
                    path,
                    "r",
                    encoding="utf-8",
                    errors="ignore",
                ) as f:

                    text = f.read()

            except OSError:
                continue

            writes = find_write_locations(
                text
            )

            if not writes:
                continue

            lines = text.splitlines()

            for operation, position, sql in writes:

                line_number = (
                    text[:position].count("\n")
                    + 1
                )

                results.append(
                    {
                        "path": path,
                        "filename": filename,
                        "operation": operation,
                        "line": line_number,
                        "sql": normalize_sql(sql),
                        "lines": lines,
                    }
                )

    return results


# =============================================================================
# MAIN
# =============================================================================

def main():

    line()

    print(
        "ARUNDA TRADER — REAL OPPORTUNITY SIGNALS WRITER"
    )

    line()

    print(
        f"PROJECT : {PROJECT_ROOT}"
    )

    print(
        f"TARGET  : {TARGET_TABLE}"
    )

    print(
        "MODE    : READ ONLY"
    )

    print(
        "WRITE   : NONE"
    )

    line()

    print()
    print(
        "Searching production Python source for actual "
        "INSERT/UPDATE statements..."
    )

    results = scan_project()

    print()

    line()

    print(
        f"REAL WRITER LOCATIONS : {len(results)}"
    )

    line()

    if not results:

        print()
        print(
            "NO DIRECT INSERT/UPDATE WRITER FOUND."
        )

        print()
        print(
            "This means the production writer may use:"
        )

        print(
            "  - dynamic SQL"
        )

        print(
            "  - executemany()"
        )

        print(
            "  - SQL stored in another variable"
        )

        print(
            "  - helper/repository abstraction"
        )

        print(
            "  - INSERT generated outside the obvious SQL pattern"
        )

        line()

        return 0

    for index, result in enumerate(
        results,
        1
    ):

        print()
        print(
            f"WRITER #{index}"
        )

        print("-" * 100)

        print(
            f"FILE      : {result['path']}"
        )

        print(
            f"OPERATION : {result['operation']}"
        )

        print(
            f"LINE      : {result['line']}"
        )

        print(
            f"SQL       : {result['sql']}"
        )

        print()

        print(
            "SOURCE CONTEXT"
        )

        print("-" * 100)

        print_context(
            result["lines"],
            result["line"],
            radius=15,
        )

    print()
    line()

    print(
        "RESULT : REAL opportunity_signals writer location(s) found."
    )

    print(
        "NEXT   : Execute/trace ONLY the production path containing "
        "the writer above."
    )

    line()

    return 0


# =============================================================================
# ENTRY
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )