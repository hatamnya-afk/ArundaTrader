from pathlib import Path
import re
import sys


# =============================================================================
# ARUNDA INDICATOR CONVENTION RECONSTRUCTION v0.1
# =============================================================================
# MODE            : READ ONLY
# DATABASE WRITE  : NONE
# FORMULA CALC    : NONE
# PURPOSE         : Extract implemented mathematical conventions directly
#                   from market_data_engine.py
# =============================================================================


BASE_DIR = Path(__file__).resolve().parent
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

EXPECTED_INDICATORS = [
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

GROUPS = {
    "EMA": [
        "ema",
        "ema_series",
    ],
    "RSI": [
        "rsi",
    ],
    "MACD": [
        "macd",
        "ema12",
        "ema26",
        "signal_series",
        "histogram",
    ],
    "ATR": [
        "true_range",
        "true_ranges",
        "atr",
    ],
    "ADX": [
        "plus_dm",
        "minus_dm",
        "dx_values",
        "plus_di",
        "minus_di",
        "adx",
    ],
    "BOLLINGER": [
        "bollinger",
        "bb_middle",
        "bb_upper",
        "bb_lower",
        "bb_width",
        "deviation",
        "stdev",
    ],
    "VOLUME": [
        "volume_metrics",
        "volume_sma20",
        "volume_ratio",
    ],
    "VOLATILITY": [
        "volatility",
        "returns",
        "stdev",
    ],
    "TECHNICAL_SCORE": [
        "technical_score",
        "score",
    ],
}


def separator(char="=", width=99):
    print(char * width)


def section(title):
    print()
    separator("=")
    print(title)
    separator("=")


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def find_function(source, function_name):
    """
    Extract a Python function body using indentation.
    This is source inspection only.
    """

    pattern = re.compile(
        rf"^def\s+{re.escape(function_name)}\s*\(",
        re.MULTILINE,
    )

    match = pattern.search(source)

    if not match:
        return None, None, None

    start = match.start()

    line_start = source.rfind("\n", 0, start) + 1
    line_number = source.count("\n", 0, line_start) + 1

    next_def = re.search(
        r"^def\s+\w+\s*\(",
        source[match.end():],
        re.MULTILINE,
    )

    if next_def:
        end = match.end() + next_def.start()
    else:
        end = len(source)

    body = source[start:end]

    return body, line_number, end


def print_function_excerpt(source, function_name, max_lines=80):
    body, line_number, _ = find_function(source, function_name)

    if body is None:
        print(f"  [NOT FOUND] {function_name}")
        return False

    lines = body.splitlines()

    print(f"  FUNCTION    : {function_name}")
    print(f"  START LINE  : {line_number}")
    print(f"  SOURCE LINES: {len(lines)}")

    for i, line in enumerate(lines[:max_lines]):
        absolute_line = line_number + i
        print(f"    {absolute_line:5d} : {line}")

    if len(lines) > max_lines:
        print(
            f"    ... {len(lines) - max_lines} additional lines"
        )

    return True


def detect_periods(source):
    patterns = [
        r"period\s*=\s*(\d+)",
        r"period\s*:\s*int\s*=\s*(\d+)",
        r"PERIOD\s*=\s*(\d+)",
    ]

    periods = []

    for pattern in patterns:
        for match in re.finditer(pattern, source):
            value = int(match.group(1))

            if value not in periods:
                periods.append(value)

    return sorted(periods)


def detect_signal_period(source):
    patterns = [
        r"ema_series\s*\([^)]*?,\s*9\s*\)",
        r"signal.*period.*9",
        r"period\s*=\s*9",
    ]

    return any(
        re.search(pattern, source, re.IGNORECASE | re.DOTALL)
        for pattern in patterns
    )


def detect_seed_keywords(body):
    keywords = [
        "mean(",
        "values[:period]",
        "[:period]",
        "seed",
        "initial",
        "smoothing",
        "alpha",
        "2.0 /",
        "period + 1",
        "period-1",
    ]

    found = []

    lower = body.lower()

    for keyword in keywords:
        if keyword.lower() in lower:
            found.append(keyword)

    return found


def detect_formula_signals(body):
    signals = []

    checks = {
        "EMA_SMOOTHING_ALPHA": [
            "2.0 / (period + 1)",
            "2 / (period + 1)",
        ],
        "SMA_SEED": [
            "mean(values[:period])",
            "mean(",
        ],
        "WILDER_STYLE": [
            "((period - 1)",
            "(period - 1)",
            "/ period",
        ],
        "TRUE_RANGE": [
            "high - low",
            "abs(high - previous_close)",
            "abs(low - previous_close)",
        ],
        "RSI_GAIN_LOSS": [
            "gains",
            "losses",
        ],
        "MACD_EMA12": [
            "ema_series(values, 12)",
        ],
        "MACD_EMA26": [
            "ema_series(values, 26)",
        ],
        "MACD_SIGNAL_EMA9": [
            "ema_series(macd_values, 9)",
            "ema_series(",
        ],
        "BOLLINGER_STDEV": [
            "stdev(",
        ],
        "VOLUME_RATIO": [
            "current / average",
            "current / sma",
            "current / volume_sma",
        ],
        "LOG_RETURN": [
            "log(",
        ],
    }

    for name, patterns in checks.items():
        for pattern in patterns:
            if pattern.lower() in body.lower():
                signals.append(name)
                break

    return signals


def reconstruct_indicator(indicator, source):
    """
    Semantic reconstruction from implementation.
    No numeric calculation.
    """

    print()
    separator("-")
    print(f"INDICATOR : {indicator}")
    separator("-")

    if indicator in ("EMA20", "EMA50"):
        body, line, _ = find_function(source, "ema")

        if body:
            print("TYPE        : Exponential Moving Average")
            print("FUNCTION    : ema")
            print("PERIOD      :", "20" if indicator == "EMA20" else "50")

            alpha = re.search(
                r"2\.0\s*/\s*\(\s*period\s*\+\s*1\s*\)",
                body,
            )

            if alpha:
                print("SMOOTHING   : alpha = 2 / (period + 1)")
            else:
                print("SMOOTHING   : NOT EXPLICITLY DETECTED")

            seeds = detect_seed_keywords(body)

            if "mean(" in seeds or "values[:period]" in seeds:
                print("SEED        : INITIAL PERIOD MEAN DETECTED")
            else:
                print("SEED        : NOT EXPLICITLY DETECTED")

            print("STATUS      : RECONSTRUCTED_FROM_SOURCE")
            return True

    if indicator == "RSI14":
        body, line, _ = find_function(source, "rsi")

        if body:
            print("TYPE        : Relative Strength Index")
            print("FUNCTION    : rsi")
            print("PERIOD      : 14")

            if "gains" in body:
                print("GAINS       : DETECTED")

            if "losses" in body:
                print("LOSSES      : DETECTED")

            if "mean(" in body:
                print("INITIAL AVG : ARITHMETIC MEAN SIGNAL DETECTED")

            if "avg_gain" in body:
                print("AVG GAIN    : DETECTED")

            if "avg_loss" in body:
                print("AVG LOSS    : DETECTED")

            if "100" in body and "1 +" in body:
                print("RSI FORM     : STANDARD RSI TRANSFORMATION SIGNAL")

            print("STATUS      : RECONSTRUCTED_FROM_SOURCE")
            return True

    if indicator in ("MACD", "MACD_SIGNAL", "MACD_HIST"):
        body, line, _ = find_function(source, "macd")

        if body:
            print("TYPE        : Moving Average Convergence Divergence")
            print("FUNCTION    : macd")

            if "12" in body:
                print("FAST EMA    : 12")

            if "26" in body:
                print("SLOW EMA    : 26")

            if "9" in body:
                print("SIGNAL      : 9")

            if "ema12" in body:
                print("EMA12       : DETECTED")

            if "ema26" in body:
                print("EMA26       : DETECTED")

            if "signal_series" in body:
                print("SIGNAL EMA  : DETECTED")

            if "histogram" in body:
                print("HISTOGRAM   : DETECTED")

            print("STATUS      : RECONSTRUCTED_FROM_SOURCE")
            return True

    if indicator == "ATR14":
        body, line, _ = find_function(source, "atr")

        if body:
            print("TYPE        : Average True Range")
            print("FUNCTION    : atr")
            print("PERIOD      : 14")

            if "true_ranges" in body:
                print("TR SERIES   : DETECTED")

            if "high - low" in body:
                print("TR COMPONENT : HIGH - LOW")

            if "previous_close" in body:
                print("TR COMPONENT : PREVIOUS CLOSE")

            if "mean(" in body:
                print("INITIAL ATR  : ARITHMETIC MEAN SIGNAL")

            print("STATUS      : RECONSTRUCTED_FROM_SOURCE")
            return True

    if indicator == "ADX14":
        body, line, _ = find_function(source, "adx")

        if body:
            print("TYPE        : Average Directional Index")
            print("FUNCTION    : adx")
            print("PERIOD      : 14")

            for item in [
                "plus_dm",
                "minus_dm",
                "dx_values",
                "plus_di",
                "minus_di",
            ]:
                if item in body:
                    print(f"{item.upper():12s}: DETECTED")

            if "atr_value" in body:
                print("ATR INPUT   : DETECTED")

            print("STATUS      : RECONSTRUCTED_FROM_SOURCE")
            return True

    if indicator in (
        "BB_MIDDLE",
        "BB_UPPER",
        "BB_LOWER",
        "BB_WIDTH",
    ):
        body, line, _ = find_function(source, "bollinger")

        if body:
            print("TYPE        : Bollinger Bands")
            print("FUNCTION    : bollinger")
            print("PERIOD      : 20")

            if "mean(" in body:
                print("MIDDLE      : SMA SIGNAL DETECTED")

            if "stdev(" in body:
                print("DEVIATION   : STANDARD DEVIATION SIGNAL DETECTED")

            if "2" in body:
                print("MULTIPLIER  : 2 SIGNAL DETECTED")

            if "bb_width" in body:
                print("WIDTH       : DETECTED")

            print("STATUS      : RECONSTRUCTED_FROM_SOURCE")
            return True

    if indicator in ("VOLUME_SMA20", "VOLUME_RATIO"):
        body, line, _ = find_function(source, "volume_metrics")

        if body:
            print("TYPE        : Volume Metrics")
            print("FUNCTION    : volume_metrics")
            print("PERIOD      : 20")

            if "volumes[-period:]" in body:
                print("WINDOW      : LAST PERIOD VOLUMES")

            if "current" in body:
                print("CURRENT     : LAST VOLUME")

            if "mean(" in body:
                print("SMA         : ARITHMETIC MEAN SIGNAL")

            print("STATUS      : RECONSTRUCTED_FROM_SOURCE")
            return True

    if indicator == "VOLATILITY":
        body, line, _ = find_function(source, "volatility")

        if body:
            print("TYPE        : Return-Based Volatility")
            print("FUNCTION    : volatility")

            if "returns" in body:
                print("RETURNS     : DETECTED")

            if "stdev(" in body:
                print("STDEV       : DETECTED")

            if "log(" in body:
                print("RETURN TYPE : LOG RETURN SIGNAL")
            else:
                print("RETURN TYPE : NON-LOG RETURN / NOT EXPLICITLY LOG")

            print("STATUS      : RECONSTRUCTED_FROM_SOURCE")
            return True

    if indicator == "TECHNICAL_SCORE":
        body, line, _ = find_function(source, "technical_score")

        if body:
            print("TYPE        : Rule-Based Technical Score")
            print("FUNCTION    : technical_score")

            score_changes = re.findall(
                r"score\s*([+-]=)\s*([0-9]+(?:\.[0-9]+)?)",
                body,
            )

            if score_changes:
                print("SCORE RULES : DETECTED")

                for operator, value in score_changes:
                    print(
                        f"  {operator:3s} {value}"
                    )

            print("STATUS      : RECONSTRUCTED_FROM_SOURCE")
            return True

    print("STATUS      : SOURCE FUNCTION NOT RESOLVED")
    return False


def main():
    section(
        "ARUNDA INDICATOR CONVENTION RECONSTRUCTION v0.1"
    )

    print("MODE            : READ ONLY")
    print("DATABASE WRITE  : NONE")
    print("FORMULA CALC    : NONE")
    print("SOURCE          : market_data_engine.py")
    print("PURPOSE         : IMPLEMENTATION-LEVEL CONVENTION EXTRACTION")

    section("SOURCE INVENTORY")

    print("ENGINE PATH     :", ENGINE_PATH)
    print("ENGINE FOUND    :", ENGINE_PATH.exists())

    if not ENGINE_PATH.exists():
        print()
        print("FATAL ERROR     : market_data_engine.py NOT FOUND")
        sys.exit(1)

    source = ENGINE_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )

    print("SOURCE SIZE     :", len(source), "characters")
    print("SOURCE LINES    :", len(source.splitlines()))

    section("ENGINE VERSION")

    versions = re.findall(
        r'ENGINE_VERSION\s*=\s*["\']([^"\']+)["\']',
        source,
    )

    if versions:
        for version in dict.fromkeys(versions):
            print("ENGINE VERSION  :", version)
    else:
        print("ENGINE VERSION  : NOT DETECTED")

    section("PERIOD SIGNAL SCAN")

    periods = detect_periods(source)

    if periods:
        print("PERIOD SIGNALS  :", ", ".join(map(str, periods)))
    else:
        print("NO EXPLICIT PERIOD CONSTANTS DETECTED")

    print(
        "MACD SIGNAL 9   :",
        "DETECTED" if detect_signal_period(source) else "NOT EXPLICITLY DETECTED",
    )

    section("INDICATOR RECONSTRUCTION")

    reconstructed = 0

    for indicator in EXPECTED_INDICATORS:
        if reconstruct_indicator(indicator, source):
            reconstructed += 1

    section("SOURCE FUNCTION MAP")

    function_map = {
        "EMA20": "ema",
        "EMA50": "ema",
        "RSI14": "rsi",
        "MACD": "macd",
        "MACD_SIGNAL": "macd",
        "MACD_HIST": "macd",
        "ATR14": "atr",
        "ADX14": "adx",
        "BB_MIDDLE": "bollinger",
        "BB_UPPER": "bollinger",
        "BB_LOWER": "bollinger",
        "BB_WIDTH": "bollinger",
        "VOLUME_SMA20": "volume_metrics",
        "VOLUME_RATIO": "volume_metrics",
        "VOLATILITY": "volatility",
        "TECHNICAL_SCORE": "technical_score",
    }

    for indicator, function_name in function_map.items():
        body, line, _ = find_function(
            source,
            function_name,
        )

        if body is not None:
            print(
                f"  [MAPPED] {indicator:16s} -> "
                f"{function_name}() @ line {line}"
            )
        else:
            print(
                f"  [MISSING] {indicator:16s} -> "
                f"{function_name}()"
            )

    section("DETAILED SOURCE SIGNALS")

    for group, keywords in GROUPS.items():
        print()
        print(f"GROUP : {group}")

        matches = []

        source_lines = source.splitlines()

        for index, line in enumerate(source_lines, start=1):
            lower = line.lower()

            for keyword in keywords:
                if keyword.lower() in lower:
                    matches.append(
                        (
                            index,
                            line.strip(),
                        )
                    )
                    break

        print("MATCHES :", len(matches))

        for line_number, text in matches[:20]:
            print(
                f"  LINE {line_number:5d} : {text}"
            )

        if len(matches) > 20:
            print(
                f"  ... {len(matches) - 20} additional matches"
            )

    section("FINAL RECONSTRUCTION SUMMARY")

    print("EXPECTED INDICATORS :", len(EXPECTED_INDICATORS))
    print("RECONSTRUCTED       :", reconstructed)
    print(
        "UNRESOLVED          :",
        len(EXPECTED_INDICATORS) - reconstructed,
    )

    if reconstructed == len(EXPECTED_INDICATORS):
        print("RECONSTRUCTION STATUS : COMPLETE")
    else:
        print("RECONSTRUCTION STATUS : PARTIAL")

    print()
    print("DATABASE WRITE OPERATIONS : NONE")
    print("FORMULA CALCULATIONS      : NONE")
    print("AUDIT COMPLETE")

    separator("=")


if __name__ == "__main__":
    main()