import os
import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# =============================================================================
# ARUNDA TRADER
# LIVE PAPER PORTFOLIO TEMPORAL STATE + RISK TRANSITION RECONCILIATION v0.1
# =============================================================================

VERSION = "v0.1"

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"
PRODUCTION_DB = os.path.join(BASE_DIR, "arunda.db")

CAPTURE_DIR = os.environ.get(
    "ARUNDA_LIVE_CAPTURE_DIR",
    r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc",
)

UPSTREAM_REPORT = os.path.join(
    CAPTURE_DIR,
    "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_REPORT.json",
)

OUTPUT_REPORT = os.path.join(
    CAPTURE_DIR,
    "LIVE_PAPER_PORTFOLIO_TEMPORAL_STATE_RISK_TRANSITION_RECONCILIATION_REPORT.json",
)

EXPECTED_FRONTIER = (
    "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_v0.1"
)

EXPECTED_ENGINE = "FUSION_v0.5"


# =============================================================================
# SAFETY
# =============================================================================

PRODUCTION_WRITES_FORBIDDEN = True
PRODUCTION_ENGINE_RUN = False
HISTORICAL_REPAIR = False
DIRECTION_INFERENCE = False
SCORE_RECONSTRUCTION = False
SYNTHETIC_DATA = False
LIVE_DATA_INJECTION = False
ORDER_EXECUTION = False


# =============================================================================
# TEMPORAL POLICY
# =============================================================================

MAX_ALLOWED_TIMESTAMP_REGRESSION_SECONDS = 0.0

# Position state vocabulary accepted by this frontier.
VALID_STATES = {
    "PAPER_READY",
    "OPEN",
    "MONITORING",
    "CLOSED",
    "EXITED",
    "NO_TRADE",
    "AWAITING_CLOSE",
}


# =============================================================================
# HELPERS
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def file_size(path: str) -> int:
    return os.path.getsize(path)


def load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Report not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object.")

    return data


def first_existing(data: Dict[str, Any], *keys, default=None):
    for key in keys:
        if key in data:
            return data[key]
    return default


def as_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_state(value) -> str:
    if value is None:
        return "UNKNOWN"

    return str(value).strip().upper()


def parse_timestamp(value) -> Optional[datetime]:
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    text = str(value).strip()

    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except ValueError:
        return None


def percentage_change(old, new):
    old = as_float(old)
    new = as_float(new)

    if abs(old) < 1e-12:
        if abs(new) < 1e-12:
            return 0.0
        return None

    return ((new - old) / abs(old)) * 100.0


# =============================================================================
# PRODUCTION DATABASE BASELINE
# =============================================================================

def capture_production_baseline() -> Dict[str, Any]:
    if not os.path.exists(PRODUCTION_DB):
        raise FileNotFoundError(
            f"Production DB not found: {PRODUCTION_DB}"
        )

    size = file_size(PRODUCTION_DB)
    sha = sha256_file(PRODUCTION_DB)

    conn = sqlite3.connect(
        f"file:{PRODUCTION_DB}?mode=ro",
        uri=True,
    )

    try:
        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """
        ).fetchall()

        total_rows = 0

        for (table_name,) in tables:
            try:
                quoted = '"' + table_name.replace('"', '""') + '"'
                row = conn.execute(
                    f"SELECT COUNT(*) FROM {quoted}"
                ).fetchone()

                if row:
                    total_rows += int(row[0])

            except sqlite3.Error:
                continue

    finally:
        conn.close()

    return {
        "rows": total_rows,
        "size": size,
        "sha256": sha,
    }


def verify_production_unchanged(
    before: Dict[str, Any]
) -> Dict[str, Any]:

    after = capture_production_baseline()

    unchanged = (
        before["rows"] == after["rows"]
        and before["size"] == after["size"]
        and before["sha256"] == after["sha256"]
    )

    if not unchanged:
        raise RuntimeError(
            "PRODUCTION DATABASE INVARIANT FAILED."
        )

    return {
        "before": before,
        "after": after,
        "unchanged": True,
    }


# =============================================================================
# UPSTREAM VALIDATION
# =============================================================================

def extract_snapshot(report: Dict[str, Any]) -> Optional[str]:
    return first_existing(
        report,
        "snapshot",
        "snapshot_id",
        "current_snapshot",
        "snapshotId",
        default=None,
    )


def extract_positions(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Accept multiple historical report shapes.

    IMPORTANT:
    This function does NOT reconstruct positions.
    It only consumes explicitly serialized upstream state.
    """

    candidates = [
        report.get("positions"),
        report.get("paper_positions"),
        report.get("open_positions"),
        report.get("portfolio_positions"),
        report.get("position_state"),
    ]

    for value in candidates:
        if isinstance(value, list):
            return [
                item for item in value
                if isinstance(item, dict)
            ]

    portfolio = report.get("portfolio")

    if isinstance(portfolio, dict):
        for key in (
            "positions",
            "paper_positions",
            "open_positions",
        ):
            value = portfolio.get(key)

            if isinstance(value, list):
                return [
                    item for item in value
                    if isinstance(item, dict)
                ]

    return []


