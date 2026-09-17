
from pathlib import Path
import re

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

EXCLUDE = (
    "verify_",
    "test_",
    "audit_",
    "forensic_",
    "debug_",
    "repair_",
)

PATTERNS = (
    r"^\s*(from|import)\s+.*(?:bitpin|exchange|adapter)",
    r"^\s*class\s+.*(?:adapter|exchange|market)",
    r"^\s*def\s+.*(?:market|exchange|ticker|orderbook|account|balance)",
    r"\b(?:requests|httpx|urllib)\.",
    r"\.get\(",
    r"\.post\(",
    r"\b(?:BITPIN|Bitpin)\b",
    r"\b(?:exchange|adapter)\b",
)

compiled = [re.compile(x, re.I) for x in PATTERNS]


def candidate(path: Path) -> bool:
    name = path.name.lower()

    if not path.is_file():
        return False

    if path.suffix.lower() != ".py":
        return False

    if name.startswith(EXCLUDE):
        return False

    if name in {
        "toobit_trading_adapter.py",
        "bitpin_trading_adapter.py",
    }:
        return False

    return True


def main():
    print("=" * 90)
    print("ARUNDA TRADER — PRODUCTION EXCHANGE BOUNDARY DISCOVERY v0.3")
    print("=" * 90)
    print("MODE       : READ-ONLY")
    print("WRITE      : NONE")
    print("EXECUTION  : FALSE")
    print("=" * 90)

    found = 0

    for path in sorted(ROOT.rglob("*.py")):
        if not candidate(path):
            continue

        try:
            lines = path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()
        except Exception:
            continue

        hits = []

        for n, line in enumerate(lines, 1):
            s = line.strip()

            if not s or s.startswith("#"):
                continue

            # فقط خطوطی که واقعاً ساختاری هستند
            if any(p.search(line) for p in compiled):
                hits.append((n, s))

        if not hits:
            continue

        found += 1

        print()
        print(f"FILE: {path.relative_to(ROOT)}")

        # حداکثر 12 خط از هر فایل
        for n, line in hits[:12]:
            print(f"  {n}: {line}")

        if len(hits) > 12:
            print(f"  ... {len(hits) - 12} more")

    print()
    print("=" * 90)
    print(f"FILES WITH RELEVANT HITS: {found}")
    print("=" * 90)
    print("HARD STOP — READ ONLY")


if __name__ == "__main__":
    main()