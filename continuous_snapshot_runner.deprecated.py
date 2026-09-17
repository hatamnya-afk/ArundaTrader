import time

import market_snapshot_engine


# ============================================================
# ARUNDA SNAPSHOT CONTINUITY RUNNER v0.1
# ============================================================
#
# PURPOSE
# -------
# Repeatedly execute the existing real Snapshot Producer.
#
# IMPORTANT
# ---------
# This runner does NOT:
#
# - fetch market data itself
# - modify Snapshot logic
# - calculate indicators
# - generate signals
# - rank assets
# - calculate risk
# - execute trades
# - manufacture data
#
# It only orchestrates repeated execution of:
#
#     market_snapshot_engine.main()
#
# ============================================================


# ============================================================
# CONFIG
# ============================================================

CYCLE_INTERVAL_SECONDS = 60


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 78)
    print("       ARUNDA SNAPSHOT CONTINUITY RUNNER v0.1")
    print("=" * 78)

    print(
        f"Cycle interval : {CYCLE_INTERVAL_SECONDS} seconds"
    )

    print(
        "Producer       : market_snapshot_engine.main()"
    )

    print(
        "Mode           : REAL SNAPSHOT COLLECTION"
    )

    print("=" * 78)

    cycle = 0

    while True:

        cycle += 1

        started = time.perf_counter()

        print()
        print("=" * 78)
        print(
            f"SNAPSHOT CYCLE #{cycle}"
        )
        print("=" * 78)

        try:

            result = (
                market_snapshot_engine.main()
            )

            elapsed = (
                time.perf_counter()
                - started
            )

            print()
            print(
                f"CYCLE #{cycle} COMPLETE | "
                f"RESULT={result} | "
                f"ELAPSED={elapsed:.2f}s"
            )

        except KeyboardInterrupt:

            print()
            print("=" * 78)
            print(
                "SNAPSHOT CONTINUITY STOPPED BY USER"
            )
            print("=" * 78)

            return 0

        except Exception as exc:

            elapsed = (
                time.perf_counter()
                - started
            )

            print()
            print("=" * 78)
            print(
                f"CYCLE #{cycle} ERROR"
            )
            print(
                f"{type(exc).__name__}: {exc}"
            )
            print(
                f"Elapsed: {elapsed:.2f}s"
            )
            print(
                "CONTINUITY ACTION: WAIT AND RETRY"
            )
            print("=" * 78)

        print()
        print(
            f"Waiting {CYCLE_INTERVAL_SECONDS} seconds "
            "before next snapshot cycle..."
        )

        try:

            time.sleep(
                CYCLE_INTERVAL_SECONDS
            )

        except KeyboardInterrupt:

            print()
            print("=" * 78)
            print(
                "SNAPSHOT CONTINUITY STOPPED BY USER"
            )
            print("=" * 78)

            return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )