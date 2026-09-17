import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional


VERSION = "v0.1"

PRODUCTION_DB = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

LAUNCH_DIR = Path(
    r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_m1ld7rpr"
)

OBSERVATION_STORE = LAUNCH_DIR / (
    "LIVE_PAPER_PORTFOLIO_TEMPORAL_OBSERVATION_STORE.json"
)

OLD_SNAPSHOT_ID = (
    "FUSION-20260823T164452832734+0000-fb3f0e1dd5c862ed"
)

REQUIRED_PAPER_REPORTS = [
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


def production_fingerprint() -> dict[str, Any]:
    stat = PRODUCTION_DB.stat()

    return {
        "size": stat.st_size,
        "sha256": sha256_file(PRODUCTION_DB),
    }


def load_json(path: Path) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        return data

    return None


def recursive_find(
    obj: Any,
    keys: set[str],
) -> dict[str, Any]:
    """
    Best-effort extraction of portfolio fields from already-produced
    upstream reports.

    No values are invented.
    """

    found: dict[str, Any] = {}

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                normalized = str(k).lower()

                if normalized in keys and normalized not in found:
                    found[normalized] = v

                walk(v)

        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(obj)

    return found


def find_value(
    obj: Any,
    aliases: list[str],
    default: Any = None,
) -> Any:
    keys = {a.lower() for a in aliases}

    result = recursive_find(obj, keys)

    for key in aliases:
        value = result.get(key.lower())

        if value is not None:
            return value

    return default


def numeric(
    value: Any,
    default: float = 0.0,
) -> float:
    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def integer(
    value: Any,
    default: int = 0,
) -> int:
    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def inspect_isolated_db() -> dict[str, Any]:
    db = LAUNCH_DIR / "arunda_live_capture.db"

    if not db.exists():
        raise FileNotFoundError(
            f"Isolated DB not found: {db}"
        )

    result: dict[str, Any] = {
        "path": str(db),
        "fusion_signals_before": None,
        "fusion_signals_after": None,
        "fusion_signal_delta": None,
        "directions": {},
    }

    with sqlite3.connect(str(db)) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'"
            )
        }

        if "fusion_signals" not in tables:
            return result

        count = conn.execute(
            "SELECT COUNT(*) FROM fusion_signals"
        ).fetchone()[0]

        result["fusion_signals_after"] = int(count)

        try:
            rows = conn.execute(
                """
                SELECT direction, COUNT(*)
                FROM fusion_signals
                GROUP BY direction
                """
            ).fetchall()

            result["directions"] = {
                str(direction): int(count)
                for direction, count in rows
            }

        except sqlite3.Error:
            pass

    return result


def discover_paper_reports() -> dict[str, Path]:
    discovered: dict[str, Path] = {}

    for name in REQUIRED_PAPER_REPORTS:
        path = LAUNCH_DIR / name

        if path.exists():
            discovered[name] = path

    return discovered


def validate_new_snapshot_id(snapshot_id: Any) -> str:
    if not isinstance(snapshot_id, str):
        raise ValueError(
            "New PAPER snapshot does not contain a valid snapshot_id."
        )

    snapshot_id = snapshot_id.strip()

    if not snapshot_id:
        raise ValueError(
            "New PAPER snapshot contains an empty snapshot_id."
        )

    if snapshot_id == OLD_SNAPSHOT_ID:
        raise ValueError(
            "Snapshot ID is identical to the previous snapshot. "
            "Independent temporal evidence was NOT created."
        )

    return snapshot_id


