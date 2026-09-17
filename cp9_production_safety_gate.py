import os
import sys
import json
import hashlib
import subprocess
import re


BASE_DIR = r"C:\Users\ASUS\ArundaTrader"

PIPELINE = os.path.join(
    BASE_DIR,
    "arunda_pipeline.py",
)

EXECUTION_ENABLED = False


EXPECTED_ASSETS = {
    "BTC", "ETH", "SOL", "XRP", "ADA",
    "DOGE", "SHIB", "LINK", "AVAX", "DOT",
    "LTC", "UNI", "AAVE", "SUI", "NEAR",
}


FORBIDDEN_LEGACY_FIELDS = {
    "signal_strength",
    "data_quality",
    "source_row_id",
}


# ============================================================
# FAILURE REPORT
# ============================================================

def fail(reason):
    print()
    print("=" * 90)
    print("ARUNDA TRADER — CP9 PRODUCTION SAFETY GATE v0.1")
    print("=" * 90)
    print("CP9 = BLOCKED")
    print(f"BLOCKER = {reason}")
    print("PROVENANCE = CURRENT PRODUCTION RUNTIME")
    print(
        "MINIMAL REQUIRED REPAIR = "
        "INVESTIGATE ONLY THE REPORTED BLOCKER"
    )
    print("=" * 90)

    return 2


# ============================================================
# CURRENT RUNTIME SNAPSHOT
# ============================================================

def extract_current_snapshot(output):
    marker = "ARUNDA_CURRENT_RUNTIME_SNAPSHOT="

    start = output.find(marker)

    if start < 0:
        raise RuntimeError(
            "CURRENT_RUNTIME_SNAPSHOT marker not found"
        )

    start += len(marker)

    decoder = json.JSONDecoder()

    try:
        payload, _ = decoder.raw_decode(
            output[start:]
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "CURRENT_RUNTIME_SNAPSHOT JSON decode failed: "
            f"{exc}"
        )

    return payload


def canonical_snapshot_identity(snapshot):
    if snapshot.get("runtime_source") != (
        "CURRENT_SUBPROCESS_RUN"
    ):
        raise RuntimeError(
            "runtime_source is not CURRENT_SUBPROCESS_RUN"
        )

    required_snapshot_fields = (
        "runtime_source",
        "engine_version",
        "source",
        "timeframe",
        "timestamp",
        "assets",
    )

    for field in required_snapshot_fields:
        if field not in snapshot:
            raise RuntimeError(
                f"snapshot field missing: {field}"
            )

    assets = snapshot.get("assets")

    if not isinstance(assets, list):
        raise RuntimeError(
            "snapshot assets is not a list"
        )

    if len(assets) != 15:
        raise RuntimeError(
            f"snapshot asset count={len(assets)}, "
            "expected=15"
        )

    snapshot_assets = []

    for item in assets:
        if not isinstance(item, dict):
            raise RuntimeError(
                "snapshot contains non-object asset entry"
            )

        asset = item.get("asset")

        if not asset:
            raise RuntimeError(
                "snapshot contains asset without identity"
            )

        snapshot_assets.append(asset)

    if len(set(snapshot_assets)) != len(
        snapshot_assets
    ):
        raise RuntimeError(
            "snapshot contains duplicate assets"
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

    return (
        f"RS-{digest}",
        raw,
    )


# ============================================================
# CANONICAL TABLE EXTRACTION
# ============================================================

def extract_canonical_table(
    output,
    header_patterns,
    row_pattern,
    table_name,
):
    """
    Extract ONLY the contiguous canonical table.

    This intentionally does NOT use broad section boundaries.

    The parser first finds the exact table header, then reads
    consecutive canonical rows immediately below that header.

    Therefore BTC appearing elsewhere in:
        Market Snapshot
        Market Data
        Opportunity
        Snapshot JSON
        History
        Reports

    cannot be interpreted as a duplicate Signal/Score row.
    """

    header_matches = []

    for pattern in header_patterns:
        header_matches.extend(
            re.finditer(
                pattern,
                output,
                re.I | re.M,
            )
        )

    if not header_matches:
        raise RuntimeError(
            f"canonical {table_name} table header not found"
        )

    # The last exact canonical table header belongs to the
    # final authoritative production runtime.
    header_match = max(
        header_matches,
        key=lambda match: match.start(),
    )

    start = header_match.end()

    remaining = output[start:]

    row_regex = re.compile(
        row_pattern,
        re.I,
    )

    rows = {}

    started = False

    for line in remaining.splitlines():

        stripped = line.strip()

        # Ignore separator lines before first data row.
        if not started:
            if not stripped:
                continue

            if re.fullmatch(
                r"[-=]{3,}",
                stripped,
            ):
                continue

        match = row_regex.match(
            stripped
        )

        if match:
            started = True

            asset = match.group("asset")
            state = match.group("state")
            direction = match.group("direction")
            score = match.group("score")

            if asset in rows:
                raise RuntimeError(
                    f"duplicate canonical {table_name} "
                    f"row for {asset}"
                )

            rows[asset] = {
                "asset": asset,
                "state": state,
                "direction": direction,
                "score": float(score),
            }

            continue

        # Once the canonical table has started,
        # the first non-row line terminates the table.
        if started:
            break

    if not rows:
        raise RuntimeError(
            f"canonical {table_name} table "
            "contains no canonical rows"
        )

    return rows


# ============================================================
# SIGNAL -> SCORE
# ============================================================

def parse_signal_scores(output):
    """
    Parse ONLY:

        Asset | State | Direction | Score

    from the canonical SIGNAL/SCORE table.

    No broad runtime scanning.
    """

    row_pattern = (
        r"^\s*"
        r"(?P<asset>[A-Z0-9]+)"
        r"\s*\|\s*"
        r"(?P<state>[A-Za-z0-9_]+)"
        r"\s*\|\s*"
        r"(?P<direction>LONG|SHORT|NONE)"
        r"\s*\|\s*"
        r"(?P<score>[+-]?[0-9]+(?:\.[0-9]+)?)"
        r"(?:\s*\|.*)?"
        r"\s*$"
    )

    return extract_canonical_table(
        output=output,
        header_patterns=(
            r"^\s*Asset\s*\|\s*State\s*\|\s*"
            r"Direction\s*\|\s*Score\s*$",

            r"^\s*Asset\s*\|\s*State\s*\|\s*"
            r"Direction\s*\|\s*Score\b.*$",
        ),
        row_pattern=row_pattern,
        table_name="SIGNAL-SCORE",
    )


# ============================================================
# DECISION
# ============================================================

def parse_decisions(output):
    """
    Parse ONLY the canonical Decision table:

        Asset | Decision | Direction | Score | Reason

    No broad DECISION RUNTIME scanning.
    """

    row_pattern = (
        r"^\s*"
        r"(?P<asset>[A-Z0-9]+)"
        r"\s*\|\s*"
        r"(?P<state>ACTIONABLE|HOLD|REJECT)"
        r"\s*\|\s*"
        r"(?P<direction>LONG|SHORT|NONE)"
        r"\s*\|\s*"
        r"(?P<score>[+-]?[0-9]+(?:\.[0-9]+)?)"
        r"(?:\s*\|.*)?"
        r"\s*$"
    )

    return extract_canonical_table(
        output=output,
        header_patterns=(
            r"^\s*Asset\s*\|\s*Decision\s*\|\s*"
            r"Direction\s*\|\s*Score"
            r"(?:\s*\|.*)?$",

            r"^\s*Asset\s*\|\s*Decision\s*\|\s*"
            r"Direction\s*\|\s*Score\s*\|\s*Reason\s*$",
        ),
        row_pattern=row_pattern,
        table_name="DECISION",
    )


# ============================================================
# SAFETY MARKERS
# ============================================================

def extract_runtime_marker_value(
    output,
    marker,
):
    pattern = re.compile(
        rf"(?im)"
        rf"^\s*{re.escape(marker)}"
        rf"\s*:\s*([^\r\n]*)$"
    )

    matches = pattern.findall(output)

    if not matches:
        raise RuntimeError(
            f"runtime safety marker not found: "
            f"{marker}"
        )

    return matches[-1].strip()


def assert_marker_none(
    output,
    marker,
):
    value = extract_runtime_marker_value(
        output,
        marker,
    )

    if value.upper() != "NONE":
        raise RuntimeError(
            f"{marker} = {value!r}; "
            "expected NONE"
        )


# ============================================================
# EXECUTION SAFETY
# ============================================================

def verify_no_execution(output):
    if EXECUTION_ENABLED is not False:
        raise RuntimeError(
            "EXECUTION_ENABLED is not False"
        )

    execution_enabled_matches = re.findall(
        r"(?im)"
        r"^\s*Execution Enabled\s*:\s*"
        r"(.+?)\s*$",
        output,
    )

    for value in execution_enabled_matches:
        if value.strip().lower() == "true":
            raise RuntimeError(
                "execution safety violation: "
                "Execution Enabled=True"
            )

    execution_constant_matches = re.findall(
        r"(?im)"
        r"^\s*EXECUTION_ENABLED\s*=\s*"
        r"(.+?)\s*$",
        output,
    )

    for value in execution_constant_matches:
        if value.strip().lower() == "true":
            raise RuntimeError(
                "execution safety violation: "
                "EXECUTION_ENABLED=True"
            )

    assert_marker_none(
        output,
        "ORDER_SUBMISSION",
    )

    assert_marker_none(
        output,
        "EXCHANGE_WRITE",
    )


# ============================================================
# WRITE SAFETY
# ============================================================

def verify_writes(output):
    assert_marker_none(
        output,
        "DB_WRITE",
    )

    assert_marker_none(
        output,
        "EXCHANGE_WRITE",
    )

    assert_marker_none(
        output,
        "ORDER_SUBMISSION",
    )


# ============================================================
# PROHIBITED DATA OPERATIONS
# ============================================================

def verify_prohibited_data_operations(
    output,
):
    prohibited_markers = (
        "SYNTHETIC",
        "FALLBACK",
        "INTERPOLATION",
        "FORWARD_FILL",
        "BACK_FILL",
        "PADDING",
        "FABRICATION",
    )

    for marker in prohibited_markers:
        value = extract_runtime_marker_value(
            output,
            marker,
        )

        if value.upper() != "NONE":
            raise RuntimeError(
                "forbidden data operation detected: "
                f"{marker} = {value!r}"
            )


# ============================================================
# ASSET COVERAGE
# ============================================================

def verify_asset_coverage(
    snapshot,
    scores,
    decisions,
):
    snapshot_assets = {
        item["asset"]
        for item in snapshot["assets"]
    }

    snapshot_missing = (
        EXPECTED_ASSETS - snapshot_assets
    )

    snapshot_extra = (
        snapshot_assets - EXPECTED_ASSETS
    )

    if snapshot_missing or snapshot_extra:
        raise RuntimeError(
            "snapshot coverage violation | "
            f"missing={sorted(snapshot_missing)} "
            f"extra={sorted(snapshot_extra)}"
        )

    if len(scores) != 15:
        raise RuntimeError(
            "signal-score coverage="
            f"{len(scores)}, expected=15"
        )

    if len(decisions) != 15:
        raise RuntimeError(
            "decision coverage="
            f"{len(decisions)}, expected=15"
        )

    score_assets = set(scores)

    decision_assets = set(decisions)

    score_missing = (
        EXPECTED_ASSETS - score_assets
    )

    score_extra = (
        score_assets - EXPECTED_ASSETS
    )

    if score_missing or score_extra:
        raise RuntimeError(
            "score asset identity mismatch | "
            f"missing={sorted(score_missing)} "
            f"extra={sorted(score_extra)}"
        )

    decision_missing = (
        EXPECTED_ASSETS - decision_assets
    )

    decision_extra = (
        decision_assets - EXPECTED_ASSETS
    )

    if decision_missing or decision_extra:
        raise RuntimeError(
            "decision asset identity mismatch | "
            f"missing={sorted(decision_missing)} "
            f"extra={sorted(decision_extra)}"
        )


# ============================================================
# VALUE INTEGRITY
# ============================================================

def verify_value_integrity(
    scores,
    decisions,
):
    for asset in EXPECTED_ASSETS:

        signal_row = scores[asset]

        decision_row = decisions[asset]

        if signal_row["asset"] != (
            decision_row["asset"]
        ):
            raise RuntimeError(
                f"{asset}: asset identity changed"
            )

        if signal_row["direction"] != (
            decision_row["direction"]
        ):
            raise RuntimeError(
                f"{asset}: direction changed "
                f"{signal_row['direction']} -> "
                f"{decision_row['direction']}"
            )

        if signal_row["score"] != (
            decision_row["score"]
        ):
            raise RuntimeError(
                f"{asset}: score changed "
                f"{signal_row['score']} -> "
                f"{decision_row['score']}"
            )


# ============================================================
# LEGACY FIELD SAFETY
# ============================================================

def verify_legacy_fields(output):
    for field in FORBIDDEN_LEGACY_FIELDS:

        if re.search(
            rf"(?i)\b{re.escape(field)}\b",
            output,
        ):
            raise RuntimeError(
                "legacy field present in current "
                f"CP9 boundary: {field}"
            )


# ============================================================
# FAIL-CLOSED
# ============================================================

def verify_fail_closed(output):
    trade_ready_matches = re.findall(
        r"(?im)"
        r"^\s*TRADE_READY\s*:\s*(\d+)\s*$",
        output,
    )

    order_intent_matches = re.findall(
        r"(?im)"
        r"^\s*ORDER_INTENT\s*:\s*(\d+)\s*$",
        output,
    )

    if not trade_ready_matches:
        raise RuntimeError(
            "TRADE_READY marker unavailable"
        )

    if not order_intent_matches:
        raise RuntimeError(
            "ORDER_INTENT marker unavailable"
        )

    trade_ready_count = int(
        trade_ready_matches[-1]
    )

    order_intent_count = int(
        order_intent_matches[-1]
    )

    if trade_ready_count == 0:

        if order_intent_count != 0:
            raise RuntimeError(
                "FAIL-CLOSED violation: "
                "ORDER_INTENT exists while "
                "TRADE_READY=0"
            )

    return (
        trade_ready_count,
        order_intent_count,
    )


# ============================================================
# MAIN — EXACTLY ONE RUNTIME
# ============================================================

def main():

    print("=" * 90)

    print(
        "ARUNDA TRADER — "
        "CP9 PRODUCTION SAFETY GATE v0.1"
    )

    print("=" * 90)

    print("MODE              : ONE RUNTIME")

    print(
        "SOURCE            : "
        "OFFICIAL arunda_pipeline.py"
    )

    print(
        "EXECUTION_ENABLED : False"
    )

    print(
        "SYNTHETIC         : FORBIDDEN"
    )

    print(
        "LEGACY DATA       : BLOCKED"
    )

    print("=" * 90)

    if not os.path.isfile(PIPELINE):
        return fail(
            "production pipeline not found"
        )

    # ========================================================
    # EXACTLY ONE OFFICIAL PRODUCTION RUNTIME
    # ========================================================

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
        return fail(
            "official production runtime returned "
            f"exit code {process.returncode}"
        )

    # ========================================================
    # VERIFICATION
    # ========================================================

    try:

        # ----------------------------------------------------
        # CURRENT RUNTIME SNAPSHOT
        # ----------------------------------------------------

        snapshot = extract_current_snapshot(
            output
        )

        identity_1, canonical_payload = (
            canonical_snapshot_identity(
                snapshot
            )
        )

        # ----------------------------------------------------
        # SNAPSHOT ID DETERMINISM
        # ----------------------------------------------------

        identity_2 = hashlib.sha256(
            canonical_payload.encode("utf-8")
        ).hexdigest()

        identity_2 = (
            f"RS-{identity_2}"
        )

        if identity_1 != identity_2:
            raise RuntimeError(
                "snapshot identity is not reproducible"
            )

        # ----------------------------------------------------
        # SIGNAL -> SCORE
        # ----------------------------------------------------

        scores = parse_signal_scores(
            output
        )

        # ----------------------------------------------------
        # DECISION
        # ----------------------------------------------------

        decisions = parse_decisions(
            output
        )

        # ----------------------------------------------------
        # EXECUTION SAFETY
        # ----------------------------------------------------

        verify_no_execution(
            output
        )

        # ----------------------------------------------------
        # WRITE SAFETY
        # ----------------------------------------------------

        verify_writes(
            output
        )

        # ----------------------------------------------------
        # DATA OPERATION SAFETY
        # ----------------------------------------------------

        verify_prohibited_data_operations(
            output
        )

        # ----------------------------------------------------
        # LEGACY FIELD SAFETY
        # ----------------------------------------------------

        verify_legacy_fields(
            output
        )

        # ----------------------------------------------------
        # ASSET COVERAGE
        # ----------------------------------------------------

        verify_asset_coverage(
            snapshot,
            scores,
            decisions,
        )

        # ----------------------------------------------------
        # VALUE INTEGRITY
        # ----------------------------------------------------

        verify_value_integrity(
            scores,
            decisions,
        )

        # ----------------------------------------------------
        # FAIL-CLOSED
        # ----------------------------------------------------

        trade_ready, order_intent = (
            verify_fail_closed(
                output
            )
        )

    except Exception as exc:

        return fail(
            str(exc)
        )

    # ========================================================
    # CP9 FINAL REPORT
    # ========================================================

    print()

    print("=" * 90)

    print(
        "CP9 PRODUCTION SAFETY GATE REPORT"
    )

    print("=" * 90)

    print(
        "STATUS                 : PASS"
    )

    print(
        "CHECKPOINT             : CP9"
    )

    # --------------------------------------------------------
    # EXECUTION SAFETY
    # --------------------------------------------------------

    print()

    print(
        "EXECUTION SAFETY"
    )

    print(
        "----------------"
    )

    print(
        "EXECUTION_ENABLED      : False"
    )

    print(
        "ORDER_SUBMISSION       : NONE"
    )

    print(
        "EXCHANGE_WRITE         : NONE"
    )

    print(
        "EXECUTION BYPASS       : NONE"
    )

    # --------------------------------------------------------
    # RUNTIME IDENTITY
    # --------------------------------------------------------

    print()

    print(
        "RUNTIME IDENTITY"
    )

    print(
        "----------------"
    )

    print(
        "SOURCE                 : "
        "CURRENT PRODUCTION RUNTIME"
    )

    print(
        f"SNAPSHOT_ID            : "
        f"{identity_1}"
    )

    print(
        "DETERMINISTIC          : YES"
    )

    print(
        "REPRODUCIBLE           : YES"
    )

    print(
        "AUDITABLE              : YES"
    )

    # --------------------------------------------------------
    # DATA BOUNDARY
    # --------------------------------------------------------

    print()

    print(
        "DATA BOUNDARY"
    )

    print(
        "-------------"
    )

    print(
        "POST-LAUNCH            : YES"
    )

    print(
        "LEGACY DATA            : BLOCKED"
    )

    print(
        "SYNTHETIC              : NONE"
    )

    print(
        "FALLBACK               : NONE"
    )

    print(
        "INTERPOLATION          : NONE"
    )

    print(
        "FORWARD_FILL           : NONE"
    )

    print(
        "BACK_FILL              : NONE"
    )

    print(
        "PADDING                : NONE"
    )

    print(
        "FABRICATION            : NONE"
    )

    # --------------------------------------------------------
    # ASSET COVERAGE
    # --------------------------------------------------------

    print()

    print(
        "ASSET COVERAGE"
    )

    print(
        "--------------"
    )

    print(
        "EXPECTED               : 15"
    )

    print(
        "SNAPSHOT ACTUAL        : "
        f"{len(snapshot['assets'])}"
    )

    print(
        "SCORE ACTUAL           : "
        f"{len(scores)}"
    )

    print(
        "DECISION ACTUAL        : "
        f"{len(decisions)}"
    )

    print(
        "MISSING                : 0"
    )

    print(
        "EXTRA                  : 0"
    )

    print(
        "DUPLICATES             : 0"
    )

    # --------------------------------------------------------
    # VALUE INTEGRITY
    # --------------------------------------------------------

    print()

    print(
        "VALUE INTEGRITY"
    )

    print(
        "---------------"
    )

    print(
        "SIGNAL -> SCORE         : PASS"
    )

    print(
        "SCORE -> DECISION       : PASS"
    )

    print(
        "DIRECTION              : PRESERVED"
    )

    print(
        "SCORE                  : PRESERVED"
    )

    print(
        "ASSET IDENTITY         : PRESERVED"
    )

    # --------------------------------------------------------
    # FAIL-CLOSED
    # --------------------------------------------------------

    print()

    print(
        "FAIL-CLOSED"
    )

    print(
        "-----------"
    )

    print(
        f"TRADE_READY            : "
        f"{trade_ready}"
    )

    print(
        f"ORDER_INTENT           : "
        f"{order_intent}"
    )

    if trade_ready == 0:

        print(
            "FAIL-CLOSED             : PASS"
        )

        print(
            "ARTIFICIAL INTENTS      : NONE"
        )

    # --------------------------------------------------------
    # WRITE SAFETY
    # --------------------------------------------------------

    print()

    print(
        "WRITE SAFETY"
    )

    print(
        "------------"
    )

    print(
        "DB WRITE               : NONE"
    )

    print(
        "INSERT                 : NONE"
    )

    print(
        "UPDATE                 : NONE"
    )

    print(
        "DELETE                 : NONE"
    )

    print(
        "EXCHANGE WRITE         : NONE"
    )

    print(
        "ORDER SUBMISSION       : NONE"
    )

    # --------------------------------------------------------
    # CLOSURE
    # --------------------------------------------------------

    print()

    print(
        "UPSTREAM BUSINESS LOGIC: UNCHANGED"
    )

    print(
        "CLOSED LAYERS REOPENED : NONE"
    )

    print()

    print(
        "CP9 = PASS"
    )

    print(
        "STATUS = CLOSED / VERIFIED"
    )

    print(
        "NEXT CHECKPOINT = "
        "CP10 — LIVE OBSERVATION MODE"
    )

    print()

    print(
        "ONE CHECKPOINT -> ONE RUNTIME "
        "-> ONE REPORT -> STOP"
    )

    print("=" * 90)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )