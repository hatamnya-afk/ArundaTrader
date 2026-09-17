import sqlite3
from pathlib import Path

# ============================================================
# ARUNDA
# INDICATOR STANDARD CONVENTION TARGET RESOLUTION AUDIT v0.1
# ============================================================
# MODE              : READ ONLY
# DATABASE WRITE    : NONE
# FORMULA CALC      : NONE
# PURPOSE           : Resolve a valid market_data target whose
#                     indicator fields are actually populated.
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"

SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]

REQUIRED_FIELDS = [
    "ema20",
    "ema50",
    "rsi14",
]

EXPECTED_ENGINE = "MARKET_DATA_CMC_SNAPSHOT_v0.2"


def divider(char="=", width=99):
    print(char * width)


def get_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return {row[1] for row in rows}


def find_latest_valid_target(conn, symbol):
    """
    Find the latest market_data row for this symbol where
    all required indicator fields are populated.

    No calculations.
    No writes.
    """

    query = """
        SELECT
            id,
            symbol,
            source_timestamp,
            engine_version,
            close,
            ema20,
            ema50,
            rsi14,
            technical_score
        FROM market_data
        WHERE symbol = ?
          AND ema20 IS NOT NULL
          AND ema50 IS NOT NULL
          AND rsi14 IS NOT NULL
        ORDER BY source_timestamp DESC, id DESC
        LIMIT 1
    """

    return conn.execute(query, (symbol,)).fetchone()


def find_raw_cmc_target(conn, symbol, source_timestamp):
    """
    Resolve raw CMC row using the exact source timestamp.

    This function is intentionally read-only.
    """

    columns = get_columns(conn, "market_data")

    # If source/source fields exist in market_data, try to use them.
    # Otherwise only report that raw resolution is unavailable.
    possible_source_columns = [
        "source",
        "data_source",
        "source_name",
    ]

    source_column = None

    for candidate in possible_source_columns:
        if candidate in columns:
            source_column = candidate
            break

    if source_column is None:
        return None

    query = f"""
        SELECT
            id,
            symbol,
            source_timestamp,
            close,
            volume,
            {source_column}
        FROM market_data
        WHERE symbol = ?
          AND source_timestamp = ?
          AND UPPER(COALESCE({source_column}, '')) = 'COINMARKETCAP'
        ORDER BY id DESC
        LIMIT 1
    """

    return conn.execute(
        query,
        (symbol, source_timestamp)
    ).fetchone()


def resolve_symbol(conn, symbol):
    print()
    divider("=")
    print(f"SYMBOL : {symbol}")
    divider("-")

    row = find_latest_valid_target(conn, symbol)

    if row is None:
        print("CURRENT TARGET : NOT FOUND")
        print("TARGET STATUS   : BLOCKED")
        print("REASON          : NO_NON_NULL_INDICATOR_TARGET")
        return {
            "symbol": symbol,
            "status": "BLOCKED",
        }

    (
        analysis_id,
        db_symbol,
        source_timestamp,
        engine_version,
        close,
        ema20,
        ema50,
        rsi14,
        technical_score,
    ) = row

    print("CURRENT TARGET : FOUND")
    print("Analysis ID     :", analysis_id)
    print("Symbol          :", db_symbol)
    print("Source Time     :", source_timestamp)
    print("Engine Version  :", engine_version)
    print("Stored Close    :", close)
    print("Stored EMA20    :", ema20)
    print("Stored EMA50    :", ema50)
    print("Stored RSI14    :", rsi14)
    print("Stored Score    :", technical_score)

    print()
    print("INDICATOR FIELD RESOLUTION")
    print("-" * 99)

    all_present = True

    for field, value in [
        ("EMA20", ema20),
        ("EMA50", ema50),
        ("RSI14", rsi14),
    ]:
        if value is None:
            print(f"  [MISSING] : {field}")
            all_present = False
        else:
            print(f"  [FOUND]   : {field} = {value}")

    print()
    print("ENGINE RESOLUTION")
    print("-" * 99)

    if engine_version == EXPECTED_ENGINE:
        print("  [EXPECTED] :", engine_version)
        engine_status = "EXPECTED"
    else:
        print("  [OTHER]    :", engine_version)
        engine_status = "OTHER"

    raw_target = find_raw_cmc_target(
        conn,
        symbol,
        source_timestamp,
    )

    print()
    print("RAW CMC TARGET")
    print("-" * 99)

    if raw_target is None:
        print("RAW CMC TARGET : NOT RESOLVED")
        raw_status = "NOT_RESOLVED"
    else:
        (
            raw_id,
            raw_symbol,
            raw_timestamp,
            raw_close,
            raw_volume,
            raw_source,
        ) = raw_target

        print("RAW CMC TARGET : FOUND")
        print("Raw ID         :", raw_id)
        print("Raw Symbol     :", raw_symbol)
        print("Raw Time       :", raw_timestamp)
        print("Raw Close      :", raw_close)
        print("Raw Volume     :", raw_volume)
        print("Raw Source     :", raw_source)

        if raw_close == close:
            print("PRICE IDENTITY : EXACT")
            raw_status = "EXACT"
        else:
            print("PRICE IDENTITY : MISMATCH")
            raw_status = "MISMATCH"

    print()
    print("TARGET RESOLUTION")
    print("-" * 99)

    if not all_present:
        status = "BLOCKED"
        reason = "MISSING_REQUIRED_INDICATOR"

    elif raw_status == "MISMATCH":
        status = "BLOCKED"
        reason = "RAW_TARGET_PRICE_MISMATCH"

    elif raw_status == "NOT_RESOLVED":
        status = "READY_WITHOUT_RAW_LINK"
        reason = "RAW_CMC_TARGET_NOT_RESOLVED"

    else:
        status = "READY"
        reason = "VALID_NON_NULL_INDICATOR_TARGET"

    print("TARGET STATUS   :", status)
    print("REASON          :", reason)

    return {
        "symbol": symbol,
        "analysis_id": analysis_id,
        "source_timestamp": source_timestamp,
        "engine_version": engine_version,
        "ema20": ema20,
        "ema50": ema50,
        "rsi14": rsi14,
        "engine_status": engine_status,
        "raw_status": raw_status,
        "status": status,
    }


def main():
    divider("=")
    print("ARUNDA INDICATOR STANDARD CONVENTION TARGET RESOLUTION AUDIT v0.1")
    divider("=")

    print("MODE              : READ ONLY")
    print("DATABASE          : arunda.db")
    print("DATABASE WRITE    : NONE")
    print("FORMULA CALC      : NONE")
    print("PURPOSE           : NON-NULL INDICATOR TARGET RESOLUTION")
    divider("=")

    print("DATABASE RESOLUTION")
    divider("-")

    print("DATABASE PATH     :", DB_PATH)
    print("DATABASE FOUND    :", DB_PATH.exists())

    if not DB_PATH.exists():
        print("AUDIT STATUS      : BLOCKED")
        print("REASON            : DATABASE_NOT_FOUND")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

        table_names = [row[0] for row in tables]

        print("TABLE COUNT       :", len(table_names))
        print("MARKET_DATA       :", "FOUND" if "market_data" in table_names else "MISSING")

        if "market_data" not in table_names:
            print()
            print("AUDIT STATUS      : BLOCKED")
            print("REASON            : MARKET_DATA_TABLE_NOT_FOUND")
            return

        columns = get_columns(conn, "market_data")

        print("COLUMN COUNT      :", len(columns))

        required_db_fields = [
            "id",
            "symbol",
            "source_timestamp",
            "engine_version",
            "close",
            "ema20",
            "ema50",
            "rsi14",
        ]

        print()
        print("REQUIRED DATABASE FIELDS")
        divider("-")

        missing_fields = []

        for field in required_db_fields:
            if field in columns:
                print(f"  [PRESENT] : {field}")
            else:
                print(f"  [MISSING] : {field}")
                missing_fields.append(field)

        if missing_fields:
            print()
            print("AUDIT STATUS      : BLOCKED")
            print(
                "REASON            : MISSING_DB_FIELDS =",
                ", ".join(missing_fields),
            )
            return

        results = []

        for symbol in SYMBOLS:
            result = resolve_symbol(conn, symbol)
            results.append(result)

        divider("=")
        print("FINAL TARGET RESOLUTION SUMMARY")
        divider("=")

        ready = sum(
            1
            for result in results
            if result["status"] in (
                "READY",
                "READY_WITHOUT_RAW_LINK",
            )
        )

        blocked = sum(
            1
            for result in results
            if result["status"] == "BLOCKED"
        )

        raw_exact = sum(
            1
            for result in results
            if result.get("raw_status") == "EXACT"
        )

        print("SYMBOLS CHECKED        :", len(results))
        print("READY TARGETS          :", ready)
        print("BLOCKED TARGETS        :", blocked)
        print("RAW TARGETS EXACT      :", raw_exact)

        print()
        print("TARGET MATRIX")
        divider("-")

        for result in results:
            print(
                f"  [{result['status']:<22}] : "
                f"{result['symbol']}"
            )

        print()
        divider("=")

        if ready == len(results):
            print("TARGET RESOLUTION STATUS : READY")
            print("NEXT FRONTIER            : STANDARD CONVENTION COMPARISON")
        else:
            print("TARGET RESOLUTION STATUS : REVIEW_REQUIRED")
            print("NEXT ACTION              : RESOLVE BLOCKED TARGETS")

        divider("=")
        print("DATABASE WRITE OPERATIONS : NONE")
        print("FORMULA CALCULATIONS      : NONE")
        print("AUDIT COMPLETE")
        divider("=")

    finally:
        conn.close()


if __name__ == "__main__":
    main()