from pathlib import Path
import re

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

EXCLUDE_DIRS = {
    "__pycache__", ".git", ".venv", "venv",
    "node_modules"
}

PATTERNS = [
    r"(?i)api\.bitpin\.ir",
    r"(?i)bitpin",
    r"(?i)authorization",
    r"(?i)api[_-]?key",
    r"(?i)api[_-]?secret",
    r"(?i)secret",
    r"(?i)signature",
    r"(?i)nonce",
    r"(?i)balance",
    r"(?i)account",
    r"(?i)order",
    r"(?i)create[_-]?order",
    r"(?i)place[_-]?order",
    r"(?i)cancel[_-]?order",
    r"(?i)withdraw",
    r"(?i)private",
]

SECRET_PATTERNS = [
    r"(?i)(api[_-]?key\s*[=:]\s*)[^\s,'\"]+",
    r"(?i)(api[_-]?secret\s*[=:]\s*)[^\s,'\"]+",
    r"(?i)(secret\s*[=:]\s*)[^\s,'\"]+",
    r"(?i)(token\s*[=:]\s*)[^\s,'\"]+",
    r"(?i)(authorization\s*[=:]\s*)[^\s,'\"]+",
]

def redact(line):
    for pattern in SECRET_PATTERNS:
        line = re.sub(
            pattern,
            r"\1[REDACTED]",
            line
        )
    return line

print("=" * 90)
print("ARUNDA TRADER — BITPIN PRIVATE API FORENSIC v0.1")
print("=" * 90)
print("MODE              : READ ONLY")
print("ROOT              :", ROOT)
print("CODE CHANGES      : NONE")
print("ORDER SUBMISSION  : NONE")
print("EXCHANGE WRITES   : NONE")
print("CREDENTIAL OUTPUT : REDACTED")
print("=" * 90)

files_scanned = 0
matching_files = 0
total_hits = 0

for path in ROOT.rglob("*.py"):

    if any(part in EXCLUDE_DIRS for part in path.parts):
        continue

    files_scanned += 1

    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines()
    except Exception:
        continue

    hits = []

    for line_no, line in enumerate(lines, 1):

        if any(
            re.search(pattern, line)
            for pattern in PATTERNS
        ):
            hits.append(
                (line_no, redact(line.strip()))
            )

    if not hits:
        continue

    matching_files += 1
    total_hits += len(hits)

    print()
    print("-" * 90)
    print("FILE :", path.relative_to(ROOT))
    print("-" * 90)

    for line_no, line in hits[:30]:
        print(f"{line_no:5d}: {line}")

print()
print("=" * 90)
print("SUMMARY")
print("=" * 90)
print("Python files scanned :", files_scanned)
print("Matching files       :", matching_files)
print("Total hits            :", total_hits)
print("=" * 90)

print()
print("CLASSIFICATION TARGETS")
print("----------------------")
print("PUBLIC MARKET API        = /v1/mkt/markets/")
print("PUBLIC ORDERBOOK API     = /v4/mth/orderbook/")
print("PRIVATE AUTH             = SEARCH")
print("ACCOUNT/BALANCE          = SEARCH")
print("ORDER CREATE             = SEARCH")
print("ORDER CANCEL             = SEARCH")
print("PRIVATE BITPIN ENDPOINT  = SEARCH")
print()
print("HARD RULE: NO REQUEST IS SENT BY THIS SCRIPT.")