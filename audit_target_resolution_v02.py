import sqlite3


DB = "arunda.db"

ANALYSIS_SOURCE = "CMC_SNAPSHOT_ANALYSIS_v0.2"
SNAPSHOT_SOURCE = "COINMARKETCAP"
TIMEFRAME = "SNAPSHOT"

LOOKBACK = 120
MIN_HISTORY = 60

SYMBOLS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
]


def connect_database():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def find_analysis_target(conn, symbol):
    return conn.execute(
        """
        SELECT
            id,
            timestamp,
            source_timestamp,
            close,
            technical_score,
            engine_version
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            symbol,
            ANALYSIS_SOURCE,
            TIMEFRAME,
        ),
    ).fetchone()


def find_raw_target(conn, symbol, source_timestamp):
    return conn.execute(
        """
        SELECT
            id,
            timestamp,
            source_timestamp,
            close,
            volume
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = ?
            AND source_timestamp = ?
        ORDER BY id ASC
        LIMIT 1
        """,
        (
            symbol,
            SNAPSHOT_SOURCE,
            TIMEFRAME,
            source_timestamp,
        ),
    ).fetchone()


def get_raw_window(
    conn,
    symbol,
    target_source_timestamp,
    limit,
):
    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            source_timestamp,
            close,
            volume
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = ?
            AND source_timestamp <= ?
            AND close IS NOT NULL
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            symbol,
            SNAPSHOT_SOURCE,
            TIMEFRAME,
            target_source_timestamp,
            limit,
        ),
    ).fetchall()

    return list(reversed(rows))


def print_line():
    print("=" * 100)


def main():

    print_line()
    print("ARUNDA TARGET RESOLUTION AUDIT v0.3")
    print_line()

    print("MODE              : READ ONLY")
    print(f"DATABASE          : {DB}")
    print(f"ANALYSIS SOURCE   : {ANALYSIS_SOURCE}")
    print(f"SNAPSHOT SOURCE   : {SNAPSHOT_SOURCE}")
    print(f"TIMEFRAME         : {TIMEFRAME}")
    print(f"LOOKBACK          : {LOOKBACK}")
    print(f"MIN HISTORY       : {MIN_HISTORY}")
    print("LOOKBACK STATUS   : WINDOW SIZE ONLY")
    print("FORMULA STATUS    : NOT CALCULATED")

    print_line()

    conn = None

    exact_count = 0
    ready_count = 0
    blocked_count = 0

    try:

        conn = connect_database()

        for symbol in SYMBOLS:

            print()
            print_line()
            print(f"SYMBOL : {symbol}")
            print("-" * 100)

            # ------------------------------------------------
            # ANALYSIS TARGET
            # ------------------------------------------------

            analysis = find_analysis_target(
                conn,
                symbol,
            )

            if analysis is None:

                print("ANALYSIS TARGET : NOT FOUND")
                print("TARGET STATUS   : BLOCKED")
                print("REASON          : ANALYSIS_TARGET_NOT_FOUND")

                blocked_count += 1
                continue

            print("ANALYSIS TARGET : FOUND")
            print(f"Analysis ID     : {analysis['id']}")
            print(f"Analysis Time   : {analysis['timestamp']}")
            print(f"Source Time     : {analysis['source_timestamp']}")
            print(f"Stored Close    : {analysis['close']}")
            print(f"Stored Score    : {analysis['technical_score']}")
            print(f"Engine Version  : {analysis['engine_version']}")

            # ------------------------------------------------
            # RAW TARGET
            # ------------------------------------------------

            raw = find_raw_target(
                conn,
                symbol,
                analysis["source_timestamp"],
            )

            if raw is None:

                print()
                print("RAW CMC TARGET  : NOT FOUND")
                print("TARGET STATUS   : BLOCKED")
                print("REASON          : RAW_TARGET_NOT_FOUND")

                blocked_count += 1
                continue

            print()
            print("RAW CMC TARGET  : FOUND")
            print(f"Raw ID          : {raw['id']}")
            print(f"Raw Timestamp   : {raw['timestamp']}")
            print(f"Raw Source Time : {raw['source_timestamp']}")
            print(f"Raw Close       : {raw['close']}")
            print(f"Raw Volume      : {raw['volume']}")

            # ------------------------------------------------
            # TIMESTAMP CHECK
            # ------------------------------------------------

            if (
                analysis["source_timestamp"]
                != raw["source_timestamp"]
            ):

                print()
                print("TARGET STATUS   : BLOCKED")
                print("REASON          : SOURCE_TIMESTAMP_MISMATCH")

                blocked_count += 1
                continue

            # ------------------------------------------------
            # CLOSE CHECK
            # ------------------------------------------------

            if (
                analysis["close"] is None
                or raw["close"] is None
            ):

                print()
                print("TARGET STATUS   : BLOCKED")
                print("REASON          : TARGET_CLOSE_MISSING")

                blocked_count += 1
                continue

            close_difference = abs(
                float(analysis["close"])
                - float(raw["close"])
            )

            if close_difference != 0.0:

                print()
                print("TARGET STATUS   : BLOCKED")
                print("REASON          : TARGET_CLOSE_MISMATCH")
                print(f"CLOSE DIFFERENCE: {close_difference}")

                blocked_count += 1
                continue

            # ------------------------------------------------
            # TARGET RESOLVED
            # ------------------------------------------------

            exact_count += 1

            print()
            print("TARGET IDENTITY : EXACT")

            # ------------------------------------------------
            # WINDOW
            # ------------------------------------------------

            window = get_raw_window(
                conn,
                symbol,
                analysis["source_timestamp"],
                LOOKBACK,
            )

            window_count = len(window)

            print()
            print(f"WINDOW REQUESTED: {LOOKBACK}")
            print(f"WINDOW FOUND    : {window_count}")

            if window:

                print(
                    f"WINDOW FIRST    : "
                    f"{window[0]['source_timestamp']}"
                )

                print(
                    f"WINDOW LAST     : "
                    f"{window[-1]['source_timestamp']}"
                )

            # ------------------------------------------------
            # ELIGIBILITY
            # ------------------------------------------------

            if window_count >= MIN_HISTORY:

                ready_count += 1

                print()
                print("TARGET STATUS   : READY_FOR_RECONSTRUCTION")
                print(
                    f"ELIGIBILITY     : "
                    f"SUFFICIENT_HISTORY_{window_count}"
                )
                print("FORMULA STATUS  : NOT CALCULATED")

            else:

                blocked_count += 1

                print()
                print("TARGET STATUS   : BLOCKED")
                print(
                    f"REASON          : "
                    f"INSUFFICIENT_HISTORY_{window_count}"
                )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        print()
        print_line()
        print("TARGET RESOLUTION SUMMARY")
        print_line()

        print(
            f"Symbols Checked          : {len(SYMBOLS)}"
        )

        print(
            f"Target Identities Exact  : {exact_count}"
        )

        print(
            f"Ready For Reconstruction : {ready_count}"
        )

        print(
            f"Blocked                  : {blocked_count}"
        )

        print()

        if ready_count > 0:

            print(
                "TARGET RESOLUTION STATUS : READY"
            )

        else:

            print(
                "TARGET RESOLUTION STATUS : BLOCKED"
            )

        print(
            "FORMULA VERIFICATION     : NOT STARTED"
        )

        print_line()

        return 0

    except Exception as exc:

        print()
        print_line()
        print("TARGET RESOLUTION AUDIT ERROR")
        print_line()
        print(repr(exc))
        print_line()

        return 1

    finally:

        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())