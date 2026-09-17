import os
import re

ROOT = os.getcwd()

patterns = [
    "TRADE_GATE_CANDIDATES",
    "FULLY_QUALIFIED_CANDIDATES",
    "OPPORTUNITY_STATUS:",
    "OPPORTUNITY_CONFIDENCE:",
    "OPPORTUNITY_SCORE:",
    "DECISION_STATE:",
    "RISK_STATUS:",
]

print("=== CHECKPOINT 13 AGGREGATE PRODUCER TRACE ===")

for root, dirs, files in os.walk(ROOT):
    dirs[:] = [
        d for d in dirs
        if d not in {".git", "__pycache__", ".venv", "venv"}
    ]

    for name in files:
        if not name.endswith((".py", ".txt", ".log")):
            continue

        path = os.path.join(root, name)

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            continue

        hits = []

        for i, line in enumerate(lines):
            if any(p in line for p in patterns):
                hits.append((i + 1, line.rstrip()))

        if hits:
            print()
            print("=" * 80)
            print(path)
            print("=" * 80)

            for line_no, line in hits:
                print(f"{line_no}: {line}")

                start = max(0, line_no - 6)
                end = min(len(lines), line_no + 6)

                for j in range(start, end):
                    if j + 1 == line_no:
                        continue
                    text = lines[j].rstrip()
                    if text.strip():
                        print(f"    {j + 1}: {text}")

print()
print("=== SAFETY ===")
print("RUNTIME=FALSE")
print("DB_WRITES=0")
print("PRODUCTION_DB_TOUCHED=FALSE")
print("EXECUTION=OFF")
