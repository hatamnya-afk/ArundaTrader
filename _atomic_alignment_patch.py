from pathlib import Path
import py_compile
import shutil
import sys

TARGET = Path(r"C:\Users\ASUS\ArundaTrader\arunda_pipeline.py")
BACKUP = Path(r"C:\Users\ASUS\ArundaTrader\arunda_pipeline.py.alignment_backup")

text = TARGET.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# PRE-CHECK
# ---------------------------------------------------------------------------

compile(text, str(TARGET), "exec")

if "opportunity_signal_alignment_v0_1" in text:
    raise RuntimeError("ALIGNMENT_ALREADY_PRESENT")

if "raw_opportunity_rows" in text:
    raise RuntimeError("RAW_OPPORTUNITY_SYMBOL_ALREADY_PRESENT")

# ---------------------------------------------------------------------------
# FIND MAIN() OPPORTUNITY BIND
# ---------------------------------------------------------------------------

main_pos = text.rfind("def main(")

if main_pos < 0:
    raise RuntimeError("MAIN_FUNCTION_NOT_FOUND")

anchor = '''        opportunity_rows = (
            opportunity_snapshot["opportunities"]
        )
'''

positions = []
start = 0

while True:
    p = text.find(anchor, start)
    if p < 0:
        break
    positions.append(p)
    start = p + 1

valid = [p for p in positions if p > main_pos]

if len(valid) != 1:
    raise RuntimeError(
        f"MAIN_OPPORTUNITY_ANCHOR_COUNT={len(valid)}"
    )

opp_pos = valid[0]

# ---------------------------------------------------------------------------
# ALIGNMENT BOUNDARY
# ---------------------------------------------------------------------------

replacement = '''        # ------------------------------------------------------------------------
        # OPPORTUNITY <-> SIGNAL ALIGNMENT BOUNDARY
        # ------------------------------------------------------------------------

        import opportunity_signal_alignment_v0_1

        raw_opportunity_rows = (
            opportunity_snapshot["opportunities"]
        )

        if not isinstance(
            raw_opportunity_rows,
            (list, tuple),
        ):
            fail(
                "RAW_OPPORTUNITY_ROWS_INVALID"
            )

        raw_opportunity_map = {}

        for opportunity in raw_opportunity_rows:

            if not isinstance(
                opportunity,
                dict,
            ):
                fail(
                    "RAW_OPPORTUNITY_RECORD_INVALID"
                )

            asset = str(
                opportunity.get("asset", "")
            ).strip().upper()

            if not asset:
                fail(
                    "RAW_OPPORTUNITY_ASSET_MISSING"
                )

            if asset in raw_opportunity_map:
                fail(
                    f"DUPLICATE_RAW_OPPORTUNITY={asset}"
                )

            raw_opportunity_map[asset] = opportunity

        expected_assets = {
            "BTC",
            "ETH",
            "SOL",
            "XRP",
            "ADA",
            "DOGE",
            "SHIB",
            "LINK",
            "AVAX",
            "DOT",
            "LTC",
            "UNI",
            "AAVE",
            "SUI",
            "NEAR",
        }

        if set(raw_opportunity_map) != expected_assets:
            fail(
                "RAW_OPPORTUNITY_ASSET_COVERAGE_MISMATCH"
            )

        alignment_snapshot = (
            opportunity_signal_alignment_v0_1.align_snapshot(
                raw_opportunity_map,
                validated_signals,
            )
        )

        opportunity_signal_alignment_v0_1.validate_aligned_snapshot(
            alignment_snapshot,
            validated_signals,
        )

        if set(alignment_snapshot) != expected_assets:
            fail(
                "ALIGNED_OPPORTUNITY_ASSET_COVERAGE_MISMATCH"
            )

        opportunity_rows = [
            alignment_snapshot[asset]
            for asset in (
                "BTC",
                "ETH",
                "SOL",
                "XRP",
                "ADA",
                "DOGE",
                "SHIB",
                "LINK",
                "AVAX",
                "DOT",
                "LTC",
                "UNI",
                "AAVE",
                "SUI",
                "NEAR",
            )
        ]

        print()
        print(
            "OPPORTUNITY_SIGNAL_ALIGNMENT=PASS"
        )
        print(
            "RAW_OPPORTUNITY_ROWS="
            f"{len(raw_opportunity_rows)}"
        )
        print(
            "ALIGNED_OPPORTUNITY_ROWS="
            f"{len(opportunity_rows)}"
        )
        print(
            "DIRECTION_OVERRIDE=FALSE"
        )
        print(
            "THRESHOLD_MUTATION=FALSE"
        )
        print(
            "DB_WRITES=0"
        )
        print(
            "EXECUTION=OFF"
        )
'''

patched = (
    text[:opp_pos]
    + replacement
    + text[opp_pos + len(anchor):]
)

# ---------------------------------------------------------------------------
# FIND MAIN() TRADE GATE
# ---------------------------------------------------------------------------

gate_anchor = '''        gate_results = (
            trade_gate_engine.run_runtime(
                opportunity_rows,
                decision_snapshot,
                risk_snapshot,
            )
        )
'''

gate_positions = []
start = main_pos

while True:
    p = patched.find(gate_anchor, start)
    if p < 0:
        break
    gate_positions.append(p)
    start = p + 1

if len(gate_positions) != 1:
    raise RuntimeError(
        f"MAIN_TRADE_GATE_ANCHOR_COUNT={len(gate_positions)}"
    )

gate_pos = gate_positions[0]

gate_replacement = '''        # ------------------------------------------------------------------------
        # HARD RAW-OPPORTUNITY LEAK GUARD
        # ------------------------------------------------------------------------

        if opportunity_rows is raw_opportunity_rows:
            fail(
                "RAW OPPORTUNITY LEAKED INTO TRADE GATE"
            )

        gate_results = (
            trade_gate_engine.run_runtime(
                opportunity_rows,
                decision_snapshot,
                risk_snapshot,
            )
        )
'''

patched = (
    patched[:gate_pos]
    + gate_replacement
    + patched[gate_pos + len(gate_anchor):]
)

# ---------------------------------------------------------------------------
# STRUCTURAL CHECKS BEFORE WRITE
# ---------------------------------------------------------------------------

if "opportunity_signal_alignment_v0_1" not in patched:
    raise RuntimeError("ALIGNMENT_IMPORT_NOT_INSERTED")

if "raw_opportunity_rows" not in patched:
    raise RuntimeError("RAW_OPPORTUNITY_BIND_NOT_INSERTED")

if "RAW OPPORTUNITY LEAKED INTO TRADE GATE" not in patched:
    raise RuntimeError("RAW_LEAK_GUARD_NOT_INSERTED")

if patched.count(
    "opportunity_signal_alignment_v0_1.align_snapshot("
) != 1:
    raise RuntimeError(
        "ALIGNMENT_CALL_COUNT_INVALID"
    )

# Compile patched source BEFORE touching target.
compile(
    patched,
    str(TARGET),
    "exec",
)

# ---------------------------------------------------------------------------
# ATOMIC BACKUP + WRITE
# ---------------------------------------------------------------------------

shutil.copy2(TARGET, BACKUP)

tmp = TARGET.with_suffix(".alignment_tmp.py")

try:

    tmp.write_text(
        patched,
        encoding="utf-8",
        newline="",
    )

    compile(
        tmp.read_text(encoding="utf-8"),
        str(tmp),
        "exec",
    )

    tmp.replace(TARGET)

    # Final real-target compile.
    compile(
        TARGET.read_text(encoding="utf-8"),
        str(TARGET),
        "exec",
    )

except Exception:

    if tmp.exists():
        tmp.unlink()

    if BACKUP.exists():
        shutil.copy2(BACKUP, TARGET)

    raise

print()
print("=" * 80)
print("PATCH_PASS")
print("=" * 80)
print("ALIGNMENT_BOUNDARY=INSERTED")
print("RAW_OPPORTUNITY_LEAK_GUARD=INSERTED")
print("BACKUP=CREATED")
print("COMPILE=PASS")
print("=" * 80)
