import os
import re


# =============================================================================
# ARUNDA TRADER — TRACE OPPORTUNITY SIGNALS WRITE PATH v0.1
# =============================================================================
#
# PURPOSE:
#   Trace indirect production writes to opportunity_signals.
#
# READ ONLY:
#   - no DB access
#   - no code execution
#   - no source modification
#
# TARGET:
#   opportunity_signals
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
# TARGET REFERENCES
# =============================================================================

def find_target_references(text):

    pattern = re.compile(
        r"opportunity_signals",
        re.IGNORECASE,
    )

    return list(
        pattern.finditer(text)
    )


# =============================================================================
# WRITE-LIKE CONTEXT
# =============================================================================

def classify_context(
    text,
    position,
):

    start = max(
        0,
        position - 1800
    )

    end = min(
        len(text),
        position + 1800
    )

    block = text[start:end]

    lower = block.lower()

    signals = []

    # Direct SQL
    if re.search(
        r"\binsert\b",
        lower,
    ):
        signals.append(
            "INSERT_CONTEXT"
        )

    if re.search(
        r"\bupdate\b",
        lower,
    ):
        signals.append(
            "UPDATE_CONTEXT"
        )

    if re.search(
        r"\bdelete\b",
        lower,
    ):
        signals.append(
            "DELETE_CONTEXT"
        )

    # DB execution
    execute_patterns = (
        ".execute(",
        ".executemany(",
        "cursor.execute(",
        "cursor.executemany(",
        "conn.execute(",
        "conn.executemany(",
    )

    if any(
        pattern in lower
        for pattern in execute_patterns
    ):
        signals.append(
            "SQL_EXECUTION_CONTEXT"
        )

    # Generic writers
    writer_words = (
        "insert",
        "write",
        "save",
        "persist",
        "store",
        "upsert",
        "record",
        "create",
    )

    if any(
        word in lower
        for word in writer_words
    ):
        signals.append(
            "WRITER_CONTEXT"
        )

    return signals


# =============================================================================
# LINE
# =============================================================================

def get_line_number(
    text,
    position,
):

    return (
        text[:position].count("\n")
        + 1
    )


def print_context(
    text,
    line_number,
    radius=15,
):

    lines = text.splitlines()

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

        marker = (
            " >>> "
            if number == line_number
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

            if not filename.lower().endswith(
                ".py"
            ):
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

            references = find_target_references(
                text
            )

            for match in references:

                signals = classify_context(
                    text,
                    match.start()
                )

                # We only care about references
                # that occur near write-like behavior.
                if not signals:
                    continue

                results.append(
                    {
                        "path": path,
                        "file": filename,
                        "line": get_line_number(
                            text,
                            match.start()
                        ),
                        "signals": signals,
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
        "ARUNDA TRADER — "
        "TRACE OPPORTUNITY SIGNALS WRITE PATH v0.1"
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
        "Tracing indirect references near "
        "write/execution contexts..."
    )

    results = scan()

    print()
    print("=" * 100)

    print(
        f"INDIRECT WRITE-PATH CANDIDATES : "
        f"{len(results)}"
    )

    print("=" * 100)

    if not results:

        print()
        print(
            "NO INDIRECT WRITE CONTEXT FOUND."
        )

        print()
        print(
            "This means the production writer is "
            "likely one of:"
        )

        print(
            "1. Generic repository/table writer"
        )

        print(
            "2. Dynamic table-name construction"
        )

        print(
            "3. ORM/model layer"
        )

        print(
            "4. opportunity_signals is populated "
            "through another table/view pipeline"
        )

        print("=" * 100)

        return 0

    for index, result in enumerate(
        results,
        1
    ):

        print()
        print(
            f"CANDIDATE #{index}"
        )

        print("-" * 100)

        print(
            f"FILE    : {result['path']}"
        )

        print(
            f"LINE    : {result['line']}"
        )

        print(
            f"CONTEXT : "
            f"{', '.join(result['signals'])}"
        )

        print()
        print(
            "SOURCE CONTEXT"
        )

        print("-" * 100)

        print_context(
            result["text"],
            result["line"],
        )

        print("-" * 100)

    print()
    print("=" * 100)

    print(
        "RESULT : INDIRECT WRITE PATH CANDIDATE(S) FOUND."
    )

    print(
        "NEXT   : TRACE THE SHOWN PRODUCTION FUNCTION "
        "TO ITS ACTUAL WRITER."
    )

    print("=" * 100)

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )