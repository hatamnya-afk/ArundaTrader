from pathlib import Path

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

FILES = [
    "execution_contract.py",
    "execution_engine.py",
    "orderbook.py",
    "ARUNDA_LIVE_DATA_ENTRYPOINT_FORENSIC_v0.1.py",
    "find_execution_path.py",
]

KEYWORDS = (
    "bitpin",
    "authorization",
    "api_key",
    "api_secret",
    "signature",
    "nonce",
    "balance",
    "account",
    "wallet",
    "create_order",
    "place_order",
    "cancel_order",
    "private",
    "post(",
    "delete(",
)

print("=" * 80)
print("ARUNDA TRADER — BITPIN PRIVATE CANDIDATE INSPECTION v0.1")
print("=" * 80)
print("MODE              : READ ONLY")
print("REQUESTS          : NONE")
print("DATABASE WRITES   : NONE")
print("ORDERS            : NONE")
print()

for filename in FILES:

    path = ROOT / filename

    print("-" * 80)
    print("FILE :", filename)
    print("-" * 80)

    if not path.exists():
        print("NOT FOUND")
        continue

    lines = path.read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines()

    found = 0

    for i, line in enumerate(lines):

        low = line.lower()

        if any(k in low for k in KEYWORDS):

            found += 1

            start = max(0, i - 1)
            end = min(len(lines), i + 2)

            print(f"\n[{i + 1}]")

            for j in range(start, end):
                print(f"{j + 1:5}: {lines[j]}")

            if found >= 12:
                print("\n... LIMIT 12 HITS ...")
                break

    if found == 0:
        print("NO RELEVANT HITS")

print()
print("=" * 80)
print("INSPECTION COMPLETE")
print("=" * 80)
print("NO REQUESTS SENT")
print("NO DB WRITES")
print("NO ORDERS")
print("=" * 80)