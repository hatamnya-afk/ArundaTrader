from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "arunda_pipeline.py"
OUTPUT = ROOT / "arunda_pipeline_FIXED_v3.py"

source = SOURCE.read_text(encoding="utf-8")

marker = "# -*- coding: utf-8 -*-"

positions = []
p = 0
while True:
    p = source.find(marker, p)
    if p < 0:
        break
    positions.append(p)
    p += len(marker)

if len(positions) < 2:
    raise RuntimeError(f"Expected >=2 coding headers, found {len(positions)}")

second = positions[1]

# Start at the beginning of the SECOND header's physical line.
second_line_start = source.rfind("\n", 0, second) + 1

# Verify the second header is exactly four spaces indented.
if source[second_line_start:second] != "    ":
    raise RuntimeError(
        f"Unexpected second-header prefix: "
        f"{source[second_line_start:second]!r}"
    )

class_marker = "class RuntimeOrderIntent(dict):"
class_pos = source.find(class_marker, second)

if class_pos < 0:
    raise RuntimeError("RuntimeOrderIntent class not found")

# Start of the physical line containing the class.
class_line_start = source.rfind("\n", 0, class_pos) + 1

# Verify the original class is genuinely column 0.
if source[class_line_start:class_pos] != "":
    raise RuntimeError(
        f"Original RuntimeOrderIntent indentation is not zero: "
        f"{source[class_line_start:class_pos]!r}"
    )

# Remove ONLY the duplicate block between the second header line
# and the original RuntimeOrderIntent class.
fixed = source[:second_line_start] + source[class_line_start:]

old = '''score_snapshot[asset] = build_dynamic_score(
                f"{asset}/USDT",
                direction,
                feature_records,
                structural_state,
                regime_data,
            )'''

new = '''score_snapshot[asset] = build_dynamic_score(
                f"{asset}/USDT",
                direction,
                signal_record.get("feature_records"),
                structural_state,
                regime_data,
            )'''

count = fixed.count(old)

if count != 1:
    raise RuntimeError(
        f"Score target count={count}; expected exactly 1"
    )

fixed = fixed.replace(old, new, 1)

# Exact structural safety checks.
if "\n    class RuntimeOrderIntent(dict):" in fixed:
    raise RuntimeError("RuntimeOrderIntent became indented")

if "\nclass RuntimeOrderIntent(dict):" not in fixed:
    raise RuntimeError("Top-level RuntimeOrderIntent missing")

ast.parse(fixed, filename=str(OUTPUT))
compile(fixed, str(OUTPUT), "exec")

OUTPUT.write_text(fixed, encoding="utf-8", newline="")

print("SOURCE=arunda_pipeline.py")
print("DUPLICATE_NESTED_BLOCK_REMOVED=TRUE")
print("RUNTIME_ORDER_INTENT_INDENTATION_PRESERVED=TRUE")
print("SCORE_FEATURE_RECORDS_FIXED=TRUE")
print("AST=PASS")
print("COMPILE=PASS")
print(f"OUTPUT={OUTPUT}")
print("ORIGINAL_OVERWRITTEN=FALSE")
print("RUNTIME_EXECUTED=FALSE")
