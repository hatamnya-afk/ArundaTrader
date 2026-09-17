import os
import sys
import json
import hashlib
import subprocess
import re
from datetime import datetime, timezone


BASE_DIR = r"C:\Users\ASUS\ArundaTrader"
PIPELINE = os.path.join(BASE_DIR, "arunda_pipeline.py")

CYCLES_REQUIRED = 5
EXECUTION_ENABLED = False

EXPECTED_ASSETS = {
    "BTC", "ETH", "SOL", "XRP", "ADA",
    "DOGE", "SHIB", "LINK", "AVAX", "DOT",
    "LTC", "UNI", "AAVE", "SUI", "NEAR",
}


def canonical_snapshot_identity(snapshot):
    if snapshot.get("runtime_source") != "CURRENT_SUBPROCESS_RUN":
        raise RuntimeError(
            "runtime_source is not CURRENT_SUBPROCESS_RUN"
        )

    assets = snapshot.get("assets")

    if not isinstance(assets, list):
        raise RuntimeError("snapshot assets is not a list")

    if len(assets) != 15:
        raise RuntimeError(
            f"snapshot asset count={len(assets)}, expected=15"
        )

    identities = [x.get("asset") for x in assets]

    if any(not x for x in identities):
        raise RuntimeError("snapshot contains asset without identity")

    if len(set(identities)) != len(identities):
        raise RuntimeError("snapshot contains duplicate assets")

    if set(identities) != EXPECTED_ASSETS:
        missing = EXPECTED_ASSETS - set(identities)
        extra = set(identities) - EXPECTED_ASSETS

        raise RuntimeError(
            f"snapshot coverage mismatch | "
            f"missing={sorted(missing)} "
            f"extra={sorted(extra)}"
        )

    canonical = {
        "runtime_source": snapshot["runtime_source"],
        "engine_version": snapshot["engine_version"],
        "source": snapshot["source"],
        "timeframe": snapshot["timeframe"],
        "timestamp": snapshot["timestamp"],
        "assets": sorted(
            assets,
            key=lambda x: x["asset"],
        ),
    }

    raw = json.dumps(
        canonical,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()

    return f"RS-{digest}", raw


def extract_snapshot(output):
    marker = "ARUNDA_CURRENT_RUNTIME_SNAPSHOT="

    start = output.find(marker)

    if start < 0:
        raise RuntimeError(
            "CURRENT_RUNTIME_SNAPSHOT marker not found"
        )

    decoder = json.JSONDecoder()

    payload, _ = decoder.raw_decode(
        output[start + len(marker):]
    )

    return payload


def extract_canonical_table(
    output,
    header_pattern,
    row_pattern,
    name,
):
    headers = list(
        re.finditer(
            header_pattern,
            output,
            re.I | re.M,
        )
    )

    if not headers:
        raise RuntimeError(
            f"{name} canonical table header not found"
        )

    header = headers[-1]
    remaining = output[header.end():]

    row_regex = re.compile(
        row_pattern,
        re.I,
    )

    rows = {}
    started = False

    for line in remaining.splitlines():

        stripped = line.strip()

        if not stripped:
            if started:
                break
            continue

        if re.fullmatch(r"[-=]{3,}", stripped):
            continue

        match = row_regex.match(stripped)

        if match:
            started = True

            asset = match.group("asset")

            if asset in rows:
                raise RuntimeError(
                    f"duplicate canonical {name} row for {asset}"
                )

            rows[asset] = match.groupdict()

            continue

        if started:
            break

    if not rows:
        raise RuntimeError(
            f"{name} canonical table contains no rows"
        )

    return rows


def parse_signal_score(output):
    return extract_canonical_table(
        output,
        r"^\s*Asset\s*\|\s*State\s*\|\s*"
        r"Direction\s*\|\s*Score\s*$",

        r"^\s*"
        r"(?P<asset>[A-Z0-9]+)"
        r"\s*\|\s*"
        r"(?P<state>[A-Za-z0-9_]+)"
        r"\s*\|\s*"
        r"(?P<direction>LONG|SHORT|NONE)"
        r"\s*\|\s*"
        r"(?P<score>[+-]?[0-9]+(?:\.[0-9]+)?)"
        r"(?:\s*\|.*)?\s*$",

        "SIGNAL-SCORE",
    )


def parse_decision(output):
    return extract_canonical_table(
        output,
        r"^\s*Asset\s*\|\s*Decision\s*\|\s*"
        r"Direction\s*\|\s*Score",

        r"^\s*"
        r"(?P<asset>[A-Z0-9]+)"
        r"\s*\|\s*"
        r"(?P<state>ACTIONABLE|HOLD|REJECT)"
        r"\s*\|\s*"
        r"(?P<direction>LONG|SHORT|NONE)"
        r"\s*\|\s*"
        r"(?P<score>[+-]?[0-9]+(?:\.[0-9]+)?)"
        r"(?:\s*\|.*)?\s*$",

        "DECISION",
    )


def marker(output, name):
    matches = re.findall(
        rf"(?im)^\s*{re.escape(name)}\s*:\s*([^\r\n]*)$",
        output,
    )

    if not matches:
        raise RuntimeError(
            f"marker unavailable: {name}"
        )

    return matches[-1].strip()


def require_none(output, name):
    value = marker(output, name)

    if value.upper() != "NONE":
        raise RuntimeError(
            f"{name}={value}; expected NONE"
        )


def parse_count(output, name):
    matches = re.findall(
        rf"(?im)^\s*{re.escape(name)}\s*:\s*(\d+)\s*$",
        output,
    )

    if not matches:
        raise RuntimeError(
            f"count marker unavailable: {name}"
        )

    return int(matches[-1])


def verify_cycle(cycle_id, output):
    if EXECUTION_ENABLED is not False:
        raise RuntimeError(
            "EXECUTION_ENABLED is not False"
        )

    snapshot = extract_snapshot(output)

    snapshot_id, canonical_payload = (
        canonical_snapshot_identity(snapshot)
    )

    repeat_id = (
        "RS-" +
        hashlib.sha256(
            canonical_payload.encode("utf-8")
        ).hexdigest()
    )

    if snapshot_id != repeat_id:
        raise RuntimeError(
            "snapshot identity is not reproducible"
        )

    scores = parse_signal_score(output)
    decisions = parse_decision(output)

    if set(scores) != EXPECTED_ASSETS:
        raise RuntimeError(
            "SIGNAL/SCORE asset coverage mismatch"
        )

    if set(decisions) != EXPECTED_ASSETS:
        raise RuntimeError(
            "DECISION asset coverage mismatch"
        )

    for asset in EXPECTED_ASSETS:

        s = scores[asset]
        d = decisions[asset]

        if s["direction"] != d["direction"]:
            raise RuntimeError(
                f"{asset}: direction changed "
                f"{s['direction']} -> {d['direction']}"
            )

        if float(s["score"]) != float(d["score"]):
            raise RuntimeError(
                f"{asset}: score changed "
                f"{s['score']} -> {d['score']}"
            )

    for name in (
        "ORDER_SUBMISSION",
        "EXCHANGE_WRITE",
        "DB_WRITE",
        "SYNTHETIC",
        "FALLBACK",
        "INTERPOLATION",
        "FORWARD_FILL",
        "BACK_FILL",
        "PADDING",
        "FABRICATION",
    ):
        require_none(output, name)

    trade_ready = parse_count(
        output,
        "TRADE_READY",
    )

    order_intent = parse_count(
        output,
        "ORDER_INTENT",
    )

    if trade_ready == 0 and order_intent != 0:
        raise RuntimeError(
            "FAIL-CLOSED violation"
        )

    return {
        "cycle_id": cycle_id,
        "snapshot_id": snapshot_id,
        "snapshot_timestamp": snapshot["timestamp"],
        "assets": sorted(EXPECTED_ASSETS),
        "score_count": len(scores),
        "decision_count": len(decisions),
        "trade_ready": trade_ready,
        "order_intent": order_intent,
        "signal_active": sum(
            1 for x in scores.values()
            if x["state"].upper() == "ACTIVE"
        ),
        "signal_neutral": sum(
            1 for x in scores.values()
            if x["state"].upper() == "NEUTRAL"
        ),
        "decision_actionable": sum(
            1 for x in decisions.values()
            if x["state"].upper() == "ACTIONABLE"
        ),
        "decision_hold": sum(
            1 for x in decisions.values()
            if x["state"].upper() == "HOLD"
        ),
        "decision_reject": sum(
            1 for x in decisions.values()
            if x["state"].upper() == "REJECT"
        ),
    }


def main():

    print("=" * 90)
    print("ARUNDA TRADER — CP10 LIVE OBSERVATION MODE v0.1")
    print("=" * 90)
    print("MODE                  : MULTI-CYCLE OBSERVATION")
    print("REQUIRED CYCLES       : 5")
    print("SOURCE                : OFFICIAL arunda_pipeline.py")
    print("EXECUTION_ENABLED     : False")
    print("EXECUTION             : DISABLED")
    print("=" * 90)

    if not os.path.isfile(PIPELINE):
        print("CP10 = BLOCKED")
        print("BLOCKER = production pipeline not found")
        return 2

    cycles = []

    for cycle_id in range(
        1,
        CYCLES_REQUIRED + 1,
    ):

        print()
        print(
            f"CP10 CYCLE {cycle_id}/{CYCLES_REQUIRED}"
        )

        process = subprocess.run(
            [
                sys.executable,
                PIPELINE,
            ],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        output = (
            process.stdout
            + "\n"
            + process.stderr
        )

        if process.returncode != 0:
            print()
            print("=" * 90)
            print("CP10 = BLOCKED")
            print(
                f"BLOCKER = Cycle {cycle_id} "
                f"official runtime exit code "
                f"{process.returncode}"
            )
            print(
                "PROVENANCE = CURRENT PRODUCTION RUNTIME"
            )
            print(
                "MINIMAL REQUIRED ACTION = "
                "INVESTIGATE ONLY THIS CYCLE"
            )
            print("=" * 90)

            return 2

        try:
            report = verify_cycle(
                cycle_id,
                output,
            )

        except Exception as exc:

            print()
            print("=" * 90)
            print("CP10 = BLOCKED")
            print(
                f"BLOCKER = Cycle {cycle_id}: {exc}"
            )
            print(
                "PROVENANCE = CURRENT PRODUCTION RUNTIME"
            )
            print(
                "MINIMAL REQUIRED ACTION = "
                "INVESTIGATE ONLY THE REPORTED CYCLE"
            )
            print("=" * 90)

            return 2

        cycles.append(report)

        print(
            f"[PASS] Cycle {cycle_id}"
        )
        print(
            f"Snapshot ID : {report['snapshot_id']}"
        )
        print(
            f"Assets      : {len(report['assets'])}/15"
        )
        print(
            f"Trade Ready : {report['trade_ready']}"
        )
        print(
            f"Order Intent: {report['order_intent']}"
        )

    # ========================================================
    # CROSS-CYCLE INTEGRITY
    # ========================================================

    snapshot_ids = [
        x["snapshot_id"]
        for x in cycles
    ]

    if len(set(snapshot_ids)) != len(snapshot_ids):
        raise RuntimeError(
            "cross-cycle snapshot identity collision"
        )

    for cycle in cycles:

        if len(cycle["assets"]) != 15:
            raise RuntimeError(
                f"Cycle {cycle['cycle_id']}: "
                "asset coverage regression"
            )

        if cycle["trade_ready"] == 0:

            if cycle["order_intent"] != 0:
                raise RuntimeError(
                    f"Cycle {cycle['cycle_id']}: "
                    "FAIL-CLOSED regression"
                )

    print()
    print("=" * 90)
    print("CP10 LIVE OBSERVATION FINAL REPORT")
    print("=" * 90)

    print("CP10                    : PASS")
    print("STATUS                  : CLOSED / VERIFIED")
    print("CYCLES                  : 5/5")
    print("EXECUTION               : DISABLED")

    print()
    print("CROSS-CYCLE SNAPSHOT")
    print("--------------------")

    for cycle in cycles:
        print(
            f"Cycle {cycle['cycle_id']} | "
            f"{cycle['snapshot_id']} | "
            f"{cycle['snapshot_timestamp']}"
        )

    print()
    print("ASSET COVERAGE")
    print("--------------")

    for cycle in cycles:
        print(
            f"Cycle {cycle['cycle_id']} | "
            f"Expected=15 | "
            f"Actual={len(cycle['assets'])} | "
            f"Missing=0 | Extra=0 | Duplicates=0"
        )

    print()
    print("SIGNAL / SCORE")
    print("--------------")

    for cycle in cycles:
        print(
            f"Cycle {cycle['cycle_id']} | "
            f"Score={cycle['score_count']} | "
            f"ACTIVE={cycle['signal_active']} | "
            f"NEUTRAL={cycle['signal_neutral']}"
        )

    print()
    print("DECISION")
    print("--------")

    for cycle in cycles:
        print(
            f"Cycle {cycle['cycle_id']} | "
            f"ACTIONABLE={cycle['decision_actionable']} | "
            f"HOLD={cycle['decision_hold']} | "
            f"REJECT={cycle['decision_reject']}"
        )

    print()
    print("FAIL-CLOSED")
    print("-----------")

    for cycle in cycles:
        print(
            f"Cycle {cycle['cycle_id']} | "
            f"TRADE_READY={cycle['trade_ready']} | "
            f"ORDER_INTENT={cycle['order_intent']}"
        )

    print()
    print("CROSS-CYCLE INTEGRITY")
    print("---------------------")
    print("ASSET COVERAGE REGRESSION : NONE")
    print("MISSING ASSETS            : NONE")
    print("EXTRA ASSETS              : NONE")
    print("DUPLICATE ASSETS          : NONE")
    print("SNAPSHOT COLLISION        : NONE")
    print("RANDOM SNAPSHOT ID        : NONE")
    print("DB-ROW SNAPSHOT ID        : NONE")
    print("DIRECTION FABRICATION     : NONE")
    print("SCORE FABRICATION         : NONE")
    print("SILENT FALLBACK           : NONE")
    print("FAIL-CLOSED REGRESSION    : NONE")

    print()
    print("WRITE / EXECUTION")
    print("-----------------")
    print("DB WRITE                  : NONE")
    print("INSERT                    : NONE")
    print("UPDATE                    : NONE")
    print("DELETE                    : NONE")
    print("EXCHANGE WRITE            : NONE")
    print("ORDER SUBMISSION          : NONE")
    print("EXECUTION                 : DISABLED")

    print()
    print("DATA SAFETY")
    print("-----------")
    print("SYNTHETIC                 : NONE")
    print("FALLBACK                  : NONE")
    print("INTERPOLATION             : NONE")
    print("FORWARD_FILL              : NONE")
    print("BACK_FILL                 : NONE")
    print("PADDING                   : NONE")
    print("FABRICATION               : NONE")

    print()
    print("CP10 = PASS")
    print("STATUS = CLOSED / VERIFIED")
    print("EXECUTION = DISABLED")
    print(
        "NEXT CHECKPOINT = "
        "CP11 — EXECUTION RELEASE PREFLIGHT"
    )

    print()
    print(
        "ONE CHECKPOINT -> MULTI-CYCLE RUNTIME "
        "OBSERVATION -> ONE REPORT -> STOP"
    )

    print("=" * 90)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())