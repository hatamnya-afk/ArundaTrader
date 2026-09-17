import subprocess
import sys
import time
from datetime import datetime, timezone

ENGINE_SCRIPT = "market_snapshot_engine.py"
INTERVAL_SECONDS = 300
ENGINE_TIMEOUT_SECONDS = 120

SCHEDULER_VERSION = "MARKET_SNAPSHOT_SCHEDULER_v0.1"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def print_header():
    print("=" * 78)
    print("             ARUNDA MARKET SNAPSHOT SCHEDULER v0.1")
    print("=" * 78)
    print(f"Engine          : {ENGINE_SCRIPT}")
    print(f"Interval        : {INTERVAL_SECONDS} seconds")
    print(f"Interval        : {INTERVAL_SECONDS / 60:.0f} minutes")
    print("Mode            : PERIODIC COLLECTION")
    print("Provider        : COINMARKETCAP")
    print("Analysis        : NOT USED")
    print("Signal          : NOT USED")
    print("Risk            : NOT USED")
    print("Execution       : NOT USED")
    print("Prediction      : NOT USED")
    print("Ranking         : NOT USED")
    print("Database        : HANDLED BY SNAPSHOT ENGINE")
    print("=" * 78)


def print_status(message):
    print(
        f"[{utc_now()}] {message}",
        flush=True
    )


def run_snapshot_engine():

    print()
    print("-" * 78)

    print_status(
        "Starting market_snapshot_engine.py"
    )

    print("-" * 78)

    started = time.perf_counter()

    try:

        result = subprocess.run(
            [
                sys.executable,
                ENGINE_SCRIPT
            ],
            timeout=ENGINE_TIMEOUT_SECONDS
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        if result.returncode == 0:

            print()
            print_status(
                f"Snapshot engine SUCCESS | "
                f"Runtime {elapsed:.2f} sec"
            )

            return True

        print()
        print_status(
            f"Snapshot engine FAILED | "
            f"Exit Code {result.returncode}"
        )

        return False

    except subprocess.TimeoutExpired:

        print()
        print_status(
            "Snapshot engine TIMEOUT"
        )

        return False

    except FileNotFoundError:

        print()
        print_status(
            f"ENGINE NOT FOUND: {ENGINE_SCRIPT}"
        )

        return False

    except Exception as exc:

        print()
        print_status(
            f"ENGINE ERROR: {repr(exc)}"
        )

        return False


def wait_for_next_cycle():

    print()
    print("-" * 78)

    print_status(
        f"Waiting {INTERVAL_SECONDS} seconds "
        f"for next snapshot cycle..."
    )

    print(
        "Press Ctrl+C to stop."
    )

    print("-" * 78)

    for remaining in range(
        INTERVAL_SECONDS,
        0,
        -1
    ):

        time.sleep(1)

        if remaining % 60 == 0:

            print_status(
                f"Next cycle in "
                f"{remaining - 1} seconds"
            )


def main():

    print()
    print_header()

    print_status(
        "Scheduler initialized."
    )

    print_status(
        "Continuous snapshot collection ACTIVE."
    )

    print_status(
        "Trading logic DISABLED."
    )

    runs = 0
    successful = 0
    failed = 0

    try:

        while True:

            runs += 1

            print()
            print("=" * 78)
            print(
                f"SNAPSHOT CYCLE #{runs}"
            )
            print(
                f"Time : {utc_now()}"
            )
            print("=" * 78)

            success = run_snapshot_engine()

            if success:

                successful += 1

            else:

                failed += 1

            print()
            print("=" * 78)
            print("SCHEDULER STATUS")
            print("=" * 78)

            print(
                f"Total Runs      : {runs}"
            )

            print(
                f"Successful      : {successful}"
            )

            print(
                f"Failed          : {failed}"
            )

            print(
                f"Interval        : "
                f"{INTERVAL_SECONDS / 60:.0f} minutes"
            )

            print(
                "Market Scope    : 15 TEST ASSETS"
            )

            print(
                "Universe Mode   : EXTENSIBLE"
            )

            print(
                "Analysis        : NOT USED"
            )

            print(
                "Signal          : NOT USED"
            )

            print(
                "Risk            : NOT USED"
            )

            print(
                "Execution       : NOT USED"
            )

            print("=" * 78)

            wait_for_next_cycle()

    except KeyboardInterrupt:

        print()
        print()
        print("=" * 78)
        print(
            "       ARUNDA SNAPSHOT SCHEDULER STOPPED"
        )
        print("=" * 78)

        print(
            f"Total Runs      : {runs}"
        )

        print(
            f"Successful      : {successful}"
        )

        print(
            f"Failed          : {failed}"
        )

        print(
            "Reason          : USER INTERRUPT"
        )

        print(
            "Database        : PRESERVED"
        )

        print("=" * 78)

        return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
