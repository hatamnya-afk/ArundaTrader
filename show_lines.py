from pathlib import Path

path = Path(
    r"C:\Users\ASUS\ArundaTrader\FIND_FUTURE_PRICE_COMPARE_OP_RUNTIME_OPERAND_RESULT_FORENSIC_AUDIT_v0.1.py"
)

start = 545
end = 575

print("=" * 100)
print(f"FILE : {path}")
print(f"LINES: {start}-{end}")
print("=" * 100)

with path.open(
    "r",
    encoding="utf-8",
    errors="replace",
) as f:

    lines = f.readlines()

for number in range(
    start,
    min(end, len(lines)) + 1,
):

    print(
        f"{number:5d} | {lines[number - 1].rstrip()}"
    )

print("=" * 100)