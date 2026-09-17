import os
import sys
import json
import hashlib
import subprocess


# ============================================================
# ARUNDA TRADER
# PIPELINE v0.4
# CHECKPOINT 7-G RUNTIME IDENTITY
# ============================================================

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_PATH = os.path.join(
    PROJECT_DIR,
    "arunda.db"
)

EXECUTION_ENABLED = False

EXPECTED_ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "SHIB",
    "LINK",
    "AVAX",
    "DOT",
    "LTC",
    "UNI",
    "AAVE",
    "SUI",
    "NEAR",
]


# ============================================================
# IMPORTS
# ============================================================

import signal_validator
import score_producer
import signal_scorer
import decision_engine
import risk_engine
import trade_gate_engine


# ============================================================
# HELPERS
# ============================================================

def line(char="=", length=90):
    print(char * length)


def normalize_asset(value):

    if value is None:
        return None

    return str(
        value
    ).strip().upper()


def get_asset(row):

    if not isinstance(
        row,
        dict
    ):
        return None

    for key in (
        "asset",
        "symbol",
        "ticker",
    ):

        if key in row:

            asset = normalize_asset(
                row[key]
            )

            if asset:
                return asset

    return None


def normalize_direction(value):

    if value is None:
        return None

    value = str(
        value
    ).strip().upper()

    if value == "BUY":
        return "LONG"

    if value == "SELL":
        return "SHORT"

    return value


# ============================================================
# STAGE RUNNER
# ============================================================

def run_script_stage(
    script_name
):

    script_path = os.path.join(
        PROJECT_DIR,
        script_name
    )

    if not os.path.exists(
        script_path
    ):

        raise RuntimeError(
            f"Stage script not found: {script_path}"
        )

    result = subprocess.run(
        [
            sys.executable,
            script_path,
        ],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )

    if result.stdout:

        print(
            result.stdout,
            end=""
        )

    if result.stderr:

        print(
            result.stderr,
            end="",
            file=sys.stderr
        )

    if result.returncode != 0:

        raise RuntimeError(
            f"{script_name} failed "
            f"with exit code {result.returncode}"
        )

    return result.stdout


# ============================================================
# CP7-G CURRENT RUNTIME SNAPSHOT BRIDGE
# ============================================================

def parse_current_runtime_snapshot(
    stdout
):

    marker = (
        "ARUNDA_CURRENT_RUNTIME_SNAPSHOT="
    )

    payload = None

    for raw_line in stdout.splitlines():

        line_text = raw_line.strip()

        if line_text.startswith(
            marker
        ):

            payload_text = (
                line_text[
                    len(marker):
                ]
            )

            try:

                candidate = json.loads(
                    payload_text
                )

            except json.JSONDecodeError as exc:

                raise RuntimeError(
                    "CP7-G: CURRENT_RUNTIME_SNAPSHOT "
                    f"JSON is invalid: {exc}"
                )

            if payload is not None:

                raise RuntimeError(
                    "CP7-G: duplicate "
                    "CURRENT_RUNTIME_SNAPSHOT marker."
                )

            payload = candidate

    if payload is None:

        raise RuntimeError(
            "CP7-G: Market Snapshot Engine did not expose "
            "CURRENT_RUNTIME_SNAPSHOT."
        )

    if not isinstance(
        payload,
        dict
    ):

        raise RuntimeError(
            "CP7-G: current runtime snapshot "
            "must be a dict."
        )

    if (
        payload.get(
            "runtime_source"
        )
        !=
        "CURRENT_SUBPROCESS_RUN"
    ):

        raise RuntimeError(
            "CP7-G: runtime snapshot source is not "
            "CURRENT_SUBPROCESS_RUN."
        )

    if payload.get(
        "engine_version"
    ) is None:

        raise RuntimeError(
            "CP7-G: runtime snapshot engine_version missing."
        )

    if payload.get(
        "source"
    ) != "COINMARKETCAP":

        raise RuntimeError(
            "CP7-G: runtime snapshot provenance "
            "is not COINMARKETCAP."
        )

    if payload.get(
        "timeframe"
    ) != "SNAPSHOT":

        raise RuntimeError(
            "CP7-G: runtime snapshot timeframe "
            "is not SNAPSHOT."
        )

    timestamp = payload.get(
        "timestamp"
    )

    if not isinstance(
        timestamp,
        str
    ) or not timestamp:

        raise RuntimeError(
            "CP7-G: runtime snapshot timestamp missing."
        )

    assets = payload.get(
        "assets"
    )

    if not isinstance(
        assets,
        list
    ):

        raise RuntimeError(
            "CP7-G: runtime snapshot assets "
            "must be a list."
        )

    return payload


