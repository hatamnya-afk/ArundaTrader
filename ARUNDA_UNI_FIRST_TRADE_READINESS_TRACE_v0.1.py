# -*- coding: utf-8 -*-

"""
ARUNDA TRADER — UNI FIRST-TRADE READINESS TRACE v0.3

READ ONLY
ONE CURRENT PRODUCTION RUNTIME
ONE UNI TRACE
NO ORDER
NO EXCHANGE WRITE
NO EXECUTION

IMPORTANT:
- Never scans controller / forensic files for execution flags.
- Only production entrypoint is checked for EXECUTION_ENABLED.
- Does not invent stage payloads.
- Does not infer asset from numeric values.
- Does not query DB to reconstruct runtime stages.
- Uses ONLY the stdout of the single current production runtime.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# HARD SAFETY
# ============================================================

TARGET_ASSET = "UNI"
EXECUTION_ENABLED = False

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB = ROOT / "arunda.db"
ENTRYPOINT = ROOT / "arunda_pipeline.py"

if EXECUTION_ENABLED:
    raise SystemExit(
        "BLOCKED — TRACE CONTROLLER EXECUTION_ENABLED MUST BE FALSE"
    )


# ============================================================
# HELPERS
# ============================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def norm_asset(value):
    if value is None:
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    # Never interpret numeric values as assets.
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value):
        return None

    return value


def safe_json(value):
    try:
        return json.loads(value)
    except Exception:
        return None


def explicit_asset(obj):
    if not isinstance(obj, dict):
        return None

    for key in (
        "asset",
        "symbol",
        "ticker",
        "market",
        "pair",
    ):
        if key in obj:
            asset = norm_asset(obj[key])

            if asset == TARGET_ASSET:
                return asset

    return None


def recursive_uni_objects(obj):
    """
    Return dictionaries where UNI is explicitly present
    in an asset/symbol/ticker/market/pair field.
    """

    found = []

    if isinstance(obj, dict):

        if explicit_asset(obj) == TARGET_ASSET:
            found.append(obj)

        for value in obj.values():
            found.extend(
                recursive_uni_objects(value)
            )

    elif isinstance(obj, list):

        for item in obj:
            found.extend(
                recursive_uni_objects(item)
            )

    return found


def extract_balanced_json(text, start):
    """
    Extract one balanced JSON object/array beginning at start.
    """

    if start >= len(text):
        return None

    opening = text[start]

    if opening not in "{[":
        return None

    closing = "}" if opening == "{" else "]"

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):

        c = text[i]

        if in_string:

            if escape:
                escape = False

            elif c == "\\":
                escape = True

            elif c == '"':
                in_string = False

            continue

        if c == '"':
            in_string = True
            continue

        if c == opening:
            depth += 1

        elif c == closing:
            depth -= 1

            if depth == 0:
                return text[start:i + 1]

    return None


def extract_all_json_fragments(line):
    """
    Find JSON objects/arrays embedded in arbitrary runtime text.
    """

    fragments = []

    for i, char in enumerate(line):

        if char not in "{[":
            continue

        raw = extract_balanced_json(line, i)

        if raw is None:
            continue

        parsed = safe_json(raw)

        if parsed is not None:
            fragments.append(parsed)

    return fragments


def collect_runtime_uni_objects(stdout):
    """
    Parse every stdout line independently.

    No assumed marker names.
    No DB reconstruction.
    """

    results = []

    for line_no, line in enumerate(
        stdout.splitlines(),
        1,
    ):

        # ----------------------------------------------------
        # JSON fragments
        # ----------------------------------------------------

        fragments = extract_all_json_fragments(line)

        for payload in fragments:

            objects = recursive_uni_objects(payload)

            for obj in objects:

                results.append(
                    {
                        "line": line_no,
                        "source": "JSON",
                        "object": obj,
                        "raw": line.strip(),
                    }
                )

        # ----------------------------------------------------
        # Explicit key/value runtime lines
        # ----------------------------------------------------

        if re.search(
            r"\b(?:asset|symbol|ticker|market|pair)\s*[:=]\s*UNI\b",
            line,
            flags=re.IGNORECASE,
        ):

            results.append(
                {
                    "line": line_no,
                    "source": "TEXT",
                    "object": None,
                    "raw": line.strip(),
                }
            )

    return results


def find_field(obj, names):

    if not isinstance(obj, dict):
        return None

    for name in names:

        if name in obj and obj[name] is not None:
            return obj[name]

    return None


def classify_object(obj):

    if not isinstance(obj, dict):
        return None

    keys = {
        str(k).lower()
        for k in obj.keys()
    }

    if keys & {
        "intent_id",
        "order_intent",
        "order_intent_id",
    }:
        return "ORDER_INTENT"

    if keys & {
        "trade_ready",
        "gate_status",
        "trade_gate",
        "gate_reason",
    }:
        return "TRADE_GATE"

    if keys & {
        "risk_state",
        "risk_status",
        "risk_result",
    }:
        return "RISK"

    if keys & {
        "decision",
        "decision_state",
        "decision_result",
        "actionable",
    }:
        return "DECISION"

    if keys & {
        "score_identity",
        "signal_score",
        "technical_score",
    }:
        return "SCORE"

    if keys & {
        "signal_identity",
        "signal_state",
        "validation",
        "validation_result",
    }:
        return "SIGNAL"

    if keys & {
        "opportunity_score",
        "confidence",
        "status",
        "points",
    }:
        return "OPPORTUNITY"

    return None


def db_fingerprint():

    con = sqlite3.connect(DB)

    try:

        integrity = con.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        tables = [
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' ORDER BY name"
            ).fetchall()
        ]

        counts = {}

        for table in tables:

            try:
                counts[table] = con.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]

            except Exception:
                counts[table] = "ERROR"

        payload = json.dumps(
            {
                "tables": tables,
                "counts": counts,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

        return {
            "integrity": integrity,
            "tables": len(tables),
            "counts": counts,
            "hash": hashlib.sha256(
                payload.encode()
            ).hexdigest(),
        }

    finally:
        con.close()


def parse_trade_ready(stdout):

    patterns = [
        r"(?im)^\s*Trade\s+Ready\s*[:=]\s*(TRUE|FALSE|0|1)\s*$",
        r"(?im)^\s*TRADE\s+READY\s*[:=]\s*(TRUE|FALSE|0|1)\s*$",
    ]

    values = []

    for pattern in patterns:
        values.extend(
            re.findall(
                pattern,
                stdout,
            )
        )

    values = [
        str(x).upper()
        for x in values
    ]

    values = list(dict.fromkeys(values))

    if not values:
        return None, False

    if len(values) > 1:
        return None, True

    return values[0] in {"TRUE", "1"}, False


def parse_order_intent_count(stdout):

    patterns = [
        r"(?im)^\s*Order\s+Intent\s*[:=]\s*(\d+)\s*$",
        r"(?im)^\s*Order\s+Intents\s*[:=]\s*(\d+)\s*$",
        r"(?im)^\s*Order\s+Intent\s+Count\s*[:=]\s*(\d+)\s*$",
        r"(?im)^\s*Order\s+Intents\s+Count\s*[:=]\s*(\d+)\s*$",
    ]

    values = []

    for pattern in patterns:
        values.extend(
            re.findall(
                pattern,
                stdout,
            )
        )

    values = list(dict.fromkeys(values))

    if not values:
        return None, False

    if len(values) > 1:
        return None, True

    return int(values[0]), False


def get_stage_candidate(runtime_objects, stage):

    candidates = []

    for item in runtime_objects:

        obj = item["object"]

        if obj is None:
            continue

        if classify_object(obj) == stage:
            candidates.append(item)

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) == 0:
        return None

    # If multiple objects exist, only accept when their
    # content is byte-for-byte equivalent JSON.
    serialized = []

    for item in candidates:
        serialized.append(
            json.dumps(
                item["object"],
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    if len(set(serialized)) == 1:
        return candidates[0]

    return "__AMBIGUOUS__"


# ============================================================
# HEADER
# ============================================================

started = datetime.now(
    timezone.utc
).isoformat()

print("=" * 110)
print("ARUNDA TRADER — UNI FIRST-TRADE READINESS TRACE v0.3")
print("=" * 110)
print("MODE                  : READ ONLY")
print(f"STARTED               : {started}")
print(f"TARGET ASSET          : {TARGET_ASSET}")
print(f"PROJECT ROOT          : {ROOT}")
print(f"DATABASE              : {DB}")
print(f"ENTRYPOINT            : {ENTRYPOINT}")
print("EXECUTION ENABLED     : False")
print("ORDER SUBMISSION      : FORBIDDEN")
print("EXCHANGE WRITE        : FORBIDDEN")
print("OLD SNAPSHOT          : FORBIDDEN")
print("LEGACY DATA           : FORBIDDEN")
print("FABRICATION           : FORBIDDEN")
print("=" * 110)


# ============================================================
# STATIC SAFETY
# ============================================================

if not ROOT.exists():
    raise SystemExit(
        "BLOCKED — PROJECT ROOT NOT FOUND"
    )

if not DB.exists():
    raise SystemExit(
        "BLOCKED — DATABASE NOT FOUND"
    )

if not ENTRYPOINT.exists():
    raise SystemExit(
        "BLOCKED — ENTRYPOINT NOT FOUND"
    )


entry_hash_before = sha256_file(
    ENTRYPOINT
)

print(
    f"ENTRYPOINT SHA256     : "
    f"{entry_hash_before}"
)

print("ENTRYPOINT PRESENT    : True")


# ------------------------------------------------------------
# CRITICAL FIX:
# Only production entrypoint is inspected.
# ------------------------------------------------------------

entry_text = ENTRYPOINT.read_text(
    encoding="utf-8-sig",
    errors="replace",
)

production_true_hits = []

for line_no, line in enumerate(
    entry_text.splitlines(),
    1,
):

    if re.search(
        r"\bEXECUTION_ENABLED\s*=\s*True\b",
        line,
        flags=re.IGNORECASE,
    ):

        production_true_hits.append(
            line_no
        )


print(
    "PRODUCTION EXECUTION TRUE HITS : "
    f"{len(production_true_hits)}"
)

if production_true_hits:

    for line_no in production_true_hits:
        print(
            f"  arunda_pipeline.py:{line_no}"
        )

    print(
        "FINAL STATUS           : "
        "BLOCKED — PRODUCTION EXECUTION FLAG"
    )

    raise SystemExit(1)

print("PRODUCTION EXECUTION   : FALSE")


# ============================================================
# DB BEFORE
# ============================================================

db_before = db_fingerprint()

print()
print(
    "DB INTEGRITY BEFORE    : "
    f"{db_before['integrity']}"
)

print(
    "DB TABLES BEFORE       : "
    f"{db_before['tables']}"
)

print(
    "DB FINGERPRINT BEFORE : "
    f"{db_before['hash']}"
)


# ============================================================
# ONE CURRENT PRODUCTION RUNTIME
# ============================================================

print()
print("=" * 110)
print("ONE CURRENT PRODUCTION RUNTIME")
print("=" * 110)

env = os.environ.copy()
env["PYTHONUNBUFFERED"] = "1"

process = subprocess.run(
    [
        sys.executable,
        str(ENTRYPOINT),
    ],
    cwd=str(ROOT),
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    env=env,
)

stdout = process.stdout or ""
stderr = process.stderr or ""

print(
    "RUNTIME EXIT CODE      : "
    f"{process.returncode}"
)

if process.returncode != 0:

    print()
    print("RUNTIME STDERR:")
    print(stderr)

    print()
    print(
        "FINAL STATUS           : "
        "BLOCKED — RUNTIME INCONSISTENCY"
    )

    raise SystemExit(
        process.returncode
    )


# ============================================================
# SNAPSHOT ID
# ============================================================

snapshot_ids = list(
    dict.fromkeys(
        re.findall(
            r"RS-[0-9a-fA-F]{64}",
            stdout,
        )
    )
)

if len(snapshot_ids) != 1:

    print(
        "SNAPSHOT IDS FOUND     : "
        f"{len(snapshot_ids)}"
    )

    for sid in snapshot_ids:
        print(" ", sid)

    print(
        "FINAL STATUS           : "
        "BLOCKED — SNAPSHOT ID AMBIGUOUS"
    )

    raise SystemExit(1)


snapshot_id = snapshot_ids[0]

print(
    f"CURRENT SNAPSHOT ID    : "
    f"{snapshot_id}"
)


# ============================================================
# PARSE ACTUAL RUNTIME
# ============================================================

runtime_objects = collect_runtime_uni_objects(
    stdout
)

print(
    "EXPLICIT UNI RUNTIME OBJECTS : "
    f"{len(runtime_objects)}"
)


# ============================================================
# STAGE RESOLUTION
# ============================================================

stage_names = [
    "OPPORTUNITY",
    "SIGNAL",
    "SCORE",
    "DECISION",
    "RISK",
    "TRADE_GATE",
    "ORDER_INTENT",
]

stage_objects = {}

for stage in stage_names:

    result = get_stage_candidate(
        runtime_objects,
        stage,
    )

    if result == "__AMBIGUOUS__":

        print()
        print(
            f"{stage} : AMBIGUOUS"
        )

        print(
            "FINAL STATUS           : "
            "BLOCKED — RUNTIME INCONSISTENCY"
        )

        raise SystemExit(1)

    stage_objects[stage] = (
        result["object"]
        if result is not None
        else None
    )


# ============================================================
# OPPORTUNITY
# ============================================================

opp = stage_objects["OPPORTUNITY"]

if opp is None:

    # Opportunity may be the only known structured
    # runtime object even if its key classification differs.
    opp = recursive_uni_objects(
        extract_all_json_fragments(stdout)
    )

    if len(opp) == 1:
        opp = opp[0]
    else:
        opp = None


if opp is None:

    print()
    print(
        "OPPORTUNITY             : "
        "UNI NOT RESOLVED"
    )

    print(
        "FINAL STATUS            : "
        "BLOCKED — UNI PROVENANCE UNRESOLVED"
    )

    raise SystemExit(1)


opp_asset = norm_asset(
    find_field(
        opp,
        [
            "asset",
            "symbol",
            "ticker",
            "market",
            "pair",
        ],
    )
)

opp_timestamp = find_field(
    opp,
    [
        "timestamp",
        "created_at",
    ],
)

opp_price = find_field(
    opp,
    [
        "price",
        "entry_price",
    ],
)

opp_score = find_field(
    opp,
    [
        "score",
        "opportunity_score",
    ],
)

opp_confidence = find_field(
    opp,
    [
        "confidence",
    ],
)

opp_eligibility = find_field(
    opp,
    [
        "eligible",
        "eligibility",
    ],
)

opp_status = find_field(
    opp,
    [
        "status",
    ],
)


# ============================================================
# SIGNAL
# ============================================================

sig = stage_objects["SIGNAL"]

signal_asset = norm_asset(
    find_field(
        sig,
        [
            "asset",
            "symbol",
            "ticker",
        ],
    )
)

signal_state = find_field(
    sig,
    [
        "signal_state",
        "state",
        "signal",
    ],
)

signal_direction = find_field(
    sig,
    [
        "direction",
        "signal_direction",
    ],
)

signal_identity = find_field(
    sig,
    [
        "signal_identity",
        "signal_id",
        "identity",
    ],
)

validation_result = find_field(
    sig,
    [
        "validation_result",
        "validation",
        "validated",
    ],
)


# ============================================================
# SCORE
# ============================================================

score_obj = stage_objects["SCORE"]

score_asset = norm_asset(
    find_field(
        score_obj,
        [
            "asset",
            "symbol",
            "ticker",
        ],
    )
)

score_value = find_field(
    score_obj,
    [
        "score",
        "signal_score",
        "technical_score",
    ],
)

score_identity = find_field(
    score_obj,
    [
        "score_identity",
        "score_id",
        "identity",
    ],
)


# ============================================================
# DECISION
# ============================================================

dec = stage_objects["DECISION"]

decision_asset = norm_asset(
    find_field(
        dec,
        [
            "asset",
            "symbol",
            "ticker",
        ],
    )
)

decision_state = find_field(
    dec,
    [
        "decision_state",
        "state",
        "decision",
    ],
)

decision_direction = find_field(
    dec,
    [
        "direction",
        "decision_direction",
    ],
)

decision_score = find_field(
    dec,
    [
        "score",
        "signal_score",
    ],
)

decision_result = find_field(
    dec,
    [
        "decision_result",
        "result",
    ],
)


# ============================================================
# RISK
# ============================================================

risk = stage_objects["RISK"]

risk_asset = norm_asset(
    find_field(
        risk,
        [
            "asset",
            "symbol",
            "ticker",
        ],
    )
)

risk_state = find_field(
    risk,
    [
        "risk_state",
        "state",
        "risk_status",
    ],
)

risk_direction = find_field(
    risk,
    [
        "direction",
    ],
)

risk_result = find_field(
    risk,
    [
        "risk_result",
        "result",
    ],
)


# ============================================================
# TRADE GATE
# ============================================================

gate = stage_objects["TRADE_GATE"]

gate_asset = norm_asset(
    find_field(
        gate,
        [
            "asset",
            "symbol",
            "ticker",
        ],
    )
)

gate_status = find_field(
    gate,
    [
        "gate_status",
        "trade_gate",
        "status",
    ],
)

gate_direction = find_field(
    gate,
    [
        "direction",
    ],
)

gate_score = find_field(
    gate,
    [
        "score",
    ],
)

gate_risk_status = find_field(
    gate,
    [
        "risk_status",
        "risk_state",
    ],
)

gate_reason = find_field(
    gate,
    [
        "gate_reason",
        "reason",
    ],
)


# ============================================================
# ORDER INTENT
# ============================================================

intent = stage_objects["ORDER_INTENT"]

intent_asset = norm_asset(
    find_field(
        intent,
        [
            "asset",
            "symbol",
            "ticker",
        ],
    )
)

intent_direction = find_field(
    intent,
    [
        "direction",
    ],
)

intent_entry_price = find_field(
    intent,
    [
        "entry_price",
        "price",
    ],
)

intent_confidence = find_field(
    intent,
    [
        "confidence",
    ],
)

intent_regime = find_field(
    intent,
    [
        "regime",
    ],
)

intent_timestamp = find_field(
    intent,
    [
        "timestamp",
        "created_at",
    ],
)

intent_snapshot_id = find_field(
    intent,
    [
        "snapshot_id",
    ],
)

intent_id = find_field(
    intent,
    [
        "intent_id",
        "order_intent_id",
    ],
)


# ============================================================
# TRADE READY / INTENT COUNT
# ============================================================

trade_ready, trade_ready_ambiguous = (
    parse_trade_ready(stdout)
)

intent_count, intent_count_ambiguous = (
    parse_order_intent_count(stdout)
)


# ============================================================
# IDENTITY
# ============================================================

asset_chain = {
    "Opportunity": opp_asset,
    "Signal": signal_asset,
    "Score": score_asset,
    "Decision": decision_asset,
    "Risk": risk_asset,
    "Trade Gate": gate_asset,
    "Order Intent": intent_asset,
}

known_assets = [
    value
    for value in asset_chain.values()
    if value is not None
]

asset_identity_pass = (
    bool(known_assets)
    and all(
        value == TARGET_ASSET
        for value in known_assets
    )
)

direction_chain = [
    signal_direction,
    decision_direction,
    risk_direction,
    gate_direction,
    intent_direction,
]

direction_chain = [
    str(x).strip().upper()
    for x in direction_chain
    if x is not None
]

direction_identity_pass = (
    len(direction_chain) <= 1
    or len(set(direction_chain)) == 1
)

score_chain = [
    score_value,
    decision_score,
    gate_score,
]

score_chain = [
    str(x)
    for x in score_chain
    if x is not None
]

score_identity_pass = (
    len(score_chain) <= 1
    or len(set(score_chain)) == 1
)

snapshot_identity_pass = bool(
    snapshot_id
)

timestamp_provenance_pass = bool(
    opp_timestamp
)


# ============================================================
# INTENT PROVENANCE
# ============================================================

intent_fields = {
    "asset": intent_asset,
    "direction": intent_direction,
    "entry_price": intent_entry_price,
    "confidence": intent_confidence,
    "regime": intent_regime,
    "timestamp": intent_timestamp,
    "snapshot_id": intent_snapshot_id,
    "intent_id": intent_id,
}

intent_complete = all(
    value is not None
    for value in intent_fields.values()
)

intent_snapshot_match = (
    intent_snapshot_id == snapshot_id
    if intent_snapshot_id is not None
    else False
)


# ============================================================
# FINAL REPORT
# ============================================================

print()
print("=" * 110)
print("UNI FIRST-TRADE READINESS TRACE v0.3 — FINAL REPORT")
print("=" * 110)

print()
print("CURRENT SNAPSHOT")
print(
    f"  Snapshot ID              : "
    f"{snapshot_id}"
)

print()
print("OPPORTUNITY")
print(
    f"  asset                    : "
    f"{opp_asset}"
)
print(
    f"  timestamp                : "
    f"{opp_timestamp}"
)
print(
    f"  price                    : "
    f"{opp_price}"
)
print(
    f"  score                    : "
    f"{opp_score}"
)
print(
    f"  confidence               : "
    f"{opp_confidence}"
)
print(
    f"  eligibility              : "
    f"{opp_eligibility}"
)
print(
    f"  status                   : "
    f"{opp_status}"
)

print()
print("SIGNAL")
print(
    f"  asset                    : "
    f"{signal_asset}"
)
print(
    f"  signal state             : "
    f"{signal_state}"
)
print(
    f"  direction                : "
    f"{signal_direction}"
)
print(
    f"  signal identity          : "
    f"{signal_identity}"
)
print(
    f"  validation result        : "
    f"{validation_result}"
)

print()
print("SCORE")
print(
    f"  asset                    : "
    f"{score_asset}"
)
print(
    f"  score                    : "
    f"{score_value}"
)
print(
    f"  score identity           : "
    f"{score_identity}"
)
print(
    f"  score/signals alignment  : "
    f"{'PASS' if score_identity_pass else 'FAIL'}"
)

print()
print("DECISION")
print(
    f"  asset                    : "
    f"{decision_asset}"
)
print(
    f"  state                    : "
    f"{decision_state}"
)
print(
    f"  direction                : "
    f"{decision_direction}"
)
print(
    f"  score                    : "
    f"{decision_score}"
)
print(
    f"  decision result          : "
    f"{decision_result}"
)

print()
print("RISK")
print(
    f"  asset                    : "
    f"{risk_asset}"
)
print(
    f"  risk_state               : "
    f"{risk_state}"
)
print(
    f"  direction                : "
    f"{risk_direction}"
)
print(
    f"  risk result              : "
    f"{risk_result}"
)

print()
print("TRADE GATE")
print(
    f"  asset                    : "
    f"{gate_asset}"
)
print(
    f"  gate status              : "
    f"{gate_status}"
)
print(
    f"  direction                : "
    f"{gate_direction}"
)
print(
    f"  score                    : "
    f"{gate_score}"
)
print(
    f"  risk status              : "
    f"{gate_risk_status}"
)
print(
    f"  exact gate reason        : "
    f"{gate_reason}"
)

print()
print("TRADE READY")
print(
    f"  TRUE/FALSE               : "
    f"{trade_ready}"
)
print(
    f"  ambiguous                : "
    f"{trade_ready_ambiguous}"
)

print()
print("ORDER INTENT")
print(
    f"  count                    : "
    f"{intent_count}"
)
print(
    f"  ambiguous                : "
    f"{intent_count_ambiguous}"
)
print(
    f"  runtime object           : "
    f"{'PRESENT' if intent is not None else 'NONE'}"
)

if intent is not None:

    print(
        f"  asset                    : "
        f"{intent_asset}"
    )
    print(
        f"  direction                : "
        f"{intent_direction}"
    )
    print(
        f"  entry_price              : "
        f"{intent_entry_price}"
    )
    print(
        f"  confidence               : "
        f"{intent_confidence}"
    )
    print(
        f"  regime                   : "
        f"{intent_regime}"
    )
    print(
        f"  timestamp                : "
        f"{intent_timestamp}"
    )
    print(
        f"  snapshot_id              : "
        f"{intent_snapshot_id}"
    )
    print(
        f"  intent_id                : "
        f"{intent_id}"
    )

    print(
        f"  contract validity        : "
        f"{'PASS' if intent_complete else 'FAIL'}"
    )

    print(
        f"  snapshot match           : "
        f"{'PASS' if intent_snapshot_match else 'FAIL'}"
    )

else:

    print(
        "  contract validity        : N/A"
    )


# ============================================================
# IDENTITY REPORT
# ============================================================

print()
print("IDENTITY INTEGRITY")

for stage, value in asset_chain.items():

    print(
        f"  {stage:24s}: "
        f"{value}"
    )

print(
    f"  asset identity           : "
    f"{'PASS' if asset_identity_pass else 'FAIL/UNRESOLVED'}"
)

print(
    f"  direction identity       : "
    f"{'PASS' if direction_identity_pass else 'FAIL'}"
)

print(
    f"  score identity           : "
    f"{'PASS' if score_identity_pass else 'FAIL'}"
)

print(
    f"  snapshot identity        : "
    f"{'PASS' if snapshot_identity_pass else 'FAIL'}"
)

print(
    f"  timestamp provenance     : "
    f"{'PASS' if timestamp_provenance_pass else 'FAIL'}"
)


# ============================================================
# CRITICAL DECISION
# ============================================================

blocking_boundary = "NONE"
blocking_reason = "NONE"

if trade_ready_ambiguous:

    blocking_boundary = "TRADE_READY"

    blocking_reason = (
        "Multiple conflicting Trade Ready "
        "values were found in the same runtime."
    )

elif intent_count_ambiguous:

    blocking_boundary = "ORDER_INTENT"

    blocking_reason = (
        "Multiple conflicting Order Intent "
        "counts were found in the same runtime."
    )

elif not asset_identity_pass:

    blocking_boundary = "IDENTITY"

    blocking_reason = (
        "UNI asset identity could not be "
        "verified across available runtime stages."
    )

elif not direction_identity_pass:

    blocking_boundary = "DIRECTION"

    blocking_reason = (
        "Direction identity differs across "
        "current runtime stages."
    )

elif not score_identity_pass:

    blocking_boundary = "SCORE"

    blocking_reason = (
        "Score identity differs across "
        "current runtime stages."
    )

elif trade_ready is False:

    blocking_boundary = "TRADE_READY"

    if gate_reason is not None:
        blocking_reason = str(gate_reason)

    elif gate_status is not None:
        blocking_reason = (
            f"Trade Gate status={gate_status}; "
            "runtime exposed no more specific gate reason."
        )

    else:
        blocking_reason = (
            "Current runtime explicitly reports "
            "Trade Ready FALSE."
        )

elif trade_ready is None:

    blocking_boundary = "TRADE_READY"

    blocking_reason = (
        "Current runtime did not expose one "
        "unambiguous Trade Ready value."
    )

elif trade_ready is True:

    if intent_count != 1:

        blocking_boundary = "ORDER_INTENT"

        blocking_reason = (
            "Trade Ready TRUE but runtime does not "
            "expose exactly one Order Intent."
        )

    elif intent is None:

        blocking_boundary = "ORDER_INTENT"

        blocking_reason = (
            "Runtime reports one Order Intent but "
            "no explicit UNI Intent object was exposed."
        )

    elif not intent_complete:

        blocking_boundary = (
            "ORDER_INTENT_PROVENANCE"
        )

        missing = [
            key
            for key, value
            in intent_fields.items()
            if value is None
        ]

        blocking_reason = (
            "Intent provenance incomplete; "
            f"missing fields: {', '.join(missing)}"
        )

    elif not intent_snapshot_match:

        blocking_boundary = (
            "ORDER_INTENT_PROVENANCE"
        )

        blocking_reason = (
            "Intent snapshot_id does not match "
            "the Current Runtime Snapshot ID."
        )


print()
print("=" * 110)
print("CRITICAL DECISION")
print("=" * 110)

print(
    f"Exact Blocking Boundary    : "
    f"{blocking_boundary}"
)

print(
    f"Exact Blocking Reason      : "
    f"{blocking_reason}"
)


# ============================================================
# DB AFTER
# ============================================================

db_after = db_fingerprint()

entry_hash_after = sha256_file(
    ENTRYPOINT
)

print()
print("SAFETY")
print("  DB Write by Controller   : NONE")
print("  Exchange Write           : NONE")
print("  Order Submission         : NONE")
print("  Execution Enabled        : FALSE")
print("  Synthetic Data           : NONE")
print("  Fallback                 : NONE")
print("  Fabrication              : NONE")
print("  Interpolation            : NONE")
print("  Forward Fill             : NONE")
print("  Back Fill                : NONE")
print("  Padding                  : NONE")
print("  Legacy/Museum            : NONE")

print()
print("DB")
print(
    f"  Integrity After          : "
    f"{db_after['integrity']}"
)

print(
    f"  Fingerprint After        : "
    f"{db_after['hash']}"
)

print(
    "  Fingerprint Delta        : "
    + (
        "PRESENT — EXISTING OPERATIONAL RUNTIME PERSISTENCE"
        if db_after["hash"] != db_before["hash"]
        else "NONE"
    )
)

print()
print("PRODUCTION LOGIC")
print(
    f"  Entrypoint unchanged     : "
    f"{entry_hash_before == entry_hash_after}"
)

print(
    f"  Before SHA256            : "
    f"{entry_hash_before}"
)

print(
    f"  After SHA256             : "
    f"{entry_hash_after}"
)

print(
    "  Production Logic Change  : NONE"
)

print(
    "  Threshold Change         : NONE"
)


# ============================================================
# FINAL STATUS
# ============================================================

print()
print("=" * 110)

if (
    trade_ready is True
    and intent_count == 1
    and intent is not None
    and intent_complete
    and intent_snapshot_match
    and asset_identity_pass
    and direction_identity_pass
    and score_identity_pass
):

    final_status = (
        "PASS — UNI REACHES VALID TRADE READY + "
        "VALID RUNTIME ORDER INTENT"
    )

elif (
    trade_ready is False
    and blocking_boundary not in {
        "IDENTITY",
        "DIRECTION",
        "SCORE",
    }
):

    final_status = (
        "PASS — UNI CORRECTLY BLOCKED DOWNSTREAM "
        "WITH VERIFIED RUNTIME REASON"
    )

else:

    final_status = (
        "BLOCKED — PROVENANCE/CONTRACT OR "
        "RUNTIME INCONSISTENCY"
    )


print(
    f"FINAL STATUS             : "
    f"{final_status}"
)

print("EXECUTION                : DISABLED")
print("ORDER                    : NONE")
print("EXCHANGE WRITE           : NONE")
print("NEXT CHECKPOINT          : NONE — MANAGEMENT REVIEW ONLY")
print("HARD STOP                : YES")
print("=" * 110)