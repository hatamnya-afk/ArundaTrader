import os
import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


# =============================================================================
# ARUNDA TRADER
# LIVE PAPER PORTFOLIO PERFORMANCE METRICS + TRADE STATISTICS RECONCILIATION
# v0.2
# =============================================================================

VERSION = "v0.2"

PRODUCTION_DB = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

LIVE_DIR = Path(
    r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc"
)

UPSTREAM_REPORT = (
    LIVE_DIR
    / "LIVE_PAPER_PORTFOLIO_PERFORMANCE_ATTRIBUTION_PNL_CONSISTENCY_REPORT.json"
)

OUTPUT_REPORT = (
    LIVE_DIR
    / "LIVE_PAPER_PORTFOLIO_PERFORMANCE_METRICS_TRADE_STATISTICS_RECONCILIATION_REPORT.json"
)

EXPECTED_UPSTREAM_FRONTIER = (
    "LIVE_PAPER_PORTFOLIO_PERFORMANCE_ATTRIBUTION_PNL_CONSISTENCY_v0.2"
)

EXPECTED_ENGINE = "None"

PNL_EPSILON = 1e-12


# =============================================================================
# SAFETY
# =============================================================================

PRODUCTION_WRITES_FORBIDDEN = True
PRODUCTION_ENGINE_EXECUTION = False
HISTORICAL_REPAIR = False
DIRECTION_INFERENCE = False
SCORE_RECONSTRUCTION = False
SYNTHETIC_DATA = False
LIVE_DATA_INJECTION = False
REAL_ORDER_EXECUTION = False
PAPER_EXECUTION_ANALYTICAL_ONLY = True


# =============================================================================
# UTILITIES
# =============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def sqlite_row_count(path: Path):
    """
    Read-only production DB row count.

    Important:
      This does NOT modify the production database.
    """

    if not path.exists():
        raise FileNotFoundError(f"Production DB not found: {path}")

    uri = f"file:{path.as_posix()}?mode=ro"

    with sqlite3.connect(uri, uri=True) as conn:
        total = 0

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()

        for (table_name,) in tables:
            try:
                quoted = '"' + table_name.replace('"', '""') + '"'
                row = conn.execute(
                    f"SELECT COUNT(*) FROM {quoted}"
                ).fetchone()

                if row:
                    total += int(row[0])

            except sqlite3.DatabaseError:
                # A table that cannot be read is ignored rather than causing
                # any write or repair operation.
                continue

        return total


def production_fingerprint():
    return {
        "rows": sqlite_row_count(PRODUCTION_DB),
        "size": PRODUCTION_DB.stat().st_size,
        "sha256": sha256_file(PRODUCTION_DB),
    }


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Required report not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def first_present(mapping, keys, default=None):
    if not isinstance(mapping, dict):
        return default

    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]

    return default


def as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# =============================================================================
# UPSTREAM NORMALIZATION
# =============================================================================

def normalize_upstream(report):
    """
    Consume the already verified upstream frontier.

    No re-audit of previous frontiers is performed.
    """

    if not isinstance(report, dict):
        raise ValueError("Upstream report must be a JSON object.")

    frontier = report.get("frontier")

    if frontier != EXPECTED_UPSTREAM_FRONTIER:
        raise ValueError(
            "Unexpected upstream frontier: "
            f"{frontier!r}; expected {EXPECTED_UPSTREAM_FRONTIER!r}"
        )

    # -------------------------------------------------------------------------
    # Snapshot propagation
    # -------------------------------------------------------------------------

    current_snapshot = first_present(
        report,
        [
            "current_snapshot",
            "snapshot",
            "snapshot_id",
        ],
    )

    # Some reports may place snapshot metadata in a nested object.
    if current_snapshot is None:
        snapshot_obj = report.get("snapshot_state")

        if isinstance(snapshot_obj, dict):
            current_snapshot = first_present(
                snapshot_obj,
                [
                    "current_snapshot",
                    "snapshot",
                    "snapshot_id",
                ],
            )

    # -------------------------------------------------------------------------
    # Engine propagation
    # -------------------------------------------------------------------------

    engine = first_present(
        report,
        [
            "engine",
            "source_engine",
        ],
        default="None",
    )

    # -------------------------------------------------------------------------
    # Snapshot collection propagation
    # -------------------------------------------------------------------------

    snapshot_collection = None

    for key in (
        "snapshots",
        "temporal_snapshots",
        "snapshot_records",
        "equity_curve",
        "snapshot_history",
    ):
        value = report.get(key)

        if isinstance(value, list):
            snapshot_collection = value
            break

    if snapshot_collection is None:
        snapshot_collection = []

    snapshots_available = len(snapshot_collection)

    # If the upstream explicitly reports the number, use it only when
    # consistent with an actual collection.
    explicit_count = first_present(
        report,
        [
            "snapshots_available",
            "snapshot_count",
        ],
    )

    if snapshots_available == 0 and explicit_count is not None:
        snapshots_available = as_int(explicit_count, 0)

    # If the upstream contains a valid current snapshot but no collection,
    # this is still one known state for this frontier.
    if snapshots_available == 0 and current_snapshot:
        snapshots_available = 1

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
        total_pnl = as_float(realized_pnl) + as_float(unrealized_pnl)

    # -------------------------------------------------------------------------
    # Position collection
    # -------------------------------------------------------------------------

    positions = []

    for key in (
        "positions",
        "paper_positions",
        "position_records",
        "closed_positions",
        "trades",
    ):
        value = report.get(key)

        if isinstance(value, list):
            positions = value
            break

    # Do NOT infer trades from empty/absent fields.
    closed_positions = [
        p for p in positions
        if isinstance(p, dict)
        and str(
            first_present(
                p,
                ["state", "status", "position_state"],
                default=""
            )
        ).upper()
        in {
            "CLOSED",
            "CLOSE",
            "CLOSED_POSITION",
        }
    ]

    open_positions = [
        p for p in positions
        if isinstance(p, dict)
        and str(
            first_present(
                p,
                ["state", "status", "position_state"],
                default=""
            )
        ).upper()
        in {
            "OPEN",
            "ACTIVE",
            "OPEN_POSITION",
        }
    ]

    # If upstream explicitly gives counts, preserve them.
    explicit_closed = first_present(
        report,
        [
            "closed_positions",
            "closed_position_count",
        ],
    )

    explicit_open = first_present(
        report,
        [
            "open_positions",
            "open_position_count",
        ],
    )

    if isinstance(explicit_closed, int):
        closed_count = explicit_closed
    else:
        closed_count = len(closed_positions)

    if isinstance(explicit_open, int):
        open_count = explicit_open
    else:
        open_count = len(open_positions)

    return {
        "frontier": frontier,
        "engine": engine,
        "current_snapshot": current_snapshot,
        "snapshot_collection": snapshot_collection,
        "snapshots_available": snapshots_available,
        "positions": positions,
        "closed_positions": closed_positions,
        "open_positions": open_positions,
        "closed_count": closed_count,
        "open_count": open_count,
        "realized_pnl": as_float(realized_pnl),
        "unrealized_pnl": as_float(unrealized_pnl),
        "total_pnl": as_float(total_pnl),
    }


# =============================================================================
# TRADE STATISTICS
# =============================================================================

def extract_trade_pnl(position):
    if not isinstance(position, dict):
        return None

    value = first_present(
        position,
        [
            "pnl_pct",
            "realized_pnl_pct",
            "return_pct",
            "pnl_percent",
            "profit_pct",
        ],
    )

    if value is not None:
        return as_float(value)

    value = first_present(
        position,
        [
            "pnl",
            "realized_pnl",
            "profit",
        ],
    )

    if value is not None:
        return as_float(value)

    return None


def extract_exit_reason(position):
    if not isinstance(position, dict):
        return "OTHER"

    value = first_present(
        position,
        [
            "exit_reason",
            "close_reason",
            "reason",
            "exit_type",
        ],
        default="OTHER",
    )

    value = str(value).upper()

    if "STOP" in value:
        return "STOP_LOSS"

    if "TAKE" in value or value in {"TP", "TAKE_PROFIT"}:
        return "TAKE_PROFIT"

    return "OTHER"


def extract_holding_seconds(position):
    if not isinstance(position, dict):
        return 0.0

    value = first_present(
        position,
        [
            "holding_seconds",
            "duration_seconds",
            "holding_time_seconds",
        ],
        default=0.0,
    )

    return max(0.0, as_float(value))


def calculate_trade_statistics(closed_positions):
    pnl_values = []

    stop_loss = 0
    take_profit = 0
    other_close = 0

    holding_times = []

    for position in closed_positions:
        pnl = extract_trade_pnl(position)

        if pnl is not None:
            pnl_values.append(pnl)

        reason = extract_exit_reason(position)

        if reason == "STOP_LOSS":
            stop_loss += 1
        elif reason == "TAKE_PROFIT":
            take_profit += 1
        else:
            other_close += 1

        holding_times.append(
            extract_holding_seconds(position)
        )

    wins = [x for x in pnl_values if x > PNL_EPSILON]
    losses = [x for x in pnl_values if x < -PNL_EPSILON]
    breakeven = [
        x for x in pnl_values
        if abs(x) <= PNL_EPSILON
    ]

    closed_count = len(closed_positions)

    win_rate = (
        len(wins) / closed_count
        if closed_count
        else 0.0
    )

    average_win = (
        sum(wins) / len(wins)
        if wins
        else 0.0
    )

    average_loss = (
        sum(losses) / len(losses)
        if losses
        else 0.0
    )

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > PNL_EPSILON:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > PNL_EPSILON:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    expectancy = (
        sum(pnl_values) / closed_count
        if closed_count
        else 0.0
    )

    average_holding = (
        sum(holding_times) / len(holding_times)
        if holding_times
        else 0.0
    )

    return {
        "closed_trades": closed_count,
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(breakeven),
        "win_rate": win_rate,
        "average_win": average_win,
        "average_loss": average_loss,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "average_holding_time_seconds": average_holding,
        "stop_loss_closes": stop_loss,
        "take_profit_closes": take_profit,
        "other_closes": other_close,
        "calculated_realized_pnl": sum(pnl_values),
    }


