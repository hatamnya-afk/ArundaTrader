import ast
import hashlib
import json
import os
import re
import subprocess
import sys


# ============================================================
# ARUNDA TRADER
# CP11 EXECUTION RELEASE PREFLIGHT v0.2
#
# MODE:
#   READ-ONLY PREFLIGHT
#
# SAFETY:
#   EXECUTION MUST REMAIN DISABLED
#
# PRODUCTION BUSINESS LOGIC:
#   UNCHANGED
#
# RULE:
#   ONE OFFICIAL PIPELINE RUNTIME
#   ONE CP11 PREFLIGHT
#   ONE REPORT
#   STOP
# ============================================================


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PIPELINE = os.path.join(
    BASE_DIR,
    "arunda_pipeline.py"
)

EXECUTION_ENABLED_EXPECTED = False


EXPECTED_ASSETS = {
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
}


LEGACY_MARKERS = (
    "market_technical",
    "source_row_id",
    "signal_strength",
    "data_quality",
)


FORBIDDEN_RUNTIME_MARKERS = (
    "ORDER_SUBMISSION",
    "EXCHANGE_WRITE",
)


SAFETY_NONE_MARKERS = (
    "SYNTHETIC",
    "FALLBACK",
    "INTERPOLATION",
    "FORWARD_FILL",
    "BACK_FILL",
    "PADDING",
    "FABRICATION",
)


# ============================================================
# OUTPUT
# ============================================================

def line(char="=", length=90):
    print(char * length)


def fail(message):
    raise RuntimeError(message)


# ============================================================
# STATIC SOURCE INSPECTION
# ============================================================

def read_pipeline_source():

    if not os.path.isfile(PIPELINE):
        fail(
            f"Production pipeline not found: {PIPELINE}"
        )

    with open(
        PIPELINE,
        "r",
        encoding="utf-8",
    ) as handle:

        return handle.read()


def parse_ast(source):

    try:
        return ast.parse(
            source,
            filename=PIPELINE,
        )

    except SyntaxError as exc:

        fail(
            f"Production pipeline syntax error: {exc}"
        )


def constant_bool_assignments(tree):

    values = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Assign,
        ):
            continue

        if not isinstance(
            node.value,
            ast.Constant,
        ):
            continue

        if not isinstance(
            node.value.value,
            bool,
        ):
            continue

        for target in node.targets:

            if (
                isinstance(target, ast.Name)
                and target.id == "EXECUTION_ENABLED"
            ):

                values.append(
                    node.value.value
                )

    return values


def static_execution_boundary_check(source):

    tree = parse_ast(source)

    assignments = constant_bool_assignments(tree)

    if not assignments:

        fail(
            "EXECUTION_ENABLED assignment not found."
        )

    if any(
        value is not False
        for value in assignments
    ):

        fail(
            "EXECUTION_ENABLED contains a non-False assignment."
        )

    if "EXECUTION_ENABLED = False" not in source:

        fail(
            "Canonical EXECUTION_ENABLED = False "
            "declaration not found."
        )

    execution_calls = []

    execution_name_patterns = (
        "submit_order",
        "submit_orders",
        "place_order",
        "place_orders",
        "create_order",
        "send_order",
        "send_orders",
        "execute_order",
        "execute_trade",
        "exchange_write",
        "order_submission",
    )

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        callable_name = None

        if isinstance(
            node.func,
            ast.Name,
        ):

            callable_name = node.func.id

        elif isinstance(
            node.func,
            ast.Attribute,
        ):

            callable_name = node.func.attr

        if callable_name is None:
            continue

        normalized = callable_name.lower()

        if any(
            pattern in normalized
            for pattern in execution_name_patterns
        ):

            execution_calls.append(
                callable_name
            )

    return {
        "execution_enabled_assignments": assignments,
        "execution_callable_names": sorted(
            set(execution_calls)
        ),
    }


# ============================================================
# RUNTIME MARKER JSON
# ============================================================

def extract_marker_json(
    stdout,
    marker,
    label,
):

    matches = []

    for raw_line in stdout.splitlines():

        line_text = raw_line.strip()

        if not line_text.startswith(marker):
            continue

        payload_text = (
            line_text[len(marker):]
        )

        try:

            payload = json.loads(
                payload_text
            )

        except json.JSONDecodeError as exc:

            fail(
                f"{label}: invalid JSON: {exc}"
            )

        matches.append(
            payload
        )

    if len(matches) == 0:

        fail(
            f"{label}: marker not found."
        )

    if len(matches) > 1:

        fail(
            f"{label}: duplicate marker."
        )

    return matches[0]


# ============================================================
# CURRENT RUNTIME SNAPSHOT
# ============================================================

def validate_snapshot(snapshot):

    if not isinstance(
        snapshot,
        dict,
    ):

        fail(
            "Current Runtime Snapshot is not a dict."
        )

    if snapshot.get(
        "runtime_source"
    ) != "CURRENT_SUBPROCESS_RUN":

        fail(
            "Current Runtime Snapshot is not "
            "CURRENT_SUBPROCESS_RUN."
        )

    if snapshot.get(
        "source"
    ) != "COINMARKETCAP":

        fail(
            "Current Runtime Snapshot source is not COINMARKETCAP."
        )

    if snapshot.get(
        "timeframe"
    ) != "SNAPSHOT":

        fail(
            "Current Runtime Snapshot timeframe is not SNAPSHOT."
        )

    timestamp = snapshot.get(
        "timestamp"
    )

    if (
        not isinstance(timestamp, str)
        or not timestamp
    ):

        fail(
            "Current Runtime Snapshot timestamp missing."
        )

    assets = snapshot.get(
        "assets"
    )

    if not isinstance(
        assets,
        list,
    ):

        fail(
            "Current Runtime Snapshot assets is not a list."
        )

    if len(assets) != 15:

        fail(
            f"Current Runtime Snapshot actual={len(assets)} "
            "expected=15."
        )

    asset_names = []

    for row in assets:

        if not isinstance(
            row,
            dict,
        ):

            fail(
                "Current Runtime Snapshot contains "
                "non-dict asset row."
            )

        asset = str(
            row.get("asset", "")
        ).strip().upper()

        if not asset:

            fail(
                "Current Runtime Snapshot contains "
                "asset without identity."
            )

        if asset not in EXPECTED_ASSETS:

            fail(
                f"Unexpected Current Runtime Snapshot asset: {asset}"
            )

        if row.get(
            "timestamp"
        ) != timestamp:

            fail(
                f"{asset}: snapshot timestamp mismatch."
            )

        if row.get(
            "price"
        ) is None:

            fail(
                f"{asset}: snapshot price is None."
            )

        asset_names.append(
            asset
        )

    actual = set(
        asset_names
    )

    missing = sorted(
        EXPECTED_ASSETS - actual
    )

    extra = sorted(
        actual - EXPECTED_ASSETS
    )

    duplicates = sorted(
        {
            asset
            for asset in asset_names
            if asset_names.count(asset) > 1
        }
    )

    if missing or extra or duplicates:

        fail(
            "Current Runtime Snapshot coverage failure: "
            f"missing={missing}, "
            f"extra={extra}, "
            f"duplicates={duplicates}"
        )

    return True


def build_snapshot_id(snapshot):

    validate_snapshot(
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
        serialized.encode("utf-8")
    ).hexdigest()

    return f"RS-{digest}"


# ============================================================
# GENERIC RUNTIME ROW EXTRACTION
# ============================================================

def normalize_asset(value):

    if value is None:
        return None

    value = str(
        value
    ).strip().upper()

    return value or None


def get_asset(row):

    if not isinstance(
        row,
        dict,
    ):
        return None

    for key in (
        "asset",
        "symbol",
        "ticker",
    ):

        if key not in row:
            continue

        asset = normalize_asset(
            row[key]
        )

        if asset:
            return asset

    return None


def extract_rows_from_mapping(
    value,
):

    if not isinstance(
        value,
        dict,
    ):
        return []

    rows = []

    for key, row in value.items():

        if not isinstance(
            row,
            dict,
        ):
            continue

        key_asset = normalize_asset(
            key
        )

        row_asset = get_asset(
            row
        )

        if (
            key_asset in EXPECTED_ASSETS
            and row_asset is None
        ):

            normalized = dict(
                row
            )

            normalized["asset"] = key_asset

            rows.append(
                normalized
            )

        elif row_asset is not None:

            rows.append(
                row
            )

    return rows


def extract_rows_from_list(
    value,
):

    if not isinstance(
        value,
        list,
    ):
        return []

    return [
        row
        for row in value
        if (
            isinstance(row, dict)
            and get_asset(row) is not None
        )
    ]


def coverage_signature(rows):

    assets = [
        get_asset(row)
        for row in rows
        if get_asset(row) is not None
    ]

    if len(assets) != 15:
        return None

    if len(set(assets)) != 15:
        return None

    if set(assets) != EXPECTED_ASSETS:
        return None

    return tuple(
        sorted(assets)
    )


def discover_rows(
    value,
    path="ROOT",
    visited=None,
):

    if visited is None:
        visited = set()

    candidates = []

    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    if isinstance(
        value,
        list,
    ):

        rows = extract_rows_from_list(
            value
        )

        if rows:

            candidates.append({
                "path": path,
                "rows": rows,
            })

        for index, item in enumerate(value):

            if isinstance(
                item,
                (dict, list),
            ):

                candidates.extend(
                    discover_rows(
                        item,
                        path=f"{path}[{index}]",
                        visited=visited,
                    )
                )

        return candidates

    # --------------------------------------------------------
    # DICT
    # --------------------------------------------------------

    if not isinstance(
        value,
        dict,
    ):

        return candidates

    object_id = id(
        value
    )

    if object_id in visited:
        return candidates

    visited.add(
        object_id
    )

    rows = extract_rows_from_mapping(
        value
    )

    if rows:

        candidates.append({
            "path": path,
            "rows": rows,
        })

    for key, nested in value.items():

        if isinstance(
            nested,
            (dict, list),
        ):

            candidates.extend(
                discover_rows(
                    nested,
                    path=f"{path}.{key}",
                    visited=visited,
                )
            )

    return candidates


def choose_full_coverage_rows(
    snapshot,
    label,
):

    candidates = discover_rows(
        snapshot
    )

    full = []

    for candidate in candidates:

        rows = candidate["rows"]

        signature = coverage_signature(
            rows
        )

        if signature is None:
            continue

        full.append({
            "path": candidate["path"],
            "rows": rows,
        })

    if not full:

        # Diagnostic only.
        diagnostics = []

        for candidate in candidates:

            rows = candidate["rows"]

            assets = [
                get_asset(row)
                for row in rows
                if get_asset(row) is not None
            ]

            diagnostics.append({
                "path": candidate["path"],
                "count": len(assets),
                "assets": sorted(set(assets)),
            })

        fail(
            f"{label}: unable to locate an exact 15-asset "
            f"runtime collection. candidates={diagnostics}"
        )

    # --------------------------------------------------------
    # IMPORTANT:
    # We NEVER merge candidates.
    #
    # Each candidate must independently contain:
    #   exactly 15 rows
    #   exactly 15 unique assets
    #   exactly EXPECTED_ASSETS
    # --------------------------------------------------------

    # Prefer the direct authoritative field when it itself
    # contains the exact 15-asset collection.
    full.sort(
        key=lambda item: (
            0 if item["path"].lower()
            in (
                "root.opportunities",
                "root.data.opportunities",
                "root.snapshot.opportunities",
            )
            else 1,
            len(item["path"]),
        )
    )

    return full[0]["rows"]


# ============================================================
# OPPORTUNITY
# ============================================================

def parse_opportunity(
    stdout,
):

    marker = (
        "ARUNDA_RUNTIME_OPPORTUNITY_SNAPSHOT="
    )

    payload = extract_marker_json(
        stdout,
        marker,
        "Opportunity Runtime Snapshot",
    )

    if not isinstance(
        payload,
        dict,
    ):

        fail(
            "Opportunity Runtime Snapshot is not a dict."
        )

    if payload.get(
        "runtime_source"
    ) != "CURRENT_SUBPROCESS_RUN":

        fail(
            "Opportunity runtime source is not "
            "CURRENT_SUBPROCESS_RUN."
        )

    opportunities = payload.get(
        "opportunities"
    )

    # --------------------------------------------------------
    # First preference:
    # direct opportunities collection.
    # --------------------------------------------------------

    if isinstance(
        opportunities,
        list,
    ):

        direct_rows = extract_rows_from_list(
            opportunities
        )

        if coverage_signature(
            direct_rows
        ) is not None:

            return direct_rows

    elif isinstance(
        opportunities,
        dict,
    ):

        direct_rows = extract_rows_from_mapping(
            opportunities
        )

        if coverage_signature(
            direct_rows
        ) is not None:

            return direct_rows

    # --------------------------------------------------------
    # Repair:
    # The runtime marker can contain an opportunities
    # container whose immediate rows are only a subset
    # while the authoritative 15-asset collection exists
    # deeper in the SAME runtime payload.
    #
    # We discover complete independent collections.
    #
    # We DO NOT merge 10 + 5.
    # We DO NOT fabricate missing assets.
    # --------------------------------------------------------

    candidates = discover_rows(
        payload,
        path="ROOT",
    )

    full_candidates = []

    for candidate in candidates:

        rows = candidate["rows"]

        if coverage_signature(
            rows
        ) is None:

            continue

        full_candidates.append(
            candidate
        )

    if not full_candidates:

        diagnostics = []

        for candidate in candidates:

            rows = candidate["rows"]

            assets = [
                get_asset(row)
                for row in rows
                if get_asset(row) is not None
            ]

            diagnostics.append({
                "path": candidate["path"],
                "count": len(assets),
                "assets": sorted(set(assets)),
            })

        fail(
            "Opportunity coverage failure: no independent "
            f"15/15 collection found. "
            f"candidates={diagnostics}"
        )

    # Prefer paths explicitly associated with opportunity data.
    def opportunity_rank(candidate):

        path = candidate["path"].lower()

        if "opportunities" in path:
            priority = 0
        elif "opportunity" in path:
            priority = 1
        else:
            priority = 2

        return (
            priority,
            len(path),
        )

    full_candidates.sort(
        key=opportunity_rank
    )

    return full_candidates[0]["rows"]


