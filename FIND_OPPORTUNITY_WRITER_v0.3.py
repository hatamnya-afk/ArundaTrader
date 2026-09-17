import os
import re


PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"

TARGET = "opportunity_signals"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}


def read_file(path):

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as f:
            return f.read()

    except Exception:
        return ""


def show_match(path, text, start, end, title):

    lines = text.splitlines()

    line_start = text[:start].count("\n") + 1
    line_end = text[:end].count("\n") + 1

    context_start = max(
        0,
        line_start - 12,
    )

    context_end = min(
        len(lines),
        line_end + 12,
    )

    print("\n" + "=" * 110)
    print("FILE :", path)
    print("TYPE :", title)
    print(
        f"LINES : {context_start + 1}-{context_end}"
    )
    print("=" * 110)

    for i in range(
        context_start,
        context_end,
    ):

        print(
            f"{i + 1:6} | "
            f"{lines[i]}"
        )


def scan_file(path):

    text = read_file(path)

    if not text:
        return

    # ------------------------------------------------------------
    # 1. Direct INSERT into opportunity_signals
    # ------------------------------------------------------------

    pattern_insert = re.compile(
        r"""
        INSERT
        (?:\s+OR\s+\w+)?
        \s+INTO\s+
        ["'`]?
        opportunity_signals
        ["'`]?
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    for match in pattern_insert.finditer(text):

        show_match(
            path,
            text,
            match.start(),
            match.end(),
            "DIRECT INSERT INTO opportunity_signals",
        )


    # ------------------------------------------------------------
    # 2. UPDATE opportunity_signals
    # ------------------------------------------------------------

    pattern_update = re.compile(
        r"""
        UPDATE
        \s+
        ["'`]?
        opportunity_signals
        ["'`]?
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    for match in pattern_update.finditer(text):

        show_match(
            path,
            text,
            match.start(),
            match.end(),
            "UPDATE opportunity_signals",
        )


    # ------------------------------------------------------------
    # 3. DELETE opportunity_signals
    # ------------------------------------------------------------

    pattern_delete = re.compile(
        r"""
        DELETE
        \s+FROM
        \s+
        ["'`]?
        opportunity_signals
        ["'`]?
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    for match in pattern_delete.finditer(text):

        show_match(
            path,
            text,
            match.start(),
            match.end(),
            "DELETE FROM opportunity_signals",
        )


    # ------------------------------------------------------------
    # 4. executemany / execute with opportunity_signals
    #    در صورتی که نام جدول داخل همان SQL باشد.
    # ------------------------------------------------------------

    pattern_execute = re.compile(
        r"""
        (?:
            executemany
            |
            execute
        )
        \s*\(
        [\s\S]{0,1200}?
        opportunity_signals
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    for match in pattern_execute.finditer(text):

        # اگر قبلاً INSERT مستقیم پیدا شده،
        # این مورد را دوباره چاپ نکن.
        before = text[
            max(0, match.start() - 100)
            :
            match.start()
        ]

        if re.search(
            r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+opportunity_signals",
            before,
            re.IGNORECASE,
        ):
            continue

        show_match(
            path,
            text,
            match.start(),
            match.end(),
            "EXECUTE/EXECUTEMANY referencing opportunity_signals",
        )


def main():

    print("=" * 110)
    print(
        "ARUNDA TRADER — OPPORTUNITY WRITER DISCOVERY v0.3"
    )
    print("=" * 110)

    print("MODE    : READ ONLY")
    print("PROJECT :", PROJECT_ROOT)
    print("TARGET  :", TARGET)
    print("WRITE   : NONE")

    print("=" * 110)

    scanned = 0

    for root, dirs, files in os.walk(
        PROJECT_ROOT
    ):

        dirs[:] = [
            d
            for d in dirs
            if d not in SKIP_DIRS
        ]

        for filename in files:

            if not filename.endswith(".py"):
                continue

            path = os.path.join(
                root,
                filename,
            )

            scanned += 1

            scan_file(path)

    print("\n" + "=" * 110)
    print("SCAN COMPLETE")
    print("=" * 110)

    print(
        "Python files scanned :",
        scanned,
    )

    print(
        "TARGET               :",
        TARGET,
    )

    print(
        "PURPOSE              :",
        "FIND REAL PRODUCTION WRITER",
    )

    print("=" * 110)


if __name__ == "__main__":
    main()