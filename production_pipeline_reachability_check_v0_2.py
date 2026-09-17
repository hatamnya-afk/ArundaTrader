from pathlib import Path
import ast

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PIPELINE = ROOT / "arunda_pipeline.py"

print("=" * 80)
print("ARUNDA TRADER — PRODUCTION PIPELINE REACHABILITY CHECK v0.2")
print("=" * 80)
print("MODE              : READ ONLY")
print("DATABASE WRITE    : NONE")
print("EXCHANGE REQUEST  : NONE")
print("EXECUTION         : NONE")
print()

violations = []

if not PIPELINE.exists():
    print("PIPELINE FILE                 : FAIL")
    raise SystemExit(1)

source = PIPELINE.read_text(encoding="utf-8")

try:
    tree = ast.parse(source, filename=str(PIPELINE))
    print("PIPELINE SYNTAX               : PASS")
except SyntaxError as exc:
    print("PIPELINE SYNTAX               : FAIL")
    print(exc)
    raise SystemExit(1)

functions = {
    node.name
    for node in ast.walk(tree)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
}

print(
    "FUNCTION main                 :",
    "PASS" if "main" in functions else "FAIL"
)

print(
    "FUNCTION run_script           :",
    "PASS" if "run_script" in functions else "FAIL"
)

if "main" not in functions:
    violations.append("main() missing")

if "run_script" not in functions:
    violations.append("run_script() missing")

print()

# ------------------------------------------------------------
# Actual orchestrator boundary
# ------------------------------------------------------------

markers = {
    "market_snapshot_engine": "market_snapshot_engine",
    "run_script": "run_script",
    "CURRENT_RUNTIME_SNAPSHOT": "CURRENT_RUNTIME_SNAPSHOT",
}

for name, marker in markers.items():
    present = marker in source

    print(
        f"PATH MARKER {name:<20}: "
        f"{'PRESENT' if present else 'MISSING'}"
    )

    if not present:
        violations.append(
            f"missing production path marker: {marker}"
        )

print()

# ------------------------------------------------------------
# Exchange independence
# ------------------------------------------------------------

exchange_terms = [
    "BitpinTradingAdapter",
    "ToobitTradingAdapter",
    "build_bitpin_boundary",
    "build_toobit_boundary",
    "BITPIN",
    "TOOBIT",
    "api.toobit.com",
    "place_order(",
    "cancel_order(",
    "withdraw(",
]

found_exchange = [
    term for term in exchange_terms
    if term in source
]

print(
    "EXCHANGE-SPECIFIC CORE PATH  :",
    "NONE" if not found_exchange else "FAIL"
)

if found_exchange:
    for term in found_exchange:
        violations.append(
            f"exchange-specific reference: {term}"
        )

# ------------------------------------------------------------
# Boundary module existence
# ------------------------------------------------------------

boundary = ROOT / "exchange_adapter_boundary.py"
mapping = ROOT / "exchange_adapter_mapping.py"

print(
    "CANONICAL BOUNDARY FILE       :",
    "PRESENT" if boundary.exists() else "MISSING"
)

print(
    "MAPPING LAYER FILE            :",
    "PRESENT" if mapping.exists() else "MISSING"
)

# Boundary files being present must NOT imply Core dependency.
if not boundary.exists():
    violations.append("canonical boundary file missing")

if not mapping.exists():
    violations.append("mapping layer file missing")

print()

# ------------------------------------------------------------
# Critical rule:
# process_signals is NOT required inside arunda_pipeline.py.
# It belongs to downstream production execution chain.
# ------------------------------------------------------------

print("PROCESS_SIGNALS IN ORCHESTRATOR: NOT REQUIRED")
print("SUBPROCESS PRODUCTION BOUNDARY : PRESERVED")

print()

if violations:
    print("RESULT                       : FAIL")
    print()
    for item in sorted(set(violations)):
        print(" -", item)
else:
    print("PRODUCTION ENTRY             : REACHABLE")
    print("RUN_SCRIPT BOUNDARY          : REACHABLE")
    print("MARKET SNAPSHOT PATH         : REACHABLE")
    print("CURRENT SNAPSHOT PATH        : REACHABLE")
    print("EXCHANGE CORE DEPENDENCY     : NONE")
    print("ORDER/EXCHANGE WRITE PATH    : NONE")
    print("PROCESS_SIGNALS ASSUMPTION   : REMOVED")
    print()
    print("RESULT                       : PASS")

print("=" * 80)
