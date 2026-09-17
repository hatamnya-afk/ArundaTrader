from pathlib import Path

p = Path("fusion_engine.py")

# Read raw text and remove UTF-8 BOM
text = p.read_text(encoding="utf-8-sig")

# Fix accidental quoted function block created by the previous patch
text = text.replace(
    "'def get_latest_market(conn, asset):",
    "def get_latest_market(conn, asset):"
)

# Remove the closing quote if the accidental block was closed with a lone quote.
lines = text.splitlines(keepends=True)

out = []
inside_fix = False

for line in lines:
    stripped = line.strip()

    if stripped == "'":
        # Remove only a lone quote accidentally inserted by the patch.
        continue

    out.append(line)

text = "".join(out)

# Remove any remaining BOM just in case
text = text.replace("\ufeff", "")

# Normalize line endings
text = text.replace("\r\n", "\n").replace("\r", "\n")

# Write clean UTF-8 without BOM
p.write_text(text, encoding="utf-8", newline="\n")

# Verify syntax
compile(text, str(p), "exec")

print("============================================================")
print("FUSION ENGINE REPAIR")
print("============================================================")
print("File    :", p.resolve())
print("STATUS  : SYNTAX OK")
print("BOM     : REMOVED")
print("============================================================")
