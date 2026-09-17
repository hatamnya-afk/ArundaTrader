import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")
TABLE = "market_history"


def parse_timestamp(value):
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except Exception:
        return None


def main():

    print("=" * 100)
    print("ARUNDA TRADER — HISTORY WRITER BATCH FINGERPRINT AUDIT v0.1")
    print("=" * 100)

    print("MODE              : READ ONLY")
    print("DATABASE          :", DB_PATH)
    print("WRITE OPERATIONS  : NONE")
    print("INSERT            : NONE")
    print("UPDATE            : NONE")
    print("DELETE            : NONE")
    print("ALTER             : NONE")
    print("CREATE            : NONE")
    print()

    if not DB_PATH.exists():
        print("ERROR: DATABASE NOT FOUND")
        print(DB_PATH)
        return

    # SQLite read-only connection
    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True
    )

    try:

        exists = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type='table'
              AND name=?
            """,
            (TABLE,),
        ).fetchone()

        if not exists:
            print("ERROR: market_history table not found")
            return

        # ---------------------------------------------------------
        # GLOBAL DATABASE
        # ---------------------------------------------------------

        total_rows = conn.execute(
            "SELECT COUNT(*) FROM market_history"
        ).fetchone()[0]

        distinct_assets = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM market_history"
        ).fetchone()[0]

        # ---------------------------------------------------------
        # SNAPSHOT BATCHES
        # ---------------------------------------------------------

        batches = conn.execute(
            """
            SELECT
                timestamp,
                COUNT(*) AS row_count,
                COUNT(DISTINCT symbol) AS symbol_count,
                MIN(id) AS min_id,
                MAX(id) AS max_id
            FROM market_history
            WHERE timestamp IS NOT NULL
            GROUP BY timestamp
            ORDER BY timestamp
            """
        ).fetchall()

        print("=" * 100)
        print("DATABASE FINGERPRINT")
        print("=" * 100)

        print(f"Total Rows          : {total_rows:,}")
        print(f"Distinct Assets     : {distinct_assets:,}")
        print(f"Snapshot Batches    : {len(batches):,}")

        if not batches:
            print()
            print("VERDICT             : REJECTED")
            print("Reason              : No timestamp batches found.")
            return

        # ---------------------------------------------------------
        # BATCH SIZE ANALYSIS
        # ---------------------------------------------------------

        batch_sizes = [
            row[1]
            for row in batches
        ]

        print()
        print("-" * 100)
        print("BATCH SIZE ANALYSIS")
        print("-" * 100)

        print(f"Minimum Batch       : {min(batch_sizes):,}")
        print(f"Maximum Batch       : {max(batch_sizes):,}")
        print(
            f"Average Batch       : "
            f"{sum(batch_sizes) / len(batch_sizes):.2f}"
        )

        exact_987 = sum(
            1
            for size in batch_sizes
            if size == 987
        )

        ge_950 = sum(
            1
            for size in batch_sizes
            if size >= 950
        )

        ge_900 = sum(
            1
            for size in batch_sizes
            if size >= 900
        )

        print(f"Exactly 987         : {exact_987:,}")
        print(f">= 950              : {ge_950:,}")
        print(f">= 900              : {ge_900:,}")

        # ---------------------------------------------------------
        # TEMPORAL ANALYSIS
        # ---------------------------------------------------------

        timestamps = []

        for row in batches:

            dt = parse_timestamp(row[0])

            if dt is not None:
                timestamps.append(dt)

        deltas = []

        for previous, current in zip(
            timestamps,
            timestamps[1:]
        ):

            delta = (
                current - previous
            ).total_seconds()

            deltas.append(delta)

        print()
        print("-" * 100)
        print("TEMPORAL ANALYSIS")
        print("-" * 100)

        print(
            "First Snapshot      :",
            batches[0][0]
        )

        print(
            "Last Snapshot       :",
            batches[-1][0]
        )

        if deltas:

            near_60 = sum(
                1
                for delta in deltas
                if 50 <= delta <= 70
            )

            print(
                f"Interval Minimum    : "
                f"{min(deltas):.2f} sec"
            )

            print(
                f"Interval Maximum    : "
                f"{max(deltas):.2f} sec"
            )

            print(
                f"Interval Average    : "
                f"{sum(deltas) / len(deltas):.2f} sec"
            )

            print(
                f"50-70 sec intervals : "
                f"{near_60:,}/{len(deltas):,}"
            )

            interval_ratio = (
                near_60 / len(deltas)
            )

        else:

            interval_ratio = 0

            print(
                "Interval Data       : INSUFFICIENT"
            )

        # ---------------------------------------------------------
        # 987 × BATCH FINGERPRINT
        # ---------------------------------------------------------

        expected_987 = (
            len(batches) * 987
        )

        difference = (
            total_rows - expected_987
        )

        print()
        print("-" * 100)
        print("987-ASSET FINGERPRINT")
        print("-" * 100)

        print(
            f"Observed Rows       : {total_rows:,}"
        )

        print(
            f"Batches             : {len(batches):,}"
        )

        print(
            f"987 × Batches       : {expected_987:,}"
        )

        print(
            f"Difference          : {difference:,}"
        )

        # ---------------------------------------------------------
        # REPRESENTATIVE BATCHES
        # ---------------------------------------------------------

        indexes = sorted(
            set(
                [
                    0,
                    len(batches) // 4,
                    len(batches) // 2,
                    (len(batches) * 3) // 4,
                    len(batches) - 1,
                ]
            )
        )

        print()
        print("-" * 100)
        print("REPRESENTATIVE SNAPSHOTS")
        print("-" * 100)

        for index in indexes:

            timestamp, rows, symbols, min_id, max_id = (
                batches[index]
            )

            print(
                f"{index + 1:>5} | "
                f"{timestamp} | "
                f"rows={rows:<5} | "
                f"symbols={symbols:<5} | "
                f"id={min_id}-{max_id}"
            )

        # ---------------------------------------------------------
        # FINAL FORENSIC VERDICT
        # ---------------------------------------------------------

        size_ratio = (
            ge_900 / len(batch_sizes)
        )

        strong_size = (
            len(batches) >= 600
            and size_ratio >= 0.90
        )

        strong_interval = (
            len(deltas) >= 100
            and interval_ratio >= 0.90
        )

        total_tolerance = max(
            987 * 20,
            int(total_rows * 0.03)
        )

        strong_total = (
            abs(difference)
            <= total_tolerance
        )

        print()
        print("=" * 100)
        print("FORENSIC VERDICT")
        print("=" * 100)

        print(
            "Large Batches       :",
            "MATCH" if strong_size else "NO MATCH"
        )

        print(
            "~60 Second Loop     :",
            "MATCH" if strong_interval else "NO MATCH"
        )

        print(
            "987 Asset Fingerprint:",
            "MATCH" if strong_total else "NO MATCH"
        )

        print()

        if (
            strong_size
            and strong_interval
            and strong_total
        ):

            print(
                "VERDICT             : "
                "CONFIRMED / STRONGLY CONSISTENT"
            )

            print()
            print(
                "The market_history database pattern is "
                "strongly consistent with a recurring "
                "full-universe writer operating at "
                "approximately 60-second intervals."
            )

        elif (
            strong_size
            or strong_interval
        ):

            print(
                "VERDICT             : "
                "STRONGLY CONSISTENT"
            )

            print()
            print(
                "Major writer fingerprint components "
                "match, but full confirmation is not "
                "established."
            )

        else:

            print(
                "VERDICT             : "
                "NOT CONFIRMED"
            )

            print()
            print(
                "The observed database pattern does not "
                "sufficiently match the expected writer."
            )

        print()
        print("=" * 100)
        print("AUDIT COMPLETE — DATABASE PRESERVED")
        print("=" * 100)

    finally:

        conn.close()


if __name__ == "__main__":
    main()