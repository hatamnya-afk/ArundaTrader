import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


VERSION = "v0.2"
FRONTIER = "LIVE_PAPER_PORTFOLIO_RISK_LIMITS_CIRCUIT_BREAKER_GATE_v0.2"

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
CAPTURE_DIR = Path(
    r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc"
)

PRODUCTION_DB = BASE_DIR / "arunda.db"

UPSTREAM_REPORT = (
    CAPTURE_DIR
    / "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_REPORT.json"
)

OUTPUT_REPORT = (
    CAPTURE_DIR
    / "LIVE_PAPER_PORTFOLIO_RISK_LIMITS_CIRCUIT_BREAKER_GATE_REPORT.json"
)

# ---------------------------------------------------------------------------
# ANALYTICAL RISK LIMITS
# ---------------------------------------------------------------------------

MAX_PORTFOLIO_RISK = 0.02
MAX_ANALYTICAL_NOTIONAL = 1.00
MAX_ASSET_CONCENTRATION = 0.50
MAX_UNREALIZED_LOSS = 0.02

CIRCUIT_BREAKER_ON_LOSS = True
CIRCUIT_BREAKER_ON_RISK = True
CIRCUIT_BREAKER_ON_NOTIONAL = True
CIRCUIT_BREAKER_ON_CONCENTRATION = True

# ---------------------------------------------------------------------------
# SAFETY
# ---------------------------------------------------------------------------

WRITE_FORBIDDEN = True
REAL_ORDER_EXECUTION = False
PRODUCTION_ENGINE_EXECUTED = False
HISTORICAL_REPAIR = False
DIRECTION_INFERENCE = False
SCORE_RECONSTRUCTION = False
SYNTHETIC_DATA = False
LIVE_DATA_INJECTION = False


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def production_baseline():
    stat = PRODUCTION_DB.stat()

    return {
        "rows": get_production_row_count(),
        "size": stat.st_size,
        "sha256": sha256_file(PRODUCTION_DB),
    }


def get_production_row_count():
    import sqlite3

    conn = sqlite3.connect(str(PRODUCTION_DB))

    try:
        tables = [
            "market_records",
            "market_data",
            "market_history",
            "market_universe",
            "market_state",
        ]

        counts = {}

        for table in tables:
            try:
                row = conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()

                counts[table] = int(row[0])
            except Exception:
                continue

        if counts:
            return max(counts.values())

        return 0

    finally:
        conn.close()


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Report not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Upstream report root must be a JSON object.")

    return data


# ---------------------------------------------------------------------------
# UPSTREAM NORMALIZATION
# ---------------------------------------------------------------------------

def first_present(data, *keys, default=None):
    for key in keys:
        if key in data:
            return data[key]
    return default