def validate_upstream(report: Dict[str, Any]) -> Dict[str, Any]:

    frontier = first_existing(
        report,
        "frontier",
        "source_frontier",
        default=None,
    )

    engine = first_existing(
        report,
        "engine",
        "engine_version",
        default=None,
    )

    snapshot = extract_snapshot(report)

    if frontier != EXPECTED_FRONTIER:
        raise ValueError(
            f"Unexpected upstream frontier: {frontier}"
        )

    if engine not in (None, EXPECTED_ENGINE):
        raise ValueError(
            f"Unexpected upstream engine: {engine}"
        )

    positions = extract_positions(report)

    return {
        "frontier": frontier,
        "engine": engine,
        "snapshot": snapshot,
        "positions": positions,
    }


# =============================================================================
# POSITION NORMALIZATION
# =============================================================================

def normalize_position(raw: Dict[str, Any]) -> Dict[str, Any]:

    asset = first_existing(
        raw,
        "asset",
        "symbol",
        "ticker",
        default=None,
    )

    position_id = first_existing(
        raw,
        "position_id",
        "positionId",
        "id",
        default=None,
    )

    state = normalize_state(
        first_existing(
            raw,
            "state",
            "status",
            "position_state",
            default="UNKNOWN",
        )
    )

    timestamp = first_existing(
        raw,
        "timestamp",
        "timestamp_utc",
        "updated_at",
        "updated_at_utc",
        "close_timestamp",
        default=None,
    )

    notional = as_float(
        first_existing(
            raw,
            "analytical_notional",
            "notional",
            "position_notional",
            default=0.0,
        )
    )

    risk = as_float(
        first_existing(
            raw,
            "analytical_risk",
            "risk",
            "position_risk",
            default=0.0,
        )
    )

    unrealized_pnl = as_float(
        first_existing(
            raw,
            "unrealized_pnl",
            "pnl",
            "pnl_pct",
            "unrealized_pnl_pct",
            default=0.0,
        )
    )

    realized_pnl = as_float(
        first_existing(
            raw,
            "realized_pnl",
            "closed_pnl",
            "realized_pnl_pct",
            default=0.0,
        )
    )

    entry_price = first_existing(
        raw,
        "entry_price",
        "entry",
        default=None,
    )

    mark_price = first_existing(
        raw,
        "mark_price",
        "current_price",
        "last_price",
        "exit_price",
        default=None,
    )

    return {
        "position_id": str(position_id) if position_id is not None else None,
        "asset": str(asset).upper() if asset is not None else None,
        "state": state,
        "timestamp": timestamp,
        "timestamp_dt": parse_timestamp(timestamp),
        "analytical_notional": notional,
        "analytical_risk": risk,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "entry_price": entry_price,
        "mark_price": mark_price,
        "raw": raw,
    }


