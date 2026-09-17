from pathlib import Path
import re


# =============================================================================
# ARUNDA INDICATOR STANDARD CONVENTION RESOLUTION AUDIT v0.1
# =============================================================================
# MODE            : READ ONLY
# DATABASE WRITE  : NONE
# FORMULA CALC    : NONE
# PURPOSE         : Resolve exact implementation conventions for EMA20/EMA50/RSI14
# =============================================================================


BASE_DIR = Path(__file__).resolve().parent
ENGINE_PATH = BASE_DIR / "market_data_engine.py"


TARGETS = {
    "EMA20": {
        "functions": ["ema", "ema_series"],
        "period": 20,
        "family": "EMA",
    },
    "EMA50": {
        "functions": ["ema", "ema_series"],
        "period": 50,
        "family": "EMA",
    },
    "RSI14": {
        "functions": ["rsi"],
        "period": 14,
        "family": "RSI",
    },
}


def print_header(title, char="="):
    print(char * 99)
    print(title)
    print(char * 99)


def load_source():
    if not ENGINE_PATH.exists():
        return None

    try:
        return ENGINE_PATH.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ENGINE_PATH.read_text(encoding="utf-8-sig")


def source_lines(text):
    return text.splitlines()


def find_function(lines, function_name):
    """
    Locate a Python function definition and return its start/end lines.
    Handles normal def and async def.
    """
    pattern = re.compile(
        rf"^\s*(?:async\s+)?def\s+{re.escape(function_name)}\s*\("
    )

    start = None

    for i, line in enumerate(lines):
        if pattern.search(line):
            start = i
            break

    if start is None:
        return None, None

    base_indent = len(lines[start]) - len(lines[start].lstrip())

    end = len(lines)

    for j in range(start + 1, len(lines)):
        line = lines[j]

        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip())

        if indent <= base_indent and re.match(
            r"^\s*(?:async\s+)?def\s+\w+\s*\(", line
        ):
            end = j
            break

        if indent <= base_indent and re.match(
            r"^\s*class\s+\w+", line
        ):
            end = j
            break

    return start, end


def extract_function(lines, function_name):
    start, end = find_function(lines, function_name)

    if start is None:
        return None

    return {
        "name": function_name,
        "start": start + 1,
        "end": end,
        "lines": lines[start:end],
    }


def print_function_block(block, max_lines=120):
    if block is None:
        return

    print(
        f"\nFUNCTION : {block['name']}"
    )
    print(
        f"LINES    : {block['start']} - {block['end']}"
    )
    print("-" * 99)

    function_lines = block["lines"]

    if len(function_lines) > max_lines:
        display_lines = function_lines[:max_lines]
        truncated = True
    else:
        display_lines = function_lines
        truncated = False

    for offset, line in enumerate(display_lines):
        line_no = block["start"] + offset
        print(f"{line_no:5d} : {line}")

    if truncated:
        print(
            f"... FUNCTION OUTPUT TRUNCATED AFTER {max_lines} LINES ..."
        )


def scan_signals(block):
    """
    Detect semantic signals without calculating anything.
    """

    if block is None:
        return {
            "found": False,
            "signals": [],
        }

    text = "\n".join(block["lines"])

    signals = []

    checks = [
        (
            "PERIOD_PARAMETER",
            r"\bperiod\s*=",
        ),
        (
            "PERIOD_USAGE",
            r"\bperiod\b",
        ),
        (
            "ALPHA_FORMULA",
            r"2\s*/\s*\(\s*period\s*\+\s*1\s*\)",
        ),
        (
            "EMA_MULTIPLIER",
            r"\(\s*2\s*/\s*\(\s*period\s*\+\s*1\s*\)\s*\)",
        ),
        (
            "SEED_MEAN",
            r"\bmean\s*\(",
        ),
        (
            "SEED_SUM_DIVISION",
            r"\bsum\s*\([^)]*\)\s*/\s*period",
        ),
        (
            "RECURSIVE_PREVIOUS_EMA",
            r"\bema\b[^=\n]*\*",
        ),
        (
            "PREVIOUS_VALUE",
            r"\[-1\]",
        ),
        (
            "GAIN",
            r"\bgains?\b",
        ),
        (
            "LOSS",
            r"\bloss(?:es)?\b",
        ),
        (
            "AVG_GAIN",
            r"\bavg_gain\b",
        ),
        (
            "AVG_LOSS",
            r"\bavg_loss\b",
        ),
        (
            "WILDER",
            r"\b[wW]ilder\b",
        ),
        (
            "SMOOTH",
            r"\bsmooth",
        ),
        (
            "RS_FORMULA",
            r"\brs\b",
        ),
        (
            "RSI_STANDARD_FORM",
            r"100\s*-\s*100\s*/",
        ),
        (
            "ONE_PLUS_RS",
            r"1\s*\+\s*rs",
        ),
        (
            "DELTA",
            r"\bdelta\b",
        ),
    ]

    for name, pattern in checks:
        if re.search(pattern, text, re.IGNORECASE):
            signals.append(name)

    return {
        "found": True,
        "signals": signals,
    }


def find_matching_lines(block, patterns):
    if block is None:
        return []

    matches = []

    compiled = [
        (label, re.compile(pattern, re.IGNORECASE))
        for label, pattern in patterns
    ]

    for offset, line in enumerate(block["lines"]):
        line_no = block["start"] + offset

        for label, pattern in compiled:
            if pattern.search(line):
                matches.append(
                    {
                        "label": label,
                        "line_no": line_no,
                        "text": line,
                    }
                )

    return matches


def resolve_ema(lines, function_name):
    block = extract_function(lines, function_name)

    result = {
        "function": function_name,
        "found": block is not None,
        "alpha": "UNRESOLVED",
        "seed": "UNRESOLVED",
        "recursive": "UNRESOLVED",
        "signals": [],
        "matches": [],
    }

    if block is None:
        return result

    result["signals"] = scan_signals(block)["signals"]

    patterns = [
        (
            "ALPHA",
            r"2\s*/\s*\(\s*period\s*\+\s*1\s*\)",
        ),
        (
            "MEAN_SEED",
            r"\bmean\s*\(",
        ),
        (
            "SUM_DIV_PERIOD",
            r"\bsum\s*\([^)]*\)\s*/\s*period",
        ),
        (
            "RECURSIVE_ASSIGNMENT",
            r"ema_value|ema_val|previous|prev",
        ),
        (
            "MULTIPLICATIVE_UPDATE",
            r"\*.*period|period.*\*",
        ),
    ]

    result["matches"] = find_matching_lines(
        block,
        patterns,
    )

    alpha_found = any(
        m["label"] == "ALPHA"
        for m in result["matches"]
    )

    mean_found = any(
        m["label"] == "MEAN_SEED"
        for m in result["matches"]
    )

    sum_found = any(
        m["label"] == "SUM_DIV_PERIOD"
        for m in result["matches"]
    )

    recursive_found = any(
        m["label"] == "RECURSIVE_ASSIGNMENT"
        for m in result["matches"]
    )

    result["alpha"] = (
        "STANDARD_ALPHA_2_OVER_PERIOD_PLUS_1"
        if alpha_found
        else "NOT_EXPLICITLY_RESOLVED"
    )

    if mean_found or sum_found:
        result["seed"] = "ARITHMETIC_MEAN_SIGNAL_FOUND"
    else:
        result["seed"] = "NOT_EXPLICITLY_RESOLVED"

    if recursive_found:
        result["recursive"] = "RECURSIVE_SIGNAL_FOUND"
    else:
        result["recursive"] = "NOT_EXPLICITLY_RESOLVED"

    return result


def resolve_rsi(lines):
    block = extract_function(lines, "rsi")

    result = {
        "found": block is not None,
        "initial_gain": "UNRESOLVED",
        "initial_loss": "UNRESOLVED",
        "smoothing": "UNRESOLVED",
        "rs_formula": "UNRESOLVED",
        "rsi_formula": "UNRESOLVED",
        "signals": [],
        "matches": [],
    }

    if block is None:
        return result

    result["signals"] = scan_signals(block)["signals"]

    patterns = [
        (
            "GAIN_COLLECTION",
            r"\bgains?\b",
        ),
        (
            "LOSS_COLLECTION",
            r"\bloss(?:es)?\b",
        ),
        (
            "AVG_GAIN",
            r"\bavg_gain\b",
        ),
        (
            "AVG_LOSS",
            r"\bavg_loss\b",
        ),
        (
            "MEAN",
            r"\bmean\s*\(",
        ),
        (
            "RS",
            r"\brs\b",
        ),
        (
            "RSI_FORM",
            r"100\s*-\s*100\s*/",
        ),
        (
            "ONE_PLUS_RS",
            r"1\s*\+\s*rs",
        ),
        (
            "WILDER_SMOOTHING",
            r"avg_gain.*period|avg_loss.*period",
        ),
        (
            "RECURSIVE",
            r"\[-1\]",
        ),
    ]

    result["matches"] = find_matching_lines(
        block,
        patterns,
    )

    labels = {
        m["label"]
        for m in result["matches"]
    }

    if "MEAN" in labels and "AVG_GAIN" in labels:
        result["initial_gain"] = "ARITHMETIC_MEAN_SIGNAL_FOUND"
    else:
        result["initial_gain"] = "NOT_EXPLICITLY_RESOLVED"

    if "MEAN" in labels and "AVG_LOSS" in labels:
        result["initial_loss"] = "ARITHMETIC_MEAN_SIGNAL_FOUND"
    else:
        result["initial_loss"] = "NOT_EXPLICITLY_RESOLVED"

    if "WILDER_SMOOTHING" in labels or "RECURSIVE" in labels:
        result["smoothing"] = "SMOOTHING_SIGNAL_FOUND"
    else:
        result["smoothing"] = "NOT_EXPLICITLY_RESOLVED"

    if "RS" in labels:
        result["rs_formula"] = "RS_SIGNAL_FOUND"
    else:
        result["rs_formula"] = "NOT_EXPLICITLY_RESOLVED"

    if "RSI_FORM" in labels and "ONE_PLUS_RS" in labels:
        result["rsi_formula"] = (
            "STANDARD_RSI_FORM_SIGNAL_FOUND"
        )
    else:
        result["rsi_formula"] = "NOT_EXPLICITLY_RESOLVED"

    return result


def print_matches(matches):
    if not matches:
        print("  NO DIRECT SIGNAL MATCHES")
        return

    for match in matches:
        print(
            f"  [SIGNAL] {match['label']:28s}"
            f" LINE {match['line_no']:4d} : {match['text']}"
        )


def audit_ema(lines, indicator, period):
    print("-" * 99)
    print(f"INDICATOR : {indicator}")
    print("-" * 99)
    print("STANDARD FAMILY : EMA")
    print("STANDARD PERIOD : ", period)
    print()
    print("STANDARD CONVENTION:")
    print("  - alpha = 2 / (period + 1)")
    print("  - initial seed = arithmetic mean of first period values")
    print("  - recursive EMA smoothing after initialization")
    print()

    print("IMPLEMENTATION FUNCTION SCAN")
    print("-" * 99)

    ema_function = resolve_ema(lines, "ema")
    ema_series_function = resolve_ema(lines, "ema_series")

    print(
        f"ema() FOUND        : {ema_function['found']}"
    )
    print(
        f"ema_series() FOUND : {ema_series_function['found']}"
    )

    print()
    print("EMA FUNCTION SIGNALS")
    print("-" * 99)
    print("ema()")
    print(
        "  ALPHA     :",
        ema_function["alpha"]
    )
    print(
        "  SEED      :",
        ema_function["seed"]
    )
    print(
        "  RECURSIVE :",
        ema_function["recursive"]
    )

    print()
    print("ema() MATCHES")
    print("-" * 99)
    print_matches(ema_function["matches"])

    print()
    print("EMA SERIES SIGNALS")
    print("-" * 99)
    print("ema_series()")
    print(
        "  ALPHA     :",
        ema_series_function["alpha"]
    )
    print(
        "  SEED      :",
        ema_series_function["seed"]
    )
    print(
        "  RECURSIVE :",
        ema_series_function["recursive"]
    )

    print()
    print("ema_series() MATCHES")
    print("-" * 99)
    print_matches(ema_series_function["matches"])

    resolved_components = []

    for result in [ema_function, ema_series_function]:
        if result["alpha"] != "UNRESOLVED":
            resolved_components.append("ALPHA")

        if result["seed"] != "UNRESOLVED":
            resolved_components.append("SEED")

        if result["recursive"] != "UNRESOLVED":
            resolved_components.append("RECURSIVE")

    resolved_components = sorted(
        set(resolved_components)
    )

    print()
    print("RESOLUTION STATUS")
    print("-" * 99)
    print(
        "RESOLVED COMPONENTS :",
        ", ".join(resolved_components)
        if resolved_components
        else "NONE"
    )

    if len(resolved_components) == 3:
        print("STATUS              : RESOLVED")
    else:
        print("STATUS              : PARTIALLY_RESOLVED")


def audit_rsi(lines):
    print("-" * 99)
    print("INDICATOR : RSI14")
    print("-" * 99)
    print("STANDARD FAMILY : RSI")
    print("STANDARD PERIOD : 14")
    print()
    print("STANDARD CONVENTION:")
    print("  - gains and losses are separated")
    print("  - initial average gain = arithmetic mean")
    print("  - initial average loss = arithmetic mean")
    print("  - subsequent averages use Wilder smoothing")
    print("  - RS = average gain / average loss")
    print("  - RSI = 100 - 100 / (1 + RS)")
    print()

    result = resolve_rsi(lines)

    print("RSI FUNCTION")
    print("-" * 99)
    print(
        "rsi() FOUND :",
        result["found"]
    )

    print()
    print("RESOLVED CONVENTION SIGNALS")
    print("-" * 99)
    print(
        "INITIAL GAIN :",
        result["initial_gain"]
    )
    print(
        "INITIAL LOSS :",
        result["initial_loss"]
    )
    print(
        "SMOOTHING    :",
        result["smoothing"]
    )
    print(
        "RS FORMULA   :",
        result["rs_formula"]
    )
    print(
        "RSI FORMULA  :",
        result["rsi_formula"]
    )

    print()
    print("RSI SOURCE SIGNALS")
    print("-" * 99)
    print_matches(result["matches"])

    resolved = 0

    fields = [
        result["initial_gain"],
        result["initial_loss"],
        result["smoothing"],
        result["rs_formula"],
        result["rsi_formula"],
    ]

    for value in fields:
        if "UNRESOLVED" not in value:
            resolved += 1

    print()
    print("RESOLUTION STATUS")
    print("-" * 99)

    if resolved == 5:
        print("STATUS : RESOLVED")
    elif resolved > 0:
        print(
            f"STATUS : PARTIALLY_RESOLVED ({resolved}/5)"
        )
    else:
        print("STATUS : UNRESOLVED")


def main():
    print_header(
        "ARUNDA INDICATOR STANDARD CONVENTION RESOLUTION AUDIT v0.1"
    )

    print("MODE            : READ ONLY")
    print("DATABASE WRITE   : NONE")
    print("FORMULA CALC     : NONE")
    print(
        "PURPOSE         : Resolve implementation conventions for EMA20/EMA50/RSI14"
    )
    print("=" * 99)

    print("SOURCE INVENTORY")
    print("-" * 99)
    print("ENGINE PATH     :", ENGINE_PATH)
    print("ENGINE FOUND    :", ENGINE_PATH.exists())

    if not ENGINE_PATH.exists():
        print()
        print("FINAL AUDIT STATUS")
        print("-" * 99)
        print("AUDIT STATUS    : BLOCKED")
        print("REASON          : ENGINE_SOURCE_NOT_FOUND")
        return

    text = load_source()

    if text is None:
        print()
        print("FINAL AUDIT STATUS")
        print("-" * 99)
        print("AUDIT STATUS    : BLOCKED")
        print("REASON          : SOURCE_READ_FAILED")
        return

    lines = source_lines(text)

    print("SOURCE SIZE     :", len(text), "characters")
    print("SOURCE LINES    :", len(lines))

    print("=" * 99)

    print("TARGET RESOLUTION SCOPE")
    print("-" * 99)
    print("  [TARGET] EMA20")
    print("  [TARGET] EMA50")
    print("  [TARGET] RSI14")
    print()
    print("NOTE            :")
    print(
        "This audit inspects implementation signals only."
    )
    print(
        "No indicator values are reconstructed."
    )
    print(
        "No database rows are modified."
    )

    print("=" * 99)

    audit_ema(
        lines,
        "EMA20",
        20,
    )

    print()

    audit_ema(
        lines,
        "EMA50",
        50,
    )

    print()

    audit_rsi(lines)

    print()
    print("=" * 99)
    print("FUNCTION SOURCE EXCERPTS")
    print("=" * 99)

    for function_name in [
        "ema",
        "ema_series",
        "rsi",
    ]:
        block = extract_function(
            lines,
            function_name,
        )

        print_function_block(
            block,
            max_lines=120,
        )

    print()
    print("=" * 99)
    print("FINAL AUDIT SUMMARY")
    print("=" * 99)

    ema = resolve_ema(lines, "ema")
    ema_series = resolve_ema(lines, "ema_series")
    rsi_result = resolve_rsi(lines)

    ema_components = set()

    for result in [ema, ema_series]:
        if result["alpha"] != "UNRESOLVED":
            ema_components.add("ALPHA")

        if result["seed"] != "UNRESOLVED":
            ema_components.add("SEED")

        if result["recursive"] != "UNRESOLVED":
            ema_components.add("RECURSIVE")

    rsi_components = [
        rsi_result["initial_gain"],
        rsi_result["initial_loss"],
        rsi_result["smoothing"],
        rsi_result["rs_formula"],
        rsi_result["rsi_formula"],
    ]

    rsi_resolved = sum(
        "UNRESOLVED" not in value
        for value in rsi_components
    )

    print(
        "EMA COMPONENTS RESOLVED :",
        len(ema_components),
        "/ 3",
    )

    print(
        "RSI COMPONENTS RESOLVED :",
        rsi_resolved,
        "/ 5",
    )

    total_resolved = len(ema_components) + rsi_resolved
    total_expected = 8

    print(
        "TOTAL COMPONENTS        :",
        total_resolved,
        "/",
        total_expected,
    )

    if total_resolved == total_expected:
        status = "RESOLVED"
        reason = "ALL TARGET CONVENTION SIGNALS RESOLVED"
    elif total_resolved > 0:
        status = "PARTIALLY_RESOLVED"
        reason = "SOME CONVENTION SIGNALS REQUIRE DIRECT SOURCE REVIEW"
    else:
        status = "UNRESOLVED"
        reason = "INSUFFICIENT SOURCE SIGNALS"

    print()
    print("AUDIT STATUS            :", status)
    print("REASON                  :", reason)
    print()
    print("DATABASE WRITE OPERATIONS : NONE")
    print("FORMULA CALCULATIONS      : NONE")
    print("AUDIT COMPLETE")
    print("=" * 99)


if __name__ == "__main__":
    main()