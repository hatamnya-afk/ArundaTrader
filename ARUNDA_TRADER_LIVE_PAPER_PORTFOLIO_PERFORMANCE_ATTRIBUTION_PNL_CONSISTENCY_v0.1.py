import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# ARUNDA TRADER LIVE PAPER PORTFOLIO PERFORMANCE ATTRIBUTION
# + REALIZED/UNREALIZED P&L CONSISTENCY v0.2
# =============================================================================

PRODUCTION_DB = r"C:\Users\ASUS\ArundaTrader\arunda.db"

CAPTURE_DIR = os.environ.get(
    "ARUNDA_LIVE_CAPTURE_DIR",
    r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc",
)

UPSTREAM_REPORT = os.path.join(
    CAPTURE_DIR,
    "LIVE_PAPER_PORTFOLIO_TEMPORAL_STATE_RISK_TRANSITION_RECONCILIATION_REPORT.json",
)

OUTPUT_REPORT = os.path.join(
    CAPTURE_DIR,
    "LIVE_PAPER_PORTFOLIO_PERFORMANCE_ATTRIBUTION_PNL_CONSISTENCY_REPORT.json",
)

EXPECTED_UPSTREAM_FRONTIER = (
    "LIVE_PAPER_PORTFOLIO_TEMPORAL_STATE_RISK_TRANSITION_RECONCILIATION"
)

EXPECTED_ENGINE = "FUSION_v0.5"


# =============================================================================
# SAFETY
# =============================================================================

PRODUCTION_WRITES_FORBIDDEN = True
PRODUCTION_ENGINE_EXECUTION_FORBIDDEN = True
HISTORICAL_REPAIR_FORBIDDEN = True
DIRECTION_INFERENCE_FORBIDDEN = True
SCORE_RECONSTRUCTION_FORBIDDEN = True
SYNTHETIC_DATA_FORBIDDEN = True
LIVE_DATA_INJECTION_FORBIDDEN = True
ORDER_EXECUTION_FORBIDDEN = True


# =============================================================================
# HELPERS
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Required report not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Report root must be a JSON object.")

    return data


def sha256_file(path: str) -> str:
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def file_size(path: str) -> int:
    return os.path.getsize(path)


def deep_get(obj: Any, *paths: Tuple[str, ...]) -> Any:
    for path in paths:
        cur = obj
        ok = True

        for key in path:
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break

        if ok:
            return cur

    return None


def first_value(obj: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        if key in obj:
            return obj[key]
    return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


# =============================================================================
# PRODUCTION BASELINE
# =============================================================================

def production_baseline() -> Dict[str, Any]:
    if not os.path.isfile(PRODUCTION_DB):
        raise FileNotFoundError(
            f"Production database not found: {PRODUCTION_DB}"
        )

    size = file_size(PRODUCTION_DB)
    digest = sha256_file(PRODUCTION_DB)

    rows = None

    # Read-only SQLite inspection.
    try:
        import sqlite3

        uri = f"file:{PRODUCTION_DB}?mode=ro"

        conn = sqlite3.connect(uri, uri=True)
        try:
            tables = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                """
            ).fetchall()

            preferred = [
                "market_history",
                "market_data",
                "market_records",
            ]

            selected = None

            table_names = {x[0] for x in tables}

            for name in preferred:
                if name in table_names:
                    selected = name
                    break

            if selected:
                rows = conn.execute(
                    f'SELECT COUNT(*) FROM "{selected}"'
                ).fetchone()[0]

        finally:
            conn.close()

    except Exception:
        rows = None

    return {
        "rows": rows,
        "size": size,
        "sha256": digest,
    }


# =============================================================================
# UPSTREAM EXTRACTION
# =============================================================================

def extract_snapshot(report: Dict[str, Any]) -> Optional[str]:
    """
    Accept the actual temporal frontier schema without requiring a single
    rigid field name.

    Supported forms include:
      current_snapshot
      snapshot_id
      snapshot
      temporal_snapshot
      upstream.current_snapshot
      upstream.snapshot
      current_snapshot_id
    """

    candidates = [
        report.get("current_snapshot"),
        report.get("snapshot_id"),
        report.get("snapshot"),
        report.get("temporal_snapshot"),
        report.get("current_snapshot_id"),

        deep_get(report, ("upstream", "current_snapshot")),
        deep_get(report, ("upstream", "snapshot")),
        deep_get(report, ("upstream_state", "current_snapshot")),
        deep_get(report, ("upstream_state", "snapshot")),
    ]

    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()

        if isinstance(value, dict):
            for key in (
                "snapshot_id",
                "id",
                "snapshot",
                "current_snapshot",
            ):
                nested = value.get(key)
                if isinstance(nested, str) and nested.strip():
                    return nested.strip()

    # Final fallback: inspect temporal snapshot collection.
    temporal = first_value(
        report,
        [
            "snapshots",
            "temporal_snapshots",
            "snapshot_history",
        ],
    )

    if isinstance(temporal, list) and temporal:
        for item in reversed(temporal):
            if isinstance(item, dict):
                for key in (
                    "snapshot_id",
                    "snapshot",
                    "id",
                ):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()

    return None


def extract_snapshots(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = first_value(
        report,
        [
            "snapshots",
            "temporal_snapshots",
            "snapshot_history",
        ],
    )

    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]

    # Some reports store the aggregate transition records here.
    raw = first_value(
        report,
        [
            "aggregate_risk_transitions",
            "risk_transitions",
            "transitions",
        ],
    )

    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]

    return []


def extract_positions(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    possible = [
        report.get("positions"),
        report.get("paper_positions"),
        report.get("position_records"),

        deep_get(report, ("portfolio", "positions")),
        deep_get(report, ("portfolio_state", "positions")),
        deep_get(report, ("paper_portfolio", "positions")),
    ]

    for value in possible:
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]

    return []


def extract_transition_records(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    possible = [
        report.get("state_transitions"),
        report.get("position_transitions"),
        report.get("transitions"),
    ]

    for value in possible:
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]

    return []


def validate_upstream(report: Dict[str, Any]) -> Dict[str, Any]:
    frontier = str(
        first_value(
            report,
            ["frontier", "source_frontier"],
        )
        or ""
    )

    engine = first_value(
        report,
        ["engine"],
    )

    snapshot = extract_snapshot(report)
    snapshots = extract_snapshots(report)
    positions = extract_positions(report)
    transitions = extract_transition_records(report)

    # The temporal report previously produced by the project has:
    #
    # "Current snapshot : FUSION-..."
    #
    # and may not serialize that value as "current_snapshot".
    #
    # Therefore snapshot extraction is compatibility-based rather than
    # forcing a new audit/reconstruction.

    if not frontier:
        raise ValueError("Upstream temporal report missing frontier.")

    if EXPECTED_UPSTREAM_FRONTIER not in frontier:
        raise ValueError(
            f"Unexpected upstream frontier: {frontier}"
        )

    if snapshot is None and snapshots:
        snapshot = extract_snapshot(
            {
                "snapshots": snapshots
            }
        )

    if snapshot is None:
        # A completely empty temporal state is still valid only if the report
        # explicitly says that no current snapshot exists.
        decision = str(report.get("decision", "")).upper()

        if decision in {
            "NO_TRADE",
            "NO_TRADE_CANDIDATE",
            "EMPTY",
            "NO_POSITION",
        }:
            snapshot = None
        else:
            raise ValueError(
                "Unable to resolve upstream current snapshot."
            )

    return {
        "frontier": frontier,
        "engine": engine,
        "snapshot": snapshot,
        "snapshots": snapshots,
        "positions": positions,
        "transitions": transitions,
    }


# =============================================================================
# SNAPSHOT NORMALIZATION
# =============================================================================

def normalize_snapshot(item: Dict[str, Any]) -> Dict[str, Any]:
    snapshot_id = (
        first_value(
            item,
            [
                "snapshot_id",
                "snapshot",
                "id",
            ],
        )
        or ""
    )

    timestamp = (
        first_value(
            item,
            [
                "timestamp_utc",
                "timestamp",
                "time",
                "created_at",
            ],
        )
        or ""
    )

    positions = safe_int(
        first_value(
            item,
            [
                "positions",
                "position_count",
                "paper_positions",
            ]
        ),
        0,
    )

    notional = safe_float(
        first_value(
            item,
            [
                "notional",
                "analytical_notional",
                "total_analytical_notional",
            ]
        ),
        0.0,
    )

    risk = safe_float(
        first_value(
            item,
            [
                "risk",
                "analytical_risk",
                "portfolio_risk",
                "total_analytical_risk",
            ]
        ),
        0.0,
    )

    pnl = safe_float(
        first_value(
            item,
            [
                "pnl",
                "unrealized_pnl",
                "aggregate_unrealized_pnl",
                "total_pnl",
            ]
        ),
        0.0,
    )

    return {
        "snapshot_id": str(snapshot_id),
        "timestamp": str(timestamp),
        "positions": positions,
        "notional": notional,
        "risk": risk,
        "pnl": pnl,
    }


# =============================================================================
# POSITION NORMALIZATION
# =============================================================================

def normalize_position(item: Dict[str, Any]) -> Dict[str, Any]:
    position_id = first_value(
        item,
        [
            "position_id",
            "id",
            "trade_id",
        ],
    )

    asset = first_value(
        item,
        [
            "asset",
            "symbol",
        ],
    )

    state = first_value(
        item,
        [
            "state",
            "status",
            "position_state",
        ],
    )

    realized = safe_float(
        first_value(
            item,
            [
                "realized_pnl",
                "realized_pnl_pct",
            ]
        ),
        0.0,
    )

    unrealized = safe_float(
        first_value(
            item,
            [
                "unrealized_pnl",
                "unrealized_pnl_pct",
                "mtm_pnl",
            ]
        ),
        0.0,
    )

    total = safe_float(
        first_value(
            item,
            [
                "total_pnl",
                "pnl",
                "net_pnl",
            ]
        ),
        realized + unrealized,
    )

    return {
        "position_id": str(position_id) if position_id is not None else None,
        "asset": str(asset) if asset is not None else None,
        "state": str(state).upper() if state is not None else "UNKNOWN",
        "realized_pnl": realized,
        "unrealized_pnl": unrealized,
        "total_pnl": total,
        "raw": item,
    }


# =============================================================================
# PERFORMANCE ATTRIBUTION
# =============================================================================

def reconcile_performance(
    snapshots: List[Dict[str, Any]],
    positions: List[Dict[str, Any]],
) -> Dict[str, Any]:

    normalized_snapshots = [
        normalize_snapshot(x)
        for x in snapshots
    ]

    normalized_snapshots.sort(
        key=lambda x: x.get("timestamp", "")
    )

    realized_total = 0.0
    unrealized_total = 0.0

    normalized_positions = [
        normalize_position(x)
        for x in positions
    ]

    for position in normalized_positions:
        realized_total += position["realized_pnl"]
        unrealized_total += position["unrealized_pnl"]

    position_total = sum(
        p["total_pnl"]
        for p in normalized_positions
    )

    if normalized_snapshots:
        first = normalized_snapshots[0]
        last = normalized_snapshots[-1]

        pnl_change = last["pnl"] - first["pnl"]
    else:
        pnl_change = 0.0

    consistency_error = (
        position_total - (realized_total + unrealized_total)
    )

    return {
        "snapshot_count": len(normalized_snapshots),
        "normalized_snapshots": normalized_snapshots,
        "position_count": len(normalized_positions),
        "normalized_positions": normalized_positions,
        "realized_pnl": realized_total,
        "unrealized_pnl": unrealized_total,
        "position_total_pnl": position_total,
        "snapshot_pnl_change": pnl_change,
        "consistency_error": consistency_error,
        "consistent": abs(consistency_error) <= 1e-9,
    }


# =============================================================================
# REPORT
# =============================================================================

def build_report(
    baseline_before: Dict[str, Any],
    baseline_after: Dict[str, Any],
    upstream: Dict[str, Any],
    performance: Dict[str, Any],
) -> Dict[str, Any]:

    snapshot = upstream["snapshot"]
    positions = performance["normalized_positions"]

    closed = [
        p for p in positions
        if p["state"] in {
            "CLOSED",
            "CLOSE",
            "EXITED",
        }
    ]

    open_positions = [
        p for p in positions
        if p["state"] in {
            "OPEN",
            "ACTIVE",
        }
    ]

    realized = performance["realized_pnl"]
    unrealized = performance["unrealized_pnl"]

    total = realized + unrealized

    if len(positions) == 0:
        frontier_verdict = "NO_TRADE"
        performance_status = "NOT_PERFORMED"
        pnl_status = "NOT_PERFORMED"
    else:
        performance_status = "PASS"
        pnl_status = (
            "PASS"
            if performance["consistent"]
            else "FAIL"
        )

        frontier_verdict = (
            "PASS"
            if performance["consistent"]
            else "BLOCKED"
        )

    unchanged = (
        baseline_before["rows"] == baseline_after["rows"]
        and baseline_before["size"] == baseline_after["size"]
        and baseline_before["sha256"] == baseline_after["sha256"]
    )

    return {
        "frontier": (
            "LIVE_PAPER_PORTFOLIO_PERFORMANCE_ATTRIBUTION_PNL_CONSISTENCY_v0.2"
        ),
        "timestamp_utc": utc_now(),
        "engine": upstream["engine"],
        "current_snapshot": snapshot,

        "source_frontier": upstream["frontier"],

        "upstream": {
            "frontier": upstream["frontier"],
            "engine": upstream["engine"],
            "current_snapshot": snapshot,
            "snapshot_count": len(performance["normalized_snapshots"]),
        },

        "performance": {
            "status": performance_status,
            "snapshot_count": performance["snapshot_count"],
            "position_count": performance["position_count"],
            "open_positions": len(open_positions),
            "closed_positions": len(closed),
            "realized_pnl": realized,
            "unrealized_pnl": unrealized,
            "total_pnl": total,
            "snapshot_pnl_change": performance["snapshot_pnl_change"],
        },

        "pnl_consistency": {
            "status": pnl_status,
            "realized_pnl": realized,
            "unrealized_pnl": unrealized,
            "total_pnl": total,
            "consistency_error": performance["consistency_error"],
            "consistent": performance["consistent"],
        },

        "attribution": {
            "available": len(positions) > 0,
            "realized_component": realized,
            "unrealized_component": unrealized,
            "total_component": total,
        },

        "positions": positions,

        "production_database": {
            "before": baseline_before,
            "after": baseline_after,
            "unchanged": unchanged,
        },

        "safety": {
            "production_db_modified": not unchanged,
            "production_engine_executed": False,
            "historical_repair": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "synthetic_data": False,
            "live_data_injection": False,
            "order_execution": False,
        },

        "decision": frontier_verdict,
    }


# =============================================================================
# CONSOLE OUTPUT
# =============================================================================

def print_report(
    baseline: Dict[str, Any],
    upstream: Dict[str, Any],
    result: Dict[str, Any],
) -> None:

    performance = result["performance"]
    pnl = result["pnl_consistency"]

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO PERFORMANCE ATTRIBUTION "
        "+ REALIZED/UNREALIZED P&L CONSISTENCY v0.2"
    )
    print("=" * 100)

    print()
    print("=" * 100)
    print("OBJECTIVE:")
    print(
        "  Consume ONLY the verified temporal PAPER portfolio frontier."
    )
    print(
        "  Reconcile performance attribution and realized/unrealized P&L."
    )
    print("  No real order is created or submitted.")
    print("=" * 100)

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)
    print(f"Rows   : {baseline['rows']}")
    print(f"Size   : {baseline['size']}")
    print(f"SHA256 : {baseline['sha256']}")

    print()
    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)
    print(f"Frontier : {upstream['frontier']}")
    print(f"Engine   : {upstream['engine']}")
    print(f"Snapshot : {upstream['snapshot']}")
    print(
        f"Snapshots available : "
        f"{performance_snapshot_count(result)}"
    )

    print()
    print("=" * 100)
    print("PAPER PERFORMANCE ATTRIBUTION")
    print("=" * 100)
    print(
        f"Positions observed : "
        f"{performance['position_count']}"
    )
    print(
        f"Open positions     : "
        f"{performance['open_positions']}"
    )
    print(
        f"Closed positions   : "
        f"{performance['closed_positions']}"
    )
    print(
        f"Realized P&L       : "
        f"{performance['realized_pnl']:.6f}"
    )
    print(
        f"Unrealized P&L     : "
        f"{performance['unrealized_pnl']:.6f}"
    )
    print(
        f"Total P&L          : "
        f"{performance['total_pnl']:.6f}"
    )

    if performance["position_count"] == 0:
        print()
        print("Performance attribution : NOT PERFORMED")
        print("Reason                  : NO_PAPER_POSITIONS")

    print()
    print("=" * 100)
    print("REALIZED / UNREALIZED P&L CONSISTENCY")
    print("=" * 100)
    print(
        f"Realized component   : "
        f"{pnl['realized_pnl']:.6f}"
    )
    print(
        f"Unrealized component : "
        f"{pnl['unrealized_pnl']:.6f}"
    )
    print(
        f"Total P&L            : "
        f"{pnl['total_pnl']:.6f}"
    )
    print(
        f"Consistency error     : "
        f"{pnl['consistency_error']:.12f}"
    )

    if performance["position_count"] == 0:
        print("Consistency status   : NOT_PERFORMED")
    else:
        print(
            "Consistency status   : "
            + ("PASS" if pnl["consistent"] else "FAIL")
        )

    print()
    print("=" * 100)
    print(
        "LIVE PAPER PORTFOLIO PERFORMANCE ATTRIBUTION "
        "+ REALIZED/UNREALIZED P&L CONSISTENCY VERDICT"
    )
    print("=" * 100)

    print("UPSTREAM_STATE_CONSUMED       : PASS")
    print(
        "PERFORMANCE_ATTRIBUTION      : "
        + performance["status"]
    )
    print(
        "PNL_CONSISTENCY               : "
        + pnl["status"]
    )

    unchanged = result["production_database"]["unchanged"]

    print(
        "PRODUCTION_ISOLATION          : "
        + ("PASS" if unchanged else "FAIL")
    )

    print(
        "FRONTIER VERDICT              : "
        + result["decision"]
    )

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    before = result["production_database"]["before"]
    after = result["production_database"]["after"]

    print(f"Before rows : {before['rows']}")
    print(f"After rows  : {after['rows']}")
    print(f"Before size : {before['size']}")
    print(f"After size  : {after['size']}")
    print(f"Before SHA256 : {before['sha256']}")
    print(f"After SHA256  : {after['sha256']}")

    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if unchanged else "FAIL")
    )

    print()
    print("=" * 100)
    print("FINAL SAFETY VERDICT")
    print("=" * 100)
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

    if performance["position_count"] == 0:
        print()
        print("No paper positions exist.")
        print("Performance attribution and P&L reconciliation were not performed.")

    print()
    print(f"Runtime report : {OUTPUT_REPORT}")


def performance_snapshot_count(result: Dict[str, Any]) -> int:
    return safe_int(
        deep_get(
            result,
            ("upstream", "snapshot_count"),
        ),
        0,
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO PERFORMANCE ATTRIBUTION "
        "+ REALIZED/UNREALIZED P&L CONSISTENCY v0.2"
    )
    print("=" * 100)

    baseline_before = production_baseline()

    report = load_json(UPSTREAM_REPORT)

    upstream = validate_upstream(report)

    performance = reconcile_performance(
        upstream["snapshots"],
        upstream["positions"],
    )

    result = build_report(
        baseline_before,
        production_baseline(),
        upstream,
        performance,
    )

    # Final production invariant.
    baseline_after = production_baseline()

    result["production_database"]["after"] = baseline_after

    result["production_database"]["unchanged"] = (
        baseline_before["rows"] == baseline_after["rows"]
        and baseline_before["size"] == baseline_after["size"]
        and baseline_before["sha256"] == baseline_after["sha256"]
    )

    if not result["production_database"]["unchanged"]:
        result["decision"] = "BLOCKED"

    result["safety"]["production_db_modified"] = not (
        result["production_database"]["unchanged"]
    )

    os.makedirs(CAPTURE_DIR, exist_ok=True)

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print_report(
        baseline_before,
        upstream,
        result,
    )


if __name__ == "__main__":
    main()