from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v0.1"
FRONTIER = (
    "LIVE_PAPER_PORTFOLIO_TEMPORAL_EVIDENCE_ACCUMULATION_"
    "SNAPSHOT_COHERENCE_GATE_v0.1"
)

UPSTREAM_FRONTIER = (
    "LIVE_PAPER_PORTFOLIO_RISK_GOVERNANCE_READINESS_GATE_v0.2"
)

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = BASE_DIR / "arunda.db"

LIVE_DIR = Path(
    os.environ.get(
        "ARUNDA_LIVE_DIR",
        r"C:\Users\ASUS\AppData\Local\Temp\arunda_live_launch_76134ecc",
    )
)

UPSTREAM_REPORT = (
    LIVE_DIR
    / "LIVE_PAPER_PORTFOLIO_RISK_GOVERNANCE_READINESS_GATE_REPORT.json"
)

OUTPUT_REPORT = (
    LIVE_DIR
    / "LIVE_PAPER_PORTFOLIO_TEMPORAL_EVIDENCE_ACCUMULATION_"
    "SNAPSHOT_COHERENCE_GATE_REPORT.json"
)

MIN_SNAPSHOTS = 2


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def db_baseline() -> dict[str, Any]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Production DB not found: {DB_PATH}")

    size = DB_PATH.stat().st_size
    sha = sha256_file(DB_PATH)

    rows: int | None = None

    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
            total = 0

            tables = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()

            for (table,) in tables:
                try:
                    value = conn.execute(
                        f'SELECT COUNT(*) FROM "{table}"'
                    ).fetchone()[0]
                    total += int(value)
                except Exception:
                    pass

            rows = total
    except Exception:
        rows = None

    return {
        "rows": rows,
        "size": size,
        "sha256": sha,
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required report not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Upstream report root must be a JSON object.")

    return data


def first_value(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]

    return None


def extract_frontier(report: dict[str, Any]) -> str | None:
    return first_value(
        report,
        "frontier",
        "FRONTIER",
        "upstream_frontier",
        "UPSTREAM_FRONTIER",
    )


def extract_snapshot(report: dict[str, Any]) -> str | None:
    value = first_value(
        report,
        "snapshot",
        "current_snapshot",
        "currentSnapshot",
        "CURRENT_SNAPSHOT",
    )

    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def extract_snapshots(report: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        report.get("snapshots"),
        report.get("temporal_snapshots"),
        report.get("snapshot_history"),
        report.get("snapshot_records"),
        report.get("evidence"),
        report.get("temporal_evidence"),
    ]

    for value in candidates:
        if isinstance(value, list):
            result: list[dict[str, Any]] = []

            for item in value:
                if isinstance(item, dict):
                    result.append(dict(item))
                elif isinstance(item, str) and item.strip():
                    result.append(
                        {
                            "snapshot": item.strip(),
                        }
                    )

            return result

    return []


def extract_snapshot_count(report: dict[str, Any]) -> int:
    explicit = first_value(
        report,
        "snapshots_available",
        "snapshots_observed",
        "snapshot_count",
        "temporal_snapshot_count",
    )

    if isinstance(explicit, (int, float)):
        return max(0, int(explicit))

    snapshots = extract_snapshots(report)

    if snapshots:
        return len(snapshots)

    current = extract_snapshot(report)

    if current:
        return 1

    return 0


def normalize_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    snapshot = first_value(
        item,
        "snapshot",
        "current_snapshot",
        "snapshot_id",
        "id",
    )

    timestamp = first_value(
        item,
        "timestamp",
        "observed_at",
        "time",
        "created_at",
    )

    positions = first_value(
        item,
        "positions",
        "position_count",
        "paper_positions",
    )

    notional = first_value(
        item,
        "analytical_notional",
        "notional",
        "total_analytical_notional",
    )

    risk = first_value(
        item,
        "portfolio_risk",
        "analytical_risk",
        "risk",
        "total_analytical_risk",
    )

    pnl = first_value(
        item,
        "pnl",
        "total_pnl",
        "unrealized_pnl",
        "realized_pnl",
    )

    return {
        "snapshot": snapshot,
        "timestamp": timestamp,
        "positions": positions,
        "analytical_notional": notional,
        "risk": risk,
        "pnl": pnl,
    }


def validate_snapshot_identity(
    snapshots: list[dict[str, Any]],
) -> tuple[bool, str, list[dict[str, Any]]]:

    normalized = [
        normalize_snapshot(item)
        for item in snapshots
    ]

    seen: set[str] = set()
    duplicate_ids: list[str] = []

    for item in normalized:
        sid = item.get("snapshot")

        if sid is None:
            continue

        sid = str(sid)

        if sid in seen:
            duplicate_ids.append(sid)

        seen.add(sid)

    if duplicate_ids:
        return (
            False,
            "DUPLICATE_SNAPSHOT_IDENTITIES",
            normalized,
        )

    return True, "PASS", normalized


def validate_temporal_order(
    snapshots: list[dict[str, Any]],
) -> tuple[bool, str]:

    timestamps: list[datetime] = []

    for item in snapshots:
        value = item.get("timestamp")

        if not isinstance(value, str) or not value.strip():
            continue

        text = value.strip()

        try:
            parsed = datetime.fromisoformat(
                text.replace("Z", "+00:00")
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            timestamps.append(parsed)
        except ValueError:
            continue

    if len(timestamps) < 2:
        return True, "INSUFFICIENT_DATA"

    for previous, current in zip(
        timestamps,
        timestamps[1:],
    ):
        if current < previous:
            return False, "NON_MONOTONIC_TEMPORAL_ORDER"

    return True, "PASS"


def validate_coherence(
    snapshots: list[dict[str, Any]],
) -> tuple[bool, list[str]]:

    problems: list[str] = []

    for index, item in enumerate(snapshots, start=1):
        sid = item.get("snapshot")

        if sid is None:
            problems.append(
                f"SNAPSHOT_{index}_MISSING_ID"
            )

        numeric_fields = [
            "positions",
            "analytical_notional",
            "risk",
            "pnl",
        ]

        for field in numeric_fields:
            value = item.get(field)

            if value is None:
                continue

            try:
                numeric = float(value)

                if numeric != numeric:
                    problems.append(
                        f"SNAPSHOT_{index}_{field.upper()}_NAN"
                    )

            except (TypeError, ValueError):
                problems.append(
                    f"SNAPSHOT_{index}_{field.upper()}_INVALID"
                )

    return len(problems) == 0, problems


def print_header() -> None:
    print("=" * 100)
    print(
        "ARUNDA TRADER LIVE PAPER PORTFOLIO TEMPORAL EVIDENCE "
        "ACCUMULATION + SNAPSHOT COHERENCE GATE v0.1"
    )
    print("=" * 100)


def main() -> None:
    print_header()

    print()
    print("=" * 100)
    print("OBJECTIVE:")
    print("=" * 100)
    print(
        "Consume ONLY the verified LIVE PAPER PORTFOLIO "
        "RISK GOVERNANCE READINESS frontier."
    )
    print(
        "Accumulate and validate available temporal evidence."
    )
    print(
        "No synthetic snapshot is created."
    )
    print(
        "No real order is created or submitted."
    )

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

    baseline_before = db_baseline()

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

    upstream_frontier = extract_frontier(report)
    upstream_snapshot = extract_snapshot(report)

    print()
    print("=" * 100)
    print("UPSTREAM FRONTIER")
    print("=" * 100)
    print(f"Frontier         : {upstream_frontier}")
    print(f"Current snapshot : {upstream_snapshot}")

    if upstream_frontier != UPSTREAM_FRONTIER:
        raise ValueError(
            "Unexpected upstream frontier.\n"
            f"Expected: {UPSTREAM_FRONTIER}\n"
            f"Received: {upstream_frontier}"
        )

    source_snapshots = extract_snapshots(report)
    explicit_count = extract_snapshot_count(report)

    if not source_snapshots and upstream_snapshot:
        source_snapshots = [
            {
                "snapshot": upstream_snapshot,
                "timestamp": report.get(
                    "timestamp",
                    report.get("generated_at"),
                ),
                "positions": report.get("positions"),
                "analytical_notional": report.get(
                    "analytical_notional"
                ),
                "risk": report.get(
                    "portfolio_risk",
                    report.get("risk"),
                ),
                "pnl": report.get(
                    "unrealized_pnl",
                    report.get("total_pnl"),
                ),
            }
        ]

    identity_pass, identity_reason, snapshots = (
        validate_snapshot_identity(source_snapshots)
    )

    temporal_pass, temporal_reason = (
        validate_temporal_order(snapshots)
    )

    coherence_pass, coherence_problems = (
        validate_coherence(snapshots)
    )

    observed_count = max(
        len(snapshots),
        explicit_count if not snapshots else 0,
    )

    print()
    print("=" * 100)
    print("TEMPORAL EVIDENCE ACCUMULATION")
    print("=" * 100)
    print(f"Snapshots discovered : {observed_count}")
    print(f"Usable snapshots    : {len(snapshots)}")

    if len(snapshots) == 0:
        evidence_status = "INSUFFICIENT_DATA"
        evidence_reason = "NO_SNAPSHOT_EVIDENCE"
    elif len(snapshots) == 1:
        evidence_status = "INSUFFICIENT_DATA"
        evidence_reason = "MINIMUM_TWO_SNAPSHOTS_REQUIRED"
    else:
        evidence_status = "PASS"
        evidence_reason = "SUFFICIENT_TEMPORAL_EVIDENCE"

    print(f"Status              : {evidence_status}")
    print(f"Reason              : {evidence_reason}")

    print()
    print("=" * 100)
    print("SNAPSHOT COHERENCE")
    print("=" * 100)
    print(
        f"IDENTITY             : "
        f"{'PASS' if identity_pass else 'FAIL'}"
    )
    print(
        f"TEMPORAL ORDER       : "
        f"{temporal_reason}"
    )
    print(
        f"FIELD COHERENCE      : "
        f"{'PASS' if coherence_pass else 'FAIL'}"
    )

    if coherence_problems:
        for problem in coherence_problems:
            print(f"  - {problem}")

    print()
    print("=" * 100)
    print("SNAPSHOT EVIDENCE")
    print("=" * 100)

    if snapshots:
        for index, item in enumerate(snapshots, start=1):
            print(
                f"{index:>3} | "
                f"{item.get('snapshot')} | "
                f"{item.get('timestamp')} | "
                f"positions={item.get('positions')} | "
                f"risk={item.get('risk')} | "
                f"PnL={item.get('pnl')}"
            )
    else:
        print("No usable snapshots observed.")

    print()
    print("=" * 100)
    print("TEMPORAL EVIDENCE GATE")
    print("=" * 100)

    if (
        identity_pass
        and coherence_pass
        and temporal_pass
        and len(snapshots) >= MIN_SNAPSHOTS
    ):
        gate = "PASS"
        gate_reason = "TEMPORAL_EVIDENCE_COHERENT"
    elif not identity_pass:
        gate = "BLOCKED"
        gate_reason = identity_reason
    elif not coherence_pass:
        gate = "BLOCKED"
        gate_reason = "SNAPSHOT_FIELD_COHERENCE_FAILURE"
    elif not temporal_pass:
        gate = "BLOCKED"
        gate_reason = temporal_reason
    else:
        gate = "INSUFFICIENT_DATA"
        gate_reason = (
            "MINIMUM_TWO_TEMPORAL_SNAPSHOTS_REQUIRED"
        )

    print(f"Gate state : {gate}")
    print(f"Reason     : {gate_reason}")

    baseline_after = db_baseline()

    invariant_pass = (
        baseline_before["rows"]
        == baseline_after["rows"]
        and baseline_before["size"]
        == baseline_after["size"]
        and baseline_before["sha256"]
        == baseline_after["sha256"]
    )

    print()
    print("=" * 100)
    print("PRODUCTION DATABASE INVARIANT")
    print("=" * 100)
    print(f"Before rows  : {baseline_before['rows']}")
    print(f"After rows   : {baseline_after['rows']}")
    print(f"Before size  : {baseline_before['size']}")
    print(f"After size   : {baseline_after['size']}")
    print(
        f"Before SHA256: "
        f"{baseline_before['sha256']}"
    )
    print(
        f"After SHA256 : "
        f"{baseline_after['sha256']}"
    )
    print(
        "PRODUCTION DB INVARIANT : "
        f"{'PASS' if invariant_pass else 'FAIL'}"
    )

    final_verdict = (
        "PASS"
        if gate == "PASS" and invariant_pass
        else gate
    )

    print()
    print("=" * 100)
    print("LIVE PAPER PORTFOLIO TEMPORAL EVIDENCE ACCUMULATION + "
          "SNAPSHOT COHERENCE GATE VERDICT")
    print("=" * 100)
    print(
        f"UPSTREAM_STATE_CONSUMED : "
        f"{'PASS' if upstream_frontier == UPSTREAM_FRONTIER else 'FAIL'}"
    )
    print(
        f"TEMPORAL_EVIDENCE       : {evidence_status}"
    )
    print(
        f"SNAPSHOT_IDENTITY       : "
        f"{'PASS' if identity_pass else 'FAIL'}"
    )
    print(
        f"TEMPORAL_ORDER          : "
        f"{temporal_reason}"
    )
    print(
        f"SNAPSHOT_COHERENCE      : "
        f"{'PASS' if coherence_pass else 'FAIL'}"
    )
    print(
        f"PRODUCTION_ISOLATION    : "
        f"{'PASS' if invariant_pass else 'FAIL'}"
    )
    print(f"FRONTIER VERDICT        : {final_verdict}")

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
    print("Live data injection   : NONE")
    print("REAL ORDER EXECUTION : NONE")
    print("PAPER EXECUTION      : ANALYTICAL ONLY")

    if final_verdict == "PASS":
        print()
        print(
            "Temporal evidence is sufficient and snapshot coherence "
            "has passed."
        )
    else:
        print()
        print(
            "No synthetic temporal evidence was created."
        )
        print(
            "Additional independent live-paper snapshots are required "
            "before temporal verification can pass."
        )

    output = {
        "frontier": FRONTIER,
        "version": VERSION,
        "generated_at": now_iso(),
        "objective": (
            "Temporal evidence accumulation and snapshot coherence "
            "validation for the live paper portfolio."
        ),
        "safety": {
            "production_db_writes": False,
            "production_engine_run": False,
            "historical_repair": False,
            "direction_inference": False,
            "score_reconstruction": False,
            "synthetic_data": False,
            "live_data_injection": False,
            "real_order_execution": False,
            "paper_execution": "ANALYTICAL_ONLY",
        },
        "upstream": {
            "frontier": upstream_frontier,
            "current_snapshot": upstream_snapshot,
            "report": str(UPSTREAM_REPORT),
        },
        "temporal_evidence": {
            "snapshots_discovered": observed_count,
            "usable_snapshots": len(snapshots),
            "status": evidence_status,
            "reason": evidence_reason,
            "records": snapshots,
        },
        "snapshot_coherence": {
            "identity": (
                "PASS" if identity_pass else "FAIL"
            ),
            "temporal_order": temporal_reason,
            "field_coherence": (
                "PASS" if coherence_pass else "FAIL"
            ),
            "problems": coherence_problems,
        },
        "gate": {
            "state": gate,
            "reason": gate_reason,
        },
        "production_database_invariant": {
            "before": baseline_before,
            "after": baseline_after,
            "pass": invariant_pass,
        },
        "verdict": final_verdict,
    }

    OUTPUT_REPORT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_REPORT.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(f"Runtime report : {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()