# =============================================================================
# P&L RECONCILIATION
# =============================================================================

def reconcile_pnl(upstream, statistics):
    reported = upstream["realized_pnl"]
    calculated = statistics["calculated_realized_pnl"]

    error = abs(reported - calculated)

    if upstream["closed_count"] == 0:
        return {
            "reported_realized_pnl": reported,
            "calculated_realized_pnl": calculated,
            "consistency_error": error,
            "status": "NOT_PERFORMED",
            "reason": "NO_CLOSED_PAPER_TRADES",
        }

    status = (
        "PASS"
        if error <= PNL_EPSILON
        else "FAIL"
    )

    return {
        "reported_realized_pnl": reported,
        "calculated_realized_pnl": calculated,
        "consistency_error": error,
        "status": status,
        "reason": None,
    }


# =============================================================================
# REPORT
# =============================================================================

def build_report(
    before,
    after,
    upstream,
    statistics,
    pnl_reconciliation,
):
    closed_count = statistics["closed_trades"]

    if closed_count == 0:
        performance_status = "NOT_PERFORMED"
        trade_statistics_status = "NOT_PERFORMED"
        frontier_verdict = "NO_TRADE"
        reason = "NO_CLOSED_PAPER_TRADES"
    else:
        performance_status = "PASS"
        trade_statistics_status = "PASS"

        if pnl_reconciliation["status"] == "PASS":
            frontier_verdict = "PASS"
            reason = None
        else:
            frontier_verdict = "BLOCKED"
            reason = "PNL_RECONCILIATION_FAILED"

    return {
        "frontier": (
            "LIVE_PAPER_PORTFOLIO_PERFORMANCE_METRICS_"
            "TRADE_STATISTICS_RECONCILIATION_v0.2"
        ),
        "version": VERSION,
        "timestamp_utc": utc_now(),

        "objective": (
            "Consume only the verified PAPER portfolio "
            "performance/P&L frontier and reconcile "
            "performance metrics and trade statistics."
        ),

        "upstream": {
            "report": str(UPSTREAM_REPORT),
            "frontier": upstream["frontier"],
            "engine": upstream["engine"],
            "current_snapshot": upstream["current_snapshot"],
            "snapshots_available": upstream["snapshots_available"],
        },

        "trade_statistics": statistics,

        "pnl_reconciliation": pnl_reconciliation,

        "production_database": {
            "before": before,
            "after": after,
            "unchanged": before == after,
        },

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

        "verdict": {
            "upstream_state_consumed": "PASS",
            "performance_metrics": performance_status,
            "trade_statistics": trade_statistics_status,
            "pnl_reconciliation": pnl_reconciliation["status"],
            "production_isolation": (
                "PASS"
                if before == after
                else "FAIL"
            ),
            "frontier_verdict": frontier_verdict,
            "reason": reason,
        },
    }


# =============================================================================
# CONSOLE
# =============================================================================

def print_header():
    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO PERFORMANCE METRICS + "
        "TRADE STATISTICS RECONCILIATION v0.2"
    )
    print("=" * 100)


