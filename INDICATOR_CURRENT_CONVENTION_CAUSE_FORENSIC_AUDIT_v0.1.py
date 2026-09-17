from pathlib import Path
import ast
import re
import sqlite3
import math
from datetime import datetime, timezone


# =============================================================================
# ARUNDA INDICATOR CURRENT CONVENTION CAUSE FORENSIC AUDIT v0.1
# =============================================================================
# MODE              : READ ONLY
# DATABASE WRITE    : NONE
# FORMULA WRITE     : NONE
# PURPOSE           : IDENTIFY EXACT CURRENT IMPLEMENTATION CAUSE
#
# IMPORTANT:
# - NO database writes
# - NO engine modifications
# - NO production recalculation
# - NO replacement of current values
# - This audit stops after identifying evidence
# =============================================================================


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

TARGET_SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]

EMA_PERIODS = [20, 50]
RSI_PERIOD = 14

LOOKBACK = 120
MIN_HISTORY = 60

ABS_TOLERANCE = 1e-10
REL_TOLERANCE = 1e-10


# =============================================================================
# OUTPUT
# =============================================================================

def line():
    print("=" * 100)


def section(title):
    print()
    line()
    print(title)
    line()


def subsection(title):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def fmt(value):
    if value is None:
        return "None"
    if isinstance(value, float):
        return repr(value)
    return str(value)


# =============================================================================
# SOURCE FORENSICS
# =============================================================================

def read_engine_source():
    if not ENGINE_PATH.exists():
        return None

    try:
        return ENGINE_PATH.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def normalize_source(source):
    if source is None:
        return ""

    return source.replace("\r\n", "\n").replace("\r", "\n")


def source_lines(source):
    return normalize_source(source).splitlines()


def compact(text):
    return re.sub(r"\s+", " ", text).strip()


def contains_any(source, patterns):
    return any(re.search(pattern, source, re.IGNORECASE | re.DOTALL)
               for pattern in patterns)


# =============================================================================
# AST FORENSICS
# =============================================================================

def parse_ast(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def function_inventory(tree):
    result = {}

    if tree is None:
        return result

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node

    return result


def function_source(source, node):
    if node is None:
        return ""

    lines = source_lines(source)

    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)

    if start is None:
        return ""

    if end is None:
        end = start

    return "\n".join(lines[start - 1:end])


def ast_names(node):
    names = []

    if node is None:
        return names

    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.append(child.id)

    return names


def ast_calls(node):
    calls = []

    if node is None:
        return calls

    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)

            elif isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)

    return calls


def ast_constants(node):
    values = []

    if node is None:
        return values

    for child in ast.walk(node):
        if isinstance(child, ast.Constant):
            values.append(child.value)

    return values


# =============================================================================
# EMA CAUSE FORENSICS
# =============================================================================

def inspect_ema_function(source, functions):
    candidates = []

    for name, node in functions.items():
        lname = name.lower()

        if "ema" in lname:
            candidates.append((name, function_source(source, node)))

    if not candidates:
        return {
            "function_found": False,
            "functions": [],
            "alpha": False,
            "seed": False,
            "recursive": False,
            "signals": [],
        }

    alpha_patterns = [
        r"2\s*/\s*\(\s*(?:period|length|window)\s*\+\s*1\s*\)",
        r"2\.0\s*/\s*\(\s*(?:period|length|window)\s*\+\s*1\.0?\s*\)",
        r"alpha\s*=\s*2",
    ]

    seed_patterns = [
        r"mean\s*\(",
        r"sum\s*\(",
        r"initial.*mean",
        r"seed",
        r"first\s+period",
        r"[:\[]\s*period",
    ]

    recursive_patterns = [
        r"\(\s*1\s*-\s*alpha\s*\)",
        r"alpha\s*\*",
        r"previous.*ema",
        r"ema\s*=",
        r"result\s*\[.*\]\s*=",
        r"values?\s*\[.*\]\s*\*",
    ]

    all_text = "\n".join(text for _, text in candidates)

    alpha = contains_any(all_text, alpha_patterns)
    seed = contains_any(all_text, seed_patterns)
    recursive = contains_any(all_text, recursive_patterns)

    return {
        "function_found": True,
        "functions": [name for name, _ in candidates],
        "alpha": alpha,
        "seed": seed,
        "recursive": recursive,
        "signals": candidates,
    }


