import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "v0.2"

PRODUCTION_DB = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

LAUNCH_ROOT = Path(r"C:\Users\ASUS\AppData\Local\Temp")

REPORT_NAMES = [
    "LIVE_PAPER_TRADE_SIMULATION_POSITION_LIFECYCLE_REPORT.json",
    "LIVE_PAPER_TRADE_OUTCOME_PNL_RECONCILIATION_REPORT.json",
    "LIVE_PAPER_POSITION_MONITORING_DYNAMIC_EXIT_MTM_REPORT.json",
    "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_REPORT.json",
]

OUTPUT_REPORT_NAME = (
    "LIVE_PAPER_LIFECYCLE_STATE_CAPTURE_FROM_ISOLATED_LAUNCH_REPORT.json"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def db_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)

    size = path.stat().st_size
    sha = sha256_file(path)

    rows = None

    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table'"
                )
            }

            if "fusion_signals" in tables:
                rows = conn.execute(
                    "SELECT COUNT(*) FROM fusion_signals"
                ).fetchone()[0]

    except Exception:
        rows = None

    return {
        "size": size,
        "sha256": sha,
        "rows": rows,
    }


def print_section(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        value = json.load(f)

    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")

    return value


def find_latest_launch() -> Path | None:
    candidates = []

    for path in LAUNCH_ROOT.glob("arunda_live_launch_*"):
        if path.is_dir():
            candidates.append(path)

    if not candidates:
        return None

    candidates.sort(
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return candidates[0]


def discover_reports(launch_dir: Path) -> dict[str, Path]:
    found = {}

    for name in REPORT_NAMES:
        path = launch_dir / name

        if path.exists() and path.is_file():
            found[name] = path

    return found


def extract_snapshot(
    report: dict[str, Any],
) -> dict[str, Any] | None:

    candidate_keys = [
        "current_snapshot",
        "snapshot",
        "latest_snapshot",
        "portfolio_snapshot",
        "current_state",
    ]

    for key in candidate_keys:
        value = report.get(key)

        if isinstance(value, dict):
            snapshot = dict(value)

            if (
                snapshot.get("snapshot_id")
                or snapshot.get("id")
                or snapshot.get("timestamp")
            ):
                return snapshot

    snapshots = report.get("snapshots")

    if isinstance(snapshots, list):
        valid = [
            item
            for item in snapshots
            if isinstance(item, dict)
            and (
                item.get("snapshot_id")
                or item.get("id")
                or item.get("timestamp")
            )
        ]

        if valid:
            return valid[-1]

    return None


def normalize_snapshot(
    snapshot: dict[str, Any],
    source_report: str,
) -> dict[str, Any]:

    snapshot_id = (
        snapshot.get("snapshot_id")
        or snapshot.get("id")
        or snapshot.get("snapshot")
    )

    timestamp = (
        snapshot.get("timestamp")
        or snapshot.get("time")
        or snapshot.get("created_at")
        or snapshot.get("observed_at")
    )

    return {
        "snapshot_id": snapshot_id,
        "timestamp": timestamp,
        "positions": snapshot.get(
            "positions",
            snapshot.get("position_count", 0),
        ),
        "open_positions": snapshot.get(
            "open_positions",
            snapshot.get("open_position_count", 0),
        ),
        "closed_positions": snapshot.get(
            "closed_positions",
            snapshot.get("closed_position_count", 0),
        ),
        "analytical_notional": snapshot.get(
            "analytical_notional",
            snapshot.get("notional", 0.0),
        ),
        "portfolio_risk": snapshot.get(
            "portfolio_risk",
            snapshot.get("risk", 0.0),
        ),
        "realized_pnl": snapshot.get(
            "realized_pnl",
            snapshot.get("realized_pnl_value", 0.0),
        ),
        "unrealized_pnl": snapshot.get(
            "unrealized_pnl",
            snapshot.get("unrealized_pnl_value", 0.0),
        ),
        "total_pnl": snapshot.get(
            "total_pnl",
            snapshot.get("pnl", 0.0),
        ),
        "current_drawdown": snapshot.get(
            "current_drawdown",
            0.0,
        ),
        "maximum_drawdown": snapshot.get(
            "maximum_drawdown",
            0.0,
        ),
        "max_concentration": snapshot.get(
            "max_concentration",
            0.0,
        ),
        "circuit_breaker": snapshot.get(
            "circuit_breaker",
            "UNKNOWN",
        ),
        "source_report": source_report,
    }


def validate_snapshot(
    snapshot: dict[str, Any],
) -> tuple[bool, list[str]]:

    required = [
        "snapshot_id",
        "timestamp",
    ]

    missing = [
        key
        for key in required
        if snapshot.get(key) in (None, "")
    ]

    return len(missing) == 0, missing


def find_snapshot_in_reports(
    reports: dict[str, Path],
) -> tuple[dict[str, Any] | None, str | None]:

    priority = [
        "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_REPORT.json",
        "LIVE_PAPER_POSITION_MONITORING_DYNAMIC_EXIT_MTM_REPORT.json",
        "LIVE_PAPER_TRADE_OUTCOME_PNL_RECONCILIATION_REPORT.json",
        "LIVE_PAPER_TRADE_SIMULATION_POSITION_LIFECYCLE_REPORT.json",
    ]

    for name in priority:
        path = reports.get(name)

        if path is None:
            continue

        try:
            report = load_json(path)
        except Exception:
            continue

        snapshot = extract_snapshot(report)

        if snapshot is not None:
            return (
                normalize_snapshot(snapshot, name),
                name,
            )

    return None, None


def main() -> None:
    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER LIFECYCLE STATE CAPTURE "
        "FROM ISOLATED LAUNCH " + VERSION
    )
    print("=" * 100)

    print_section("OBJECTIVE")

    print(
        "Consume ONLY the actual isolated LIVE PAPER launch."
    )
    print(
        "Capture a portfolio state only when an upstream PAPER "
        "lifecycle/state report genuinely exists."
    )
    print("Synthetic snapshot : FORBIDDEN")
    print("Production DB write : FORBIDDEN")
    print("Real order          : FORBIDDEN")

    print_section("SAFETY POLICY")

    print("Production DB writes : FORBIDDEN")
    print("Production engine run : NO")
    print("Historical repair    : NONE")
    print("Direction inference  : NONE")
    print("Score reconstruction : NONE")
    print("Synthetic data       : FORBIDDEN")
    print("Live data injection  : NONE")
    print("Order execution      : NONE")
    print("PAPER EXECUTION      : ANALYTICAL ONLY")

    print_section("PRODUCTION BASELINE")

    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(
            f"Production DB not found: {PRODUCTION_DB}"
        )

    before = db_fingerprint(PRODUCTION_DB)

    print(f"Rows   : {before['rows']}")
    print(f"Size   : {before['size']}")
    print(f"SHA256 : {before['sha256']}")

    print_section("ISOLATED LIVE LAUNCH DISCOVERY")

    launch_dir = find_latest_launch()

    if launch_dir is None:
        print("No isolated LIVE launch directory found.")
        print("RESULT : BLOCKED")
        return

    isolated_db = launch_dir / "arunda_live_capture.db"

    print(f"Directory : {launch_dir}")

    if isolated_db.exists():
        print(f"Isolated DB : {isolated_db}")
    else:
        print("Isolated DB : NOT FOUND")

    print_section("PAPER REPORT DISCOVERY")

    reports = discover_reports(launch_dir)

    for name in REPORT_NAMES:
        if name in reports:
            print(f"FOUND   | {name}")
        else:
            print(f"MISSING | {name}")

    print_section("UPSTREAM PAPER SNAPSHOT")

    snapshot, source_report = find_snapshot_in_reports(reports)

    if snapshot is None:
        print("NEW PORTFOLIO SNAPSHOT : NOT AVAILABLE")
        print()
        print(
            "The verified isolated FUSION launch did not produce "
            "a consumable PAPER lifecycle/state snapshot."
        )
        print()
        print(
            "The script REFUSES to construct portfolio state "
            "from fusion_signals."
        )
        print()
        print("RESULT : INSUFFICIENT_DATA")

        after = db_fingerprint(PRODUCTION_DB)

        print_section("PRODUCTION DATABASE INVARIANT")

        print(f"Before rows  : {before['rows']}")
        print(f"After rows   : {after['rows']}")
        print(f"Before size  : {before['size']}")
        print(f"After size   : {after['size']}")
        print(f"Before SHA256: {before['sha256']}")
        print(f"After SHA256 : {after['sha256']}")

        invariant = (
            before["rows"] == after["rows"]
            and before["size"] == after["size"]
            and before["sha256"] == after["sha256"]
        )

        print(
            "PRODUCTION DB INVARIANT : "
            + ("PASS" if invariant else "FAIL")
        )

        report = {
            "version": VERSION,
            "frontier": (
                "LIVE_PAPER_LIFECYCLE_STATE_CAPTURE_"
                "FROM_ISOLATED_LAUNCH"
            ),
            "status": "INSUFFICIENT_DATA",
            "new_portfolio_snapshot": False,
            "reason": "NO_PAPER_LIFECYCLE_STATE_REPORT",
            "launch_directory": str(launch_dir),
            "production_db_invariant": invariant,
            "production_before": before,
            "production_after": after,
            "synthetic_snapshot_created": False,
            "real_order_execution": False,
            "paper_execution": "ANALYTICAL_ONLY",
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        output = launch_dir / OUTPUT_REPORT_NAME

        with output.open("w", encoding="utf-8") as f:
            json.dump(
                report,
                f,
                indent=2,
                ensure_ascii=False,
            )

        print()
        print(f"Runtime report : {output}")
        return

    valid, missing = validate_snapshot(snapshot)

    if not valid:
        print("SNAPSHOT FOUND : INVALID")
        print(f"Missing fields : {missing}")
        print("RESULT : BLOCKED")
        return

    print(f"Source report        : {source_report}")
    print(f"Snapshot ID          : {snapshot['snapshot_id']}")
    print(f"Timestamp            : {snapshot['timestamp']}")
    print(f"Positions            : {snapshot['positions']}")
    print(f"Open positions       : {snapshot['open_positions']}")
    print(f"Closed positions     : {snapshot['closed_positions']}")

    print(
        f"Analytical notional  : "
        f"{float(snapshot['analytical_notional'] or 0):.6f}"
    )

    print(
        f"Portfolio risk       : "
        f"{float(snapshot['portfolio_risk'] or 0):.6f}"
    )

    print(
        f"Realized P&L         : "
        f"{float(snapshot['realized_pnl'] or 0):.6f}"
    )

    print(
        f"Unrealized P&L       : "
        f"{float(snapshot['unrealized_pnl'] or 0):.6f}"
    )

    print(
        f"Total P&L            : "
        f"{float(snapshot['total_pnl'] or 0):.6f}"
    )

    print(
        f"Current drawdown     : "
        f"{float(snapshot['current_drawdown'] or 0):.6f}"
    )

    print(
        f"Maximum drawdown     : "
        f"{float(snapshot['maximum_drawdown'] or 0):.6f}"
    )

    print(
        f"Max concentration    : "
        f"{float(snapshot['max_concentration'] or 0):.6f}"
    )

    print(
        f"Circuit breaker      : "
        f"{snapshot['circuit_breaker']}"
    )

    after = db_fingerprint(PRODUCTION_DB)

    invariant = (
        before["rows"] == after["rows"]
        and before["size"] == after["size"]
        and before["sha256"] == after["sha256"]
    )

    print_section("PRODUCTION DATABASE INVARIANT")

    print(f"Before rows  : {before['rows']}")
    print(f"After rows   : {after['rows']}")
    print(f"Before size  : {before['size']}")
    print(f"After size   : {after['size']}")
    print(f"Before SHA256: {before['sha256']}")
    print(f"After SHA256 : {after['sha256']}")

    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if invariant else "FAIL")
    )

    print_section(
        "LIVE PAPER LIFECYCLE STATE CAPTURE VERDICT"
    )

    print("UPSTREAM_PAPER_STATE_FOUND : PASS")
    print("SNAPSHOT_IDENTITY          : PASS")

    print(
        "PRODUCTION_ISOLATION       : "
        + ("PASS" if invariant else "FAIL")
    )

    print(
        "NEW_PORTFOLIO_SNAPSHOT     : "
        + ("PASS" if invariant else "BLOCKED")
    )

    report = {
        "version": VERSION,
        "frontier": (
            "LIVE_PAPER_LIFECYCLE_STATE_CAPTURE_"
            "FROM_ISOLATED_LAUNCH"
        ),
        "status": "PASS" if invariant else "BLOCKED",
        "new_portfolio_snapshot": bool(invariant),
        "snapshot": snapshot,
        "source_report": source_report,
        "launch_directory": str(launch_dir),
        "production_db_invariant": invariant,
        "production_before": before,
        "production_after": after,
        "synthetic_snapshot_created": False,
        "real_order_execution": False,
        "paper_execution": "ANALYTICAL_ONLY",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    output = launch_dir / OUTPUT_REPORT_NAME

    with output.open("w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(f"Runtime report : {output}")


if __name__ == "__main__":
    main()