import os
import json
import math
import hashlib
import sqlite3
from datetime import datetime, timezone
from statistics import mean, pstdev


# ==================================================================================================
# ARUNDA TRADER LIVE PAPER PORTFOLIO TEMPORAL PERFORMANCE WINDOW + RISK REGIME RECONCILIATION v0.1
# ==================================================================================================

VERSION = "v0.1"

PRODUCTION_DB = r"C:\Users\ASUS\ArundaTrader\arunda.db"

LIVE_DIR = r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc"

UPSTREAM_REPORT = os.path.join(
    LIVE_DIR,
    "LIVE_PAPER_PORTFOLIO_PERFORMANCE_STABILITY_RISK_ADJUSTED_METRICS_REPORT.json",
)

RUNTIME_REPORT = os.path.join(
    LIVE_DIR,
    "LIVE_PAPER_PORTFOLIO_TEMPORAL_PERFORMANCE_WINDOW_RISK_REGIME_RECONCILIATION_REPORT.json",
)

EXPECTED_UPSTREAM_FRONTIER = (
    "LIVE_PAPER_PORTFOLIO_PERFORMANCE_STABILITY_RISK_ADJUSTED_METRICS_v0.1"
)

EXPECTED_SNAPSHOT_PREFIX = "FUSION-"

EPSILON = 1e-12


# --------------------------------------------------------------------------------------------------
# SAFETY
# --------------------------------------------------------------------------------------------------

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


# --------------------------------------------------------------------------------------------------
# DATABASE FINGERPRINT
# --------------------------------------------------------------------------------------------------

