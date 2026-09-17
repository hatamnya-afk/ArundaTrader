from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent

KEYWORDS = [
    "bitpin",
    "exchange",
    "order",
    "execution",
    "position",
    "sizing",
    "api",
    "client",
    "market",
    "symbol",
    "balance",
    "account",
    "credential",
    "config",
    "secret",
    "api_key",
]

SECRET_PATTERNS = [
    r'(?i)(api[_-]?key\s*[=:]\s*)[^\s,"\']+',
    r'(?i)(api[_-]?secret\s*[=:]\s*)[^\s,"\']+',
    r'(?i)(secret[_-]?key\s*[=:]\s*)[^\s,"\']+',
    r'(?i)(password\s*[=:]\s*)[^\s,"\']+',
    r'(?i)(token\s*[=:]\s*)[^\s,"\']+',
    r'(?i)(authorization\s*[=:]\s*)[^\s,"\']+',
]

def redact(text):
    for p in SECRET_PATTERNS:
        text = re.sub(p, r'\1[REDACTED]', text)
    return text

def score_file(path, text):
    low = text.lower()
    score = 0
    hits = []

    for kw in KEYWORDS:
        n = low.count(kw)
        if n:
            score += min(n, 10)
            hits.append(f"{kw}:{n}")

    return score, hits

results = []

print("=" * 90)
print("ARUNDA TRADER — EXECUTION / EXCHANGE PATH DISCOVERY v0.1")
print("=" * 90)
print(f"ROOT = {ROOT}")
print("MODE = READ ONLY")
print("DB WRITE = NONE")
print("EXCHANGE WRITE = NONE")
print("ORDER SUBMISSION = NONE")
print()

for path in ROOT.rglob("*.py"):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    score, hits = score_file(path, text)

    if score > 0:
        results.append((score, path, hits, text))

results.sort(key=lambda x: (-x[0], str(x[1]).lower()))

print(f"PYTHON FILES SCANNED = {len(list(ROOT.rglob('*.py')))}")
print(f"MATCHING FILES = {len(results)}")
print()

print("-" * 90)
print("TOP CANDIDATE FILES")
print("-" * 90)

for i, (score, path, hits, text) in enumerate(results[:30], 1):
    print(f"\n[{i}] SCORE={score}")
    print(f"FILE : {path.relative_to(ROOT)}")
    print(f"HITS : {', '.join(hits)}")

print()
print("=" * 90)
print("EXECUTION / EXCHANGE REFERENCES")
print("=" * 90)

patterns = [
    r'(?i)bitpin',
    r'(?i)requests\.(get|post|put|delete)',
    r'(?i)httpx\.(get|post|put|delete)',
    r'(?i)Client\(',
    r'(?i)api[_-]?key',
    r'(?i)api[_-]?secret',
    r'(?i)balance',
    r'(?i)minimum',
    r'(?i)min[_-]?order',
    r'(?i)minimum[_-]?order',
    r'(?i)order[_-]?(create|submit|place|send)',
    r'(?i)create[_-]?order',
    r'(?i)place[_-]?order',
    r'(?i)submit[_-]?order',
    r'(?i)EXECUTION_ENABLED',
]

shown = 0

for score, path, hits, text in results:
    lines = text.splitlines()

    local_hits = []

    for line_no, line in enumerate(lines, 1):
        if any(re.search(p, line) for p in patterns):
            local_hits.append((line_no, line))

    if not local_hits:
        continue

    print()
    print("-" * 90)
    print(f"FILE: {path.relative_to(ROOT)}")
    print("-" * 90)

    for line_no, line in local_hits:
        start = max(1, line_no - 2)
        end = min(len(lines), line_no + 2)

        print(f"\n--- lines {start}-{end} ---")

        for n in range(start, end + 1):
            print(f"{n:5}: {redact(lines[n-1])}")

        shown += 1

    if shown >= 20:
        break

print()
print("=" * 90)
print("CONFIGURATION FILE DISCOVERY")
print("=" * 90)

config_candidates = []

for p in ROOT.rglob("*"):
    if not p.is_file():
        continue

    name = p.name.lower()

    if any(x in name for x in [
        "config",
        "setting",
        "env",
        "credential",
        "secret",
        "exchange",
        "bitpin",
        "execution",
        "order",
        "position",
    ]):
        config_candidates.append(p)

for p in sorted(config_candidates):
    try:
        size = p.stat().st_size
    except Exception:
        size = -1

    print(f"{p.relative_to(ROOT)} | {size} bytes")

print()
print("=" * 90)
print("END — READ ONLY")
print("=" * 90)