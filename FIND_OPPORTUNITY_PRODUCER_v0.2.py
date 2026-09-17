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


WRITE_PATTERNS = [
    r"INSERT\s+INTO\s+opportunity_signals",
    r"INSERT\s+OR\s+\w+\s+INTO\s+opportunity_signals",
    r"UPDATE\s+opportunity_signals",
    r"DELETE\s+FROM\s+opportunity_signals",
    r"executemany\s*\(",
    r"execute\s*\(",
]


def scan_file(path):

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as f:
            lines = f.readlines()

    except Exception:
        return

    matches = []

    for i, line in enumerate(lines):

        if TARGET not in line:
            continue

        context_start = max(0, i - 15)
        context_end = min(
            len(lines),
            i + 16,
        )

        context = "".join(
            lines[
                context_start:context_end
            ]
        )

        for pattern in WRITE_PATTERNS:

            if re.search(
                pattern,
                context,
                re.IGNORECASE,
            ):

                matches.append(
                    (
                        i + 1,
                        context_start + 1,
                        context_end,
                        pattern,
                        context,
                    )
                )

                break

    if not matches:
        return

    print("\n" + "=" * 110)
    print("FILE :", path)
    print("=" * 110)

    for (
        target_line,
        start,
        end,
        pattern,
        context,
    ) in matches:

        print(
            f"\nMATCH NEAR LINE : {target_line}"
        )

        print(
            f"PATTERN         : {pattern}"
        )

        print(
            f"CONTEXT         : LINES {start}-{end}"
        )

        print("-" * 110)

        for n in range(
            start - 1,
            end,
        ):

            print(
                f"{n + 1:6} | "
                f"{lines[n].rstrip()}"
            )


def main():

    print("=" * 110)
    print(
        "ARUNDA TRADER — OPPORTUNITY WRITER DISCOVERY v0.2"
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
        "\nTARGET : opportunity_signals"
    )

    print(
        "LOOKING FOR : REAL WRITE / PRODUCER EVIDENCE"
    )

    print("=" * 110)


if __name__ == "__main__":
    main()