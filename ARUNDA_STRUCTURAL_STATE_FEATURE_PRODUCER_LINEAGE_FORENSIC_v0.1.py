from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = PROJECT_ROOT / "market_regime.py"

START_LINE = 130
END_LINE = 205

print("=" * 100)
print("ARUNDA TRADER — STRUCTURAL STATE FEATURE PRODUCER LINEAGE FORENSIC v0.1")
print("=" * 100)
print(f"PROJECT ROOT : {PROJECT_ROOT}")
print(f"TARGET       : {TARGET}")
print("MODE         : READ ONLY STATIC SOURCE INSPECTION")
print("DATABASE     : NONE")
print("WRITE        : NONE")
print("EXECUTION    : NONE")
print("SOURCE MUTATION : NONE")
print("=" * 100)

if not TARGET.exists():
    print()
    print("TARGET FILE NOT FOUND")
    raise SystemExit(1)

lines = TARGET.read_text(encoding="utf-8").splitlines()

print()
print("=" * 100)
print(f"TARGET SOURCE CONTEXT : lines {START_LINE}-{END_LINE}")
print("=" * 100)

for number in range(
    START_LINE,
    min(END_LINE, len(lines)) + 1,
):
    print(
        f"{number:5} | {lines[number - 1]}"
    )

print()
print("=" * 100)
print("LOAD_STRUCTURAL_STATE REFERENCES")
print("=" * 100)

for number, line in enumerate(lines, 1):
    if "load_structural_state" in line:
        print(
            f"{number:5} | {line}"
        )

print()
print("=" * 100)
print("STRUCTURAL STATE CONSTRUCTION REFERENCES")
print("=" * 100)

keywords = (
    "structural_state",
    "structure_state",
    "structural",
)

for number, line in enumerate(lines, 1):
    if any(
        keyword in line
        for keyword in keywords
    ):
        print(
            f"{number:5} | {line}"
        )

print()
print("=" * 100)
print("PRODUCER LINEAGE TARGET")
print("=" * 100)

print(
    "QUESTION:"
)
print(
    "What code produces the object returned by "
    "load_structural_state()?"
)

print()
print(
    "NEXT REPAIR DECISION:"
)
print(
    "Do NOT modify build_structure()."
)
print(
    "Do NOT create a mapping."
)
print(
    "Do NOT synthesize missing fields."
)
print(
    "Identify the actual producer contract first."
)

print()
print("=" * 100)
print("SAFETY ASSERTION")
print("=" * 100)

print("DATABASE ACCESS : False")
print("DATABASE WRITE  : False")
print("FILE WRITE      : False")
print("SOURCE MUTATION : False")
print("EXECUTION       : False")
print("NETWORK         : False")
print("=" * 100)