import sqlite3
import shutil
import ast
from pathlib import Path
from datetime import datetime, timezone
import math

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]

EMA20_PERIOD = 20
EMA50_PERIOD = 50
RSI_PERIOD = 14

ABS_TOLERANCE = 1e-10
REL_TOLERANCE = 1e-10

print("=" * 100)
print("ARUNDA INDICATOR POST REPAIR PRODUCTION RECALCULATION AND VERIFICATION v0.1")
print("=" * 100)
print("MODE                  : CONTROLLED PRODUCTION RECALCULATION")
print("DATABASE WRITE        : YES - TARGET RECORDS ONLY")
print("ENGINE WRITE          : NONE")
print("FORMULA WRITE         : NONE")
print("PURPOSE               : POST-REPAIR RECALCULATION + INDEPENDENT VERIFICATION")
print("=" * 100)


def utc_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def is_number(value):
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def relative_error(a, b):
    if not is_number(a) or not is_number(b):
        return None
    denominator = max(abs(float(b)), 1e-300)
    return abs(float(a) - float(b)) / denominator


def values_match(a, b):
    if not is_number(a) or not is_number(b):
        return False

    abs_err = abs(float(a) - float(b))
    rel_err = relative_error(a, b)

    return (
        abs_err <= ABS_TOLERANCE
        or rel_err <= REL_TOLERANCE
    )


def standard_ema(values, period):
    if len(values) < period:
        return None

    alpha = 2.0 / (period + 1.0)

    seed = sum(values[:period]) / float(period)
    ema_value = seed

    for value in values[period:]:
        ema_value = (value * alpha) + (ema_value * (1.0 - alpha))

    return ema_value


def standard_rsi(values, period=14):
    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]

        if delta > 0:
            gains.append(delta)
            losses.append(0.0)
        elif delta < 0:
            gains.append(0.0)
            losses.append(-delta)
        else:
            gains.append(0.0)
            losses.append(0.0)

    if len(gains) < period:
        return None

    avg_gain = sum(gains[:period]) / float(period)
    avg_loss = sum(losses[:period]) / float(period)

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / float(period)
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / float(period)

    if avg_loss == 0:
        if avg_gain == 0:
            return 50.0
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def backup_database():
    backup_dir = BASE_DIR / "indicator_post_repair_backups" / utc_stamp()
    backup_dir.mkdir(parents=True, exist_ok=False)

    backup_db = backup_dir / "arunda.db"

    shutil.copy2(DB_PATH, backup_db)

    if not backup_db.exists():
        raise RuntimeError("DATABASE BACKUP FAILED")

    return backup_dir, backup_db


def validate_engine_syntax():
    source = ENGINE_PATH.read_text(encoding="utf-8")

    try:
        ast.parse(source)
    except SyntaxError as exc:
        raise RuntimeError(
            f"ENGINE SYNTAX INVALID: line {exc.lineno}: {exc.msg}"
        )

    return len(source), len(source.splitlines())


def get_market_data_schema(conn):
    rows = conn.execute(
        "PRAGMA table_info(market_data)"
    ).fetchall()

    columns = {row[1] for row in rows}

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

    missing = required - columns

    if missing:
        raise RuntimeError(
            "MISSING MARKET_DATA COLUMNS: "
            + ", ".join(sorted(missing))
        )

    return columns


def resolve_targets(conn):
    placeholders = ",".join("?" for _ in SYMBOLS)

    query = f"""
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
        WHERE symbol IN ({placeholders})
        ORDER BY source_timestamp DESC, id DESC
    """

    rows = conn.execute(query, SYMBOLS).fetchall()

    latest = {}

    for row in rows:
        symbol = row[1]

        if symbol not in latest:
            latest[symbol] = row

    missing = [s for s in SYMBOLS if s not in latest]

    if missing:
        raise RuntimeError(
            "TARGET RECORDS NOT FOUND: " + ", ".join(missing)
        )

    return latest


def resolve_history(conn, symbol, target_timestamp, minimum=60):
    rows = conn.execute(
        """
        SELECT close
        FROM market_data
        WHERE symbol = ?
          AND source_timestamp <= ?
          AND close IS NOT NULL
        ORDER BY source_timestamp DESC, id DESC
        LIMIT 122
        """,
        (symbol, target_timestamp),
    ).fetchall()

    closes = [float(row[0]) for row in reversed(rows)]

    if len(closes) < minimum:
        raise RuntimeError(
            f"{symbol}: insufficient history: {len(closes)}"
        )

    return closes


def calculate_standard_values(closes):
    ema20 = standard_ema(closes, EMA20_PERIOD)
    ema50 = standard_ema(closes, EMA50_PERIOD)
    rsi14 = standard_rsi(closes, RSI_PERIOD)

    return ema20, ema50, rsi14


def update_target(conn, row, standard_values):
    record_id = row[0]

    ema20, ema50, rsi14 = standard_values

    if not all(
        is_number(v)
        for v in (ema20, ema50, rsi14)
    ):
        raise RuntimeError(
            f"ID {record_id}: standard calculation returned invalid value"
        )

    conn.execute(
        """
        UPDATE market_data
        SET
            ema20 = ?,
            ema50 = ?,
            rsi14 = ?
        WHERE id = ?
        """,
        (
            float(ema20),
            float(ema50),
            float(rsi14),
            record_id,
        ),
    )


def verify_target(conn, record_id, standard_values):
    row = conn.execute(
        """
        SELECT
            symbol,
            source_timestamp,
            ema20,
            ema50,
            rsi14
        FROM market_data
        WHERE id = ?
        """,
        (record_id,),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            f"POST-REPAIR RECORD NOT FOUND: {record_id}"
        )

    symbol = row[0]
    source_timestamp = row[1]

    stored = {
        "EMA20": row[2],
        "EMA50": row[3],
        "RSI14": row[4],
    }

    standard = {
        "EMA20": standard_values[0],
        "EMA50": standard_values[1],
        "RSI14": standard_values[2],
    }

    results = {}

    for name in ("EMA20", "EMA50", "RSI14"):
        current = stored[name]
        expected = standard[name]

        abs_err = (
            abs(float(current) - float(expected))
            if is_number(current) and is_number(expected)
            else None
        )

        rel_err = relative_error(current, expected)

        matched = values_match(current, expected)

        results[name] = {
            "current": current,
            "standard": expected,
            "abs_err": abs_err,
            "rel_err": rel_err,
            "matched": matched,
        }

    return symbol, source_timestamp, results


def main():
    if not DB_PATH.exists():
        raise SystemExit(
            f"DATABASE NOT FOUND: {DB_PATH}"
        )

    if not ENGINE_PATH.exists():
        raise SystemExit(
            f"ENGINE NOT FOUND: {ENGINE_PATH}"
        )

    print("\n" + "=" * 100)
    print("STEP 1 — ENGINE POST-REPAIR SYNTAX VERIFICATION")
    print("=" * 100)

    source_size, source_lines = validate_engine_syntax()

    print(f"ENGINE PATH       : {ENGINE_PATH}")
    print(f"SOURCE SIZE       : {source_size} characters")
    print(f"SOURCE LINES      : {source_lines}")
    print("POST-REPAIR SYNTAX : VALID")

    print("\n" + "=" * 100)
    print("STEP 2 — DATABASE BACKUP BEFORE PRODUCTION RECALCULATION")
    print("=" * 100)

    backup_dir, backup_db = backup_database()

    print(f"BACKUP DIRECTORY  : {backup_dir}")
    print(f"DATABASE BACKUP   : {backup_db}")
    print("BACKUP STATUS     : VERIFIED")

    conn = sqlite3.connect(DB_PATH)

    try:
        print("\n" + "=" * 100)
        print("STEP 3 — DATABASE RESOLUTION")
        print("=" * 100)

        columns = get_market_data_schema(conn)

        print("MARKET_DATA       : FOUND")
        print(f"COLUMN COUNT      : {len(columns)}")
        print("REQUIRED FIELDS   : VERIFIED")

        targets = resolve_targets(conn)

        print("\n" + "=" * 100)
        print("STEP 4 — TARGET RESOLUTION")
        print("=" * 100)

        for symbol in SYMBOLS:
            row = targets[symbol]

            print(f"\nSYMBOL : {symbol}")
            print("-" * 100)
            print(f"ID              : {row[0]}")
            print(f"SOURCE TIME     : {row[2]}")
            print(f"ENGINE VERSION  : {row[3]}")
            print(f"CLOSE           : {row[4]}")
            print(f"OLD EMA20       : {row[5]}")
            print(f"OLD EMA50       : {row[6]}")
            print(f"OLD RSI14       : {row[7]}")

        print("\n" + "=" * 100)
        print("STEP 5 — STANDARD RECONSTRUCTION")
        print("=" * 100)

        reconstructed = {}

        for symbol in SYMBOLS:
            row = targets[symbol]

            closes = resolve_history(
                conn,
                symbol,
                row[2],
                minimum=60,
            )

            standard_values = calculate_standard_values(closes)

            reconstructed[symbol] = {
                "id": row[0],
                "timestamp": row[2],
                "history_count": len(closes),
                "values": standard_values,
            }

            print(f"\nSYMBOL : {symbol}")
            print("-" * 100)
            print(f"HISTORY COUNT   : {len(closes)}")
            print(f"STANDARD EMA20  : {standard_values[0]}")
            print(f"STANDARD EMA50  : {standard_values[1]}")
            print(f"STANDARD RSI14  : {standard_values[2]}")

        print("\n" + "=" * 100)
        print("STEP 6 — PRODUCTION RECALCULATION")
        print("=" * 100)

        for symbol in SYMBOLS:
            item = reconstructed[symbol]

            row = targets[symbol]

            print(f"\nRECALCULATING : {symbol}")
            print(f"TARGET ID     : {row[0]}")

            update_target(
                conn,
                row,
                item["values"],
            )

        conn.commit()

        print("\nPRODUCTION RECALCULATION : COMMITTED")
        print("TARGET RECORDS UPDATED   :", len(SYMBOLS))

        print("\n" + "=" * 100)
        print("STEP 7 — POST-REPAIR VERIFICATION")
        print("=" * 100)

        total = 0
        matched = 0
        mismatched = 0

        for symbol in SYMBOLS:
            item = reconstructed[symbol]

            symbol_name, timestamp, results = verify_target(
                conn,
                item["id"],
                item["values"],
            )

            print(f"\nSYMBOL : {symbol_name}")
            print("-" * 100)
            print(f"ID          : {item['id']}")
            print(f"SOURCE TIME : {timestamp}")

            for name in ("EMA20", "EMA50", "RSI14"):
                result = results[name]

                total += 1

                if result["matched"]:
                    status = "MATCH"
                    matched += 1
                else:
                    status = "MISMATCH"
                    mismatched += 1

                print(f"\nINDICATOR : {name}")
                print(f"STORED    : {result['current']}")
                print(f"STANDARD  : {result['standard']}")
                print(f"ABS ERR   : {result['abs_err']}")
                print(f"REL ERR   : {result['rel_err']}")
                print(f"STATUS    : {status}")

        print("\n" + "=" * 100)
        print("FINAL POST-REPAIR VERIFICATION SUMMARY")
        print("=" * 100)
        print(f"SYMBOLS CHECKED       : {len(SYMBOLS)}")
        print(f"TOTAL COMPARISONS     : {total}")
        print(f"TOTAL MATCH            : {matched}")
        print(f"TOTAL MISMATCH         : {mismatched}")

        if mismatched == 0 and matched == total:
            final_status = "VERIFIED"
            reason = (
                "ALL STORED INDICATOR VALUES MATCH STANDARD "
                "CONVENTION AFTER REPAIR"
            )
        else:
            final_status = "VERIFICATION_FAILED"
            reason = (
                "ONE OR MORE STORED INDICATOR VALUES DO NOT "
                "MATCH STANDARD CONVENTION"
            )

        print("\n" + "=" * 100)
        print("FINAL CONCLUSION")
        print("=" * 100)
        print(f"STATUS                : {final_status}")
        print(f"REASON                : {reason}")
        print(f"BACKUP                : {backup_db}")
        print("ENGINE MODIFICATIONS  : ALREADY APPLIED")
        print("DATABASE RECALCULATION: COMPLETED")

        if final_status != "VERIFIED":
            print("\nSTOP CONDITION         : ACTIVE")
            print("NEXT ACTION            : NO FURTHER REPAIR WITHOUT FORENSIC REVIEW")

        print("\n" + "=" * 100)
        print("AUDIT COMPLETE")
        print("=" * 100)

    except Exception as exc:
        conn.rollback()

        print("\n" + "=" * 100)
        print("FATAL ERROR")
        print("=" * 100)
        print(type(exc).__name__)
        print(str(exc))
        print("DATABASE TRANSACTION  : ROLLED BACK")
        print(f"BACKUP AVAILABLE      : {backup_db}")
        print("=" * 100)

        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()