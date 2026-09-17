from pathlib import Path
import re
import sys


# =============================================================================
# ARUNDA INDICATOR STANDARD CONFORMANCE AUDIT v0.1
# =============================================================================
# MODE            : READ ONLY
# DATABASE WRITE  : NONE
# FORMULA CALC    : NONE
# PURPOSE         : Compare implemented indicator conventions against
#                   explicitly defined standard conventions.
# =============================================================================


BASE_DIR = Path(__file__).resolve().parent
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

ENGINE_EXPECTED = "MARKET_DATA_CMC_SNAPSHOT_v0.2"


# =============================================================================
# STANDARD CONVENTION SPECIFICATION
# =============================================================================

STANDARDS = {
    "EMA20": {
        "family": "EMA",
        "period": 20,
        "requirements": [
            "EMA smoothing alpha = 2 / (period + 1)",
            "Initial EMA seed uses arithmetic mean of first period values",
            "Recursive EMA smoothing is used after initialization",
        ],
    },

    "EMA50": {
        "family": "EMA",
        "period": 50,
        "requirements": [
            "EMA smoothing alpha = 2 / (period + 1)",
            "Initial EMA seed uses arithmetic mean of first period values",
            "Recursive EMA smoothing is used after initialization",
        ],
    },

    "RSI14": {
        "family": "RSI",
        "period": 14,
        "requirements": [
            "Price changes are separated into gains and losses",
            "Initial average gain uses arithmetic mean over period",
            "Initial average loss uses arithmetic mean over period",
            "Subsequent averages use Wilder smoothing",
            "RSI uses 100 - 100 / (1 + RS)",
        ],
    },

    "MACD": {
        "family": "MACD",
        "requirements": [
            "Fast EMA period = 12",
            "Slow EMA period = 26",
            "MACD = EMA12 - EMA26",
        ],
    },

    "MACD_SIGNAL": {
        "family": "MACD",
        "requirements": [
            "Signal EMA period = 9",
            "Signal is calculated from MACD series",
        ],
    },

    "MACD_HIST": {
        "family": "MACD",
        "requirements": [
            "Histogram = MACD - Signal",
        ],
    },

    "ATR14": {
        "family": "ATR",
        "period": 14,
        "requirements": [
            "True Range includes high - low",
            "True Range includes abs(high - previous close)",
            "True Range includes abs(low - previous close)",
            "Initial ATR uses arithmetic mean of first period TR values",
            "Subsequent ATR uses Wilder smoothing",
        ],
    },

    "ADX14": {
        "family": "ADX",
        "period": 14,
        "requirements": [
            "Directional movement uses +DM and -DM",
            "True Range is used",
            "ATR is used in DI normalization",
            "+DI is derived from smoothed +DM / ATR",
            "-DI is derived from smoothed -DM / ATR",
            "DX = 100 * abs(+DI - -DI) / (+DI + -DI)",
            "Initial ADX uses arithmetic mean of initial DX values",
            "Subsequent ADX uses Wilder smoothing",
        ],
    },

    "BB_MIDDLE": {
        "family": "BOLLINGER",
        "period": 20,
        "requirements": [
            "Middle band = SMA20",
        ],
    },

    "BB_UPPER": {
        "family": "BOLLINGER",
        "period": 20,
        "requirements": [
            "Upper band = middle band + 2 * standard deviation",
        ],
    },

    "BB_LOWER": {
        "family": "BOLLINGER",
        "period": 20,
        "requirements": [
            "Lower band = middle band - 2 * standard deviation",
        ],
    },

    "BB_WIDTH": {
        "family": "BOLLINGER",
        "period": 20,
        "requirements": [
            "Width = (upper - lower) / middle",
        ],
    },

    "VOLUME_SMA20": {
        "family": "VOLUME",
        "period": 20,
        "requirements": [
            "Volume SMA uses arithmetic mean",
            "Volume SMA window = 20 observations",
        ],
    },

    "VOLUME_RATIO": {
        "family": "VOLUME",
        "period": 20,
        "requirements": [
            "Current volume is divided by Volume SMA20",
        ],
    },

    "VOLATILITY": {
        "family": "VOLATILITY",
        "requirements": [
            "Volatility is based on sequential returns",
            "Standard deviation is applied to the return series",
            "No annualization unless explicitly implemented",
        ],
    },

    "TECHNICAL_SCORE": {
        "family": "SCORE",
        "requirements": [
            "Score is rule based",
            "Score components are explicitly weighted",
            "Positive and negative contributions are explicitly defined",
        ],
    },
}


# =============================================================================
# SOURCE HELPERS
# =============================================================================

def separator(char="=", width=99):
    print(char * width)


def section(title):
    print()
    separator("=")
    print(title)
    separator("=")


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def get_function(source, name):
    pattern = re.compile(
        rf"^def\s+{re.escape(name)}\s*\(",
        re.MULTILINE,
    )

    match = pattern.search(source)

    if not match:
        return None

    start = match.start()

    next_function = re.search(
        r"^def\s+\w+\s*\(",
        source[match.end():],
        re.MULTILINE,
    )

    if next_function:
        end = match.end() + next_function.start()
    else:
        end = len(source)

    return source[start:end]


def get_line_number(source, text):
    index = source.find(text)

    if index < 0:
        return None

    return source.count("\n", 0, index) + 1


def contains_any(text, patterns):
    lower = text.lower()

    for pattern in patterns:
        if pattern.lower() in lower:
            return True

    return False


def find_periods(text):
    values = []

    patterns = [
        r"period\s*=\s*(\d+)",
        r"period\s*:\s*int\s*=\s*(\d+)",
        r"PERIOD\s*=\s*(\d+)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = int(match.group(1))

            if value not in values:
                values.append(value)

    return values


# =============================================================================
# CONFORMANCE CHECKS
# =============================================================================

def check_ema(source, period):
    body = get_function(source, "ema")

    if body is None:
        return {
            "status": "FAIL",
            "reason": "EMA_FUNCTION_NOT_FOUND",
        }

    results = []

    alpha_ok = contains_any(
        body,
        [
            "2.0 / (period + 1)",
            "2 / (period + 1)",
        ],
    )

    seed_ok = contains_any(
        body,
        [
            "mean(values[:period])",
            "mean(values[: period])",
            "mean(values[0:period])",
        ],
    )

    recursive_ok = contains_any(
        body,
        [
            "alpha *",
            "1 - alpha",
            "ema_value",
        ],
    )

    results.append(
        ("EMA_ALPHA", alpha_ok)
    )

    results.append(
        ("EMA_INITIAL_SEED", seed_ok)
    )

    results.append(
        ("EMA_RECURSIVE_SMOOTHING", recursive_ok)
    )

    failed = [
        name for name, ok in results
        if not ok
    ]

    if failed:
        return {
            "status": "PARTIAL",
            "failed": failed,
        }

    return {
        "status": "CONFORMANT",
        "failed": [],
    }


def check_rsi(source):
    body = get_function(source, "rsi")

    if body is None:
        return {
            "status": "FAIL",
            "reason": "RSI_FUNCTION_NOT_FOUND",
        }

    checks = {}

    checks["GAIN_SERIES"] = contains_any(
        body,
        ["gains ="],
    )

    checks["LOSS_SERIES"] = contains_any(
        body,
        ["losses ="],
    )

    checks["INITIAL_GAIN_MEAN"] = (
        "mean(" in body
        and "gains[:period]" in body
    )

    checks["INITIAL_LOSS_MEAN"] = (
        "mean(" in body
        and "losses[:period]" in body
    )

    checks["WILDER_SMOOTHING"] = (
        contains_any(
            body,
            [
                "(period - 1)",
                "period - 1",
            ],
        )
        and "/ period" in body
    )

    checks["RSI_STANDARD_FORM"] = (
        "100" in body
        and (
            "1 + rs" in body.lower()
            or "1+rs" in body.lower()
        )
    )

    failed = [
        name for name, ok in checks.items()
        if not ok
    ]

    if not failed:
        status = "CONFORMANT"
    else:
        status = "PARTIAL"

    return {
        "status": status,
        "failed": failed,
    }


def check_macd(source):
    body = get_function(source, "macd")

    if body is None:
        return {
            "status": "FAIL",
            "reason": "MACD_FUNCTION_NOT_FOUND",
        }

    checks = {}

    checks["EMA12"] = (
        "ema_series" in body
        and "12" in body
    )

    checks["EMA26"] = (
        "ema_series" in body
        and "26" in body
    )

    checks["MACD_DIFFERENCE"] = (
        "ema12" in body
        and "ema26" in body
        and "-" in body
    )

    checks["SIGNAL_EMA9"] = (
        "signal_series" in body
        and "9" in body
    )

    checks["HISTOGRAM"] = (
        "histogram" in body
        and "signal" in body.lower()
    )

    failed = [
        name for name, ok in checks.items()
        if not ok
    ]

    if not failed:
        status = "CONFORMANT"
    else:
        status = "PARTIAL"

    return {
        "status": status,
        "failed": failed,
    }


def check_atr(source):
    body = get_function(source, "atr")

    if body is None:
        return {
            "status": "FAIL",
            "reason": "ATR_FUNCTION_NOT_FOUND",
        }

    checks = {}

    checks["HIGH_LOW"] = (
        "high - low" in body
    )

    checks["HIGH_PREVIOUS_CLOSE"] = (
        "previous_close" in body
        and "high" in body
    )

    checks["LOW_PREVIOUS_CLOSE"] = (
        "previous_close" in body
        and "low" in body
    )

    checks["INITIAL_MEAN"] = (
        "mean(" in body
        and "true_ranges" in body
    )

    checks["WILDER_SMOOTHING"] = (
        "(period - 1)" in body
        or "period - 1" in body
    )

    failed = [
        name for name, ok in checks.items()
        if not ok
    ]

    return {
        "status": (
            "CONFORMANT"
            if not failed
            else "PARTIAL"
        ),
        "failed": failed,
    }


def check_adx(source):
    body = get_function(source, "adx")

    if body is None:
        return {
            "status": "FAIL",
            "reason": "ADX_FUNCTION_NOT_FOUND",
        }

    checks = {}

    checks["PLUS_DM"] = "plus_dm" in body
    checks["MINUS_DM"] = "minus_dm" in body
    checks["TR"] = "true_ranges" in body or "atr_value" in body
    checks["PLUS_DI"] = "plus_di" in body
    checks["MINUS_DI"] = "minus_di" in body
    checks["DX"] = "dx_values" in body
    checks["INITIAL_ADX_MEAN"] = (
        "mean(" in body
        and "dx_values" in body
    )
    checks["WILDER_SMOOTHING"] = (
        "(period - 1)" in body
        or "period - 1" in body
    )

    failed = [
        name for name, ok in checks.items()
        if not ok
    ]

    return {
        "status": (
            "CONFORMANT"
            if not failed
            else "PARTIAL"
        ),
        "failed": failed,
    }


def check_bollinger(source):
    body = get_function(source, "bollinger")

    if body is None:
        return {
            "status": "FAIL",
            "reason": "BOLLINGER_FUNCTION_NOT_FOUND",
        }

    checks = {}

    checks["SMA"] = "mean(" in body
    checks["STDEV"] = "stdev(" in body
    checks["MULTIPLIER_2"] = "2" in body
    checks["UPPER"] = (
        "bb_upper" in body
        or "upper" in body
    )
    checks["LOWER"] = (
        "bb_lower" in body
        or "lower" in body
    )
    checks["WIDTH"] = (
        "bb_width" in body
        or "width" in body
    )

    failed = [
        name for name, ok in checks.items()
        if not ok
    ]

    return {
        "status": (
            "CONFORMANT"
            if not failed
            else "PARTIAL"
        ),
        "failed": failed,
    }


def check_volume(source):
    body = get_function(source, "volume_metrics")

    if body is None:
        return {
            "status": "FAIL",
            "reason": "VOLUME_FUNCTION_NOT_FOUND",
        }

    checks = {}

    checks["PERIOD_WINDOW"] = (
        "volumes[-period:]" in body
    )

    checks["CURRENT_VOLUME"] = (
        "current" in body
    )

    checks["ARITHMETIC_MEAN"] = (
        "mean(" in body
    )

    checks["RATIO"] = (
        "/" in body
    )

    failed = [
        name for name, ok in checks.items()
        if not ok
    ]

    return {
        "status": (
            "CONFORMANT"
            if not failed
            else "PARTIAL"
        ),
        "failed": failed,
    }


def check_volatility(source):
    body = get_function(source, "volatility")

    if body is None:
        return {
            "status": "FAIL",
            "reason": "VOLATILITY_FUNCTION_NOT_FOUND",
        }

    checks = {}

    checks["RETURNS"] = "returns" in body
    checks["STDEV"] = "stdev(" in body

    annualization = contains_any(
        body,
        [
            "sqrt(252)",
            "sqrt(365)",
            "* 252",
            "* 365",
        ],
    )

    checks["NO_ANNUALIZATION"] = not annualization

    failed = [
        name for name, ok in checks.items()
        if not ok
    ]

    return {
        "status": (
            "CONFORMANT"
            if not failed
            else "PARTIAL"
        ),
        "failed": failed,
    }


def check_score(source):
    body = get_function(source, "technical_score")

    if body is None:
        return {
            "status": "FAIL",
            "reason": "TECHNICAL_SCORE_FUNCTION_NOT_FOUND",
        }

    checks = {}

    checks["SCORE_VARIABLE"] = (
        "score = 0.0" in body
        or "score = 0" in body
    )

    checks["POSITIVE_RULES"] = (
        re.search(
            r"score\s*\+=\s*[0-9]",
            body,
        )
        is not None
    )

    checks["NEGATIVE_RULES"] = (
        re.search(
            r"score\s*-=\s*[0-9]",
            body,
        )
        is not None
    )

    failed = [
        name for name, ok in checks.items()
        if not ok
    ]

    return {
        "status": (
            "CONFORMANT"
            if not failed
            else "PARTIAL"
        ),
        "failed": failed,
    }


# =============================================================================
# MAIN INDICATOR DISPATCH
# =============================================================================

def check_indicator(indicator, source):
    if indicator in ("EMA20", "EMA50"):
        period = 20 if indicator == "EMA20" else 50
        return check_ema(source, period)

    if indicator == "RSI14":
        return check_rsi(source)

    if indicator in (
        "MACD",
        "MACD_SIGNAL",
        "MACD_HIST",
    ):
        return check_macd(source)

    if indicator == "ATR14":
        return check_atr(source)

    if indicator == "ADX14":
        return check_adx(source)

    if indicator in (
        "BB_MIDDLE",
        "BB_UPPER",
        "BB_LOWER",
        "BB_WIDTH",
    ):
        return check_bollinger(source)

    if indicator in (
        "VOLUME_SMA20",
        "VOLUME_RATIO",
    ):
        return check_volume(source)

    if indicator == "VOLATILITY":
        return check_volatility(source)

    if indicator == "TECHNICAL_SCORE":
        return check_score(source)

    return {
        "status": "FAIL",
        "reason": "NO_CHECKER_DEFINED",
    }


# =============================================================================
# DETAILED OUTPUT
# =============================================================================

def print_standard(indicator):
    spec = STANDARDS[indicator]

    print("STANDARD FAMILY :", spec["family"])

    if "period" in spec:
        print("STANDARD PERIOD :", spec["period"])

    print("STANDARD REQUIREMENTS:")

    for requirement in spec["requirements"]:
        print("  -", requirement)


def print_result(result):
    status = result.get("status", "UNKNOWN")

    print("CONFORMANCE STATUS :", status)

    if "reason" in result:
        print("REASON             :", result["reason"])

    failed = result.get("failed", [])

    if failed:
        print("FAILED CHECKS:")

        for item in failed:
            print("  [FAIL] :", item)

    if status == "CONFORMANT":
        print("CONFORMANCE RESULT : STANDARD CONFORMANT")

    elif status == "PARTIAL":
        print("CONFORMANCE RESULT : REVIEW REQUIRED")

    elif status == "FAIL":
        print("CONFORMANCE RESULT : SOURCE IMPLEMENTATION NOT RESOLVED")


# =============================================================================
# MAIN
# =============================================================================

def main():

    section(
        "ARUNDA INDICATOR STANDARD CONFORMANCE AUDIT v0.1"
    )

    print("MODE            : READ ONLY")
    print("DATABASE WRITE  : NONE")
    print("FORMULA CALC    : NONE")
    print("SOURCE          : market_data_engine.py")
    print("PURPOSE         : STANDARD CONFORMANCE VERIFICATION")

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

            if version == ENGINE_EXPECTED:
                print("VERSION STATUS  : EXPECTED")
            else:
                print("VERSION STATUS  : DIFFERENT_FROM_EXPECTED")
    else:
        print("ENGINE VERSION  : NOT DETECTED")

    section("STANDARD CONVENTION MATRIX")

    print(
        "STANDARD BASELINE : "
        "EMA / Wilder RSI / MACD 12-26-9 / "
        "Wilder ATR / Wilder ADX / "
        "Bollinger 20,2 / Volume SMA20 / "
        "non-annualized return volatility"
    )

    section("INDICATOR CONFORMANCE")

    counts = {
        "CONFORMANT": 0,
        "PARTIAL": 0,
        "FAIL": 0,
    }

    results = {}

    for indicator in STANDARDS:

        print()
        separator("-")
        print("INDICATOR :", indicator)
        separator("-")

        print_standard(indicator)

        print()

        result = check_indicator(
            indicator,
            source,
        )

        results[indicator] = result

        print_result(result)

        status = result.get("status", "FAIL")

        if status not in counts:
            counts[status] = 0

        counts[status] += 1

    section("CONFORMANCE SUMMARY")

    print(
        "EXPECTED INDICATORS :",
        len(STANDARDS),
    )

    print(
        "CONFORMANT          :",
        counts["CONFORMANT"],
    )

    print(
        "PARTIAL             :",
        counts["PARTIAL"],
    )

    print(
        "FAIL                :",
        counts["FAIL"],
    )

    print()

    print("INDICATOR STATUS MATRIX")

    for indicator, result in results.items():
        status = result.get("status", "UNKNOWN")

        print(
            f"  [{status:10s}] : {indicator}"
        )

    section("FINAL AUDIT STATUS")

    if counts["FAIL"] > 0:
        print(
            "AUDIT STATUS        : BLOCKED"
        )
        print(
            "REASON              : SOURCE IMPLEMENTATION GAP"
        )

    elif counts["PARTIAL"] > 0:
        print(
            "AUDIT STATUS        : REVIEW_REQUIRED"
        )
        print(
            "REASON              : CONVENTION DIFFERENCES OR "
            "INSUFFICIENT SOURCE SIGNALS"
        )

    else:
        print(
            "AUDIT STATUS        : CONFORMANT"
        )
        print(
            "ALL INDICATORS      : STANDARD CONFORMANT"
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

    separator("=")


if __name__ == "__main__":
    main()