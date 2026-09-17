# -*- coding: utf-8 -*-
"""
ARUNDA TRADER — BUILD_SIGNAL RUNTIME FORENSIC TRACE
READ ONLY / NO SYNTHETIC DATA / NO DB WRITE / NO ORDER
"""

import inspect
import sqlite3
import signal_engine

DB = r"C:\Users\ASUS\ArundaTrader\arunda.db"


def main():
    print("=" * 82)
    print("ARUNDA TRADER — BUILD_SIGNAL RUNTIME TRACE")
    print("=" * 82)

    print(f"BUILD_SIGNAL : {inspect.getsourcefile(signal_engine.build_signal)}")
    print(f"LINE         : {inspect.getsourcelines(signal_engine.build_signal)[1]}")
    print("MODE         : READ ONLY")
    print("SYNTHETIC    : NO")
    print("DB WRITE     : NO")
    print("ORDER        : NO")
    print()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT *
        FROM fusion_signals
        WHERE engine_version = 'FUSION_v0.5'
        ORDER BY timestamp DESC, id DESC
        LIMIT 4
    """).fetchall()

    conn.close()

    print("CURRENT SIGNALS")

    for r in rows:
        asset = r["asset"]
        direction = r["direction"]

        print("-" * 82)
        print(
            f"{asset:5} "
            f"direction={direction} "
            f"fused={r['fused_score']:.2f} "
            f"confidence={r['confidence']:.3f} "
            f"strength={r['signal_strength']} "
            f"quality={r['data_quality']}"
        )

        # First obvious runtime gate
        if direction not in ("LONG", "SHORT"):
            print(f"FAILURE: direction={direction}")
            continue

        print("BUILD_SIGNAL INPUT: ELIGIBLE_DIRECTION")

        # Trace actual function contract
        try:
            sig = inspect.signature(signal_engine.build_signal)

            print(
                "BUILD_SIGNAL CONTRACT:",
                ", ".join(sig.parameters.keys())
            )

        except Exception as e:
            print("BUILD_SIGNAL CONTRACT ERROR:", e)

        print("RESULT: NO FAILURE OBSERVED AT INPUT BOUNDARY")

    print("-" * 82)
    print("TRACE COMPLETE")
    print("REPAIR: NONE")
    print("DB WRITE: NONE")
    print("FRONTIER: LIVE_SIGNAL_ORDER_INTENT_VALIDATION_CONTRACT_REPAIR")
    print("=" * 82)


if __name__ == "__main__":
    main()