import os
import re


# =============================================================================
# ARUNDA TRADER — TRACE REAL OPPORTUNITY SIGNAL WRITER v0.2
# =============================================================================
#
# PURPOSE
# -------
# Find the REAL production write path feeding opportunity_signals.
#
# This is SOURCE-ONLY forensic tracing.
#
# DOES NOT:
#   - access database
#   - execute production code
#   - modify source
#   - modify database
#   - create tables
#   - infer strategy
#
# TARGET:
#   opportunity_signals
#
# METHOD:
#   1. Exclude forensic / FIND / audit scripts.
#   2. Find references to opportunity_signals.
#   3. Find SQL execution primitives nearby.
#   4. Find generic INSERT/UPDATE/DELETE patterns.
#   5. Find dynamic table-name construction.
#   6. Find repository/helper writer functions.
#   7. Print source context for actual production candidates.
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
    "trace_",
    "discovery",
    "reconciliation",
    "repair",
    "verify",
    "verification",
    "check_",
)


SOURCE_EXTENSIONS = {
    ".py",
}


# =============================================================================
# TERMINAL
# =============================================================================

def line(char="=", n=100):
    print(char * n)


def section(title):
    print()
    line()
    print(title)
    line()


# =============================================================================
# FILE FILTER
# =============================================================================

def is_excluded_path(path):

    parts = {
        part.lower()
        for part in os.path.normpath(path).split(os.sep)
    }

    if parts & EXCLUDED_DIRS:
        return True

    filename = os.path.basename(path).lower()

    return any(
        word in filename
        for word in EXCLUDED_FILE_WORDS
    )


def iter_python_files():

    for root, dirs, files in os.walk(PROJECT_ROOT):

        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIRS
        ]

        for filename in files:

            path = os.path.join(
                root,
                filename
            )

            if (
                os.path.splitext(filename)[1].lower()
                not in SOURCE_EXTENSIONS
            ):
                continue

            if is_excluded_path(path):
                continue

            yield path


# =============================================================================
# READ SOURCE
# =============================================================================

def read_source(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as handle:

            return handle.read()

    except UnicodeDecodeError:

        try:

            with open(
                path,
                "r",
                encoding="utf-8-sig"
            ) as handle:

                return handle.read()

        except Exception:
            return ""

    except Exception:

        return ""


# =============================================================================
# NORMALIZE
# =============================================================================

def normalize(text):

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


# =============================================================================
# FUNCTION DISCOVERY
# =============================================================================

FUNCTION_PATTERN = re.compile(
    r"""
    ^[ \t]*
    def
    \s+
    ([A-Za-z_][A-Za-z0-9_]*)
    \s*\(
    """,
    re.MULTILINE | re.VERBOSE
)


def get_functions(text):

    results = []

    matches = list(
        FUNCTION_PATTERN.finditer(text)
    )

    for index, match in enumerate(matches):

        start = match.start()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        results.append(
            {
                "name": match.group(1),
                "start": start,
                "end": end,
                "text": text[start:end],
            }
        )

    return results


# =============================================================================
# TARGET REFERENCES
# =============================================================================

def find_target_references(text):

    pattern = re.compile(
        r"opportunity_signals",
        re.IGNORECASE
    )

    return list(
        pattern.finditer(text)
    )


# =============================================================================
# SQL EXECUTION PRIMITIVES
# =============================================================================

EXECUTION_PATTERNS = (
    r"\.execute\s*\(",
    r"\.executemany\s*\(",
    r"\.executescript\s*\(",
    r"cursor\s*\(",
    r"executemany\s*\(",
    r"execute\s*\(",
)


def has_sql_execution_context(text):

    return any(
        re.search(
            pattern,
            text,
            re.IGNORECASE
        )
        for pattern in EXECUTION_PATTERNS
    )


# =============================================================================
# DIRECT SQL WRITERS
# =============================================================================

DIRECT_WRITE_PATTERNS = (
    r"\bINSERT\s+(?:OR\s+\w+\s+)?INTO\b",
    r"\bUPDATE\s+[A-Za-z_\"'`$]+",
    r"\bDELETE\s+FROM\b",
    r"\bREPLACE\s+INTO\b",
)


def has_direct_write(text):

    return any(
        re.search(
            pattern,
            text,
            re.IGNORECASE
        )
        for pattern in DIRECT_WRITE_PATTERNS
    )


# =============================================================================
# GENERIC WRITER PATTERNS
# =============================================================================

GENERIC_WRITER_PATTERNS = (
    "insert",
    "update",
    "upsert",
    "write",
    "save",
    "persist",
    "store",
    "create",
    "record",
    "append",
    "bulk_insert",
    "insert_many",
    "save_signal",
    "write_signal",
    "persist_signal",
)


def has_generic_writer_name(function_name):

    name = function_name.lower()

    return any(
        word in name
        for word in GENERIC_WRITER_PATTERNS
    )


# =============================================================================
# DYNAMIC TABLE CONSTRUCTION
# =============================================================================

DYNAMIC_TABLE_PATTERNS = (
    r'f["\'].*\{.*table',
    r'f["\'].*\{.*TABLE',
    r'\+\s*table',
    r'\+\s*TABLE',
    r'\.format\s*\(.*table',
    r'\.format\s*\(.*TABLE',
    r'["\']table["\']\s*:',
    r'table_name\s*=',
    r'TABLE_NAME\s*=',
    r'target_table\s*=',
    r'TARGET_TABLE\s*=',
)


def has_dynamic_table_context(text):

    return any(
        re.search(
            pattern,
            text,
            re.IGNORECASE
        )
        for pattern in DYNAMIC_TABLE_PATTERNS
    )


# =============================================================================
# SQL VARIABLE CONSTRUCTION
# =============================================================================

SQL_VARIABLE_PATTERNS = (
    r'\bsql\s*=',
    r'\bquery\s*=',
    r'\bstatement\s*=',
    r'\bstmt\s*=',
    r'\binsert_sql\s*=',
    r'\bupdate_sql\s*=',
    r'\bwrite_sql\s*=',
    r'\bupsert_sql\s*=',
)


def has_sql_variable_context(text):

    return any(
        re.search(
            pattern,
            text,
            re.IGNORECASE
        )
        for pattern in SQL_VARIABLE_PATTERNS
    )


# =============================================================================
# CONTEXT
# =============================================================================

def source_context(
    text,
    position,
    radius=900
):

    start = max(
        0,
        position - radius
    )

    end = min(
        len(text),
        position + radius
    )

    return text[start:end]


def line_number(text, position):

    return (
        text.count(
            "\n",
            0,
            position
        )
        + 1
    )


# =============================================================================
# SCORE CANDIDATE
# =============================================================================

def score_candidate(
    function_name,
    function_text,
    full_text
):

    score = 0
    reasons = []

    name = function_name.lower()

    # -------------------------------------------------------------------------
    # Target
    # -------------------------------------------------------------------------

    if TARGET.lower() in function_text.lower():

        score += 100
        reasons.append(
            "TARGET_REFERENCE"
        )

    # -------------------------------------------------------------------------
    # SQL execution
    # -------------------------------------------------------------------------

    if has_sql_execution_context(
        function_text
    ):

        score += 30
        reasons.append(
            "SQL_EXECUTION"
        )

    # -------------------------------------------------------------------------
    # Direct write
    # -------------------------------------------------------------------------

    if has_direct_write(
        function_text
    ):

        score += 50
        reasons.append(
            "DIRECT_WRITE_SQL"
        )

    # -------------------------------------------------------------------------
    # Generic writer
    # -------------------------------------------------------------------------

    if has_generic_writer_name(
        function_name
    ):

        score += 40
        reasons.append(
            "WRITER_FUNCTION_NAME"
        )

    # -------------------------------------------------------------------------
    # Dynamic table
    # -------------------------------------------------------------------------

    if has_dynamic_table_context(
        function_text
    ):

        score += 35
        reasons.append(
            "DYNAMIC_TABLE"
        )

    # -------------------------------------------------------------------------
    # SQL variable
    # -------------------------------------------------------------------------

    if has_sql_variable_context(
        function_text
    ):

        score += 25
        reasons.append(
            "SQL_VARIABLE"
        )

    # -------------------------------------------------------------------------
    # Production-like function
    # -------------------------------------------------------------------------

    if name in (
        "main",
        "run",
        "process",
        "process_signals",
        "generate",
        "build",
        "create",
        "evaluate",
    ):

        score += 10
        reasons.append(
            "PRODUCTION_ENTRY_FUNCTION"
        )

    return score, reasons


# =============================================================================
# SCAN
# =============================================================================

def scan():

    candidates = []

    files_scanned = 0

    for path in iter_python_files():

        files_scanned += 1

        text = read_source(path)

        if not text:
            continue

        functions = get_functions(text)

        # ---------------------------------------------------------------------
        # Function-level analysis
        # ---------------------------------------------------------------------

        for function in functions:

            function_text = function["text"]

            target_here = (
                TARGET.lower()
                in function_text.lower()
            )

            writer_here = (
                has_direct_write(
                    function_text
                )
                or
                has_dynamic_table_context(
                    function_text
                )
                or
                has_sql_variable_context(
                    function_text
                )
                or
                has_generic_writer_name(
                    function["name"]
                )
            )

            execution_here = has_sql_execution_context(
                function_text
            )

            if not (
                target_here
                or writer_here
            ):
                continue

            score, reasons = score_candidate(
                function["name"],
                function_text,
                text
            )

            if score <= 0:
                continue

            candidates.append(
                {
                    "path": path,
                    "function": function["name"],
                    "score": score,
                    "reasons": reasons,
                    "text": function_text,
                    "target": target_here,
                    "execution": execution_here,
                    "writer": writer_here,
                }
            )

        # ---------------------------------------------------------------------
        # File-level target reference outside functions
        # ---------------------------------------------------------------------

        refs = find_target_references(
            text
        )

        if refs and not functions:

            for ref in refs:

                context = source_context(
                    text,
                    ref.start()
                )

                score = 100

                if has_sql_execution_context(
                    context
                ):
                    score += 30

                if has_direct_write(
                    context
                ):
                    score += 50

                candidates.append(
                    {
                        "path": path,
                        "function": "<MODULE>",
                        "score": score,
                        "reasons": [
                            "TARGET_REFERENCE",
                            "MODULE_LEVEL",
                        ],
                        "text": context,
                        "target": True,
                        "execution": has_sql_execution_context(
                            context
                        ),
                        "writer": has_direct_write(
                            context
                        ),
                    }
                )

    candidates.sort(
        key=lambda item: (
            item["score"],
            item["writer"],
            item["execution"],
        ),
        reverse=True
    )

    return files_scanned, candidates


# =============================================================================
# MAIN
# =============================================================================

def main():

    section(
        "ARUNDA TRADER — TRACE REAL OPPORTUNITY SIGNAL WRITER v0.2"
    )

    print(
        f"PROJECT : {PROJECT_ROOT}"
    )

    print(
        f"TARGET  : {TARGET}"
    )

    print(
        "MODE    : SOURCE ONLY"
    )

    print(
        "DATABASE: NOT ACCESSED"
    )

    print(
        "EXECUTE : NONE"
    )

    print(
        "WRITE   : NONE"
    )

    section(
        "SCANNING PRODUCTION SOURCE"
    )

    files_scanned, candidates = scan()

    print(
        f"Python files scanned : {files_scanned}"
    )

    print(
        f"Candidates found     : {len(candidates)}"
    )

    if not candidates:

        section(
            "NO CANDIDATE FOUND"
        )

        print(
            "No production-level writer candidate "
            "was identified."
        )

        print()
        print(
            "Possible remaining architecture:"
        )

        print(
            "1. Generic repository writer"
        )

        print(
            "2. Dynamic SQL builder"
        )

        print(
            "3. ORM/model layer"
        )

        print(
            "4. Imported writer function"
        )

        print(
            "5. Table populated by another production stage"
        )

        return 0

    section(
        "RANKED PRODUCTION WRITE-PATH CANDIDATES"
    )

    for index, candidate in enumerate(
        candidates,
        1
    ):

        print()
        print(
            f"CANDIDATE #{index}"
        )

        print(
            "-" * 100
        )

        print(
            f"SCORE    : {candidate['score']}"
        )

        print(
            f"FILE     : {candidate['path']}"
        )

        print(
            f"FUNCTION : {candidate['function']}"
        )

        print(
            f"TARGET   : "
            f"{'YES' if candidate['target'] else 'NO'}"
        )

        print(
            f"SQL EXEC : "
            f"{'YES' if candidate['execution'] else 'NO'}"
        )

        print(
            f"WRITE    : "
            f"{'YES' if candidate['writer'] else 'NO'}"
        )

        print(
            "REASONS  : "
            + ", ".join(
                candidate["reasons"]
            )
        )

        # ---------------------------------------------------------------------
        # Print useful source context
        # ---------------------------------------------------------------------

        print()
        print(
            "SOURCE CONTEXT"
        )

        print(
            "-" * 100
        )

        lines = candidate[
            "text"
        ].splitlines()

        # Keep context bounded
        if len(lines) > 80:

            lines = lines[:80]

        for number, text in enumerate(
            lines,
            1
        ):

            upper = text.upper()

            important = (
                TARGET.upper() in upper
                or
                "INSERT" in upper
                or
                "UPDATE" in upper
                or
                "UPSERT" in upper
                or
                ".EXECUTE" in upper
                or
                "TABLE_NAME" in upper
                or
                "SQL =" in upper
                or
                "QUERY =" in upper
            )

            if important:

                print(
                    f"{number:5} | >>> {text}"
                )

    # -------------------------------------------------------------------------
    # Best candidate
    # -------------------------------------------------------------------------

    best = candidates[0]

    section(
        "BEST CURRENT PRODUCTION WRITER CANDIDATE"
    )

    print(
        f"FILE     : {best['path']}"
    )

    print(
        f"FUNCTION : {best['function']}"
    )

    print(
        f"SCORE    : {best['score']}"
    )

    print(
        "REASONS  : "
        + ", ".join(
            best["reasons"]
        )
    )

    print()
    print(
        "NEXT:"
    )

    print(
        "Trace ONLY this production function "
        "to its caller and actual SQL execution boundary."
    )

    print(
        "Do NOT modify strategy."
    )

    print(
        "Do NOT repair opportunity_signals yet."
    )

    print(
        "Do NOT execute the writer yet."
    )

    print(
        "Do NOT write to production DB."
    )

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )