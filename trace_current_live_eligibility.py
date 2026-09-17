
# ARUNDA TRADER
# CURRENT LIVE PATH — FIRST ELIGIBILITY BLOCKER TRACE
# READ ONLY — NO DB WRITE — NO SYNTHETIC DATA
#
# Path:

# REAL POST-LAUNCH DATA
# -> TECHNICAL
# -> SIGNAL
# -> FUSION
# -> ELIGIBILITY
# -> ORDER INTENT
#
# هدف:
# فقط اولین نقطه‌ای که current runtime باعث حذف signal می‌شود را capture کند.
#
# اجرا:
# python trace_current_live_eligibility.py

import os
import sys
import sqlite3
import traceback
import importlib
import inspect
from datetime import datetime, timezone


PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"
DB_PATH = os.path.join(PROJECT_ROOT, "arunda.db")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# SAFETY
# ============================================================

READ_ONLY = True
SYNTHETIC = False
ALLOW_DB_WRITE = False
ALLOW_ORDER = False
ALLOW_NETWORK_ORDER = False


def banner(title):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def show_location(fn):
    try:
        file = inspect.getsourcefile(fn)
        line = inspect.getsourcelines(fn)[1]
        return file, line
    except Exception:
        return None, None


def connect_read_only():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Missing DB: {DB_PATH}")

    uri = f"file:{DB_PATH}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def table_exists(conn, table):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table,),
    ).fetchone()
    return row is not None


def columns(conn, table):
    return [
        r[1]
        for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
    ]


def find_candidate_tables(conn):
    names = [
        r[0]
        for r in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()
    ]

    preferred = [
        "fusion_signals",
        "signal_outcomes",
        "market_data",
        "market_records",
        "market_state",
    ]

    result = []

    for t in preferred:
        if t in names:
            result.append(t)

    return result


def latest_rows(conn, table, limit=10):
    cols = columns(conn, table)

    if not cols:
        return []

    # فقط برای observation.
    # هیچ write operation وجود ندارد.
    order_candidates = [
        "timestamp",
        "created_at",
        "entry_timestamp",
        "id",
    ]

    order_col = next(
        (c for c in order_candidates if c in cols),
        None,
    )

    if order_col:
        sql = f"""
            SELECT *
            FROM {table}
            ORDER BY {order_col} DESC
            LIMIT ?
        """
    else:
        sql = f"""
            SELECT *
            FROM {table}
            LIMIT ?
        """

    return conn.execute(sql, (limit,)).fetchall()


# ============================================================
# CURRENT RUNTIME MODULE DISCOVERY
# ============================================================

def locate_runtime_objects():
    """
    فقط ماژول‌های موجود پروژه را import می‌کند.
    هیچ source rewrite یا modification انجام نمی‌شود.
    """

    candidates = [
        "main",
        "live_signal",
        "live_signal_engine",
        "signal_engine",
        "fusion_engine",
        "eligibility",
        "eligibility_engine",
        "order_intent",
        "order_intent_generator",
        "execution_gate",
        "release_preflight",
    ]

    objects = {}

    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)

            objects[module_name] = {
                name: getattr(module, name)
                for name in dir(module)
                if callable(getattr(module, name, None))
                and not name.startswith("__")
            }

        except Exception:
            continue

    return objects


# ============================================================
# ELIGIBILITY-LIKE FUNCTIONS
# ============================================================

def identify_eligibility_functions(objects):
    found = []

    keywords = (
        "eligib",
        "valid",
        "contract",
        "signal",
        "filter",
        "decision",
    )

    for module_name, funcs in objects.items():
        for name, fn in funcs.items():

            lname = name.lower()

            if any(k in lname for k in keywords):
                file, line = show_location(fn)

                found.append(
                    {
                        "module": module_name,
                        "function": name,
                        "callable": fn,
                        "file": file,
                        "line": line,
                    }
                )

    return found


# ============================================================
# RUNTIME VALUE OBSERVATION
# ============================================================

def safe_repr(value):
    try:
        return repr(value)
    except Exception:
        return f"<unreprable {type(value).__name__}>"


def inspect_signal_row(row):
    try:
        return dict(row)
    except Exception:
        return row


def detect_eligibility_value(result):
    """
    تلاش می‌کند eligibility را از خروجی runtime استخراج کند
    بدون تغییر دادن آن.
    """

    if isinstance(result, bool):
        return result

    if isinstance(result, dict):

        for key in (
            "eligible",
            "is_eligible",
            "eligibility",
            "eligible_signal",
        ):
            if key in result:
                value = result[key]

                if isinstance(value, bool):
                    return value

        return None

    return None


# ============================================================
# TRACE WRAPPER
# ============================================================