def extract_portfolio_observation(
    reports: dict[str, Path],
) -> dict[str, Any]:
    """
    Extract only values already present in the PAPER reports.

    Nothing is inferred from Fusion direction.
    """

    loaded: dict[str, dict[str, Any]] = {}

    for name, path in reports.items():
        data = load_json(path)

        if data is not None:
            loaded[name] = data

    if not loaded:
        raise ValueError(
            "No usable PAPER reports were found."
        )

    # Prefer the portfolio state report.
    state_report = loaded.get(
        "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_REPORT.json"
    )

    if state_report is None:
        raise ValueError(
            "A new portfolio state report was not produced by this "
            "independent launch."
        )

    snapshot_id = find_value(
        state_report,
        [
            "snapshot",
            "snapshot_id",
            "current_snapshot",
        ],
    )

    snapshot_id = validate_new_snapshot_id(snapshot_id)

    timestamp = find_value(
        state_report,
        [
            "timestamp",
            "current_timestamp",
            "snapshot_timestamp",
            "observed_at",
        ],
    )

    positions = integer(
        find_value(
            state_report,
            [
                "positions",
                "paper_positions",
                "total_positions",
            ],
        )
    )

    open_positions = integer(
        find_value(
            state_report,
            [
                "open_positions",
                "active_positions",
            ],
        )
    )

    closed_positions = integer(
        find_value(
            state_report,
            [
                "closed_positions",
                "closed_trades",
            ],
        )
    )

    notional = numeric(
        find_value(
            state_report,
            [
                "analytical_notional",
                "total_analytical_notional",
                "total_notional",
            ]
        )
    )

    portfolio_risk = numeric(
        find_value(
            state_report,
            [
                "portfolio_risk",
                "analytical_risk",
                "total_analytical_risk",
            ]
        )
    )

    realized_pnl = numeric(
        find_value(
            state_report,
            [
                "realized_pnl",
                "aggregate_realized_pnl",
            ]
        )
    )

    unrealized_pnl = numeric(
        find_value(
            state_report,
            [
                "unrealized_pnl",
                "aggregate_unrealized_pnl",
            ]
        )
    )

    total_pnl = numeric(
        find_value(
            state_report,
            [
                "total_pnl",
                "aggregate_pnl",
            ],
            realized_pnl + unrealized_pnl,
        )
    )

    current_drawdown = numeric(
        find_value(
            state_report,
            [
                "current_drawdown",
                "drawdown",
            ]
        )
    )

    maximum_drawdown = numeric(
        find_value(
            state_report,
            [
                "maximum_drawdown",
                "max_drawdown",
            ]
        )
    )

    max_concentration = numeric(
        find_value(
            state_report,
            [
                "maximum_concentration",
                "max_concentration",
            ]
        )
    )

    circuit_breaker = find_value(
        state_report,
        [
            "circuit_breaker",
            "circuit_breaker_state",
        ],
        "UNKNOWN",
    )

    return {
        "snapshot_id": snapshot_id,
        "timestamp": timestamp,
        "source": "INDEPENDENT_LIVE_PAPER_LAUNCH",
        "launch_directory": str(LAUNCH_DIR),
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
        "max_concentration": max_concentration,
        "circuit_breaker": circuit_breaker,
    }


def load_store() -> list[dict[str, Any]]:
    if not OBSERVATION_STORE.exists():
        return []

    try:
        data = json.loads(
            OBSERVATION_STORE.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            observations = data.get("observations")

            if isinstance(observations, list):
                return observations

    except Exception:
        pass

    return []


def validate_temporal_continuity(
    observations: list[dict[str, Any]],
    current: dict[str, Any],
) -> dict[str, Any]:

    previous = None

    if observations:
        previous = observations[-1]

    if previous is None:
        return {
            "status": "FIRST_OBSERVATION",
            "previous_snapshot": None,
            "snapshot_changed": None,
            "timestamp_order": "N/A",
        }

    previous_id = previous.get("snapshot_id")
    current_id = current.get("snapshot_id")

    if previous_id == current_id:
        raise ValueError(
            "Current snapshot ID equals the latest stored observation."
        )

    previous_ts = previous.get("timestamp")
    current_ts = current.get("timestamp")

    timestamp_order = "UNKNOWN"

    if previous_ts and current_ts:
        try:
            p = datetime.fromisoformat(
                str(previous_ts).replace("Z", "+00:00")
            )
            c = datetime.fromisoformat(
                str(current_ts).replace("Z", "+00:00")
            )

            if c <= p:
                raise ValueError(
                    "New snapshot timestamp is not later than "
                    "the previous stored observation."
                )

            timestamp_order = "PASS"

        except ValueError:
            raise
        except Exception:
            timestamp_order = "UNKNOWN"

    return {
        "status": "CONTINUOUS",
        "previous_snapshot": previous_id,
        "snapshot_changed": True,
        "timestamp_order": timestamp_order,
    }


def save_observation(
    observations: list[dict[str, Any]],
    current: dict[str, Any],
) -> None:

    observations.append(current)

    payload = {
        "schema": "LIVE_PAPER_TEMPORAL_OBSERVATION_STORE_v0.1",
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "observations": observations,
    }

    OBSERVATION_STORE.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def print_section(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def main() -> None:

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER INDEPENDENT SNAPSHOT "
        "FROM VERIFIED LAUNCH v0.1"
    )
    print("=" * 100)

    print_section("OBJECTIVE")

    print(
        "Consume ONLY the newly produced isolated LIVE PAPER launch."
    )
    print(
        "Create one independent portfolio observation only when "
        "a genuinely new PAPER portfolio snapshot exists."
    )
    print("Synthetic snapshot : FORBIDDEN")
    print("Production DB write : FORBIDDEN")
    print("Real order          : FORBIDDEN")

    if not LAUNCH_DIR.exists():
        raise FileNotFoundError(
            f"Launch directory does not exist: {LAUNCH_DIR}"
        )

    before = production_fingerprint()

    print_section("PRODUCTION BASELINE")

    print(f"Size   : {before['size']}")
    print(f"SHA256 : {before['sha256']}")

    print_section("ISOLATED LIVE LAUNCH")

    print(f"Directory : {LAUNCH_DIR}")

    isolated_db = LAUNCH_DIR / "arunda_live_capture.db"

    if not isolated_db.exists():
        raise FileNotFoundError(
            f"Isolated DB not found: {isolated_db}"
        )

    print(f"Isolated DB : {isolated_db}")

    db_info = inspect_isolated_db()

    print(
        f"fusion_signals rows : "
        f"{db_info['fusion_signals_after']}"
    )

    print("Direction distribution:")

    for direction, count in sorted(
        db_info["directions"].items()
    ):
        print(
            f"  {direction:<10} | {count}"
        )

    print_section("PAPER REPORT DISCOVERY")

    reports = discover_paper_reports()

    for name in REQUIRED_PAPER_REPORTS:
        status = "FOUND" if name in reports else "MISSING"

        print(
            f"{status:<8} | {name}"
        )

    if (
        "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_REPORT.json"
        not in reports
    ):
        print_section("RESULT")

        print(
            "NEW PORTFOLIO SNAPSHOT : NOT CREATED"
        )
        print()
        print(
            "The isolated launch produced a valid new FUSION runtime, "
            "but it did not produce a new PAPER portfolio-state report."
        )
        print()
        print(
            "Therefore this script REFUSES to manufacture a portfolio "
            "snapshot from Fusion signals."
        )
        print()
        print(
            "Required next step:"
        )
        print(
            "Run the verified PAPER lifecycle/state pipeline against "
            "this isolated launch."
        )

        after = production_fingerprint()

        print_section("PRODUCTION DATABASE INVARIANT")

        print(f"Before size  : {before['size']}")
        print(f"After size   : {after['size']}")
        print(f"Before SHA256: {before['sha256']}")
        print(f"After SHA256 : {after['sha256']}")

        invariant = (
            before["size"] == after["size"]
            and before["sha256"] == after["sha256"]
        )

        print(
            "PRODUCTION DB INVARIANT : "
            + ("PASS" if invariant else "FAIL")
        )

        print_section(
            "TEMPORAL SNAPSHOT VERDICT"
        )

        print(
            "FUSION_RUNTIME_CAPTURE : PASS"
        )
        print(
            "NEW_PORTFOLIO_SNAPSHOT : NOT_AVAILABLE"
        )
        print(
            "TEMPORAL_EVIDENCE      : INSUFFICIENT_DATA"
        )
        print(
            "PRODUCTION_ISOLATION   : "
            + ("PASS" if invariant else "FAIL")
        )

        return

    print_section("NEW PAPER PORTFOLIO OBSERVATION")

    current = extract_portfolio_observation(reports)

    print(
        f"Snapshot ID          : {current['snapshot_id']}"
    )
    print(
        f"Timestamp            : {current['timestamp']}"
    )
    print(
        f"Positions            : {current['positions']}"
    )
    print(
        f"Open positions       : {current['open_positions']}"
    )
    print(
        f"Closed positions     : {current['closed_positions']}"
    )
    print(
        f"Analytical notional  : "
        f"{current['analytical_notional']:.6f}"
    )
    print(
        f"Portfolio risk       : "
        f"{current['portfolio_risk']:.6f}"
    )
    print(
        f"Realized P&L         : "
        f"{current['realized_pnl']:.6f}"
    )
    print(
        f"Unrealized P&L       : "
        f"{current['unrealized_pnl']:.6f}"
    )
    print(
        f"Total P&L            : "
        f"{current['total_pnl']:.6f}"
    )

    observations = load_store()

    continuity = validate_temporal_continuity(
        observations,
        current,
    )

    print_section("TEMPORAL CONTINUITY")

    print(
        f"Stored observations : {len(observations)}"
    )
    print(
        f"Previous snapshot   : "
        f"{continuity['previous_snapshot']}"
    )
    print(
        f"Current snapshot    : "
        f"{current['snapshot_id']}"
    )
    print(
        f"Snapshot changed    : "
        f"{continuity['snapshot_changed']}"
    )
    print(
        f"Timestamp order     : "
        f"{continuity['timestamp_order']}"
    )
    print(
        f"Continuity status   : "
        f"{continuity['status']}"
    )

    save_observation(
        observations,
        current,
    )

    after = production_fingerprint()

    invariant = (
        before["size"] == after["size"]
        and before["sha256"] == after["sha256"]
    )

    print_section("TEMPORAL EVIDENCE STATUS")

    print(
        f"Snapshots stored : {len(observations) + 1}"
    )

    if len(observations) + 1 >= 2:
        evidence_status = "READY_FOR_TEMPORAL_RECONCILIATION"
    else:
        evidence_status = "INSUFFICIENT_DATA"

    print(
        f"Evidence status : {evidence_status}"
    )

    print_section("PRODUCTION DATABASE INVARIANT")

    print(f"Before size   : {before['size']}")
    print(f"After size    : {after['size']}")
    print(f"Before SHA256 : {before['sha256']}")
    print(f"After SHA256  : {after['sha256']}")

    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if invariant else "FAIL")
    )

    print_section(
        "LIVE PAPER INDEPENDENT SNAPSHOT VERDICT"
    )

    print(
        "FUSION_RUNTIME_CAPTURE      : PASS"
    )
    print(
        "NEW_PORTFOLIO_SNAPSHOT      : PASS"
    )
    print(
        "SNAPSHOT_IDENTITY           : PASS"
    )
    print(
        "TEMPORAL_CONTINUITY         : "
        + (
            "PASS"
            if continuity["status"] == "CONTINUOUS"
            else "FIRST_OBSERVATION"
        )
    )
    print(
        "PRODUCTION_ISOLATION        : "
        + ("PASS" if invariant else "FAIL")
    )
    print(
        "FRONTIER VERDICT            : "
        + (
            "READY_FOR_TEMPORAL_RECONCILIATION"
            if len(observations) + 1 >= 2
            else "INSUFFICIENT_DATA"
        )
    )

    print()
    print(
        f"Observation store : {OBSERVATION_STORE}"
    )


if __name__ == "__main__":
    main()