# ARUNDA_UNI_FIRST_TRADE_READINESS_TRACE_v0.4.py
# READ ONLY — FORENSIC RUNTIME OBJECT EXTRACTION
# NO PRODUCTION CHANGE / NO ORDER / NO EXCHANGE WRITE

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB = ROOT / "arunda.db"
ENTRYPOINT = ROOT / "arunda_pipeline.py"

TARGET = "UNI"
EXECUTION_ENABLED = False


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def db_fingerprint(path: Path) -> str:
    h = hashlib.sha256()

    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            """
            SELECT name, type, sql
            FROM sqlite_master
            WHERE sql IS NOT NULL
            ORDER BY type, name
            """
        ).fetchall()

        for row in rows:
            h.update(repr(row).encode("utf-8"))

        tables = [
            r[0]
            for r in conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                ORDER BY name
                """
            ).fetchall()
        ]

        for table in tables:
            try:
                cols = conn.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()
                h.update(repr((table, cols)).encode("utf-8"))

                count = conn.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]

                h.update(repr((table, count)).encode("utf-8"))
            except Exception:
                pass

    return h.hexdigest()


def db_integrity(path: Path):
    with sqlite3.connect(path) as conn:
        return conn.execute("PRAGMA integrity_check").fetchone()[0]


def extract_json_fragments(text: str):
    fragments = []
    decoder = json.JSONDecoder()

    for i, ch in enumerate(text):
        if ch not in "{[":
            continue

        try:
            obj, end = decoder.raw_decode(text[i:])
            fragments.append(obj)
        except Exception:
            continue

    return fragments


def walk_objects(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk_objects(value)

    elif isinstance(obj, list):
        for value in obj:
            yield from walk_objects(value)


def norm(value):
    if value is None:
        return None
    return str(value).strip().upper()


def asset_of(obj):
    for key in (
        "asset",
        "symbol",
        "ticker",
        "market",
        "pair",
        "instrument",
        "coin",
    ):
        if key in obj and obj[key] is not None:
            if norm(obj[key]) == TARGET:
                return TARGET

    return None


def classify(obj):
    keys = {str(k).lower() for k in obj.keys()}

    # Most specific first.

    if (
        "intent_id" in keys
        or "order_intent" in keys
        or "order_intent_id" in keys
    ):
        return "ORDER_INTENT"

    if (
        "trade_ready" in keys
        or "gate_status" in keys
        or "trade_gate" in keys
        or "gate_reason" in keys
    ):
        return "TRADE_GATE"

    if (
        "risk_state" in keys
        or "risk_result" in keys
        or "risk_status" in keys
        or "risk_score" in keys
    ):
        return "RISK"

    if (
        "decision_result" in keys
        or "decision_state" in keys
        or "decision" in keys
        or "decision_status" in keys
    ):
        return "DECISION"

    if (
        "score_identity" in keys
        or "signal_score" in keys
        or "score" in keys
    ):
        return "SCORE"

    if (
        "signal_identity" in keys
        or "signal_state" in keys
        or "signal" in keys
        or "direction" in keys
    ):
        return "SIGNAL"

    if (
        "opportunity_score" in keys
        or "eligibility" in keys
        or "opportunity" in keys
        or "points" in keys
        or "confidence" in keys
    ):
        return "OPPORTUNITY"

    return "UNKNOWN"


def relevant_fields(obj):
    wanted = {
        "asset",
        "symbol",
        "ticker",
        "market",
        "pair",
        "instrument",
        "timestamp",
        "time",
        "price",
        "entry_price",
        "score",
        "signal_score",
        "confidence",
        "direction",
        "state",
        "status",
        "signal_state",
        "decision",
        "decision_state",
        "decision_result",
        "risk_state",
        "risk_status",
        "risk_result",
        "gate_status",
        "trade_gate",
        "gate_reason",
        "trade_ready",
        "order_intent",
        "intent_id",
        "snapshot_id",
        "signal_identity",
        "score_identity",
        "validation_result",
        "regime",
    }

    return {
        k: v
        for k, v in obj.items()
        if str(k).lower() in wanted
    }


def extract_snapshot_ids(text):
    return re.findall(r"\bRS-[0-9a-fA-F]{64}\b", text)


def exact_runtime_lines(text):
    patterns = [
        r"^\s*Trade\s+Ready.*$",
        r"^\s*Order\s+Intent.*$",
        r"^\s*Validated\s+Order\s+Intent.*$",
        r"^\s*No\s+Trade.*$",
        r"^\s*Actionable.*$",
        r"^\s*Hold.*$",
        r"^\s*Reject.*$",
    ]

    out = []

    for line in text.splitlines():
        for pattern in patterns:
            if re.match(pattern, line, re.I):
                out.append(line.rstrip())
                break

    return out


print("=" * 110)
print("ARUNDA TRADER — UNI FIRST-TRADE READINESS FORENSIC TRACE v0.4")
print("=" * 110)

print("MODE                  : READ ONLY")
print("STARTED               :", datetime.now(timezone.utc).isoformat())
print("TARGET ASSET          :", TARGET)
print("PROJECT ROOT          :", ROOT)
print("DATABASE              :", DB)
print("ENTRYPOINT            :", ENTRYPOINT)
print("EXECUTION ENABLED     :", EXECUTION_ENABLED)
print("ORDER SUBMISSION      : FORBIDDEN")
print("EXCHANGE WRITE        : FORBIDDEN")
print("FABRICATION           : FORBIDDEN")
print("SYNTHETIC DATA        : FORBIDDEN")
print("=" * 110)

before_sha = sha256_file(ENTRYPOINT)
before_db = db_fingerprint(DB)
before_integrity = db_integrity(DB)

print("ENTRYPOINT SHA256     :", before_sha)
print("DB INTEGRITY BEFORE   :", before_integrity)
print("DB FINGERPRINT BEFORE :", before_db)

print()
print("=" * 110)
print("ONE CURRENT PRODUCTION RUNTIME")
print("=" * 110)

proc = subprocess.run(
    ["python", str(ENTRYPOINT)],
    cwd=str(ROOT),
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)

stdout = proc.stdout or ""
stderr = proc.stderr or ""

print("RUNTIME EXIT CODE     :", proc.returncode)

snapshot_ids = list(dict.fromkeys(extract_snapshot_ids(stdout)))

print(
    "RUNTIME SNAPSHOT IDS  :",
    len(snapshot_ids),
)

for sid in snapshot_ids:
    print("  ", sid)

fragments = extract_json_fragments(stdout)

uni_objects = []

for fragment in fragments:
    for obj in walk_objects(fragment):
        if not isinstance(obj, dict):
            continue

        if asset_of(obj) != TARGET:
            continue

        uni_objects.append(obj)

# Deduplicate by serialized representation.
unique = []
seen = set()

for obj in uni_objects:
    key = json.dumps(obj, sort_keys=True, default=str)

    if key not in seen:
        seen.add(key)
        unique.append(obj)

print("EXPLICIT UNI OBJECTS   :", len(unique))

print()
print("=" * 110)
print("RAW UNI RUNTIME OBJECTS")
print("=" * 110)

stage_buckets = {
    "OPPORTUNITY": [],
    "SIGNAL": [],
    "SCORE": [],
    "DECISION": [],
    "RISK": [],
    "TRADE_GATE": [],
    "ORDER_INTENT": [],
    "UNKNOWN": [],
}

for index, obj in enumerate(unique, 1):

    stage = classify(obj)
    fields = relevant_fields(obj)

    stage_buckets[stage].append(fields)

    print()
    print(f"[UNI OBJECT {index}]")
    print("  CLASSIFIED STAGE :", stage)
    print("  KEYS             :", ", ".join(sorted(obj.keys())))
    print("  RELEVANT FIELDS  :")
    print(
        json.dumps(
            fields,
            indent=4,
            ensure_ascii=False,
            default=str,
        )
    )

print()
print("=" * 110)
print("STAGE OBJECT INVENTORY")
print("=" * 110)

for stage, objects in stage_buckets.items():
    print(f"{stage:15} : {len(objects)}")

print()
print("=" * 110)
print("EXACT RUNTIME STATUS LINES")
print("=" * 110)

status_lines = exact_runtime_lines(stdout)

if status_lines:
    for line in status_lines:
        print(line)
else:
    print("NONE")

print()
print("=" * 110)
print("RAW RUNTIME OUTPUT — UNI / STAGE EVIDENCE")
print("=" * 110)

# Print only lines containing UNI or stage/status vocabulary.
keywords = (
    "UNI",
    "SIGNAL",
    "SCORE",
    "DECISION",
    "RISK",
    "TRADE GATE",
    "TRADE READY",
    "ORDER INTENT",
    "VALIDATED ORDER",
    "ACTIONABLE",
    "HOLD",
    "REJECT",
)

evidence_lines = []

for line in stdout.splitlines():
    upper = line.upper()

    if any(k in upper for k in keywords):
        evidence_lines.append(line.rstrip())

for line in evidence_lines:
    print(line)

print()
print("=" * 110)
print("PROVENANCE ANALYSIS")
print("=" * 110)

for stage, objects in stage_buckets.items():

    if not objects:
        print(f"{stage:15} : NO EXPLICIT UNI OBJECT")
        continue

    print(f"{stage:15} : {len(objects)} OBJECT(S)")

    for idx, obj in enumerate(objects, 1):

        print(f"  [{idx}]")

        for field in (
            "asset",
            "symbol",
            "ticker",
            "timestamp",
            "price",
            "entry_price",
            "score",
            "confidence",
            "direction",
            "state",
            "status",
            "signal_state",
            "decision",
            "decision_state",
            "decision_result",
            "risk_state",
            "risk_status",
            "risk_result",
            "gate_status",
            "trade_gate",
            "gate_reason",
            "trade_ready",
            "intent_id",
            "snapshot_id",
            "signal_identity",
            "score_identity",
            "validation_result",
            "regime",
        ):
            if field in obj:
                print(f"     {field:22} : {obj[field]}")

print()
print("=" * 110)
print("CONTROLLER INTERPRETATION")
print("=" * 110)

print(
    "IMPORTANT             : "
    "NO TRADE-READY VALUE IS INFERRED FROM MISSING DATA."
)

print(
    "IMPORTANT             : "
    "NO STAGE IS MARKED BLOCKED UNLESS RUNTIME EVIDENCE EXISTS."
)

print(
    "IMPORTANT             : "
    "UNKNOWN OBJECTS REMAIN UNKNOWN."
)

print()
print("=" * 110)
print("SAFETY / INTEGRITY")
print("=" * 110)

after_integrity = db_integrity(DB)
after_db = db_fingerprint(DB)
after_sha = sha256_file(ENTRYPOINT)

print("DB INTEGRITY AFTER    :", after_integrity)
print("DB FINGERPRINT AFTER  :", after_db)
print(
    "DB FINGERPRINT DELTA  :",
    "PRESENT — OPERATIONAL RUNTIME PERSISTENCE"
    if before_db != after_db
    else "NONE",
)

print("ENTRYPOINT UNCHANGED  :", before_sha == after_sha)
print("BEFORE SHA256         :", before_sha)
print("AFTER SHA256          :", after_sha)

print()
print("=" * 110)
print("FORENSIC CONCLUSION")
print("=" * 110)

if proc.returncode != 0:
    conclusion = "BLOCKED — CURRENT RUNTIME FAILED"

elif not snapshot_ids:
    conclusion = "BLOCKED — CURRENT SNAPSHOT ID NOT EXPOSED"

elif not unique:
    conclusion = "BLOCKED — NO EXPLICIT UNI RUNTIME OBJECT EXPOSED"

else:
    conclusion = (
        "PASS — UNI RUNTIME OBJECTS EXTRACTED; "
        "DOWNSTREAM STAGE PROVENANCE REQUIRES NO GUESSING"
    )

print("FINAL STATUS           :", conclusion)
print("EXECUTION              : DISABLED")
print("ORDER                  : NONE")
print("EXCHANGE WRITE        : NONE")
print("PRODUCTION LOGIC      : UNCHANGED")
print("THRESHOLD CHANGE      : NONE")
print("SYNTHETIC/FALLBACK    : NONE")
print("HARD STOP             : YES")
print("=" * 110)