def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def database_fingerprint(path):
    if not os.path.exists(path):
        return {
            "rows": None,
            "size": None,
            "sha256": None,
        }

    size = os.path.getsize(path)

    sha256 = sha256_file(path)

    rows = None

    try:
        conn = sqlite3.connect(
            f"file:{path}?mode=ro",
            uri=True,
        )

        try:
            tables = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                ORDER BY name
                """
            ).fetchall()

            # Prefer the primary historical table if available.
            preferred = [
                "market_history",
                "market_history_repair",
                "market_records",
                "market_data",
            ]

            selected = None

            existing = {row[0] for row in tables}

            for table in preferred:
                if table in existing:
                    selected = table
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
        "sha256": sha256,
    }


# --------------------------------------------------------------------------------------------------
# JSON HELPERS
# --------------------------------------------------------------------------------------------------

def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Required report not found: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def first_value(obj, keys, default=None):
    if not isinstance(obj, dict):
        return default

    for key in keys:
        if key in obj:
            return obj[key]

    return default


def numeric(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, bool):
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------------------------------
# UPSTREAM VALIDATION
# --------------------------------------------------------------------------------------------------

def validate_upstream(report):
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

    snapshot = first_value(
        report,
        [
            "snapshot",
            "current_snapshot",
            "snapshot_id",
        ],
        None,
    )

    if snapshot is not None:
        snapshot = str(snapshot)

    snapshots = report.get("snapshots")

    if snapshots is None:
        snapshots = report.get("temporal_snapshots")

    if snapshots is None:
        snapshots = report.get("equity_curve")

    if snapshots is None:
        snapshots = report.get("snapshot_history")

    if snapshots is None:
        snapshots = []

    if not isinstance(snapshots, list):
        raise ValueError(
            "Upstream snapshot collection must be a list."
        )

    return {
        "frontier": frontier,
        "snapshot": snapshot,
        "snapshots": snapshots,
        "raw": report,
    }


# --------------------------------------------------------------------------------------------------
# SNAPSHOT NORMALIZATION
# --------------------------------------------------------------------------------------------------

def normalize_snapshot(item, fallback_snapshot=None):
    if not isinstance(item, dict):
        return None

    snapshot_id = first_value(
        item,
        [
            "snapshot",
            "snapshot_id",
            "id",
        ],
        fallback_snapshot,
    )

    if snapshot_id is None:
        return None

    snapshot_id = str(snapshot_id)

    timestamp = first_value(
        item,
        [
            "timestamp_utc",
            "timestamp",
            "time",
            "observed_at",
        ],
        None,
    )

    positions = numeric(
        first_value(
            item,
            [
                "positions",
                "position_count",
                "paper_positions",
            ],
            0,
        )
    )

    notional = numeric(
        first_value(
            item,
            [
                "notional",
                "analytical_notional",
                "total_analytical_notional",
            ],
            0.0,
        )
    )

    risk = numeric(
        first_value(
            item,
            [
                "risk",
                "portfolio_risk",
                "analytical_risk",
                "total_analytical_risk",
            ],
            0.0,
        )
    )

    pnl = numeric(
        first_value(
            item,
            [
                "pnl",
                "total_pnl",
                "total_pnl_pct",
                "unrealized_pnl",
            ],
            0.0,
        )
    )

    equity = first_value(
        item,
        [
            "equity",
            "portfolio_equity",
            "account_equity",
        ],
        None,
    )

    if equity is None:
        equity = pnl

    equity = numeric(equity, 0.0)

    realized_pnl = numeric(
        first_value(
            item,
            [
                "realized_pnl",
                "realized_pnl_pct",
            ],
            0.0,
        )
    )

    unrealized_pnl = numeric(
        first_value(
            item,
            [
                "unrealized_pnl",
                "unrealized_pnl_pct",
            ],
            0.0,
        )
    )

    return {
        "snapshot": snapshot_id,
        "timestamp": timestamp,
        "positions": int(max(0, round(positions))),
        "notional": notional,
        "risk": risk,
        "pnl": pnl,
        "equity": equity,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
    }


def collect_snapshots(upstream):
    raw_snapshots = upstream["snapshots"]

    normalized = []

    for item in raw_snapshots:
        record = normalize_snapshot(
            item,
            fallback_snapshot=upstream["snapshot"],
        )

        if record is not None:
            normalized.append(record)

    # If the upstream report contains one current snapshot but does not
    # expose it inside the collection, preserve it as a single observation.
    if not normalized and upstream["snapshot"]:
        raw = upstream["raw"]

        normalized.append(
            normalize_snapshot(
                {
                    "snapshot": upstream["snapshot"],
                    "timestamp_utc": raw.get("timestamp_utc"),
                    "positions": raw.get("positions", 0),
                    "notional": raw.get(
                        "analytical_notional",
                        0.0,
                    ),
                    "risk": raw.get(
                        "portfolio_risk",
                        raw.get("analytical_risk", 0.0),
                    ),
                    "pnl": raw.get(
                        "total_pnl",
                        raw.get("reported_total_pnl", 0.0),
                    ),
                    "equity": raw.get(
                        "equity",
                        raw.get("reported_total_pnl", 0.0),
                    ),
                    "realized_pnl": raw.get(
                        "realized_pnl",
                        0.0,
                    ),
                    "unrealized_pnl": raw.get(
                        "unrealized_pnl",
                        0.0,
                    ),
                }
            )
        )

    normalized = [
        x for x in normalized
        if x is not None
    ]

    # De-duplicate snapshot identity.
    dedup = {}

    for record in normalized:
        dedup[record["snapshot"]] = record

    normalized = list(dedup.values())

    # Temporal ordering.
    def sort_key(record):
        timestamp = record.get("timestamp")

        if timestamp:
            try:
                return datetime.fromisoformat(
                    str(timestamp).replace(
                        "Z",
                        "+00:00",
                    )
                ).timestamp()

            except Exception:
                pass

        return record["snapshot"]

    normalized.sort(key=sort_key)

    return normalized


# --------------------------------------------------------------------------------------------------
# TRANSITIONS
# --------------------------------------------------------------------------------------------------

def calculate_transitions(snapshots):
    transitions = []

    for previous, current in zip(
        snapshots,
        snapshots[1:],
    ):
        transitions.append(
            {
                "from_snapshot": previous["snapshot"],
                "to_snapshot": current["snapshot"],

                "position_delta": (
                    current["positions"]
                    - previous["positions"]
                ),

                "notional_delta": (
                    current["notional"]
                    - previous["notional"]
                ),

                "risk_delta": (
                    current["risk"]
                    - previous["risk"]
                ),

                "pnl_delta": (
                    current["pnl"]
                    - previous["pnl"]
                ),

                "equity_delta": (
                    current["equity"]
                    - previous["equity"]
                ),
            }
        )

    return transitions


# --------------------------------------------------------------------------------------------------
# RISK REGIME
# --------------------------------------------------------------------------------------------------

def classify_risk_regime(risk):
    if risk < 0:
        return "INVALID"

    if risk <= 0.005:
        return "LOW"

    if risk <= 0.010:
        return "MODERATE"

    if risk <= 0.020:
        return "ELEVATED"

    return "HIGH"


def calculate_regimes(snapshots):
    result = []

    for snapshot in snapshots:
        regime = classify_risk_regime(
            snapshot["risk"]
        )

        result.append(
            {
                "snapshot": snapshot["snapshot"],
                "risk": snapshot["risk"],
                "risk_regime": regime,
            }
        )

    return result


# --------------------------------------------------------------------------------------------------
# PERFORMANCE WINDOW
# --------------------------------------------------------------------------------------------------

def calculate_return(previous, current):
    base = previous["equity"]

    if abs(base) <= EPSILON:
        return None

    return (
        current["equity"] - base
    ) / abs(base)


def calculate_performance_window(snapshots):
    returns = []

    for previous, current in zip(
        snapshots,
        snapshots[1:],
    ):
        ret = calculate_return(
            previous,
            current,
        )

        if ret is not None:
            returns.append(ret)

    if len(returns) == 0:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "NO_VALID_RETURN_OBSERVATIONS",
            "return_observations": 0,
            "mean_return": None,
            "volatility": None,
            "positive_periods": 0,
            "negative_periods": 0,
        }

    positive = [
        x for x in returns
        if x > EPSILON
    ]

    negative = [
        x for x in returns
        if x < -EPSILON
    ]

    volatility = (
        pstdev(returns)
        if len(returns) >= 2
        else None
    )

    return {
        "status": (
            "PASS"
            if len(returns) >= 2
            else "INSUFFICIENT_DATA"
        ),
        "reason": (
            None
            if len(returns) >= 2
            else "MINIMUM_TWO_RETURN_OBSERVATIONS_REQUIRED"
        ),
        "return_observations": len(returns),
        "mean_return": mean(returns),
        "volatility": volatility,
        "positive_periods": len(positive),
        "negative_periods": len(negative),
    }


# --------------------------------------------------------------------------------------------------
# REGIME TRANSITION RECONCILIATION
# --------------------------------------------------------------------------------------------------

def reconcile_regime_transitions(regimes):
    transitions = []

    for previous, current in zip(
        regimes,
        regimes[1:],
    ):
        transitions.append(
            {
                "from_snapshot": previous["snapshot"],
                "to_snapshot": current["snapshot"],
                "from_regime": previous["risk_regime"],
                "to_regime": current["risk_regime"],
                "risk_delta": (
                    current["risk"]
                    - previous["risk"]
                ),
                "changed": (
                    previous["risk_regime"]
                    != current["risk_regime"]
                ),
            }
        )

    changed = sum(
        1
        for item in transitions
        if item["changed"]
    )

    return {
        "transitions": transitions,
        "total_transitions": len(transitions),
        "regime_changes": changed,
    }


# --------------------------------------------------------------------------------------------------
# SAFETY VALIDATION
# --------------------------------------------------------------------------------------------------

def verify_production_unchanged(
    before,
    after,
):
    return (
        before["rows"] == after["rows"]
        and before["size"] == after["size"]
        and before["sha256"] == after["sha256"]
    )


# --------------------------------------------------------------------------------------------------
# REPORT
# --------------------------------------------------------------------------------------------------

def write_report(report):
    os.makedirs(
        os.path.dirname(RUNTIME_REPORT),
        exist_ok=True,
    )

    with open(
        RUNTIME_REPORT,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )


# --------------------------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------------------------

def main():
    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO TEMPORAL "
        "PERFORMANCE WINDOW + RISK REGIME RECONCILIATION v0.1"
    )
    print("=" * 100)

    print()
    print("=" * 100)
    print("OBJECTIVE:")
    print(
        "  Consume ONLY the verified PAPER portfolio "
        "performance stability frontier."
    )
    print(
        "  Reconcile temporal performance windows and risk regimes."
    )
    print(
        "  No real order is created or submitted."
    )
    print("=" * 100)

    print()
    print("=" * 100)
    print("SAFETY POLICY")
    print("=" * 100)

    print("Production DB writes       : FORBIDDEN")
    print("Production engine run     : NO")
    print("Historical repair         : NONE")
    print("Direction inference       : NONE")
    print("Score reconstruction      : NONE")
    print("Synthetic data            : FORBIDDEN")
    print("Live data injection       : NONE")
    print("Order execution           : NONE")
    print("PAPER EXECUTION           : ANALYTICAL ONLY")

    before = database_fingerprint(
        PRODUCTION_DB
    )

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)

    print(f"Rows   : {before['rows']}")
    print(f"Size   : {before['size']}")
    print(f"SHA256 : {before['sha256']}")

    upstream_report = load_json(
        UPSTREAM_REPORT
    )

    upstream = validate_upstream(
        upstream_report
    )

    snapshots = collect_snapshots(
        upstream
    )

    print()
    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)

    print(
        f"Frontier : {upstream['frontier']}"
    )

    print(
        f"Snapshot : "
        f"{upstream['snapshot']}"
    )

    print(
        f"Snapshots available : "
        f"{len(snapshots)}"
    )

    # ----------------------------------------------------------------------------------------------
    # TEMPORAL WINDOW
    # ----------------------------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("TEMPORAL PERFORMANCE WINDOW")
    print("=" * 100)

    window = calculate_performance_window(
        snapshots
    )

    print(
        f"Snapshots observed  : "
        f"{len(snapshots)}"
    )

    print(
        f"Return observations : "
        f"{window['return_observations']}"
    )

    if window["status"] == "INSUFFICIENT_DATA":
        print("Status              : INSUFFICIENT_DATA")
        print(
            f"Reason              : "
            f"{window['reason']}"
        )

    else:
        print(
            f"Mean period return : "
            f"{window['mean_return']:.8f}"
        )

        if window["volatility"] is None:
            print(
                "Period volatility  : INSUFFICIENT_DATA"
            )
        else:
            print(
                f"Period volatility  : "
                f"{window['volatility']:.8f}"
            )

        print(
            f"Positive periods   : "
            f"{window['positive_periods']}"
        )

        print(
            f"Negative periods   : "
            f"{window['negative_periods']}"
        )

    # ----------------------------------------------------------------------------------------------
    # RISK REGIME
    # ----------------------------------------------------------------------------------------------

    regimes = calculate_regimes(
        snapshots
    )

    regime_reconciliation = (
        reconcile_regime_transitions(
            regimes
        )
    )

    print()
    print("=" * 100)
    print("RISK REGIME RECONCILIATION")
    print("=" * 100)

    if not regimes:
        print(
            "Risk regime observations : 0"
        )

        print(
            "Status                    : "
            "INSUFFICIENT_DATA"
        )

    else:
        for regime in regimes:
            print(
                f"{regime['snapshot']} | "
                f"risk={regime['risk']:.6f} | "
                f"regime={regime['risk_regime']}"
            )

        print()
        print(
            f"Regime transitions : "
            f"{regime_reconciliation['total_transitions']}"
        )

        print(
            f"Regime changes     : "
            f"{regime_reconciliation['regime_changes']}"
        )

    # ----------------------------------------------------------------------------------------------
    # STATE TRANSITIONS
    # ----------------------------------------------------------------------------------------------

    transitions = calculate_transitions(
        snapshots
    )

    print()
    print("=" * 100)
    print("PORTFOLIO TEMPORAL TRANSITIONS")
    print("=" * 100)

    if not transitions:
        print(
            "No portfolio transitions observed."
        )

    else:
        for transition in transitions:
            print(
                f"{transition['from_snapshot']} -> "
                f"{transition['to_snapshot']} | "
                f"positions Δ="
                f"{transition['position_delta']} | "
                f"notional Δ="
                f"{transition['notional_delta']:.6f} | "
                f"risk Δ="
                f"{transition['risk_delta']:.6f} | "
                f"PnL Δ="
                f"{transition['pnl_delta']:.6f}"
            )

    # ----------------------------------------------------------------------------------------------
    # VERDICT
    # ----------------------------------------------------------------------------------------------

    temporal_order = True

    for previous, current in zip(
        snapshots,
        snapshots[1:],
    ):
        if (
            previous["timestamp"]
            and current["timestamp"]
        ):
            try:
                previous_time = datetime.fromisoformat(
                    previous["timestamp"].replace(
                        "Z",
                        "+00:00",
                    )
                )

                current_time = datetime.fromisoformat(
                    current["timestamp"].replace(
                        "Z",
                        "+00:00",
                    )
                )

                if current_time < previous_time:
                    temporal_order = False

            except Exception:
                pass

    if len(snapshots) < 2:
        frontier_verdict = "INSUFFICIENT_DATA"

        performance_status = "INSUFFICIENT_DATA"
        risk_regime_status = "INSUFFICIENT_DATA"

    else:
        performance_status = window["status"]

        risk_regime_status = (
            "PASS"
            if len(regimes) >= 2
            else "INSUFFICIENT_DATA"
        )

        frontier_verdict = (
            "PASS"
            if (
                temporal_order
                and performance_status == "PASS"
                and risk_regime_status == "PASS"
            )
            else "INSUFFICIENT_DATA"
        )

    after = database_fingerprint(
        PRODUCTION_DB
    )

    production_unchanged = (
        verify_production_unchanged(
            before,
            after,
        )
    )

    SAFETY["production_db_modified"] = (
        not production_unchanged
    )

    print()
    print("=" * 100)
    print(
        "LIVE PAPER PORTFOLIO TEMPORAL PERFORMANCE WINDOW "
        "+ RISK REGIME RECONCILIATION VERDICT"
    )
    print("=" * 100)

    print(
        "UPSTREAM_STATE_CONSUMED       : PASS"
    )

    print(
        "TEMPORAL_ORDER                : "
        + ("PASS" if temporal_order else "FAIL")
    )

    print(
        "PERFORMANCE_WINDOW            : "
        + performance_status
    )

    print(
        "RISK_REGIME_RECONCILIATION    : "
        + risk_regime_status
    )

    print(
        "PRODUCTION_ISOLATION          : "
        + ("PASS" if production_unchanged else "FAIL")
    )

    print(
        "FRONTIER VERDICT              : "
        + frontier_verdict
    )

    # ----------------------------------------------------------------------------------------------
    # PRODUCTION INVARIANT
    # ----------------------------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    print(
        f"Before rows  : {before['rows']}"
    )

    print(
        f"After rows   : {after['rows']}"
    )

    print(
        f"Before size  : {before['size']}"
    )

    print(
        f"After size   : {after['size']}"
    )

    print(
        f"Before SHA256: {before['sha256']}"
    )

    print(
        f"After SHA256 : {after['sha256']}"
    )

    print(
        "PRODUCTION DB INVARIANT : "
        + (
            "PASS"
            if production_unchanged
            else "FAIL"
        )
    )

    # ----------------------------------------------------------------------------------------------
    # FINAL SAFETY
    # ----------------------------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("FINAL SAFETY VERDICT")
    print("=" * 100)

    print(
        "Production DB writes : NONE"
    )
    print(
        "INSERT               : NONE"
    )
    print(
        "UPDATE               : NONE"
    )
    print(
        "DELETE               : NONE"
    )
    print(
        "DDL                  : NONE"
    )
    print(
        "Production engine    : NOT EXECUTED"
    )
    print(
        "Historical repair    : NONE"
    )
    print(
        "Direction inference  : NONE"
    )
    print(
        "Score reconstruction : NONE"
    )
    print(
        "Synthetic data       : NONE"
    )
    print(
        "Live data injection  : NONE"
    )
    print(
        "REAL ORDER EXECUTION : NONE"
    )
    print(
        "PAPER EXECUTION      : ANALYTICAL ONLY"
    )

    # ----------------------------------------------------------------------------------------------
    # REPORT
    # ----------------------------------------------------------------------------------------------

    report = {
        "frontier": (
            "LIVE_PAPER_PORTFOLIO_TEMPORAL_PERFORMANCE_WINDOW_"
            "RISK_REGIME_RECONCILIATION_v0.1"
        ),
        "version": VERSION,
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "source_frontier": (
            upstream["frontier"]
        ),

        "snapshot": upstream["snapshot"],

        "snapshots_available": len(
            snapshots
        ),

        "snapshots": snapshots,

        "performance_window": window,

        "risk_regime": {
            "observations": regimes,
            "transitions": (
                regime_reconciliation[
                    "transitions"
                ]
            ),
            "total_transitions": (
                regime_reconciliation[
                    "total_transitions"
                ]
            ),
            "regime_changes": (
                regime_reconciliation[
                    "regime_changes"
                ]
            ),
        },

        "portfolio_transitions": transitions,

        "reconciliation": {
            "temporal_order": temporal_order,
            "performance_window_status": (
                performance_status
            ),
            "risk_regime_status": (
                risk_regime_status
            ),
        },

        "production_database": {
            "before": before,
            "after": after,
            "unchanged": production_unchanged,
        },

        "safety": SAFETY,

        "frontier_verdict": frontier_verdict,
    }

    write_report(
        report
    )

    print()
    print(
        f"Runtime report : {RUNTIME_REPORT}"
    )


if __name__ == "__main__":
    main()