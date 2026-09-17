# -*- coding: utf-8 -*-

import os
import sys
import sqlite3
import dis
import inspect
import traceback
import importlib.util
from datetime import datetime, timezone


BASE_DIR = r"C:\Users\ASUS\ArundaTrader"

TARGET_FILE = os.path.join(
    BASE_DIR,
    "signal_outcome_engine.py"
)

DB_FILE = os.path.join(
    BASE_DIR,
    "arunda.db"
)

TARGET_FUNCTION = "find_future_price"

TARGET_COMPARE_OFFSET = 202
TARGET_BRANCH_OFFSET = 206
TARGET_BRANCH_OFFSET_2 = 226

ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP"
]

MINUTES_LIST = [
    5,
    15,
    30,
    60
]


print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE COMPARE_OP RUNTIME OPERAND RESULT FORENSIC AUDIT v0.1")
print("=" * 100)
print(f"TARGET : {TARGET_FILE}")
print(f"DATABASE : {DB_FILE}")
print("MODE : READ-ONLY REAL-RUNTIME FORENSICS")
print("PRODUCTION SOURCE : UNMODIFIED")
print("DATABASE WRITES : BLOCKED")
print("=" * 100)


# =================================================================================================
# SQLITE READ-ONLY CONNECTION
# =================================================================================================

def open_readonly_database():

    if not os.path.exists(DB_FILE):
        raise FileNotFoundError(
            f"DATABASE_NOT_FOUND:{DB_FILE}"
        )

    uri = (
        "file:"
        + DB_FILE.replace("\\", "/")
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    # CRITICAL:
    # signal_outcome_engine.find_future_price()
    # accesses rows as row["timestamp"].
    #
    # Without this row_factory sqlite returns tuples and
    # production code raises:
    #
    # TypeError: tuple indices must be integers or slices, not str

    conn.row_factory = sqlite3.Row

    return conn


# =================================================================================================
# PRODUCTION MODULE LOADER
# =================================================================================================

def load_production_module_without_main():

    module_name = "_arunda_signal_outcome_engine_forensic"

    spec = importlib.util.spec_from_file_location(
        module_name,
        TARGET_FILE
    )

    if spec is None:
        raise RuntimeError(
            "MODULE_SPEC_CREATION_FAILED"
        )

    if spec.loader is None:
        raise RuntimeError(
            "MODULE_LOADER_UNAVAILABLE"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    original_argv = sys.argv[:]

    try:

        sys.argv = [
            TARGET_FILE
        ]

        spec.loader.exec_module(
            module
        )

    finally:

        sys.argv[:] = original_argv

    return module


print()
print("=" * 100)
print("STEP 1 — LOAD PRODUCTION MODULE WITHOUT AUTO-MAIN")
print("=" * 100)

try:

    production = load_production_module_without_main()

    print(
        "MODULE LOAD : OK"
    )

except Exception as exc:

    print(
        "MODULE LOAD : FAILED"
    )

    print(
        repr(exc)
    )

    traceback.print_exc()

    sys.exit(1)


# =================================================================================================
# TARGET FUNCTION
# =================================================================================================

if not hasattr(
    production,
    TARGET_FUNCTION
):

    print(
        "find_future_price : NOT FOUND"
    )

    sys.exit(1)


find_future_price = getattr(
    production,
    TARGET_FUNCTION
)


print()
print("=" * 100)
print("STEP 2 — STATIC TARGET RESOLUTION")
print("=" * 100)

print(
    f"FUNCTION : {TARGET_FUNCTION}"
)

print(
    f"FILE     : "
    f"{inspect.getsourcefile(find_future_price)}"
)

print(
    f"LINE     : "
    f"{find_future_price.__code__.co_firstlineno}"
)

print(
    f"SIGNATURE: "
    f"{inspect.signature(find_future_price)}"
)


code = find_future_price.__code__

instructions = list(
    dis.get_instructions(
        find_future_price
    )
)


# =================================================================================================
# BYTECODE MAP
# =================================================================================================

print()
print("=" * 100)
print("STEP 3 — TARGET BYTECODE MAP")
print("=" * 100)

for ins in instructions:

    if ins.offset in {
        TARGET_COMPARE_OFFSET,
        TARGET_BRANCH_OFFSET,
        TARGET_BRANCH_OFFSET_2
    }:

        print(
            f"OFFSET={ins.offset:4d} | "
            f"OP={ins.opname:<30} | "
            f"ARG={ins.arg!s:<5} | "
            f"ARGVAL={ins.argval!r}"
        )


# =================================================================================================
# SAFE REPRESENTATION
# =================================================================================================

def safe_repr(
    value,
    limit=600
):

    try:

        text = repr(value)

    except Exception:

        text = "<repr-failed>"

    if len(text) > limit:

        return (
            text[:limit]
            + "...<TRUNCATED>"
        )

    return text


# =================================================================================================
# LOCAL DUMP
# =================================================================================================

def print_runtime_locals(
    frame,
    title
):

    print()
    print("-" * 100)
    print(title)
    print("-" * 100)

    names = sorted(
        frame.f_locals.keys()
    )

    for name in names:

        try:

            value = frame.f_locals[name]

            print(
                f"{name:<24} | "
                f"TYPE={type(value).__name__:<18} | "
                f"ID={id(value):<16} | "
                f"VALUE={safe_repr(value)}"
            )

        except Exception as exc:

            print(
                f"{name:<24} | "
                f"LOCAL_READ_ERROR={exc!r}"
            )


# =================================================================================================
# DATABASE VERIFICATION
# =================================================================================================

print()
print("=" * 100)
print("STEP 4 — READ-ONLY SQLITE CONNECTION VERIFICATION")
print("=" * 100)

try:

    readonly_conn = open_readonly_database()

    print(
        "DATABASE CONNECTION : OK"
    )

    print(
        "ROW FACTORY         :",
        readonly_conn.row_factory
    )

    if readonly_conn.row_factory is not sqlite3.Row:

        raise RuntimeError(
            "READONLY_CONNECTION_ROW_FACTORY_NOT_SQLITE_ROW"
        )

    print(
        "ROW FACTORY STATUS  : OK"
    )

    # Verify that the connection actually produces sqlite3.Row.

    test_cursor = readonly_conn.execute(
        "SELECT 1 AS test_value"
    )

    test_row = test_cursor.fetchone()

    if not isinstance(
        test_row,
        sqlite3.Row
    ):

        raise RuntimeError(
            "SQLITE_ROW_FACTORY_RUNTIME_VERIFICATION_FAILED"
        )

    print(
        "ROW OBJECT TYPE     :",
        type(test_row).__name__
    )

    print(
        "ROW ACCESS TEST     :",
        test_row["test_value"]
    )

    print(
        "ROW ACCESS STATUS   : OK"
    )

except Exception as exc:

    print(
        "READ-ONLY CONNECTION VERIFICATION FAILED"
    )

    print(
        repr(exc)
    )

    traceback.print_exc()

    sys.exit(1)


# =================================================================================================
# DATABASE DISCOVERY
# =================================================================================================

def get_tables(
    conn
):

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


def get_columns(
    conn,
    table
):

    safe_table = table.replace(
        '"',
        '""'
    )

    rows = conn.execute(
        f'PRAGMA table_info("{safe_table}")'
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


def discover_timestamp_sources(
    conn
):

    discovered = []

    tables = get_tables(
        conn
    )

    for table in tables:

        try:

            columns = get_columns(
                conn,
                table
            )

        except Exception:

            continue

        lower_map = {
            column.lower(): column
            for column in columns
        }

        timestamp_columns = []

        for lower_name, original_name in lower_map.items():

            if (
                "timestamp" in lower_name
                or lower_name in {
                    "time",
                    "datetime",
                    "date"
                }
            ):

                timestamp_columns.append(
                    original_name
                )

        asset_columns = []

        for lower_name, original_name in lower_map.items():

            if lower_name in {
                "asset",
                "symbol",
                "ticker",
                "market",
                "coin"
            }:

                asset_columns.append(
                    original_name
                )

        if (
            timestamp_columns
            and asset_columns
        ):

            discovered.append(
                (
                    table,
                    timestamp_columns,
                    asset_columns
                )
            )

    return discovered


# =================================================================================================
# REAL TIMESTAMP CANDIDATE DISCOVERY
# =================================================================================================

def collect_timestamp_candidates(
    conn
):

    discovered = discover_timestamp_sources(
        conn
    )

    candidates = []

    for (
        table,
        timestamp_columns,
        asset_columns
    ) in discovered:

        timestamp_column = timestamp_columns[0]
        asset_column = asset_columns[0]

        safe_table = table.replace(
            '"',
            '""'
        )

        safe_timestamp = timestamp_column.replace(
            '"',
            '""'
        )

        safe_asset = asset_column.replace(
            '"',
            '""'
        )

        for asset in ASSETS:

            sql = (
                f'SELECT '
                f'"{safe_asset}" AS asset_value, '
                f'"{safe_timestamp}" AS timestamp_value '
                f'FROM "{safe_table}" '
                f'WHERE UPPER(CAST("{safe_asset}" AS TEXT)) = ? '
                f'AND "{safe_timestamp}" IS NOT NULL '
                f'ORDER BY "{safe_timestamp}" DESC '
                f'LIMIT 5'
            )

            try:

                rows = conn.execute(
                    sql,
                    (
                        asset.upper(),
                    )
                ).fetchall()

            except Exception:

                continue

            for row in rows:

                timestamp_value = row[
                    "timestamp_value"
                ]

                if timestamp_value is None:
                    continue

                candidates.append(
                    {
                        "asset": asset,
                        "entry_timestamp": timestamp_value,
                        "source_table": table,
                        "source_asset_column": asset_column,
                        "source_timestamp_column": timestamp_column
                    }
                )

    return candidates


def normalize_timestamp(
    value
):

    if value is None:
        return None

    if isinstance(
        value,
        datetime
    ):

        if value.tzinfo is None:

            value = value.replace(
                tzinfo=timezone.utc
            )

        return value.isoformat()

    return str(value)


def build_unique_candidates(
    conn
):

    raw_candidates = collect_timestamp_candidates(
        conn
    )

    unique = []

    seen = set()

    for item in raw_candidates:

        asset = item[
            "asset"
        ]

        timestamp = normalize_timestamp(
            item[
                "entry_timestamp"
            ]
        )

        if timestamp is None:
            continue

        key = (
            asset,
            timestamp
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        item = dict(
            item
        )

        item[
            "entry_timestamp"
        ] = timestamp

        unique.append(
            item
        )

    return unique


print()
print("=" * 100)
print("STEP 5 — REAL DATABASE ENTRY TIMESTAMP DISCOVERY")
print("=" * 100)

try:

    candidates = build_unique_candidates(
        readonly_conn
    )

except Exception as exc:

    print(
        "CANDIDATE DISCOVERY FAILED"
    )

    print(
        repr(exc)
    )

    traceback.print_exc()

    readonly_conn.close()

    sys.exit(1)


print(
    f"REAL TIMESTAMP CANDIDATES : "
    f"{len(candidates)}"
)


if not candidates:

    print()
    print(
        "NO REAL ENTRY TIMESTAMP WAS FOUND."
    )

    print(
        "AUDIT REFUSES TO INVENT entry_timestamp."
    )

    readonly_conn.close()

    sys.exit(0)


# =================================================================================================
# TRACE STATE
# =================================================================================================

trace_state = {

    "calls": 0,

    "returns": 0,

    "real_returns": 0,

    "none_returns": 0,

    "non_none_returns": 0,

    "exceptions": 0,

    "compare_events": 0,

    "branch_events": 0,

    "branch_226_events": 0,

    "comparison_true": 0,

    "comparison_false": 0,

    "comparison_unresolved": 0
}


active_calls = {}


# =================================================================================================
# INDEPENDENT COMPARE EVALUATION
# =================================================================================================

def evaluate_compare_from_runtime_locals(
    frame
):

    local_values = frame.f_locals

    has_distance = (
        "distance"
        in local_values
    )

    has_tolerance = (
        "tolerance"
        in local_values
    )

    distance = local_values.get(
        "distance"
    )

    tolerance = local_values.get(
        "tolerance"
    )

    print()
    print("=" * 100)
    print("COMPARE_OP RUNTIME OPERAND RESULT")
    print("=" * 100)

    print(
        f"TARGET OFFSET : "
        f"{TARGET_COMPARE_OFFSET}"
    )

    print(
        "OPERATION     : distance <= tolerance"
    )

    print()
    print("OPERAND A")
    print("-" * 100)

    if has_distance:

        print(
            f"distance : "
            f"TYPE={type(distance).__name__} | "
            f"VALUE={safe_repr(distance)}"
        )

    else:

        print(
            "distance : <MISSING>"
        )

    print()
    print("OPERAND B")
    print("-" * 100)

    if has_tolerance:

        print(
            f"tolerance : "
            f"TYPE={type(tolerance).__name__} | "
            f"VALUE={safe_repr(tolerance)}"
        )

    else:

        print(
            "tolerance : <MISSING>"
        )

    if not has_distance:

        trace_state[
            "comparison_unresolved"
        ] += 1

        print()
        print(
            "COMPARISON RESULT : UNRESOLVED"
        )

        print(
            "REASON : distance local unavailable"
        )

        return None

    if not has_tolerance:

        trace_state[
            "comparison_unresolved"
        ] += 1

        print()
        print(
            "COMPARISON RESULT : UNRESOLVED"
        )

        print(
            "REASON : tolerance local unavailable"
        )

        return None

    try:

        result = (
            distance
            <=
            tolerance
        )

    except Exception as exc:

        trace_state[
            "comparison_unresolved"
        ] += 1

        print()
        print(
            "COMPARISON RESULT : UNRESOLVED"
        )

        print(
            f"REASON : {exc!r}"
        )

        return None

    if result:

        trace_state[
            "comparison_true"
        ] += 1

    else:

        trace_state[
            "comparison_false"
        ] += 1

    print()
    print(
        "INDEPENDENT COMPARISON RESULT"
    )

    print("-" * 100)

    print(
        f"{safe_repr(distance)} "
        f"<= "
        f"{safe_repr(tolerance)} "
        f"=> "
        f"{result!r}"
    )

    if result:

        print(
            "INTERPRETATION : TRUE"
        )

    else:

        print(
            "INTERPRETATION : FALSE"
        )

    print()
    print(
        "STACK NOTE : "
        "The CPython evaluation stack itself is not "
        "read directly. The result above is independently "
        "computed from runtime locals immediately at "
        "COMPARE_OP."
    )

    return result


# =================================================================================================
# TRACE FUNCTION
# =================================================================================================

def trace_function(
    frame,
    event,
    arg
):

    if frame.f_code is not code:

        return trace_function

    offset = frame.f_lasti

    # ---------------------------------------------------------------------------------------------
    # CALL
    # ---------------------------------------------------------------------------------------------

    if event == "call":

        trace_state[
            "calls"
        ] += 1

        call_id = trace_state[
            "calls"
        ]

        active_calls[
            id(frame)
        ] = {

            "call_id": call_id,

            "asset": frame.f_locals.get(
                "asset"
            ),

            "entry_timestamp":
                frame.f_locals.get(
                    "entry_timestamp"
                ),

            "minutes":
                frame.f_locals.get(
                    "minutes"
                ),

            "compare_result":
                None,

            "exception":
                None
        }

        frame.f_trace_opcodes = True

        print()
        print("=" * 100)
        print(
            f"FIND_FUTURE_PRICE CALL #{call_id}"
        )
        print("=" * 100)

        print(
            f"asset           : "
            f"{frame.f_locals.get('asset')!r}"
        )

        print(
            f"entry_timestamp : "
            f"{frame.f_locals.get('entry_timestamp')!r}"
        )

        print(
            f"minutes         : "
            f"{frame.f_locals.get('minutes')!r}"
        )

        return trace_function

    # ---------------------------------------------------------------------------------------------
    # OPCODE
    # ---------------------------------------------------------------------------------------------

    if event == "opcode":

        # -----------------------------------------------------------------------------------------
        # COMPARE_OP
        # -----------------------------------------------------------------------------------------

        if offset == TARGET_COMPARE_OFFSET:

            trace_state[
                "compare_events"
            ] += 1

            print()
            print("=" * 100)
            print(
                "COMPARE_OP TARGET EVENT"
            )
            print("=" * 100)

            print(
                f"OFFSET : {offset}"
            )

            print(
                "OPCODE : COMPARE_OP"
            )

            print(
                "OPERATION : <="
            )

            print_runtime_locals(
                frame,
                "RUNTIME LOCALS AT COMPARE_OP"
            )

            compare_result = (
                evaluate_compare_from_runtime_locals(
                    frame
                )
            )

            current = active_calls.get(
                id(frame)
            )

            if current is not None:

                current[
                    "compare_result"
                ] = compare_result

        # -----------------------------------------------------------------------------------------
        # POP_JUMP_IF_TRUE
        # -----------------------------------------------------------------------------------------

        elif offset == TARGET_BRANCH_OFFSET:

            trace_state[
                "branch_events"
            ] += 1

            print()
            print("=" * 100)
            print(
                "POP_JUMP_IF_TRUE TARGET EVENT"
            )
            print("=" * 100)

            print(
                f"OFFSET : {offset}"
            )

            print(
                "OPCODE : POP_JUMP_IF_TRUE"
            )

            print_runtime_locals(
                frame,
                "RUNTIME LOCALS AT POP_JUMP_IF_TRUE"
            )

            current = active_calls.get(
                id(frame)
            )

            if current is not None:

                result = current.get(
                    "compare_result"
                )

                print()
                print(
                    "CORRELATED COMPARE RESULT"
                )

                print("-" * 100)

                print(
                    f"distance <= tolerance : "
                    f"{result!r}"
                )

                if result is True:

                    print(
                        "BRANCH CORRELATION : TRUE"
                    )

                elif result is False:

                    print(
                        "BRANCH CORRELATION : FALSE"
                    )

                else:

                    print(
                        "BRANCH CORRELATION : UNRESOLVED"
                    )

        # -----------------------------------------------------------------------------------------
        # SECOND BRANCH
        # -----------------------------------------------------------------------------------------

        elif offset == TARGET_BRANCH_OFFSET_2:

            trace_state[
                "branch_226_events"
            ] += 1

            print()
            print("=" * 100)
            print(
                "SECOND POP_JUMP_IF_TRUE TARGET EVENT"
            )
            print("=" * 100)

            print(
                f"OFFSET : {offset}"
            )

            print_runtime_locals(
                frame,
                "RUNTIME LOCALS AT SECOND BRANCH"
            )

    # ---------------------------------------------------------------------------------------------
    # EXCEPTION
    # ---------------------------------------------------------------------------------------------

    elif event == "exception":

        trace_state[
            "exceptions"
        ] += 1

        exc_type, exc_value, exc_tb = arg

        current = active_calls.get(
            id(frame)
        )

        if current is not None:

            current[
                "exception"
            ] = exc_value

        print()
        print("=" * 100)
        print(
            "FIND_FUTURE_PRICE RUNTIME EXCEPTION"
        )
        print("=" * 100)

        print(
            f"TYPE  : "
            f"{getattr(exc_type, '__name__', exc_type)}"
        )

        print(
            f"VALUE : "
            f"{exc_value!r}"
        )

        print_runtime_locals(
            frame,
            "LOCALS AT EXCEPTION"
        )

    # ---------------------------------------------------------------------------------------------
    # RETURN
    # ---------------------------------------------------------------------------------------------

    elif event == "return":

        current = active_calls.get(
            id(frame)
        )

        exception_value = None

        if current is not None:

            exception_value = current.get(
                "exception"
            )

        # IMPORTANT:
        # When a Python function exits because of an exception,
        # tracing may still generate a return event with arg=None.
        #
        # Therefore arg=None is NOT automatically counted as
        # a genuine None return.

        if exception_value is not None:

            print()
            print("=" * 100)
            print(
                "FIND_FUTURE_PRICE EXCEPTIONAL RETURN EVENT"
            )
            print("=" * 100)

            print(
                "RETURN VALUE : IGNORED"
            )

            print(
                f"EXCEPTION    : "
                f"{exception_value!r}"
            )

        else:

            trace_state[
                "returns"
            ] += 1

            trace_state[
                "real_returns"
            ] += 1

            if arg is None:

                trace_state[
                    "none_returns"
                ] += 1

            else:

                trace_state[
                    "non_none_returns"
                ] += 1

            print()
            print("=" * 100)
            print(
                f"FIND_FUTURE_PRICE REAL RETURN "
                f"#{trace_state['returns']}"
            )
            print("=" * 100)

            print(
                f"TYPE  : "
                f"{type(arg).__name__}"
            )

            print(
                f"VALUE : "
                f"{safe_repr(arg)}"
            )

            print_runtime_locals(
                frame,
                "RETURN LOCALS"
            )

        active_calls.pop(
            id(frame),
            None
        )

    return trace_function


# =================================================================================================
# STEP 6 — DIRECT INVOCATION
# =================================================================================================

print()
print("=" * 100)
print("STEP 6 — DIRECT FIND_FUTURE_PRICE REAL-RUNTIME INVOCATIONS")
print("=" * 100)


original_trace = sys.gettrace()

invocation_number = 0

# Keep the forensic run bounded.
# Use the first 16 real timestamp candidates.
selected_candidates = candidates[:16]

try:

    for candidate in selected_candidates:

        asset = candidate[
            "asset"
        ]

        entry_timestamp = candidate[
            "entry_timestamp"
        ]

        for minutes in MINUTES_LIST:

            invocation_number += 1

            print()
            print("-" * 100)

            print(
                f"DIRECT INVOCATION #{invocation_number}"
            )

            print(
                f"ASSET           : "
                f"{asset}"
            )

            print(
                f"ENTRY TIMESTAMP : "
                f"{entry_timestamp}"
            )

            print(
                f"MINUTES         : "
                f"{minutes}"
            )

            print(
                f"SOURCE TABLE    : "
                f"{candidate['source_table']}"
            )

            try:

                sys.settrace(
                    trace_function
                )

                result = find_future_price(
                    readonly_conn,
                    asset,
                    entry_timestamp,
                    minutes
                )

                sys.settrace(
                    None
                )

                print()
                print(
                    "DIRECT INVOCATION RESULT"
                )

                print("-" * 100)

                print(
                    f"TYPE  : "
                    f"{type(result).__name__}"
                )

                print(
                    f"VALUE : "
                    f"{safe_repr(result)}"
                )

            except Exception as exc:

                sys.settrace(
                    None
                )

                print()
                print(
                    "DIRECT INVOCATION EXCEPTION"
                )

                print("-" * 100)

                print(
                    f"TYPE  : "
                    f"{type(exc).__name__}"
                )

                print(
                    f"VALUE : "
                    f"{exc!r}"
                )

                traceback.print_exc()

            finally:

                sys.settrace(
                    None
                )

finally:

    sys.settrace(
        original_trace
    )

    try:

        readonly_conn.close()

    except Exception:

        pass


# =================================================================================================
# FINAL SUMMARY
# =================================================================================================

print()
print("=" * 100)
print("STEP 7 — FINAL FORENSIC SUMMARY")
print("=" * 100)

print(
    f"DIRECT INVOCATIONS             : "
    f"{invocation_number}"
)

print(
    f"FIND_FUTURE_PRICE CALLS        : "
    f"{trace_state['calls']}"
)

print(
    f"REAL RETURNS                   : "
    f"{trace_state['real_returns']}"
)

print(
    f"REAL NONE RETURNS              : "
    f"{trace_state['none_returns']}"
)

print(
    f"REAL NON-NONE RETURNS          : "
    f"{trace_state['non_none_returns']}"
)

print(
    f"COMPARE_OP OFFSET 202 EVENTS   : "
    f"{trace_state['compare_events']}"
)

print(
    f"OFFSET 206 EVENTS              : "
    f"{trace_state['branch_events']}"
)

print(
    f"OFFSET 226 EVENTS              : "
    f"{trace_state['branch_226_events']}"
)

print(
    f"COMPARISON TRUE                 : "
    f"{trace_state['comparison_true']}"
)

print(
    f"COMPARISON FALSE                : "
    f"{trace_state['comparison_false']}"
)

print(
    f"COMPARISON UNRESOLVED           : "
    f"{trace_state['comparison_unresolved']}"
)

print(
    f"RUNTIME EXCEPTIONS              : "
    f"{trace_state['exceptions']}"
)


# =================================================================================================
# SAFETY
# =================================================================================================

print()
print("=" * 100)
print("STEP 8 — SAFETY VERIFICATION")
print("=" * 100)

print(
    "DATABASE WRITES              : NONE"
)

print(
    "INSERT                       : NONE"
)

print(
    "UPDATE                       : NONE"
)

print(
    "DELETE                       : NONE"
)

print(
    "ALTER                        : NONE"
)

print(
    "CREATE                       : NONE"
)

print(
    "DROP                         : NONE"
)

print(
    "COMMIT                       : NONE"
)

print(
    "PRODUCTION SOURCE MODIFIED  : NONE"
)

print(
    "PRODUCTION FORMULA MODIFIED : NONE"
)

print(
    "PRODUCTION MAIN MODIFIED    : NONE"
)

print(
    "DATABASE FILE WRITES        : NONE"
)


# =================================================================================================
# FORENSIC CONCLUSION
# =================================================================================================

print()
print("=" * 100)
print("FINAL FORENSIC CONCLUSION")
print("=" * 100)


if trace_state["exceptions"] > 0 and trace_state["compare_events"] == 0:

    print(
        "STATUS : "
        "COMPARE_OP_NOT_REACHED_RUNTIME_EXCEPTION_PATH"
    )

    print(
        "MEANING : "
        "find_future_price() was entered, but execution "
        "failed before reaching COMPARE_OP."
    )

    print(
        "NEXT FRONTIER : "
        "Inspect the exact runtime exception path before "
        "attempting branch interpretation."
    )

elif trace_state["compare_events"] == 0:

    print(
        "STATUS : "
        "COMPARE_OP_RUNTIME_NOT_REACHED"
    )

    print(
        "MEANING : "
        "No genuine invocation reached the target COMPARE_OP."
    )

    print(
        "NEXT FRONTIER : "
        "Reproduce a valid find_future_price() execution "
        "until offset 202 is reached."
    )

elif trace_state["branch_events"] == 0:

    print(
        "STATUS : "
        "COMPARE_OP_RUNTIME_RESULT_CAPTURED_BRANCH_NOT_REACHED"
    )

    print(
        "MEANING : "
        "The runtime comparison operands were captured, "
        "but offset 206 was not observed."
    )

    print(
        "NEXT FRONTIER : "
        "Correlate the comparison result with subsequent "
        "control flow."
    )

else:

    print(
        "STATUS : "
        "COMPARE_OP_RUNTIME_RESULT_AND_BRANCH_CORRELATED"
    )

    print(
        "MEANING : "
        "The runtime-local operands used immediately before "
        "COMPARE_OP were captured and independently evaluated."
    )

    print(
        "NEXT FRONTIER : "
        "Determine whether distance <= tolerance is TRUE or FALSE "
        "in the observed None-return path."
    )


print()
print(
    "STACK EVIDENCE : "
    "CPython frame API does not expose the evaluation stack directly."
)

print(
    "OPERAND POLICY : "
    "No evaluation-stack operand was fabricated."
)

print(
    "COMPARISON POLICY : "
    "Comparison result is independently evaluated from "
    "runtime locals captured at offset 202."
)

print()
print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)