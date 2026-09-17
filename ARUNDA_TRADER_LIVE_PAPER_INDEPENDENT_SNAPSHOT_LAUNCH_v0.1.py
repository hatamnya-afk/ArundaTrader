from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = PROJECT_ROOT / "arunda.db"

# Existing live-paper launch directory discovered from the verified reports.
CURRENT_LAUNCH_DIR = Path(
    r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc"
)

# Existing upstream reports.
UPSTREAM_REPORTS = [
    "LIVE_TRADE_RISK_POSITION_SIZING_REPORT.json",
    "LIVE_TRADE_PLAN_STOP_TP_REPORT.json",
    "LIVE_PAPER_TRADE_SIMULATION_POSITION_LIFECYCLE_REPORT.json",
    "LIVE_PAPER_TRADE_OUTCOME_PNL_RECONCILIATION_REPORT.json",
    "LIVE_PAPER_POSITION_MONITORING_DYNAMIC_EXIT_MTM_REPORT.json",
    "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_REPORT.json",
    "LIVE_PAPER_PORTFOLIO_RISK_LIMITS_CIRCUIT_BREAKER_GATE_REPORT.json",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def db_fingerprint() -> dict[str, Any]:
    stat = DB_PATH.stat()

    return {
        "exists": True,
        "rows": None,
        "size": stat.st_size,
        "sha256": sha256_file(DB_PATH),
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)

    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object: {path}")

    return obj


def extract_snapshot(report: dict[str, Any]) -> str | None:
    candidates = [
        report.get("snapshot"),
        report.get("snapshot_id"),
        report.get("current_snapshot"),
        report.get("fusion_snapshot"),
    ]

    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()

    upstream = report.get("upstream")

    if isinstance(upstream, dict):
        for key in (
            "snapshot",
            "snapshot_id",
            "current_snapshot",
            "fusion_snapshot",
        ):
            value = upstream.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def find_upstream_snapshot() -> tuple[str | None, str | None]:
    for filename in UPSTREAM_REPORTS:
        path = CURRENT_LAUNCH_DIR / filename

        if not path.exists():
            continue

        try:
            report = load_json(path)
        except Exception:
            continue

        snapshot = extract_snapshot(report)

        if snapshot:
            return snapshot, filename

    return None, None


def discover_live_launchers() -> list[Path]:
    patterns = [
        "*LIVE*LAUNCH*.py",
        "*PAPER*LAUNCH*.py",
        "*LIVE*PAPER*.py",
    ]

    found: set[Path] = set()

    for pattern in patterns:
        for path in PROJECT_ROOT.glob(pattern):
            if path.is_file():
                found.add(path)

    return sorted(found)


def create_run_directory() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = Path(
        os.environ.get("TEMP", r"C:\Users\ASUS\AppData\Local\Temp")
    ) / f"arunda_independent_snapshot_{stamp}"

    path.mkdir(parents=True, exist_ok=False)
    return path


def main() -> None:
    print("=" * 100)
    print("ARUNDA TRADER LIVE PAPER INDEPENDENT SNAPSHOT LAUNCH v0.1")
    print("=" * 100)

    print()
    print("SAFETY POLICY")
    print("=" * 100)
    print("Production DB writes       : FORBIDDEN")
    print("Historical repair         : NONE")
    print("Direction inference       : NONE")
    print("Score reconstruction      : NONE")
    print("Synthetic snapshot        : FORBIDDEN")
    print("Live data injection       : NONE")
    print("REAL ORDER EXECUTION      : FORBIDDEN")
    print("PAPER EXECUTION           : ANALYTICAL ONLY")

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Production DB not found: {DB_PATH}")

    print()
    print("PRODUCTION BASELINE")
    print("=" * 100)

    before = db_fingerprint()

    print(f"Size   : {before['size']}")
    print(f"SHA256 : {before['sha256']}")

    old_snapshot, source_file = find_upstream_snapshot()

    print()
    print("CURRENT UPSTREAM SNAPSHOT")
    print("=" * 100)
    print(f"Snapshot : {old_snapshot}")
    print(f"Source   : {source_file}")

    launchers = discover_live_launchers()

    print()
    print("DISCOVERED LIVE-PAPER LAUNCHERS")
    print("=" * 100)

    if not launchers:
        print("No launcher automatically identified.")
        print()
        print("IMPORTANT:")
        print("Do NOT fabricate a snapshot.")
        print("Run the already-verified upstream live-paper launcher manually.")
        print()
        print("After that, rerun this script to verify whether the Snapshot ID changed.")
        return

    for i, launcher in enumerate(launchers, 1):
        print(f"{i} | {launcher}")

    print()
    print("=" * 100)
    print("SAFETY STOP")
    print("=" * 100)
    print(
        "The script will NOT automatically execute an unknown launcher."
    )
    print(
        "This prevents accidentally invoking production execution or an "
        "unverified entry point."
    )

    print()
    print("NEXT ACTION")
    print("=" * 100)
    print(
        "Select the exact launcher that previously produced the verified "
        "LIVE PAPER reports and execute THAT launcher in PAPER/ANALYTICAL mode."
    )
    print()
    print(
        "After the independent launch finishes, run this script again."
    )
    print()
    print(
        "Required condition:"
    )
    print(
        "NEW_SNAPSHOT_ID != OLD_SNAPSHOT_ID"
    )
    print()
    print(
        "Only then will the temporal evidence chain be allowed to continue."
    )

    after = db_fingerprint()

    print()
    print("PRODUCTION DATABASE CHECK")
    print("=" * 100)
    print(f"Before size   : {before['size']}")
    print(f"After size    : {after['size']}")
    print(f"Before SHA256 : {before['sha256']}")
    print(f"After SHA256  : {after['sha256']}")

    if (
        before["size"] == after["size"]
        and before["sha256"] == after["sha256"]
    ):
        print("PRODUCTION DB INVARIANT : PASS")
    else:
        print("PRODUCTION DB INVARIANT : FAIL")
        raise RuntimeError(
            "Production DB fingerprint changed."
        )


if __name__ == "__main__":
    main()