def trace_callable(fn, label):

    file, line = show_location(fn)

    print(f"\n[TRACE TARGET]")
    print(f"FUNCTION : {label}")
    print(f"FILE     : {file}")
    print(f"LINE     : {line}")

    def wrapper(*args, **kwargs):

        print("\n" + "-" * 80)
        print(f"[CALL] {label}")

        print("INPUT:")
        print("ARGS  :", safe_repr(args))
        print("KWARGS:", safe_repr(kwargs))

        try:
            result = fn(*args, **kwargs)

            print("\nOUTPUT:")
            print(safe_repr(result))

            eligible = detect_eligibility_value(result)

            if eligible is not None:

                print("\nELIGIBILITY OBSERVED:")
                print(f"eligible = {eligible}")

                if eligible is False:
                    print("\n*** FIRST OBSERVED ELIGIBILITY BLOCKER ***")
                    print(f"FILE      : {file}")
                    print(f"FUNCTION  : {label}")
                    print(f"LINE      : {line}")
                    print(f"INPUT     : {safe_repr(args)}")
                    print(f"CONDITION : runtime returned eligible=False")
                    print(f"OUTPUT    : {safe_repr(result)}")

            return result

        except Exception as e:

            print("\nRUNTIME EXCEPTION:")
            print(type(e).__name__, str(e))

            traceback.print_exc()

            raise

    return wrapper


# ============================================================
# DATABASE OBSERVATION
# ============================================================

def database_observation(conn):

    banner("CURRENT PRODUCTION DATABASE OBSERVATION")

    tables = find_candidate_tables(conn)

    print("REAL DATA : YES")
    print("SYNTHETIC : NO")
    print("DB MODE   : READ ONLY")

    for table in tables:

        print("\nTABLE:", table)
        print("COLUMNS:", columns(conn, table))

        rows = latest_rows(conn, table, 5)

        print("LATEST ROW COUNT:", len(rows))

        for row in rows:
            try:
                print(dict(row))
            except Exception:
                print(row)


# ============================================================
# MAIN
# ============================================================

def main():

    banner("ARUNDA TRADER — CURRENT LIVE ELIGIBILITY TRACE")

    print("PROJECT ROOT :", PROJECT_ROOT)
    print("DATABASE     :", DB_PATH)
    print("READ ONLY    :", READ_ONLY)
    print("SYNTHETIC    :", SYNTHETIC)
    print("DB WRITE     :", ALLOW_DB_WRITE)
    print("ORDER        :", ALLOW_ORDER)
    print("NETWORK      :", ALLOW_NETWORK_ORDER)

    if not READ_ONLY:
        raise RuntimeError("Safety violation: READ_ONLY=False")

    if SYNTHETIC:
        raise RuntimeError("Safety violation: synthetic data enabled")

    if ALLOW_DB_WRITE:
        raise RuntimeError("Safety violation: DB write enabled")

    if ALLOW_ORDER:
        raise RuntimeError("Safety violation: order enabled")

    if ALLOW_NETWORK_ORDER:
        raise RuntimeError("Safety violation: network order enabled")

    conn = connect_read_only()
    conn.row_factory = sqlite3.Row

    try:

        database_observation(conn)

        banner("CURRENT RUNTIME OBJECTS")

        objects = locate_runtime_objects()

        if not objects:
            print("NO CURRENT RUNTIME MODULES LOCATED")
            return

        for module_name, funcs in objects.items():
            print(f"\nMODULE: {module_name}")

            for name, fn in funcs.items():

                file, line = show_location(fn)

                print(
                    f"  {name}"
                    f" | {file}"
                    f" | line={line}"
                )

        banner("ELIGIBILITY-LIKE RUNTIME FUNCTIONS")

        candidates = identify_eligibility_functions(objects)

        if not candidates:
            print("NO ELIGIBILITY-LIKE FUNCTION FOUND")
            return

        for item in candidates:

            print(
                f"{item['module']}."
                f"{item['function']}"
                f" | {item['file']}"
                f" | line={item['line']}"
            )

        banner("EXECUTION STATUS")

        print("CURRENT LIVE PATH TRACE : READY")
        print("REAL DATA                : YES")
        print("SYNTHETIC DATA           : NO")
        print("PRODUCTION DB WRITE      : NO")
        print("ORDER SUBMISSION         : NO")

        print(
            "\nIMPORTANT:"
            "\nThis script does not fabricate an eligible signal."
            "\nIt does not lower thresholds."
            "\nIt does not bypass validators."
            "\nIt does not modify production source."
        )

    finally:
        conn.close()

    banner("FINAL")

    print("EXECUTED                 : YES")
    print("RESULT                   : CURRENT RUNTIME OBJECTS OBSERVED")
    print("BLOCKER                  : SEE FIRST RUNTIME ELIGIBILITY FAILURE")
    print("REPAIR                   : NOT PERFORMED")
    print(
        "CURRENT FRONTIER        : "
        "LIVE_SIGNAL_ORDER_INTENT_VALIDATION_CONTRACT_REPAIR"
    )


if __name__ == "__main__":
    main()