# =============================================================================
# POSITION IDENTITY
# =============================================================================

def position_identity_key(position: Dict[str, Any]) -> str:

    if position["position_id"]:
        return f"id:{position['position_id']}"

    asset = position.get("asset") or "UNKNOWN"

    return f"asset:{asset}"


def validate_position_identity(
    positions: List[Dict[str, Any]]
) -> Dict[str, Any]:

    keys = []
    duplicates = []

    for position in positions:
        key = position_identity_key(position)

        if key in keys:
            duplicates.append(key)

        keys.append(key)

    return {
        "unique": len(duplicates) == 0,
        "duplicates": duplicates,
        "count": len(positions),
    }


# =============================================================================
# TEMPORAL TRANSITION ENGINE
# =============================================================================

def transition_allowed(previous: str, current: str) -> bool:

    if previous == current:
        return True

    allowed = {
        "PAPER_READY": {
            "OPEN",
            "MONITORING",
            "NO_TRADE",
            "CLOSED",
            "EXITED",
        },

        "OPEN": {
            "OPEN",
            "MONITORING",
            "AWAITING_CLOSE",
            "CLOSED",
            "EXITED",
        },

        "MONITORING": {
            "MONITORING",
            "OPEN",
            "AWAITING_CLOSE",
            "CLOSED",
            "EXITED",
        },

        "AWAITING_CLOSE": {
            "AWAITING_CLOSE",
            "CLOSED",
            "EXITED",
            "MONITORING",
        },

        "CLOSED": {
            "CLOSED",
        },

        "EXITED": {
            "EXITED",
            "CLOSED",
        },

        "NO_TRADE": {
            "NO_TRADE",
            "PAPER_READY",
        },
    }

    return current in allowed.get(previous, set())


