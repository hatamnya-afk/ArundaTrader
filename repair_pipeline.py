from pathlib import Path
import re

path = Path("arunda_pipeline.py")
lines = path.read_text(encoding="utf-8-sig").splitlines()

out = []
i = 0

def indent_of(s):
    return len(s) - len(s.lstrip(" "))

def is_top_level_def(s):
    return re.match(r"^(def|class)\s+", s.strip()) is not None

while i < len(lines):
    line = lines[i]
    stripped = line.strip()

    # Skip markdown fences accidentally embedded in Python
    if stripped == "```":
        i += 1
        continue

    # Repair future/file/main corruption
    line = line.replace("from **future** import annotations",
                        "from __future__ import annotations")
    line = line.replace("Path(**file**)", "Path(__file__)")
    line = line.replace('**name** == "**main**"',
                        '__name__ == "__main__"')

    # Top-level def/class
    if indent_of(line) == 0 and re.match(r"^(def|class)\s+", stripped):
        out.append(line)
        base = 0
        i += 1

        # Process everything belonging to this block.
        while i < len(lines):
            raw = lines[i]
            s = raw.strip()

            if s == "```":
                i += 1
                continue

            if indent_of(raw) == 0 and re.match(r"^(def|class)\s+", s):
                break

            # blank
            if not s:
                out.append("")
                i += 1
                continue

            # Existing indentation inside the function/class.
            # The original file lost one indentation level.
            out.append("    " + raw)
            i += 1

        continue

    out.append(line)
    i += 1

path.write_text("\n".join(out) + "\n", encoding="utf-8")
print("INDENTATION REPAIR APPLIED")
print("LINES:", len(out))
