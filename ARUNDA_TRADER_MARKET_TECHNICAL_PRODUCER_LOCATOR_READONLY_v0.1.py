import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 90)
print("ARUNDA MARKET_TECHNICAL PRODUCER LOCATOR READONLY v0.1")
print("=" * 90)
print("MODE : READ ONLY")
print()

for root, dirs, files in os.walk(BASE_DIR):
    dirs[:] = [d for d in dirs if d not in {
        ".git", "__pycache__", "venv", ".venv"
    }]

    for file in files:
        if not file.endswith(".py"):
            continue

        path = os.path.join(root, file)

        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
        except Exception:
            continue

        for i, line in enumerate(lines, 1):
            text = line.lower()

            if (
                "market_technical" in text
                and (
                    "insert" in text
                    or "update" in text
                    or "executemany" in text
                    or "execute" in text
                )
            ):
                print("-" * 90)
                print("FILE :", os.path.relpath(path, BASE_DIR))
                print("LINE :", i)
                print("CODE :", line.strip())

                start = max(0, i - 3)
                end = min(len(lines), i + 2)

                print("CONTEXT:")
                for n in range(start, end):
                    print(f"{n + 1}: {lines[n].rstrip()}")

print()
print("=" * 90)
print("LOCATOR COMPLETE")
print("=" * 90)