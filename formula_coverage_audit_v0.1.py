import sqlite3
import re
import os

DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

ENGINE_FILES = [
    r"C:\Users\ASUS\ArundaTrader\market_data_engine.py",
    r"C:\Users\ASUS\ArundaTrader\fusion_engine.py",
]

FORMULAS = [
    "EMA20",
    "EMA50",
    "RSI14",
    "MACD",
    "MACD_SIGNAL",
    "MACD_HIST",
    "ATR14",
    "ADX14",
    "BB_MIDDLE",
    "BB_UPPER",
    "BB_LOWER",
    "BB_WIDTH",
    "VOLUME_SMA20",
    "VOLUME_RATIO",
    "VOLATILITY",
    "TECHNICAL_SCORE",
]

COLUMNS = {
    "EMA20": "ema20",
    "EMA50": "ema50",
    "RSI14": "rsi14",
    "MACD": "macd",
    "MACD_SIGNAL": "macd_signal",
    "MACD_HIST": "macd_hist",
    "ATR14": "atr14",
    "ADX14": "adx14",
    "BB_MIDDLE": "bb_middle",
    "BB_UPPER": "bb_upper",
    "BB_LOWER": "bb_lower",
    "BB_WIDTH": "bb_width",
    "VOLUME_SMA20": "volume_sma20",
    "VOLUME_RATIO": "volume_ratio",
    "VOLATILITY": "volatility",
    "TECHNICAL_SCORE": "technical_score",
}


def separator(char="=", count=100):
    print(char * count)


def read_file(path):
    if not os.path.exists(path):
        return ""

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as exc:
        print("READ ERROR:", path)
        print(exc)
        return ""


def scan_formulas(text):
    found = set()

    for formula in FORMULAS:
        if re.search(r"\b" + re.escape(formula) + r"\b", text):
            found.add(formula)

        lower_formula = formula.lower()

        if re.search(r"\b" + re.escape(lower_formula) + r"\b", text):
            found.add(formula)

    return found


def get_database_info():
    tables = set()
    columns = set()

    if not os.path.exists(DB_PATH):
        return tables, columns

    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )

        rows = cursor.fetchall()

        for row in rows:
            tables.add(row[0])

        if "market_data" in tables:

            cursor.execute(
                "PRAGMA table_info(market_data)"
            )

            rows = cursor.fetchall()

            for row in rows:
                columns.add(row[1])

    finally:
        connection.close()

    return tables, columns


def main():

    separator()

    print("ARUNDA FORMULA COVERAGE AUDIT v0.1")

    separator()

    print("MODE            : READ ONLY")
    print("DATABASE        : arunda.db")
    print("DATABASE WRITE  : NONE")
    print("FORMULA CALC    : NONE")

    separator()

    print("DATABASE INVENTORY")

    separator("-")

    tables, columns = get_database_info()

    print("DATABASE FOUND  :", os.path.exists(DB_PATH))
    print("TABLE COUNT     :", len(tables))

    if "market_data" in tables:
        print("MARKET_DATA     : FOUND")
        print("COLUMN COUNT    :", len(columns))
    else:
        print("MARKET_DATA     : NOT FOUND")

    print()

    print("ENGINE SOURCE SCAN")

    separator("-")

    detected = set()
    sources = {}

    for path in ENGINE_FILES:

        print()
        print("FILE            :", os.path.basename(path))

        if not os.path.exists(path):
            print("STATUS          : NOT FOUND")
            continue

        text = read_file(path)

        print("STATUS          : FOUND")
        print("SOURCE SIZE     :", len(text), "characters")

        found = scan_formulas(text)

        print("FORMULAS FOUND  :", len(found))

        for formula in sorted(found):

            detected.add(formula)

            if formula not in sources:
                sources[formula] = []

            sources[formula].append(
                os.path.basename(path)
            )

            print("  [FOUND]       :", formula)

    separator()

    print("FORMULA COVERAGE")

    separator("-")

    expected = set(FORMULAS)

    covered = detected.intersection(expected)

    not_detected = expected.difference(detected)

    print("EXPECTED FORMULAS :", len(FORMULAS))
    print("DETECTED FORMULAS :", len(detected))
    print("COVERED           :", len(covered))
    print("NOT DETECTED      :", len(not_detected))

    print()

    print("COVERED FORMULAS")

    for formula in sorted(covered):

        source_names = ", ".join(
            sources.get(formula, [])
        )

        print(
            "  [COVERED]      :",
            formula,
            "->",
            source_names
        )

    print()

    print("NOT DETECTED FORMULAS")

    if len(not_detected) == 0:
        print("  NONE")
    else:
        for formula in sorted(not_detected):
            print("  [NOT DETECTED] :", formula)

    separator()

    print("DATABASE FIELD COVERAGE")

    separator("-")

    missing_fields = []

    for formula in FORMULAS:

        column = COLUMNS[formula]

        if column in columns:

            print(
                "  [FIELD PRESENT] :",
                formula,
                "->",
                column
            )

        else:

            missing_fields.append(formula)

            print(
                "  [FIELD MISSING] :",
                formula,
                "->",
                column
            )

    separator()

    print("FINAL SUMMARY")

    separator("-")

    print("EXPECTED FORMULAS :", len(FORMULAS))
    print("DETECTED FORMULAS :", len(detected))
    print("COVERED           :", len(covered))
    print("NOT DETECTED      :", len(not_detected))
    print("MISSING DB FIELDS :", len(missing_fields))

    if len(not_detected) == 0 and len(missing_fields) == 0:
        print("COVERAGE STATUS   : COMPLETE")
    else:
        print("COVERAGE STATUS   : PARTIAL")

    print()
    print("DATABASE WRITE OPERATIONS : NONE")
    print("FORMULA CALCULATIONS      : NONE")
    print("AUDIT COMPLETE")

    separator()


if __name__ == "__main__":
    main()