import ast
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

TARGET_SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]
TARGET_IDS = {
    "BTC": 1706,
    "ETH": 1707,
    "SOL": 1708,
    "XRP": 1709,
}

print("=" * 100)
print("ARUNDA INDICATOR POST-REPAIR PRODUCTION INPUT PATH FORENSIC AUDIT v0.1")
print("=" * 100)
print("MODE                  : READ ONLY")
print("DATABASE WRITE        : NONE")
print("ENGINE WRITE          : NONE")
print("FORMULA WRITE         : NONE")
print("PRODUCTION RECALCULATION : NONE")
print("PURPOSE               : TRACE EXACT PRODUCTION INPUT PATH")
print("=" * 100)


def section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def lines(node):
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", start)
    return start, end


def load_source():
    if not ENGINE_PATH.exists():
        print("ENGINE FOUND          : False")
        return None, None

    source = ENGINE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    return source, tree


def find_functions(tree):
    result = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node

    return result


def find_calls(tree, names):
    result = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in names:
                    result.append(node)
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in names:
                    result.append(node)

    return result


def db_tables(conn):
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()
    ]


def market_data_columns(conn):
    return [
        row[1]
        for row in conn.execute(
            'PRAGMA table_info("market_data")'
        ).fetchall()
    ]


def history_columns(conn):
    return [
        row[1]
        for row in conn.execute(
            'PRAGMA table_info("market_history")'
        ).fetchall()
    ]


def latest_market_data(conn, symbol):
    return conn.execute(
        """
        SELECT
            id,
            symbol,
            source_timestamp,
            engine_version,
            close,
            ema20,
            ema50,
            rsi14
        FROM market_data
        WHERE symbol = ?
        ORDER BY source_timestamp DESC, id DESC
        LIMIT 1
        """,
        (symbol,),
    ).fetchone()


def history_inventory(conn, symbol):
    return conn.execute(
        """
        SELECT
            COUNT(*),
            MIN(timestamp),
            MAX(timestamp),
            COUNT(DISTINCT cmc_id),
            COUNT(DISTINCT symbol)
        FROM market_history
        WHERE symbol = ?
        """,
        (symbol,),
    ).fetchone()


def history_source_distribution(conn, symbol):
    return conn.execute(
        """
        SELECT
            COALESCE(source, '<NULL>'),
            COALESCE(engine_version, '<NULL>'),
            COUNT(*)
        FROM market_history
        WHERE symbol = ?
        GROUP BY source, engine_version
        ORDER BY COUNT(*) DESC
        """,
        (symbol,),
    ).fetchall()


def history_timestamp_relation(conn, symbol, target_timestamp):
    return conn.execute(
        """
        SELECT
            timestamp,
            price,
            source,
            engine_version
        FROM market_history
        WHERE symbol = ?
          AND timestamp <= ?
        ORDER BY timestamp DESC
        LIMIT 10
        """,
        (symbol, target_timestamp),
    ).fetchall()


def history_latest_before(conn, symbol, target_timestamp):
    return conn.execute(
        """
        SELECT
            timestamp,
            price,
            source,
            engine_version
        FROM market_history
        WHERE symbol = ?
          AND timestamp <= ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (symbol, target_timestamp),
    ).fetchone()


def print_source_context(source, start_line, end_line, radius=8):
    if not source or start_line is None:
        return

    source_lines = source.splitlines()

    lo = max(1, start_line - radius)
    hi = min(len(source_lines), end_line + radius)

    for number in range(lo, hi + 1):
        print(
            f"{number:>5}: {source_lines[number - 1]}"
        )


def main():
    section("STEP 1 — ENGINE SOURCE RESOLUTION")

    source, tree = load_source()

    if source is None:
        print("STATUS               : ABORTED")
        return

    print(f"ENGINE PATH          : {ENGINE_PATH}")
    print(f"ENGINE FOUND         : True")
    print(f"SOURCE SIZE          : {len(source)} characters")
    print(f"SOURCE LINES         : {len(source.splitlines())}")
    print("AST STATUS           : SUCCESS")

    functions = find_functions(tree)

    print()
    print("FUNCTION INVENTORY")
    print("-" * 100)

    for name in [
        "ema",
        "ema_series",
        "rsi",
        "calculate_analysis",
    ]:
        node = functions.get(name)

        if node:
            start, end = lines(node)
            print(
                f"[FOUND] {name}() "
                f"LINE {start}-{end}"
            )
        else:
            print(f"[NOT FOUND] {name}()")

    section("STEP 2 — INDICATOR CALL-SITE FORENSICS")

    calls = find_calls(
        tree,
        {
            "ema",
            "ema_series",
            "rsi",
        },
    )

    if not calls:
        print("INDICATOR CALLS       : NONE")
    else:
        for node in calls:
            start, end = lines(node)

            if isinstance(node.func, ast.Name):
                name = node.func.id
            else:
                name = node.func.attr

            print(
                f"[CALL FOUND] {name}() "
                f"LINE {start}"
            )

    section("STEP 3 — PRODUCTION ANALYSIS FUNCTION")

    analysis_node = functions.get("calculate_analysis")

    if analysis_node:
        start, end = lines(analysis_node)

        print(
            f"calculate_analysis() : LINE {start}-{end}"
        )

        print()
        print("SOURCE CONTEXT")
        print("-" * 100)

        print_source_context(
            source,
            start,
            min(end, start + 400),
            radius=5,
        )
    else:
        print("calculate_analysis() : NOT FOUND")

    section("STEP 4 — DATABASE RESOLUTION")

    if not DB_PATH.exists():
        print(f"DATABASE PATH         : {DB_PATH}")
        print("DATABASE FOUND        : False")
        print("STATUS                : ABORTED")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        tables = db_tables(conn)

        print(f"DATABASE PATH         : {DB_PATH}")
        print("DATABASE FOUND        : True")
        print(f"TABLE COUNT           : {len(tables)}")
        print(
            f"MARKET_DATA           : "
            f"{'FOUND' if 'market_data' in tables else 'MISSING'}"
        )
        print(
            f"MARKET_HISTORY        : "
            f"{'FOUND' if 'market_history' in tables else 'MISSING'}"
        )

        print()
        print("MARKET_DATA COLUMNS")
        print("-" * 100)

        for column in market_data_columns(conn):
            print(f"  {column}")

        print()
        print("MARKET_HISTORY COLUMNS")
        print("-" * 100)

        for column in history_columns(conn):
            print(f"  {column}")

        section("STEP 5 — PRODUCTION RECORD → INPUT HISTORY RELATION")

        results = []

        for symbol in TARGET_SYMBOLS:
            print()
            print("=" * 100)
            print(f"SYMBOL : {symbol}")
            print("=" * 100)

            md = latest_market_data(conn, symbol)

            if md is None:
                print("MARKET_DATA            : NOT FOUND")
                results.append((symbol, "UNRESOLVED"))
                continue

            (
                md_id,
                md_symbol,
                source_timestamp,
                engine_version,
                close,
                ema20,
                ema50,
                rsi14,
            ) = md

            print(f"MARKET_DATA ID         : {md_id}")
            print(f"SOURCE TIME            : {source_timestamp}")
            print(f"ENGINE VERSION         : {engine_version}")
            print(f"CLOSE                  : {close}")
            print(f"EMA20                  : {ema20}")
            print(f"EMA50                  : {ema50}")
            print(f"RSI14                  : {rsi14}")

            inventory = history_inventory(
                conn,
                symbol,
            )

            (
                history_count,
                history_first,
                history_last,
                distinct_cmc,
                distinct_symbol,
            ) = inventory

            print()
            print("HISTORY INVENTORY")
            print("-" * 100)

            print(f"HISTORY ROWS           : {history_count}")
            print(f"HISTORY FIRST          : {history_first}")
            print(f"HISTORY LAST           : {history_last}")
            print(f"DISTINCT CMC_ID        : {distinct_cmc}")
            print(f"DISTINCT SYMBOL        : {distinct_symbol}")

            print()
            print("SOURCE / ENGINE DISTRIBUTION")
            print("-" * 100)

            for row in history_source_distribution(
                conn,
                symbol,
            ):
                print(
                    f"SOURCE={row[0]} | "
                    f"ENGINE={row[1]} | "
                    f"ROWS={row[2]}"
                )

            print()
            print("LATEST HISTORY BEFORE PRODUCTION TIME")
            print("-" * 100)

            latest_before = history_latest_before(
                conn,
                symbol,
                source_timestamp,
            )

            if latest_before:
                print(
                    f"TIMESTAMP             : {latest_before[0]}"
                )
                print(
                    f"PRICE                 : {latest_before[1]}"
                )
                print(
                    f"SOURCE                : {latest_before[2]}"
                )
                print(
                    f"ENGINE                : {latest_before[3]}"
                )
            else:
                print("NO HISTORY ROW BEFORE TARGET")

            print()
            print("LAST 10 ELIGIBLE HISTORY ROWS")
            print("-" * 100)

            eligible = history_timestamp_relation(
                conn,
                symbol,
                source_timestamp,
            )

            for row in eligible:
                print(
                    f"TIME={row[0]} | "
                    f"PRICE={row[1]} | "
                    f"SOURCE={row[2]} | "
                    f"ENGINE={row[3]}"
                )

            print()
            print("INPUT PATH VERDICT")
            print("-" * 100)

            if history_count == 0:
                status = "HISTORY_NOT_FOUND"
                reason = "NO_HISTORY_ROWS"

            elif history_last is None:
                status = "HISTORY_UNRESOLVED"
                reason = "INVALID_HISTORY_TIMELINE"

            elif str(history_last) < str(source_timestamp):
                status = "HISTORY_STALE"
                reason = (
                    "HISTORY_ENDS_BEFORE_PRODUCTION_TIMESTAMP"
                )

            else:
                status = "HISTORY_TEMPORALLY_AVAILABLE"
                reason = (
                    "HISTORY_REACHES_PRODUCTION_TIME"
                )

            print(f"STATUS                 : {status}")
            print(f"REASON                 : {reason}")

            results.append((symbol, status))

        section("FINAL PRODUCTION INPUT PATH FORENSIC SUMMARY")

        print(f"TARGETS CHECKED       : {len(results)}")

        for symbol, status in results:
            print(
                f"  [{status:>32}] : {symbol}"
            )

        stale = [
            symbol
            for symbol, status in results
            if status == "HISTORY_STALE"
        ]

        available = [
            symbol
            for symbol, status in results
            if status == "HISTORY_TEMPORALLY_AVAILABLE"
        ]

        print()
        print("=" * 100)
        print("FORENSIC CONCLUSION")
        print("=" * 100)

        if stale:
            print("STATUS                  : PRODUCTION_HISTORY_PATH_STALE")
            print(
                "REASON                  : "
                "MARKET_HISTORY DOES NOT REACH PRODUCTION TARGET TIME"
            )
            print(
                "NEXT FRONTIER           : "
                "TRACE THE ACTUAL PRODUCTION PRICE INPUT SOURCE"
            )

        elif available:
            print("STATUS                  : PRODUCTION_HISTORY_PATH_POSSIBLE")
            print(
                "REASON                  : "
                "HISTORY TEMPORALLY REACHES PRODUCTION TARGET"
            )
            print(
                "NEXT FRONTIER           : "
                "TRACE EXACT HISTORY CONSUMPTION CALL"
            )

        else:
            print("STATUS                  : INPUT_PATH_UNRESOLVED")
            print(
                "REASON                  : "
                "PRODUCTION INPUT SOURCE NOT YET PROVEN"
            )
            print(
                "NEXT FRONTIER           : "
                "TRACE ACTUAL PRODUCTION INPUT SOURCE"
            )

        print()
        print("DATABASE WRITE OPERATIONS : NONE")
        print("ENGINE MODIFICATIONS      : NONE")
        print("FORMULA WRITE             : NONE")
        print("PRODUCTION RECALCULATION  : NONE")
        print("AUDIT COMPLETE")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