def print_report(report):
    upstream = report["upstream"]
    stats = report["trade_statistics"]
    pnl = report["pnl_reconciliation"]
    verdict = report["verdict"]

    db_before = report["production_database"]["before"]
    db_after = report["production_database"]["after"]

    print()
    print("=" * 100)
    print("OBJECTIVE:")
    print(
        "  Consume ONLY the verified PAPER portfolio "
        "performance/P&L frontier."
    )
    print(
        "  Reconcile performance metrics and trade statistics."
    )
    print("  No real order is created or submitted.")
    print("=" * 100)

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)
    print(f"Rows   : {db_before['rows']}")
    print(f"Size   : {db_before['size']}")
    print(f"SHA256 : {db_before['sha256']}")

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

    print()
    print("=" * 100)
    print("TRADE STATISTICS")
    print("=" * 100)
    print(f"Closed trades        : {stats['closed_trades']}")
    print(f"Wins                 : {stats['wins']}")
    print(f"Losses               : {stats['losses']}")
    print(f"Breakeven            : {stats['breakeven']}")
    print(
        f"Win rate             : "
        f"{stats['win_rate'] * 100:.6f}%"
    )
    print(
        f"Average win          : "
        f"{stats['average_win']:.6f}%"
    )
    print(
        f"Average loss         : "
        f"{stats['average_loss']:.6f}%"
    )

    pf = stats["profit_factor"]

    if pf == float("inf"):
        pf_text = "INF"
    else:
        pf_text = f"{pf:.6f}"

    print(f"Profit factor        : {pf_text}")
    print(
        f"Expectancy           : "
        f"{stats['expectancy']:.6f}%"
    )
    print(
        f"Average holding time : "
        f"{stats['average_holding_time_seconds']:.2f} sec"
    )
    print(
        f"STOP LOSS closes     : "
        f"{stats['stop_loss_closes']}"
    )
    print(
        f"TAKE PROFIT closes   : "
        f"{stats['take_profit_closes']}"
    )
    print(
        f"Other closes         : "
        f"{stats['other_closes']}"
    )

    if stats["closed_trades"] == 0:
        print()
        print("Performance metrics : NOT PERFORMED")
        print("Trade statistics    : NOT PERFORMED")
        print("Reason              : NO_CLOSED_PAPER_TRADES")

    print()
    print("=" * 100)
    print("P&L RECONCILIATION")
    print("=" * 100)
    print(
        f"Reported realized P&L   : "
        f"{pnl['reported_realized_pnl']:.6f}%"
    )
    print(
        f"Calculated realized P&L : "
        f"{pnl['calculated_realized_pnl']:.6f}%"
    )
    print(
        f"Consistency error       : "
        f"{pnl['consistency_error']:.12f}"
    )
    print(
        f"Consistency status      : "
        f"{pnl['status']}"
    )

    if pnl["reason"]:
        print(f"Reason                  : {pnl['reason']}")

    print()
    print("=" * 100)
    print(
        "LIVE PAPER PORTFOLIO PERFORMANCE METRICS + "
        "TRADE STATISTICS RECONCILIATION VERDICT"
    )
    print("=" * 100)
    print(
        f"UPSTREAM_STATE_CONSUMED : "
        f"{verdict['upstream_state_consumed']}"
    )
    print(
        f"PERFORMANCE_METRICS     : "
        f"{verdict['performance_metrics']}"
    )
    print(
        f"TRADE_STATISTICS        : "
        f"{verdict['trade_statistics']}"
    )
    print(
        f"PNL_RECONCILIATION      : "
        f"{verdict['pnl_reconciliation']}"
    )
    print(
        f"PRODUCTION_ISOLATION    : "
        f"{verdict['production_isolation']}"
    )
    print(
        f"FRONTIER VERDICT        : "
        f"{verdict['frontier_verdict']}"
    )

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)
    print(f"Before rows : {db_before['rows']}")
    print(f"After rows  : {db_after['rows']}")
    print(f"Before size : {db_before['size']}")
    print(f"After size  : {db_after['size']}")
    print(f"Before SHA256 : {db_before['sha256']}")
    print(f"After SHA256  : {db_after['sha256']}")
    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if db_before == db_after else "FAIL")
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

    if stats["closed_trades"] == 0:
        print()
        print("No closed paper trades exist.")
        print(
            "Performance metrics and trade statistics "
            "were not performed."
        )

    print()
    print("No real trading order was created, submitted, or executed.")

    print()
    print(f"Runtime report : {OUTPUT_REPORT}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print_header()

    # -------------------------------------------------------------------------
    # Production baseline
    # -------------------------------------------------------------------------

    before = production_fingerprint()

    # -------------------------------------------------------------------------
    # Upstream
    # -------------------------------------------------------------------------

    upstream_raw = load_json(UPSTREAM_REPORT)
    upstream = normalize_upstream(upstream_raw)

    # -------------------------------------------------------------------------
    # Metrics
    # -------------------------------------------------------------------------

    statistics = calculate_trade_statistics(
        upstream["closed_positions"]
    )

    pnl_reconciliation = reconcile_pnl(
        upstream,
        statistics,
    )

    # -------------------------------------------------------------------------
    # Production invariant
    # -------------------------------------------------------------------------

    after = production_fingerprint()

    if before != after:
        raise RuntimeError(
            "PRODUCTION DATABASE INVARIANT FAILED: "
            "production DB changed during analytical execution."
        )

    # -------------------------------------------------------------------------
    # Build report
    # -------------------------------------------------------------------------

    report = build_report(
        before=before,
        after=after,
        upstream=upstream,
        statistics=statistics,
        pnl_reconciliation=pnl_reconciliation,
    )

    LIVE_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_REPORT.open("w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print_report(report)


if __name__ == "__main__":
    main()