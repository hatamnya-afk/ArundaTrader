from pathlib import Path
import ast
import re
import subprocess

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "arunda_pipeline_FIXED.py"

source = subprocess.check_output(
    ["git", "-C", str(ROOT), "show", "origin/main:arunda_pipeline.py"],
    text=True,
    encoding="utf-8",
)

marker = "# -*- coding: utf-8 -*-"
positions = [m.start() for m in re.finditer(re.escape(marker), source)]
assert len(positions) >= 2, f"expected >=2 coding headers, found {len(positions)}"

second = positions[1]
line_start = source.rfind("\n", 0, second) + 1
assert source[line_start:second].startswith("    "), (
    "second coding header is not indented; refusing destructive edit"
)

class_match = re.search(
    r"(?m)^class RuntimeOrderIntent\(dict\):",
    source[second:],
)
assert class_match, "top-level RuntimeOrderIntent(dict) not found"
end = second + class_match.start()

fixed = source[:second] + source[end:]

old = '''score_snapshot[asset] = build_dynamic_score(\n                f"{asset}/USDT",\n                direction,\n                feature_records,\n                structural_state,\n                regime_data,\n            )'''
new = '''score_snapshot[asset] = build_dynamic_score(\n                f"{asset}/USDT",\n                direction,\n                signal_record.get("feature_records"),\n                structural_state,\n                regime_data,\n            )'''

count = fixed.count(old)
assert count == 1, f"targeted Score block count={count}, expected 1"
fixed = fixed.replace(old, new, 1)

ast.parse(fixed, filename=str(OUT))
compile(fixed, str(OUT), "exec")
OUT.write_text(fixed, encoding="utf-8", newline="")

print("SOURCE=origin/main")
print("DUPLICATE_NESTED_BLOCK_REMOVED=TRUE")
print("SCORE_FEATURE_RECORDS_FIXED=TRUE")
print("AST=PASS")
print("COMPILE=PASS")
print(f"OUTPUT={OUT}")
print("ORIGINAL_OVERWRITTEN=FALSE")
print("RUNTIME_EXECUTED=FALSE")
