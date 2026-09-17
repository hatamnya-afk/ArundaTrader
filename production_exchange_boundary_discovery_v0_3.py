
from pathlib import Path

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

EXCLUDE = (
    "verify_",
    "test_",
    "audit_",
    "forensic_",
    "debug_",
    "repair_",
)

KEYWORDS = (
    "bitpin",
    "exchange",
    "adapter",
    "market",
    "ticker",
    "orderbook",
)

SKIP = {
    "toobit_trading_adapter.py",
    "bitpin_trading_adapter.py",
}


def main():
    print("=" * 80)
    print("ARUNDA TRADER — PRODUCTION BOUNDARY FILE FINDER")
    print("=" * 80)
    print("MODE: READ-ONLY")
    print("WRITE: NONE")
    print("=" * 80)

    results = []

    for path in ROOT.rglob("*.py"):
        name = path.name.lower()

        if name in SKIP:
            continue

        if name.startswith(EXCLUDE):
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).lower()
        except Exception:
            continue

        matches = [
            key
            for key in KEYWORDS
            if key in text
        ]

        if matches:
            results.append(
                (
                    path.relative_to(ROOT),
                    matches,
                )
            )

    # اول فایل‌هایی که بیشترین ارتباط را دارند
    results.sort(
        key=lambda x: (-len(x[1]), str(x[0]))
    )

    print()
    print(f"CANDIDATE FILES: {min(len(results), 30)}")
    print()

    for path, matches in results[:30]:
        print(
            f"{path}  [{', '.join(matches)}]"
        )

    if len(results) > 30:
        print()
        print(
            f"... {len(results) - 30} additional files omitted"
        )

    print()
    print("=" * 80)
    print("HARD STOP — NO FILES MODIFIED")
    print("=" * 80)


if __name__ == "__main__":
    main()