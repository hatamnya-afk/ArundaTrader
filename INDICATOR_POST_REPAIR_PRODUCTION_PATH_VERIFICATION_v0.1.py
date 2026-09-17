import ast
import math
import sqlite3
from pathlib import Path
from statistics import mean

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]

MIN_HISTORY = 60
EMA20_PERIOD = 20
EMA50_PERIOD = 50
RSI_PERIOD = 14

ABS_TOLERANCE = 1e-10
REL_TOLERANCE = 1e-10


def fmt(value):
    if value is None:
        return "None"
    return repr(float(value))


def relative_error(a, b):
    if a is None or b is None:
        return None
    return abs(a - b) / max(abs(b), 1e-300)


def values_match(a, b):
    if a is None or b is None:
        return False

    abs_err = abs(a - b)
    rel_err = relative_error(a, b)

    return (
        abs_err <= ABS_TOLERANCE
        or rel_err <= REL_TOLERANCE
    )


def standard_ema(values, period):
    if values is None or len(values) < period:
        return None

    seed = mean(values[:period])
    alpha = 2.0 / (period + 1.0)

    result = seed

    for value in values[period:]:
        result = (
            value * alpha
            + result * (1.0 - alpha)
        )

    return result


def standard_rsi(values, period=14):
    if values is None or len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0.0)

        elif change < 0:
            gains.append(0.0)
            losses.append(-change)

        else:
            gains.append(0.0)
            losses.append(0.0)

    if len(gains) < period:
        return None

    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (
            (avg_gain * (period - 1))
            + gains[i]
        ) / period

        avg_loss = (
            (avg_loss * (period - 1))
            + losses[i]
        ) / period

    if avg_loss == 0:
        if avg_gain == 0:
            return 50.0
        return 100.0

    rs = avg_gain / avg_loss

    return 100.0 - (
        100.0 / (1.0 + rs)
    )


def verify_engine_syntax():
    print("=" * 100)
    print("STEP 1 — POST-REPAIR ENGINE VERIFICATION")
    print("=" * 100)

    print(f"ENGINE PATH        : {ENGINE_PATH}")
    print(f"ENGINE FOUND       : {ENGINE_PATH.exists()}")

    if not ENGINE_PATH.exists():
        print("POST-REPAIR SYNTAX : NOT_VERIFIED")
        return False

    source = ENGINE_PATH.read_text(
        encoding="utf-8",
        errors="replace"
    )

    print(f"SOURCE SIZE        : {len(source)} characters")
    print(f"SOURCE LINES       : {len(source.splitlines())}")

    try:
        tree = ast.parse(
            source,
            filename=str(ENGINE_PATH)
        )
    except SyntaxError as exc:
        print("POST-REPAIR SYNTAX : INVALID")
        print(f"SYNTAX ERROR       : {exc}")
        return False

    print("POST-REPAIR SYNTAX : VALID")

    functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        )
    }

    print()
    print("STANDARD FUNCTION INVENTORY")
    print("-" * 100)

    for name in ("ema", "rsi"):
        status = "FOUND" if name in functions else "MISSING"
        print(f"  [{status:7}] : {name}()")

    return (
        "ema" in functions
        and "rsi" in functions
    )


def get_table_names(conn):
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    ).fetchall()

    return [row[0] for row in rows]


def get_columns(conn, table):
    rows = conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    return [row[1] for row in rows]


