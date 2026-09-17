import os
import re


# =============================================================================
# ARUNDA TRADER — REAL OPPORTUNITY SIGNALS WRITER v0.2
# =============================================================================
#
# PURPOSE:
#     Locate the actual production writer of opportunity_signals.
#
# READ ONLY:
#     - source files are only read
#     - database is NOT opened
#     - no production code is executed
#     - no database mutation
#
# IMPORTANT:
#     Discovery/helper/forensic scripts are excluded.
#
# =============================================================================


PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"

TARGET = "opportunity_signals"


EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "backup",
    "backups",
    "_backups",
}


EXCLUDED_FILE_WORDS = (
    "find_",
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
# FILE
# =============================================================================

def read_file(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as f:

            return f.read()

    except OSError:

        return ""


def should_skip(filename):

    lower = filename.lower()

    return any(
        word in lower
        for word in EXCLUDED_FILE_WORDS
    )


# =============================================================================
# REAL WRITE PATTERN
# =============================================================================

def find_real_writes(text):

    results = []

    # -------------------------------------------------------------------------
    # INSERT ... INTO opportunity_signals
    # -------------------------------------------------------------------------

    insert_pattern = re.compile(
        r"""
        INSERT
        \s+
        (?:OR\s+\w+\s+)?
        INTO
        \s+
        ["'`]?
        opportunity_signals
        ["'`]?
        """,
        re.IGNORECASE | re.VERBOSE,
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

    for match in insert_pattern.finditer(text):

        results.append(
            (
                "INSERT",
                match.start(),
                match.group(0),
            )
        )

    for match in update_pattern.finditer(text):

        results.append(
            (
                "UPDATE",
                match.start(),
                match.group(0),
            )
        )

    return results


# =============================================================================
# EXECUTION CONTEXT
# =============================================================================

def has_execution_context(text, position):

    # Only inspect the surrounding source.
    start = max(
        0,
        position - 2500
    )

    end = min(
        len(text),
        position + 2500
    )

    block = text[start:end]

    lower = block.lower()

    execute_patterns = (
        ".execute(",
        ".executemany(",
        "cursor.execute(",
        "cursor.executemany(",
        "conn.execute(",
        "conn.executemany(",
    )

    return any(
        pattern in lower
        for pattern in execute_patterns
    )


# =============================================================================
# CONTEXT
# =============================================================================

def line_number(text, position):

    return (
        text[:position].count("\n")
        + 1
    )


def source_context(
    text,
    target_line,
    radius=18,
):

    lines = text.splitlines()

    start = max(
        1,
        target_line - radius
    )

    end = min(
        len(lines),
        target_line + radius
    )

    for number in range(
        start,
        end + 1
    ):

        marker = (
            " >>> "
            if number == target_line
            else "     "
        )

        print(
            f"{marker}{number:5d} | "
            f"{lines[number - 1]}"
        )


# =============================================================================
# SCAN
# =============================================================================

def scan():

    results = []

    for root, dirs, files in os.walk(
        PROJECT_ROOT
    ):

        dirs[:] = [
            d
            for d in dirs
            if d not in EXCLUDED_DIRS
        ]

        for filename in files:

            if not filename.lower().endswith(".py"):
                continue

            if should_skip(filename):
                continue

            path = os.path.join(
                root,
                filename
            )

            text = read_file(path)

            if not text:
                continue

            writes = find_real_writes(
                text
            )

            if not writes:
                continue

            for operation, position, sql in writes:

                if not has_execution_context(
                    text,
                    position
                ):
                    continue

                results.append(
                    {
                        "path": path,
                        "file": filename,
                        "operation": operation,
                        "line": line_number(
                            text,
                            position
                        ),
                        "sql": sql.strip(),
                        "text": text,
                    }
                )

    return results


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — REAL OPPORTUNITY SIGNALS WRITER v0.2"
    )
    print("=" * 100)

    print(
        f"PROJECT : {PROJECT_ROOT}"
    )

    print(
        f"TARGET  : {TARGET}"
    )

    print(
        "MODE    : READ ONLY"
    )

    print(
        "DATABASE: NOT ACCESSED"
    )

    print(
        "EXECUTE : NONE"
    )

    print("=" * 100)

    print()
    print(
        "Scanning production Python files..."
    )

    results = scan()

    print()
    print("=" * 100)

    print(
        f"REAL WRITER CANDIDATES : {len(results)}"
    )

    print("=" * 100)

    if not results:

        print()
        print(
            "NO REAL DIRECT WRITER FOUND."
        )

        print()
        print(
            "NEXT POSSIBILITY:"
        )

        print(
            "writer may use a dynamic SQL variable, "
            "helper function, repository layer, "
            "or table name assembled indirectly."
        )

        print("=" * 100)

        return 0

    for index, result in enumerate(
        results,
        1
    ):

        print()
        print(
            f"WRITER CANDIDATE #{index}"
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

        source_context(
            result["text"],
            result["line"],
        )

        print("-" * 100)

    print()
    print("=" * 100)

    print(
        "RESULT : DIRECT PRODUCTION WRITER CANDIDATE(S) FOUND."
    )

    print(
        "NEXT   : TRACE ONLY THE SHOWN PRODUCTION FUNCTION."
    )

    print("=" * 100)

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )