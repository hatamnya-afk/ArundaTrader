from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "arunda_pipeline.py"
OUTPUT = ROOT / "arunda_pipeline_FIXED_v2.py"

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

line_start = source.rfind("\n", 0, second) + 1
header_indent = source[line_start:second]

if header_indent != "    ":
    raise RuntimeError(
        f"Unexpected second-header indentation: {header_indent!r}"
    )

class_marker = "class RuntimeOrderIntent(dict):"
class_pos = source.find(class_marker, second)

if class_pos < 0:
    raise RuntimeError("RuntimeOrderIntent class not found")

# The class itself must start at column 0.
class_line_start = source.rfind("\n", 0, class_pos) + 1
class_prefix = source[class_line_start:class_pos]

if class_prefix != "":
    raise RuntimeError(
        f"RuntimeOrderIntent is not top-level: prefix={class_prefix!r}"
    )

# Remove from the nested second coding header through the newline
# immediately before the real top-level class.
fixed = source[:second] + source[class_line_start:]

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

# Safety assertions: the top-level class must remain unchanged.
if "class RuntimeOrderIntent(dict):" not in fixed:
    raise RuntimeError("RuntimeOrderIntent disappeared")

if "\n    class RuntimeOrderIntent(dict):" in fixed:
    raise RuntimeError("RuntimeOrderIntent became indented")

ast.parse(fixed, filename=str(OUTPUT))
compile(fixed, str(OUTPUT), "exec")

OUTPUT.write_text(fixed, encoding="utf-8", newline="")

print("SOURCE=arunda_pipeline.py")
print("NESTED_DUPLICATE_REMOVED=TRUE")
print("RUNTIME_ORDER_INTENT_INDENTATION_PRESERVED=TRUE")
print("SCORE_FEATURE_RECORDS_FIXED=TRUE")
print("AST=PASS")
print("COMPILE=PASS")
print(f"OUTPUT={OUTPUT}")
print("ORIGINAL_OVERWRITTEN=FALSE")
print("RUNTIME_EXECUTED=FALSE")