def numeric(value, default=0.0):
    if value is None:
        return default

    if isinstance(value, bool):
        return float(value)

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def integer(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def extract_snapshot(report):
    snapshot = first_present(
        report,
        "snapshot",
        "snapshot_id",
        "current_snapshot",
        default=None,
    )

    if snapshot is None:
        return None

    if isinstance(snapshot, dict):
        return first_present(
            snapshot,
            "snapshot_id",
            "id",
            "value",
            default=None,
        )

    return str(snapshot)


def extract_positions(report):
    candidates = [
        report.get("positions"),
        report.get("paper_positions"),
        report.get("open_positions"),
        report.get("portfolio_positions"),
    ]

    for value in candidates:
        if isinstance(value, list):
            return value

    return []


def extract_risk(report):
    """
    Supports the actual upstream v0.1 structure:

    Aggregate risk is stored as:
        aggregate_paper_risk.portfolio_risk

    Some versions may instead expose:
        risk
        portfolio_risk
        total_analytical_risk
    """

    aggregate = report.get("aggregate_paper_risk")

    if isinstance(aggregate, dict):
        return {
            "portfolio_risk": numeric(
                first_present(
                    aggregate,
                    "portfolio_risk",
                    "total_risk",
                    default=0.0,
                )
            ),
            "aggregate_unrealized_pnl": numeric(
                first_present(
                    aggregate,
                    "aggregate_unrealized_pnl",
                    "unrealized_pnl",
                    "pnl",
                    default=0.0,
                )
            ),
            "risk_notional_ratio": numeric(
                first_present(
                    aggregate,
                    "risk_notional_ratio",
                    "risk_to_notional",
                    default=0.0,
                )
            ),
        }

    risk = report.get("risk")

    if isinstance(risk, dict):
        return {
            "portfolio_risk": numeric(
                first_present(
                    risk,
                    "portfolio_risk",
                    "total_risk",
                    "risk",
                    default=0.0,
                )
            ),
            "aggregate_unrealized_pnl": numeric(
                first_present(
                    risk,
                    "aggregate_unrealized_pnl",
                    "unrealized_pnl",
                    "pnl",
                    default=0.0,
                )
            ),
            "risk_notional_ratio": numeric(
                first_present(
                    risk,
                    "risk_notional_ratio",
                    "risk_to_notional",
                    default=0.0,
                )
            ),
        }

    return {
        "portfolio_risk": numeric(
            first_present(
                report,
                "portfolio_risk",
                "total_analytical_risk",
                default=0.0,
            )
        ),
        "aggregate_unrealized_pnl": numeric(
            first_present(
                report,
                "aggregate_unrealized_pnl",
                "unrealized_pnl",
                default=0.0,
            )
        ),
        "risk_notional_ratio": numeric(
            first_present(
                report,
                "risk_notional_ratio",
                default=0.0,
            )
        ),
    }


def extract_exposure(report):
    exposure = report.get("portfolio_exposure")

    if not isinstance(exposure, dict):
        exposure = report.get("exposure")

    if not isinstance(exposure, dict):
        exposure = {}

    total_positions = integer(
        first_present(
            exposure,
            "total_positions",
            "positions",
            default=report.get("total_positions", 0),
        )
    )

    total_notional = numeric(
        first_present(
            exposure,
            "total_analytical_notional",
            "analytical_notional",
            "notional",
            default=report.get("total_analytical_notional", 0.0),
        )
    )

    total_risk = numeric(
        first_present(
            exposure,
            "total_analytical_risk",
            "analytical_risk",
            default=report.get("total_analytical_risk", 0.0),
        )
    )

    return {
        "total_positions": total_positions,
        "total_analytical_notional": total_notional,
        "total_analytical_risk": total_risk,
    }


def extract_concentration(report):
    concentration = report.get("portfolio_concentration")

    if not isinstance(concentration, dict):
        concentration = report.get("concentration")

    if not isinstance(concentration, dict):
        concentration = {}

    maximum_asset = first_present(
        concentration,
        "maximum_asset",
        "max_asset",
        default=None,
    )

    maximum_concentration = numeric(
        first_present(
            concentration,
            "maximum_concentration",
            "max_concentration",
            default=0.0,
        )
    )

    return {
        "maximum_asset": maximum_asset,
        "maximum_concentration": maximum_concentration,
    }


# ---------------------------------------------------------------------------
# UPSTREAM VALIDATION
# ---------------------------------------------------------------------------

def validate_upstream(report):
    frontier = str(report.get("frontier", ""))

    if frontier and (
        "PORTFOLIO_STATE" not in frontier
        and "EXPOSURE" not in frontier
    ):
        raise ValueError(
            f"Unexpected upstream frontier: {frontier}"
        )

    snapshot = extract_snapshot(report)

    positions = extract_positions(report)
    risk = extract_risk(report)
    exposure = extract_exposure(report)
    concentration = extract_concentration(report)

    # Empty portfolio is a valid upstream state.
    # It must NOT be rejected merely because there is no explicit "risk" key.
    if not positions:
        if exposure["total_positions"] != 0:
            raise ValueError(
                "Upstream exposure reports non-zero positions "
                "but position collection is empty."
            )

    if exposure["total_positions"] == 0:
        exposure["total_analytical_notional"] = 0.0
        exposure["total_analytical_risk"] = 0.0

        risk["portfolio_risk"] = 0.0
        risk["aggregate_unrealized_pnl"] = 0.0
        risk["risk_notional_ratio"] = 0.0

        concentration["maximum_asset"] = None
        concentration["maximum_concentration"] = 0.0

    return {
        "frontier": frontier,
        "snapshot": snapshot,
        "positions": positions,
        "risk": risk,
        "exposure": exposure,
        "concentration": concentration,
    }


# ---------------------------------------------------------------------------
# POSITION NORMALIZATION
# ---------------------------------------------------------------------------

def normalize_position(position):
    if not isinstance(position, dict):
        return None

    asset = first_present(
        position,
        "asset",
        "symbol",
        "ticker",
        default=None,
    )

    if asset is not None:
        asset = str(asset)

    notional = numeric(
        first_present(
            position,
            "analytical_notional",
            "notional",
            "position_notional",
            default=0.0,
        )
    )

    risk = numeric(
        first_present(
            position,
            "analytical_risk",
            "risk",
            "position_risk",
            default=0.0,
        )
    )

    return {
        "asset": asset,
        "notional": notional,
        "risk": risk,
    }


# ---------------------------------------------------------------------------
# LIMIT ENGINE
# ---------------------------------------------------------------------------

def evaluate_limits(upstream):
    exposure = upstream["exposure"]
    risk = upstream["risk"]
    concentration = upstream["concentration"]

    total_positions = exposure["total_positions"]
    total_notional = exposure["total_analytical_notional"]

    portfolio_risk = max(
        exposure["total_analytical_risk"],
        risk["portfolio_risk"],
    )

    unrealized_pnl = risk["aggregate_unrealized_pnl"]

    max_concentration = concentration["maximum_concentration"]

    checks = []

    checks.append({
        "name": "MAX_PORTFOLIO_RISK",
        "observed": portfolio_risk,
        "limit": MAX_PORTFOLIO_RISK,
        "pass": portfolio_risk <= MAX_PORTFOLIO_RISK,
    })

    checks.append({
        "name": "MAX_ANALYTICAL_NOTIONAL",
        "observed": total_notional,
        "limit": MAX_ANALYTICAL_NOTIONAL,
        "pass": total_notional <= MAX_ANALYTICAL_NOTIONAL,
    })

    checks.append({
        "name": "MAX_ASSET_CONCENTRATION",
        "observed": max_concentration,
        "limit": MAX_ASSET_CONCENTRATION,
        "pass": max_concentration <= MAX_ASSET_CONCENTRATION,
    })

    loss_exceeded = unrealized_pnl < -MAX_UNREALIZED_LOSS

    checks.append({
        "name": "MAX_UNREALIZED_LOSS",
        "observed": unrealized_pnl,
        "limit": -MAX_UNREALIZED_LOSS,
        "pass": not loss_exceeded,
    })

    circuit_breakers = []

    if (
        CIRCUIT_BREAKER_ON_RISK
        and portfolio_risk > MAX_PORTFOLIO_RISK
    ):
        circuit_breakers.append("PORTFOLIO_RISK_LIMIT")

    if (
        CIRCUIT_BREAKER_ON_NOTIONAL
        and total_notional > MAX_ANALYTICAL_NOTIONAL
    ):
        circuit_breakers.append("NOTIONAL_LIMIT")

    if (
        CIRCUIT_BREAKER_ON_CONCENTRATION
        and max_concentration > MAX_ASSET_CONCENTRATION
    ):
        circuit_breakers.append("CONCENTRATION_LIMIT")

    if (
        CIRCUIT_BREAKER_ON_LOSS
        and loss_exceeded
    ):
        circuit_breakers.append("UNREALIZED_LOSS_LIMIT")

    limits_pass = all(item["pass"] for item in checks)

    circuit_breaker = len(circuit_breakers) > 0

    # Empty portfolio is safe by construction.
    if total_positions == 0:
        limits_pass = True
        circuit_breaker = False
        circuit_breakers = []

    return {
        "limits_pass": limits_pass,
        "circuit_breaker": circuit_breaker,
        "circuit_breakers": circuit_breakers,
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# DECISION
# ---------------------------------------------------------------------------

def build_decision(upstream, evaluation):
    positions = upstream["exposure"]["total_positions"]

    if positions == 0:
        return {
            "decision": "NO_TRADE",
            "state": "EMPTY_PORTFOLIO",
            "reason": "NO_OPEN_PAPER_POSITIONS",
        }

    if evaluation["circuit_breaker"]:
        return {
            "decision": "CIRCUIT_BREAKER",
            "state": "RISK_BLOCKED",
            "reason": ",".join(
                evaluation["circuit_breakers"]
            ),
        }

    if not evaluation["limits_pass"]:
        return {
            "decision": "NO_TRADE",
            "state": "LIMIT_BLOCKED",
            "reason": "PORTFOLIO_RISK_LIMIT_FAILED",
        }

    return {
        "decision": "PAPER_RISK_ALLOWED",
        "state": "WITHIN_LIMITS",
        "reason": "ALL_RISK_LIMITS_PASS",
    }


# ---------------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------------

def build_report(
    baseline_before,
    baseline_after,
    upstream,
    evaluation,
    decision,
):
    exposure = upstream["exposure"]
    risk = upstream["risk"]
    concentration = upstream["concentration"]

    return {
        "frontier": FRONTIER,
        "version": VERSION,
        "timestamp_utc": utc_now(),

        "objective": (
            "Evaluate analytical PAPER portfolio risk limits "
            "and circuit-breaker state without execution."
        ),

        "upstream": {
            "frontier": upstream["frontier"],
            "snapshot": upstream["snapshot"],
            "position_count": exposure["total_positions"],
        },

        "portfolio": {
            "positions": exposure["total_positions"],
            "analytical_notional": exposure[
                "total_analytical_notional"
            ],
            "analytical_risk": exposure[
                "total_analytical_risk"
            ],
            "portfolio_risk": risk["portfolio_risk"],
            "aggregate_unrealized_pnl": risk[
                "aggregate_unrealized_pnl"
            ],
            "risk_notional_ratio": risk[
                "risk_notional_ratio"
            ],
        },

        "concentration": {
            "maximum_asset": concentration["maximum_asset"],
            "maximum_concentration": concentration[
                "maximum_concentration"
            ],
        },

        "risk_limits": {
            "max_portfolio_risk": MAX_PORTFOLIO_RISK,
            "max_analytical_notional": MAX_ANALYTICAL_NOTIONAL,
            "max_asset_concentration": MAX_ASSET_CONCENTRATION,
            "max_unrealized_loss": MAX_UNREALIZED_LOSS,
        },

        "limit_evaluation": evaluation,

        "decision": decision,

        "production_database": {
            "before": baseline_before,
            "after": baseline_after,
            "unchanged": baseline_before == baseline_after,
        },

        "safety": {
            "production_db_modified": False,
            "production_engine_executed": False,
            "historical_repair": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "synthetic_data": False,
            "live_data_injection": False,
            "real_order_execution": False,
            "paper_execution": "ANALYTICAL_ONLY",
        },
    }


# ---------------------------------------------------------------------------
# CONSOLE
# ---------------------------------------------------------------------------

def print_header():
    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO "
        "RISK LIMITS + CIRCUIT BREAKER GATE v0.2"
    )
    print("=" * 100)

    print()
    print("OBJECTIVE:")
    print(
        "  Consume ONLY verified upstream PAPER portfolio state."
    )
    print(
        "  Evaluate analytical portfolio risk limits "
        "and circuit-breaker state."
    )
    print(
        "  No real order is created or submitted."
    )

    print()
    print("=" * 100)
    print("SAFETY POLICY")
    print("=" * 100)
    print(f"Production DB writes       : FORBIDDEN")
    print(f"Production engine run      : NO")
    print(f"Historical repair          : NONE")
    print(f"Direction inference        : NONE")
    print(f"Score reconstruction       : NONE")
    print(f"Synthetic data             : FORBIDDEN")
    print(f"Live data injection        : NONE")
    print(f"REAL ORDER EXECUTION       : NONE")
    print(f"PAPER EXECUTION            : ANALYTICAL ONLY")


def print_report(
    baseline_before,
    baseline_after,
    upstream,
    evaluation,
    decision,
):
    exposure = upstream["exposure"]
    risk = upstream["risk"]
    concentration = upstream["concentration"]

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)
    print(f"Rows   : {baseline_before['rows']}")
    print(f"Size   : {baseline_before['size']}")
    print(f"SHA256 : {baseline_before['sha256']}")

    print()
    print("=" * 100)
    print("UPSTREAM PORTFOLIO STATE")
    print("=" * 100)
    print(f"Frontier         : {upstream['frontier']}")
    print(f"Snapshot         : {upstream['snapshot']}")
    print(
        f"Positions        : {exposure['total_positions']}"
    )

    print()
    print("=" * 100)
    print("PORTFOLIO RISK STATE")
    print("=" * 100)
    print(
        f"Analytical notional : "
        f"{exposure['total_analytical_notional']:.6f}"
    )
    print(
        f"Analytical risk    : "
        f"{exposure['total_analytical_risk']:.6f}"
    )
    print(
        f"Portfolio risk     : "
        f"{risk['portfolio_risk']:.6f}"
    )
    print(
        f"Unrealized P&L     : "
        f"{risk['aggregate_unrealized_pnl']:.6f}"
    )
    print(
        f"Risk / notional    : "
        f"{risk['risk_notional_ratio']:.6f}"
    )

    print()
    print("=" * 100)
    print("PORTFOLIO CONCENTRATION")
    print("=" * 100)
    print(
        f"Maximum asset        : "
        f"{concentration['maximum_asset']}"
    )
    print(
        f"Maximum concentration: "
        f"{concentration['maximum_concentration']:.6f}"
    )

    print()
    print("=" * 100)
    print("RISK LIMIT EVALUATION")
    print("=" * 100)

    for check in evaluation["checks"]:
        status = "PASS" if check["pass"] else "FAIL"

        print(
            f"{check['name']:<30} | "
            f"observed={check['observed']:.6f} | "
            f"limit={check['limit']:.6f} | "
            f"{status}"
        )

    print()
    print("=" * 100)
    print("CIRCUIT BREAKER")
    print("=" * 100)

    print(
        f"State : "
        f"{'TRIGGERED' if evaluation['circuit_breaker'] else 'CLEAR'}"
    )

    if evaluation["circuit_breakers"]:
        for reason in evaluation["circuit_breakers"]:
            print(f"  - {reason}")
    else:
        print("Reason : NONE")

    print()
    print("=" * 100)
    print("PORTFOLIO RISK LIMITS + CIRCUIT BREAKER VERDICT")
    print("=" * 100)

    print(
        f"UPSTREAM_STATE_CONSUMED : PASS"
    )
    print(
        f"RISK_LIMIT_EVALUATION   : "
        f"{'PASS' if evaluation['limits_pass'] else 'FAIL'}"
    )
    print(
        f"CIRCUIT_BREAKER         : "
        f"{'TRIGGERED' if evaluation['circuit_breaker'] else 'CLEAR'}"
    )
    print(
        f"PRODUCTION_ISOLATION    : PASS"
    )
    print(
        f"FRONTIER VERDICT        : "
        f"{decision['decision']}"
    )

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    print(
        f"Before rows : {baseline_before['rows']}"
    )
    print(
        f"After rows  : {baseline_after['rows']}"
    )
    print(
        f"Before size : {baseline_before['size']}"
    )
    print(
        f"After size  : {baseline_after['size']}"
    )
    print(
        f"Before SHA256 : {baseline_before['sha256']}"
    )
    print(
        f"After SHA256  : {baseline_after['sha256']}"
    )
    print(
        "PRODUCTION DB INVARIANT : "
        f"{'PASS' if baseline_before == baseline_after else 'FAIL'}"
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
        "No real trading order was created, submitted, "
        "or executed."
    )


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print_header()

    if not PRODUCTION_DB.exists():
        raise FileNotFoundError(
            f"Production DB not found: {PRODUCTION_DB}"
        )

    if not UPSTREAM_REPORT.exists():
        raise FileNotFoundError(
            f"Upstream report not found: {UPSTREAM_REPORT}"
        )

    print()
    print("=" * 100)
    print("UPSTREAM PORTFOLIO STATE")
    print("=" * 100)
    print(f"Report : {UPSTREAM_REPORT}")

    baseline_before = production_baseline()

    report = load_json(UPSTREAM_REPORT)

    upstream = validate_upstream(report)

    evaluation = evaluate_limits(upstream)

    decision = build_decision(
        upstream,
        evaluation,
    )

    # This script performs NO production DB writes.
    baseline_after = production_baseline()

    if baseline_before != baseline_after:
        raise RuntimeError(
            "PRODUCTION DATABASE INVARIANT FAILED."
        )

    final_report = build_report(
        baseline_before,
        baseline_after,
        upstream,
        evaluation,
        decision,
    )

    CAPTURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
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

    print_report(
        baseline_before,
        baseline_after,
        upstream,
        evaluation,
        decision,
    )

    print()
    print(
        f"Runtime report : {OUTPUT_REPORT}"
    )


if __name__ == "__main__":
    main()