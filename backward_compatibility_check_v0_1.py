from pathlib import Path
import importlib
import ast

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGETS = [
    "arunda_pipeline",
    "market_snapshot_engine",
    "market_adapter",
]

violations = []

print("=" * 80)
print("ARUNDA TRADER — BACKWARD COMPATIBILITY CHECK v0.1")
print("=" * 80)
print("MODE              : READ ONLY")
print("EXCHANGE REQUEST  : NONE")
print("DATABASE WRITE    : NONE")
print("EXECUTION         : NONE")
print()

# ------------------------------------------------------------
# 1. Syntax
# ------------------------------------------------------------

for module_name in TARGETS:
    path = ROOT / f"{module_name}.py"

    if not path.exists():
        violations.append(f"{module_name}: FILE NOT FOUND")
        continue

    try:
        ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path)
        )
        print(f"SYNTAX {module_name:<24}: PASS")
    except SyntaxError as exc:
        violations.append(
            f"{module_name}: SYNTAX ERROR: {exc}"
        )

print()

# ------------------------------------------------------------
# 2. Import
# ------------------------------------------------------------

for module_name in TARGETS:
    try:
        importlib.import_module(module_name)
        print(f"IMPORT {module_name:<24}: PASS")
    except Exception as exc:
        violations.append(
            f"{module_name}: IMPORT ERROR: {type(exc).__name__}: {exc}"
        )

print()

# ------------------------------------------------------------
# 3. Boundary independence
# ------------------------------------------------------------

pipeline_text = (
    ROOT / "arunda_pipeline.py"
).read_text(encoding="utf-8")

forbidden = [
    "ToobitTradingAdapter",
    "BitpinTradingAdapter",
    "build_toobit_boundary",
    "build_bitpin_boundary",
    "TOOBIT",
    "BITPIN",
    "place_order",
    "cancel_order",
    "withdraw",
]

boundary_refs = [
    x for x in forbidden
    if x in pipeline_text
]

print(
    "PIPELINE EXCHANGE DEPENDENCY : "
    + ("NONE" if not boundary_refs else "FAIL")
)

if boundary_refs:
    for x in boundary_refs:
        violations.append(
            f"arunda_pipeline.py: unexpected dependency -> {x}"
        )

# ------------------------------------------------------------
# 4. CMC path presence
# ------------------------------------------------------------

snapshot_text = (
    ROOT / "market_snapshot_engine.py"
).read_text(encoding="utf-8")

if "COINMARKETCAP" in snapshot_text.upper() or "CMC" in snapshot_text:
    print("CMC MARKET DATA PATH         : PRESENT")
else:
    violations.append(
        "market_snapshot_engine.py: CMC path not detected"
    )
    print("CMC MARKET DATA PATH         : FAIL")

print()

if violations:
    print("RESULT                       : FAIL")
    print()
    for item in sorted(set(violations)):
        print(" -", item)
else:
    print("TOOBIT REQUIRED              : NO")
    print("BITPIN REQUIRED              : NO")
    print("BOUNDARY REQUIRED            : NO")
    print("CMC PATH                     : PRESERVED")
    print()
    print("RESULT                       : PASS")

print("=" * 80)
