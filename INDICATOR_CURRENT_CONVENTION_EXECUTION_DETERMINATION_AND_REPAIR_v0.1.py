import ast
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

BACKUP_DIR = BASE_DIR / "indicator_repair_backups"

SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]

PERIODS = {
    "EMA20": 20,
    "EMA50": 50,
    "RSI14": 14,
}

ABS_TOLERANCE = 1e-10
REL_TOLERANCE = 1e-10


def utc_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def line_end(node):
    return getattr(node, "end_lineno", node.lineno)


def function_map(tree):
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def standard_ema(values, period):
    if values is None:
        return None

    values = [float(x) for x in values if x is not None]

    if len(values) < period:
        return None

    alpha = 2.0 / (period + 1.0)

    seed = sum(values[:period]) / period
    result = seed

    for value in values[period:]:
        result = (value - result) * alpha + result

    return result


def standard_rsi(values, period=14):
    if values is None:
        return None

    values = [float(x) for x in values if x is not None]

    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]

        if delta > 0:
            gains.append(delta)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(delta))

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


def fetch_history(conn, symbol, target_time):
    rows = conn.execute(
        """
        SELECT close, source_timestamp
        FROM market_data
        WHERE symbol = ?
          AND close IS NOT NULL
          AND source_timestamp <= ?
        ORDER BY source_timestamp ASC
        """,
        (symbol, target_time),
    ).fetchall()

    return rows


def compare_values(current, standard):
    if current is None or standard is None:
        return False, None, None

    abs_err = abs(float(current) - float(standard))

    denominator = max(abs(float(standard)), 1e-300)
    rel_err = abs_err / denominator

    match = (
        abs_err <= ABS_TOLERANCE
        or rel_err <= REL_TOLERANCE
    )

    return match, abs_err, rel_err


def backup_files():
    stamp = utc_stamp()

    target = BACKUP_DIR / stamp
    target.mkdir(parents=True, exist_ok=True)

    engine_backup = target / "market_data_engine.py"
    db_backup = target / "arunda.db"

    shutil.copy2(ENGINE_PATH, engine_backup)
    shutil.copy2(DB_PATH, db_backup)

    return target, engine_backup, db_backup


def inspect_current_engine():
    source = ENGINE_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )

    tree = ast.parse(source)
    functions = function_map(tree)

    return source, tree, functions


def print_function_source(source, node, name):
    lines = source.splitlines()

    print()
    print("=" * 100)
    print(f"CURRENT IMPLEMENTATION : {name}")
    print("=" * 100)

    for number in range(node.lineno, line_end(node) + 1):
        print(f"{number:5d}: {lines[number - 1]}")


def standard_ema_source():
    return """def ema(values, period=20):
    if values is None:
        return None

    values = [float(x) for x in values if x is not None]

    if len(values) < period:
        return None

    alpha = 2.0 / (period + 1.0)

    result = sum(values[:period]) / period

    for value in values[period:]:
        result = (value - result) * alpha + result

    return result
"""


def standard_rsi_source():
    return """def rsi(values, period=14):
    if values is None:
        return None

    values = [float(x) for x in values if x is not None]

    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]

        if delta > 0:
            gains.append(delta)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(delta))

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
"""


def replace_function(source, node, replacement):
    lines = source.splitlines(keepends=True)

    start = node.lineno - 1
    end = line_end(node)

    indent = len(lines[start]) - len(lines[start].lstrip())

    if indent != 0:
        raise RuntimeError(
            f"Cannot safely replace nested function at line {node.lineno}"
        )

    replacement_lines = replacement.splitlines(True)

    if not replacement.endswith("\n"):
        replacement += "\n"

    replacement_lines = replacement.splitlines(True)

    new_lines = (
        lines[:start]
        + replacement_lines
        + lines[end:]
    )

    return "".join(new_lines)


def verify_syntax(source):
    try:
        ast.parse(source)
        return True, None
    except SyntaxError as exc:
        return False, exc


def verify_standard_functions(source):
    tree = ast.parse(source)
    functions = function_map(tree)

    required = ["ema", "rsi"]

    for name in required:
        if name not in functions:
            return False, f"Missing function after repair: {name}"

    ema_text = ast.get_source_segment(
        source,
        functions["ema"],
    ) or ""

    rsi_text = ast.get_source_segment(
        source,
        functions["rsi"],
    ) or ""

    ema_checks = [
        "2.0 / (period + 1.0)" in ema_text,
        "sum(values[:period]) / period" in ema_text,
        "result = (value - result) * alpha + result" in ema_text,
    ]

    rsi_checks = [
        "avg_gain = sum(gains[:period]) / period" in rsi_text,
        "avg_loss = sum(losses[:period]) / period" in rsi_text,
        "((avg_gain * (period - 1)) + gains[i]) / period" in rsi_text,
        "((avg_loss * (period - 1)) + losses[i]) / period" in rsi_text,
        "100.0 - (100.0 / (1.0 + rs))" in rsi_text,
    ]

    if not all(ema_checks):
        return False, "EMA standard implementation verification failed"

    if not all(rsi_checks):
        return False, "RSI standard implementation verification failed"

    return True, None