def resolve_history_schema(conn):
    print()
    print("=" * 100)
    print("STEP 2A — HISTORY SCHEMA RESOLUTION")
    print("=" * 100)

    tables = get_table_names(conn)

    candidates = [
        "market_history",
        "market_history_repair",
    ]

    selected = None

    for table in candidates:
        if table in tables:
            selected = table
            break

    if selected is None:
        print("HISTORY TABLE       : NOT FOUND")
        return None

    columns = get_columns(conn, selected)

    print(f"HISTORY TABLE       : {selected}")
    print(f"COLUMN COUNT        : {len(columns)}")

    print()
    print("HISTORY COLUMNS")
    print("-" * 100)

    for column in columns:
        print(f"  {column}")

    timestamp_candidates = [
        "timestamp",
        "source_timestamp",
        "time",
        "datetime",
        "date",
    ]

    price_candidates = [
        "close",
        "close_price",
        "price",
        "close_usd",
        "quote_close",
        "last_price",
    ]

    symbol_candidates = [
        "symbol",
        "asset_symbol",
    ]

    timestamp_col = next(
        (
            column
            for column in timestamp_candidates
            if column in columns
        ),
        None,
    )

    price_col = next(
        (
            column
            for column in price_candidates
            if column in columns
        ),
        None,
    )

    symbol_col = next(
        (
            column
            for column in symbol_candidates
            if column in columns
        ),
        None,
    )

    print()
    print("RESOLVED HISTORY FIELDS")
    print("-" * 100)
    print(f"SYMBOL COLUMN       : {symbol_col}")
    print(f"TIMESTAMP COLUMN    : {timestamp_col}")
    print(f"PRICE COLUMN        : {price_col}")

    if (
        symbol_col is None
        or timestamp_col is None
        or price_col is None
    ):
        print()
        print("HISTORY SCHEMA STATUS : UNRESOLVED")
        return None

    print("HISTORY SCHEMA STATUS : RESOLVED")

    return {
        "table": selected,
        "symbol": symbol_col,
        "timestamp": timestamp_col,
        "price": price_col,
    }


def verify_database_schema(conn):
    print()
    print("=" * 100)
    print("STEP 2 — DATABASE RESOLUTION")
    print("=" * 100)

    print(f"DATABASE PATH      : {DB_PATH}")
    print(f"DATABASE FOUND     : {DB_PATH.exists()}")

    if not DB_PATH.exists():
        return None

    tables = get_table_names(conn)

    print(f"TABLE COUNT        : {len(tables)}")

    if "market_data" not in tables:
        print("MARKET_DATA        : MISSING")
        return None

    print("MARKET_DATA        : FOUND")

    columns = get_columns(
        conn,
        "market_data"
    )

    print(f"COLUMN COUNT       : {len(columns)}")

    required = {
        "id",
        "symbol",
        "source_timestamp",
        "engine_version",
        "close",
        "ema20",
        "ema50",
        "rsi14",
    }

    missing = required - set(columns)

    if missing:
        print(
            f"REQUIRED FIELDS    : MISSING {sorted(missing)}"
        )
        return None

    print("REQUIRED FIELDS    : VERIFIED")

    return resolve_history_schema(conn)


def resolve_latest_record(conn, symbol):
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
        ORDER BY
            source_timestamp DESC,
            id DESC
        LIMIT 1
        """,
        (symbol,),
    ).fetchone()


def resolve_history(
    conn,
    schema,
    symbol,
    latest_timestamp,
):
    table = schema["table"]
    symbol_col = schema["symbol"]
    timestamp_col = schema["timestamp"]
    price_col = schema["price"]

    sql = f'''
        SELECT
            "{timestamp_col}",
            "{price_col}"
        FROM "{table}"
        WHERE "{symbol_col}" = ?
          AND "{timestamp_col}" <= ?
          AND "{price_col}" IS NOT NULL
        ORDER BY "{timestamp_col}" ASC
    '''

    rows = conn.execute(
        sql,
        (symbol, latest_timestamp),
    ).fetchall()

    valid = []

    for timestamp, price in rows:
        try:
            value = float(price)
        except (TypeError, ValueError):
            continue

        if math.isfinite(value):
            valid.append(
                (timestamp, value)
            )

    return valid


def print_indicator(
    name,
    current,
    standard,
):
    print()
    print(f"INDICATOR : {name}")
    print(f"CURRENT   : {fmt(current)}")
    print(f"STANDARD  : {fmt(standard)}")

    if current is None:
        print("ABS ERR   : None")
        print("REL ERR   : None")
        print("STATUS    : MISMATCH")
        return False

    abs_err = abs(
        current - standard
    )

    rel_err = relative_error(
        current,
        standard
    )

    status = (
        "MATCH"
        if values_match(current, standard)
        else "MISMATCH"
    )

    print(f"ABS ERR   : {abs_err}")
    print(f"REL ERR   : {rel_err}")
    print(f"STATUS    : {status}")

    return status == "MATCH"


def verify_symbol(
    conn,
    history_schema,
    symbol,
):
    print()
    print("=" * 100)
    print(f"SYMBOL : {symbol}")
    print("=" * 100)

    latest = resolve_latest_record(
        conn,
        symbol
    )

    if latest is None:
        print("LATEST PRODUCTION RECORD : NOT FOUND")

        return {
            "symbol": symbol,
            "status": "UNRESOLVED",
            "matches": 0,
            "comparisons": 0,
        }

    (
        record_id,
        db_symbol,
        source_timestamp,
        engine_version,
        close,
        current_ema20,
        current_ema50,
        current_rsi14,
    ) = latest

    print(f"ID              : {record_id}")
    print(f"SOURCE TIME     : {source_timestamp}")
    print(f"ENGINE VERSION  : {engine_version}")
    print(f"CLOSE           : {fmt(close)}")

    history = resolve_history(
        conn,
        history_schema,
        symbol,
        source_timestamp,
    )

    print()
    print("PRODUCTION PATH HISTORY")
    print("-" * 100)
    print(f"HISTORY COUNT   : {len(history)}")

    if len(history) < MIN_HISTORY:
        print(
            f"MIN HISTORY     : {MIN_HISTORY}"
        )
        print("HISTORY STATUS  : INSUFFICIENT")
        print("SYMBOL STATUS   : UNRESOLVED")

        return {
            "symbol": symbol,
            "status": "UNRESOLVED",
            "matches": 0,
            "comparisons": 0,
        }

    closes = [
        item[1]
        for item in history
    ]

    standard_ema20 = standard_ema(
        closes,
        EMA20_PERIOD
    )

    standard_ema50 = standard_ema(
        closes,
        EMA50_PERIOD
    )

    standard_rsi14 = standard_rsi(
        closes,
        RSI_PERIOD
    )

    print()
    print("INDEPENDENT STANDARD RECONSTRUCTION")
    print("-" * 100)
    print(f"VALID CLOSES    : {len(closes)}")
    print(f"STANDARD EMA20  : {fmt(standard_ema20)}")
    print(f"STANDARD EMA50  : {fmt(standard_ema50)}")
    print(f"STANDARD RSI14  : {fmt(standard_rsi14)}")

    print()
    print("POST-REPAIR PRODUCTION PATH VERIFICATION")
    print("-" * 100)

    comparisons = 0
    matches = 0

    comparisons += 1

    if print_indicator(
        "EMA20",
        current_ema20,
        standard_ema20,
    ):
        matches += 1

    comparisons += 1

    if print_indicator(
        "EMA50",
        current_ema50,
        standard_ema50,
    ):
        matches += 1

    comparisons += 1

    if print_indicator(
        "RSI14",
        current_rsi14,
        standard_rsi14,
    ):
        matches += 1

    mismatches = comparisons - matches

    status = (
        "VERIFIED"
        if mismatches == 0
        else "DIFFERENCE_DETECTED"
    )

    print()
    print("SYMBOL VERIFICATION SUMMARY")
    print("-" * 100)
    print(f"COMPARISONS      : {comparisons}")
    print(f"MATCHES          : {matches}")
    print(f"MISMATCHES       : {mismatches}")
    print(f"SYMBOL STATUS    : {status}")

    return {
        "symbol": symbol,
        "status": status,
        "matches": matches,
        "comparisons": comparisons,
    }


def main():
    print("=" * 100)
    print(
        "ARUNDA INDICATOR POST REPAIR "
        "PRODUCTION PATH VERIFICATION v0.1"
    )
    print("=" * 100)
    print("MODE                  : READ ONLY")
    print("DATABASE WRITE        : NONE")
    print("ENGINE WRITE          : NONE")
    print("FORMULA WRITE         : NONE")
    print("PRODUCTION RECALCULATION : NONE")
    print("PURPOSE               : VERIFY POST-REPAIR PRODUCTION PATH")
    print("=" * 100)

    if not verify_engine_syntax():
        print()
        print("=" * 100)
        print("FINAL CONCLUSION")
        print("=" * 100)
        print("STATUS : BLOCKED")
        print(
            "REASON : POST-REPAIR ENGINE VERIFICATION FAILED"
        )
        print("DATABASE WRITE OPERATIONS : NONE")
        return

    try:
        conn = sqlite3.connect(
            f"file:{DB_PATH}?mode=ro",
            uri=True,
        )
    except Exception as exc:
        print()
        print("=" * 100)
        print("FINAL CONCLUSION")
        print("=" * 100)
        print("STATUS : BLOCKED")
        print(
            f"REASON : DATABASE READ-ONLY OPEN FAILED: {exc}"
        )
        print("DATABASE WRITE OPERATIONS : NONE")
        return

    try:
        history_schema = verify_database_schema(
            conn
        )

        if history_schema is None:
            print()
            print("=" * 100)
            print("FINAL CONCLUSION")
            print("=" * 100)
            print("STATUS : BLOCKED")
            print(
                "REASON : HISTORY SCHEMA COULD NOT BE RESOLVED"
            )
            print("DATABASE WRITE OPERATIONS : NONE")
            return

        results = []

        for symbol in SYMBOLS:
            result = verify_symbol(
                conn,
                history_schema,
                symbol,
            )

            results.append(result)

        total_comparisons = sum(
            item["comparisons"]
            for item in results
        )

        total_matches = sum(
            item["matches"]
            for item in results
        )

        total_mismatches = (
            total_comparisons
            - total_matches
        )

        unresolved = sum(
            1
            for item in results
            if item["status"] == "UNRESOLVED"
        )

        print()
        print("=" * 100)
        print(
            "FINAL POST-REPAIR PRODUCTION "
            "PATH VERIFICATION SUMMARY"
        )
        print("=" * 100)
        print(
            f"SYMBOLS CHECKED       : {len(SYMBOLS)}"
        )
        print(
            f"TOTAL COMPARISONS     : {total_comparisons}"
        )
        print(
            f"TOTAL MATCH           : {total_matches}"
        )
        print(
            f"TOTAL MISMATCH        : {total_mismatches}"
        )
        print(
            f"TOTAL UNRESOLVED      : {unresolved}"
        )

        print()
        print("TARGET MATRIX")
        print("-" * 100)

        for item in results:
            print(
                f"  [{item['status']:18}] : "
                f"{item['symbol']}"
            )

        if (
            unresolved == 0
            and total_comparisons == 12
            and total_matches == 12
            and total_mismatches == 0
        ):
            final_status = "VERIFIED"
            reason = (
                "POST-REPAIR PRODUCTION VALUES MATCH "
                "INDEPENDENT STANDARD RECONSTRUCTION"
            )

        elif unresolved > 0:
            final_status = "REVIEW_REQUIRED"
            reason = (
                "ONE OR MORE PRODUCTION TARGETS "
                "COULD NOT BE VERIFIED"
            )

        else:
            final_status = "DIFFERENCE_DETECTED"
            reason = (
                "POST-REPAIR PRODUCTION VALUES "
                "STILL DIFFER FROM STANDARD"
            )

        print()
        print("=" * 100)
        print("FINAL CONCLUSION")
        print("=" * 100)
        print(f"STATUS                : {final_status}")
        print(f"REASON                : {reason}")

        if final_status == "VERIFIED":
            print(
                "NEXT FRONTIER         : "
                "INDICATOR_REPAIR_REGRESSION_GUARD_AUDIT"
            )

        elif final_status == "DIFFERENCE_DETECTED":
            print(
                "NEXT FRONTIER         : "
                "REOPEN CAUSE FORENSICS"
            )

        else:
            print(
                "NEXT FRONTIER         : "
                "RESOLVE UNVERIFIED TARGETS"
            )

        print()
        print("DATABASE WRITE OPERATIONS : NONE")
        print("ENGINE MODIFICATIONS      : NONE")
        print("PRODUCTION RECALCULATION  : NONE")
        print("AUDIT COMPLETE")

    finally:
        conn.close()


if __name__ == "__main__":
    main()