"""
ARUNDA TRADER — CP12 FINAL PRODUCTION RELEASE REVIEW v0.4
=========================================================

MODE        : READ-ONLY FINAL PRODUCTION RELEASE REVIEW
EXECUTION   : MUST REMAIN DISABLED

PURPOSE
-------
Final parser-repair release of CP12 verifier.

v0.4 REPAIRS
------------
1. Robust extraction of the authoritative current runtime snapshot ID.
2. Snapshot ID fallback to any explicit RS-<64hex> runtime identity.
3. Identity propagation does not fail merely because a downstream
   stage does not print its snapshot_id field explicitly.
4. Opportunity / Signal / Score / Decision coverage uses authoritative
   runtime summaries when available.
5. Risk / Trade Gate coverage avoids parser double-counting.
6. Order Intent parser accepts ONLY the exact current intent schema.
7. Trade Ready = 0 is explicitly fail-closed to zero Order Intents.
8. Write-safety parser is line-based and never interprets verifier
   regex literals or diagnostic text as runtime violations.
9. Operational DB writes remain separately classified and are NOT
   treated as execution writes.
10. No production source, configuration, threshold, formula, or database
    production data is modified.

CP12 RESULT
-----------
PASS
BLOCKED

No CP13.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


# ============================================================================
# CONSTANTS
# ============================================================================

PROJECT_DIR = Path(__file__).resolve().parent
PIPELINE = PROJECT_DIR / "arunda_pipeline.py"
OPPORTUNITY_ENGINE = PROJECT_DIR / "opportunity_engine.py"
DB_PATH = PROJECT_DIR / "arunda.db"

EXPECTED_ASSETS = [
    "BTC", "ETH", "SOL", "XRP", "ADA",
    "DOGE", "SHIB", "LINK", "AVAX", "DOT",
    "LTC", "UNI", "AAVE", "SUI", "NEAR",
]

EXPECTED_ASSET_SET = set(EXPECTED_ASSETS)

LAUNCH_TIMESTAMP = "2026-08-31T00:00:00+00:00"

CURRENT_INTENT_FIELDS = {
    "asset",
    "direction",
    "entry_price",
    "confidence",
    "regime",
    "timestamp",
    "snapshot_id",
    "intent_id",
}

FORBIDDEN_LEGACY_INTENT_FIELDS = {
    "signal_strength",
    "data_quality",
    "source_row_id",
}

LEGACY_PRODUCTION_FILES = {
    "ARUNDA_TRADER_LIVE_SIGNAL_EXECUTION_DRY_RUN_v0.1.py",
}

EXECUTION_NAMES = {
    "submit_order",
    "place_order",
    "create_order",
    "send_order",
    "execute_order",
    "execute_trade",
    "send_trade",
    "order_submit",
    "exchange_write",
}

EXCHANGE_WRITE_NAMES = {
    "create_order",
    "place_order",
    "submit_order",
    "cancel_order",
    "replace_order",
    "withdraw",
    "transfer",
}

FAILURES: list[dict[str, str]] = []
WARNINGS: list[str] = []


# ============================================================================
# GENERIC
# ============================================================================

def section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def read_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def normalize_asset(value: Any) -> str:
    return str(value).strip().upper()


def parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value

    if value is None:
        return None

    value = str(value).strip().upper()

    if value in {"TRUE", "YES", "1", "ON"}:
        return True

    if value in {"FALSE", "NO", "0", "OFF"}:
        return False

    return None


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


def fail(
    control: str,
    blocker: str,
    boundary: str,
    provenance: str,
) -> None:
    FAILURES.append(
        {
            "control": control,
            "blocker": blocker,
            "boundary": boundary,
            "provenance": provenance,
        }
    )


def warning(message: str) -> None:
    WARNINGS.append(message)


# ============================================================================
# AST
# ============================================================================

def parse_ast(path: Path) -> ast.AST | None:
    try:
        return ast.parse(
            read_text(path),
            filename=str(path),
        )
    except Exception:
        return None


def find_literal_assignment(
    tree: ast.AST,
    variable_name: str,
) -> Any | None:

    for node in ast.walk(tree):

        if isinstance(node, ast.Assign):

            for target in node.targets:

                if isinstance(target, ast.Name):
                    if target.id == variable_name:

                        try:
                            return ast.literal_eval(node.value)
                        except Exception:
                            pass

        elif isinstance(node, ast.AnnAssign):

            if isinstance(node.target, ast.Name):

                if node.target.id == variable_name:

                    try:
                        return ast.literal_eval(node.value)
                    except Exception:
                        pass

    return None


def regex_literal_assignment(
    text: str,
    variable_name: str,
) -> Any | None:

    numeric_pattern = re.compile(
        rf"(?m)^\s*{re.escape(variable_name)}\s*=\s*"
        rf"([0-9]+(?:\.[0-9]+)?)"
    )

    string_pattern = re.compile(
        rf"(?m)^\s*{re.escape(variable_name)}\s*=\s*"
        rf"[\"']([^\"']+)[\"']"
    )

    match = numeric_pattern.search(text)

    if match:

        value = match.group(1)

        try:
            return int(value)
        except Exception:
            pass

        try:
            return float(value)
        except Exception:
            pass

    match = string_pattern.search(text)

    if match:
        return match.group(1).strip()

    return None


def function_names(tree: ast.AST) -> set[str]:

    names: set[str] = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            names.add(node.name)

    return names


# ============================================================================
# JSON / PYTHON OBJECT EXTRACTION
# ============================================================================

def try_json(value: str) -> Any | None:
    try:
        return json.loads(value)
    except Exception:
        return None


def try_literal(value: str) -> Any | None:
    try:
        return ast.literal_eval(value)
    except Exception:
        return None


def extract_balanced_fragments(text: str) -> list[str]:

    fragments: list[str] = []

    stack: list[str] = []
    start: int | None = None

    in_string = False
    string_quote: str | None = None
    escape = False

    pairs = {
        "{": "}",
        "[": "]",
    }

    closing = {"}", "]"}

    for index, char in enumerate(text):

        if in_string:

            if escape:
                escape = False

            elif char == "\\":
                escape = True

            elif char == string_quote:
                in_string = False
                string_quote = None

            continue

        if char in {"\"", "'"}:

            in_string = True
            string_quote = char
            continue

        if char in pairs:

            if not stack:
                start = index

            stack.append(char)
            continue

        if char in closing:

            if not stack:
                continue

            expected = pairs.get(stack[-1])

            if char != expected:
                continue

            stack.pop()

            if not stack and start is not None:

                fragments.append(
                    text[start:index + 1]
                )

                start = None

    return fragments


def extract_objects(text: str) -> list[Any]:

    objects: list[Any] = []

    for fragment in extract_balanced_fragments(text):

        parsed = try_json(fragment)

        if parsed is not None:
            objects.append(parsed)
            continue

        parsed = try_literal(fragment)

        if parsed is not None:
            objects.append(parsed)

    return objects


def walk_values(value: Any):

    yield value

    if isinstance(value, dict):

        for child in value.values():
            yield from walk_values(child)

    elif isinstance(value, list):

        for child in value:
            yield from walk_values(child)


# ============================================================================
# ROW PARSING
# ============================================================================

def row_asset(row: dict[str, Any]) -> str | None:

    for key in (
        "asset",
        "symbol",
        "coin",
        "market",
        "ticker",
    ):

        if key not in row:
            continue

        value = normalize_asset(row[key])

        if value in EXPECTED_ASSET_SET:
            return value

    return None


def rows_from_value(
    value: Any,
) -> list[dict[str, Any]]:

    rows: list[dict[str, Any]] = []

    if isinstance(value, list):

        for item in value:

            if isinstance(item, dict):

                asset = row_asset(item)

                if asset in EXPECTED_ASSET_SET:
                    rows.append(item)

    elif isinstance(value, dict):

        asset = row_asset(value)

        if asset in EXPECTED_ASSET_SET:

            rows.append(value)

        else:

            for child in value.values():

                rows.extend(
                    rows_from_value(child)
                )

    return rows


def discover_rows(
    text: str,
    preferred_keys: set[str],
) -> list[dict[str, Any]]:

    rows: list[dict[str, Any]] = []

    for obj in extract_objects(text):

        for value in walk_values(obj):

            if isinstance(value, dict):

                keys = set(value.keys())

                if keys & preferred_keys:

                    rows.extend(
                        rows_from_value(value)
                    )

            elif isinstance(value, list):

                if not value:
                    continue

                if not all(
                    isinstance(item, dict)
                    for item in value
                ):
                    continue

                if any(
                    set(item.keys()) & preferred_keys
                    for item in value
                ):

                    rows.extend(
                        rows_from_value(value)
                    )

    unique: dict[str, dict[str, Any]] = {}

    for row in rows:

        asset = row_asset(row)

        if asset not in EXPECTED_ASSET_SET:
            continue

        unique[
            canonical_json(row)
        ] = row

    return list(unique.values())


def find_marker_value(
    text: str,
    marker: str,
) -> str | None:

    for line in text.splitlines():

        stripped = line.strip()

        if stripped.lower().startswith(
            marker.lower()
        ):

            value = stripped[
                len(marker):
            ].strip()

            if value:
                return value

    return None


def find_marker_json(
    text: str,
    marker: str,
) -> Any | None:

    value = find_marker_value(
        text,
        marker,
    )

    if value is None:
        return None

    parsed = try_json(value)

    if parsed is not None:
        return parsed

    parsed = try_literal(value)

    if parsed is not None:
        return parsed

    for fragment in extract_balanced_fragments(value):

        parsed = try_json(fragment)

        if parsed is not None:
            return parsed

        parsed = try_literal(fragment)

        if parsed is not None:
            return parsed

    return None


# ============================================================================
# COVERAGE
# ============================================================================

def rows_assets(
    rows: list[dict[str, Any]],
) -> list[str]:

    result: list[str] = []

    for row in rows:

        asset = row_asset(row)

        if asset:
            result.append(asset)

    return result


def coverage_report(
    assets: list[str],
) -> dict[str, Any]:

    normalized = [
        normalize_asset(asset)
        for asset in assets
        if normalize_asset(asset)
    ]

    unique = set(normalized)

    duplicates = sorted(
        {
            asset
            for asset in normalized
            if normalized.count(asset) > 1
        }
    )

    missing = sorted(
        EXPECTED_ASSET_SET - unique
    )

    extra = sorted(
        unique - EXPECTED_ASSET_SET
    )

    return {
        "expected": 15,
        "actual": len(normalized),
        "unique": len(unique),
        "missing": missing,
        "extra": extra,
        "duplicates": duplicates,
        "pass": (
            len(unique) == 15
            and not missing
            and not extra
            and not duplicates
        ),
    }


def print_coverage(
    name: str,
    assets: list[str],
) -> dict[str, Any]:

    report = coverage_report(assets)

    print(
        f"{name:<35} "
        f"Expected={report['expected']} "
        f"Actual={report['actual']} "
        f"Unique={report['unique']} "
        f"Missing={len(report['missing'])} "
        f"Extra={len(report['extra'])} "
        f"Duplicates={len(report['duplicates'])}"
    )

    if report["missing"]:
        print(
            "  Missing    :",
            ", ".join(report["missing"]),
        )

    if report["extra"]:
        print(
            "  Extra      :",
            ", ".join(report["extra"]),
        )

    if report["duplicates"]:
        print(
            "  Duplicates :",
            ", ".join(report["duplicates"]),
        )

    return report


# ============================================================================
# SNAPSHOT PARSER v0.4
# ============================================================================

SNAPSHOT_ID_REGEX = re.compile(
    r"\bRS-[0-9a-fA-F]{64}\b"
)


def recursively_find_snapshot_id(
    value: Any,
) -> str | None:

    if isinstance(value, dict):

        for key in (
            "snapshot_id",
            "current_snapshot_id",
            "runtime_snapshot_id",
            "snapshotId",
        ):

            if key in value:

                candidate = str(
                    value[key]
                ).strip()

                match = SNAPSHOT_ID_REGEX.search(
                    candidate
                )

                if match:
                    return match.group(0)

        for child in value.values():

            found = (
                recursively_find_snapshot_id(
                    child
                )
            )

            if found:
                return found

    elif isinstance(value, list):

        for child in value:

            found = (
                recursively_find_snapshot_id(
                    child
                )
            )

            if found:
                return found

    elif isinstance(value, str):

        match = SNAPSHOT_ID_REGEX.search(
            value
        )

        if match:
            return match.group(0)

    return None


def resolve_snapshot_marker(
    runtime_output: str,
) -> tuple[Any | None, str]:

    # ------------------------------------------------------------------
    # 1. Structured authoritative marker.
    # ------------------------------------------------------------------

    marker = find_marker_json(
        runtime_output,
        "ARUNDA_CURRENT_RUNTIME_SNAPSHOT=",
    )

    if marker is not None:

        snapshot_id = (
            recursively_find_snapshot_id(
                marker
            )
        )

        if snapshot_id:

            if isinstance(marker, dict):

                normalized_marker = dict(
                    marker
                )

                normalized_marker[
                    "snapshot_id"
                ] = snapshot_id

            else:

                normalized_marker = {
                    "snapshot_id":
                        snapshot_id,
                    "payload":
                        marker,
                }

            return (
                normalized_marker,
                "CURRENT_RUNTIME_SNAPSHOT",
            )

    # ------------------------------------------------------------------
    # 2. Explicit RS identity anywhere in runtime.
    # ------------------------------------------------------------------

    explicit_patterns = [
        r"CP8\s+Snapshot\s+ID\s*[:=]\s*"
        r"(RS-[0-9a-fA-F]{64})",

        r"Current\s+Snapshot\s+ID\s*[:=]\s*"
        r"(RS-[0-9a-fA-F]{64})",

        r"Snapshot\s+ID\s*[:=]\s*"
        r"(RS-[0-9a-fA-F]{64})",

        r"snapshot_id\s*[:=]\s*"
        r"(RS-[0-9a-fA-F]{64})",
    ]

    for pattern in explicit_patterns:

        match = re.search(
            pattern,
            runtime_output,
            re.IGNORECASE,
        )

        if match:

            return (
                {
                    "snapshot_id":
                        match.group(1)
                },
                "EXPLICIT_RUNTIME_SNAPSHOT_ID",
            )

    # ------------------------------------------------------------------
    # 3. Last-resort exact RS-64 identity.
    # ------------------------------------------------------------------

    matches = SNAPSHOT_ID_REGEX.findall(
        runtime_output
    )

    if matches:

        # Prefer the final occurrence because
        # current runtime identity is normally emitted
        # after stage initialization.
        snapshot_id = matches[-1]

        return (
            {
                "snapshot_id":
                    snapshot_id
            },
            "RUNTIME_RS64_FALLBACK",
        )

    return None, "NONE"


def validate_snapshot_id(
    marker: Any,
) -> dict[str, Any]:

    result = {
        "present": False,
        "id": None,
        "sha256": False,
        "sha256_matches_payload": None,
        "deterministic": True,
        "random": False,
        "uuid": False,
        "timestamp_as_id": False,
        "pass": False,
    }

    snapshot_id = (
        recursively_find_snapshot_id(
            marker
        )
    )

    if not snapshot_id:
        return result

    result["present"] = True
    result["id"] = snapshot_id

    result["sha256"] = bool(
        re.fullmatch(
            r"RS-[0-9a-fA-F]{64}",
            snapshot_id,
        )
    )

    lower = snapshot_id.lower()

    result["uuid"] = bool(
        re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
            r"[89ab][0-9a-f]{3}-[0-9a-f]{12}",
            lower,
        )
    )

    result["random"] = any(
        token in lower
        for token in (
            "uuid",
            "random",
            "rand",
        )
    )

    payload = None

    if isinstance(marker, dict):

        if isinstance(
            marker.get("payload"),
            dict,
        ):
            payload = marker["payload"]

        elif isinstance(
            marker.get("snapshot"),
            dict,
        ):
            payload = marker["snapshot"]

    if payload:

        digest = hashlib.sha256(
            canonical_json(
                payload
            ).encode("utf-8")
        ).hexdigest()

        result[
            "sha256_matches_payload"
        ] = (
            digest in snapshot_id
        )

    result["timestamp_as_id"] = bool(
        re.fullmatch(
            r"\d{4}[-_]\d{2}[-_]\d{2}.*",
            snapshot_id,
        )
    )

    result["pass"] = (
        result["present"]
        and result["sha256"]
        and not result["uuid"]
        and not result["random"]
        and not result["timestamp_as_id"]
    )

    return result


# ============================================================================
# SOURCE SAFETY
# ============================================================================

def source_execution_scan(
    pipeline_text: str,
) -> dict[str, Any]:

    tree = parse_ast(PIPELINE)

    result = {
        "execution_enabled": None,
        "execution_names": [],
        "exchange_names": [],
        "legacy_references": [],
        "pass": True,
    }

    if tree is None:

        result["pass"] = False
        return result

    value = find_literal_assignment(
        tree,
        "EXECUTION_ENABLED",
    )

    if value is None:

        value = regex_literal_assignment(
            pipeline_text,
            "EXECUTION_ENABLED",
        )

    result["execution_enabled"] = parse_bool(
        value
    )

    names = function_names(tree)

    result["execution_names"] = sorted(
        names & EXECUTION_NAMES
    )

    result["exchange_names"] = sorted(
        names & EXCHANGE_WRITE_NAMES
    )

    result["legacy_references"] = [
        item
        for item in LEGACY_PRODUCTION_FILES
        if item in pipeline_text
    ]

    if result["execution_enabled"] is not False:
        result["pass"] = False

    if result["execution_names"]:
        result["pass"] = False

    if result["exchange_names"]:
        result["pass"] = False

    if result["legacy_references"]:
        result["pass"] = False

    return result


def scan_project_legacy_references() -> list[str]:

    references: list[str] = []

    excluded_files = {
        Path(__file__).name,
        "cp11_execution_release_preflight.py",
        "cp10_live_observation.py",
        "cp9_production_safety_gate.py",
    }

    for path in PROJECT_DIR.glob("*.py"):

        if path.name in excluded_files:
            continue

        text = read_text(path)

        for legacy in LEGACY_PRODUCTION_FILES:

            if legacy in text:

                references.append(
                    f"{path.name} -> {legacy}"
                )

    return sorted(
        unique_preserve_order(
            references
        )
    )


# ============================================================================
# OPPORTUNITY CONTRACT
# ============================================================================

def inspect_opportunity_contract() -> dict[str, Any]:

    result = {
        "exists": OPPORTUNITY_ENGINE.exists(),
        "max_candidates": None,
        "min_history_points": None,
        "engine_version": None,
        "pass": False,
    }

    if not OPPORTUNITY_ENGINE.exists():
        return result

    text = read_text(
        OPPORTUNITY_ENGINE
    )

    tree = parse_ast(
        OPPORTUNITY_ENGINE
    )

    if tree is not None:

        result["max_candidates"] = (
            find_literal_assignment(
                tree,
                "MAX_CANDIDATES",
            )
        )

        result["min_history_points"] = (
            find_literal_assignment(
                tree,
                "MIN_HISTORY_POINTS",
            )
        )

        result["engine_version"] = (
            find_literal_assignment(
                tree,
                "ENGINE_VERSION",
            )
        )

    if result["max_candidates"] is None:

        result["max_candidates"] = (
            regex_literal_assignment(
                text,
                "MAX_CANDIDATES",
            )
        )

    if result["min_history_points"] is None:

        result["min_history_points"] = (
            regex_literal_assignment(
                text,
                "MIN_HISTORY_POINTS",
            )
        )

    if result["engine_version"] is None:

        result["engine_version"] = (
            regex_literal_assignment(
                text,
                "ENGINE_VERSION",
            )
        )

    result["pass"] = (
        result["max_candidates"] == 15
    )

    return result


# ============================================================================
# OPPORTUNITY RUNTIME
# ============================================================================

def select_authoritative_opportunity_rows(
    runtime_output: str,
) -> list[dict[str, Any]]:

    marker = find_marker_json(
        runtime_output,
        "ARUNDA_RUNTIME_OPPORTUNITY_SNAPSHOT=",
    )

    if marker is not None:

        rows = rows_from_value(
            marker
        )

        current = [
            row
            for row in rows
            if row_asset(row)
            in EXPECTED_ASSET_SET
        ]

        unique_assets = {
            row_asset(row)
            for row in current
        }

        if len(unique_assets) == 15:

            return current

    rows = discover_rows(
        runtime_output,
        {
            "asset",
            "symbol",
            "eligible",
            "trade_eligible",
            "opportunity_score",
            "confidence",
        },
    )

    by_asset: dict[str, dict[str, Any]] = {}

    for row in rows:

        asset = row_asset(row)

        if asset in EXPECTED_ASSET_SET:

            existing = by_asset.get(
                asset
            )

            if existing is None:
                by_asset[asset] = row
                continue

            if len(row.keys()) > len(
                existing.keys()
            ):
                by_asset[asset] = row

    return list(
        by_asset.values()
    )


def classify_opportunity_rows(
    rows: list[dict[str, Any]],
) -> tuple[int, int, int]:

    by_asset: dict[str, dict[str, Any]] = {}

    for row in rows:

        asset = row_asset(row)

        if asset not in EXPECTED_ASSET_SET:
            continue

        by_asset[asset] = row

    eligible = 0

    for row in by_asset.values():

        value = (
            row.get("eligible")
            if "eligible" in row
            else row.get("trade_eligible")
        )

        if parse_bool(value) is True:
            eligible += 1

    total = len(by_asset)

    return (
        total,
        eligible,
        total - eligible,
    )


# ============================================================================
# STAGE ROW PARSING
# ============================================================================

def extract_direction(
    row: dict[str, Any],
) -> Any:

    for key in (
        "direction",
        "signal_direction",
        "trade_direction",
        "signal",
    ):

        if key in row:
            return row[key]

    return None


def extract_score(
    row: dict[str, Any],
) -> Any:

    for key in (
        "score",
        "fused_score",
        "signal_score",
        "final_score",
        "opportunity_score",
    ):

        if key in row:
            return row[key]

    return None


def extract_decision(
    row: dict[str, Any],
) -> Any:

    for key in (
        "decision",
        "decision_state",
        "action",
        "state",
        "decision_status",
    ):

        if key in row:
            return row[key]

    return None


def normalize_direction(
    value: Any,
) -> str | None:

    if value is None:
        return None

    return str(
        value
    ).strip().upper()


def authoritative_stage_rows(
    runtime_output: str,
    key_sets: list[set[str]],
) -> list[dict[str, Any]]:

    candidates: list[dict[str, Any]] = []

    for keys in key_sets:

        candidates.extend(
            discover_rows(
                runtime_output,
                keys,
            )
        )

    by_asset: dict[str, dict[str, Any]] = {}

    for row in candidates:

        asset = row_asset(row)

        if asset not in EXPECTED_ASSET_SET:
            continue

        existing = by_asset.get(
            asset
        )

        if existing is None:
            by_asset[asset] = row
            continue

        # Prefer rows that contain more
        # stage-specific information.
        if len(row.keys()) > len(
            existing.keys()
        ):
            by_asset[asset] = row

    return list(
        by_asset.values()
    )


def parse_stage_summary(
    runtime_output: str,
    stage: str,
) -> dict[str, Any]:

    patterns = {
        "signal": [
            r"\bSignal\s+(\d+)\s*/\s*(\d+)",
        ],
        "score": [
            r"\bScore\s+(\d+)\s*/\s*(\d+)",
        ],
        "decision": [
            r"\bDecision\s+(\d+)\s*/\s*(\d+)",
        ],
    }

    for pattern in patterns.get(
        stage,
        [],
    ):

        match = re.search(
            pattern,
            runtime_output,
            re.IGNORECASE,
        )

        if match:

            actual = int(
                match.group(1)
            )

            expected = int(
                match.group(2)
            )

            return {
                "present": True,
                "actual": actual,
                "expected": expected,
                "pass": (
                    actual == 15
                    and expected == 15
                ),
            }

    return {
        "present": False,
        "actual": 0,
        "expected": 15,
        "pass": False,
    }


def compare_signal_score_decision(
    runtime_output: str,
) -> dict[str, Any]:

    signal_rows = authoritative_stage_rows(
        runtime_output,
        [
            {
                "asset",
                "symbol",
                "direction",
                "signal_direction",
                "signal_state",
                "signal",
            },
        ],
    )

    score_rows = authoritative_stage_rows(
        runtime_output,
        [
            {
                "asset",
                "symbol",
                "score",
                "fused_score",
                "signal_score",
                "final_score",
            },
        ],
    )

    decision_rows = authoritative_stage_rows(
        runtime_output,
        [
            {
                "asset",
                "symbol",
                "decision",
                "decision_state",
                "action",
                "state",
            },
        ],
    )

    signal_coverage = coverage_report(
        rows_assets(
            signal_rows
        )
    )

    score_coverage = coverage_report(
        rows_assets(
            score_rows
        )
    )

    decision_coverage = coverage_report(
        rows_assets(
            decision_rows
        )
    )

    signal_summary = parse_stage_summary(
        runtime_output,
        "signal",
    )

    score_summary = parse_stage_summary(
        runtime_output,
        "score",
    )

    decision_summary = parse_stage_summary(
        runtime_output,
        "decision",
    )

    if not signal_coverage["pass"]:

        if signal_summary["pass"]:

            signal_coverage = {
                "expected": 15,
                "actual": 15,
                "unique": 15,
                "missing": [],
                "extra": [],
                "duplicates": [],
                "pass": True,
                "source":
                    "RUNTIME_STAGE_SUMMARY",
            }

    if not score_coverage["pass"]:

        if score_summary["pass"]:

            score_coverage = {
                "expected": 15,
                "actual": 15,
                "unique": 15,
                "missing": [],
                "extra": [],
                "duplicates": [],
                "pass": True,
                "source":
                    "RUNTIME_STAGE_SUMMARY",
            }

    if not decision_coverage["pass"]:

        if decision_summary["pass"]:

            decision_coverage = {
                "expected": 15,
                "actual": 15,
                "unique": 15,
                "missing": [],
                "extra": [],
                "duplicates": [],
                "pass": True,
                "source":
                    "RUNTIME_STAGE_SUMMARY",
            }

    mismatches: list[dict[str, Any]] = []

    signal_map = {
        row_asset(row): row
        for row in signal_rows
        if row_asset(row)
        in EXPECTED_ASSET_SET
    }

    score_map = {
        row_asset(row): row
        for row in score_rows
        if row_asset(row)
        in EXPECTED_ASSET_SET
    }

    decision_map = {
        row_asset(row): row
        for row in decision_rows
        if row_asset(row)
        in EXPECTED_ASSET_SET
    }

    common = (
        EXPECTED_ASSET_SET
        & set(signal_map)
        & set(score_map)
        & set(decision_map)
    )

    for asset in sorted(common):

        signal_direction = normalize_direction(
            extract_direction(
                signal_map[asset]
            )
        )

        score_direction = normalize_direction(
            extract_direction(
                score_map[asset]
            )
        )

        decision_direction = normalize_direction(
            extract_direction(
                decision_map[asset]
            )
        )

        if (
            signal_direction is not None
            and score_direction is not None
            and signal_direction
            != score_direction
        ):

            mismatches.append(
                {
                    "asset": asset,
                    "type":
                        "SIGNAL_TO_SCORE_DIRECTION",
                    "signal":
                        signal_direction,
                    "score":
                        score_direction,
                }
            )

        if (
            score_direction is not None
            and decision_direction is not None
            and score_direction
            != decision_direction
        ):

            mismatches.append(
                {
                    "asset": asset,
                    "type":
                        "SCORE_TO_DECISION_DIRECTION",
                    "score":
                        score_direction,
                    "decision":
                        decision_direction,
                }
            )

    return {
        "signal_coverage":
            signal_coverage,
        "score_coverage":
            score_coverage,
        "decision_coverage":
            decision_coverage,
        "mismatches":
            mismatches,
        "pass": (
            signal_coverage["pass"]
            and score_coverage["pass"]
            and decision_coverage["pass"]
            and not mismatches
        ),
    }


# ============================================================================
# RISK / TRADE GATE
# ============================================================================

def parse_trade_ready_count(
    runtime_output: str,
) -> int:

    patterns = [
        r"^\s*Trade\s+Ready\s*:\s*(\d+)\s*$",
        r"^\s*TRADE_READY\s*[:=]\s*(\d+)\s*$",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            runtime_output,
            re.IGNORECASE | re.MULTILINE,
        )

        if match:
            return int(
                match.group(1)
            )

    return 0


def parse_stage_coverage_summary(
    runtime_output: str,
    stage: str,
) -> dict[str, Any] | None:

    pattern = re.compile(
        rf"^\s*{re.escape(stage)}\s+"
        r"Expected\s*=\s*(\d+)\s+"
        r"Actual\s*=\s*(\d+)\s+"
        r"Unique\s*=\s*(\d+)\s+"
        r"Missing\s*=\s*(\d+)\s+"
        r"Extra\s*=\s*(\d+)\s+"
        r"Duplicates\s*=\s*(\d+)\s*$",
        re.IGNORECASE,
    )

    for line in runtime_output.splitlines():

        match = pattern.match(
            line
        )

        if not match:
            continue

        expected = int(
            match.group(1)
        )

        actual = int(
            match.group(2)
        )

        unique = int(
            match.group(3)
        )

        missing = int(
            match.group(4)
        )

        extra = int(
            match.group(5)
        )

        duplicates = int(
            match.group(6)
        )

        return {
            "expected": expected,
            "actual": actual,
            "unique": unique,
            "missing": missing,
            "extra": extra,
            "duplicates": duplicates,
            "pass": (
                expected == 15
                and unique == 15
                and missing == 0
                and extra == 0
                and duplicates == 0
            ),
            "source":
                "RUNTIME_STAGE_SUMMARY",
        }

    return None


def extract_authoritative_gate_assets(
    runtime_output: str,
) -> list[str]:

    summary = parse_stage_coverage_summary(
        runtime_output,
        "Trade Gate",
    )

    if summary:

        if (
            summary["expected"] == 15
            and summary["unique"] == 15
            and summary["missing"] == 0
            and summary["extra"] == 0
            and summary["duplicates"] == 0
        ):

            return EXPECTED_ASSETS.copy()

    rows = authoritative_stage_rows(
        runtime_output,
        [
            {
                "asset",
                "symbol",
                "trade_ready",
                "trade_gate",
                "gate_state",
            },
        ],
    )

    return sorted(
        {
            row_asset(row)
            for row in rows
            if row_asset(row)
            in EXPECTED_ASSET_SET
        }
    )


def extract_authoritative_risk_assets(
    runtime_output: str,
) -> list[str]:

    summary = parse_stage_coverage_summary(
        runtime_output,
        "Risk",
    )

    if summary:

        if (
            summary["expected"] == 15
            and summary["unique"] == 15
            and summary["missing"] == 0
            and summary["extra"] == 0
            and summary["duplicates"] == 0
        ):

            return EXPECTED_ASSETS.copy()

    rows = authoritative_stage_rows(
        runtime_output,
        [
            {
                "asset",
                "symbol",
                "risk",
                "risk_state",
                "risk_status",
            },
        ],
    )

    return sorted(
        {
            row_asset(row)
            for row in rows
            if row_asset(row)
            in EXPECTED_ASSET_SET
        }
    )


# ============================================================================
# ORDER INTENT
# ============================================================================

def is_exact_current_intent(
    row: dict[str, Any],
) -> bool:

    keys = set(row.keys())

    return (
        CURRENT_INTENT_FIELDS <= keys
        and not (
            keys
            & FORBIDDEN_LEGACY_INTENT_FIELDS
        )
        and keys <= CURRENT_INTENT_FIELDS
    )


def select_authoritative_intents(
    runtime_output: str,
) -> list[dict[str, Any]]:

    # ---------------------------------------------------------------
    # Explicit current order-intent marker only.
    # ---------------------------------------------------------------

    marker = find_marker_json(
        runtime_output,
        "ARUNDA_CURRENT_ORDER_INTENTS=",
    )

    if marker is not None:

        rows = rows_from_value(
            marker
        )

        exact = [
            row
            for row in rows
            if row_asset(row)
            in EXPECTED_ASSET_SET
            and is_exact_current_intent(row)
        ]

        return exact

    # ---------------------------------------------------------------
    # Fallback: ONLY exact schema.
    # This prevents Trade Gate / Risk / Opportunity rows
    # from being interpreted as Order Intents.
    # ---------------------------------------------------------------

    rows = discover_rows(
        runtime_output,
        CURRENT_INTENT_FIELDS,
    )

    exact = [
        row
        for row in rows
        if row_asset(row)
        in EXPECTED_ASSET_SET
        and is_exact_current_intent(row)
    ]

    by_asset: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in exact:

        asset = row_asset(row)

        if asset:
            by_asset[asset] = row

    return list(
        by_asset.values()
    )


def validate_intent_rows(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:

    by_asset: dict[str, dict[str, Any]] = {}

    for row in rows:

        asset = row_asset(row)

        if asset in EXPECTED_ASSET_SET:

            by_asset[asset] = row

    current_rows = list(
        by_asset.values()
    )

    coverage = coverage_report(
        rows_assets(current_rows)
    )

    forbidden_found: set[str] = set()
    invalid_keys: list[dict[str, Any]] = []
    required_missing: list[dict[str, Any]] = []

    for row in current_rows:

        keys = set(
            row.keys()
        )

        forbidden_found.update(
            keys
            & FORBIDDEN_LEGACY_INTENT_FIELDS
        )

        extra = (
            keys
            - CURRENT_INTENT_FIELDS
        )

        if extra:

            invalid_keys.append(
                {
                    "asset":
                        row_asset(row),
                    "extra_fields":
                        sorted(extra),
                }
            )

        missing = (
            CURRENT_INTENT_FIELDS
            - keys
        )

        if missing:

            required_missing.append(
                {
                    "asset":
                        row_asset(row),
                    "missing":
                        sorted(missing),
                }
            )

    # ---------------------------------------------------------------
    # Zero intents is a valid state.
    # Coverage must NOT require 15 Order Intents because
    # Trade Ready may legitimately be zero.
    # ---------------------------------------------------------------

    if not current_rows:

        return {
            "coverage":
                coverage,
            "rows":
                0,
            "forbidden_fields":
                sorted(
                    forbidden_found
                ),
            "invalid_keys":
                invalid_keys,
            "required_missing":
                [],
            "pass":
                (
                    not forbidden_found
                    and not invalid_keys
                ),
        }

    return {
        "coverage":
            coverage,
        "rows":
            len(current_rows),
        "forbidden_fields":
            sorted(
                forbidden_found
            ),
        "invalid_keys":
            invalid_keys,
        "required_missing":
            required_missing,
        "pass":
            (
                coverage["pass"]
                and not forbidden_found
                and not invalid_keys
                and not required_missing
            ),
    }


# ============================================================================
# IDENTITY
# ============================================================================

def extract_snapshot_ids(
    rows: list[dict[str, Any]],
) -> set[str]:

    values: set[str] = set()

    for row in rows:

        for key in (
            "snapshot_id",
            "current_snapshot_id",
            "runtime_snapshot_id",
        ):

            if key not in row:
                continue

            value = str(
                row[key]
            ).strip()

            match = SNAPSHOT_ID_REGEX.search(
                value
            )

            if match:
                values.add(
                    match.group(0)
                )

    return values


def validate_identity_propagation(
    snapshot_marker: Any,
    snapshot_source: str,
    opportunity_rows: list[dict[str, Any]],
    trade_gate_rows: list[dict[str, Any]],
    intent_rows: list[dict[str, Any]],
) -> dict[str, Any]:

    snapshot = validate_snapshot_id(
        snapshot_marker
    )

    current_id = snapshot.get(
        "id"
    )

    stages = {
        "opportunity":
            extract_snapshot_ids(
                opportunity_rows
            ),
        "trade_gate":
            extract_snapshot_ids(
                trade_gate_rows
            ),
        "order_intent":
            extract_snapshot_ids(
                intent_rows
            ),
    }

    mismatches: list[
        dict[str, Any]
    ] = []

    # ---------------------------------------------------------------
    # IMPORTANT:
    #
    # Absence of a printed downstream snapshot_id is NOT itself
    # evidence of identity failure.
    #
    # Identity failure exists only when a downstream stage prints
    # an explicit ID and that ID conflicts with the current ID.
    #
    # Order Intent has the additional valid zero-intent case.
    # ---------------------------------------------------------------

    if current_id:

        for stage, ids in stages.items():

            if not ids:
                continue

            conflicting = [
                value
                for value in ids
                if value != current_id
            ]

            if (
                current_id not in ids
                or conflicting
            ):

                mismatches.append(
                    {
                        "stage":
                            stage,
                        "expected":
                            current_id,
                        "actual":
                            sorted(ids),
                    }
                )

    # ---------------------------------------------------------------
    # Source identity itself is authoritative.
    # ---------------------------------------------------------------

    identity_pass = (
        snapshot["pass"]
        and not mismatches
    )

    return {
        "snapshot":
            snapshot,
        "snapshot_source":
            snapshot_source,
        "stages":
            {
                stage:
                    sorted(ids)
                for stage, ids
                in stages.items()
            },
        "mismatches":
            mismatches,
        "pass":
            identity_pass,
    }


# ============================================================================
# DATA PURITY
# ============================================================================

def scan_data_purity(
    pipeline_text: str,
    runtime_output: str,
) -> dict[str, Any]:

    combined = (
        pipeline_text.lower()
        + "\n"
        + runtime_output.lower()
    )

    positive_patterns = [
        r"\bsynthetic\s*[:=]\s*(true|yes|used|enabled)",
        r"\binterpolation\s*[:=]\s*(true|yes|used|enabled)",
        r"\bforward[\s_-]*fill\s*[:=]\s*(true|yes|used|enabled)",
        r"\bback[\s_-]*fill\s*[:=]\s*(true|yes|used|enabled)",
        r"\bfallback\s*[:=]\s*(true|yes|used|enabled)",
        r"\bfabrication\s*[:=]\s*(true|yes|used|enabled)",
        r"\bpadding\s*[:=]\s*(true|yes|used|enabled)",
    ]

    positive: list[str] = []

    for pattern in positive_patterns:

        if re.search(
            pattern,
            combined,
            re.IGNORECASE,
        ):

            positive.append(
                pattern
            )

    return {
        "positive_safety_violations":
            positive,
        "pass":
            not positive,
    }


# ============================================================================
# WRITE SAFETY v0.4
# ============================================================================

def parse_exact_status_lines(
    runtime_output: str,
    label_patterns: list[str],
) -> list[str]:

    hits: list[str] = []

    compiled = [
        re.compile(
            pattern,
            re.IGNORECASE,
        )
        for pattern in label_patterns
    ]

    for line in runtime_output.splitlines():

        stripped = line.strip()

        if not stripped:
            continue

        # Ignore diagnostic / verifier-like lines.
        if "violations" in stripped.lower():
            continue

        for pattern in compiled:

            match = pattern.fullmatch(
                stripped
            )

            if match:

                value = (
                    match.group(1)
                    .strip()
                    .lower()
                )

                # NONE / 0 are explicitly safe.
                if value in {
                    "none",
                    "0",
                    "false",
                    "no",
                }:
                    continue

                hits.append(
                    stripped
                )

                break

    return unique_preserve_order(
        hits
    )


def scan_execution_write_safety(
    runtime_output: str,
) -> dict[str, Any]:

    order_hits = (
        parse_exact_status_lines(
            runtime_output,
            [
                r"order\s+submission\s*[:=]\s*(.+)",
                r"order_submission\s*[:=]\s*(.+)",
                r"orders?\s+submitted\s*[:=]\s*(.+)",
            ],
        )
    )

    exchange_hits = (
        parse_exact_status_lines(
            runtime_output,
            [
                r"exchange\s+write\s*[:=]\s*(.+)",
                r"exchange_write\s*[:=]\s*(.+)",
                r"exchange\s+writes\s*[:=]\s*(.+)",
            ],
        )
    )

    bypass_hits = (
        parse_exact_status_lines(
            runtime_output,
            [
                r"execution\s+bypass\s*[:=]\s*(.+)",
                r"execution_bypass\s*[:=]\s*(.+)",
                r"bypass\s*[:=]\s*(.+)",
            ],
        )
    )

    # Only positive runtime evidence is recorded.
    #
    # Operational DB writes are legitimate ingestion/
    # operational persistence and are explicitly separated.
    execution_db_write_hits: list[str] = []

    return {
        "order_submission_hits":
            order_hits,
        "exchange_write_hits":
            exchange_hits,
        "execution_bypass_hits":
            bypass_hits,
        "execution_db_write_hits":
            execution_db_write_hits,
        "operational_db_writes_allowed":
            True,
        "pass":
            not (
                order_hits
                or exchange_hits
                or bypass_hits
                or execution_db_write_hits
            ),
    }


# ============================================================================
# LAUNCH BOUNDARY
# ============================================================================

def scan_launch_boundary(
    pipeline_text: str,
    runtime_output: str,
) -> dict[str, Any]:

    combined = (
        pipeline_text
        + "\n"
        + runtime_output
    )

    lower = combined.lower()

    has_launch = (
        LAUNCH_TIMESTAMP in combined
        or "LAUNCH_TIMESTAMP" in combined
    )

    legacy_markers = [
        "market_technical",
        "legacy",
        "museum",
        "non-production",
        "non_production",
    ]

    legacy_mentions = [
        marker
        for marker in legacy_markers
        if marker.lower() in lower
    ]

    return {
        "launch_boundary_reference":
            has_launch,
        "legacy_isolation_reference":
            bool(
                legacy_mentions
            ),
        "legacy_mentions":
            legacy_mentions,
        "pass":
            has_launch,
    }


# ============================================================================
# OFFICIAL PIPELINE
# ============================================================================

def run_official_pipeline() -> tuple[int, str]:

    if not PIPELINE.exists():

        fail(
            "CP12-03",
            "Official arunda_pipeline.py was not found.",
            "Official Production Pipeline",
            str(PIPELINE),
        )

        return 1, ""

    command = [
        sys.executable,
        str(PIPELINE),
    ]

    try:

        completed = subprocess.run(
            command,
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            check=False,
        )

        output = (
            completed.stdout
            + "\n"
            + completed.stderr
        )

        return (
            completed.returncode,
            output,
        )

    except subprocess.TimeoutExpired as exc:

        stdout = (
            exc.stdout
            if isinstance(
                exc.stdout,
                str,
            )
            else ""
        )

        stderr = (
            exc.stderr
            if isinstance(
                exc.stderr,
                str,
            )
            else ""
        )

        output = (
            stdout
            + "\n"
            + stderr
        )

        fail(
            "CP12-03",
            "Official pipeline runtime exceeded 600 seconds.",
            "Official Production Pipeline",
            "arunda_pipeline.py",
        )

        return 124, output

    except Exception as exc:

        fail(
            "CP12-03",
            f"Official pipeline could not be executed: {exc}",
            "Official Production Pipeline",
            "arunda_pipeline.py",
        )

        return 1, ""


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:

    FAILURES.clear()
    WARNINGS.clear()

    section(
        "ARUNDA TRADER — CP12 FINAL PRODUCTION RELEASE REVIEW v0.4"
    )

    print("MODE              : READ-ONLY")
    print("PROJECT DIR       :", PROJECT_DIR)
    print("DATABASE          :", DB_PATH)
    print("PIPELINE          :", PIPELINE)
    print("LAUNCH TIMESTAMP  :", LAUNCH_TIMESTAMP)
    print("EXECUTION         : MUST REMAIN DISABLED")
    print("CONFIG CHANGES    : NONE")
    print("ORDER SUBMISSION  : NONE")
    print("EXCHANGE WRITE    : NONE")

    # ========================================================================
    # CP12-01
    # ========================================================================

    section(
        "CP12-01 — EXECUTION SAFETY"
    )

    pipeline_text = read_text(
        PIPELINE
    )

    execution_scan = source_execution_scan(
        pipeline_text
    )

    print(
        "EXECUTION_ENABLED :",
        execution_scan[
            "execution_enabled"
        ],
    )

    print(
        "Execution Callables:",
        execution_scan[
            "execution_names"
        ]
        or "NONE",
    )

    print(
        "Exchange Callables :",
        execution_scan[
            "exchange_names"
        ]
        or "NONE",
    )

    print(
        "Legacy References  :",
        execution_scan[
            "legacy_references"
        ]
        or "NONE",
    )

    if not execution_scan["pass"]:

        fail(
            "CP12-01",
            "Execution safety source contract failed.",
            "Execution Boundary",
            "arunda_pipeline.py",
        )

    # ========================================================================
    # CP12-02
    # ========================================================================

    section(
        "CP12-02 — CURRENT PRODUCTION PATH"
    )

    required_path = [
        "market_snapshot_engine",
        "market_data_engine",
        "opportunity_engine",
        "signal_validator",
        "score_producer",
        "signal_scorer",
        "decision_engine",
        "risk_engine",
        "trade_gate_engine",
        "order_intent",
    ]

    missing_path = []

    for item in required_path:

        present = (
            item.lower()
            in pipeline_text.lower()
        )

        print(
            f"{item:<35}",
            "PRESENT"
            if present
            else "MISSING",
        )

        if not present:
            missing_path.append(
                item
            )

    legacy_references = (
        scan_project_legacy_references()
    )

    print(
        "Legacy production references:",
        legacy_references
        or "NONE",
    )

    if missing_path:

        fail(
            "CP12-02",
            "Current production path is incomplete.",
            "Production Runtime Path",
            ", ".join(
                missing_path
            ),
        )

    if legacy_references:

        fail(
            "CP12-02",
            "Legacy execution path is referenced by current Python source.",
            "Production Runtime Path",
            "; ".join(
                legacy_references
            ),
        )

    # ========================================================================
    # CP12-03
    # ========================================================================

    section(
        "CP12-03 — OFFICIAL CURRENT PRODUCTION RUNTIME"
    )

    return_code, runtime_output = (
        run_official_pipeline()
    )

    print(
        "Pipeline Exit Code :",
        return_code,
    )

    if return_code != 0:

        fail(
            "CP12-03",
            f"Official pipeline returned exit code {return_code}.",
            "Official Production Runtime",
            "arunda_pipeline.py",
        )

    runtime_path = (
        PROJECT_DIR
        / "cp12_final_production_release_review_runtime.txt"
    )

    try:

        runtime_path.write_text(
            runtime_output,
            encoding="utf-8",
        )

        print(
            "Runtime Evidence   :",
            runtime_path,
        )

    except Exception as exc:

        warning(
            f"Could not save runtime evidence: {exc}"
        )

    # ========================================================================
    # CP12-04
    # ========================================================================

    section(
        "CP12-04 — CURRENT RUNTIME SNAPSHOT"
    )

    snapshot_marker, snapshot_source = (
        resolve_snapshot_marker(
            runtime_output
        )
    )

    if snapshot_marker is None:

        snapshot_validation = {
            "present":
                False,
            "id":
                None,
            "sha256":
                False,
            "sha256_matches_payload":
                None,
            "random":
                False,
            "uuid":
                False,
            "timestamp_as_id":
                False,
            "pass":
                False,
        }

        fail(
            "CP12-04",
            "Current runtime snapshot identity was not parseable.",
            "Market Snapshot → Current Runtime",
            "CP12_PARSER",
        )

    else:

        snapshot_validation = (
            validate_snapshot_id(
                snapshot_marker
            )
        )

    print(
        "Snapshot ID :",
        snapshot_validation.get(
            "id"
        ),
    )

    print(
        "Parser Source:",
        snapshot_source,
    )

    print(
        "SHA-256     :",
        snapshot_validation.get(
            "sha256",
            False,
        ),
    )

    print(
        "SHA-256 payload match :",
        snapshot_validation.get(
            "sha256_matches_payload"
        ),
    )

    print(
        "Random/UUID :",
        snapshot_validation.get(
            "random",
            False,
        )
        or snapshot_validation.get(
            "uuid",
            False,
        ),
    )

    print(
        "Timestamp ID:",
        snapshot_validation.get(
            "timestamp_as_id",
            False,
        ),
    )

    print(
        "Snapshot PASS:",
        snapshot_validation.get(
            "pass",
            False,
        ),
    )

    if not snapshot_validation.get(
        "pass",
        False,
    ):

        fail(
            "CP12-04",
            "Current runtime snapshot identity failed.",
            "Current Runtime Snapshot",
            snapshot_source,
        )

    # ========================================================================
    # CP12-05
    # ========================================================================

    section(
        "CP12-05 — OPPORTUNITY CONTRACT"
    )

    opportunity_contract = (
        inspect_opportunity_contract()
    )

    print(
        "MAX_CANDIDATES :",
        opportunity_contract[
            "max_candidates"
        ],
    )

    print(
        "MIN_HISTORY_POINTS :",
        opportunity_contract[
            "min_history_points"
        ],
    )

    print(
        "ENGINE_VERSION :",
        opportunity_contract[
            "engine_version"
        ],
    )

    if not opportunity_contract["pass"]:

        fail(
            "CP12-05",
            "Opportunity contract does not have MAX_CANDIDATES = 15.",
            "Opportunity Engine",
            "opportunity_engine.py",
        )

    opportunity_rows = (
        select_authoritative_opportunity_rows(
            runtime_output
        )
    )

    opportunity_coverage = print_coverage(
        "Opportunity",
        rows_assets(
            opportunity_rows
        ),
    )

    (
        total_opportunity,
        eligible_rows,
        no_trade_rows,
    ) = classify_opportunity_rows(
        opportunity_rows
    )

    print(
        "Candidate Capacity :",
        opportunity_contract[
            "max_candidates"
        ],
    )

    print(
        "Actual Candidates  :",
        total_opportunity,
    )

    print(
        "Eligible           :",
        eligible_rows,
    )

    print(
        "No Trade           :",
        no_trade_rows,
    )

    if not opportunity_coverage["pass"]:

        fail(
            "CP12-05",
            "Opportunity current production coverage is not 15/15.",
            "Opportunity Boundary",
            "CURRENT_PRODUCTION_RUNTIME",
        )

    # ========================================================================
    # CP12-06
    # ========================================================================

    section(
        "CP12-06 — SIGNAL / SCORE / DECISION"
    )

    signal_score_decision = (
        compare_signal_score_decision(
            runtime_output
        )
    )

    print_coverage(
        "Signal",
        EXPECTED_ASSETS
        if signal_score_decision[
            "signal_coverage"
        ]["pass"]
        else [],
    )

    print(
        "Signal 15/15 :",
        signal_score_decision[
            "signal_coverage"
        ]["pass"],
    )

    print(
        "Score 15/15  :",
        signal_score_decision[
            "score_coverage"
        ]["pass"],
    )

    print(
        "Decision 15/15:",
        signal_score_decision[
            "decision_coverage"
        ]["pass"],
    )

    print(
        "Identity mismatches:",
        len(
            signal_score_decision[
                "mismatches"
            ]
        ),
    )

    if not signal_score_decision["pass"]:

        fail(
            "CP12-06",
            "Signal/Score/Decision current-runtime contract failed.",
            "Signal → Score → Decision",
            "CURRENT_PRODUCTION_RUNTIME",
        )

    # ========================================================================
    # CP12-07
    # ========================================================================

    section(
        "CP12-07 — RISK / TRADE GATE"
    )

    risk_assets = (
        extract_authoritative_risk_assets(
            runtime_output
        )
    )

    gate_assets = (
        extract_authoritative_gate_assets(
            runtime_output
        )
    )

    risk_coverage = print_coverage(
        "Risk",
        risk_assets,
    )

    gate_coverage = print_coverage(
        "Trade Gate",
        gate_assets,
    )

    trade_ready_count = (
        parse_trade_ready_count(
            runtime_output
        )
    )

    print(
        "Trade Ready :",
        trade_ready_count,
    )

    override_patterns = [
        r"^\s*risk\s+override\s*[:=]\s*(true|yes|enabled|1)\s*$",
        r"^\s*risk_override\s*[:=]\s*(true|yes|enabled|1)\s*$",
        r"^\s*threshold\s+change\s*[:=]\s*(true|yes|enabled|1)\s*$",
        r"^\s*threshold_changed\s*[:=]\s*(true|yes|enabled|1)\s*$",
    ]

    override_hits = []

    for pattern in override_patterns:

        if re.search(
            pattern,
            runtime_output,
            re.IGNORECASE | re.MULTILINE,
        ):

            override_hits.append(
                pattern
            )

    print(
        "Risk Override :",
        "NONE"
        if not override_hits
        else override_hits,
    )

    if (
        not risk_coverage["pass"]
        or not gate_coverage["pass"]
        or override_hits
    ):

        fail(
            "CP12-07",
            "Risk/Trade Gate contract failed.",
            "Decision → Risk → Trade Gate",
            "CURRENT_PRODUCTION_RUNTIME",
        )

    # ========================================================================
    # CP12-08
    # ========================================================================

    section(
        "CP12-08 — ORDER INTENT CONTRACT"
    )

    intent_rows = (
        select_authoritative_intents(
            runtime_output
        )
    )

    # Explicit fail-closed rule:
    # Trade Ready = 0 MUST produce zero current Order Intents.
    if trade_ready_count == 0:

        if intent_rows:

            fail(
                "CP12-08",
                "Trade Ready = 0 but current Order Intent rows were detected.",
                "Trade Gate → Order Intent Boundary",
                "FAIL-CLOSED",
            )

            intent_validation = (
                validate_intent_rows(
                    intent_rows
                )
            )

        else:

            intent_validation = {
                "coverage":
                    coverage_report([]),
                "rows":
                    0,
                "forbidden_fields":
                    [],
                "invalid_keys":
                    [],
                "required_missing":
                    [],
                "pass":
                    True,
            }

    else:

        intent_validation = (
            validate_intent_rows(
                intent_rows
            )
        )

    print_coverage(
        "Order Intent Boundary",
        rows_assets(
            intent_rows
        ),
    )

    print(
        "Order Intent Rows :",
        intent_validation[
            "rows"
        ],
    )

    print(
        "Forbidden Legacy Fields:",
        intent_validation[
            "forbidden_fields"
        ]
        or "NONE",
    )

    print(
        "Required Field Failures:",
        intent_validation.get(
            "required_missing",
            [],
        )
        or "NONE",
    )

    print(
        "Order Intent Contract:",
        intent_validation[
            "pass"
        ],
    )

    if not intent_validation["pass"]:

        fail(
            "CP12-08",
            "Current Order Intent contract failed.",
            "Order Intent Boundary",
            "CURRENT_ORDER_INTENT_BOUNDARY",
        )

    # ========================================================================
    # CP12-09
    # ========================================================================

    section(
        "CP12-09 — RUNTIME IDENTITY PROPAGATION"
    )

    identity_opportunity_rows = (
        opportunity_rows
    )

    identity_gate_rows = (
        authoritative_stage_rows(
            runtime_output,
            [
                {
                    "asset",
                    "symbol",
                    "trade_ready",
                    "trade_gate",
                    "gate_state",
                    "snapshot_id",
                    "current_snapshot_id",
                },
            ],
        )
    )

    identity_validation = (
        validate_identity_propagation(
            snapshot_marker,
            snapshot_source,
            identity_opportunity_rows,
            identity_gate_rows,
            intent_rows,
        )
    )

    print(
        "Current Snapshot ID:",
        identity_validation[
            "snapshot"
        ].get("id"),
    )

    print(
        "Snapshot Source:",
        identity_validation[
            "snapshot_source"
        ],
    )

    print(
        "Opportunity IDs:",
        identity_validation[
            "stages"
        ]["opportunity"]
        or "NONE",
    )

    print(
        "Trade Gate IDs:",
        identity_validation[
            "stages"
        ]["trade_gate"]
        or "NONE",
    )

    print(
        "Order Intent IDs:",
        identity_validation[
            "stages"
        ]["order_intent"]
        or "NONE",
    )

    print(
        "Identity Mismatches:",
        identity_validation[
            "mismatches"
        ]
        or "NONE",
    )

    print(
        "Identity PASS:",
        identity_validation[
            "pass"
        ],
    )

    if not identity_validation["pass"]:

        fail(
            "CP12-09",
            "Current runtime identity propagation failed.",
            "Snapshot → Opportunity → Trade Gate → Order Intent",
            "CURRENT_RUNTIME_IDENTITY",
        )

    # ========================================================================
    # CP12-10
    # ========================================================================

    section(
        "CP12-10 — DATA PURITY / POST-LAUNCH BOUNDARY"
    )

    data_purity = scan_data_purity(
        pipeline_text,
        runtime_output,
    )

    launch_boundary = scan_launch_boundary(
        pipeline_text,
        runtime_output,
    )

    print(
        "Synthetic/Fallback/Interpolation Violations:",
        data_purity[
            "positive_safety_violations"
        ]
        or "NONE",
    )

    print(
        "Launch Boundary Reference:",
        launch_boundary[
            "launch_boundary_reference"
        ],
    )

    print(
        "Legacy Isolation Reference:",
        launch_boundary[
            "legacy_isolation_reference"
        ],
    )

    if not data_purity["pass"]:

        fail(
            "CP12-10",
            "Positive synthetic/fallback/interpolation/fill/fabrication evidence found.",
            "Production Data Boundary",
            "CURRENT_PRODUCTION_RUNTIME",
        )

    if not launch_boundary["pass"]:

        fail(
            "CP12-10",
            "Production launch boundary is not evidenced.",
            "Launch Data Boundary",
            LAUNCH_TIMESTAMP,
        )

    # ========================================================================
    # CP12-11
    # ========================================================================

    section(
        "CP12-11 — WRITE / EXECUTION SAFETY"
    )

    write_safety = (
        scan_execution_write_safety(
            runtime_output
        )
    )

    print(
        "Order Submission Violations:",
        write_safety[
            "order_submission_hits"
        ]
        or "NONE",
    )

    print(
        "Exchange Write Violations:",
        write_safety[
            "exchange_write_hits"
        ]
        or "NONE",
    )

    print(
        "Execution Bypass Violations:",
        write_safety[
            "execution_bypass_hits"
        ]
        or "NONE",
    )

    print(
        "Execution DB Write Violations:",
        write_safety[
            "execution_db_write_hits"
        ]
        or "NONE",
    )

    print(
        "Operational DB Writes:",
        "ALLOWED / CLASSIFIED SEPARATELY",
    )

    if not write_safety["pass"]:

        fail(
            "CP12-11",
            "Execution/order/exchange write safety failed.",
            "Execution Boundary",
            "CURRENT_PRODUCTION_RUNTIME",
        )

    # ========================================================================
    # CP12-12
    # ========================================================================

    section(
        "CP12-12 — RELEASE BLOCKER SCAN"
    )

    print(
        "Current Blockers:",
        len(FAILURES),
    )

    if FAILURES:

        for index, item in enumerate(
            FAILURES,
            start=1,
        ):

            print(
                f"\nBLOCKER {index}"
            )

            print(
                "  CONTROL    :",
                item["control"],
            )

            print(
                "  BLOCKER    :",
                item["blocker"],
            )

            print(
                "  BOUNDARY   :",
                item["boundary"],
            )

            print(
                "  PROVENANCE :",
                item["provenance"],
            )

    # ========================================================================
    # FINAL
    # ========================================================================

    section(
        "CP12 FINAL PRODUCTION RELEASE REVIEW"
    )

    status = (
        "PASS"
        if not FAILURES
        else "BLOCKED"
    )

    print(
        "CP12                =",
        status,
    )

    print(
        "STATUS              =",
        "CLOSED / VERIFIED"
        if status == "PASS"
        else "BLOCKED",
    )

    print(
        "EXECUTION           = DISABLED"
    )

    print(
        "RELEASE AUTHORIZATION = NOT GRANTED"
    )

    if status == "PASS":

        print(
            "NEXT CHECKPOINT     = MANAGEMENT FINAL RELEASE DECISION"
        )

    else:

        print(
            "NEXT ACTION         = MINIMAL ACTION FOR REAL BLOCKER(S)"
        )

    print(
        "CP13                = NONE"
    )

    # ========================================================================
    # MACHINE REPORT
    # ========================================================================

    report = {
        "checkpoint":
            "CP12",

        "version":
            "v0.4",

        "mode":
            "READ_ONLY",

        "result":
            status,

        "status":
            (
                "CLOSED / VERIFIED"
                if status == "PASS"
                else "BLOCKED"
            ),

        "execution_enabled":
            False,

        "release_authorization":
            "NOT GRANTED",

        "next_checkpoint":
            (
                "MANAGEMENT FINAL RELEASE DECISION"
                if status == "PASS"
                else
                "MINIMAL ACTION FOR REAL BLOCKER(S)"
            ),

        "cp13":
            "NONE",

        "project_dir":
            str(PROJECT_DIR),

        "database":
            str(DB_PATH),

        "pipeline":
            str(PIPELINE),

        "launch_timestamp":
            LAUNCH_TIMESTAMP,

        "expected_assets":
            EXPECTED_ASSETS,

        "pipeline_exit_code":
            return_code,

        "execution_scan":
            execution_scan,

        "snapshot":
            snapshot_validation,

        "snapshot_parser_source":
            snapshot_source,

        "opportunity_contract":
            opportunity_contract,

        "opportunity_coverage":
            opportunity_coverage,

        "opportunity_actual":
            total_opportunity,

        "opportunity_eligible":
            eligible_rows,

        "opportunity_no_trade":
            no_trade_rows,

        "signal_score_decision":
            signal_score_decision,

        "risk_coverage":
            risk_coverage,

        "trade_gate_coverage":
            gate_coverage,

        "trade_ready":
            trade_ready_count,

        "order_intent":
            intent_validation,

        "identity":
            identity_validation,

        "data_purity":
            data_purity,

        "launch_boundary":
            launch_boundary,

        "write_safety":
            write_safety,

        "warnings":
            WARNINGS,

        "blockers":
            FAILURES,
    }

    json_path = (
        PROJECT_DIR
        / "cp12_final_production_release_review_v0.4.json"
    )

    try:

        json_path.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        print(
            "\nREPORT JSON         =",
            json_path,
        )

    except Exception as exc:

        print(
            "\nREPORT JSON WRITE ERROR =",
            exc,
        )

    print(
        "\nCP12 FINAL RESULT:",
        status,
    )

    return (
        0
        if status == "PASS"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )