import ast
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

TARGETS = {
    "EMA20": ("ema20", "ema", 20),
    "EMA50": ("ema50", "ema", 50),
    "RSI14": ("rsi14", "rsi", 14),
}

def end_line(node):
    return getattr(node, "end_lineno", node.lineno)

def get_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None

def get_functions(tree):
    return {
        n.name: n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

def get_calls(node, name):
    return [
        n for n in ast.walk(node)
        if isinstance(n, ast.Call) and get_name(n.func) == name
    ]

def source(node):
    return ast.get_source_segment(ENGINE_SOURCE, node) or ""

def implementation_signals(node, kind):
    text = source(node).lower()

    if kind == "ema":
        return {
            "alpha": (
                "2.0 / (period + 1)" in text
                or "2 / (period + 1)" in text
            ),
            "seed": "mean(" in text,
            "recursive": (
                "result[-1]" in text
                or "previous" in text
                or "alpha *" in text
            ),
        }

    return {
        "gain_loss": "gains" in text and "losses" in text,
        "initial_avg": "mean(" in text,
        "wilder": "avg_gain" in text and "avg_loss" in text,
        "formula": "100.0 - 100.0 /" in text,
    }

def print_target(name, field, producer, functions):
    print("=" * 100)
    print(f"TARGET : {name}")
    print("=" * 100)

    fn = functions.get(producer)

    print()
    print("1. PRODUCER FUNCTION")
    print("-" * 100)

    if not fn:
        print("  [MISSING] :", producer)
        return "UNRESOLVED"

    print(
        f"  [FOUND] : {producer}() "
        f"LINES {fn.lineno}-{end_line(fn)}"
    )

    print()
    print("2. EXACT IMPLEMENTATION")
    print("-" * 100)

    returns = [
        n for n in ast.walk(fn)
        if isinstance(n, ast.Return)
    ]

    if returns:
        for ret in returns:
            try:
                value = ast.unparse(ret.value) if ret.value else "None"
            except Exception:
                value = "<expression>"
            print(
                f"  [RETURN] LINE {ret.lineno} : {value}"
            )
    else:
        print("  [MISSING] : RETURN")

    print()
    print("3. IMPLEMENTATION SIGNALS")
    print("-" * 100)

    sig = implementation_signals(fn, producer)

    if producer == "ema":
        print(
            "  EMA ALPHA FORMULA            :",
            "FOUND" if sig["alpha"] else "NOT FOUND"
        )
        print(
            "  EMA SEED                     :",
            "FOUND" if sig["seed"] else "NOT FOUND"
        )
        print(
            "  EMA RECURSIVE UPDATE         :",
            "FOUND" if sig["recursive"] else "NOT FOUND"
        )
    else:
        print(
            "  GAIN / LOSS                  :",
            "FOUND" if sig["gain_loss"] else "NOT FOUND"
        )
        print(
            "  INITIAL AVERAGE              :",
            "FOUND" if sig["initial_avg"] else "NOT FOUND"
        )
        print(
            "  WILDER SMOOTHING             :",
            "FOUND" if sig["wilder"] else "NOT FOUND"
        )
        print(
            "  RSI FORMULA                  :",
            "FOUND" if sig["formula"] else "NOT FOUND"
        )

    print()
    print("4. CALCULATE_ANALYSIS CALL-SITE")
    print("-" * 100)

    calculate = functions.get("calculate_analysis")
    direct_calls = []

    if calculate:
        direct_calls = get_calls(calculate, producer)

    if direct_calls:
        for call in direct_calls:
            try:
                expr = ast.unparse(call)
            except Exception:
                expr = producer + "(...)"

            print(
                f"  [FOUND] LINE {call.lineno} : {expr}"
            )
    else:
        print("  [NOT FOUND] : direct producer call")

    print()
    print("5. TARGET FIELD REFERENCES")
    print("-" * 100)

    refs = []

    for i, line in enumerate(ENGINE_LINES, 1):
        if field in line:
            refs.append((i, line.strip()))

    if refs:
        for i, line in refs:
            print(
                f"  [REFERENCE] LINE {i} : {line}"
            )
    else:
        print("  [NONE]")

    print()
    print("IMPLEMENTATION FORENSIC VERDICT")
    print("-" * 100)

    if direct_calls and returns:
        print("STATUS : IMPLEMENTATION_PATH_RESOLVED")
        return "RESOLVED"

    print("STATUS : IMPLEMENTATION_PATH_INCOMPLETE")
    return "PARTIAL"

def runtime_inventory():
    print("=" * 100)
    print("RUNTIME TARGET INVENTORY")
    print("=" * 100)

    if not DB_PATH.exists():
        print("DATABASE FOUND : False")
        return

    conn = sqlite3.connect(str(DB_PATH))

    try:
        rows = conn.execute(
            """
            SELECT id, symbol, source_timestamp,
                   engine_version, ema20, ema50, rsi14
            FROM market_data
            WHERE symbol IN ('BTC','ETH','SOL','XRP')
            ORDER BY id DESC
            LIMIT 4
            """
        ).fetchall()

        for row in rows:
            print()
            print(f"SYMBOL : {row[1]}")
            print("-" * 100)
            print(f"ID              : {row[0]}")
            print(f"SYMBOL          : {row[1]}")
            print(f"SOURCE TIME     : {row[2]}")
            print(f"ENGINE VERSION  : {row[3]}")
            print(f"EMA20           : {row[4]}")
            print(f"EMA50           : {row[5]}")
            print(f"RSI14           : {row[6]}")

    finally:
        conn.close()

def main():
    global ENGINE_SOURCE
    global ENGINE_LINES

    print("=" * 100)
    print("ARUNDA INDICATOR CURRENT CONVENTION IMPLEMENTATION FORENSIC AUDIT v0.1")
    print("=" * 100)
    print("MODE                         : READ ONLY")
    print("DATABASE WRITE               : NONE")
    print("FORMULA WRITE                : NONE")
    print("PRODUCTION RECALCULATION    : NONE")
    print("PURPOSE                      : EXACT INDICATOR IMPLEMENTATION FORENSICS")
    print("=" * 100)

    print()
    print("STANDARD TARGET")
    print("-" * 100)
    print("EMA20 / EMA50 : alpha=2/(period+1), SMA seed, recursive EMA")
    print("RSI14         : Wilder RSI, arithmetic initial averages, Wilder smoothing")

    print()
    print("=" * 100)
    print("DATABASE INVENTORY")
    print("=" * 100)
    print(f"DATABASE PATH               : {DB_PATH}")
    print(f"DATABASE FOUND              : {DB_PATH.exists()}")

    if not ENGINE_PATH.exists():
        print()
        print("ENGINE FOUND                : False")
        print("AUDIT STATUS                : BLOCKED")
        return

    ENGINE_SOURCE = ENGINE_PATH.read_text(
        encoding="utf-8",
        errors="replace"
    )

    ENGINE_LINES = ENGINE_SOURCE.splitlines()

    print()
    print("=" * 100)
    print("ENGINE SOURCE INVENTORY")
    print("=" * 100)
    print(f"ENGINE PATH                 : {ENGINE_PATH}")
    print(f"ENGINE FOUND                : True")
    print(f"SOURCE SIZE                 : {len(ENGINE_SOURCE)} characters")
    print(f"SOURCE LINES                : {len(ENGINE_LINES)}")

    try:
        tree = ast.parse(ENGINE_SOURCE)
    except SyntaxError as exc:
        print("AST STATUS                  : FAILED")
        print(f"SYNTAX ERROR                : {exc}")
        return

    print("AST STATUS                  : SUCCESS")

    functions = get_functions(tree)

    print()
    print("=" * 100)
    print("FUNCTION INVENTORY")
    print("=" * 100)

    for name in ("ema", "ema_series", "rsi"):
        fn = functions.get(name)

        if fn:
            print(
                f"  [FOUND] : {name}() "
                f"LINE {fn.lineno}-{end_line(fn)}"
            )
        else:
            print(f"  [NOT FOUND] : {name}()")

    results = []

    for name, (field, producer, period) in TARGETS.items():
        results.append(
            (
                name,
                print_target(
                    name,
                    field,
                    producer,
                    functions
                )
            )
        )

    runtime_inventory()

    print()
    print("=" * 100)
    print("FINAL IMPLEMENTATION FORENSIC SUMMARY")
    print("=" * 100)

    resolved = sum(
        1 for _, status in results
        if status == "RESOLVED"
    )

    partial = sum(
        1 for _, status in results
        if status == "PARTIAL"
    )

    unresolved = sum(
        1 for _, status in results
        if status == "UNRESOLVED"
    )

    print(f"TARGETS CHECKED              : {len(results)}")
    print(f"IMPLEMENTATION RESOLVED     : {resolved}")
    print(f"IMPLEMENTATION PARTIAL       : {partial}")
    print(f"IMPLEMENTATION UNRESOLVED    : {unresolved}")

    print()
    print("TARGET MATRIX")
    print("-" * 100)

    for name, status in results:
        print(
            f"  [{status:10}] : {name}"
        )

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("=" * 100)

    if unresolved == 0 and partial == 0:
        print("STATUS                      : IMPLEMENTATION_PATH_RESOLVED")
        print("REASON                      : ALL TARGET IMPLEMENTATIONS ARE TRACEABLE")
        print("NEXT FRONTIER               : EXACT CONVENTION EXECUTION DETERMINATION")
    else:
        print("STATUS                      : IMPLEMENTATION_PATH_INCOMPLETE")
        print("REASON                      : ONE OR MORE IMPLEMENTATIONS REMAIN INCOMPLETE")
        print("NEXT FRONTIER               : INSPECT ONLY REMAINING IMPLEMENTATION GAPS")

    print()
    print("DATABASE WRITE OPERATIONS   : NONE")
    print("ENGINE MODIFICATIONS        : NONE")
    print("FORMULA WRITE               : NONE")
    print("PRODUCTION RECALCULATION   : NONE")
    print("AUDIT COMPLETE")

if __name__ == "__main__":
    main()
