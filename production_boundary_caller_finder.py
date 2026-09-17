
from pathlib import Path
import re

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGETS = {
    "arunda_recorder.py",
    "market_recorder.py",
    "hunter_recorder.py",
    "trade_gate_engine.py",
    "market_adapter.py",
    "ARUNDA_LIVE_DATA_ENTRYPOINT_FORENSIC_v0.1.py",
    "ARUNDA_TRADER_LIVE_INFORMATION_ARMS_RUNTIME_BOUNDARY_TRACE_v0.1.py",
    "ARUNDA_LAUNCH_DATA_CONTRACT_v0.1.py",
}

EXCLUDE = (
    "verify_",
    "test_",
    "audit_",
    "forensic_",
    "debug_",
    "repair_",
)


def main():
    print("=" * 90)
    print("ARUNDA TRADER — PRODUCTION BOUNDARY CALLER FINDER")
    print("=" * 90)
    print("MODE: READ-ONLY")
    print("WRITE: NONE")
    print("=" * 90)

    found = 0

    for path in sorted(ROOT.rglob("*.py")):
        name = path.name.lower()

        if name.startswith(EXCLUDE):
            continue

        if path.name in TARGETS:
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        hits = []

        for target in TARGETS:
            stem = Path(target).stem

            patterns = (
                rf"\bimport\s+{re.escape(stem)}\b",
                rf"\bfrom\s+{re.escape(stem)}\s+import\b",
                rf"\b{re.escape(stem)}\.",
            )

            if any(
                re.search(p, text, re.IGNORECASE)
                for p in patterns
            ):
                hits.append(target)

        if hits:
            found += 1
            print(
                f"{path.relative_to(ROOT)}"
            )
            for target in hits:
                print(f"  -> {target}")

    print()
    print("=" * 90)
    print(f"CALLER FILES FOUND: {found}")
    print("=" * 90)
    print("HARD STOP — READ ONLY")


if __name__ == "__main__":
    main()