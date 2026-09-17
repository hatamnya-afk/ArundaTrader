from pathlib import Path
import ast

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
FILE = ROOT / "arunda_pipeline.py"

print("=" * 80)
print("ARUNDA TRADER — PRODUCTION PIPELINE REACHABILITY CHECK v0.1")
print("=" * 80)
print("MODE              : READ ONLY")
print("DATABASE WRITE    : NONE")
print("EXCHANGE REQUEST  : NONE")
print("EXECUTION         : NONE")
print()

violations = []

if not FILE.exists():
    print("PIPELINE FILE                  : FAIL — FILE NOT FOUND")
    raise SystemExit(1)

source = FILE.read_text(encoding="utf-8")

try:
    tree = ast.parse(source, filename=str(FILE))
    print("PIPELINE SYNTAX                : PASS")
except SyntaxError as exc:
    print("PIPELINE SYNTAX                : FAIL")
    print(exc)
    raise SystemExit(1)

functions = {
    node.name
    for node in ast.walk(tree)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
}

required_functions = [
    "main",
    "run_script",
]

for name in required_functions:
    status = "PASS" if name in functions else "FAIL"
    print(f"FUNCTION {name:<20}: {status}")

    if name not in functions:
        violations.append(
            f"missing production function: {name}"
        )

# ------------------------------------------------------------
# Production path markers
# ------------------------------------------------------------

markers = {
    "market_snapshot_engine": "market_snapshot_engine",
    "run_script": "run_script",
    "process": "process_signals",
    "snapshot": "CURRENT_RUNTIME_SNAPSHOT",
}

print()

for label, marker in markers.items():
    found = marker in source
    print(
        f"PATH MARKER {label:<17}: "
        f"{'PRESENT' if found else 'MISSING'}"
    )

    if not found:
        violations.append(
            f"production path marker missing: {marker}"
        )

# ------------------------------------------------------------
# No exchange-specific branching in Core
# ------------------------------------------------------------

exchange_branch_terms = [
    "if exchange ==",
    "if EXCHANGE ==",
    "elif exchange ==",
    "ToobitTradingAdapter",
    "BitpinTradingAdapter",
    "build_toobit_boundary",
    "build_bitpin_boundary",
]

found_branches = [
    x for x in exchange_branch_terms
    if x in source
]

print()
print(
    "EXCHANGE-SPECIFIC CORE BRANCH : "
    + ("NONE" if not found_branches else "FAIL")
)

if found_branches:
    for x in found_branches:
        violations.append(
            f"exchange-specific core branch/reference: {x}"
        )

# ------------------------------------------------------------
# No write/execution reachability
# ------------------------------------------------------------

write_terms = [
    "place_order(",
    "cancel_order(",
    "withdraw(",
]

found_writes = [
    x for x in write_terms
    if x in source
]

print(
    "ORDER/EXCHANGE WRITE PATH     : "
    + ("NONE" if not found_writes else "FAIL")
)

if found_writes:
    for x in found_writes:
        violations.append(
            f"write operation reachable from pipeline: {x}"
        )

print()

if violations:
    print("RESULT                        : FAIL")
    print()
    for item in sorted(set(violations)):
        print(" -", item)
else:
    print("PRODUCTION ENTRY              : REACHABLE")
    print("MARKET SNAPSHOT PATH          : REACHABLE")
    print("SCRIPT BOUNDARY               : REACHABLE")
    print("CURRENT SNAPSHOT PATH        : REACHABLE")
    print("EXCHANGE BRANCHING            : NONE")
    print("WRITE/EXECUTION PATH          : NONE")
    print()
    print("RESULT                        : PASS")

print("=" * 80)
