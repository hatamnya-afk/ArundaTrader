from pathlib import Path
import sqlite3
import math
import re
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

LOOKBACK = 120
MIN_HISTORY = 30
ABS_TOLERANCE = 1e-10
REL_TOLERANCE = 1e-10

SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]

EXPECTED_ENGINE_VERSION = "MARKET_DATA_CMC_SNAPSHOT_v0.2"


def line():
    print("-" * 100)


def section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def safe_text(value):
    if value is None:
        return "<NULL>"
    return str(value)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def mean(values):
    if not values:
        return None
    return sum(values) / len(values)


def standard_ema(values, period):
    if len(values) < period:
        return None

    seed = sum(values[:period]) / period
    alpha = 2.0 / (period + 1.0)

    ema_value = seed

    for value in values[period:]:
        ema_value = alpha * value + (1.0 - alpha) * ema_value

    return ema_value


def standard_rsi_wilder(values, period=14):
    if len(values) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        if avg_gain == 0:
            rsi = 50.0
        else:
            rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

        if avg_loss == 0:
            if avg_gain == 0:
                rsi = 50.0
            else:
                rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

    return rsi


def compare_values(current, standard):
    if current is None or standard is None:
        return None, None, "UNRESOLVED"

    if not is_number(current) or not is_number(standard):
        return None, None, "UNRESOLVED"

    abs_error = abs(current - standard)

    denominator = max(abs(standard), 1e-30)
    rel_error = abs_error / denominator

    if abs_error <= ABS_TOLERANCE or rel_error <= REL_TOLERANCE:
        status = "EXACT"
    else:
        status = "MISMATCH"

    return abs_error, rel_error, status


def get_table_names(conn):
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    return [row[0] for row in rows]


def get_columns(conn, table_name):
    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row[1] for row in rows]


def choose_history_source(conn, columns):
    required = {
        "symbol",
        "source_timestamp",
        "close",
    }

    if required.issubset(set(columns)):
        return "market_data"

    return None


def fetch_target(conn, symbol):
    columns = get_columns(conn, "market_data")

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

    if not required.issubset(set(columns)):
        return None

    row = conn.execute(
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
          AND ema20 IS NOT NULL
          AND ema50 IS NOT NULL
          AND rsi14 IS NOT NULL
        ORDER BY source_timestamp DESC, id DESC
        LIMIT 1
        """,
        (symbol,),
    ).fetchone()

    return row


def fetch_history(conn, symbol, target_time):
    columns = get_columns(conn, "market_data")

    if "source_timestamp" not in columns:
        return []

    rows = conn.execute(
        """
        SELECT
            source_timestamp,
            close,
            engine_version
        FROM market_data
        WHERE symbol = ?
          AND close IS NOT NULL
          AND source_timestamp <= ?
        ORDER BY source_timestamp ASC
        LIMIT ?
        """,
        (symbol, target_time, LOOKBACK),
    ).fetchall()

    return rows


def normalize_engine_versions(rows):
    values = []

    for row in rows:
        if len(row) >= 3:
            value = row[2]

            if value is not None:
                value = str(value).strip()

                if value:
                    values.append(value)

    return sorted(set(values))


def scan_engine_source(text):
    signals = {}

    signals["EMA_FUNCTION"] = bool(
        re.search(r"\bdef\s+ema\s*\(", text)
    )

    signals["EMA_SERIES"] = bool(
        re.search(r"\bdef\s+ema_series\s*\(", text)
    )

    signals["RSI_FUNCTION"] = bool(
        re.search(r"\bdef\s+rsi\s*\(", text)
    )

    signals["EMA_ALPHA"] = bool(
        re.search(
            r"2\s*[/]\s*\(\s*period\s*\+\s*1\s*\)",
            text
        )
        or
        re.search(
            r"2\.0\s*[/]\s*\(\s*period\s*\+\s*1\.0\s*\)",
            text
        )
    )

    signals["EMA_SEED"] = bool(
        re.search(
            r"(mean|sum)\s*\([^)]*values[^)]*\[:\s*period",
            text,
            re.IGNORECASE,
        )
    )

    signals["EMA_RECURSIVE"] = bool(
        re.search(
            r"(ema_value|ema)\s*=\s*.*alpha.*value",
            text,
            re.IGNORECASE,
        )
        or
        re.search(
            r"ema\s*=\s*alpha.*\+.*ema",
            text,
            re.IGNORECASE,
        )
    )

    signals["RSI_GAIN_LOSS"] = bool(
        re.search(r"\bgains?\b", text, re.IGNORECASE)
        and
        re.search(r"\bloss(?:es)?\b", text, re.IGNORECASE)
    )

    signals["RSI_INITIAL_AVG"] = bool(
        re.search(
            r"(avg_gain|average_gain).*(mean|period)",
            text,
            re.IGNORECASE,
        )
        or
        re.search(
            r"(avg_loss|average_loss).*(mean|period)",
            text,
            re.IGNORECASE,
        )
    )

    signals["RSI_WILDER"] = bool(
        re.search(
            r"\(.*period\s*-\s*1.*\).*period",
            text,
            re.IGNORECASE,
        )
        or
        re.search(
            r"/\s*period",
            text,
            re.IGNORECASE,
        )
    )

    signals["RSI_FORMULA"] = bool(
        re.search(
            r"100\s*-\s*100\s*/",
            text,
            re.IGNORECASE,
        )
        or
        re.search(
            r"100\.0\s*-\s*\(\s*100\.0\s*/",
            text,
            re.IGNORECASE,
        )
    )

    return signals


def print_engine_forensics():
    section("ENGINE SOURCE FORENSIC INVENTORY")

    print("ENGINE PATH       :", ENGINE_PATH)
    print("ENGINE FOUND      :", ENGINE_PATH.exists())

    if not ENGINE_PATH.exists():
        return {}

    text = ENGINE_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )

    print("SOURCE SIZE       :", len(text), "characters")
    print("SOURCE LINES      :", len(text.splitlines()))

    signals = scan_engine_source(text)

    print()
    print("FUNCTION SIGNALS")
    print("  EMA FUNCTION    :", signals["EMA_FUNCTION"])
    print("  EMA SERIES      :", signals["EMA_SERIES"])
    print("  RSI FUNCTION    :", signals["RSI_FUNCTION"])

    print()
    print("EMA CONVENTION SIGNALS")
    print("  EMA ALPHA       :", signals["EMA_ALPHA"])
    print("  EMA SEED        :", signals["EMA_SEED"])
    print("  EMA RECURSIVE   :", signals["EMA_RECURSIVE"])

    print()
    print("RSI CONVENTION SIGNALS")
    print("  GAIN / LOSS     :", signals["RSI_GAIN_LOSS"])
    print("  INITIAL AVG     :", signals["RSI_INITIAL_AVG"])
    print("  WILDER SMOOTH   :", signals["RSI_WILDER"])
    print("  RSI FORMULA     :", signals["RSI_FORMULA"])

    return signals


def main():
    section(
        "ARUNDA INDICATOR STANDARD CONVENTION DIFFERENCE FORENSIC AUDIT v0.3"
    )

    print("MODE              : READ ONLY")
    print("DATABASE           : arunda.db")
    print("DATABASE WRITE     : NONE")
    print("FORMULA WRITE      : NONE")
    print("PURPOSE            : DIFFERENCE FORENSIC ANALYSIS")

    section("STANDARD TARGET")

    print(
        "EMA20 / EMA50 : alpha=2/(period+1), SMA seed, recursive EMA"
    )
    print(
        "RSI14         : Wilder RSI, arithmetic initial averages, Wilder smoothing"
    )

    section("DATABASE INVENTORY")

    print("DATABASE PATH     :", DB_PATH)
    print("DATABASE FOUND     :", DB_PATH.exists())

    if not DB_PATH.exists():
        print()
        print("FINAL STATUS       : BLOCKED")
        print("REASON             : DATABASE NOT FOUND")
        return

    try:
        conn = sqlite3.connect(str(DB_PATH))
    except Exception as exc:
        print()
        print("FINAL STATUS       : BLOCKED")
        print("DATABASE ERROR     :", repr(exc))
        return

    try:
        tables = get_table_names(conn)

        print("TABLE COUNT        :", len(tables))
        print("MARKET_DATA        :", "FOUND" if "market_data" in tables else "MISSING")

        if "market_data" not in tables:
            print()
            print("FINAL STATUS       : BLOCKED")
            print("REASON             : market_data TABLE NOT FOUND")
            return

        md_columns = get_columns(conn, "market_data")
        print("COLUMN COUNT       :", len(md_columns))

        engine_signals = print_engine_forensics()

        total_exact = 0
        total_mismatch = 0
        total_unresolved = 0
        symbols_checked = 0

        forensic_causes = Counter()

        for symbol in SYMBOLS:
            section("SYMBOL : " + symbol)

            target = fetch_target(conn, symbol)

            if target is None:
                print("ANALYSIS TARGET    : NOT FOUND")
                print("TARGET STATUS      : UNRESOLVED")

                total_unresolved += 3
                forensic_causes["NO_VALID_TARGET"] += 3
                continue

            (
                analysis_id,
                target_symbol,
                source_time,
                engine_version,
                close_value,
                current_ema20,
                current_ema50,
                current_rsi14,
            ) = target

            symbols_checked += 1

            print("ANALYSIS ID        :", analysis_id)
            print("SOURCE TIME        :", source_time)
            print("ENGINE VERSION     :", safe_text(engine_version))
            print("STORED CLOSE       :", close_value)

            print()
            print("CURRENT IMPLEMENTATION")
            line()

            print("Current EMA20      :", current_ema20)
            print("Current EMA50      :", current_ema50)
            print("Current RSI14      :", current_rsi14)

            history = fetch_history(
                conn,
                symbol,
                source_time,
            )

            print()
            print("HISTORY FORENSIC")
            line()

            print("REQUESTED LOOKBACK :", LOOKBACK)
            print("HISTORY FOUND      :", len(history))

            if history:
                print("HISTORY FIRST      :", history[0][0])
                print("HISTORY LAST       :", history[-1][0])

            if len(history) < MIN_HISTORY:
                print("HISTORY STATUS     : INSUFFICIENT")

                print()
                print("FORENSIC CAUSE")
                print("  [UNRESOLVED]     : INSUFFICIENT HISTORY")

                total_unresolved += 3
                forensic_causes["INSUFFICIENT_HISTORY"] += 3

                continue

            closes = []

            for row in history:
                value = row[1]

                if value is None:
                    continue

                try:
                    value = float(value)
                except (TypeError, ValueError):
                    continue

                if math.isfinite(value):
                    closes.append(value)

            print("VALID CLOSES       :", len(closes))

            if len(closes) < MIN_HISTORY:
                print("HISTORY STATUS     : INSUFFICIENT_VALID_CLOSES")

                total_unresolved += 3
                forensic_causes["INSUFFICIENT_VALID_CLOSES"] += 3

                continue

            standard_ema20 = standard_ema(closes, 20)
            standard_ema50 = standard_ema(closes, 50)
            standard_rsi14 = standard_rsi_wilder(closes, 14)

            print()
            print("STANDARD CONVENTION RECONSTRUCTION")
            line()

            print("Standard EMA20     :", standard_ema20)
            print("Standard EMA50     :", standard_ema50)
            print("Standard RSI14     :", standard_rsi14)

            print()
            print("CURRENT IMPLEMENTATION vs STANDARD")
            line()

            symbol_exact = 0
            symbol_mismatch = 0
            symbol_unresolved = 0

            comparisons = [
                ("EMA20", current_ema20, standard_ema20),
                ("EMA50", current_ema50, standard_ema50),
                ("RSI14", current_rsi14, standard_rsi14),
            ]

            for indicator, current, standard in comparisons:
                abs_error, rel_error, status = compare_values(
                    current,
                    standard,
                )

                print()
                print("INDICATOR :", indicator)
                print("CURRENT   :", current)
                print("STANDARD  :", standard)
                print("ABS ERR   :", abs_error)
                print("REL ERR   :", rel_error)
                print("STATUS    :", status)

                if status == "EXACT":
                    symbol_exact += 1
                    total_exact += 1
                    forensic_causes[indicator + "_EXACT"] += 1

                elif status == "MISMATCH":
                    symbol_mismatch += 1
                    total_mismatch += 1
                    forensic_causes[indicator + "_MISMATCH"] += 1

                else:
                    symbol_unresolved += 1
                    total_unresolved += 1
                    forensic_causes[indicator + "_UNRESOLVED"] += 1

            print()
            print("SYMBOL SUMMARY")
            print("  EXACT      :", symbol_exact)
            print("  MISMATCH   :", symbol_mismatch)
            print("  UNRESOLVED :", symbol_unresolved)

            if symbol_unresolved > 0:
                print("SYMBOL STATUS : UNRESOLVED")
            elif symbol_mismatch > 0:
                print("SYMBOL STATUS : MISMATCH")
            else:
                print("SYMBOL STATUS : EXACT")

            print()
            print("SOURCE CONVENTION SIGNAL INTERPRETATION")
            line()

            if engine_signals:
                if (
                    engine_signals["EMA_FUNCTION"]
                    and not engine_signals["EMA_ALPHA"]
                    and not engine_signals["EMA_SEED"]
                    and not engine_signals["EMA_RECURSIVE"]
                ):
                    print(
                        "EMA FORENSIC       : FUNCTION EXISTS BUT STANDARD FORM SIGNALS NOT EXPLICIT"
                    )

                if (
                    engine_signals["RSI_FUNCTION"]
                    and not engine_signals["RSI_GAIN_LOSS"]
                    and not engine_signals["RSI_INITIAL_AVG"]
                    and not engine_signals["RSI_WILDER"]
                    and not engine_signals["RSI_FORMULA"]
                ):
                    print(
                        "RSI FORENSIC       : FUNCTION EXISTS BUT STANDARD FORM SIGNALS NOT EXPLICIT"
                    )

            print()
            print("DIFFERENCE INTERPRETATION")
            line()

            if symbol_mismatch == 3:
                print(
                    "  [CONFIRMED]       : ALL THREE TARGET INDICATORS DIFFER"
                )
                print(
                    "  [FORENSIC NOTE]   : Difference is deterministic against reconstructed standard"
                )

            elif symbol_mismatch > 0:
                print(
                    "  [CONFIRMED]       : SOME INDICATORS DIFFER"
                )

            elif symbol_exact == 3:
                print(
                    "  [CONFIRMED]       : CURRENT VALUES MATCH STANDARD"
                )

        section("FINAL DIFFERENCE FORENSIC SUMMARY")

        print("SYMBOLS CHECKED       :", symbols_checked)
        print("TOTAL EXACT           :", total_exact)
        print("TOTAL MISMATCH        :", total_mismatch)
        print("TOTAL UNRESOLVED      :", total_unresolved)

        print()
        print("FORENSIC CAUSE COUNTS")
        line()

        if forensic_causes:
            for key in sorted(forensic_causes):
                print(
                    f"  {key:<28} : {forensic_causes[key]}"
                )
        else:
            print("  NONE")

        print()
        print("FORENSIC CONCLUSION")
        line()

        if total_unresolved > 0 and total_mismatch == 0:
            print("STATUS : REVIEW_REQUIRED")
            print(
                "REASON : INSUFFICIENT DATA OR TARGET RESOLUTION"
            )

        elif total_mismatch > 0:
            print("STATUS : DIFFERENCE_CONFIRMED")
            print(
                "REASON : CURRENT IMPLEMENTATION VALUES DIFFER FROM STANDARD CONVENTION"
            )

        else:
            print("STATUS : NO_DIFFERENCE_DETECTED")
            print(
                "REASON : CURRENT VALUES MATCH STANDARD CONVENTION"
            )

        print()
        print("DATABASE WRITE OPERATIONS : NONE")
        print("ENGINE MODIFICATIONS      : NONE")
        print("FORMULA WRITE             : NONE")
        print("AUDIT COMPLETE")

    finally:
        conn.close()


if __name__ == "__main__":
    main()