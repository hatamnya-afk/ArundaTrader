from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "arunda_pipeline.py"
OUTPUT = ROOT / "arunda_pipeline_FIXED.py"

source = SOURCE.read_text(encoding="utf-8")

# ------------------------------------------------------------
# 1) Remove ONLY the nested duplicate module block
# ------------------------------------------------------------
marker = "# -*- coding: utf-8 -*-"
positions = []
start = 0

while True:
    pos = source.find(marker, start)
    if pos < 0:
        break
    positions.append(pos)
    start = pos + len(marker)

if len(positions) < 2:
    raise RuntimeError(
        f"Expected at least 2 coding headers, found {len(positions)}"
    )

second = positions[1]

line_start = source.rfind("\n", 0, second) + 1
indent = source[line_start:second]

if not indent.startswith("    "):
    raise RuntimeError(
        "Second coding header is not nested/indented. "
        "Refusing destructive edit."
    )

class_marker = "class RuntimeOrderIntent(dict):"
class_pos = source.find(class_marker, second)

if class_pos < 0:
    raise RuntimeError(
        "Top-level RuntimeOrderIntent(dict) not found."
    )

class_line_start = source.rfind("\n", 0, class_pos) + 1

# The real class must be top-level.
if source[class_line_start:class_pos] != "":
    raise RuntimeError(
        "RuntimeOrderIntent class is not top-level. "
        "Refusing destructive edit."
    )

fixed = source[:second] + source[class_line_start:]

# ------------------------------------------------------------
# 2) Fix ONLY the dynamic Score feature_records reference
# ------------------------------------------------------------
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
        f"Targeted Score block count={count}; expected exactly 1."
    )

fixed = fixed.replace(old, new, 1)

# ------------------------------------------------------------
# 3) Static validation BEFORE writing output
# ------------------------------------------------------------
ast.parse(fixed, filename=str(OUTPUT))
compile(fixed, str(OUTPUT), "exec")

OUTPUT.write_text(
    fixed,
    encoding="utf-8",
    newline=""
)

print("SOURCE=arunda_pipeline.py")
print("DUPLICATE_NESTED_BLOCK_REMOVED=TRUE")
print("SCORE_FEATURE_RECORDS_FIXED=TRUE")
print("AST=PASS")
print("COMPILE=PASS")
print(f"OUTPUT={OUTPUT}")
print("ORIGINAL_OVERWRITTEN=FALSE")
print("RUNTIME_EXECUTED=FALSE")
