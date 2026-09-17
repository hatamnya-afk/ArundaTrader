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
    "_backups",
    "backups",
}

TARGET_TABLE = "opportunity_signals"

PRODUCER_TERMS = [
    "opportunity_score",
    "rank_overall",
    "rank_side",
    "signal_strength",
    "fused_score",
    "snapshot_id",
    "opportunity",
]

UPSTREAM_TERMS = [
    "fusion_signals",
    "fusion_score",
    "FUSION_v0.5",
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


def print_context(
    path,
    lines,
    start,
    end,
    matched,
):

    print()
    print("=" * 110)
    print("REAL OPPORTUNITY PRODUCER CANDIDATE")
    print("=" * 110)

    print("FILE :", path)

    print(
        "MATCHED TERMS :",
        ", ".join(sorted(matched)),
    )

    print(
        f"LINES : {start + 1}-{end}"
    )

    print("-" * 110)

    for i in range(start, end):

        print(
            f"{i + 1:6} | "
            f"{lines[i].rstrip()}"
        )


def is_producer_candidate(
    text,
):

    lower = text.lower()

    producer_hits = sum(
        1
        for term in PRODUCER_TERMS
        if term.lower() in lower
    )

    upstream_hits = sum(
        1
        for term in UPSTREAM_TERMS
        if term.lower() in lower
    )

    has_target = (
        TARGET_TABLE.lower()
        in lower
    )

    has_write = bool(
        re.search(
            r"""
            \bINSERT\s+
            (?:OR\s+\w+\s+)?
            INTO\s+
            ["'`]?opportunity_signals
            |
            \bUPDATE\s+
            ["'`]?opportunity_signals
            """,
            text,
            re.IGNORECASE
            | re.VERBOSE,
        )
    )

    return (
        has_target
        and producer_hits >= 3
        and upstream_hits >= 1
        and has_write
    )


def scan_file(path):

    lines = read_file(path)

    if not lines:

        return

    text = "".join(lines)

    if not is_producer_candidate(text):

        return

    matched = set()

    for term in (
        PRODUCER_TERMS
        + UPSTREAM_TERMS
    ):

        if term.lower() in text.lower():

            matched.add(term)

    # فقط محل‌های write واقعی را نمایش بده
    patterns = [
        r"\bINSERT\s+(?:OR\s+\w+\s+)?INTO\s+['\"`]?opportunity_signals",
        r"\bUPDATE\s+['\"`]?opportunity_signals",
    ]

    positions = []

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text,
            re.IGNORECASE,
        ):

            positions.append(
                match.start()
            )

    if not positions:

        return

    for position in positions:

        line_no = text.count(
            "\n",
            0,
            position,
        )

        start = max(
            0,
            line_no - 35,
        )

        end = min(
            len(lines),
            line_no + 36,
        )

        print_context(
            path,
            lines,
            start,
            end,
            matched,
        )


def main():

    print("=" * 110)

    print(
        "ARUNDA TRADER — REAL OPPORTUNITY PRODUCER DISCOVERY v0.2"
    )

    print("=" * 110)

    print("MODE    : READ ONLY")
    print("PROJECT :", PROJECT_ROOT)
    print("TARGET  :", TARGET_TABLE)
    print("WRITE   : NONE")

    print("=" * 110)

    scanned = 0
    candidates = 0

    for root, dirs, files in os.walk(
        PROJECT_ROOT
    ):

        dirs[:] = [
            d
            for d in dirs
            if d not in SKIP_DIRS
        ]

        for filename in files:

            if not filename.endswith(
                ".py"
            ):

                continue

            # discovery scripts قبلی را دوباره بررسی نکن
            if (
                filename.startswith(
                    "FIND_OPPORTUNITY_"
                )
                or filename.startswith(
                    "FIND_REAL_OPPORTUNITY_"
                )
            ):

                continue

            path = os.path.join(
                root,
                filename,
            )

            scanned += 1

            before = candidates

            lines = read_file(path)

            if not lines:

                continue

            text = "".join(lines)

            if is_producer_candidate(
                text
            ):

                candidates += 1

                scan_file(path)

    print()
    print("=" * 110)
    print("SCAN COMPLETE")
    print("=" * 110)

    print(
        "Production Python files scanned :",
        scanned,
    )

    print(
        "Producer candidates              :",
        candidates,
    )

    print()
    print(
        "هدف: پیدا کردن writer واقعی "
        "opportunity_signals از مسیر fusion."
    )

    print("=" * 110)


if __name__ == "__main__":
    main()