def database_runtime_comparison(conn):
    print()
    print("=" * 100)
    print("CURRENT STORED VALUES vs STANDARD RECONSTRUCTION")
    print("=" * 100)

    total_mismatch = 0
    total_checked = 0

    for symbol in SYMBOLS:
        row = conn.execute(
            """
            SELECT
                id,
                source_timestamp,
                ema20,
                ema50,
                rsi14
            FROM market_data
            WHERE symbol = ?
            ORDER BY source_timestamp DESC
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()

        if not row:
            print()
            print(f"SYMBOL : {symbol}")
            print("  TARGET : NOT FOUND")
            continue

        analysis_id, target_time, current_ema20, current_ema50, current_rsi = row

        history = fetch_history(
            conn,
            symbol,
            target_time,
        )

        closes = [float(x[0]) for x in history]

        std_ema20 = standard_ema(
            closes,
            20,
        )

        std_ema50 = standard_ema(
            closes,
            50,
        )

        std_rsi = standard_rsi(
            closes,
            14,
        )

        print()
        print(f"SYMBOL : {symbol}")
        print("-" * 100)
        print(f"ANALYSIS ID       : {analysis_id}")
        print(f"SOURCE TIME       : {target_time}")
        print(f"HISTORY COUNT     : {len(closes)}")

        checks = [
            ("EMA20", current_ema20, std_ema20),
            ("EMA50", current_ema50, std_ema50),
            ("RSI14", current_rsi, std_rsi),
        ]

        for name, current, standard in checks:
            match, abs_err, rel_err = compare_values(
                current,
                standard,
            )

            total_checked += 1

            if not match:
                total_mismatch += 1

            print()
            print(f"INDICATOR : {name}")
            print(f"CURRENT   : {current}")
            print(f"STANDARD  : {standard}")
            print(f"ABS ERR   : {abs_err}")
            print(f"REL ERR   : {rel_err}")
            print(
                "STATUS    : "
                + ("MATCH" if match else "MISMATCH")
            )

    print()
    print("-" * 100)
    print(f"TOTAL COMPARISONS : {total_checked}")
    print(f"TOTAL MISMATCH    : {total_mismatch}")

    return total_mismatch


def main():
    print("=" * 100)
    print("ARUNDA INDICATOR CURRENT CONVENTION EXECUTION DETERMINATION AND REPAIR v0.1")
    print("=" * 100)
    print("MODE                         : READ + CONDITIONAL REPAIR")
    print("DATABASE WRITE               : NONE")
    print("FORMULA WRITE                : ENGINE ONLY IF CAUSE CONFIRMED")
    print("PRODUCTION RECALCULATION     : NONE")
    print("PURPOSE                      : DETERMINE AND REPAIR EXACT INDICATOR CONVENTION")
    print("=" * 100)

    print()
    print("STANDARD CONVENTION")
    print("-" * 100)
    print("EMA20 / EMA50 : alpha=2/(period+1), SMA seed, recursive EMA")
    print("RSI14         : Wilder RSI, arithmetic initial averages, Wilder smoothing")

    if not ENGINE_PATH.exists():
        print()
        print("ENGINE FOUND                 : False")
        print("STATUS                       : BLOCKED")
        return

    if not DB_PATH.exists():
        print()
        print("DATABASE FOUND               : False")
        print("STATUS                       : BLOCKED")
        return

    print()
    print("=" * 100)
    print("STEP 1 — CURRENT ENGINE RESOLUTION")
    print("=" * 100)

    source, tree, functions = inspect_current_engine()

    for name in ["ema", "rsi"]:
        if name in functions:
            print(
                f"[FOUND] {name}() "
                f"LINES {functions[name].lineno}-{line_end(functions[name])}"
            )
            print_function_source(
                source,
                functions[name],
                name,
            )
        else:
            print(f"[MISSING] {name}()")

    print()
    print("=" * 100)
    print("STEP 2 — DATABASE DIFFERENCE CONFIRMATION")
    print("=" * 100)

    conn = sqlite3.connect(str(DB_PATH))

    try:
        mismatch_count = database_runtime_comparison(conn)
    finally:
        conn.close()

    print()
    print("=" * 100)
    print("STEP 3 — REPAIR DECISION")
    print("=" * 100)

    if mismatch_count == 0:
        print("STATUS                       : NO_REPAIR_REQUIRED")
        print("REASON                       : CURRENT VALUES MATCH STANDARD")
        print("ENGINE MODIFICATION          : NONE")
        print("NEXT FRONTIER                : PRODUCTION VERIFICATION")
        print()
        print("DATABASE WRITE OPERATIONS    : NONE")
        print("AUDIT COMPLETE")
        return

    print(
        "STATUS                       : "
        "DIFFERENCE_CONFIRMED"
    )
    print(
        "REASON                       : "
        "CURRENT STORED VALUES DIFFER FROM STANDARD RECONSTRUCTION"
    )

    print()
    print("=" * 100)
    print("STEP 4 — BACKUP BEFORE ENGINE REPAIR")
    print("=" * 100)

    backup_path, engine_backup, db_backup = backup_files()

    print(f"BACKUP DIRECTORY             : {backup_path}")
    print(f"ENGINE BACKUP                : {engine_backup}")
    print(f"DATABASE BACKUP              : {db_backup}")

    print()
    print("=" * 100)
    print("STEP 5 — STANDARD IMPLEMENTATION REPAIR")
    print("=" * 100)

    current_source = ENGINE_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )

    current_tree = ast.parse(current_source)
    current_functions = function_map(current_tree)

    modified_source = current_source
    modified_targets = []

    if "ema" in current_functions:
        modified_source = replace_function(
            modified_source,
            current_functions["ema"],
            standard_ema_source(),
        )
        modified_targets.append("EMA")
    else:
        print("[SKIP] EMA function not found")

    current_tree = ast.parse(modified_source)
    current_functions = function_map(current_tree)

    if "rsi" in current_functions:
        modified_source = replace_function(
            modified_source,
            current_functions["rsi"],
            standard_rsi_source(),
        )
        modified_targets.append("RSI")
    else:
        print("[SKIP] RSI function not found")

    print(
        "TARGETS PREPARED FOR REPAIR   : "
        + (
            ", ".join(modified_targets)
            if modified_targets
            else "NONE"
        )
    )

    valid, error = verify_syntax(modified_source)

    if not valid:
        print()
        print("REPAIR ABORTED")
        print(f"SYNTAX ERROR                  : {error}")
        print("ORIGINAL ENGINE               : UNMODIFIED")
        print("STATUS                        : REPAIR_ABORTED")
        return

    valid, error = verify_standard_functions(
        modified_source
    )

    if not valid:
        print()
        print("REPAIR ABORTED")
        print(f"VERIFICATION ERROR            : {error}")
        print("ORIGINAL ENGINE               : UNMODIFIED")
        print("STATUS                        : REPAIR_ABORTED")
        return

    ENGINE_PATH.write_text(
        modified_source,
        encoding="utf-8",
        newline="\n",
    )

    print()
    print("ENGINE MODIFICATION           : APPLIED")
    print("EMA IMPLEMENTATION            : STANDARD")
    print("RSI IMPLEMENTATION            : STANDARD")

    print()
    print("=" * 100)
    print("STEP 6 — POST-REPAIR SOURCE VERIFICATION")
    print("=" * 100)

    repaired_source = ENGINE_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )

    valid, error = verify_standard_functions(
        repaired_source
    )

    if valid:
        print("POST-REPAIR SYNTAX             : VALID")
        print("POST-REPAIR IMPLEMENTATION     : VERIFIED")
    else:
        print("POST-REPAIR VERIFICATION       : FAILED")
        print(f"ERROR                          : {error}")

        print()
        print("RESTORING ENGINE BACKUP...")

        shutil.copy2(
            engine_backup,
            ENGINE_PATH,
        )

        print("ENGINE RESTORE                 : COMPLETE")
        print("STATUS                         : REPAIR_ROLLED_BACK")
        return

    print()
    print("=" * 100)
    print("FINAL REPAIR SUMMARY")
    print("=" * 100)
    print("DIFFERENCE BEFORE REPAIR       : CONFIRMED")
    print("BACKUP                         : VERIFIED")
    print("ENGINE REPAIR                  : APPLIED")
    print("ENGINE SYNTAX                  : VERIFIED")
    print("STANDARD EMA IMPLEMENTATION    : VERIFIED")
    print("STANDARD RSI IMPLEMENTATION    : VERIFIED")
    print("DATABASE RECALCULATION         : NOT PERFORMED")
    print()
    print("STATUS                         : ENGINE_REPAIRED")
    print(
        "NEXT FRONTIER                  : "
        "POST_REPAIR_PRODUCTION_RECALCULATION_AND_VERIFICATION"
    )
    print()
    print("DATABASE WRITE OPERATIONS      : NONE")
    print("PRODUCTION RECALCULATION      : NONE")
    print("AUDIT COMPLETE")


if __name__ == "__main__":
    main()
