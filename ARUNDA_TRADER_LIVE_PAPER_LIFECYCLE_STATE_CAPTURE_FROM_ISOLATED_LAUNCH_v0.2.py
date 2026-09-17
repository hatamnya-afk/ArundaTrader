import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v0.2"

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
TEMP_DIR = Path(os.environ.get("TEMP", r"C:\Users\ASUS\AppData\Local\Temp"))

PRODUCTION_DB = PROJECT_DIR / "arunda.db"

LAUNCH_ROOT_PREFIX = "arunda_live_launch_"

OUTPUT_REPORT_NAME = (
    "LIVE_PAPER_LIFECYCLE_STATE_CAPTURE_FROM_ISOLATED_LAUNCH_REPORT.json"
)

REQUIRED_REPORTS = [
    "LIVE_PAPER_TRADE_SIMULATION_POSITION_LIFECYCLE_REPORT.json",
    "LIVE_PAPER_TRADE_OUTCOME_PNL_RECONCILIATION_REPORT.json",
    "LIVE_PAPER_POSITION_MONITORING_DYNAMIC_EXIT_MTM_REPORT.json",
    "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_REPORT.json",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def discover_launches() -> list[Path]:
    launches = []

    if not TEMP_DIR.exists():
        return launches

    for p in TEMP_DIR.iterdir():
        if not p.is_dir():
            continue

        if not p.name.startswith(LAUNCH_ROOT_PREFIX):
            continue

        isolated_db = p / "arunda_live_capture.db"

        if isolated_db.exists():
            launches.append(p)

    launches.sort(
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return launches


def discover_reports(launch_dir: Path) -> dict[str, Path | None]:
    result: dict[str, Path | None] = {}

    for name in REQUIRED_REPORTS:
        path = launch_dir / name

        if path.exists():
            result[name] = path
            continue

        result[name] = None

    return result


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

    except Exception:
        return None

    return None


def find_value(
    report: dict[str, Any],
    keys: list[str],
    default: Any = None,
) -> Any:
    for key in keys:
        if key in report:
            return report[key]

    return default


def extract_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    snapshot_id = find_value(
        report,
        [
            "current_snapshot",
            "snapshot_id",
            "current_snapshot_id",
            "snapshot",
        ],
    )

    timestamp = find_value(
        report,
        [
            "timestamp",
            "current_timestamp",
            "snapshot_timestamp",
            "observation_timestamp",
        ],
    )

    positions = find_value(
        report,
        [
            "positions",
            "position_count",
            "observed_position_count",
        ],
        0,
    )

    open_positions = find_value(
        report,
        [
            "open_positions",
            "open_position_count",
            "active_positions",
        ],
        0,
    )

    closed_positions = find_value(
        report,
        [
            "closed_positions",
            "closed_position_count",
        ],
        0,
    )

    notional = find_value(
        report,
        [
            "analytical_notional",
            "notional",
            "portfolio_notional",
        ],
        0.0,
    )

    portfolio_risk = find_value(
        report,
        [
            "portfolio_risk",
            "risk",
        ],
        0.0,
    )

    realized_pnl = find_value(
        report,
        [
            "realized_pnl",
            "realized_pnl_value",
        ],
        0.0,
    )

    unrealized_pnl = find_value(
        report,
        [
            "unrealized_pnl",
            "unrealized_pnl_value",
        ],
        0.0,
    )

    total_pnl = find_value(
        report,
        [
            "total_pnl",
            "pnl",
            "total_pnl_value",
        ],
        0.0,
    )

    current_drawdown = find_value(
        report,
        [
            "current_drawdown",
            "drawdown",
        ],
        0.0,
    )

    maximum_drawdown = find_value(
        report,
        [
            "maximum_drawdown",
            "max_drawdown",
        ],
        0.0,
    )

    concentration = find_value(
        report,
        [
            "max_concentration",
            "maximum_concentration",
            "asset_concentration",
        ],
        0.0,
    )

    circuit_breaker = find_value(
        report,
        [
            "circuit_breaker",
            "circuit_breaker_state",
        ],
        "UNKNOWN",
    )

    return {
        "snapshot_id": snapshot_id,
        "timestamp": timestamp,
        "positions": positions,
        "open_positions": open_positions,
        "closed_positions": closed_positions,
        "analytical_notional": notional,
        "portfolio_risk": portfolio_risk,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": total_pnl,
        "current_drawdown": current_drawdown,
        "maximum_drawdown": maximum_drawdown,
        "max_concentration": concentration,
        "circuit_breaker": circuit_breaker,
    }


def validate_snapshot(snapshot: dict[str, Any]) -> tuple[bool, list[str]]:
    missing = []

    if not snapshot.get("snapshot_id"):
        missing.append("snapshot_id")

    if not snapshot.get("timestamp"):
        missing.append("timestamp")

    return len(missing) == 0, missing


def main() -> None:
    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER LIFECYCLE STATE "
        "CAPTURE FROM ISOLATED LAUNCH v0.2"
    )
    print("=" * 100)

    print()
    print("=" * 100)
    print("OBJECTIVE")
    print("=" * 100)
    print(
        "Consume ONLY genuine PAPER lifecycle/state reports "
        "produced by the isolated LIVE launch."
    )
    print("No snapshot is manufactured from Fusion signals.")
    print("Production DB remains untouched.")
    print("No real order is created or submitted.")

    print()
    print("=" * 100)
    print("SAFETY POLICY")
    print("=" * 100)
    print("Production DB writes       : FORBIDDEN")
    print("Production engine run     : NO")
    print("Historical repair         : NONE")
    print("Direction inference       : NONE")
    print("Score reconstruction      : NONE")
    print("Synthetic snapshot        : FORBIDDEN")
    print("Live data injection       : NONE")
    print("Order execution           : NONE")
    print("PAPER EXECUTION           : ANALYTICAL ONLY")

    if not PRODUCTION_DB.exists():
        print()
        print("ERROR: Production DB not found:")
        print(PRODUCTION_DB)
        sys.exit(1)

    baseline_size = file_size(PRODUCTION_DB)
    baseline_sha256 = sha256_file(PRODUCTION_DB)

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)
    print(f"Size   : {baseline_size}")
    print(f"SHA256 : {baseline_sha256}")

    launches = discover_launches()

    print()
    print("=" * 100)
    print("ISOLATED LIVE LAUNCH DISCOVERY")
    print("=" * 100)

    if not launches:
        print("No isolated LIVE launch directories discovered.")
        sys.exit(0)

    for index, launch in enumerate(launches, 1):
        print(f"{index} | {launch}")

    launch_dir = launches[0]

    print()
    print("=" * 100)
    print("SELECTED LAUNCH")
    print("=" * 100)
    print(f"Directory : {launch_dir}")

    isolated_db = launch_dir / "arunda_live_capture.db"

    print(f"Isolated DB : {isolated_db}")

    if not isolated_db.exists():
        print("ISOLATED DB : MISSING")
        sys.exit(1)

    print()
    print("=" * 100)
    print("PAPER REPORT DISCOVERY")
    print("=" * 100)

    reports = discover_reports(launch_dir)

    found_count = 0

    for name, path in reports.items():
        if path is None:
            print(f"MISSING  | {name}")
        else:
            print(f"FOUND    | {name}")
            found_count += 1

    if found_count == 0:
        print()
        print("=" * 100)
        print("RESULT")
        print("=" * 100)
        print("NO_PAPER_LIFECYCLE_STATE_REPORT")
        print()
        print(
            "The isolated launch produced a valid runtime database, "
            "but no genuine PAPER lifecycle/state report was found."
        )
        print()
        print(
            "The script REFUSES to manufacture a portfolio snapshot "
            "from fusion_signals."
        )
        print()
        print("NEXT ACTION:")
        print(
            "Run the verified PAPER lifecycle/state pipeline against "
            "this isolated launch."
        )

        after_size = file_size(PRODUCTION_DB)
        after_sha256 = sha256_file(PRODUCTION_DB)

        print()
        print("=" * 100)
        print("PRODUCTION DATABASE INVARIANT")
        print("=" * 100)
        print(f"Before size  : {baseline_size}")
        print(f"After size   : {after_size}")
        print(f"Before SHA256: {baseline_sha256}")
        print(f"After SHA256 : {after_sha256}")

        invariant = (
            baseline_size == after_size
            and baseline_sha256 == after_sha256
        )

        print(
            "PRODUCTION DB INVARIANT : "
            + ("PASS" if invariant else "FAIL")
        )

        report = {
            "frontier": (
                "LIVE_PAPER_LIFECYCLE_STATE_CAPTURE_FROM_ISOLATED_LAUNCH_v0.2"
            ),
            "launch_directory": str(launch_dir),
            "isolated_db": str(isolated_db),
            "paper_reports_found": found_count,
            "new_portfolio_snapshot": False,
            "temporal_evidence": "INSUFFICIENT_DATA",
            "reason": "NO_PAPER_LIFECYCLE_STATE_REPORT",
            "production_db": {
                "before_size": baseline_size,
                "after_size": after_size,
                "before_sha256": baseline_sha256,
                "after_sha256": after_sha256,
                "invariant": invariant,
            },
            "safety": {
                "production_db_writes": "NONE",
                "real_order_execution": "NONE",
                "synthetic_snapshot": "NONE",
                "paper_execution": "ANALYTICAL_ONLY",
            },
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

        sys.exit(0)

    selected_report = None

    for name in [
        "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_REPORT.json",
        "LIVE_PAPER_POSITION_MONITORING_DYNAMIC_EXIT_MTM_REPORT.json",
        "LIVE_PAPER_TRADE_OUTCOME_PNL_RECONCILIATION_REPORT.json",
        "LIVE_PAPER_TRADE_SIMULATION_POSITION_LIFECYCLE_REPORT.json",
    ]:
        if reports.get(name):
            selected_report = reports[name]
            break

    if selected_report is None:
        print("No usable PAPER state report found.")
        sys.exit(0)

    report_data = load_json(selected_report)

    if report_data is None:
        print("REPORT JSON : INVALID")
        sys.exit(1)

    snapshot = extract_snapshot(report_data)

    valid, missing = validate_snapshot(snapshot)

    print()
    print("=" * 100)
    print("PAPER SNAPSHOT EXTRACTION")
    print("=" * 100)

    print(f"Source report       : {selected_report}")
    print(f"Snapshot ID         : {snapshot['snapshot_id']}")
    print(f"Timestamp           : {snapshot['timestamp']}")
    print(f"Positions           : {snapshot['positions']}")
    print(f"Open positions      : {snapshot['open_positions']}")
    print(f"Closed positions    : {snapshot['closed_positions']}")
    print(f"Analytical notional : {snapshot['analytical_notional']}")
    print(f"Portfolio risk      : {snapshot['portfolio_risk']}")
    print(f"Realized P&L        : {snapshot['realized_pnl']}")
    print(f"Unrealized P&L      : {snapshot['unrealized_pnl']}")
    print(f"Total P&L           : {snapshot['total_pnl']}")
    print(f"Current drawdown    : {snapshot['current_drawdown']}")
    print(f"Maximum drawdown    : {snapshot['maximum_drawdown']}")
    print(f"Max concentration   : {snapshot['max_concentration']}")
    print(f"Circuit breaker     : {snapshot['circuit_breaker']}")

    print()
    print("=" * 100)
    print("SNAPSHOT VALIDITY")
    print("=" * 100)

    if valid:
        print("IDENTITY : PASS")
        print("TIMESTAMP: PASS")
    else:
        print("IDENTITY : FAIL")
        print(f"MISSING  : {missing}")

    after_size = file_size(PRODUCTION_DB)
    after_sha256 = sha256_file(PRODUCTION_DB)

    invariant = (
        baseline_size == after_size
        and baseline_sha256 == after_sha256
    )

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)
    print(f"Before size  : {baseline_size}")
    print(f"After size   : {after_size}")
    print(f"Before SHA256: {baseline_sha256}")
    print(f"After SHA256 : {after_sha256}")
    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if invariant else "FAIL")
    )

    final_verdict = (
        "PASS"
        if valid and invariant
        else "INSUFFICIENT_DATA"
    )

    result = {
        "frontier": (
            "LIVE_PAPER_LIFECYCLE_STATE_CAPTURE_FROM_ISOLATED_LAUNCH_v0.2"
        ),
        "source_report": str(selected_report),
        "snapshot": snapshot,
        "snapshot_valid": valid,
        "missing_fields": missing,
        "new_portfolio_snapshot": valid,
        "temporal_evidence": (
            "AVAILABLE" if valid else "INSUFFICIENT_DATA"
        ),
        "production_db_invariant": {
            "before_size": baseline_size,
            "after_size": after_size,
            "before_sha256": baseline_sha256,
            "after_sha256": after_sha256,
            "pass": invariant,
        },
        "final_verdict": final_verdict,
        "safety": {
            "production_db_writes": "NONE",
            "real_order_execution": "NONE",
            "synthetic_snapshot": "NONE",
            "paper_execution": "ANALYTICAL_ONLY",
        },
    }

    output = launch_dir / OUTPUT_REPORT_NAME

    with output.open("w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)
    print(f"NEW_PORTFOLIO_SNAPSHOT : {'PASS' if valid else 'NOT_AVAILABLE'}")
    print(f"PRODUCTION_ISOLATION   : {'PASS' if invariant else 'FAIL'}")
    print(f"FRONTIER VERDICT       : {final_verdict}")
    print()
    print(f"Runtime report : {output}")


if __name__ == "__main__":
    main()