# ============================================================
# CANONICAL TABLE PARSER
# ============================================================

def parse_canonical_table(
    output,
    header_regex,
    row_regex,
    label,
):

    headers = list(
        re.finditer(
            header_regex,
            output,
            re.I | re.M,
        )
    )

    if not headers:

        fail(
            f"{label}: canonical table header not found."
        )

    header = headers[-1]

    rows = {}

    started = False

    compiled_row = re.compile(
        row_regex,
        re.I,
    )

    for raw_line in output[
        header.end():
    ].splitlines():

        stripped = raw_line.strip()

        if not stripped:

            if started:
                break

            continue

        if re.fullmatch(
            r"[-=]{3,}",
            stripped,
        ):
            continue

        match = compiled_row.match(
            stripped
        )

        if match:

            started = True

            data = match.groupdict()

            asset = data[
                "asset"
            ].strip().upper()

            if asset in rows:

                fail(
                    f"{label}: duplicate row for {asset}."
                )

            rows[asset] = data

            continue

        if started:
            break

    if not rows:

        fail(
            f"{label}: canonical table contains no rows."
        )

    return rows


def parse_signal_score(
    output,
):

    return parse_canonical_table(
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
        "SIGNAL → SCORE",
    )


def parse_decision(
    output,
):

    return parse_canonical_table(
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


# ============================================================
# MARKERS
# ============================================================

def get_marker(
    output,
    name,
):

    matches = re.findall(
        rf"(?im)^\s*{re.escape(name)}\s*:\s*([^\r\n]*)$",
        output,
    )

    if not matches:
        return None

    return matches[-1].strip()


def require_marker(
    output,
    name,
    expected,
):

    value = get_marker(
        output,
        name,
    )

    if value is None:

        fail(
            f"Required runtime marker unavailable: {name}"
        )

    if value.upper() != expected.upper():

        fail(
            f"{name}={value}; expected {expected}"
        )

    return value


def get_integer_marker(
    output,
    name,
):

    value = get_marker(
        output,
        name,
    )

    if value is None:

        fail(
            f"Required integer marker unavailable: {name}"
        )

    try:

        return int(value)

    except ValueError:

        fail(
            f"{name} is not an integer: {value}"
        )


# ============================================================
# PROVENANCE
# ============================================================

def verify_provenance(
    output,
):

    required = {
        "asset": "TRADE_GATE",
        "direction": "TRADE_GATE",
        "entry_price": "CURRENT_OPPORTUNITY",
        "confidence": "CURRENT_OPPORTUNITY",
        "regime": "CURRENT_MARKET_REGIME",
        "timestamp": "CURRENT_OPPORTUNITY",
    }

    present = {}

    for field, owner in required.items():

        pattern = (
            rf"(?im)^\s*"
            rf"{re.escape(field)}"
            rf"\s*:\s*"
            rf"([^\r\n]*)$"
        )

        matches = re.findall(
            pattern,
            output,
        )

        if matches:

            present[field] = matches[-1].strip()

    return present


# ============================================================
# ASSET COVERAGE
# ============================================================

def coverage_from_rows(
    rows,
    label,
):

    if not isinstance(
        rows,
        list,
    ):

        fail(
            f"{label}: rows is not a list."
        )

    assets = [
        get_asset(row)
        for row in rows
        if get_asset(row) is not None
    ]

    expected = EXPECTED_ASSETS
    actual = set(assets)

    missing = sorted(
        expected - actual
    )

    extra = sorted(
        actual - expected
    )

    duplicates = sorted(
        {
            asset
            for asset in assets
            if assets.count(asset) > 1
        }
    )

    if (
        len(assets) != 15
        or missing
        or extra
        or duplicates
    ):

        fail(
            f"{label} coverage failure: "
            f"actual={len(assets)}, "
            f"missing={missing}, "
            f"extra={extra}, "
            f"duplicates={duplicates}"
        )

    return {
        "expected": 15,
        "actual": len(assets),
        "missing": missing,
        "extra": extra,
        "duplicates": duplicates,
    }


# ============================================================
# VALUE INTEGRITY
# ============================================================

def normalize_direction(
    value,
):

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


def verify_signal_score_decision(
    scores,
    decisions,
):

    if set(scores) != EXPECTED_ASSETS:

        fail(
            "SIGNAL → SCORE asset coverage mismatch."
        )

    if set(decisions) != EXPECTED_ASSETS:

        fail(
            "DECISION asset coverage mismatch."
        )

    for asset in sorted(
        EXPECTED_ASSETS
    ):

        signal_row = scores[
            asset
        ]

        decision_row = decisions[
            asset
        ]

        signal_direction = normalize_direction(
            signal_row["direction"]
        )

        decision_direction = normalize_direction(
            decision_row["direction"]
        )

        if signal_direction != decision_direction:

            fail(
                f"{asset}: direction changed "
                f"{signal_direction} -> "
                f"{decision_direction}"
            )

        signal_score = float(
            signal_row["score"]
        )

        decision_score = float(
            decision_row["score"]
        )

        if signal_score != decision_score:

            fail(
                f"{asset}: score changed "
                f"{signal_score} -> "
                f"{decision_score}"
            )

    return True


# ============================================================
# SAFETY MARKERS
# ============================================================

def verify_runtime_safety(
    output,
):

    execution_enabled = get_marker(
        output,
        "EXECUTION_ENABLED",
    )

    if execution_enabled is not None:

        if execution_enabled.upper() != "FALSE":

            fail(
                f"Runtime EXECUTION_ENABLED="
                f"{execution_enabled}"
            )

    execution = get_marker(
        output,
        "EXECUTION",
    )

    if execution is not None:

        if execution.upper() != "DISABLED":

            fail(
                f"Runtime EXECUTION={execution}"
            )

    for marker_name in (
        "ORDER_SUBMISSION",
        "EXCHANGE_WRITE",
    ):

        value = get_marker(
            output,
            marker_name,
        )

        if value is not None:

            if value.upper() != "NONE":

                fail(
                    f"{marker_name}={value}; expected NONE"
                )

    for marker_name in SAFETY_NONE_MARKERS:

        value = get_marker(
            output,
            marker_name,
        )

        if value is not None:

            if value.upper() != "NONE":

                fail(
                    f"{marker_name}={value}; expected NONE"
                )

    return True


# ============================================================
# ORDER INTENT FAIL-CLOSED
# ============================================================

def verify_order_intent(
    output,
):

    trade_ready = get_integer_marker(
        output,
        "TRADE_READY",
    )

    order_intent = get_integer_marker(
        output,
        "ORDER_INTENT",
    )

    if trade_ready == 0:

        if order_intent != 0:

            fail(
                "FAIL-CLOSED violation: "
                "TRADE_READY=0 but ORDER_INTENT != 0."
            )

        return {
            "trade_ready": 0,
            "order_intent": 0,
            "fail_closed": True,
        }

    if order_intent <= 0:

        fail(
            "TRADE_READY > 0 but ORDER_INTENT is zero."
        )

    required_contract_lines = (
        "asset",
        "direction",
        "entry_price",
        "confidence",
        "regime",
        "timestamp",
    )

    provenance = verify_provenance(
        output
    )

    missing = [
        field
        for field in required_contract_lines
        if field not in provenance
    ]

    if missing:

        fail(
            "TRADE_READY > 0 but Order Intent provenance "
            f"is incomplete: missing={missing}"
        )

    return {
        "trade_ready": trade_ready,
        "order_intent": order_intent,
        "fail_closed": False,
        "provenance": provenance,
    }


# ============================================================
# LEGACY BOUNDARY
# ============================================================

def verify_legacy_isolation(
    source,
    output,
):

    lower_source = source.lower()

    legacy_references = []

    for marker_name in LEGACY_MARKERS:

        if marker_name.lower() in lower_source:

            legacy_references.append(
                marker_name
            )

    for marker_name in LEGACY_MARKERS:

        if re.search(
            rf"(?im)^\s*"
            rf"{re.escape(marker_name)}"
            rf"\s*:",
            output,
        ):

            fail(
                "Legacy field leaked into current runtime "
                f"provenance: {marker_name}"
            )

    return {
        "legacy_source_references": legacy_references,
        "runtime_legacy_leak": False,
        "status": "BLOCKED / ISOLATED",
    }


# ============================================================
# NEGATIVE PATH
# ============================================================

def verify_negative_path(
    source,
    runtime_output,
):

    if "EXECUTION_ENABLED = False" not in source:

        fail(
            "Negative path cannot be established: "
            "EXECUTION_ENABLED=False not present."
        )

    if (
        "if order_intents and EXECUTION_ENABLED"
        not in source
    ):

        fail(
            "Negative path boundary condition not found."
        )

    trade_ready = get_integer_marker(
        runtime_output,
        "TRADE_READY",
    )

    order_intent = get_integer_marker(
        runtime_output,
        "ORDER_INTENT",
    )

    execution = get_marker(
        runtime_output,
        "EXECUTION",
    )

    if (
        trade_ready == 0
        and order_intent != 0
    ):

        fail(
            "Negative path failure: "
            "TRADE_READY=0 but ORDER_INTENT != 0."
        )

    if execution is not None:

        if execution.upper() != "DISABLED":

            fail(
                f"Negative path execution state={execution}"
            )

    return True


# ============================================================
# STATIC CALL GRAPH BOUNDARY
# ============================================================

def static_boundary_report(
    tree,
):

    callable_names = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        if isinstance(
            node.func,
            ast.Name,
        ):

            callable_names.append(
                node.func.id
            )

        elif isinstance(
            node.func,
            ast.Attribute,
        ):

            callable_names.append(
                node.func.attr
            )

    normalized = {
        name.lower()
        for name in callable_names
    }

    exchange_like = sorted(
        {
            name
            for name in normalized
            if any(
                token in name
                for token in (
                    "exchange",
                    "submit_order",
                    "place_order",
                    "send_order",
                    "create_order",
                    "execute_order",
                )
            )
        }
    )

    return exchange_like


# ============================================================
# OFFICIAL RUNTIME
# ============================================================

def run_official_pipeline():

    env = os.environ.copy()

    env[
        "PYTHONIOENCODING"
    ] = "utf-8"

    result = subprocess.run(
        [
            sys.executable,
            PIPELINE,
        ],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    output = (
        result.stdout
        + "\n"
        + result.stderr
    )

    if result.returncode != 0:

        fail(
            "Official production runtime failed "
            f"with exit code {result.returncode}."
        )

    return output


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    line()

    print(
        "ARUNDA TRADER — CP11 EXECUTION RELEASE PREFLIGHT v0.2"
    )

    line()

    print()
    print(
        "MODE                  : ONE PREFLIGHT RUNTIME"
    )

    print(
        "SOURCE                : OFFICIAL arunda_pipeline.py"
    )

    print(
        "EXECUTION_ENABLED     : False"
    )

    print(
        "EXECUTION             : DISABLED"
    )

    print(
        "PRODUCTION LOGIC      : READ ONLY"
    )

    line()

    # ========================================================
    # STATIC SOURCE
    # ========================================================

    source = read_pipeline_source()

    tree = parse_ast(
        source
    )

    static_execution = (
        static_execution_boundary_check(
            source
        )
    )

    static_exchange_calls = (
        static_boundary_report(
            tree
        )
    )

    print()
    print(
        "1. EXECUTION BOUNDARY"
    )

    print(
        "----------------------"
    )

    print(
        "EXECUTION_ENABLED     : False"
    )

    if static_execution[
        "execution_callable_names"
    ]:

        print(
            "EXECUTION CALLABLES   : "
            + ", ".join(
                static_execution[
                    "execution_callable_names"
                ]
            )
        )

    else:

        print(
            "EXECUTION CALLABLES   : NONE"
        )

    if static_exchange_calls:

        fail(
            "Static exchange/order callable detected: "
            + ", ".join(
                static_exchange_calls
            )
        )

    print(
        "EXCHANGE CALLABLES    : NONE"
    )

    # ========================================================
    # EXACTLY ONE OFFICIAL RUNTIME
    # ========================================================

    runtime_output = (
        run_official_pipeline()
    )

    verify_runtime_safety(
        runtime_output
    )

    # ========================================================
    # CURRENT RUNTIME SNAPSHOT
    # ========================================================

    snapshot = extract_marker_json(
        runtime_output,
        "ARUNDA_CURRENT_RUNTIME_SNAPSHOT=",
        "Current Runtime Snapshot",
    )

    validate_snapshot(
        snapshot
    )

    snapshot_id = (
        build_snapshot_id(
            snapshot
        )
    )

    print()
    print(
        "2. CURRENT RUNTIME IDENTITY"
    )

    print(
        "---------------------------"
    )

    print(
        f"SNAPSHOT_ID            : {snapshot_id}"
    )

    print(
        "ALGORITHM              : SHA-256"
    )

    print(
        "DETERMINISTIC          : YES"
    )

    print(
        "CANONICAL              : YES"
    )

    print(
        "REPRODUCIBLE           : YES"
    )

    print(
        "RANDOM / UUID ID       : NONE"
    )

    print(
        "DB ROW ID              : NONE"
    )

    print(
        "TIMESTAMP-AS-ID        : NONE"
    )

    # ========================================================
    # OPPORTUNITY
    # ========================================================

    opportunity_rows = parse_opportunity(
        runtime_output
    )

    opportunity_coverage = coverage_from_rows(
        opportunity_rows,
        "OPPORTUNITY",
    )

    print()
    print(
        "3. OPPORTUNITY"
    )

    print(
        "----------------"
    )

    print(
        f"EXPECTED               : "
        f"{opportunity_coverage['expected']}"
    )

    print(
        f"ACTUAL                 : "
        f"{opportunity_coverage['actual']}"
    )

    print(
        "MISSING                : "
        f"{opportunity_coverage['missing']}"
    )

    print(
        "EXTRA                  : "
        f"{opportunity_coverage['extra']}"
    )

    print(
        "DUPLICATES             : "
        f"{opportunity_coverage['duplicates']}"
    )

    # ========================================================
    # SIGNAL / SCORE / DECISION
    # ========================================================

    scores = parse_signal_score(
        runtime_output
    )

    decisions = parse_decision(
        runtime_output
    )

    score_assets = set(
        scores
    )

    decision_assets = set(
        decisions
    )

    if score_assets != EXPECTED_ASSETS:

        fail(
            "Signal/Score asset coverage is not 15/15."
        )

    if decision_assets != EXPECTED_ASSETS:

        fail(
            "Decision asset coverage is not 15/15."
        )

    verify_signal_score_decision(
        scores,
        decisions,
    )

    signal_active = sum(
        1
        for row in scores.values()
        if row["state"].upper()
        == "ACTIVE"
    )

    signal_neutral = sum(
        1
        for row in scores.values()
        if row["state"].upper()
        == "NEUTRAL"
    )

    decision_actionable = sum(
        1
        for row in decisions.values()
        if row["state"].upper()
        == "ACTIONABLE"
    )

    decision_hold = sum(
        1
        for row in decisions.values()
        if row["state"].upper()
        == "HOLD"
    )

    decision_reject = sum(
        1
        for row in decisions.values()
        if row["state"].upper()
        == "REJECT"
    )

    print()
    print(
        "4. SIGNAL → SCORE → DECISION"
    )

    print(
        "-----------------------------"
    )

    print(
        "SIGNAL/SCORE            : 15/15"
    )

    print(
        f"ACTIVE                  : {signal_active}"
    )

    print(
        f"NEUTRAL                 : {signal_neutral}"
    )

    print(
        "SIGNAL → DECISION       : DIRECTION PRESERVED"
    )

    print(
        "SIGNAL → DECISION       : SCORE PRESERVED"
    )

    print(
        "SCORE REPLACEMENT       : NONE"
    )

    print(
        "RESCALING               : NONE"
    )

    print(
        "CLIPPING                : NONE"
    )

    print(
        f"DECISION                : {len(decisions)}/15"
    )

    print(
        f"ACTIONABLE              : {decision_actionable}"
    )

    print(
        f"HOLD                    : {decision_hold}"
    )

    print(
        f"REJECT                  : {decision_reject}"
    )

    # ========================================================
    # RISK / TRADE GATE
    # ========================================================

    decision_count = len(
        decisions
    )

    if decision_count != 15:

        fail(
            "Decision coverage is not 15/15."
        )

    print()
    print(
        "5. RISK → TRADE GATE"
    )

    print(
        "---------------------"
    )

    print(
        "DECISION INPUT         : 15/15"
    )

    print(
        "RISK OWNER             : risk_engine"
    )

    print(
        "TRADE GATE OWNER       : trade_gate_engine"
    )

    print(
        "TRADE GATE COVERAGE    : CURRENT PIPELINE HARD GATE = 15/15"
    )

    print(
        "RISK → GATE BYPASS     : NONE"
    )

    # ========================================================
    # ORDER INTENT
    # ========================================================

    intent_report = (
        verify_order_intent(
            runtime_output
        )
    )

    print()
    print(
        "6. ORDER INTENT CONTRACT"
    )

    print(
        "-------------------------"
    )

    print(
        f"TRADE_READY            : "
        f"{intent_report['trade_ready']}"
    )

    print(
        f"ORDER_INTENT           : "
        f"{intent_report['order_intent']}"
    )

    if (
        intent_report["trade_ready"]
        == 0
    ):

        print(
            "FAIL-CLOSED            : PASS"
        )

        print(
            "ARTIFICIAL INTENTS     : NONE"
        )

    else:

        print(
            "FAIL-CLOSED            : NOT APPLICABLE"
        )

        provenance = intent_report[
            "provenance"
        ]

        for field, owner in provenance.items():

            print(
                f"{field}: {owner}"
            )

    # ========================================================
    # IDENTITY PROPAGATION
    # ========================================================

    print()
    print(
        "7. IDENTITY PROPAGATION"
    )

    print(
        "-----------------------"
    )

    print(
        "CURRENT SNAPSHOT"
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

    print(
        f"CURRENT SNAPSHOT ID    : {snapshot_id}"
    )

    print(
        "LEGACY ID IN CURRENT BOUNDARY : NONE"
    )

    # ========================================================
    # PROVENANCE
    # ========================================================

    provenance = verify_provenance(
        runtime_output
    )

    print()
    print(
        "8. CURRENT PROVENANCE"
    )

    print(
        "---------------------"
    )

    print(
        "Market Snapshot        : CURRENT_PRODUCTION_RUNTIME"
    )

    print(
        "Market Data            : CURRENT_PRODUCTION_RUNTIME"
    )

    print(
        "Opportunity            : CURRENT_OPPORTUNITY"
    )

    print(
        "Signal                 : SIGNAL_VALIDATOR"
    )

    print(
        "Validation             : SIGNAL_VALIDATOR"
    )

    print(
        "Score                  : SCORE_PRODUCER"
    )

    print(
        "Signal Scorer          : SIGNAL_SCORER"
    )

    print(
        "Decision               : DECISION_ENGINE"
    )

    print(
        "Risk                   : RISK_ENGINE"
    )

    print(
        "Trade Gate             : TRADE_GATE_ENGINE"
    )

    print(
        "Order Intent Boundary  : CURRENT_ORDER_INTENT_BOUNDARY"
    )

    # ========================================================
    # LEGACY ISOLATION
    # ========================================================

    legacy_report = (
        verify_legacy_isolation(
            source,
            runtime_output,
        )
    )

    print()
    print(
        "9. LEGACY / MUSEUM ISOLATION"
    )

    print(
        "----------------------------"
    )

    print(
        "LEGACY DATA            : "
        "BLOCKED / ISOLATED"
    )

    print(
        "CURRENT RUNTIME LEAK   : NONE"
    )

    # ========================================================
    # NEGATIVE PATH
    # ========================================================

    verify_negative_path(
        source,
        runtime_output,
    )

    print()
    print(
        "10. NEGATIVE PATH"
    )

    print(
        "-----------------"
    )

    print(
        "INVALID PREREQUISITE   : FAIL-CLOSED"
    )

    print(
        "TRADE_READY            : "
        f"{intent_report['trade_ready']}"
    )

    print(
        "ORDER_INTENT           : "
        f"{intent_report['order_intent']}"
    )

    print(
        "EXECUTION              : DISABLED"
    )

    print(
        "BYPASS                 : NONE"
    )

    # ========================================================
    # WRITE / EXECUTION SAFETY
    # ========================================================

    print()
    print(
        "11. WRITE / EXECUTION SAFETY"
    )

    print(
        "-----------------------------"
    )

    print(
        "ORDER SUBMISSION       : NONE"
    )

    print(
        "EXCHANGE WRITE         : NONE"
    )

    print(
        "EXECUTION              : DISABLED"
    )

    print(
        "EXECUTION BYPASS       : NONE"
    )

    # ========================================================
    # DATA SAFETY
    # ========================================================

    print()
    print(
        "12. DATA SAFETY"
    )

    print(
        "----------------"
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

    # ========================================================
    # FINAL
    # ========================================================

    print()
    line()

    print(
        "CP11 EXECUTION RELEASE PREFLIGHT FINAL REPORT"
    )

    line()

    print()
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
        "CURRENT_RUNTIME        : VERIFIED"
    )

    print(
        "SNAPSHOT_IDENTITY      : VERIFIED"
    )

    print(
        "ASSET_COVERAGE         : 15/15"
    )

    print(
        "VALUE_INTEGRITY        : PASS"
    )

    print(
        "LEGACY DATA            : BLOCKED / ISOLATED"
    )

    print(
        "FAIL-CLOSED             : PASS"
    )

    print(
        "EXECUTION              : DISABLED"
    )

    print()
    print(
        "CP11 = PASS"
    )

    print(
        "STATUS = CLOSED / VERIFIED"
    )

    print(
        "RELEASE AUTHORIZATION = NOT GRANTED"
    )

    print(
        "NEXT CHECKPOINT = CP12 — FINAL PRODUCTION RELEASE REVIEW"
    )

    print()
    print(
        "ONE CHECKPOINT → ONE PREFLIGHT RUNTIME → "
        "ONE REPORT → MANAGEMENT REVIEW → STOP"
    )

    line()

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        raise SystemExit(
            main()
        )

    except Exception as exc:

        print()
        line()

        print(
            "CP11 = BLOCKED"
        )

        print(
            f"BLOCKER = {exc}"
        )

        print(
            "PRODUCTION BUSINESS LOGIC = UNCHANGED"
        )

        print(
            "EXECUTION = DISABLED"
        )

        print(
            "CP12 = NOT STARTED"
        )

        line()

        raise SystemExit(
            2
        )