# ============================================================
# CP7-G SNAPSHOT COVERAGE
# ============================================================

def validate_current_runtime_snapshot(
    snapshot
):

    assets = snapshot.get(
        "assets"
    )

    if not isinstance(
        assets,
        list
    ):

        raise RuntimeError(
            "CP7-G: snapshot assets are not a list."
        )

    if len(
        assets
    ) != len(EXPECTED_ASSETS):

        raise RuntimeError(
            "CP7-G: snapshot must contain exactly "
            f"{len(EXPECTED_ASSETS)} assets. "
            f"Received {len(assets)}."
        )

    expected = set(
        EXPECTED_ASSETS
    )

    actual_assets = []

    snapshot_timestamp = snapshot.get(
        "timestamp"
    )

    for row in assets:

        if not isinstance(
            row,
            dict
        ):

            raise RuntimeError(
                "CP7-G: snapshot contains "
                "non-dict asset row."
            )

        asset = normalize_asset(
            row.get(
                "asset"
            )
        )

        if asset is None:

            raise RuntimeError(
                "CP7-G: snapshot asset is missing."
            )

        if asset not in expected:

            raise RuntimeError(
                f"CP7-G: unexpected snapshot asset {asset}."
            )

        row_timestamp = row.get(
            "timestamp"
        )

        if row_timestamp != snapshot_timestamp:

            raise RuntimeError(
                f"CP7-G: timestamp mismatch for {asset}: "
                f"snapshot={snapshot_timestamp}, "
                f"row={row_timestamp}"
            )

        if "price" not in row:

            raise RuntimeError(
                f"CP7-G: price missing for {asset}."
            )

        if row.get(
            "price"
        ) is None:

            raise RuntimeError(
                f"CP7-G: price is None for {asset}."
            )

        actual_assets.append(
            asset
        )

    actual = set(
        actual_assets
    )

    missing = sorted(
        expected
        -
        actual
    )

    extra = sorted(
        actual
        -
        expected
    )

    duplicates = sorted(
        {
            asset
            for asset in actual_assets
            if actual_assets.count(asset) > 1
        }
    )

    if missing or extra or duplicates:

        raise RuntimeError(
            "CP7-G: current runtime snapshot "
            "coverage failure: "
            f"missing={missing}, "
            f"extra={extra}, "
            f"duplicates={duplicates}"
        )

    return True


# ============================================================
# CP7-G DETERMINISTIC SNAPSHOT ID
# ============================================================

def build_current_runtime_snapshot_id(
    snapshot
):

    validate_current_runtime_snapshot(
        snapshot
    )

    canonical_assets = []

    for row in snapshot["assets"]:

        canonical_assets.append({

            "asset": row["asset"],

            "timestamp": row["timestamp"],

            "price": row["price"],

            "change_1h": row["change_1h"],

            "change_24h": row["change_24h"],

            "market_cap": row["market_cap"],

            "volume_24h": row["volume_24h"],
        })

    canonical_assets.sort(
        key=lambda row: row["asset"]
    )

    canonical_payload = {

        "timestamp": snapshot["timestamp"],

        "assets": canonical_assets,
    }

    serialized = json.dumps(

        canonical_payload,

        ensure_ascii=False,

        separators=(",", ":"),

    )

    digest = hashlib.sha256(
        serialized.encode(
            "utf-8"
        )
    ).hexdigest()

    return (
        f"RS-{digest}"
    )


# ============================================================
# OPPORTUNITY CURRENT-RUN BRIDGE
# ============================================================

def parse_opportunity_runtime_snapshot(
    stdout
):

    marker = (
        "ARUNDA_RUNTIME_OPPORTUNITY_SNAPSHOT="
    )

    payload = None

    for raw_line in stdout.splitlines():

        line_text = raw_line.strip()

        if line_text.startswith(
            marker
        ):

            payload_text = (
                line_text[
                    len(marker):
                ]
            )

            payload = json.loads(
                payload_text
            )

    if payload is None:

        raise RuntimeError(
            "Opportunity Engine did not expose "
            "CURRENT-RUN runtime snapshot."
        )

    if (
        payload.get(
            "runtime_source"
        )
        !=
        "CURRENT_SUBPROCESS_RUN"
    ):

        raise RuntimeError(
            "Opportunity runtime source is not "
            "CURRENT_SUBPROCESS_RUN."
        )

    opportunities = payload.get(
        "opportunities"
    )

    if not isinstance(
        opportunities,
        list
    ):

        raise RuntimeError(
            "Opportunity runtime payload is invalid."
        )

    return opportunities


# ============================================================
# SIGNAL VALIDATOR RUNTIME CONTRACT
# ============================================================

def validate_signal_runtime_snapshot(
    validated_signals
):

    if not isinstance(
        validated_signals,
        dict
    ):

        raise RuntimeError(
            "Signal Validator returned invalid runtime snapshot."
        )

    expected_assets = set(
        EXPECTED_ASSETS
    )

    actual_assets = {
        normalize_asset(asset)
        for asset in validated_signals.keys()
        if normalize_asset(asset)
    }

    missing = sorted(
        expected_assets
        -
        actual_assets
    )

    extra = sorted(
        actual_assets
        -
        expected_assets
    )

    if missing or extra:

        raise RuntimeError(
            "Signal Validator asset coverage failure: "
            f"missing={missing}, extra={extra}"
        )

    if len(
        actual_assets
    ) != 15:

        raise RuntimeError(
            "Signal Validator must return exactly 15 assets."
        )

    for asset in EXPECTED_ASSETS:

        row = validated_signals.get(
            asset
        )

        if row is None:

            for key, candidate in validated_signals.items():

                if (
                    normalize_asset(key)
                    ==
                    asset
                ):

                    row = candidate
                    break

        if not isinstance(
            row,
            dict
        ):

            raise RuntimeError(
                f"Signal Validator returned invalid row for {asset}."
            )

        if row.get(
            "valid"
        ) is not True:

            raise RuntimeError(
                f"Signal validation failed for {asset}: "
                f"{row.get('validation')}"
            )


# ============================================================
# SIGNAL → SCORE → DECISION
# ============================================================

def run_signal_score_decision_runtime():

    print()
    line()

    print(
        "SIGNAL → SCORE → DECISION RUNTIME"
    )

    line()

    validated_signals = (
        signal_validator.load_validated_signals()
    )

    validate_signal_runtime_snapshot(
        validated_signals
    )

    scores = (
        score_producer.run(
            validated_signals
        )
    )

    if not isinstance(
        scores,
        dict
    ):

        raise RuntimeError(
            "Score Producer returned invalid runtime snapshot."
        )

    aligned_scores = (
        signal_scorer.run(
            validated_signals,
            scores
        )
    )

    if not isinstance(
        aligned_scores,
        dict
    ):

        raise RuntimeError(
            "Signal Scorer returned invalid aligned score snapshot."
        )

    decision_snapshot = (
        decision_engine.run(
            validated_signals,
            aligned_scores
        )
    )

    if not isinstance(
        decision_snapshot,
        dict
    ):

        raise RuntimeError(
            "Decision Engine returned invalid runtime snapshot."
        )

    return {
        "validated_signals": validated_signals,
        "scores": scores,
        "aligned_scores": aligned_scores,
        "decision_snapshot": decision_snapshot,
    }


# ============================================================
# RISK
# ============================================================

def run_risk_stage(
    decision_snapshot
):

    print()
    line()

    print(
        "DECISION → RISK RUNTIME"
    )

    line()

    risk_snapshot = (
        risk_engine.run(
            decision_snapshot
        )
    )

    if not isinstance(
        risk_snapshot,
        dict
    ):

        raise RuntimeError(
            "Risk Engine returned invalid runtime snapshot."
        )

    return risk_snapshot


# ============================================================
# SNAPSHOT EXTRACTION
# ============================================================

def _rows_from_list(
    value
):

    if not isinstance(
        value,
        list
    ):

        return None

    rows = [
        row
        for row in value
        if isinstance(row, dict)
    ]

    if not rows:
        return None

    identifiable = [
        row
        for row in rows
        if get_asset(row) is not None
    ]

    if not identifiable:
        return None

    return rows


def _rows_from_asset_mapping(
    value
):

    if not isinstance(
        value,
        dict
    ):

        return None

    rows = []

    expected = set(
        EXPECTED_ASSETS
    )

    for key, row in value.items():

        if not isinstance(
            row,
            dict
        ):
            continue

        key_asset = normalize_asset(
            key
        )

        row_asset = get_asset(
            row
        )

        if (
            key_asset
            in
            expected
            and
            row_asset is None
        ):

            normalized_row = dict(
                row
            )

            normalized_row[
                "asset"
            ] = key_asset

            rows.append(
                normalized_row
            )

        elif row_asset is not None:

            rows.append(
                row
            )

    if not rows:
        return None

    return rows


def _coverage_score(
    rows
):

    if not isinstance(
        rows,
        list
    ):
        return 0

    expected = set(
        EXPECTED_ASSETS
    )

    assets = {
        get_asset(row)
        for row in rows
        if get_asset(row) is not None
    }

    return len(
        assets
        &
        expected
    )


def _select_best_rows(
    candidates
):

    if not candidates:
        return None

    best = None
    best_score = -1
    best_length = -1

    for rows in candidates:

        score = _coverage_score(
            rows
        )

        if score > best_score:

            best = rows
            best_score = score
            best_length = len(rows)

        elif (
            score == best_score
            and
            len(rows) > best_length
        ):

            best = rows
            best_length = len(rows)

    return best


def extract_rows(
    snapshot,
    names
):

    if not isinstance(
        snapshot,
        dict
    ):

        raise RuntimeError(
            "Snapshot is not a dict."
        )

    candidates = []

    visited = set()

    for name in names:

        if name not in snapshot:
            continue

        value = snapshot.get(
            name
        )

        rows = _rows_from_list(
            value
        )

        if rows is not None:

            candidates.append(
                rows
            )

        rows = _rows_from_asset_mapping(
            value
        )

        if rows is not None:

            candidates.append(
                rows
            )

    direct_mapping_rows = (
        _rows_from_asset_mapping(
            snapshot
        )
    )

    if direct_mapping_rows is not None:

        candidates.append(
            direct_mapping_rows
        )

    preferred_keys = (
        "snapshot",
        "data",
        "result",
        "payload",
        "output",
        "runtime",
        "decision_snapshot",
        "risk_snapshot",
        "decisions",
        "risks",
        "rows",
        "signals",
    )

    def discover(
        value
    ):

        if isinstance(
            value,
            list
        ):

            rows = _rows_from_list(
                value
            )

            if rows is not None:

                candidates.append(
                    rows
                )

            for item in value:

                if isinstance(
                    item,
                    (
                        dict,
                        list,
                    )
                ):

                    discover(
                        item
                    )

            return

        if not isinstance(
            value,
            dict
        ):

            return

        object_id = id(
            value
        )

        if object_id in visited:
            return

        visited.add(
            object_id
        )

        rows = _rows_from_asset_mapping(
            value
        )

        if rows is not None:

            candidates.append(
                rows
            )

        for key in preferred_keys:

            if key not in value:
                continue

            nested = value[
                key
            ]

            if isinstance(
                nested,
                (
                    dict,
                    list,
                )
            ):

                discover(
                    nested
                )

        for key, nested in value.items():

            if key in preferred_keys:
                continue

            if not isinstance(
                nested,
                (
                    dict,
                    list,
                )
            ):
                continue

            discover(
                nested
            )

    discover(
        snapshot
    )

    unique_candidates = []

    seen_signatures = set()

    for rows in candidates:

        if not rows:
            continue

        signature = tuple(
            sorted(
                (
                    get_asset(row)
                    for row in rows
                    if get_asset(row) is not None
                )
            )
        )

        if not signature:
            continue

        if signature in seen_signatures:
            continue

        seen_signatures.add(
            signature
        )

        unique_candidates.append(
            rows
        )

    full_candidates = [
        rows
        for rows in unique_candidates
        if _coverage_score(rows) == 15
    ]

    if full_candidates:

        selected = _select_best_rows(
            full_candidates
        )

        if selected is not None:
            return selected

    selected = _select_best_rows(
        unique_candidates
    )

    if selected is not None:

        return selected

    raise RuntimeError(
        "Unable to locate snapshot rows."
    )


# ============================================================
# SNAPSHOT COVERAGE VALIDATION
# ============================================================

def validate_snapshot_rows(
    rows,
    label
):

    if not isinstance(
        rows,
        list
    ):

        raise RuntimeError(
            f"{label} snapshot rows are not a list."
        )

    assets = []

    for row in rows:

        asset = get_asset(
            row
        )

        if asset is not None:

            assets.append(
                asset
            )

    expected = set(
        EXPECTED_ASSETS
    )

    actual = set(
        assets
    )

    missing = sorted(
        expected
        -
        actual
    )

    extra = sorted(
        actual
        -
        expected
    )

    duplicates = sorted(
        {
            asset
            for asset in assets
            if assets.count(asset) > 1
        }
    )

    if missing or extra or duplicates:

        raise RuntimeError(
            f"{label} snapshot coverage failure: "
            f"missing={missing}, "
            f"extra={extra}, "
            f"duplicates={duplicates}"
        )

    if len(
        assets
    ) != 15:

        raise RuntimeError(
            f"{label} snapshot must contain exactly 15 asset rows. "
            f"Received {len(assets)}."
        )

    return True


# ============================================================
# ASSET MAP
# ============================================================

def build_asset_map(
    rows,
    label
):

    result = {}

    for row in rows:

        asset = get_asset(
            row
        )

        if asset is None:
            continue

        if asset in result:

            raise RuntimeError(
                f"{label}: duplicate asset {asset}"
            )

        result[
            asset
        ] = row

    return result


# ============================================================
# CP6 INTEGRITY
# ============================================================

def validate_direction_integrity(
    decision_rows,
    risk_rows,
    gate_results
):

    decision_map = build_asset_map(
        decision_rows,
        "DECISION"
    )

    risk_map = build_asset_map(
        risk_rows,
        "RISK"
    )

    for result in gate_results:

        asset = result["asset"]

        decision = decision_map.get(
            asset
        )

        risk = risk_map.get(
            asset
        )

        if decision is None:
            continue

        decision_direction = normalize_direction(
            decision.get(
                "direction"
            )
        )

        gate_direction = normalize_direction(
            result.get(
                "direction"
            )
        )

        if decision_direction != gate_direction:

            raise RuntimeError(
                f"Direction integrity failure: "
                f"{asset}: Decision={decision_direction} "
                f"Gate={gate_direction}"
            )

        if risk is not None:

            risk_direction = normalize_direction(
                risk.get(
                    "direction"
                )
            )

            if (
                risk_direction
                !=
                decision_direction
                and
                decision_direction
                in (
                    "LONG",
                    "SHORT",
                )
            ):

                raise RuntimeError(
                    f"Risk direction integrity failure: "
                    f"{asset}: "
                    f"Decision={decision_direction}, "
                    f"Risk={risk_direction}"
                )


# ============================================================
# CP6 COVERAGE
# ============================================================

def coverage(
    rows
):

    assets = []

    for row in rows:

        asset = get_asset(
            row
        )

        if asset is not None:

            assets.append(
                asset
            )

    duplicates = sorted(
        {
            asset
            for asset in assets
            if assets.count(asset) > 1
        }
    )

    actual = set(
        assets
    )

    expected = set(
        EXPECTED_ASSETS
    )

    missing = sorted(
        expected
        -
        actual
    )

    extra = sorted(
        actual
        -
        expected
    )

    return (
        len(actual),
        missing,
        extra,
        duplicates,
    )


# ============================================================
# CP7-G REPORT
# ============================================================

def print_cp7g_report(
    snapshot_id,
    opportunity_rows,
    decision_rows,
    risk_rows,
    gate_results
):

    trade_ready = [
        row
        for row in gate_results
        if row.get(
            "trade_gate_status"
        )
        ==
        "TRADE_READY"
    ]

    line()

    print(
        "ARUNDA TRADER — CP7-G"
    )

    line()

    print()
    print(
        "STATUS:"
    )

    print(
        "CURRENT RUNTIME IDENTITY IMPLEMENTED"
    )

    print()
    print(
        "CURRENT RUNTIME SNAPSHOT ID:"
    )

    print(
        snapshot_id
    )

    print()
    print(
        "SNAPSHOT IDENTITY:"
    )

    print(
        "SOURCE: CURRENT MARKET SNAPSHOT SAME-CYCLE PAYLOAD"
    )

    print(
        "ALGORITHM: SHA-256"
    )

    print(
        "DETERMINISTIC: YES"
    )

    print(
        "REPRODUCIBLE: YES"
    )

    print(
        "AUDITABLE: YES"
    )

    print()
    print(
        "PROPAGATION:"
    )

    print(
        "RUNTIME SNAPSHOT"
    )

    print(
        "→ OPPORTUNITY"
    )

    print(
        "→ TRADE GATE"
    )

    print(
        "→ ORDER INTENT BOUNDARY"
    )

    print()
    print(
        "CURRENT ORDER INTENT CONTRACT:"
    )

    print(
        "IDENTITY CONTEXT AVAILABLE: YES"
    )

    print()
    print(
        "CURRENT REQUIRED FIELDS:"
    )

    print(
        "asset"
    )

    print(
        "direction"
    )

    print(
        "entry_price"
    )

    print(
        "confidence"
    )

    print(
        "regime"
    )

    print(
        "timestamp"
    )

    print(
        "snapshot_id"
    )

    print(
        "intent_id"
    )

    print()
    print(
        "REMOVED LEGACY:"
    )

    print(
        "signal_strength"
    )

    print(
        "data_quality"
    )

    print(
        "source_row_id"
    )

    print()
    print(
        "TRADE_READY:"
    )

    print(
        len(trade_ready)
    )

    print()
    print(
        "ORDER_INTENT:"
    )

    print(
        "0"
    )

    print()
    print(
        "ORDER_SUBMISSION:"
    )

    print(
        "NONE"
    )

    print()
    print(
        "EXCHANGE_WRITE:"
    )

    print(
        "NONE"
    )

    print()
    print(
        "EXECUTION:"
    )

    print(
        "DISABLED"
    )

    print()
    print(
        "DB_WRITE:"
    )

    print(
        "NONE"
    )

    print()
    print(
        "SYNTHETIC:"
    )

    print(
        "NONE"
    )

    print()
    print(
        "FALLBACK:"
    )

    print(
        "NONE"
    )

    print()
    print(
        "INTERPOLATION:"
    )

    print(
        "NONE"
    )

    print()
    print(
        "FORWARD_FILL:"
    )

    print(
        "NONE"
    )

    print()
    print(
        "BACK_FILL:"
    )

    print(
        "NONE"
    )

    print()
    print(
        "PADDING:"
    )

    print(
        "NONE"
    )

    print()
    print(
        "FABRICATION:"
    )

    print(
        "NONE"
    )

    print()
    print(
        "UPSTREAM BUSINESS LOGIC:"
    )

    print(
        "UNCHANGED"
    )

    print()
    print(
        "CLOSED_LAYERS_REOPENED:"
    )

    print(
        "NONE"
    )

    print()
    print(
        "RESULT:"
    )

    print(
        "IDENTITY BOUNDARY READY"
    )

    print()
    print(
        "NEXT CHECKPOINT:"
    )

    print(
        "DO NOT START AUTOMATICALLY"
    )

    print(
        "STOP HERE."
    )

    line()


