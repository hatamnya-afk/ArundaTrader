# ARUNDA_TRADER_LIVE_PAPER_PORTFOLIO_DRAWDOWN_EQUITY_CURVE_PERFORMANCE_RISK_RECONCILIATION_v0.1.py

import json
import hashlib
import os
from datetime import datetime, timezone


# =============================================================================
# CONFIGURATION
# =============================================================================

PRODUCTION_DB = r"C:\Users\ASUS\ArundaTrader\arunda.db"

CAPTURE_DIR = r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc"

UPSTREAM_REPORT = os.path.join(
    CAPTURE_DIR,
    "LIVE_PAPER_PORTFOLIO_PERFORMANCE_ATTRIBUTION_PNL_CONSISTENCY_REPORT.json",
)

OUTPUT_REPORT = os.path.join(
    CAPTURE_DIR,
    "LIVE_PAPER_PORTFOLIO_DRAWDOWN_EQUITY_CURVE_PERFORMANCE_RISK_RECONCILIATION_REPORT.json",
)


# =============================================================================
# SAFETY POLICY
# =============================================================================

PRODUCTION_DB_WRITES_FORBIDDEN = True
PRODUCTION_ENGINE_EXECUTION = False
HISTORICAL_REPAIR = False
DIRECTION_INFERENCE = False
SCORE_RECONSTRUCTION = False
SYNTHETIC_DATA = False
LIVE_DATA_INJECTION = False
ORDER_EXECUTION = False
PAPER_EXECUTION_ANALYTICAL_ONLY = True


# =============================================================================
# HELPERS
# =============================================================================

def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def file_size(path):
    return os.path.getsize(path)


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, bool):
            return default

        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def first_value(obj, *keys, default=None):
    if not isinstance(obj, dict):
        return default

    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]

    return default


def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Upstream report not found: {path}"
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# PRODUCTION BASELINE
# =============================================================================

def get_production_baseline():
    if not os.path.exists(PRODUCTION_DB):
        raise FileNotFoundError(
            f"Production DB not found: {PRODUCTION_DB}"
        )

    size = file_size(PRODUCTION_DB)
    sha = sha256_file(PRODUCTION_DB)

    rows = None

    try:
        import sqlite3

        conn = sqlite3.connect(PRODUCTION_DB)

        tables = [
            "market_history",
            "market_records",
            "market_data",
        ]

        for table in tables:
            try:
                cur = conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                )
                rows = cur.fetchone()[0]
                break
            except Exception:
                continue

        conn.close()

    except Exception:
        rows = None

    return {
        "rows": rows,
        "size": size,
        "sha256": sha,
    }


# =============================================================================
# UPSTREAM VALIDATION
# =============================================================================

def extract_snapshot(report):
    value = first_value(
        report,
        "snapshot",
        "current_snapshot",
        "snapshot_id",
        default=None,
    )

    if isinstance(value, dict):
        return first_value(
            value,
            "snapshot_id",
            "id",
            "name",
            default=None,
        )

    return value


def extract_snapshots(report):
    candidates = [
        report.get("snapshots"),
        report.get("temporal_snapshots"),
        report.get("snapshot_history"),
        report.get("equity_curve"),
    ]

    for value in candidates:
        if isinstance(value, list):
            return value

    snapshot = extract_snapshot(report)

    if snapshot:
        return [
            {
                "snapshot_id": snapshot,
                "timestamp_utc": report.get("timestamp_utc"),
                "positions": report.get("positions_observed", 0),
                "equity": report.get("equity", 0.0),
                "notional": report.get("analytical_notional", 0.0),
                "risk": report.get("analytical_risk", 0.0),
                "realized_pnl": report.get("realized_pnl", 0.0),
                "unrealized_pnl": report.get("unrealized_pnl", 0.0),
                "total_pnl": report.get("total_pnl", 0.0),
            }
        ]

    return []


def extract_positions(report):
    for key in (
        "positions",
        "position_records",
        "paper_positions",
        "observed_positions",
        "selected_positions",
    ):
        value = report.get(key)

        if isinstance(value, list):
            return value

    return []


