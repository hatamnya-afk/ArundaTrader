import sqlite3
from pathlib import Path
from collections import Counter


# ============================================================================
# ARUNDA MARKET DATA INPUT CONTRACT AUDIT v0.1
# ============================================================================
#
# MODE:
#     READ ONLY
#
# PURPOSE:
#     Extract the REAL market_data input contract from arunda.db.
#
# WRITE:
#     NONE
#
# INSERT:
#     NONE
#
# UPDATE:
#     NONE
#
# DELETE:
#     NONE
#
# ALTER:
#     NONE
#
# ============================================================================


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"
TABLE = "market_data"


def get_columns(conn):
    rows = conn.execute(
        f"PRAGMA table_info({TABLE})"
    ).fetchall()

    return rows


def print_schema(rows):

    print()
    print("=" * 100)
    print("REAL MARKET_DATA SCHEMA")
    print("=" * 100)

    print(
        f"{'CID':<6}"
        f"{'NAME':<30}"
        f"{'TYPE':<14}"
        f"{'NOTNULL':<10}"
        f"{'DEFAULT':<18}"
        f"PK"
    )

    print("-" * 100)

    for row in rows:

        cid = row[0]
        name = row[1]
        data_type = row[2]
        not_null = row[3]
        default = row[4]
        pk = row[5]

        print(
            f"{cid:<6}"
            f"{name:<30}"
            f"{data_type:<14}"
            f"{not_null:<10}"
            f"{str(default):<18}"
            f"{pk}"
        )


def print_counts(conn):

    total = conn.execute(
        f"SELECT COUNT(*) FROM {TABLE}"
    ).fetchone()[0]

    print()
    print("=" * 100)
    print("ROW COUNT")
    print("=" * 100)
    print(f"Total Rows : {total}")


def print_null_profile(conn, columns):

    print()
    print("=" * 100)
    print("NULL / NON-NULL PROFILE")
    print("=" * 100)

    total = conn.execute(
        f"SELECT COUNT(*) FROM {TABLE}"
    ).fetchone()[0]

    if total == 0:
        print("Table is empty.")
        return

    for row in columns:

        name = row[1]

        null_count = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {TABLE}
            WHERE "{name}" IS NULL
            """
        ).fetchone()[0]

        non_null_count = total - null_count

        print(
            f"{name:<30}"
            f"NULL={null_count:<10}"
            f"NON_NULL={non_null_count}"
        )


def print_distinct_profile(conn, columns):

    print()
    print("=" * 100)
    print("DISTINCT VALUE PROFILE")
    print("=" * 100)

    for row in columns:

        name = row[1]

        try:
            count = conn.execute(
                f"""
                SELECT COUNT(DISTINCT "{name}")
                FROM {TABLE}
                """
            ).fetchone()[0]

            print(
                f"{name:<30}"
                f"DISTINCT={count}"
            )

        except Exception as exc:

            print(
                f"{name:<30}"
                f"ERROR={type(exc).__name__}: {exc}"
            )


def print_symbol_profile(conn, columns):

    names = {
        row[1]
        for row in columns
    }

    if "symbol" not in names:
        print()
        print("SYMBOL column: MISSING")
        return

    print()
    print("=" * 100)
    print("SYMBOL PROFILE")
    print("=" * 100)

    total_symbols = conn.execute(
        f"""
        SELECT COUNT(DISTINCT symbol)
        FROM {TABLE}
        WHERE symbol IS NOT NULL
        """
    ).fetchone()[0]

    print(
        f"Distinct Symbols : {total_symbols}"
    )

    rows = conn.execute(
        f"""
        SELECT symbol, COUNT(*) AS n
        FROM {TABLE}
        WHERE symbol IS NOT NULL
        GROUP BY symbol
        ORDER BY n DESC, symbol ASC
        LIMIT 30
        """
    ).fetchall()

    print()
    print(
        f"{'SYMBOL':<20}"
        f"{'ROWS':<12}"
    )
    print("-" * 40)

    for symbol, count in rows:

        print(
            f"{str(symbol):<20}"
            f"{count:<12}"
        )


def print_timestamp_profile(conn, columns):

    names = {
        row[1]
        for row in columns
    }

    if "timestamp" not in names:
        print()
        print("TIMESTAMP column: MISSING")
        return

    print()
    print("=" * 100)
    print("TIMESTAMP PROFILE")
    print("=" * 100)

    result = conn.execute(
        f"""
        SELECT
            MIN(timestamp),
            MAX(timestamp),
            COUNT(DISTINCT timestamp)
        FROM {TABLE}
        WHERE timestamp IS NOT NULL
        """
    ).fetchone()

    print(
        f"MIN timestamp       : {result[0]}"
    )

    print(
        f"MAX timestamp       : {result[1]}"
    )

    print(
        f"Distinct timestamps : {result[2]}"
    )


def print_price_profile(conn, columns):

    names = {
        row[1]
        for row in columns
    }

    price_candidates = [
        "close",
        "price",
        "open",
        "high",
        "low",
        "volume",
    ]

    available = [
        name
        for name in price_candidates
        if name in names
    ]

    print()
    print("=" * 100)
    print("NUMERIC MARKET FIELD PROFILE")
    print("=" * 100)

    if not available:
        print("No standard numeric market fields detected.")
        return

    for name in available:

        try:

            result = conn.execute(
                f"""
                SELECT
                    COUNT("{name}"),
                    MIN("{name}"),
                    MAX("{name}")
                FROM {TABLE}
                WHERE "{name}" IS NOT NULL
                """
            ).fetchone()

            print()
            print(
                f"{name}"
            )

            print(
                f"  Non-NULL : {result[0]}"
            )

            print(
                f"  MIN      : {result[1]}"
            )

            print(
                f"  MAX      : {result[2]}"
            )

        except Exception as exc:

            print(
                f"  ERROR    : "
                f"{type(exc).__name__}: {exc}"
            )


def print_source_profile(conn, columns):

    names = {
        row[1]
        for row in columns
    }

    if "source" not in names:

        print()
        print("SOURCE column: MISSING")
        return

    print()
    print("=" * 100)
    print("SOURCE PROFILE")
    print("=" * 100)

    rows = conn.execute(
        f"""
        SELECT
            source,
            COUNT(*)
        FROM {TABLE}
        GROUP BY source
        ORDER BY COUNT(*) DESC
        """
    ).fetchall()

    for source, count in rows:

        print(
            f"{str(source):<30}"
            f"{count}"
        )


def print_timeframe_profile(conn, columns):

    names = {
        row[1]
        for row in columns
    }

    if "timeframe" not in names:

        print()
        print("TIMEFRAME column: MISSING")
        return

    print()
    print("=" * 100)
    print("TIMEFRAME PROFILE")
    print("=" * 100)

    rows = conn.execute(
        f"""
        SELECT
            timeframe,
            COUNT(*)
        FROM {TABLE}
        GROUP BY timeframe
        ORDER BY COUNT(*) DESC
        """
    ).fetchall()

    for timeframe, count in rows:

        print(
            f"{str(timeframe):<30}"
            f"{count}"
        )


def print_duplicate_profile(conn, columns):

    names = {
        row[1]
        for row in columns
    }

    if "symbol" not in names or "timestamp" not in names:
        return

    print()
    print("=" * 100)
    print("SYMBOL + TIMESTAMP DUPLICATE PROFILE")
    print("=" * 100)

    duplicate_groups = conn.execute(
        f"""
        SELECT
            symbol,
            timestamp,
            COUNT(*) AS n
        FROM {TABLE}
        GROUP BY symbol, timestamp
        HAVING COUNT(*) > 1
        ORDER BY n DESC
        LIMIT 30
        """
    ).fetchall()

    if not duplicate_groups:

        print("Duplicate groups : NONE")

    else:

        print(
            f"{'SYMBOL':<20}"
            f"{'TIMESTAMP':<35}"
            f"{'COUNT':<10}"
        )

        print("-" * 70)

        for symbol, timestamp, count in duplicate_groups:

            print(
                f"{str(symbol):<20}"
                f"{str(timestamp):<35}"
                f"{count:<10}"
            )


def print_sample_rows(conn, columns):

    names = [
        row[1]
        for row in columns
    ]

    print()
    print("=" * 100)
    print("REAL SAMPLE ROWS")
    print("=" * 100)

    select_list = ", ".join(
        f'"{name}"'
        for name in names
    )

    rows = conn.execute(
        f"""
        SELECT {select_list}
        FROM {TABLE}
        ORDER BY rowid DESC
        LIMIT 10
        """
    ).fetchall()

    for index, row in enumerate(rows, start=1):

        print()
        print(
            f"--- SAMPLE {index} ---"
        )

        for name, value in zip(names, row):

            print(
                f"{name:<30}: {value}"
            )


def print_candidate_contract(columns):

    names = [
        row[1]
        for row in columns
    ]

    print()
    print("=" * 100)
    print("PRELIMINARY INPUT CONTRACT DETECTION")
    print("=" * 100)

    expected_groups = {

        "IDENTITY": [
            "symbol",
            "timestamp",
        ],

        "OHLCV": [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ],

        "PRICE": [
            "price",
            "close",
        ],

        "PROVENANCE": [
            "source",
            "source_timestamp",
        ],

        "TIMEFRAME": [
            "timeframe",
        ],
    }

    for group, fields in expected_groups.items():

        present = [
            field
            for field in fields
            if field in names
        ]

        missing = [
            field
            for field in fields
            if field not in names
        ]

        print()
        print(
            f"{group}"
        )

        print(
            f"  PRESENT : "
            f"{', '.join(present) if present else 'NONE'}"
        )

        print(
            f"  MISSING : "
            f"{', '.join(missing) if missing else 'NONE'}"
        )


def main():

    print("=" * 100)
    print("ARUNDA MARKET DATA INPUT CONTRACT AUDIT v0.1")
    print("=" * 100)

    print(
        f"Database : {DB_PATH}"
    )

    print(
        f"Table    : {TABLE}"
    )

    print(
        "Mode     : READ ONLY"
    )

    print(
        "INSERT   : NONE"
    )

    print(
        "UPDATE   : NONE"
    )

    print(
        "DELETE   : NONE"
    )

    print(
        "ALTER    : NONE"
    )

    print("=" * 100)

    if not DB_PATH.exists():

        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(
        str(DB_PATH)
    )

    try:

        exists = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name=?
            """,
            (TABLE,),
        ).fetchone()

        if exists is None:

            raise RuntimeError(
                f"Table does not exist: {TABLE}"
            )

        columns = get_columns(conn)

        print_schema(columns)

        print_counts(conn)

        print_null_profile(
            conn,
            columns
        )

        print_distinct_profile(
            conn,
            columns
        )

        print_symbol_profile(
            conn,
            columns
        )

        print_timestamp_profile(
            conn,
            columns
        )

        print_price_profile(
            conn,
            columns
        )

        print_source_profile(
            conn,
            columns
        )

        print_timeframe_profile(
            conn,
            columns
        )

        print_duplicate_profile(
            conn,
            columns
        )

        print_candidate_contract(
            columns
        )

        print_sample_rows(
            conn,
            columns
        )

        print()
        print("=" * 100)
        print("AUDIT COMPLETE")
        print("=" * 100)
        print("DATABASE MODIFICATION : NONE")
        print("DATA MODIFICATION     : NONE")
        print("=" * 100)

    finally:

        conn.close()


if __name__ == "__main__":
    main()