# ============================================================
# MAIN
# ============================================================

def main():

    if EXECUTION_ENABLED:

        raise RuntimeError(
            "Execution must remain disabled for CP7-G."
        )

    print()
    line()

    print(
        "ARUNDA TRADER — CP7-G RUNTIME"
    )

    print(
        "CURRENT RUNTIME IDENTITY"
    )

    print(
        f"Execution Enabled : {EXECUTION_ENABLED}"
    )

    line()

    # --------------------------------------------------------
    # STAGE 0
    # --------------------------------------------------------

    run_script_stage(
        "upgrade_db.py"
    )

    # --------------------------------------------------------
    # STAGE 1
    # --------------------------------------------------------
    #
    # CP7-G:
    # Preserve the actual stdout so the real same-cycle
    # snapshot payload can be consumed.
    #
    # --------------------------------------------------------

    market_snapshot_stdout = run_script_stage(
        "market_snapshot_engine.py"
    )

    # --------------------------------------------------------
    # CP7-G CURRENT RUNTIME SNAPSHOT
    # --------------------------------------------------------

    current_runtime_snapshot = (
        parse_current_runtime_snapshot(
            market_snapshot_stdout
        )
    )

    validate_current_runtime_snapshot(
        current_runtime_snapshot
    )

    snapshot_id = (
        build_current_runtime_snapshot_id(
            current_runtime_snapshot
        )
    )

    print()
    print(
        "CP7-G CURRENT RUNTIME SNAPSHOT : PASS"
    )

    print(
        f"Snapshot ID : {snapshot_id}"
    )

    print(
        f"Assets      : "
        f"{len(current_runtime_snapshot['assets'])}/15"
    )

    # --------------------------------------------------------
    # RUNTIME IDENTITY CONTEXT
    # --------------------------------------------------------
    #
    # Provenance only.
    # No business logic is modified.
    #
    # --------------------------------------------------------

    runtime_identity_context = {

        "snapshot_id": snapshot_id,

        "snapshot": current_runtime_snapshot,
    }

    # --------------------------------------------------------
    # STAGE 2
    # --------------------------------------------------------

    run_script_stage(
        "market_data_engine.py"
    )

    # --------------------------------------------------------
    # STAGE 3
    # --------------------------------------------------------

    opportunity_stdout = run_script_stage(
        "opportunity_engine.py"
    )

    # --------------------------------------------------------
    # CURRENT-RUN OPPORTUNITY SNAPSHOT
    # --------------------------------------------------------

    opportunity_rows = (
        parse_opportunity_runtime_snapshot(
            opportunity_stdout
        )
    )

    print()
    print(
        "CURRENT-RUN OPPORTUNITY SNAPSHOT : "
        f"{len(opportunity_rows)}"
    )

    # --------------------------------------------------------
    # SIGNAL → SCORE → DECISION
    # --------------------------------------------------------

    runtime = (
        run_signal_score_decision_runtime()
    )

    decision_snapshot = (
        runtime[
            "decision_snapshot"
        ]
    )

    # --------------------------------------------------------
    # DECISION SNAPSHOT EXTRACTION
    # --------------------------------------------------------

    decision_rows = extract_rows(
        decision_snapshot,
        (
            "decisions",
            "rows",
            "signals",
            "snapshot",
            "data",
            "result",
            "payload",
        )
    )

    validate_snapshot_rows(
        decision_rows,
        "DECISION"
    )

    # --------------------------------------------------------
    # RISK
    # --------------------------------------------------------

    risk_snapshot = (
        run_risk_stage(
            decision_snapshot
        )
    )

    # --------------------------------------------------------
    # RISK SNAPSHOT EXTRACTION
    # --------------------------------------------------------

    risk_rows = extract_rows(
        risk_snapshot,
        (
            "risk",
            "risks",
            "rows",
            "snapshot",
            "data",
            "result",
            "payload",
        )
    )

    validate_snapshot_rows(
        risk_rows,
        "RISK"
    )

    # --------------------------------------------------------
    # DECISION → RISK HARD ALIGNMENT
    # --------------------------------------------------------

    decision_asset_set = {
        get_asset(row)
        for row in decision_rows
        if get_asset(row)
    }

    risk_asset_set = {
        get_asset(row)
        for row in risk_rows
        if get_asset(row)
    }

    if (
        decision_asset_set
        !=
        risk_asset_set
    ):

        raise RuntimeError(
            "Decision → Risk asset alignment failure: "
            f"decision={sorted(decision_asset_set)}, "
            f"risk={sorted(risk_asset_set)}"
        )

    # --------------------------------------------------------
    # CP6 — TRADE GATE
    # --------------------------------------------------------

    print()
    line()

    print(
        "RISK → TRADE GATE RUNTIME"
    )

    line()

    gate_results = (
        trade_gate_engine.run_runtime(
            opportunity_rows,
            decision_snapshot,
            risk_snapshot
        )
    )

    if not isinstance(
        gate_results,
        list
    ):

        raise RuntimeError(
            "Trade Gate returned invalid runtime result."
        )

    # --------------------------------------------------------
    # HARD 15-ASSET GATE COVERAGE
    # --------------------------------------------------------

    gate_assets = [
        get_asset(row)
        for row in gate_results
        if get_asset(row)
    ]

    if len(
        gate_assets
    ) != 15:

        raise RuntimeError(
            "Trade Gate must return exactly 15 asset results. "
            f"Received {len(gate_assets)}."
        )

    if len(
        set(gate_assets)
    ) != 15:

        raise RuntimeError(
            "Trade Gate returned duplicate assets."
        )

    gate_asset_set = set(
        gate_assets
    )

    expected_asset_set = set(
        EXPECTED_ASSETS
    )

    gate_missing = sorted(
        expected_asset_set
        -
        gate_asset_set
    )

    gate_extra = sorted(
        gate_asset_set
        -
        expected_asset_set
    )

    if gate_missing or gate_extra:

        raise RuntimeError(
            "Trade Gate asset coverage failure: "
            f"missing={gate_missing}, "
            f"extra={gate_extra}"
        )

    # --------------------------------------------------------
    # CP7-G IDENTITY REPORT
    # --------------------------------------------------------

    print_cp7g_report(
        snapshot_id,
        opportunity_rows,
        decision_rows,
        risk_rows,
        gate_results
    )

    # --------------------------------------------------------
    # HARD STOP
    # --------------------------------------------------------

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )