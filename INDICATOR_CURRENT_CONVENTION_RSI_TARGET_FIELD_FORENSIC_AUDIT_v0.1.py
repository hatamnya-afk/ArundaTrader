from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

TARGET = "rsi14"

print("=" * 100)
print("ARUNDA INDICATOR CURRENT CONVENTION RSI TARGET FIELD FORENSIC AUDIT v0.1")
print("=" * 100)
print("MODE                  : READ ONLY")
print("DATABASE WRITE        : NONE")
print("FORMULA WRITE        : NONE")
print("PRODUCTION RECALCULATION : NONE")
print("PURPOSE               : RESOLVE ONLY RSI14 TARGET FIELD")
print("=" * 100)

print("\nENGINE INVENTORY")
print("-" * 100)
print(f"ENGINE PATH           : {ENGINE_PATH}")
print(f"ENGINE FOUND          : {ENGINE_PATH.exists()}")

if not ENGINE_PATH.exists():
    print("\nFORENSIC CONCLUSION")
    print("-" * 100)
    print("STATUS                : TARGET_FIELD_INCOMPLETE")
    print("REASON                : ENGINE SOURCE NOT FOUND")
    print("AUDIT COMPLETE")
    raise SystemExit(1)

source = ENGINE_PATH.read_text(encoding="utf-8", errors="replace")
lines = source.splitlines()

print(f"SOURCE SIZE           : {len(source)} characters")
print(f"SOURCE LINES          : {len(lines)}")

print("\nTARGET SEARCH")
print("-" * 100)
print(f"TARGET FIELD          : {TARGET}")

matches = []

for i, line in enumerate(lines, start=1):
    if re.search(r"\brsi14\b", line, re.IGNORECASE):
        matches.append((i, line))

print(f"RAW TARGET REFERENCES : {len(matches)}")

for line_no, line in matches:
    print(f"\nLINE {line_no}")
    print(f"  {line.strip()}")

print("\n" + "=" * 100)
print("ASSIGNMENT CANDIDATE ANALYSIS")
print("=" * 100)

assignment_patterns = [
    r"\brsi14\s*=",
    r"\[\s*[\"']rsi14[\"']\s*\]",
    r"\.rsi14\s*=",
    r"rsi14\s*:",
]

assignment_hits = []

for i, line in enumerate(lines, start=1):
    for pattern in assignment_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            assignment_hits.append((i, line.strip()))
            break

print(f"ASSIGNMENT CANDIDATES : {len(assignment_hits)}")

if assignment_hits:
    for line_no, line in assignment_hits:
        print(f"\nLINE {line_no}")
        print(f"  {line}")
else:
    print("  NO DIRECT RSI14 ASSIGNMENT FOUND")

print("\n" + "=" * 100)
print("CONTEXT WINDOWS")
print("=" * 100)

shown = set()

for line_no, _ in matches:
    start = max(1, line_no - 6)
    end = min(len(lines), line_no + 6)

    key = (start, end)
    if key in shown:
        continue

    shown.add(key)

    print(f"\n--- CONTEXT {start}-{end} ---")

    for n in range(start, end + 1):
        marker = ">>>" if n == line_no else "   "
        print(f"{marker} {n:4d}: {lines[n - 1]}")

print("\n" + "=" * 100)
print("TARGET FIELD FORENSIC VERDICT")
print("=" * 100)

if assignment_hits:
    print("TARGET FIELD STATUS   : RESOLVED")
    print("TARGET FIELD EVIDENCE : DIRECT RSI14 ASSIGNMENT FOUND")
    print("NEXT STEP             : VERIFY EXACT PRODUCER / RETURN CHAIN")
else:
    print("TARGET FIELD STATUS   : NOT_DIRECTLY_RESOLVED")
    print("TARGET FIELD EVIDENCE : NO DIRECT RSI14 ASSIGNMENT FOUND")
    print("NEXT STEP             : INSPECT CONTAINER / RECORD MAPPING")

print("\n" + "=" * 100)
print("FINAL RSI TARGET FIELD FORENSIC SUMMARY")
print("=" * 100)
print(f"TARGET REFERENCES     : {len(matches)}")
print(f"ASSIGNMENT CANDIDATES : {len(assignment_hits)}")

if assignment_hits:
    print("TARGET RESOLUTION     : RESOLVED")
    print("STATUS                : TARGET_FIELD_RESOLVED")
else:
    print("TARGET RESOLUTION     : INCOMPLETE")
    print("STATUS                : TARGET_FIELD_NOT_PROVEN")

print("\nDATABASE WRITE OPERATIONS : NONE")
print("ENGINE MODIFICATIONS      : NONE")
print("FORMULA WRITE             : NONE")
print("PRODUCTION RECALCULATION  : NONE")
print("AUDIT COMPLETE")