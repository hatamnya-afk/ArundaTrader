import os
import re


PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

TARGET_TERMS = [
    "opportunity_signals",
    "opportunity_score",
    "rank_overall",
    "rank_side",
    "signal_strength",
    "snapshot_id",
    "fused_score",
]


def read_file(path):

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as f:
            return f.readlines()

    except Exception:
        return []


def is_read_only_context(block):

    upper = block.upper()

    read_patterns = [
        "SELECT ",
        "FROM OPPORTUNITY_SIGNALS",
        "PRAGMA ",
        "SQLITE_MASTER",
    ]

    write_patterns = [
        "INSERT INTO OPPORTUNITY_SIGNALS",
        "UPDATE OPPORTUNITY_SIGNALS",
        "DELETE FROM OPPORTUNITY_SIGNALS",
    ]

    has_write = any(
        p in upper
        for p in write_patterns
    )

    has_read = any(
        p in upper
        for p in read_patterns
    )

    return has_read and not has_write


def scan_file(path):

    lines = read_file(path)

    if not lines:
        return

    text = "".join(lines)

    found_terms = []

    for term in TARGET_TERMS:

        if term.lower() in text.lower():

            found_terms.append(term)

    if len(found_terms) < 2:
        return

    # فقط فایل‌هایی که چند مؤلفه واقعی زنجیره opportunity
    # را با هم دارند.
    for i, line in enumerate(lines):

        lower = line.lower()

        if not any(
            term.lower() in lower
            for term in TARGET_TERMS
        ):
            continue

        start = max(
            0,
            i - 20,
        )

        end = min(
            len(lines),
            i + 21,
        )

        block = "".join(
            lines[start:end]
        )

        # موارد صرفاً خواندنی را حذف کن
        if is_read_only_context(block):
            continue

        print("\n" + "=" * 110)
        print("FILE :", path)
        print(
            f"LINES : {start + 1}-{end}"
        )
        print(
            "TERMS :",
            ", ".join(found_terms),
        )
        print("=" * 110)

        for n in range(
            start,
            end,
        ):

            print(
                f"{n + 1:6} | "
                f"{lines[n].rstrip()}"
            )

        print("-" * 110)


def main():

    print("=" * 110)
    print(
        "ARUNDA TRADER — OPPORTUNITY PRODUCER CHAIN DISCOVERY v0.1"
    )
    print("=" * 110)

    print("MODE    : READ ONLY")
    print("PROJECT :", PROJECT_ROOT)
    print("TARGET  : opportunity production chain")
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

            # اسکریپت‌های discovery قبلی را کنار بگذار
            if filename.startswith(
                "FIND_OPPORTUNITY_"
            ):
                continue

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
        "\nاین خروجی فقط فایل‌هایی را نشان می‌دهد"
    )

    print(
        "که چند مؤلفه از زنجیره واقعی opportunity"
    )

    print(
        "را همزمان مصرف/تولید می‌کنند."
    )

    print("=" * 110)


if __name__ == "__main__":
    main()