# ARUNDA_UNI_FIRST_TRADE_READINESS_TRACE_v0.5.py
# SOURCE-LEVEL PROVENANCE FORENSIC
# READ ONLY — NO RUNTIME / NO DB WRITE / NO ORDER

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
ENTRYPOINT = ROOT / "arunda_pipeline.py"
TARGET = "UNI"

FORBIDDEN_WRITE_PATTERNS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bALTER\b",
    r"\bCREATE\s+TABLE\b",
    r"\bexecute\s*\(",
    r"\bexecutemany\s*\(",
]

TRADE_READY_TERMS = [
    "trade_ready",
    "trade ready",
    "trade-ready",
    "is_trade_ready",
    "tradeready",
]

ORDER_INTENT_TERMS = [
    "order_intent",
    "order intent",
    "order-intent",
    "intent_id",
    "validated_order_intent",
]

TRADE_GATE_TERMS = [
    "trade_gate",
    "trade gate",
    "trade-gate",
    "gate_status",
    "gate_reason",
]

PROVENANCE_TERMS = [
    "asset",
    "direction",
    "entry_price",
    "confidence",
    "regime",
    "timestamp",
    "snapshot_id",
    "intent_id",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def normalized(text: str) -> str:
    return text.lower().replace("_", " ").replace("-", " ")


def contains_any(text: str, terms):
    n = normalized(text)
    return any(term in n for term in terms)


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def source_excerpt(lines, center, radius=5):
    start = max(0, center - radius - 1)
    end = min(len(lines), center + radius)

    return "\n".join(
        f"{i+1:6}: {lines[i]}"
        for i in range(start, end)
    )


def ast_calls(source: str):
    try:
        tree = ast.parse(source)
    except Exception:
        return []

    calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):

            name = None

            if isinstance(node.func, ast.Name):
                name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            if name:
                calls.append(
                    (
                        name,
                        getattr(node, "lineno", None),
                        ast.unparse(node)
                        if hasattr(ast, "unparse")
                        else name,
                    )
                )

    return calls


def find_term_hits(text: str, terms):
    hits = []

    for term in terms:
        pattern = re.escape(term)

        for m in re.finditer(pattern, text, re.I):
            hits.append(
                (
                    term,
                    line_number(text, m.start()),
                )
            )

    return sorted(set(hits), key=lambda x: (x[1], x[0]))


def classify_file(path: Path, source: str):
    n = normalized(source)

    scores = {
        "TRADE_GATE": 0,
        "TRADE_READY": 0,
        "ORDER_INTENT": 0,
    }

    for term in TRADE_GATE_TERMS:
        if normalized(term) in n:
            scores["TRADE_GATE"] += 1

    for term in TRADE_READY_TERMS:
        if normalized(term) in n:
            scores["TRADE_READY"] += 1

    for term in ORDER_INTENT_TERMS:
        if normalized(term) in n:
            scores["ORDER_INTENT"] += 1

    return scores


print("=" * 110)
print("ARUNDA TRADER — UNI FIRST-TRADE READINESS SOURCE PROVENANCE TRACE v0.5")
print("=" * 110)

print("MODE                  : READ ONLY")
print("STARTED               :", datetime.now(timezone.utc).isoformat())
print("TARGET ASSET          :", TARGET)
print("PROJECT ROOT          :", ROOT)
print("ENTRYPOINT            :", ENTRYPOINT)
print("RUNTIME EXECUTION     : FORBIDDEN")
print("DB WRITE              : FORBIDDEN")
print("ORDER                 : FORBIDDEN")
print("EXCHANGE WRITE        : FORBIDDEN")
print("THRESHOLD CHANGE      : FORBIDDEN")
print("PRODUCTION PATCH      : FORBIDDEN")
print("=" * 110)

if not ENTRYPOINT.exists():
    print("FATAL                 : ENTRYPOINT NOT FOUND")
    raise SystemExit(1)

entry_sha_before = sha256_file(ENTRYPOINT)

print("ENTRYPOINT SHA256     :", entry_sha_before)

print()
print("=" * 110)
print("PHASE 1 — PRODUCTION ENTRYPOINT FORENSIC")
print("=" * 110)

entry_source = ENTRYPOINT.read_text(
    encoding="utf-8",
    errors="replace",
)

entry_lines = entry_source.splitlines()

print("ENTRYPOINT LINES      :", len(entry_lines))

execution_hits = []

for i, line in enumerate(entry_lines, 1):
    if re.search(
        r"EXECUTION_ENABLED\s*=\s*True",
        line,
        re.I,
    ):
        execution_hits.append(i)