# =============================================================================
# RSI CAUSE FORENSICS
# =============================================================================

def inspect_rsi_function(source, functions):
    candidates = []

    for name, node in functions.items():
        lname = name.lower()

        if "rsi" in lname:
            candidates.append((name, function_source(source, node)))

    if not candidates:
        return {
            "function_found": False,
            "functions": [],
            "gain_loss": False,
            "initial_avg": False,
            "wilder": False,
            "formula": False,
            "signals": [],
        }

    all_text = "\n".join(text for _, text in candidates)

    gain_patterns = [
        r"gain",
        r"loss",
        r"delta",
        r"change",
        r"np\.maximum",
        r"max\s*\(",
    ]

    initial_patterns = [
        r"mean\s*\(",
        r"sum\s*\(",
        r"initial",
        r"seed",
        r"average",
    ]

    wilder_patterns = [
        r"wilder",
        r"avg.*\+\s*gain",
        r"avg.*loss",
        r"\(.*period.*-.*1.*\)",
        r"/\s*period",
    ]

    formula_patterns = [
        r"100\s*-\s*100",
        r"100\s*-\s*\(\s*100",
        r"1\s*\+\s*rs",
        r"rs\s*=",
        r"relative\s*strength",
    ]

    gain_loss = contains_any(all_text, gain_patterns)
    initial_avg = contains_any(all_text, initial_patterns)
    wilder = contains_any(all_text, wilder_patterns)
    formula = contains_any(all_text, formula_patterns)

    return {
        "function_found": True,
        "functions": [name for name, _ in candidates],
        "gain_loss": gain_loss,
        "initial_avg": initial_avg,
        "wilder": wilder,
        "formula": formula,
        "signals": candidates,
    }


# =============================================================================
# DATABASE
# =============================================================================

def connect_db():
    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def table_columns(conn, table_name):
    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row["name"] for row in rows]


def table_count(conn):
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type='table'
        """
    ).fetchone()

    return int(row[0])


# =============================================================================
# CURRENT TARGET RESOLUTION
# =============================================================================

def resolve_targets(conn):
    required = [
        "id",
        "symbol",
        "source_timestamp",
        "engine_version",
        "close",
        "ema20",
        "ema50",
        "rsi14",
    ]

    columns = table_columns(conn, "market_data")

    missing = [x for x in required if x not in columns]

    if missing:
        return [], missing

    targets = []

    for symbol in TARGET_SYMBOLS:
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
            WHERE symbol=?
              AND ema20 IS NOT NULL
              AND ema50 IS NOT NULL
              AND rsi14 IS NOT NULL
            ORDER BY source_timestamp DESC, id DESC
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()

        if row is not None:
            targets.append(row)

    return targets, missing


# =============================================================================
# HISTORY RESOLUTION
# =============================================================================

def resolve_history(conn, symbol, target_timestamp):
    rows = conn.execute(
        """
        SELECT
            id,
            symbol,
            source_timestamp,
            close,
            ema20,
            ema50,
            rsi14,
            engine_version
        FROM market_data
        WHERE symbol=?
          AND source_timestamp <= ?
          AND close IS NOT NULL
        ORDER BY source_timestamp ASC, id ASC
        LIMIT ?
        """,
        (symbol, target_timestamp, LOOKBACK),
    ).fetchall()

    return rows


# =============================================================================
# STANDARD RECONSTRUCTION
# =============================================================================

def standard_ema(values, period):
    if len(values) < period:
        return None

    alpha = 2.0 / (period + 1.0)

    seed = sum(values[:period]) / period
    ema = seed

    for value in values[period:]:
        ema = alpha * value + (1.0 - alpha) * ema

    return ema


def standard_rsi(values, period=14):
    if len(values) <= period:
        return None

    changes = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]

    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]

    if len(gains) < period:
        return None

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        if avg_gain == 0:
            return 50.0
        return 100.0

    rs = avg_gain / avg_loss

    return 100.0 - (100.0 / (1.0 + rs))


# =============================================================================
# CURRENT VALUE COMPARISON
# =============================================================================

def error_metrics(current, standard):
    if current is None or standard is None:
        return None, None

    absolute = abs(current - standard)

    denominator = abs(standard)

    if denominator == 0:
        relative = 0.0 if absolute == 0 else math.inf
    else:
        relative = absolute / denominator

    return absolute, relative


def status(current, standard):
    if current is None or standard is None:
        return "UNRESOLVED"

    absolute, relative = error_metrics(current, standard)

    if absolute <= ABS_TOLERANCE or relative <= REL_TOLERANCE:
        return "EXACT"

    return "MISMATCH"


# =============================================================================
# SOURCE CONVENTION INTERPRETATION
# =============================================================================

def interpret_ema_source(ema_info):
    evidence = []

    if not ema_info["function_found"]:
        evidence.append("EMA_FUNCTION_NOT_FOUND")
        return evidence

    if ema_info["alpha"]:
        evidence.append("ALPHA_SIGNAL_PRESENT")
    else:
        evidence.append("ALPHA_SIGNAL_NOT_FOUND")

    if ema_info["seed"]:
        evidence.append("SEED_SIGNAL_PRESENT")
    else:
        evidence.append("SEED_SIGNAL_NOT_FOUND")

    if ema_info["recursive"]:
        evidence.append("RECURSIVE_SIGNAL_PRESENT")
    else:
        evidence.append("RECURSIVE_SIGNAL_NOT_FOUND")

    return evidence


def interpret_rsi_source(rsi_info):
    evidence = []

    if not rsi_info["function_found"]:
        evidence.append("RSI_FUNCTION_NOT_FOUND")
        return evidence

    if rsi_info["gain_loss"]:
        evidence.append("GAIN_LOSS_SIGNAL_PRESENT")
    else:
        evidence.append("GAIN_LOSS_SIGNAL_NOT_FOUND")

    if rsi_info["initial_avg"]:
        evidence.append("INITIAL_AVERAGE_SIGNAL_PRESENT")
    else:
        evidence.append("INITIAL_AVERAGE_SIGNAL_NOT_FOUND")

    if rsi_info["wilder"]:
        evidence.append("WILDER_SIGNAL_PRESENT")
    else:
        evidence.append("WILDER_SIGNAL_NOT_FOUND")

    if rsi_info["formula"]:
        evidence.append("RSI_FORMULA_SIGNAL_PRESENT")
    else:
        evidence.append("RSI_FORMULA_SIGNAL_NOT_FOUND")

    return evidence


# =============================================================================
# MAIN
# =============================================================================

def main():
    section(
        "ARUNDA INDICATOR CURRENT CONVENTION CAUSE FORENSIC AUDIT v0.1"
    )

    print("MODE              : READ ONLY")
    print("DATABASE WRITE    : NONE")
    print("FORMULA WRITE     : NONE")
    print("PURPOSE           : IDENTIFY EXACT CURRENT IMPLEMENTATION CAUSE")

    section("STANDARD TARGET")

    print(
        "EMA20 / EMA50 : alpha=2/(period+1), SMA seed, recursive EMA"
    )
    print(
        "RSI14         : Wilder RSI, arithmetic initial averages, Wilder smoothing"
    )

    section("DATABASE INVENTORY")

    print(f"DATABASE PATH     : {DB_PATH}")
    print(f"DATABASE FOUND    : {DB_PATH.exists()}")

    if not DB_PATH.exists():
        print()
        print("AUDIT STATUS      : BLOCKED")
        print("REASON            : DATABASE NOT FOUND")
        return

    conn = connect_db()

    if conn is None:
        print()
        print("AUDIT STATUS      : BLOCKED")
        print("REASON            : DATABASE CONNECTION FAILED")
        return

    try:
        print(f"TABLE COUNT       : {table_count(conn)}")

        market_exists = table_exists(conn, "market_data")
        print(f"MARKET_DATA       : {'FOUND' if market_exists else 'MISSING'}")

        if not market_exists:
            print()
            print("AUDIT STATUS      : BLOCKED")
            print("REASON            : MARKET_DATA TABLE NOT FOUND")
            return

        columns = table_columns(conn, "market_data")
        print(f"COLUMN COUNT      : {len(columns)}")

        section("ENGINE SOURCE FORENSIC INVENTORY")

        print(f"ENGINE PATH       : {ENGINE_PATH}")
        print(f"ENGINE FOUND      : {ENGINE_PATH.exists()}")

        source = read_engine_source()

        if source is None:
            print("SOURCE READ       : FAILED")
            print()
            print("AUDIT STATUS      : BLOCKED")
            print("REASON            : ENGINE SOURCE NOT READABLE")
            return

        normalized = normalize_source(source)

        print(f"SOURCE SIZE       : {len(source)} characters")
        print(f"SOURCE LINES      : {len(source_lines(source))}")

        tree = parse_ast(source)
        functions = function_inventory(tree)

        ema_info = inspect_ema_function(source, functions)
        rsi_info = inspect_rsi_function(source, functions)

        print()
        print("FUNCTION SIGNALS")
        print(
            f"  EMA FUNCTION    : "
            f"{ema_info['function_found']}"
        )
        print(
            f"  EMA FUNCTIONS   : "
            f"{', '.join(ema_info['functions']) if ema_info['functions'] else 'NONE'}"
        )
        print(
            f"  RSI FUNCTION    : "
            f"{rsi_info['function_found']}"
        )
        print(
            f"  RSI FUNCTIONS   : "
            f"{', '.join(rsi_info['functions']) if rsi_info['functions'] else 'NONE'}"
        )

        print()
        print("EMA CONVENTION SIGNALS")
        print(f"  EMA ALPHA       : {ema_info['alpha']}")
        print(f"  EMA SEED        : {ema_info['seed']}")
        print(f"  EMA RECURSIVE   : {ema_info['recursive']}")

        print()
        print("RSI CONVENTION SIGNALS")
        print(f"  GAIN / LOSS     : {rsi_info['gain_loss']}")
        print(f"  INITIAL AVG     : {rsi_info['initial_avg']}")
        print(f"  WILDER SMOOTH   : {rsi_info['wilder']}")
        print(f"  RSI FORMULA     : {rsi_info['formula']}")

        subsection("EMA FUNCTION SOURCE EVIDENCE")

        if ema_info["signals"]:
            for name, text in ema_info["signals"]:
                print()
                print(f"FUNCTION : {name}")
                print("-" * 100)
                print(text)
        else:
            print("NO EMA FUNCTION SOURCE FOUND")

        subsection("RSI FUNCTION SOURCE EVIDENCE")

        if rsi_info["signals"]:
            for name, text in rsi_info["signals"]:
                print()
                print(f"FUNCTION : {name}")
                print("-" * 100)
                print(text)
        else:
            print("NO RSI FUNCTION SOURCE FOUND")

        section("TARGET RESOLUTION")

        targets, missing = resolve_targets(conn)

        if missing:
            print("MISSING DATABASE FIELDS")
            for field in missing:
                print(f"  [MISSING] : {field}")

            print()
            print("AUDIT STATUS      : BLOCKED")
            print("REASON            : REQUIRED DATABASE FIELDS MISSING")
            return

        print(f"TARGETS FOUND      : {len(targets)} / {len(TARGET_SYMBOLS)}")

        if not targets:
            print()
            print("AUDIT STATUS      : BLOCKED")
            print("REASON            : NO NON-NULL TARGET INDICATORS")
            return

        exact_total = 0
        mismatch_total = 0
        unresolved_total = 0

        cause_rows = []

        for row in targets:
            symbol = row["symbol"]

            section(f"SYMBOL : {symbol}")

            print(f"ANALYSIS ID        : {row['id']}")
            print(f"SOURCE TIME        : {row['source_timestamp']}")
            print(f"ENGINE VERSION     : {row['engine_version']}")
            print(f"STORED CLOSE       : {fmt(row['close'])}")

            print()
            print("CURRENT IMPLEMENTATION")
            print("-" * 100)
            print(f"Current EMA20      : {fmt(row['ema20'])}")
            print(f"Current EMA50      : {fmt(row['ema50'])}")
            print(f"Current RSI14      : {fmt(row['rsi14'])}")

            history = resolve_history(
                conn,
                symbol,
                row["source_timestamp"],
            )

            print()
            print("HISTORY FORENSIC")
            print("-" * 100)
            print(f"REQUESTED LOOKBACK : {LOOKBACK}")
            print(f"HISTORY FOUND      : {len(history)}")

            if history:
                print(
                    f"HISTORY FIRST      : "
                    f"{history[0]['source_timestamp']}"
                )
                print(
                    f"HISTORY LAST       : "
                    f"{history[-1]['source_timestamp']}"
                )

            closes = [
                safe_float(item["close"])
                for item in history
            ]

            closes = [
                value
                for value in closes
                if value is not None and math.isfinite(value)
            ]

            print(f"VALID CLOSES       : {len(closes)}")

            if len(closes) < MIN_HISTORY:
                print("HISTORY STATUS     : INSUFFICIENT")

                unresolved_total += 3

                cause_rows.append({
                    "symbol": symbol,
                    "status": "UNRESOLVED",
                    "reason": "INSUFFICIENT_HISTORY",
                })

                continue

            standard_ema20 = standard_ema(closes, 20)
            standard_ema50 = standard_ema(closes, 50)
            standard_rsi14 = standard_rsi(closes, 14)

            print()
            print("STANDARD CONVENTION RECONSTRUCTION")
            print("-" * 100)
            print(f"Standard EMA20     : {fmt(standard_ema20)}")
            print(f"Standard EMA50     : {fmt(standard_ema50)}")
            print(f"Standard RSI14     : {fmt(standard_rsi14)}")

            subsection("CURRENT IMPLEMENTATION vs STANDARD")

            current_values = {
                "EMA20": safe_float(row["ema20"]),
                "EMA50": safe_float(row["ema50"]),
                "RSI14": safe_float(row["rsi14"]),
            }

            standard_values = {
                "EMA20": standard_ema20,
                "EMA50": standard_ema50,
                "RSI14": standard_rsi14,
            }

            symbol_exact = 0
            symbol_mismatch = 0
            symbol_unresolved = 0

            for indicator in ["EMA20", "EMA50", "RSI14"]:
                current = current_values[indicator]
                standard = standard_values[indicator]

                absolute, relative = error_metrics(
                    current,
                    standard,
                )

                result = status(current, standard)

                if result == "EXACT":
                    exact_total += 1
                    symbol_exact += 1

                elif result == "MISMATCH":
                    mismatch_total += 1
                    symbol_mismatch += 1

                else:
                    unresolved_total += 1
                    symbol_unresolved += 1

                print()
                print(f"INDICATOR : {indicator}")
                print(f"CURRENT   : {fmt(current)}")
                print(f"STANDARD  : {fmt(standard)}")
                print(f"ABS ERR   : {fmt(absolute)}")
                print(f"REL ERR   : {fmt(relative)}")
                print(f"STATUS    : {result}")

            print()
            print("SYMBOL SUMMARY")
            print(
                f"  EXACT      : {symbol_exact}"
            )
            print(
                f"  MISMATCH   : {symbol_mismatch}"
            )
            print(
                f"  UNRESOLVED : {symbol_unresolved}"
            )

            if symbol_unresolved:
                symbol_status = "UNRESOLVED"
            elif symbol_mismatch:
                symbol_status = "MISMATCH"
            else:
                symbol_status = "EXACT"

            print(f"SYMBOL STATUS : {symbol_status}")

            subsection("CAUSE FORENSIC INTERPRETATION")

            ema_diff = (
                status(current_values["EMA20"], standard_values["EMA20"])
                == "MISMATCH"
                or
                status(current_values["EMA50"], standard_values["EMA50"])
                == "MISMATCH"
            )

            rsi_diff = (
                status(current_values["RSI14"], standard_values["RSI14"])
                == "MISMATCH"
            )

            print("EMA EVIDENCE")
            print("-" * 100)

            for evidence in interpret_ema_source(ema_info):
                print(f"  [{evidence}]")

            print()
            print("RSI EVIDENCE")
            print("-" * 100)

            for evidence in interpret_rsi_source(rsi_info):
                print(f"  [{evidence}]")

            print()
            print("DIFFERENCE STATUS")
            print("-" * 100)

            if ema_diff:
                print(
                    "  [CONFIRMED] EMA20/EMA50 differ from reconstructed standard"
                )
            else:
                print(
                    "  [NO CONFIRMED EMA DIFFERENCE]"
                )

            if rsi_diff:
                print(
                    "  [CONFIRMED] RSI14 differs from reconstructed standard"
                )
            else:
                print(
                    "  [NO CONFIRMED RSI DIFFERENCE]"
                )

            print()
            print("CAUSE DETERMINATION")
            print("-" * 100)

            print(
                "  [NOT YET PROVEN] Exact implementation cause is not inferred "
                "from numerical difference alone."
            )
            print(
                "  [EVIDENCE ONLY] Source signals and numerical differences "
                "are reported separately."
            )
            print(
                "  [STOP] No implementation change is authorized by this audit."
            )

            cause_rows.append({
                "symbol": symbol,
                "status": symbol_status,
                "ema_difference": ema_diff,
                "rsi_difference": rsi_diff,
                "history_count": len(closes),
            })

        section("FINAL CURRENT CONVENTION CAUSE FORENSIC SUMMARY")

        print(f"SYMBOLS CHECKED       : {len(targets)}")
        print(f"TOTAL EXACT           : {exact_total}")
        print(f"TOTAL MISMATCH        : {mismatch_total}")
        print(f"TOTAL UNRESOLVED      : {unresolved_total}")

        subsection("FORENSIC EVIDENCE SUMMARY")

        print("SOURCE EVIDENCE")
        print("-" * 100)
        print(
            f"  EMA FUNCTION FOUND       : {ema_info['function_found']}"
        )
        print(
            f"  EMA ALPHA SIGNAL         : {ema_info['alpha']}"
        )
        print(
            f"  EMA SEED SIGNAL          : {ema_info['seed']}"
        )
        print(
            f"  EMA RECURSIVE SIGNAL     : {ema_info['recursive']}"
        )
        print(
            f"  RSI FUNCTION FOUND       : {rsi_info['function_found']}"
        )
        print(
            f"  RSI GAIN/LOSS SIGNAL     : {rsi_info['gain_loss']}"
        )
        print(
            f"  RSI INITIAL AVG SIGNAL   : {rsi_info['initial_avg']}"
        )
        print(
            f"  RSI WILDER SIGNAL        : {rsi_info['wilder']}"
        )
        print(
            f"  RSI FORMULA SIGNAL       : {rsi_info['formula']}"
        )

        subsection("FORENSIC CONCLUSION")

        if unresolved_total > 0:
            print("STATUS : REVIEW_REQUIRED")
            print(
                "REASON : INSUFFICIENT HISTORY OR TARGET RESOLUTION"
            )

        elif mismatch_total > 0:
            print("STATUS : DIFFERENCE_CONFIRMED")
            print(
                "REASON : CURRENT VALUES DIFFER FROM STANDARD; "
                "EXACT CAUSE MUST BE PROVEN FROM SOURCE EVIDENCE"
            )

        else:
            print("STATUS : NO_DIFFERENCE_CONFIRMED")

        print()
        print("DATABASE WRITE OPERATIONS : NONE")
        print("ENGINE MODIFICATIONS      : NONE")
        print("FORMULA WRITE             : NONE")
        print("PRODUCTION RECALCULATION : NONE")
        print("AUDIT COMPLETE")

    finally:
        conn.close()


if __name__ == "__main__":
    main()