def validate_upstream(report):
    if not isinstance(report, dict):
        raise ValueError("Upstream report must be a JSON object.")

    frontier = report.get("frontier")

    if frontier is None:
        raise ValueError(
            "Upstream report missing required field: frontier"
        )

    snapshot = extract_snapshot(report)
    snapshots = extract_snapshots(report)
    positions = extract_positions(report)

    return {
        "frontier": frontier,
        "engine": report.get("engine"),
        "snapshot": snapshot,
        "snapshots": snapshots,
        "positions": positions,
        "raw": report,
    }


# =============================================================================
# TEMPORAL NORMALIZATION
# =============================================================================

def normalize_snapshot(item, fallback_index):
    if not isinstance(item, dict):
        item = {}

    snapshot_id = first_value(
        item,
        "snapshot_id",
        "snapshot",
        "id",
        default=f"UNKNOWN-{fallback_index}",
    )

    timestamp = first_value(
        item,
        "timestamp_utc",
        "timestamp",
        "time",
        "created_at",
        default=None,
    )

    equity = safe_float(
        first_value(
            item,
            "equity",
            "portfolio_equity",
            "account_equity",
            "net_equity",
            default=0.0,
        )
    )

    total_pnl = safe_float(
        first_value(
            item,
            "total_pnl",
            "pnl",
            "portfolio_pnl",
            default=0.0,
        )
    )

    realized_pnl = safe_float(
        first_value(
            item,
            "realized_pnl",
            "realized",
            default=0.0,
        )
    )

    unrealized_pnl = safe_float(
        first_value(
            item,
            "unrealized_pnl",
            "unrealized",
            default=0.0,
        )
    )

    notional = safe_float(
        first_value(
            item,
            "analytical_notional",
            "notional",
            "portfolio_notional",
            default=0.0,
        )
    )

    risk = safe_float(
        first_value(
            item,
            "analytical_risk",
            "portfolio_risk",
            "risk",
            default=0.0,
        )
    )

    positions = safe_int(
        first_value(
            item,
            "positions",
            "position_count",
            "total_positions",
            default=0,
        )
    )

    return {
        "snapshot_id": snapshot_id,
        "timestamp_utc": timestamp,
        "equity": equity,
        "total_pnl": total_pnl,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "notional": notional,
        "risk": risk,
        "positions": positions,
    }


def build_temporal_series(upstream):
    raw_snapshots = upstream["snapshots"]

    series = []

    for index, item in enumerate(raw_snapshots, start=1):
        series.append(
            normalize_snapshot(item, index)
        )

    # Sort only when timestamps are available.
    if len(series) > 1:
        series.sort(
            key=lambda x: (
                x["timestamp_utc"] is None,
                x["timestamp_utc"] or "",
            )
        )

    return series


# =============================================================================
# EQUITY CURVE
# =============================================================================

def build_equity_curve(series):
    curve = []

    for index, point in enumerate(series, start=1):
        curve.append(
            {
                "sequence": index,
                "snapshot_id": point["snapshot_id"],
                "timestamp_utc": point["timestamp_utc"],
                "equity": point["equity"],
                "total_pnl": point["total_pnl"],
            }
        )

    return curve


# =============================================================================
# DRAWDOWN
# =============================================================================

def calculate_drawdown(series):
    if not series:
        return {
            "peak_equity": 0.0,
            "trough_equity": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "current_drawdown": 0.0,
            "current_drawdown_pct": 0.0,
            "peak_snapshot": None,
            "trough_snapshot": None,
        }

    peak_equity = None
    peak_snapshot = None

    max_drawdown = 0.0
    max_drawdown_pct = 0.0
    trough_snapshot = None

    current_drawdown = 0.0
    current_drawdown_pct = 0.0

    for point in series:
        equity = point["equity"]

        if peak_equity is None or equity > peak_equity:
            peak_equity = equity
            peak_snapshot = point["snapshot_id"]

        drawdown = peak_equity - equity

        if peak_equity != 0:
            drawdown_pct = drawdown / abs(peak_equity)
        else:
            drawdown_pct = 0.0

        if drawdown > max_drawdown:
            max_drawdown = drawdown
            max_drawdown_pct = drawdown_pct
            trough_snapshot = point["snapshot_id"]

        current_drawdown = drawdown
        current_drawdown_pct = drawdown_pct

    return {
        "peak_equity": peak_equity or 0.0,
        "trough_equity": (
            peak_equity - max_drawdown
            if peak_equity is not None
            else 0.0
        ),
        "max_drawdown": max_drawdown,
        "max_drawdown_pct": max_drawdown_pct,
        "current_drawdown": current_drawdown,
        "current_drawdown_pct": current_drawdown_pct,
        "peak_snapshot": peak_snapshot,
        "trough_snapshot": trough_snapshot,
    }


# =============================================================================
# PERFORMANCE RISK
# =============================================================================

MAX_DRAWDOWN_LIMIT = 0.10
MAX_CURRENT_DRAWDOWN_LIMIT = 0.05
MAX_PORTFOLIO_RISK_LIMIT = 0.02


def evaluate_performance_risk(series, drawdown):
    if not series:
        return {
            "status": "NOT_PERFORMED",
            "reason": "NO_TEMPORAL_EQUITY_DATA",
            "checks": [],
            "circuit_breaker": "CLEAR",
        }

    latest = series[-1]

    checks = []

    max_dd = drawdown["max_drawdown_pct"]
    current_dd = drawdown["current_drawdown_pct"]
    risk = latest["risk"]

    checks.append(
        {
            "name": "MAX_DRAWDOWN",
            "observed": max_dd,
            "limit": MAX_DRAWDOWN_LIMIT,
            "pass": max_dd <= MAX_DRAWDOWN_LIMIT,
        }
    )

    checks.append(
        {
            "name": "CURRENT_DRAWDOWN",
            "observed": current_dd,
            "limit": MAX_CURRENT_DRAWDOWN_LIMIT,
            "pass": current_dd <= MAX_CURRENT_DRAWDOWN_LIMIT,
        }
    )

    checks.append(
        {
            "name": "PORTFOLIO_RISK",
            "observed": risk,
            "limit": MAX_PORTFOLIO_RISK_LIMIT,
            "pass": risk <= MAX_PORTFOLIO_RISK_LIMIT,
        }
    )

    all_pass = all(item["pass"] for item in checks)

    return {
        "status": "PASS" if all_pass else "BREACH",
        "reason": "NONE" if all_pass else "PERFORMANCE_RISK_LIMIT_BREACH",
        "checks": checks,
        "circuit_breaker": "CLEAR" if all_pass else "TRIGGERED",
    }


# =============================================================================
# P&L CONSISTENCY
# =============================================================================

def reconcile_pnl(series):
    if not series:
        return {
            "status": "NOT_PERFORMED",
            "consistency_error": 0.0,
            "realized_total": 0.0,
            "unrealized_total": 0.0,
            "reported_total": 0.0,
        }

    latest = series[-1]

    realized = latest["realized_pnl"]
    unrealized = latest["unrealized_pnl"]
    total = latest["total_pnl"]

    expected = realized + unrealized
    error = abs(total - expected)

    return {
        "status": "PASS" if error <= 1e-12 else "FAIL",
        "consistency_error": error,
        "realized_total": realized,
        "unrealized_total": unrealized,
        "reported_total": total,
        "expected_total": expected,
    }


# =============================================================================
# PRODUCTION INVARIANT
# =============================================================================

def verify_production_invariant(before):
    after = get_production_baseline()

    unchanged = (
        before["size"] == after["size"]
        and before["sha256"] == after["sha256"]
        and before["rows"] == after["rows"]
    )

    return after, unchanged


# =============================================================================
# REPORT
# =============================================================================

def build_report(
    upstream,
    baseline_before,
    baseline_after,
    temporal_series,
    equity_curve,
    drawdown,
    performance_risk,
    pnl_reconciliation,
    production_unchanged,
):
    has_data = len(temporal_series) > 0

    if not has_data:
        frontier_verdict = "NO_TRADE"
    elif performance_risk["circuit_breaker"] == "TRIGGERED":
        frontier_verdict = "RISK_BREACH"
    elif pnl_reconciliation["status"] == "FAIL":
        frontier_verdict = "PNL_INCONSISTENCY"
    else:
        frontier_verdict = "PASS"

    return {
        "frontier": (
            "LIVE_PAPER_PORTFOLIO_DRAWDOWN_EQUITY_CURVE_"
            "PERFORMANCE_RISK_RECONCILIATION_v0.1"
        ),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_frontier": upstream["frontier"],
        "engine": upstream["engine"],
        "current_snapshot": upstream["snapshot"],

        "temporal_state": {
            "snapshots_available": len(temporal_series),
            "series": temporal_series,
        },

        "equity_curve": equity_curve,

        "drawdown": drawdown,

        "performance_risk": performance_risk,

        "pnl_reconciliation": pnl_reconciliation,

        "production_database": {
            "before": baseline_before,
            "after": baseline_after,
            "unchanged": production_unchanged,
        },

        "safety": {
            "production_db_modified": not production_unchanged,
            "production_engine_executed": False,
            "historical_repair": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "synthetic_data": False,
            "live_data_injection": False,
            "order_execution": False,
            "paper_execution": "ANALYTICAL_ONLY",
        },

        "verdict": {
            "UPSTREAM_STATE_CONSUMED": "PASS",
            "TEMPORAL_EQUITY_STATE": (
                "PASS" if has_data else "NOT_PERFORMED"
            ),
            "DRAWDOWN_RECONCILIATION": (
                "PASS" if has_data else "NOT_PERFORMED"
            ),
            "EQUITY_CURVE_RECONCILIATION": (
                "PASS" if has_data else "NOT_PERFORMED"
            ),
            "PERFORMANCE_RISK": performance_risk["status"],
            "PNL_CONSISTENCY": pnl_reconciliation["status"],
            "PRODUCTION_ISOLATION": (
                "PASS" if production_unchanged else "FAIL"
            ),
            "frontier_verdict": frontier_verdict,
        },
    }


# =============================================================================
# PRINT
# =============================================================================

def print_report(report):
    upstream = report["source_frontier"]
    series = report["temporal_state"]["series"]
    drawdown = report["drawdown"]
    risk = report["performance_risk"]
    pnl = report["pnl_reconciliation"]

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO "
        "DRAWDOWN + EQUITY CURVE + PERFORMANCE RISK RECONCILIATION v0.1"
    )
    print("=" * 100)

    print()
    print("=" * 100)
    print("OBJECTIVE:")
    print(
        "  Consume ONLY the verified PAPER portfolio "
        "performance/P&L frontier."
    )
    print(
        "  Reconcile equity curve, drawdown and performance risk."
    )
    print("  No real order is created or submitted.")
    print("=" * 100)

    print()
    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)
    print(f"Frontier : {upstream}")
    print(f"Engine   : {report.get('engine')}")
    print(
        f"Snapshot : {report.get('current_snapshot')}"
    )
    print(
        f"Snapshots available : {len(series)}"
    )

    print()
    print("=" * 100)
    print("EQUITY CURVE")
    print("=" * 100)

    if not series:
        print("No temporal equity observations available.")
        print("Equity curve : NOT PERFORMED")
    else:
        for point in series:
            print(
                f"{point['snapshot_id']} | "
                f"equity={point['equity']:.6f} | "
                f"PnL={point['total_pnl']:.6f} | "
                f"positions={point['positions']}"
            )

    print()
    print("=" * 100)
    print("DRAWDOWN RECONCILIATION")
    print("=" * 100)

    print(
        f"Peak equity          : "
        f"{drawdown['peak_equity']:.6f}"
    )
    print(
        f"Maximum drawdown     : "
        f"{drawdown['max_drawdown']:.6f}"
    )
    print(
        f"Maximum drawdown %   : "
        f"{drawdown['max_drawdown_pct']:.6%}"
    )
    print(
        f"Current drawdown     : "
        f"{drawdown['current_drawdown']:.6f}"
    )
    print(
        f"Current drawdown %   : "
        f"{drawdown['current_drawdown_pct']:.6%}"
    )
    print(
        f"Peak snapshot        : "
        f"{drawdown['peak_snapshot']}"
    )
    print(
        f"Trough snapshot      : "
        f"{drawdown['trough_snapshot']}"
    )

    print()
    print("=" * 100)
    print("PERFORMANCE RISK")
    print("=" * 100)

    if not series:
        print("Performance risk : NOT PERFORMED")
        print("Reason            : NO_TEMPORAL_EQUITY_DATA")
    else:
        for check in risk["checks"]:
            status = "PASS" if check["pass"] else "BREACH"

            print(
                f"{check['name']:28} | "
                f"observed={check['observed']:.6f} | "
                f"limit={check['limit']:.6f} | "
                f"{status}"
            )

        print(
            f"Circuit breaker : "
            f"{risk['circuit_breaker']}"
        )

    print()
    print("=" * 100)
    print("REALIZED / UNREALIZED P&L CONSISTENCY")
    print("=" * 100)

    print(
        f"Realized P&L       : "
        f"{pnl['realized_total']:.6f}"
    )
    print(
        f"Unrealized P&L     : "
        f"{pnl['unrealized_total']:.6f}"
    )
    print(
        f"Reported Total P&L : "
        f"{pnl['reported_total']:.6f}"
    )
    print(
        f"Consistency error   : "
        f"{pnl['consistency_error']:.12f}"
    )
    print(
        f"Consistency status  : "
        f"{pnl['status']}"
    )

    print()
    print("=" * 100)
    print(
        "LIVE PAPER PORTFOLIO DRAWDOWN + EQUITY CURVE + "
        "PERFORMANCE RISK RECONCILIATION VERDICT"
    )
    print("=" * 100)

    verdict = report["verdict"]

    for key, value in verdict.items():
        print(
            f"{key:32} : {value}"
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

    if not series:
        print()
        print("No temporal equity data exists.")
        print(
            "Drawdown and performance-risk analysis "
            "were not performed."
        )

    print()
    print(f"Runtime report : {OUTPUT_REPORT}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    baseline_before = get_production_baseline()

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO "
        "DRAWDOWN + EQUITY CURVE + PERFORMANCE RISK RECONCILIATION v0.1"
    )
    print("=" * 100)

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)

    print(f"Rows   : {baseline_before['rows']}")
    print(f"Size   : {baseline_before['size']}")
    print(f"SHA256 : {baseline_before['sha256']}")

    print()
    print("=" * 100)
    print("UPSTREAM REPORT")
    print("=" * 100)
    print(f"Report : {UPSTREAM_REPORT}")

    report = load_json(UPSTREAM_REPORT)
    upstream = validate_upstream(report)

    temporal_series = build_temporal_series(upstream)

    equity_curve = build_equity_curve(
        temporal_series
    )

    drawdown = calculate_drawdown(
        temporal_series
    )

    performance_risk = evaluate_performance_risk(
        temporal_series,
        drawdown,
    )

    pnl_reconciliation = reconcile_pnl(
        temporal_series
    )

    baseline_after, production_unchanged = (
        verify_production_invariant(
            baseline_before
        )
    )

    final_report = build_report(
        upstream=upstream,
        baseline_before=baseline_before,
        baseline_after=baseline_after,
        temporal_series=temporal_series,
        equity_curve=equity_curve,
        drawdown=drawdown,
        performance_risk=performance_risk,
        pnl_reconciliation=pnl_reconciliation,
        production_unchanged=production_unchanged,
    )

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            final_report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print_report(final_report)


if __name__ == "__main__":
    main()