print(
    "EXECUTION_ENABLED=True:",
    len(execution_hits),
)

if execution_hits:
    for ln in execution_hits:
        print(f"  LINE {ln}: {entry_lines[ln-1]}")

print()
print("=" * 110)
print("PHASE 2 — SOURCE INVENTORY")
print("=" * 110)

candidate_files = []

for path in ROOT.glob("*.py"):

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        continue

    scores = classify_file(path, source)

    if any(v > 0 for v in scores.values()):
        candidate_files.append(
            (
                path,
                source,
                scores,
            )
        )

print("CANDIDATE FILES       :", len(candidate_files))

for path, _, scores in candidate_files:

    print()
    print("FILE                  :", path.name)
    print(
        "  TRADE_GATE TERMS    :",
        scores["TRADE_GATE"],
    )
    print(
        "  TRADE_READY TERMS   :",
        scores["TRADE_READY"],
    )
    print(
        "  ORDER_INTENT TERMS  :",
        scores["ORDER_INTENT"],
    )

print()
print("=" * 110)
print("PHASE 3 — TRADE GATE → TRADE READY")
print("=" * 110)

trade_ready_evidence = []

for path, source, scores in candidate_files:

    hits = find_term_hits(
        source,
        TRADE_READY_TERMS,
    )

    if not hits:
        continue

    lines = source.splitlines()

    print()
    print("FILE                  :", path.name)
    print("TRADE READY HITS      :", len(hits))

    for term, ln in hits:

        print()
        print(
            f"TERM={term!r} LINE={ln}"
        )

        print(
            source_excerpt(
                lines,
                ln,
                radius=4,
            )
        )

        trade_ready_evidence.append(
            {
                "file": str(path),
                "term": term,
                "line": ln,
            }
        )

print()
print("=" * 110)
print("PHASE 4 — ORDER INTENT SOURCE")
print("=" * 110)

order_intent_evidence = []

for path, source, scores in candidate_files:

    hits = find_term_hits(
        source,
        ORDER_INTENT_TERMS,
    )

    if not hits:
        continue

    lines = source.splitlines()

    print()
    print("FILE                  :", path.name)
    print("ORDER INTENT HITS     :", len(hits))

    for term, ln in hits:

        print()
        print(
            f"TERM={term!r} LINE={ln}"
        )

        print(
            source_excerpt(
                lines,
                ln,
                radius=5,
            )
        )

        order_intent_evidence.append(
            {
                "file": str(path),
                "term": term,
                "line": ln,
            }
        )

print()
print("=" * 110)
print("PHASE 5 — TRADE GATE SOURCE")
print("=" * 110)

trade_gate_evidence = []

for path, source, scores in candidate_files:

    hits = find_term_hits(
        source,
        TRADE_GATE_TERMS,
    )

    if not hits:
        continue

    lines = source.splitlines()

    print()
    print("FILE                  :", path.name)
    print("TRADE GATE HITS       :", len(hits))

    for term, ln in hits:

        print()
        print(
            f"TERM={term!r} LINE={ln}"
        )

        print(
            source_excerpt(
                lines,
                ln,
                radius=5,
            )
        )

        trade_gate_evidence.append(
            {
                "file": str(path),
                "term": term,
                "line": ln,
            }
        )

print()
print("=" * 110)
print("PHASE 6 — PROVENANCE FIELD OWNERSHIP")
print("=" * 110)

for path, source, _ in candidate_files:

    hits = find_term_hits(
        source,
        PROVENANCE_TERMS,
    )

    if not hits:
        continue

    print()
    print("FILE                  :", path.name)

    grouped = {}

    for term, ln in hits:
        grouped.setdefault(term, []).append(ln)

    for term, lines_found in grouped.items():

        print(
            f"  {term:15} : "
            f"{len(lines_found)} hit(s) "
            f"lines={lines_found[:20]}"
        )

print()
print("=" * 110)
print("PHASE 7 — AST CALL GRAPH / CONSTRUCTION EVIDENCE")
print("=" * 110)

for path, source, _ in candidate_files:

    calls = ast_calls(source)

    interesting = []

    for name, ln, expr in calls:

        n = normalized(name)

        if (
            "trade" in n
            or "intent" in n
            or "risk" in n
            or "gate" in n
            or "decision" in n
            or "signal" in n
        ):
            interesting.append(
                (
                    name,
                    ln,
                    expr,
                )
            )

    if not interesting:
        continue

    print()
    print("FILE                  :", path.name)

    for name, ln, expr in interesting[:100]:

        print(
            f"  LINE {ln:<5} "
            f"{name:<35} "
            f"{expr[:220]}"
        )

print()
print("=" * 110)
print("PHASE 8 — DATABASE WRITE DETECTION IN CANDIDATE SOURCES")
print("=" * 110)

write_hits = []

for path, source, _ in candidate_files:

    for i, line in enumerate(
        source.splitlines(),
        1,
    ):

        for pattern in FORBIDDEN_WRITE_PATTERNS:

            if re.search(pattern, line, re.I):

                write_hits.append(
                    (
                        path.name,
                        i,
                        line.strip(),
                    )
                )

                break

print(
    "WRITE-LIKE SOURCE HITS:",
    len(write_hits),
)

for item in write_hits[:100]:
    print(
        f"  {item[0]}:{item[1]} "
        f"{item[2]}"
    )

print()
print("=" * 110)
print("PHASE 9 — DIRECT UNI REFERENCES")
print("=" * 110)

uni_hits = []

for path, source, _ in candidate_files:

    lines = source.splitlines()

    for i, line in enumerate(lines, 1):

        if re.search(
            r"\bUNI\b",
            line,
            re.I,
        ):
            uni_hits.append(
                (
                    path.name,
                    i,
                    line.strip(),
                )
            )

print(
    "DIRECT UNI SOURCE HITS:",
    len(uni_hits),
)

for item in uni_hits[:100]:
    print(
        f"  {item[0]}:{item[1]} "
        f"{item[2]}"
    )

print()
print("=" * 110)
print("PHASE 10 — PROVENANCE CHAIN CLASSIFICATION")
print("=" * 110)

print(
    "TRADE GATE SOURCE      :",
    "FOUND" if trade_gate_evidence else "NOT FOUND",
)

print(
    "TRADE READY SOURCE     :",
    "FOUND" if trade_ready_evidence else "NOT FOUND",
)

print(
    "ORDER INTENT SOURCE    :",
    "FOUND" if order_intent_evidence else "NOT FOUND",
)

print()

if trade_gate_evidence and trade_ready_evidence:
    print(
        "GATE → READY           : "
        "SOURCE EVIDENCE PRESENT"
    )
else:
    print(
        "GATE → READY           : "
        "SOURCE EVIDENCE UNRESOLVED"
    )

if trade_ready_evidence and order_intent_evidence:
    print(
        "READY → INTENT         : "
        "SOURCE EVIDENCE PRESENT"
    )
else:
    print(
        "READY → INTENT         : "
        "SOURCE EVIDENCE UNRESOLVED"
    )

print()
print("=" * 110)
print("PHASE 11 — FINAL SOURCE-LEVEL SAFETY")
print("=" * 110)

entry_sha_after = sha256_file(ENTRYPOINT)

print(
    "ENTRYPOINT UNCHANGED   :",
    entry_sha_before == entry_sha_after,
)

print(
    "BEFORE SHA256          :",
    entry_sha_before,
)

print(
    "AFTER SHA256           :",
    entry_sha_after,
)

print(
    "PRODUCTION PATCH       : NONE"
)

print(
    "RUNTIME EXECUTED       : NO"
)

print(
    "DB WRITE BY TRACE      : NONE"
)

print(
    "ORDER                  : NONE"
)

print(
    "EXCHANGE WRITE         : NONE"
)

print()
print("=" * 110)
print("FINAL FORENSIC STATUS")
print("=" * 110)

if entry_sha_before != entry_sha_after:

    final_status = (
        "BLOCKED — PRODUCTION ENTRYPOINT CHANGED"
    )

elif execution_hits:

    final_status = (
        "BLOCKED — PRODUCTION EXECUTION FLAG FOUND"
    )

elif not trade_gate_evidence:

    final_status = (
        "BLOCKED — TRADE GATE SOURCE OWNER UNRESOLVED"
    )

elif not trade_ready_evidence:

    final_status = (
        "BLOCKED — TRADE READY SOURCE OWNER UNRESOLVED"
    )

elif not order_intent_evidence:

    final_status = (
        "BLOCKED — ORDER INTENT SOURCE OWNER UNRESOLVED"
    )

else:

    final_status = (
        "PASS — TRADE GATE → TRADE READY → "
        "ORDER INTENT SOURCE OWNERS IDENTIFIED"
    )

print("FINAL STATUS           :", final_status)
print("EXECUTION              : DISABLED")
print("ORDER                  : NONE")
print("EXCHANGE WRITE         : NONE")
print("HARD STOP              : YES")
print("=" * 110)