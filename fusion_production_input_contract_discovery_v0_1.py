from pathlib import Path
import ast
import re

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGETS = {
    "MARKET": [
        "technical_score",
        "market_score",
        "CMC_SNAPSHOT_ANALYSIS",
        "market_data",
    ],
    "POSITIONING": [
        "positioning_score",
        "positioning_data",
        "COINALYZE",
        "positioning",
    ],
    "NEWS": [
        "news_score",
        "news_signals",
        "news",
    ],
}

EXCLUDE = {
    "arunda.db",
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "node_modules",
}

print("=" * 100)
print("ARUNDA FUSION PRODUCTION INPUT CONTRACT DISCOVERY v0.1")
print("=" * 100)

files = []

for p in ROOT.rglob("*.py"):
    if any(part in EXCLUDE for part in p.parts):
        continue
    files.append(p)

print(f"PYTHON_FILES_SCANNED={len(files)}")
print()

hits = {
    "MARKET": [],
    "POSITIONING": [],
    "NEWS": [],
}

for path in files:
    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        continue

    for arm, terms in TARGETS.items():

        matched = []

        for term in terms:
            if term.lower() in text.lower():
                matched.append(term)

        if matched:
            hits[arm].append(
                (path, sorted(set(matched)))
            )

for arm in ["MARKET", "POSITIONING", "NEWS"]:

    print("=" * 100)
    print(f"{arm} ARM")
    print("=" * 100)

    unique = {}

    for path, terms in hits[arm]:
        unique[str(path)] = terms

    if not unique:
        print("NO_CANDIDATE_FILES")
        continue

    for path, terms in sorted(unique.items()):
        print()
        print("FILE   :", path)
        print("MATCH  :", ", ".join(terms))

print()

# -------------------------------------------------------------------------
# AST/API discovery
# -------------------------------------------------------------------------

print("=" * 100)
print("PUBLIC API / PRODUCER DISCOVERY")
print("=" * 100)

patterns = (
    "score",
    "signal",
    "position",
    "news",
    "market",
    "technical",
    "producer",
)

for path in files:

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
        tree = ast.parse(
            source,
            filename=str(path)
        )
    except Exception:
        continue

    funcs = []

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

            name = node.name.lower()

            if any(
                token in name
                for token in patterns
            ):
                funcs.append(node.name)

    if funcs:

        print()
        print("FILE:", path)

        for name in sorted(set(funcs)):
            print("  FUNCTION:", name)

print()

# -------------------------------------------------------------------------
# Contract signals
# -------------------------------------------------------------------------

print("=" * 100)
print("CONTRACT EVIDENCE")
print("=" * 100)

for arm in ["MARKET", "POSITIONING", "NEWS"]:

    print()
    print(f"[{arm}]")

    if not hits[arm]:
        print("STATUS=ABSENT")
        continue

    print("STATUS=CANDIDATES_FOUND")

    for path, terms in hits[arm]:
        print(
            f"CANDIDATE={path.name} | "
            f"MATCH={','.join(terms)}"
        )

print()

print("=" * 100)
print("SAFETY")
print("=" * 100)

print("PRODUCTION_DB_TOUCHED=FALSE")
print("DB_WRITES=0")
print("FUSION_EXECUTED=FALSE")
print("SCORE=OFF")
print("DECISION=OFF")
print("ORDER_INTENTS=0")
print("EXECUTION=OFF")
print("SYNTHETIC_DATA=FALSE")
print("FABRIC_MODIFIED=FALSE")
print()

print("=" * 100)
print("DISCOVERY COMPLETE")
print("=" * 100)
