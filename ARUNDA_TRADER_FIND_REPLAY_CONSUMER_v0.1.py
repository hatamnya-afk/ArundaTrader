from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def main() -> int:
    print("=" * 100)
    print("ARUNDA TRADER")
    print("FIND ACTUAL REPLAY CONSUMER v0.1")
    print("=" * 100)
    print()
    print(f"PROJECT ROOT : {PROJECT_ROOT}")
    print("MODE         : READ_ONLY")
    print()
    print("SAFETY")
    print("=" * 100)
    print("Database write     : False")
    print("Network access     : False")
    print("Producer execution: False")
    print("Signal creation    : False")
    print("Signal injection   : False")
    print("Replay execution   : False")
    print()

    candidates = []

    for path in sorted(PROJECT_ROOT.glob("*.py")):
        name = path.name.lower()

        if (
            "replay" in name
            or "eligible_signal" in name
            or "signal_path" in name
        ):
            candidates.append(path)

    print("=" * 100)
    print("REPLAY CONSUMER CANDIDATES")
    print("=" * 100)

    if not candidates:
        print("NO_CANDIDATE_FOUND")
        print()
        print("Search pattern:")
        print("  *replay*.py")
        print("  *eligible_signal*.py")
        print("  *signal_path*.py")
        print("=" * 100)
        return 1

    for index, path in enumerate(candidates, start=1):
        print()
        print(f"[{index}] {path.name}")
        print(f"    FULL PATH : {path}")
        print(f"    SIZE      : {path.stat().st_size} bytes")

    print()
    print("=" * 100)
    print("RESULT")
    print("=" * 100)
    print(f"CANDIDATE COUNT : {len(candidates)}")
    print("STATUS          : DISCOVERY_ONLY")
    print("REPAIR          : NOT_PERFORMED")
    print("EXECUTION       : NOT_PERFORMED")
    print("VALIDATION      : NOT_VERIFIED")
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())