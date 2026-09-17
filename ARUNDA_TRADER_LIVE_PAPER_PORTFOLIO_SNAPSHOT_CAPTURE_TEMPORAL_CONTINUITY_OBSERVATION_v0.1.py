from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =============================================================================
# ARUNDA TRADER
# LIVE PAPER PORTFOLIO SNAPSHOT CAPTURE + TEMPORAL CONTINUITY OBSERVATION v0.1
# =============================================================================

VERSION = "v0.1"

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = PROJECT_ROOT / "arunda.db"

LIVE_ROOT = Path(
    os.environ.get(
        "ARUNDA_LIVE_ROOT",
        r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc",
    )
)

UPSTREAM_REPORT = (
    LIVE_ROOT
    / "LIVE_PAPER_PORTFOLIO_TEMPORAL_EVIDENCE_ACCUMULATION_SNAPSHOT_COHERENCE_GATE_REPORT.json"
)

RISK_REPORT = (
    LIVE_ROOT
    / "LIVE_PAPER_PORTFOLIO_RISK_GOVERNANCE_READINESS_GATE_REPORT.json"
)

PORTFOLIO_REPORT = (
    LIVE_ROOT
    / "LIVE_PAPER_PORTFOLIO_STATE_EXPOSURE_RISK_RECONCILIATION_REPORT.json"
)

TEMPORAL_REPORT = (
    LIVE_ROOT
    / "LIVE_PAPER_PORTFOLIO_TEMPORAL_STATE_RISK_TRANSITION_RECONCILIATION_REPORT.json"
)

OUTPUT_REPORT = (
    LIVE_ROOT
    / "LIVE_PAPER_PORTFOLIO_SNAPSHOT_CAPTURE_TEMPORAL_CONTINUITY_OBSERVATION_REPORT.json"
)

OBSERVATION_STORE = (
    LIVE_ROOT
    / "LIVE_PAPER_PORTFOLIO_TEMPORAL_OBSERVATION_STORE.json"
)


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
REAL_ORDER_EXECUTION = False
PAPER_EXECUTION = "ANALYTICAL_ONLY"


# =============================================================================
# HELPERS
# =============================================================================

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")

    return data


def first_value(data: dict[str, Any], *paths: str, default: Any = None) -> Any:
    """
    Supports both:
        {"snapshot": "..."}
    and nested:
        {"upstream": {"snapshot": "..."}}
    """
    for path in paths:
        current: Any = data

        try:
            for part in path.split("."):
                if not isinstance(current, dict) or part not in current:
                    raise KeyError
                current = current[part]

            if current is not None:
                return current

        except KeyError:
            continue

    return default


def to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default

    if isinstance(value, bool):
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_snapshot_id(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    lowered = value.lower()

    if lowered in {"none", "null", "n/a", "na", "unknown"}:
        return None

    return value


# =============================================================================
# DATABASE FINGERPRINT — READ ONLY
# =============================================================================

def database_fingerprint(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return {
            "path": str(db_path),
            "exists": False,
            "rows": None,
            "size": None,
            "sha256": None,
        }

    size = db_path.stat().st_size

    sha256 = hashlib.sha256()

    with db_path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    rows = None

    try:
        uri = f"file:{db_path.as_posix()}?mode=ro"

        conn = sqlite3.connect(uri, uri=True)

        try:
            tables = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                  AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()

            # The production history table is the strongest stable row-count
            # reference available in this project.
            table_names = {row[0] for row in tables}

            if "market_history" in table_names:
                rows = conn.execute(
                    "SELECT COUNT(*) FROM market_history"
                ).fetchone()[0]

            elif "market_data" in table_names:
                rows = conn.execute(
                    "SELECT COUNT(*) FROM market_data"
                ).fetchone()[0]

        finally:
            conn.close()

    except Exception:
        rows = None

    return {
        "path": str(db_path),
        "exists": True,
        "rows": rows,
        "size": size,
        "sha256": sha256.hexdigest(),
    }


# =============================================================================
# SNAPSHOT EXTRACTION
# =============================================================================

def extract_snapshot(report: dict[str, Any], source_name: str) -> dict[str, Any]:
    snapshot_id = normalize_snapshot_id(
        first_value(
            report,
            "current_snapshot",
            "snapshot",
            "snapshot_id",
            "upstream.current_snapshot",
            "upstream.snapshot",
            "upstream.snapshot_id",
        )
    )

    timestamp = first_value(
        report,
        "timestamp",
        "captured_at",
        "observation_time",
        "current_timestamp",
        "upstream.timestamp",
        "upstream.captured_at",
    )

    positions = to_int(
        first_value(
            report,
            "positions",
            "paper_positions",
            "open_positions",
            "position_count",
            "current_risk.positions",
            "portfolio.positions",
            default=0,
        )
    )

    open_positions = to_int(
        first_value(
            report,
            "open_positions",
            "open_position_count",
            "current_risk.open_positions",
            "portfolio.open_positions",
            default=positions,
        )
    )

    closed_positions = to_int(
        first_value(
            report,
            "closed_positions",
            "closed_position_count",
            "portfolio.closed_positions",
            default=0,
        )
    )

    notional = to_float(
        first_value(
            report,
            "analytical_notional",
            "total_analytical_notional",
            "notional",
            "portfolio.analytical_notional",
            "risk.analytical_notional",
            default=0.0,
        )
    )

    risk = to_float(
        first_value(
            report,
            "portfolio_risk",
            "analytical_risk",
            "total_analytical_risk",
            "risk",
            "portfolio.portfolio_risk",
            "risk.portfolio_risk",
            default=0.0,
        )
    )

    pnl = to_float(
        first_value(
            report,
            "unrealized_pnl",
            "aggregate_unrealized_pnl",
            "total_pnl",
            "reported_total_pnl",
            "pnl",
            "portfolio.unrealized_pnl",
            default=0.0,
        )
    )

    realized_pnl = to_float(
        first_value(
            report,
            "realized_pnl",
            "reported_realized_pnl",
            "portfolio.realized_pnl",
            default=0.0,
        )
    )

    drawdown = to_float(
        first_value(
            report,
            "current_drawdown",
            "drawdown",
            "portfolio.current_drawdown",
            default=0.0,
        )
    )

    max_drawdown = to_float(
        first_value(
            report,
            "maximum_drawdown",
            "max_drawdown",
            "portfolio.maximum_drawdown",
            default=0.0,
        )
    )

    concentration = to_float(
        first_value(
            report,
            "maximum_concentration",
            "max_concentration",
            "maximum_asset_concentration",
            "portfolio.maximum_concentration",
            default=0.0,
        )
    )

    circuit_state = first_value(
        report,
        "circuit_breaker.state",
        "circuit_breaker.STATE",
        "circuit_breaker_state",
        "circuit_breaker",
        default="UNKNOWN",
    )

    if isinstance(circuit_state, dict):
        circuit_state = circuit_state.get(
            "STATE",
            circuit_state.get("state", "UNKNOWN"),
        )

    circuit_reason = first_value(
        report,
        "circuit_breaker.reason",
        "circuit_breaker.REASON",
        "circuit_breaker_reason",
        default="NONE",
    )

    if isinstance(circuit_reason, dict):
        circuit_reason = circuit_reason.get(
            "REASON",
            circuit_reason.get("reason", "NONE"),
        )

    if timestamp is None:
        timestamp = now_utc()

    return {
        "snapshot_id": snapshot_id,
        "timestamp": str(timestamp),
        "source": source_name,
        "positions": positions,
        "open_positions": open_positions,
        "closed_positions": closed_positions,
        "analytical_notional": notional,
        "portfolio_risk": risk,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": pnl,
        "total_pnl": realized_pnl + pnl,
        "current_drawdown": drawdown,
        "maximum_drawdown": max_drawdown,
        "maximum_concentration": concentration,
        "circuit_breaker_state": str(circuit_state),
        "circuit_breaker_reason": str(circuit_reason),
    }


# =============================================================================
# REPORT SELECTION
# =============================================================================

def select_best_current_report() -> tuple[dict[str, Any], str]:
    """
    Prefer the most complete already-produced report.

    No engine is executed.
    No market data is fetched.
    """

    candidates = [
        (PORTFOLIO_REPORT, "PORTFOLIO_STATE"),
        (TEMPORAL_REPORT, "TEMPORAL_STATE"),
        (RISK_REPORT, "RISK_GOVERNANCE"),
        (UPSTREAM_REPORT, "TEMPORAL_EVIDENCE_GATE"),
    ]

    best: tuple[int, dict[str, Any], str] | None = None

    for path, source_name in candidates:
        if not path.exists():
            continue

        try:
            report = load_json(path)
        except Exception:
            continue

        snapshot = extract_snapshot(report, source_name)

        score = 0

        if snapshot["snapshot_id"]:
            score += 10

        if snapshot["timestamp"]:
            score += 2

        for key in (
            "positions",
            "analytical_notional",
            "portfolio_risk",
            "unrealized_pnl",
        ):
            if key in snapshot:
                score += 1

        if best is None or score > best[0]:
            best = (score, report, source_name)

    if best is None:
        return {}, "NONE"

    return best[1], best[2]


# =============================================================================
# TEMPORAL OBSERVATION STORE
# =============================================================================

def load_observation_store() -> list[dict[str, Any]]:
    if not OBSERVATION_STORE.exists():
        return []

    try:
        data = load_json(OBSERVATION_STORE)

        observations = data.get("observations", [])

        if not isinstance(observations, list):
            return []

        return [
            item
            for item in observations
            if isinstance(item, dict)
        ]

    except Exception:
        return []


def save_observation_store(observations: list[dict[str, Any]]) -> None:
    """
    Writes ONLY inside LIVE_ROOT / temp capture directory.
    Never writes to production DB.
    """

    payload = {
        "schema": "ARUNDA_TRADER_TEMPORAL_OBSERVATION_STORE_v0.1",
        "updated_at": now_utc(),
        "observation_count": len(observations),
        "observations": observations,
    }

    LIVE_ROOT.mkdir(parents=True, exist_ok=True)

    temp_path = OBSERVATION_STORE.with_suffix(".tmp")

    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    os.replace(temp_path, OBSERVATION_STORE)


# =============================================================================
# TEMPORAL CONTINUITY
# =============================================================================

def validate_observation_identity(
    observation: dict[str, Any],
) -> tuple[bool, str]:

    snapshot_id = normalize_snapshot_id(
        observation.get("snapshot_id")
    )

    if snapshot_id is None:
        return False, "MISSING_SNAPSHOT_ID"

    timestamp = observation.get("timestamp")

    if not timestamp:
        return False, "MISSING_TIMESTAMP"

    return True, "PASS"


def compare_observations(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
) -> dict[str, Any]:

    if previous is None:
        return {
            "continuity_status": "FIRST_OBSERVATION",
            "previous_snapshot": None,
            "current_snapshot": current["snapshot_id"],
            "snapshot_changed": None,
            "timestamp_order": "N/A",
            "position_delta": None,
            "notional_delta": None,
            "risk_delta": None,
            "pnl_delta": None,
            "drawdown_delta": None,
        }

    previous_id = normalize_snapshot_id(previous.get("snapshot_id"))
    current_id = normalize_snapshot_id(current.get("snapshot_id"))

    snapshot_changed = previous_id != current_id

    previous_timestamp = str(previous.get("timestamp", ""))
    current_timestamp = str(current.get("timestamp", ""))

    timestamp_order = "UNKNOWN"

    try:
        previous_dt = datetime.fromisoformat(
            previous_timestamp.replace("Z", "+00:00")
        )

        current_dt = datetime.fromisoformat(
            current_timestamp.replace("Z", "+00:00")
        )

        if current_dt > previous_dt:
            timestamp_order = "FORWARD"

        elif current_dt == previous_dt:
            timestamp_order = "EQUAL"

        else:
            timestamp_order = "REGRESSION"

    except Exception:
        timestamp_order = "UNPARSEABLE"

    position_delta = (
        to_int(current.get("positions"))
        - to_int(previous.get("positions"))
    )

    notional_delta = (
        to_float(current.get("analytical_notional"))
        - to_float(previous.get("analytical_notional"))
    )

    risk_delta = (
        to_float(current.get("portfolio_risk"))
        - to_float(previous.get("portfolio_risk"))
    )

    pnl_delta = (
        to_float(current.get("total_pnl"))
        - to_float(previous.get("total_pnl"))
    )

    drawdown_delta = (
        to_float(current.get("current_drawdown"))
        - to_float(previous.get("current_drawdown"))
    )

    if not snapshot_changed:
        continuity_status = "DUPLICATE_SNAPSHOT"

    elif timestamp_order == "REGRESSION":
        continuity_status = "TEMPORAL_REGRESSION"

    elif timestamp_order in {"UNPARSEABLE", "UNKNOWN"}:
        continuity_status = "TIMESTAMP_UNVERIFIED"

    else:
        continuity_status = "CONTINUOUS"

    return {
        "continuity_status": continuity_status,
        "previous_snapshot": previous_id,
        "current_snapshot": current_id,
        "snapshot_changed": snapshot_changed,
        "timestamp_order": timestamp_order,
        "position_delta": position_delta,
        "notional_delta": notional_delta,
        "risk_delta": risk_delta,
        "pnl_delta": pnl_delta,
        "drawdown_delta": drawdown_delta,
    }


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO "
        "SNAPSHOT CAPTURE + TEMPORAL CONTINUITY OBSERVATION v0.1"
    )
    print("=" * 100)

    print()
    print("=" * 100)
    print("OBJECTIVE:")
    print("=" * 100)
    print(
        "Capture one additional real analytical PAPER portfolio observation "
        "from already-produced upstream reports."
    )
    print(
        "No synthetic snapshot is created."
    )
    print(
        "No production engine is executed."
    )
    print(
        "No real order is created or submitted."
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
    print(f"Order execution            : NONE")
    print(f"PAPER EXECUTION            : {PAPER_EXECUTION}")

    print()
    print("=" * 100)
    print("PRODUCTION BASELINE")
    print("=" * 100)

    before = database_fingerprint(DB_PATH)

    print(f"Rows   : {before['rows']}")
    print(f"Size   : {before['size']}")
    print(f"SHA256 : {before['sha256']}")

    print()
    print("=" * 100)
    print("UPSTREAM OBSERVATION SOURCE")
    print("=" * 100)

    report, source_name = select_best_current_report()

    print(f"Source : {source_name}")

    if not report:
        print("No upstream analytical report available.")

        output = {
            "schema": "ARUNDA_TRADER_LIVE_PAPER_PORTFOLIO_SNAPSHOT_CAPTURE_TEMPORAL_CONTINUITY_OBSERVATION_v0.1",
            "generated_at": now_utc(),
            "frontier": "LIVE_PAPER_PORTFOLIO_SNAPSHOT_CAPTURE_TEMPORAL_CONTINUITY_OBSERVATION_v0.1",
            "status": "INSUFFICIENT_DATA",
            "reason": "NO_UPSTREAM_REPORT",
            "production_db": before,
            "safety": {
                "production_db_writes": "NONE",
                "production_engine": "NOT_EXECUTED",
                "synthetic_data": "NONE",
                "real_order_execution": "NONE",
            },
        }

        LIVE_ROOT.mkdir(parents=True, exist_ok=True)

        with OUTPUT_REPORT.open("w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        return

    current = extract_snapshot(report, source_name)

    valid, identity_reason = validate_observation_identity(current)

    print()
    print("=" * 100)
    print("CURRENT OBSERVATION")
    print("=" * 100)

    print(f"Snapshot ID          : {current['snapshot_id']}")
    print(f"Timestamp            : {current['timestamp']}")
    print(f"Positions            : {current['positions']}")
    print(f"Open positions       : {current['open_positions']}")
    print(f"Closed positions     : {current['closed_positions']}")
    print(f"Analytical notional  : {current['analytical_notional']:.6f}")
    print(f"Portfolio risk       : {current['portfolio_risk']:.6f}")
    print(f"Realized P&L         : {current['realized_pnl']:.6f}")
    print(f"Unrealized P&L       : {current['unrealized_pnl']:.6f}")
    print(f"Total P&L            : {current['total_pnl']:.6f}")
    print(f"Current drawdown     : {current['current_drawdown']:.6f}")
    print(f"Maximum drawdown     : {current['maximum_drawdown']:.6f}")
    print(f"Max concentration    : {current['maximum_concentration']:.6f}")
    print(f"Circuit breaker      : {current['circuit_breaker_state']}")
    print(f"Identity             : {identity_reason}")

    observations = load_observation_store()

    # Prevent duplicate observation records.
    existing_ids = {
        normalize_snapshot_id(item.get("snapshot_id"))
        for item in observations
        if isinstance(item, dict)
    }

    snapshot_id = normalize_snapshot_id(current.get("snapshot_id"))

    if valid and snapshot_id not in existing_ids:
        observations.append(current)

    # Sort only valid observations by timestamp.
    def timestamp_key(item: dict[str, Any]) -> str:
        return str(item.get("timestamp", ""))

    observations.sort(key=timestamp_key)

    # Keep the observation store bounded and deterministic.
    # This is an analytical TEMP store, not production state.
    if len(observations) > 100:
        observations = observations[-100:]

    previous = None

    if len(observations) >= 2:
        # The current observation is the newest one.
        previous = observations[-2]

    continuity = compare_observations(previous, current)

    print()
    print("=" * 100)
    print("TEMPORAL CONTINUITY")
    print("=" * 100)

    print(f"Stored observations : {len(observations)}")
    print(f"Previous snapshot   : {continuity['previous_snapshot']}")
    print(f"Current snapshot    : {continuity['current_snapshot']}")
    print(f"Snapshot changed    : {continuity['snapshot_changed']}")
    print(f"Timestamp order     : {continuity['timestamp_order']}")
    print(f"Continuity status   : {continuity['continuity_status']}")

    if continuity["position_delta"] is not None:
        print(f"Position Δ          : {continuity['position_delta']}")
        print(f"Notional Δ          : {continuity['notional_delta']:.6f}")
        print(f"Risk Δ              : {continuity['risk_delta']:.6f}")
        print(f"P&L Δ               : {continuity['pnl_delta']:.6f}")
        print(f"Drawdown Δ          : {continuity['drawdown_delta']:.6f}")

    save_observation_store(observations)

    usable_count = len(observations)

    if usable_count == 0:
        evidence_status = "INSUFFICIENT_DATA"
        evidence_reason = "NO_VALID_SNAPSHOT"

    elif usable_count == 1:
        evidence_status = "INSUFFICIENT_DATA"
        evidence_reason = "ONE_VALID_SNAPSHOT_ONLY"

    else:
        # We now have at least two stored observations.
        if continuity["continuity_status"] == "CONTINUOUS":
            evidence_status = "PASS"
            evidence_reason = "MULTIPLE_FORWARD_ORDERED_SNAPSHOTS"

        elif continuity["continuity_status"] == "DUPLICATE_SNAPSHOT":
            evidence_status = "INSUFFICIENT_DATA"
            evidence_reason = "NEW_OBSERVATION_DUPLICATES_EXISTING_SNAPSHOT"

        else:
            evidence_status = "BLOCKED"
            evidence_reason = continuity["continuity_status"]

    print()
    print("=" * 100)
    print("TEMPORAL EVIDENCE STATUS")
    print("=" * 100)
    print(f"Snapshots stored    : {usable_count}")
    print(f"Evidence status     : {evidence_status}")
    print(f"Reason              : {evidence_reason}")

    after = database_fingerprint(DB_PATH)

    db_invariant = (
        before["rows"] == after["rows"]
        and before["size"] == after["size"]
        and before["sha256"] == after["sha256"]
    )

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)

    print(f"Before rows   : {before['rows']}")
    print(f"After rows    : {after['rows']}")
    print(f"Before size   : {before['size']}")
    print(f"After size    : {after['size']}")
    print(f"Before SHA256  : {before['sha256']}")
    print(f"After SHA256   : {after['sha256']}")
    print(
        "PRODUCTION DB INVARIANT : "
        + ("PASS" if db_invariant else "FAIL")
    )

    final_verdict = (
        "PASS"
        if evidence_status == "PASS" and db_invariant
        else evidence_status
    )

    print()
    print("=" * 100)
    print(
        "LIVE PAPER PORTFOLIO SNAPSHOT CAPTURE + "
        "TEMPORAL CONTINUITY OBSERVATION VERDICT"
    )
    print("=" * 100)

    print(f"UPSTREAM_OBSERVATION_CONSUMED : PASS")
    print(f"SNAPSHOT_CAPTURE              : {'PASS' if valid else 'INSUFFICIENT_DATA'}")
    print(f"TEMPORAL_CONTINUITY           : {evidence_status}")
    print(f"SNAPSHOT_COUNT                : {usable_count}")
    print(f"PRODUCTION_ISOLATION          : {'PASS' if db_invariant else 'FAIL'}")
    print(f"FRONTIER VERDICT              : {final_verdict}")

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

    if evidence_status == "PASS":
        print()
        print(
            "At least two independent forward-ordered PAPER observations "
            "are now available for downstream temporal verification."
        )

    elif evidence_status == "INSUFFICIENT_DATA":
        print()
        print(
            "Additional independent live-paper observations are required."
        )

    elif evidence_status == "BLOCKED":
        print()
        print(
            "Temporal continuity is blocked by an observation-order "
            "or snapshot-identity violation."
        )

    output = {
        "schema": (
            "ARUNDA_TRADER_LIVE_PAPER_PORTFOLIO_"
            "SNAPSHOT_CAPTURE_TEMPORAL_CONTINUITY_OBSERVATION_v0.1"
        ),
        "generated_at": now_utc(),
        "frontier": (
            "LIVE_PAPER_PORTFOLIO_SNAPSHOT_CAPTURE_"
            "TEMPORAL_CONTINUITY_OBSERVATION_v0.1"
        ),
        "upstream": {
            "source": source_name,
            "report": str(
                {
                    "PORTFOLIO_STATE": PORTFOLIO_REPORT,
                    "TEMPORAL_STATE": TEMPORAL_REPORT,
                    "RISK_GOVERNANCE": RISK_REPORT,
                    "TEMPORAL_EVIDENCE_GATE": UPSTREAM_REPORT,
                }.get(source_name, "")
            ),
        },
        "current_observation": current,
        "previous_observation": previous,
        "temporal_continuity": continuity,
        "temporal_evidence": {
            "stored_snapshot_count": usable_count,
            "status": evidence_status,
            "reason": evidence_reason,
        },
        "production_database": {
            "before": before,
            "after": after,
            "invariant": "PASS" if db_invariant else "FAIL",
        },
        "safety": {
            "production_db_writes": "NONE",
            "production_engine": "NOT_EXECUTED",
            "historical_repair": "NONE",
            "direction_inference": "NONE",
            "score_reconstruction": "NONE",
            "synthetic_data": "NONE",
            "live_data_injection": "NONE",
            "real_order_execution": "NONE",
            "paper_execution": "ANALYTICAL_ONLY",
        },
        "verdict": final_verdict,
    }

    LIVE_ROOT.mkdir(parents=True, exist_ok=True)

    temp_output = OUTPUT_REPORT.with_suffix(".tmp")

    with temp_output.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    os.replace(temp_output, OUTPUT_REPORT)

    print()
    print(f"Runtime report : {OUTPUT_REPORT}")
    print(f"Observation store: {OBSERVATION_STORE}")


if __name__ == "__main__":
    main()