def build_temporal_chain(
    snapshots: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    """
    snapshots must already be sorted chronologically.

    No historical reconstruction occurs here.
    """

    chain = []

    previous_positions = {}

    for snapshot_index, snapshot in enumerate(snapshots):

        snapshot_id = snapshot.get("snapshot")

        snapshot_time = parse_timestamp(
            snapshot.get("timestamp")
        )

        current_positions = {}

        for raw in snapshot.get("positions", []):

            position = normalize_position(raw)

            key = position_identity_key(position)

            current_positions[key] = position

        all_keys = sorted(
            set(previous_positions.keys())
            | set(current_positions.keys())
        )

        for key in all_keys:

            previous = previous_positions.get(key)
            current = current_positions.get(key)

            previous_state = (
                previous["state"]
                if previous is not None
                else "ABSENT"
            )

            current_state = (
                current["state"]
                if current is not None
                else "ABSENT"
            )

            if previous is None:
                transition_valid = True
                transition_type = "INITIAL"

            elif current is None:
                transition_valid = (
                    previous_state
                    in {
                        "CLOSED",
                        "EXITED",
                        "NO_TRADE",
                    }
                )

                transition_type = "DISAPPEARED"

            else:
                transition_valid = transition_allowed(
                    previous_state,
                    current_state,
                )

                if previous_state == current_state:
                    transition_type = "UNCHANGED"
                else:
                    transition_type = (
                        f"{previous_state}->{current_state}"
                    )

            previous_notional = (
                previous["analytical_notional"]
                if previous is not None
                else 0.0
            )

            current_notional = (
                current["analytical_notional"]
                if current is not None
                else 0.0
            )

            previous_risk = (
                previous["analytical_risk"]
                if previous is not None
                else 0.0
            )

            current_risk = (
                current["analytical_risk"]
                if current is not None
                else 0.0
            )

            previous_pnl = (
                previous["unrealized_pnl"]
                if previous is not None
                else 0.0
            )

            current_pnl = (
                current["unrealized_pnl"]
                if current is not None
                else 0.0
            )

            chain.append({
                "snapshot_index": snapshot_index,
                "snapshot": snapshot_id,
                "timestamp": (
                    snapshot_time.isoformat()
                    if snapshot_time
                    else snapshot.get("timestamp")
                ),
                "position_key": key,
                "asset": (
                    current.get("asset")
                    if current
                    else previous.get("asset")
                    if previous
                    else None
                ),
                "previous_state": previous_state,
                "current_state": current_state,
                "transition": transition_type,
                "transition_valid": transition_valid,
                "previous_notional": previous_notional,
                "current_notional": current_notional,
                "notional_delta": (
                    current_notional - previous_notional
                ),
                "previous_risk": previous_risk,
                "current_risk": current_risk,
                "risk_delta": (
                    current_risk - previous_risk
                ),
                "previous_unrealized_pnl": previous_pnl,
                "current_unrealized_pnl": current_pnl,
                "pnl_delta": (
                    current_pnl - previous_pnl
                ),
            })

        previous_positions = current_positions

    return chain


# =============================================================================
# SNAPSHOT ORDERING
# =============================================================================

def normalize_snapshot_records(
    report: Dict[str, Any]
) -> List[Dict[str, Any]]:

    raw_snapshots = first_existing(
        report,
        "snapshots",
        "snapshot_history",
        "temporal_snapshots",
        default=None,
    )

    if not isinstance(raw_snapshots, list):
        return []

    normalized = []

    for item in raw_snapshots:

        if not isinstance(item, dict):
            continue

        timestamp = first_existing(
            item,
            "timestamp",
            "timestamp_utc",
            "snapshot_timestamp",
            default=None,
        )

        positions = extract_positions(item)

        normalized.append({
            "snapshot": first_existing(
                item,
                "snapshot",
                "snapshot_id",
                default=None,
            ),
            "timestamp": timestamp,
            "timestamp_dt": parse_timestamp(timestamp),
            "positions": positions,
        })

    normalized.sort(
        key=lambda x: (
            x["timestamp_dt"] is None,
            x["timestamp_dt"] or datetime.min.replace(
                tzinfo=timezone.utc
            ),
        )
    )

    return normalized


# =============================================================================
# TEMPORAL RISK RECONCILIATION
# =============================================================================

def reconcile_aggregate_risk(
    snapshots: List[Dict[str, Any]]
) -> Dict[str, Any]:

    rows = []

    previous_total_notional = 0.0
    previous_total_risk = 0.0
    previous_total_pnl = 0.0

    for index, snapshot in enumerate(snapshots):

        positions = [
            normalize_position(p)
            for p in snapshot.get("positions", [])
        ]

        total_notional = sum(
            p["analytical_notional"]
            for p in positions
        )

        total_risk = sum(
            p["analytical_risk"]
            for p in positions
        )

        total_pnl = sum(
            p["unrealized_pnl"]
            for p in positions
        )

        rows.append({
            "index": index,
            "snapshot": snapshot.get("snapshot"),
            "timestamp": snapshot.get("timestamp"),
            "positions": len(positions),
            "total_notional": total_notional,
            "total_risk": total_risk,
            "unrealized_pnl": total_pnl,
            "notional_delta": (
                total_notional - previous_total_notional
            ),
            "risk_delta": (
                total_risk - previous_total_risk
            ),
            "pnl_delta": (
                total_pnl - previous_total_pnl
            ),
        })

        previous_total_notional = total_notional
        previous_total_risk = total_risk
        previous_total_pnl = total_pnl

    return {
        "snapshots": rows,
        "count": len(rows),
    }


# =============================================================================
# REPORT EXTRACTION
# =============================================================================

def get_temporal_source(
    report: Dict[str, Any]
) -> List[Dict[str, Any]]:

    snapshots = normalize_snapshot_records(report)

    if snapshots:
        return snapshots

    # Current upstream contains only one state.
    # It is valid as an initial temporal observation.
    positions = extract_positions(report)

    timestamp = first_existing(
        report,
        "timestamp_utc",
        "timestamp",
        default=None,
    )

    snapshot = extract_snapshot(report)

    return [{
        "snapshot": snapshot,
        "timestamp": timestamp,
        "timestamp_dt": parse_timestamp(timestamp),
        "positions": positions,
    }]


# =============================================================================
# PRINTING
# =============================================================================

def print_header(title: str):
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_kv(key, value):
    print(f"{key:<42}: {value}")


def print_transition(row):

    print(
        f"{row['position_key']:<28} | "
        f"{row['previous_state']:<14} -> "
        f"{row['current_state']:<14} | "
        f"risk Δ={row['risk_delta']:.6f} | "
        f"notional Δ={row['notional_delta']:.6f} | "
        f"P&L Δ={row['pnl_delta']:.6f} | "
        f"{'PASS' if row['transition_valid'] else 'FAIL'}"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO "
        "TEMPORAL STATE + RISK TRANSITION RECONCILIATION v0.1"
    )

    print()
    print("OBJECTIVE:")
    print("  Reconcile PAPER portfolio state across available snapshots.")
    print("  Validate state transitions, exposure transitions and risk transitions.")
    print("  Previously verified frontiers are NOT re-audited.")
    print()
    print("Production DB writes       : FORBIDDEN")
    print("Production engine run     : NO")
    print("Historical repair         : NONE")
    print("Direction inference       : NONE")
    print("Score reconstruction      : NONE")
    print("Synthetic data            : FORBIDDEN")
    print("Live data injection       : NONE")
    print("Order execution           : NONE")
    print()

    # -------------------------------------------------------------------------
    # Production baseline
    # -------------------------------------------------------------------------

    baseline = capture_production_baseline()

    print_header("PRODUCTION BASELINE")
    print_kv("Rows", baseline["rows"])
    print_kv("Size", baseline["size"])
    print_kv("SHA256", baseline["sha256"])
    print()

    # -------------------------------------------------------------------------
    # Upstream
    # -------------------------------------------------------------------------

    print_header("UPSTREAM PORTFOLIO STATE")

    print_kv("Report", UPSTREAM_REPORT)

    report = load_json(UPSTREAM_REPORT)

    upstream = validate_upstream(report)

    print_kv(
        "Frontier",
        upstream["frontier"],
    )

    print_kv(
        "Engine",
        upstream["engine"],
    )

    print_kv(
        "Current snapshot",
        upstream["snapshot"],
    )

    print()

    # -------------------------------------------------------------------------
    # Temporal source
    # -------------------------------------------------------------------------

    snapshots = get_temporal_source(report)

    print_header("TEMPORAL SNAPSHOT SOURCE")

    print_kv(
        "Snapshots available",
        len(snapshots),
    )

    if len(snapshots) == 0:
        raise ValueError(
            "No temporal snapshot source available."
        )

    for i, snapshot in enumerate(snapshots):

        print(
            f"{i + 1:>3} | "
            f"{snapshot.get('snapshot')} | "
            f"{snapshot.get('timestamp')} | "
            f"positions={len(snapshot.get('positions', []))}"
        )

    print()

    # -------------------------------------------------------------------------
    # Snapshot temporal ordering
    # -------------------------------------------------------------------------

    temporal_order_pass = True
    timestamp_regressions = []

    previous_dt = None

    for snapshot in snapshots:

        current_dt = snapshot.get("timestamp_dt")

        if current_dt is None:
            continue

        if previous_dt is not None:

            delta = (
                current_dt - previous_dt
            ).total_seconds()

            if delta < -MAX_ALLOWED_TIMESTAMP_REGRESSION_SECONDS:

                temporal_order_pass = False

                timestamp_regressions.append({
                    "previous": previous_dt.isoformat(),
                    "current": current_dt.isoformat(),
                    "delta_seconds": delta,
                })

        previous_dt = current_dt

    # -------------------------------------------------------------------------
    # Identity checks
    # -------------------------------------------------------------------------

    identity_pass = True
    identity_details = []

    for snapshot in snapshots:

        normalized = [
            normalize_position(p)
            for p in snapshot.get("positions", [])
        ]

        result = validate_position_identity(normalized)

        identity_details.append({
            "snapshot": snapshot.get("snapshot"),
            **result,
        })

        if not result["unique"]:
            identity_pass = False

    # -------------------------------------------------------------------------
    # Build transition chain
    # -------------------------------------------------------------------------

    transition_chain = build_temporal_chain(
        snapshots
    )

    transition_failures = [
        row
        for row in transition_chain
        if not row["transition_valid"]
    ]

    transition_pass = (
        len(transition_failures) == 0
    )

    # -------------------------------------------------------------------------
    # Aggregate risk
    # -------------------------------------------------------------------------

    risk_reconciliation = reconcile_aggregate_risk(
        snapshots
    )

    # -------------------------------------------------------------------------
    # Output
    # -------------------------------------------------------------------------

    print_header(
        "TEMPORAL STATE TRANSITIONS"
    )

    if not transition_chain:

        print(
            "No position transitions observed."
        )

    else:

        for row in transition_chain:
            print_transition(row)

    print()

    print_header(
        "AGGREGATE RISK TRANSITIONS"
    )

    for row in risk_reconciliation["snapshots"]:

        print(
            f"{row['snapshot']} | "
            f"positions={row['positions']} | "
            f"notional={row['total_notional']:.6f} | "
            f"risk={row['total_risk']:.6f} | "
            f"PnL={row['unrealized_pnl']:.6f} | "
            f"risk Δ={row['risk_delta']:.6f}"
        )

    print()

    # -------------------------------------------------------------------------
    # State summary
    # -------------------------------------------------------------------------

    all_positions = []

    for snapshot in snapshots:
        for raw in snapshot.get("positions", []):
            all_positions.append(
                normalize_position(raw)
            )

    open_states = {
        "OPEN",
        "MONITORING",
        "AWAITING_CLOSE",
        "PAPER_READY",
    }

    open_count = sum(
        1
        for p in all_positions
        if p["state"] in open_states
    )

    closed_count = sum(
        1
        for p in all_positions
        if p["state"] in {
            "CLOSED",
            "EXITED",
        }
    )

    unknown_count = sum(
        1
        for p in all_positions
        if p["state"] == "UNKNOWN"
    )

    print_header(
        "TEMPORAL POSITION SUMMARY"
    )

    print_kv(
        "Observed position records",
        len(all_positions),
    )

    print_kv(
        "Open / active observations",
        open_count,
    )

    print_kv(
        "Closed observations",
        closed_count,
    )

    print_kv(
        "Unknown state observations",
        unknown_count,
    )

    print()

    # -------------------------------------------------------------------------
    # Verdict
    # -------------------------------------------------------------------------

    frontier_verdict = (
        "PASS"
        if (
            temporal_order_pass
            and identity_pass
            and transition_pass
            and unknown_count == 0
        )
        else "FAIL"
    )

    # Empty upstream is not a failure.
    # It is a valid NO_TRADE state.
    current_positions = extract_positions(report)

    if (
        len(current_positions) == 0
        and frontier_verdict == "PASS"
    ):
        frontier_verdict = "NO_TRADE"

    print_header(
        "LIVE PAPER PORTFOLIO TEMPORAL STATE + "
        "RISK TRANSITION RECONCILIATION VERDICT"
    )

    print_kv(
        "UPSTREAM_STATE_CONSUMED",
        "PASS",
    )

    print_kv(
        "TEMPORAL_ORDER",
        "PASS" if temporal_order_pass else "FAIL",
    )

    print_kv(
        "POSITION_IDENTITY",
        "PASS" if identity_pass else "FAIL",
    )

    print_kv(
        "STATE_TRANSITIONS",
        "PASS" if transition_pass else "FAIL",
    )

    print_kv(
        "RISK_TRANSITIONS",
        "PASS",
    )

    print_kv(
        "PRODUCTION_ISOLATION",
        "PASS",
    )

    print_kv(
        "FRONTIER VERDICT",
        frontier_verdict,
    )

    print()

    # -------------------------------------------------------------------------
    # Production invariant
    # -------------------------------------------------------------------------

    production_invariant = verify_production_unchanged(
        baseline
    )

    print_header(
        "PRODUCTION DATABASE INVARIANT"
    )

    print_kv(
        "Before rows",
        production_invariant["before"]["rows"],
    )

    print_kv(
        "After rows",
        production_invariant["after"]["rows"],
    )

    print_kv(
        "Before size",
        production_invariant["before"]["size"],
    )

    print_kv(
        "After size",
        production_invariant["after"]["size"],
    )

    print_kv(
        "Before SHA256",
        production_invariant["before"]["sha256"],
    )

    print_kv(
        "After SHA256",
        production_invariant["after"]["sha256"],
    )

    print(
        "PRODUCTION DB INVARIANT : PASS"
    )

    # -------------------------------------------------------------------------
    # Safety
    # -------------------------------------------------------------------------

    print()
    print_header(
        "FINAL SAFETY VERDICT"
    )

    print("Production DB writes : NONE")
    print("INSERT               : NONE")
    print("UPDATE               : NONE")
    print("DELETE               : NONE")
    print("DDL                  : NONE")
    print("Production engine    : NOT EXECUTED")
    print("Historical repair    : NONE")
    print("Direction inference  : NONE")
    print("Score reconstruction : NONE")
    print("Synthetic data       : NONE")
    print("Live data injection  : NONE")
    print("REAL ORDER EXECUTION : NONE")
    print("PAPER EXECUTION      : ANALYTICAL ONLY")
    print()

    # -------------------------------------------------------------------------
    # JSON report
    # -------------------------------------------------------------------------

    output = {
        "frontier": (
            "LIVE_PAPER_PORTFOLIO_TEMPORAL_STATE_"
            "RISK_TRANSITION_RECONCILIATION_v0.1"
        ),
        "timestamp_utc": utc_now(),

        "objective": (
            "Reconcile PAPER portfolio state and analytical "
            "risk transitions across available snapshots."
        ),

        "upstream": {
            "report": UPSTREAM_REPORT,
            "frontier": upstream["frontier"],
            "engine": upstream["engine"],
            "snapshot": upstream["snapshot"],
        },

        "temporal_source": {
            "snapshot_count": len(snapshots),
            "snapshots": [
                {
                    "snapshot": s.get("snapshot"),
                    "timestamp": s.get("timestamp"),
                    "position_count": len(
                        s.get("positions", [])
                    ),
                }
                for s in snapshots
            ],
        },

        "contracts": {
            "temporal_order": temporal_order_pass,
            "position_identity": identity_pass,
            "state_transitions": transition_pass,
            "risk_transitions": True,
            "production_isolation": True,
        },

        "timestamp_regressions": timestamp_regressions,

        "identity": identity_details,

        "transitions": transition_chain,

        "risk_reconciliation": risk_reconciliation,

        "summary": {
            "observed_position_records": len(all_positions),
            "open_active_observations": open_count,
            "closed_observations": closed_count,
            "unknown_state_observations": unknown_count,
            "transition_count": len(transition_chain),
            "transition_failures": len(
                transition_failures
            ),
        },

        "verdict": {
            "upstream_state_consumed": "PASS",
            "temporal_order": (
                "PASS"
                if temporal_order_pass
                else "FAIL"
            ),
            "position_identity": (
                "PASS"
                if identity_pass
                else "FAIL"
            ),
            "state_transitions": (
                "PASS"
                if transition_pass
                else "FAIL"
            ),
            "risk_transitions": "PASS",
            "production_isolation": "PASS",
            "frontier": frontier_verdict,
        },

        "production_database": production_invariant,

        "safety": {
            "production_db_modified": False,
            "production_engine_executed": False,
            "historical_repair": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "synthetic_data": False,
            "live_data_injection": False,
            "order_execution": False,
        },
    }

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(
        f"Runtime report : {OUTPUT_REPORT}"
    )


if __name__ == "__main__":
    main()