
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

TARGETS = (
    "market_adapter",
    "arunda_recorder",
    "market_recorder",
    "market_snapshot_engine",
)


def production_file(path):
    name = path.name.lower()

    if not path.is_file():
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
    print("ARUNDA TRADER — PRODUCTION RUNTIME ENTRY BOUNDARY FINDER")
    print("=" * 90)
    print("MODE: READ-ONLY")
    print("WRITE: NONE")
    print("EXECUTION: FALSE")
    print("=" * 90)

    results = []

    for path in sorted(ROOT.rglob("*.py")):
        if not production_file(path):
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        has_main = bool(
            re.search(
                r'if\s+__name__\s*==\s*["\']__main__["\']',
                text,
            )
        )

        imports = []

        for target in TARGETS:
            if re.search(
                rf'\b(?:import|from)\s+{re.escape(target)}\b',
                text,
                re.IGNORECASE,
            ):
                imports.append(target)

        if has_main or imports:
            results.append(
                (
                    path.relative_to(ROOT),
                    has_main,
                    imports,
                )
            )

    print()

    if not results:
        print("NO PRODUCTION ENTRY CANDIDATE FOUND")
    else:
        for path, has_main, imports in results:
            print(f"FILE: {path}")

            if has_main:
                print("  MAIN: YES")

            if imports:
                print(
                    "  IMPORTS:",
                    ", ".join(imports),
                )

    print()
    print("=" * 90)
    print(f"CANDIDATES: {len(results)}")
    print("HARD STOP — READ ONLY")
    print("=" * 90)


if __name__ == "__main__":
    main()