import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 100)
print("ARUNDA MARKET TECHNICAL REAL WRITE CALLER FORENSIC v0.1")
print("=" * 100)
print("MODE : READ ONLY")
print("EXECUTION : NO")
print("DB WRITE : NO")
print()

patterns = [
    r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+market_technical",
    r"UPDATE\s+market_technical",
    r"executemany\s*\(",
]

for root, dirs, files in os.walk(BASE_DIR):
    dirs[:] = [
        d for d in dirs
        if d not in {".git", "__pycache__", "venv", ".venv"}
    ]

    for name in files:
        if not name.endswith(".py"):
            continue

        path = os.path.join(root, name)

        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
        except Exception:
            continue

        for i, line in enumerate(lines):
            if not any(
                re.search(p, line, re.IGNORECASE)
                for p in patterns
            ):
                continue

            # Find nearest function
            function = "UNKNOWN"

            for j in range(i, -1, -1):
                m = re.match(
                    r"\s*(?:async\s+)?def\s+(\w+)\s*\(",
                    lines[j],
                )
                if m:
                    function = m.group(1)
                    break

            print("-" * 100)
            print("FILE     :", os.path.relpath(path, BASE_DIR))
            print("LINE     :", i + 1)
            print("FUNCTION :", function)
            print("CODE     :", line.strip())
            print("CONTEXT  :")

            for k in range(
                max(0, i - 2),
                min(len(lines), i + 3)
            ):
                print(f"{k + 1}: {lines[k].rstrip()}")

print()
print("=" * 100)
print("FINAL REAL WRITE CALLER FORENSIC")
print("=" * 100)
print("READ ONLY       : YES")
print("EXECUTION       : NONE")
print("DB MODIFICATION : NONE")
print("SOURCE MODIFY   : NONE")
print("=" * 100)
print("FORENSIC STATUS : COMPLETE")
print("=" * 100)