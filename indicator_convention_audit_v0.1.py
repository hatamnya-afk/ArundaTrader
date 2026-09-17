import os
import re

ENGINE_PATH = r"C:\Users\ASUS\ArundaTrader\market_data_engine.py"

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


def separator(char="=", count=100):
    print(char * count)


def read_source(path):
    if not os.path.exists(path):
        return ""

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def find_lines(text, keywords):
    lines = text.splitlines()
    results = []

    for index, line in enumerate(lines, start=1):

        lower_line = line.lower()

        for keyword in keywords:

            if keyword.lower() in lower_line:

                results.append(
                    (
                        index,
                        line.strip()
                    )
                )

                break

    return results


def find_numeric_constants(text):
    patterns = [
        r"EMA[_ ]?20\s*=\s*([0-9]+)",
        r"EMA[_ ]?50\s*=\s*([0-9]+)",
        r"RSI[_ ]?14\s*=\s*([0-9]+)",
        r"ATR[_ ]?14\s*=\s*([0-9]+)",
        r"ADX[_ ]?14\s*=\s*([0-9]+)",
        r"BB[_ ]?PERIOD\s*=\s*([0-9]+)",
        r"VOLUME[_ ]?SMA[_ ]?PERIOD\s*=\s*([0-9]+)",
    ]

    results = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if matches:

            results.append(
                (
                    pattern,
                    matches
                )
            )

    return results


def detect_methods(text):

    methods = []

    checks = [
        ("EWMA", r"\bewm\b"),
        ("EMA", r"\bema\b"),
        ("SMA", r"\bsma\b"),
        ("ROLLING", r"\.rolling\s*\("),
        ("STD", r"\.std\s*\("),
        ("WILDER", r"wilder"),
        ("TRUE_RANGE", r"true.?range"),
        ("TR", r"\btr\b"),
        ("RSI", r"\brsi\b"),
        ("MACD", r"\bmacd\b"),
        ("ADX", r"\badx\b"),
        ("ATR", r"\batr\b"),
        ("DI_PLUS", r"\+\s*di|\bplus_di\b"),
        ("DI_MINUS", r"-\s*di|\bminus_di\b"),
        ("DX", r"\bdx\b"),
        ("STDDEV", r"stddev|standard.?deviation"),
        ("LOG_RETURN", r"log.?return|np\.log"),
        ("PCT_RETURN", r"pct.?change|percent.?change"),
        ("ANNUALIZATION", r"annual|annualiz"),
        ("CLIP", r"\.clip\s*\("),
        ("ROUND", r"\.round\s*\("),
    ]

    for name, pattern in checks:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):
            methods.append(name)

    return methods


def print_formula_section(
    formula,
    text,
    keywords
):

    separator("-")

    print("FORMULA :", formula)

    matches = find_lines(
        text,
        keywords
    )

    if not matches:

        print("STATUS  : NO DIRECT SOURCE MATCH")
        return

    print("STATUS  : SOURCE REFERENCES FOUND")
    print()

    limit = 12

    for line_number, line in matches[:limit]:

        print(
            "LINE {:>5} : {}".format(
                line_number,
                line
            )
        )

    if len(matches) > limit:

        print(
            "... {} additional matches".format(
                len(matches) - limit
            )
        )


def main():

    separator()

    print("ARUNDA INDICATOR CONVENTION AUDIT v0.1")

    separator()

    print("MODE            : READ ONLY")
    print("SOURCE          : market_data_engine.py")
    print("DATABASE WRITE  : NONE")
    print("FORMULA CALC    : NONE")
    print("PURPOSE         : SEMANTIC / CONVENTION SCAN")

    separator()

    print("SOURCE INVENTORY")

    separator("-")

    print("ENGINE PATH     :", ENGINE_PATH)
    print("ENGINE FOUND    :", os.path.exists(ENGINE_PATH))

    if not os.path.exists(ENGINE_PATH):

        print()
        print("AUDIT STATUS    : BLOCKED")
        print("REASON          : ENGINE_SOURCE_NOT_FOUND")
        separator()

        return

    text = read_source(
        ENGINE_PATH
    )

    print("SOURCE SIZE     :", len(text), "characters")
    print(
        "SOURCE LINES    :",
        len(text.splitlines())
    )

    separator()

    print("ENGINE VERSION SCAN")

    separator("-")

    version_matches = find_lines(
        text,
        [
            "ENGINE_VERSION",
            "MARKET_DATA_CMC_SNAPSHOT_v0.2",
        ]
    )

    if version_matches:

        for line_number, line in version_matches[:10]:

            print(
                "LINE {:>5} : {}".format(
                    line_number,
                    line
                )
            )

    else:

        print(
            "ENGINE VERSION  : NOT DIRECTLY DETECTED"
        )

    separator()

    print("PERIOD / CONSTANT SCAN")

    separator("-")

    constants = find_numeric_constants(
        text
    )

    if constants:

        for pattern, values in constants:

            print(
                "PATTERN :",
                pattern
            )

            print(
                "VALUES  :",
                ", ".join(values)
            )

    else:

        print("NO EXPLICIT PERIOD CONSTANTS DETECTED")

    separator()

    print("METHOD / CONVENTION SIGNALS")

    separator("-")

    methods = detect_methods(
        text
    )

    if methods:

        for method in methods:

            print(
                "  [DETECTED] :",
                method
            )

    else:

        print("NO METHOD SIGNALS DETECTED")

    separator()

    print("INDICATOR SOURCE MAP")

    separator("-")

    formula_keywords = {

        "EMA20": [
            "ema20",
            "EMA20",
            "span=20",
            "period=20",
        ],

        "EMA50": [
            "ema50",
            "EMA50",
            "span=50",
            "period=50",
        ],

        "RSI14": [
            "rsi14",
            "RSI14",
            "rsi",
        ],

        "MACD": [
            "macd",
            "MACD",
        ],

        "MACD_SIGNAL": [
            "macd_signal",
            "MACD_SIGNAL",
            "signal",
        ],

        "MACD_HIST": [
            "macd_hist",
            "MACD_HIST",
            "histogram",
        ],

        "ATR14": [
            "atr14",
            "ATR14",
            "true_range",
            "true range",
        ],

        "ADX14": [
            "adx14",
            "ADX14",
            "adx",
            "plus_di",
            "minus_di",
            "dx",
        ],

        "BB_MIDDLE": [
            "bb_middle",
            "BB_MIDDLE",
            "bollinger",
        ],

        "BB_UPPER": [
            "bb_upper",
            "BB_UPPER",
            "bollinger",
        ],

        "BB_LOWER": [
            "bb_lower",
            "BB_LOWER",
            "bollinger",
        ],

        "BB_WIDTH": [
            "bb_width",
            "BB_WIDTH",
            "bollinger",
        ],

        "VOLUME_SMA20": [
            "volume_sma20",
            "VOLUME_SMA20",
            "volume_sma",
        ],

        "VOLUME_RATIO": [
            "volume_ratio",
            "VOLUME_RATIO",
            "volume /",
            "volume/",
        ],

        "VOLATILITY": [
            "volatility",
            "VOLATILITY",
            "pct_change",
            "returns",
            "std",
        ],

        "TECHNICAL_SCORE": [
            "technical_score",
            "TECHNICAL_SCORE",
            "score",
        ],
    }

    for formula in FORMULAS:

        print_formula_section(
            formula,
            text,
            formula_keywords[formula]
        )

    separator()

    print("DETAILED CONVENTION SIGNAL SCAN")

    separator("-")

    convention_groups = {

        "EMA SEED / SMOOTHING": [
            "ewm",
            "span",
            "adjust",
            "alpha",
            "ema",
        ],

        "RSI CONVENTION": [
            "gain",
            "loss",
            "avg_gain",
            "avg_loss",
            "rsi",
            "ewm",
            "rolling",
        ],

        "MACD CONVENTION": [
            "ema12",
            "ema26",
            "signal",
            "macd",
        ],

        "ATR CONVENTION": [
            "true_range",
            "true range",
            "high-low",
            "prev_close",
            "atr",
        ],

        "ADX CONVENTION": [
            "plus_dm",
            "minus_dm",
            "plus_di",
            "minus_di",
            "dx",
            "adx",
        ],

        "BOLLINGER CONVENTION": [
            "rolling",
            "std",
            "ddof",
            "bb_middle",
            "bb_upper",
            "bb_lower",
        ],

        "VOLUME CONVENTION": [
            "volume_sma",
            "volume_ratio",
            "rolling",
            "volume",
        ],

        "VOLATILITY CONVENTION": [
            "pct_change",
            "returns",
            "log_return",
            "std",
            "annual",
            "annualiz",
        ],

        "SCORE CONVENTION": [
            "technical_score",
            "score",
            "threshold",
            "weight",
            "points",
            "clip",
            "round",
        ],
    }

    for group, keywords in convention_groups.items():

        print()

        print("GROUP :", group)

        matches = find_lines(
            text,
            keywords
        )

        if not matches:

            print(
                "STATUS : NO DIRECT SIGNAL"
            )

            continue

        print(
            "MATCHES :",
            len(matches)
        )

        for line_number, line in matches[:15]:

            print(
                "LINE {:>5} : {}".format(
                    line_number,
                    line
                )
            )

        if len(matches) > 15:

            print(
                "... {} additional matches".format(
                    len(matches) - 15
                )
            )

    separator()

    print("FINAL AUDIT SUMMARY")

    separator("-")

    detected_count = 0

    for formula in FORMULAS:

        matches = find_lines(
            text,
            formula_keywords[formula]
        )

        if matches:

            detected_count += 1

    print(
        "EXPECTED INDICATORS :",
        len(FORMULAS)
    )

    print(
        "SOURCE REFERENCES    :",
        detected_count
    )

    print(
        "SOURCE GAPS          :",
        len(FORMULAS) - detected_count
    )

    if detected_count == len(FORMULAS):

        print(
            "CONVENTION SCAN      : COMPLETE"
        )

    else:

        print(
            "CONVENTION SCAN      : PARTIAL"
        )

    print()
    print(
        "DATABASE WRITE OPERATIONS : NONE"
    )

    print(
        "FORMULA CALCULATIONS      : NONE"
    )

    print(
        "AUDIT COMPLETE"
    )

    separator()


if __name__ == "__main__":
    main()