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


def scan_file(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as f:
            text = f.read()
    except Exception:
        return

    if TARGET not in text:
        return

    lines = text.splitlines()

    print("\n" + "=" * 100)
    print("FILE :", path)
    print("=" * 100)

    found = False

    for i, line in enumerate(lines):

        if TARGET not in line:
            continue

        found = True

        start = max(0, i - 8)
        end = min(len(lines), i + 12)

        print(
            f"\n--- LINES {start + 1}-{end} ---"
        )

        for n in range(start, end):
            print(
                f"{n + 1:5} | {lines[n]}"
            )

    if not found:
        return


def main():

    print("=" * 100)
    print("ARUNDA TRADER — OPPORTUNITY PRODUCER DISCOVERY v0.1")
    print("=" * 100)

    print("MODE        : READ ONLY")
    print("PROJECT     :", PROJECT_ROOT)
    print("TARGET      :", TARGET)
    print("WRITE       : NONE")
    print("=" * 100)

    if not os.path.isdir(PROJECT_ROOT):

        print(
            "\nPROJECT DIRECTORY NOT FOUND"
        )

        return

    file_count = 0

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
                filename
            )

            file_count += 1

            scan_file(path)

    print("\n" + "=" * 100)
    print("SCAN COMPLETE")
    print("=" * 100)

    print(
        "Python files scanned :",
        file_count
    )

    print(
        "\nNEXT:"
    )

    print(
        "Send me the output showing the files/functions"
    )

    print(
        "that WRITE or PRODUCE opportunity_signals."
    )

    print("=" * 100)


if __name__ == "__main__":
    main()