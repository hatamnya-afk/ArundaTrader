# cleanup_inventory_short.py

from pathlib import Path
import re
import json

ROOT = Path(__file__).resolve().parent

PROD = {
    "arunda_pipeline.py",
    "feature_contract.py",
    "feature_snapshot_reader.py",
    "score_producer.py",
    "signal_engine.py",
    "signal_validator.py",
    "signal_scorer.py",
    "decision_engine.py",
    "risk_engine.py",
    "trade_gate_engine.py",
    "order_intent.py",
    "market_snapshot_engine.py",
    "market_data_engine.py",
    "opportunity_engine.py",
    "arunda.db",
}

KEYWORDS = {
    "forensic": "FORENSIC",
    "audit": "FORENSIC",
    "diagnostic": "FORENSIC",
    "verify": "FORENSIC",
    "repair": "FORENSIC",
    "checkpoint": "CHECKPOINT",
    "cp1": "CHECKPOINT",
    "cp2": "CHECKPOINT",
    "cp3": "CHECKPOINT",
    "cp4": "CHECKPOINT",
    "cp5": "CHECKPOINT",
    "cp6": "CHECKPOINT",
    "cp7": "CHECKPOINT",
    "cp8": "CHECKPOINT",
    "cp9": "CHECKPOINT",
    "cp10": "CHECKPOINT",
    "cp11": "CHECKPOINT",
    "cp12": "CHECKPOINT",
    "legacy": "LEGACY",
    "museum": "LEGACY",
    "deprecated": "LEGACY",
    "archive": "LEGACY",
    "temp": "TEMP",
    "tmp": "TEMP",
    "cache": "TEMP",
    "log": "TEMP",
    "backup": "BACKUP",
    ".bak": "BACKUP",
    ".old": "BACKUP",
}

def classify(p):
    n = p.name.lower()

    if p.name in PROD:
        return "PRODUCTION"

    for k, c in KEYWORDS.items():
        if k in n:
            return c

    if p.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
        return "UNKNOWN"

    if p.suffix.lower() in {".py", ".json", ".csv", ".txt"}:
        return "UNKNOWN"

    return "UNKNOWN"


files = [
    p for p in ROOT.rglob("*")
    if p.is_file()
]

groups = {
    "PRODUCTION": [],
    "FORENSIC": [],
    "CHECKPOINT": [],
    "LEGACY": [],
    "TEMP": [],
    "BACKUP": [],
    "UNKNOWN": [],
}

for p in files:
    groups[classify(p)].append(str(p.relative_to(ROOT)))

print("=" * 80)
print("ARUNDA TRADER — CLEANUP CONTROLLED INVENTORY v0.2")
print("=" * 80)

print(f"FILES BEFORE : {len(files)}")
print()

for name in groups:
    items = groups[name]
    print(f"{name:12} : {len(items)}")

    if name != "PRODUCTION":
        for x in items:
            print(f"  {x}")

print()
print("=" * 80)
print("PRODUCTION PROTECTION")
print("=" * 80)

missing = []

for p in sorted(PROD):
    exists = (ROOT / p).exists()
    print(f"{'OK' if exists else 'MISSING':8} {p}")

    if not exists:
        missing.append(p)

print()
print("=" * 80)
print("EXECUTION SAFETY")
print("=" * 80)

pipeline = ROOT / "arunda_pipeline.py"

if pipeline.exists():
    text = pipeline.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    m = re.search(
        r"EXECUTION_ENABLED\s*=\s*(True|False)",
        text,
        re.I
    )

    execution = m.group(1) if m else "NOT_FOUND"
else:
    execution = "PIPELINE_MISSING"

print(f"EXECUTION_ENABLED : {execution}")

opp = ROOT / "opportunity_engine.py"

if opp.exists():
    text = opp.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    m = re.search(
        r"MAX_CANDIDATES\s*=\s*(\d+)",
        text
    )

    print(
        f"MAX_CANDIDATES    : "
        f"{m.group(1) if m else 'NOT_FOUND'}"
    )

print()
print("=" * 80)
print("CLEANUP DECISION")
print("=" * 80)

print("SAFE_TO_REMOVE    : NONE")
print("REVIEW_REQUIRED   :", len(groups["UNKNOWN"]) + len(groups["LEGACY"]) + len(groups["FORENSIC"]) + len(groups["CHECKPOINT"]) + len(groups["TEMP"]) + len(groups["BACKUP"]))
print("FILES DELETED     : 0")
print("DB CHANGED        : NO")
print("PRODUCTION CHANGED: NO")
print("RUNTIME EXECUTED  : NO")

if missing:
    print("STATUS            : BLOCKED")
    print("MISSING           :", ", ".join(missing))
elif execution != "False":
    print("STATUS            : BLOCKED")
else:
    print("STATUS            : INVENTORY PASS")

print("=" * 80)