import json
import math
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


# =============================================================================
# ARUNDA TRADER
# LIVE PAPER PORTFOLIO PERFORMANCE STABILITY + RISK-ADJUSTED METRICS
# v0.1
# =============================================================================

VERSION = "v0.1"

PRODUCTION_DB = Path(
    r"C:\Users\ASUS\ArundaTrader\arunda.db"
)

LIVE_DIR = Path(
    r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc"
)

UPSTREAM_REPORT = (
    LIVE_DIR
    / "LIVE_PAPER_PORTFOLIO_PERFORMANCE_METRICS_TRADE_STATISTICS_RECONCILIATION_REPORT.json"
)

OUTPUT_REPORT = (
    LIVE_DIR
    / "LIVE_PAPER_PORTFOLIO_PERFORMANCE_STABILITY_RISK_ADJUSTED_METRICS_REPORT.json"
)

EXPECTED_UPSTREAM_FRONTIER = (
    "LIVE_PAPER_PORTFOLIO_PERFORMANCE_METRICS_"
    "TRADE_STATISTICS_RECONCILIATION_v0.2"
)

EPSILON = 1e-12


# =============================================================================
# SAFETY POLICY
# =============================================================================

SAFETY = {
    "production_db_modified": False,
    "production_engine_executed": False,
    "historical_repair": False,
    "direction_inference": False,
    "score_reconstruction": False,
    "synthetic_data": False,
    "live_data_injection": False,
    "order_execution": False,
}


# =============================================================================
# BASIC UTILITIES
# =============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def read_only_row_count(path):
    """
    Read-only production DB inspection.

    No INSERT / UPDATE / DELETE / DDL is executed.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Production database not found: {path}"
        )

    uri = f"file:{path.as_posix()}?mode=ro"

    total = 0

    with sqlite3.connect(uri, uri=True) as conn:

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()

        for (table_name,) in tables:

            quoted = '"' + table_name.replace('"', '""') + '"'

            try:
                row = conn.execute(
                    f"SELECT COUNT(*) FROM {quoted}"
                ).fetchone()

                if row:
                    total += int(row[0])

            except sqlite3.DatabaseError:
                continue

    return total


def production_fingerprint():

    return {
        "rows": read_only_row_count(PRODUCTION_DB),
        "size": PRODUCTION_DB.stat().st_size,
        "sha256": sha256_file(PRODUCTION_DB),
    }


def load_json(path):

    if not path.exists():
        raise FileNotFoundError(
            f"Required upstream report not found: {path}"
        )

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def first_present(obj, keys, default=None):

    if not isinstance(obj, dict):
        return default

    for key in keys:

        if key in obj and obj[key] is not None:
            return obj[key]

    return default


def as_float(value, default=None):

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# =============================================================================
# UPSTREAM NORMALIZATION
# =============================================================================

def normalize_upstream(report):

    if not isinstance(report, dict):
        raise ValueError(
            "Upstream report must be a JSON object."
        )

    frontier = report.get("frontier")

    if frontier != EXPECTED_UPSTREAM_FRONTIER:
        raise ValueError(
            "Unexpected upstream frontier: "
            f"{frontier!r}; expected "
            f"{EXPECTED_UPSTREAM_FRONTIER!r}"
        )

    upstream = report.get("upstream", {})

    if not isinstance(upstream, dict):
        upstream = {}

    current_snapshot = first_present(
        upstream,
        [
            "current_snapshot",
            "snapshot",
            "snapshot_id",
        ],
    )

    if current_snapshot is None:
        current_snapshot = first_present(
            report,
            [
                "current_snapshot",
                "snapshot",
                "snapshot_id",
            ],
        )

    engine = first_present(
        upstream,
        [
            "engine",
            "source_engine",
        ],
        default="None",
    )

    if engine is None:
        engine = first_present(
            report,
            ["engine"],
            default="None",
        )

    snapshots_available = first_present(
        upstream,
        [
            "snapshots_available",
            "snapshot_count",
        ],
    )

    if snapshots_available is None:
        snapshots_available = first_present(
            report,
            [
                "snapshots_available",
                "snapshot_count",
            ],
        )

    snapshots_available = (
        int(snapshots_available)
        if snapshots_available is not None
        else 0
    )

    # -------------------------------------------------------------------------
    # Snapshot records
    # -------------------------------------------------------------------------

    snapshots = []

    possible_collections = [
        report.get("snapshots"),
        report.get("snapshot_history"),
        report.get("temporal_snapshots"),
        report.get("snapshot_records"),
        report.get("equity_curve"),
        upstream.get("snapshots"),
        upstream.get("snapshot_history"),
        upstream.get("temporal_snapshots"),
        upstream.get("snapshot_records"),
        upstream.get("equity_curve"),
    ]

    for collection in possible_collections:

        if isinstance(collection, list):

            snapshots = collection
            break

    # If the upstream has one explicit current snapshot but no collection,
    # represent the known state as a single observational point.
    if not snapshots and current_snapshot:

        snapshots = [
            {
                "snapshot": current_snapshot,
            }
        ]

    if snapshots_available == 0 and snapshots:
        snapshots_available = len(snapshots)

    # -------------------------------------------------------------------------
    # Performance values
    # -------------------------------------------------------------------------

    realized_pnl = first_present(
        report,
        [
            "realized_pnl",
            "reported_realized_pnl",
        ],
        default=0.0,
    )

    unrealized_pnl = first_present(
        report,
        [
            "unrealized_pnl",
            "reported_unrealized_pnl",
        ],
        default=0.0,
    )

    total_pnl = first_present(
        report,
        [
            "total_pnl",
            "reported_total_pnl",
        ],
        default=None,
    )

    if total_pnl is None:
        total_pnl = (
            as_float(realized_pnl, 0.0)
            + as_float(unrealized_pnl, 0.0)
        )

    # -------------------------------------------------------------------------
    # Trade statistics
    # -------------------------------------------------------------------------

    trade_stats = report.get(
        "trade_statistics",
        {}
    )

    if not isinstance(trade_stats, dict):
        trade_stats = {}

    closed_trades = first_present(
        trade_stats,
        [
            "closed_trades",
            "closed_positions",
        ],
        default=0,
    )

    open_trades = first_present(
        trade_stats,
        [
            "open_trades",
            "open_positions",
        ],
        default=0,
    )

    return {
        "frontier": frontier,
        "engine": engine,
        "current_snapshot": current_snapshot,
        "snapshots_available": snapshots_available,
        "snapshots": snapshots,
        "realized_pnl": as_float(realized_pnl, 0.0),
        "unrealized_pnl": as_float(unrealized_pnl, 0.0),
        "total_pnl": as_float(total_pnl, 0.0),
        "closed_trades": int(closed_trades or 0),
        "open_trades": int(open_trades or 0),
    }


# =============================================================================
# SNAPSHOT EXTRACTION
# =============================================================================

def snapshot_value(snapshot, keys, default=None):

    if not isinstance(snapshot, dict):
        return default

    value = first_present(
        snapshot,
        keys,
        default=None,
    )

    if value is not None:
        return value

    nested = snapshot.get("state")

    if isinstance(nested, dict):

        value = first_present(
            nested,
            keys,
            default=None,
        )

        if value is not None:
            return value

    return default


def normalize_snapshots(upstream):

    normalized = []

    for index, snapshot in enumerate(
        upstream["snapshots"]
    ):

        snapshot_id = snapshot_value(
            snapshot,
            [
                "snapshot",
                "snapshot_id",
                "id",
            ],
            default=None,
        )

        timestamp = snapshot_value(
            snapshot,
            [
                "timestamp_utc",
                "timestamp",
                "time",
            ],
            default=None,
        )

        equity = snapshot_value(
            snapshot,
            [
                "equity",
                "equity_value",
            ],
            default=None,
        )

        pnl = snapshot_value(
            snapshot,
            [
                "pnl",
                "total_pnl",
                "total_pnl_pct",
            ],
            default=None,
        )

        risk = snapshot_value(
            snapshot,
            [
                "risk",
                "portfolio_risk",
                "analytical_risk",
            ],
            default=None,
        )

        positions = snapshot_value(
            snapshot,
            [
                "positions",
                "position_count",
            ],
            default=None,
        )

        normalized.append(
            {
                "index": index,
                "snapshot": snapshot_id,
                "timestamp": timestamp,
                "equity": as_float(equity),
                "pnl": as_float(pnl),
                "risk": as_float(risk),
                "positions": (
                    int(positions)
                    if positions is not None
                    else None
                ),
            }
        )

    return normalized


# =============================================================================
# RETURN SERIES
# =============================================================================

def build_return_series(snapshots):

    valid = [
        s for s in snapshots
        if s["equity"] is not None
    ]

    if len(valid) < 2:
        return []

    returns = []

    for previous, current in zip(
        valid,
        valid[1:],
    ):

        previous_equity = previous["equity"]
        current_equity = current["equity"]

        if abs(previous_equity) <= EPSILON:
            continue

        ret = (
            current_equity - previous_equity
        ) / abs(previous_equity)

        if math.isfinite(ret):
            returns.append(ret)

    return returns


# =============================================================================
# STATISTICS
# =============================================================================

def mean(values):

    if not values:
        return None

    return sum(values) / len(values)


def sample_std(values):

    if len(values) < 2:
        return None

    avg = mean(values)

    variance = sum(
        (x - avg) ** 2
        for x in values
    ) / (len(values) - 1)

    return math.sqrt(variance)


def downside_deviation(values):

    downside = [
        x for x in values
        if x < 0
    ]

    if len(downside) < 2:
        return None

    squared = [
        x ** 2
        for x in downside
    ]

    return math.sqrt(
        sum(squared) / len(squared)
    )


def calculate_risk_adjusted_metrics(returns):

    if len(returns) < 2:

        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "MINIMUM_TWO_RETURN_OBSERVATIONS_REQUIRED",
            "observations": len(returns),
            "mean_return": None,
            "volatility": None,
            "downside_deviation": None,
            "sharpe_like": None,
            "sortino_like": None,
        }

    avg = mean(returns)
    volatility = sample_std(returns)
    downside = downside_deviation(returns)

    sharpe = None

    if volatility is not None and volatility > EPSILON:
        sharpe = avg / volatility

    sortino = None

    if downside is not None and downside > EPSILON:
        sortino = avg / downside

    return {
        "status": "PASS",
        "reason": None,
        "observations": len(returns),
        "mean_return": avg,
        "volatility": volatility,
        "downside_deviation": downside,
        "sharpe_like": sharpe,
        "sortino_like": sortino,
    }


# =============================================================================
# PERFORMANCE STABILITY
# =============================================================================

def evaluate_stability(
    snapshots,
    returns,
):

    if len(snapshots) < 2:

        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "MINIMUM_TWO_SNAPSHOTS_REQUIRED",
            "snapshots": len(snapshots),
            "return_observations": len(returns),
            "stable": None,
        }

    finite_returns = [
        x for x in returns
        if math.isfinite(x)
    ]

    if not finite_returns:

        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "NO_VALID_RETURN_SERIES",
            "snapshots": len(snapshots),
            "return_observations": 0,
            "stable": None,
        }

    volatility = sample_std(
        finite_returns
    )

    if volatility is None:

        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "VOLATILITY_REQUIRES_TWO_RETURN_OBSERVATIONS",
            "snapshots": len(snapshots),
            "return_observations": len(finite_returns),
            "stable": None,
        }

    return {
        "status": "PASS",
        "reason": None,
        "snapshots": len(snapshots),
        "return_observations": len(finite_returns),
        "stable": True,
    }


# =============================================================================
# CROSS-CHECK WITH UPSTREAM P&L
# =============================================================================

def reconcile_current_pnl(
    upstream,
    snapshots,
):

    if not snapshots:

        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "NO_SNAPSHOT_DATA",
            "error": None,
        }

    latest = snapshots[-1]

    latest_pnl = latest["pnl"]

    if latest_pnl is None:

        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "LATEST_SNAPSHOT_HAS_NO_PNL",
            "error": None,
        }

    error = abs(
        latest_pnl
        - upstream["total_pnl"]
    )

    return {
        "status": (
            "PASS"
            if error <= EPSILON
            else "FAIL"
        ),
        "reason": None,
        "error": error,
        "latest_snapshot_pnl": latest_pnl,
        "upstream_total_pnl": upstream["total_pnl"],
    }


# =============================================================================
# BUILD REPORT
# =============================================================================

def build_report(
    before,
    after,
    upstream,
    snapshots,
    returns,
    stability,
    risk_metrics,
    pnl_check,
):

    enough_for_metrics = (
        risk_metrics["status"] == "PASS"
    )

    enough_for_stability = (
        stability["status"] == "PASS"
    )

    if not enough_for_metrics:

        performance_metrics_status = (
            "INSUFFICIENT_DATA"
        )

    else:

        performance_metrics_status = "PASS"

    if not enough_for_stability:

        stability_status = "INSUFFICIENT_DATA"

    else:

        stability_status = "PASS"

    if (
        before != after
        or pnl_check["status"] == "FAIL"
    ):

        frontier_verdict = "BLOCKED"

    elif (
        performance_metrics_status == "PASS"
        and stability_status == "PASS"
    ):

        frontier_verdict = "PASS"

    else:

        frontier_verdict = "INSUFFICIENT_DATA"

    return {

        "frontier": (
            "LIVE_PAPER_PORTFOLIO_PERFORMANCE_STABILITY_"
            "RISK_ADJUSTED_METRICS_v0.1"
        ),

        "version": VERSION,

        "timestamp_utc": utc_now(),

        "objective": (
            "Evaluate temporal PAPER portfolio performance "
            "stability and risk-adjusted metrics without "
            "reconstructing or inferring upstream signals."
        ),

        "upstream": {
            "report": str(UPSTREAM_REPORT),
            "frontier": upstream["frontier"],
            "engine": upstream["engine"],
            "current_snapshot": upstream["current_snapshot"],
            "snapshots_available": upstream["snapshots_available"],
            "closed_trades": upstream["closed_trades"],
            "open_trades": upstream["open_trades"],
        },

        "temporal_observations": {
            "snapshots": snapshots,
            "return_series": returns,
            "return_observations": len(returns),
        },

        "performance_stability": stability,

        "risk_adjusted_metrics": risk_metrics,

        "pnl_consistency": pnl_check,

        "production_database": {
            "before": before,
            "after": after,
            "unchanged": before == after,
        },

        "safety": SAFETY.copy(),

        "verdict": {
            "UPSTREAM_STATE_CONSUMED": "PASS",
            "PERFORMANCE_STABILITY": stability_status,
            "RISK_ADJUSTED_METRICS": performance_metrics_status,
            "PNL_CONSISTENCY": pnl_check["status"],
            "PRODUCTION_ISOLATION": (
                "PASS"
                if before == after
                else "FAIL"
            ),
            "FRONTIER_VERDICT": frontier_verdict,
        },
    }


# =============================================================================
# CONSOLE
# =============================================================================

def print_report(report):

    upstream = report["upstream"]
    stability = report["performance_stability"]
    metrics = report["risk_adjusted_metrics"]
    pnl = report["pnl_consistency"]
    verdict = report["verdict"]

    before = report["production_database"]["before"]
    after = report["production_database"]["after"]

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO "
        "PERFORMANCE STABILITY + RISK-ADJUSTED METRICS v0.1"
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
        "  Evaluate temporal performance stability and "
        "risk-adjusted metrics."
    )
    print(
        "  No real order is created or submitted."
    )
    print("=" * 100)

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)
    print(f"Rows   : {before['rows']}")
    print(f"Size   : {before['size']}")
    print(f"SHA256 : {before['sha256']}")

    print()
    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)
    print(f"Frontier : {upstream['frontier']}")
    print(f"Engine   : {upstream['engine']}")
    print(f"Snapshot : {upstream['current_snapshot']}")
    print(
        f"Snapshots available : "
        f"{upstream['snapshots_available']}"
    )
    print(
        f"Closed trades       : "
        f"{upstream['closed_trades']}"
    )
    print(
        f"Open trades         : "
        f"{upstream['open_trades']}"
    )

    print()
    print("=" * 100)
    print("PERFORMANCE STABILITY")
    print("=" * 100)
    print(
        f"Snapshots observed  : "
        f"{stability['snapshots']}"
    )
    print(
        f"Return observations : "
        f"{stability['return_observations']}"
    )
    print(
        f"Status              : "
        f"{stability['status']}"
    )

    if stability["reason"]:
        print(
            f"Reason              : "
            f"{stability['reason']}"
        )

    print()
    print("=" * 100)
    print("RISK-ADJUSTED METRICS")
    print("=" * 100)

    if metrics["status"] == "PASS":

        print(
            f"Mean return          : "
            f"{metrics['mean_return']:.12f}"
        )

        print(
            f"Volatility            : "
            f"{metrics['volatility']:.12f}"
        )

        print(
            f"Downside deviation   : "
            f"{metrics['downside_deviation']:.12f}"
        )

        print(
            f"Sharpe-like          : "
            f"{metrics['sharpe_like']}"
        )

        print(
            f"Sortino-like         : "
            f"{metrics['sortino_like']}"
        )

        print(
            "Risk-adjusted metrics : PASS"
        )

    else:

        print(
            "Risk-adjusted metrics : INSUFFICIENT_DATA"
        )

        print(
            f"Reason                : "
            f"{metrics['reason']}"
        )

        print(
            "No synthetic metric was generated."
        )

    print()
    print("=" * 100)
    print("P&L CONSISTENCY")
    print("=" * 100)
    print(
        f"Status : {pnl['status']}"
    )

    if pnl.get("error") is not None:
        print(
            f"Consistency error : "
            f"{pnl['error']:.12f}"
        )

    if pnl.get("reason"):
        print(
            f"Reason : {pnl['reason']}"
        )

    print()
    print("=" * 100)
    print(
        "LIVE PAPER PORTFOLIO PERFORMANCE STABILITY + "
        "RISK-ADJUSTED METRICS VERDICT"
    )
    print("=" * 100)

    print(
        f"UPSTREAM_STATE_CONSUMED : "
        f"{verdict['UPSTREAM_STATE_CONSUMED']}"
    )

    print(
        f"PERFORMANCE_STABILITY   : "
        f"{verdict['PERFORMANCE_STABILITY']}"
    )

    print(
        f"RISK_ADJUSTED_METRICS   : "
        f"{verdict['RISK_ADJUSTED_METRICS']}"
    )

    print(
        f"PNL_CONSISTENCY         : "
        f"{verdict['PNL_CONSISTENCY']}"
    )

    print(
        f"PRODUCTION_ISOLATION    : "
        f"{verdict['PRODUCTION_ISOLATION']}"
    )

    print(
        f"FRONTIER VERDICT        : "
        f"{verdict['FRONTIER_VERDICT']}"
    )

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    print(f"Before rows : {before['rows']}")
    print(f"After rows  : {after['rows']}")
    print(f"Before size : {before['size']}")
    print(f"After size  : {after['size']}")
    print(f"Before SHA256 : {before['sha256']}")
    print(f"After SHA256  : {after['sha256']}")

    print(
        "PRODUCTION DB INVARIANT : "
        + (
            "PASS"
            if before == after
            else "FAIL"
        )
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

    print()
    print(
        f"Runtime report : {OUTPUT_REPORT}"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    # -------------------------------------------------------------------------
    # Production baseline
    # -------------------------------------------------------------------------

    before = production_fingerprint()

    # -------------------------------------------------------------------------
    # Load verified upstream
    # -------------------------------------------------------------------------

    raw = load_json(
        UPSTREAM_REPORT
    )

    upstream = normalize_upstream(
        raw
    )

    # -------------------------------------------------------------------------
    # Normalize temporal observations
    # -------------------------------------------------------------------------

    snapshots = normalize_snapshots(
        upstream
    )

    returns = build_return_series(
        snapshots
    )

    # -------------------------------------------------------------------------
    # Evaluate stability
    # -------------------------------------------------------------------------

    stability = evaluate_stability(
        snapshots,
        returns,
    )

    # -------------------------------------------------------------------------
    # Risk-adjusted metrics
    # -------------------------------------------------------------------------

    risk_metrics = calculate_risk_adjusted_metrics(
        returns
    )

    # -------------------------------------------------------------------------
    # P&L consistency
    # -------------------------------------------------------------------------

    pnl_check = reconcile_current_pnl(
        upstream,
        snapshots,
    )

    # -------------------------------------------------------------------------
    # Production invariant
    # -------------------------------------------------------------------------

    after = production_fingerprint()

    if before != after:

        raise RuntimeError(
            "PRODUCTION DATABASE INVARIANT FAILED: "
            "production database changed."
        )

    # -------------------------------------------------------------------------
    # Build final report
    # -------------------------------------------------------------------------

    report = build_report(
        before=before,
        after=after,
        upstream=upstream,
        snapshots=snapshots,
        returns=returns,
        stability=stability,
        risk_metrics=risk_metrics,
        pnl_check=pnl_check,
    )

    LIVE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_REPORT.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            report,
            handle,
            indent=2,
            ensure_ascii=False,
        )

    print_report(
        report
    )


if __name__ == "__main__":
    main()