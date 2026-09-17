from pathlib import Path
import shutil

T = Path(r"C:\Users\ASUS\ArundaTrader\arunda_pipeline.py")
B = Path(r"C:\Users\ASUS\ArundaTrader\arunda_pipeline.py.alignment_backup")

S = T.read_text(encoding="utf-8")
compile(S, str(T), "exec")

if "opportunity_signal_alignment_v0_1" in S:
    raise SystemExit("ALIGNMENT_ALREADY_PRESENT")

main_pos = S.rfind("def main(")
if main_pos < 0:
    raise SystemExit("MAIN_NOT_FOUND")

anchor = '''        opportunity_rows = (
            opportunity_snapshot["opportunities"]
        )
'''

positions = []
p = 0
while True:
    p = S.find(anchor, p)
    if p < 0:
        break
    positions.append(p)
    p += 1

positions = [p for p in positions if p > main_pos]

if len(positions) != 1:
    raise SystemExit(
        f"OPPORTUNITY_ANCHOR_COUNT={len(positions)}"
    )

pos = positions[0]

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
            fail("RAW_OPPORTUNITY_ROWS_INVALID")

        raw_opportunity_map = {}

        for opportunity in raw_opportunity_rows:

            if not isinstance(
                opportunity,
                dict,
            ):
                fail("RAW_OPPORTUNITY_RECORD_INVALID")

            asset = str(
                opportunity.get("asset", "")
            ).strip().upper()

            if not asset:
                fail("RAW_OPPORTUNITY_ASSET_MISSING")

            if asset in raw_opportunity_map:
                fail(
                    f"DUPLICATE_RAW_OPPORTUNITY={asset}"
                )

            raw_opportunity_map[asset] = opportunity

        expected_assets = {
            "BTC", "ETH", "SOL", "XRP", "ADA",
            "DOGE", "SHIB", "LINK", "AVAX", "DOT",
            "LTC", "UNI", "AAVE", "SUI", "NEAR",
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
                "BTC", "ETH", "SOL", "XRP", "ADA",
                "DOGE", "SHIB", "LINK", "AVAX", "DOT",
                "LTC", "UNI", "AAVE", "SUI", "NEAR",
            )
        ]

        print("OPPORTUNITY_SIGNAL_ALIGNMENT=PASS")
        print(
            f"RAW_OPPORTUNITY_ROWS={len(raw_opportunity_rows)}"
        )
        print(
            f"ALIGNED_OPPORTUNITY_ROWS={len(opportunity_rows)}"
        )
        print("DIRECTION_OVERRIDE=FALSE")
        print("THRESHOLD_MUTATION=FALSE")
'''

P = S[:pos] + replacement + S[pos + len(anchor):]

gate = '''        gate_results = (
            trade_gate_engine.run_runtime(
                opportunity_rows,
                decision_snapshot,
                risk_snapshot,
            )
        )
'''

gpos = P.rfind(gate)

if gpos < main_pos:
    raise SystemExit("TRADE_GATE_ANCHOR_NOT_FOUND")

guard = '''        if opportunity_rows is raw_opportunity_rows:
            fail("RAW OPPORTUNITY LEAKED INTO TRADE GATE")

        gate_results = (
            trade_gate_engine.run_runtime(
                opportunity_rows,
                decision_snapshot,
                risk_snapshot,
            )
        )
'''

P = P[:gpos] + guard + P[gpos + len(gate):]

if P.count(
    "opportunity_signal_alignment_v0_1.align_snapshot("
) != 1:
    raise SystemExit("ALIGNMENT_CALL_COUNT_INVALID")

compile(P, str(T), "exec")

shutil.copy2(T, B)

tmp = T.with_suffix(".alignment_tmp.py")

try:
    tmp.write_text(
        P,
        encoding="utf-8",
        newline="",
    )

    compile(
        tmp.read_text(encoding="utf-8"),
        str(tmp),
        "exec",
    )

    tmp.replace(T)

    compile(
        T.read_text(encoding="utf-8"),
        str(T),
        "exec",
    )

except Exception:

    if tmp.exists():
        tmp.unlink()

    shutil.copy2(B, T)
    raise

print("=" * 70)
print("PATCH_PASS")
print("COMPILE_PASS")
print("BACKUP_CREATED")
print("ALIGNMENT_BOUNDARY_INSERTED")
print("RAW_OPPORTUNITY_LEAK_GUARD_INSERTED")
print("=" * 70)