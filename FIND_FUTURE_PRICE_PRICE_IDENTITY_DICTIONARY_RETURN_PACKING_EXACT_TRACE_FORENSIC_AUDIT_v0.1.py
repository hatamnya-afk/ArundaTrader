import os
import sys
import sqlite3
import importlib.util
import traceback
import dis
import types
import time


# =============================================================================
# ARUNDA FIND_FUTURE_PRICE PRICE IDENTITY DICTIONARY RETURN PACKING
# EXACT TRACE FORENSIC AUDIT v0.1
# =============================================================================

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"
TARGET_FILE = os.path.join(BASE_DIR, "signal_outcome_engine.py")
DATABASE = os.path.join(BASE_DIR, "arunda.db")

MODULE_NAME = "__arunda_forensic_exact_trace__"

WRITE_BLOCKED = True

stats = {
    "main_calls": 0,
    "process_signals_calls": 0,
    "create_outcome_calls": 0,
    "find_future_price_calls": 0,
    "find_future_price_returns": 0,
    "create_outcome_returns": 0,
    "main_returns": 0,
    "runtime_exceptions": 0,
    "blocked_write_attempts": 0,
    "price_identity_matches": 0,
    "dictionary_identity_matches": 0,
    "return_identity_matches": 0,
    "return_structure_snapshots": 0,
}

future_price_objects = []
price_local_objects = []
dictionary_matches = []
return_matches = []
return_structures = []

active_frames = {}


# =============================================================================
# READ-ONLY SQLITE CONNECTION
# =============================================================================

_original_sqlite_connect = sqlite3.connect


def forensic_connect(database, *args, **kwargs):
    """
    Read-only SQLite connection guard.

    Important:
    - Does NOT blindly add uri=True.
    - Prevents the previous 'multiple values for keyword argument uri' issue.
    - Existing production uri argument is respected.
    """

    global stats

    db_value = database

    if isinstance(db_value, os.PathLike):
        db_value = os.fspath(db_value)

    if isinstance(db_value, str):

        is_target_db = (
            os.path.abspath(db_value).lower()
            == os.path.abspath(DATABASE).lower()
        )

        if is_target_db:

            # If production already supplied uri=True, do not duplicate it.
            production_uri = kwargs.get("uri", False)

            if production_uri:
                if db_value.startswith("file:"):
                    readonly_database = db_value

                    if "mode=" not in readonly_database:
                        separator = "&" if "?" in readonly_database else "?"
                        readonly_database += separator + "mode=ro"

                    db_value = readonly_database
                else:
                    db_value = (
                        "file:"
                        + os.path.abspath(DATABASE)
                        + "?mode=ro"
                    )

            else:
                db_value = (
                    "file:"
                    + os.path.abspath(DATABASE)
                    + "?mode=ro"
                )
                kwargs["uri"] = True

    conn = _original_sqlite_connect(
        db_value,
        *args,
        **kwargs
    )

    # Defensive write blocking through authorizer.
    def authorizer(action, arg1, arg2, dbname, source):
        write_actions = {
            sqlite3.SQLITE_INSERT,
            sqlite3.SQLITE_UPDATE,
            sqlite3.SQLITE_DELETE,
            sqlite3.SQLITE_CREATE_INDEX,
            sqlite3.SQLITE_CREATE_TABLE,
            sqlite3.SQLITE_CREATE_TEMP_INDEX,
            sqlite3.SQLITE_CREATE_TEMP_TABLE,
            sqlite3.SQLITE_CREATE_TRIGGER,
            sqlite3.SQLITE_CREATE_VIEW,
            sqlite3.SQLITE_DROP_INDEX,
            sqlite3.SQLITE_DROP_TABLE,
            sqlite3.SQLITE_DROP_TEMP_INDEX,
            sqlite3.SQLITE_DROP_TEMP_TABLE,
            sqlite3.SQLITE_DROP_TRIGGER,
            sqlite3.SQLITE_DROP_VIEW,
            sqlite3.SQLITE_ALTER_TABLE,
        }

        if action in write_actions:
            stats["blocked_write_attempts"] += 1
            return sqlite3.SQLITE_DENY

        return sqlite3.SQLITE_OK

    try:
        conn.set_authorizer(authorizer)
    except Exception:
        pass

    return conn


sqlite3.connect = forensic_connect


# =============================================================================
# STATIC RESOLUTION
# =============================================================================

print("=" * 100)
print("ARUNDA FIND_FUTURE_PRICE PRICE IDENTITY DICTIONARY RETURN PACKING")
print("EXACT TRACE FORENSIC AUDIT v0.1")
print("=" * 100)
print("MODE                         : READ-ONLY EXACT IDENTITY FORENSICS")
print("TARGET                       :", TARGET_FILE)
print("DATABASE                     :", DATABASE)
print("PRODUCTION SOURCE MODIFIED  : NONE")
print("DATABASE WRITE               : BLOCKED")
print("=" * 100)


if not os.path.exists(TARGET_FILE):
    print("TARGET FILE NOT FOUND")
    sys.exit(1)


# =============================================================================
# LOAD PRODUCTION MODULE
# =============================================================================

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    TARGET_FILE
)

module = importlib.util.module_from_spec(spec)

sys.modules[MODULE_NAME] = module

try:
    spec.loader.exec_module(module)
except Exception as exc:
    print()
    print("=" * 100)
    print("MODULE LOAD ERROR")
    print("=" * 100)
    print(type(exc).__name__, repr(exc))
    traceback.print_exc()
    sys.exit(1)


# =============================================================================
# FUNCTION RESOLUTION
# =============================================================================

main_fn = getattr(module, "main", None)
process_fn = getattr(module, "process_signals", None)
create_fn = getattr(module, "create_outcome", None)
future_fn = getattr(module, "find_future_price", None)


print()
print("=" * 100)
print("STEP 1 — STATIC FUNCTION RESOLUTION")
print("=" * 100)

for name, fn in (
    ("main", main_fn),
    ("process_signals", process_fn),
    ("create_outcome", create_fn),
    ("find_future_price", future_fn),
):

    if fn is None:
        print(f"{name:24} : NOT FOUND")
    else:
        code = getattr(fn, "__code__", None)

        if code:
            print(
                f"{name:24} : FOUND | "
                f"LINE={code.co_firstlineno} | "
                f"FILE={code.co_filename}"
            )
        else:
            print(f"{name:24} : FOUND")


if not all(
    isinstance(fn, types.FunctionType)
    for fn in (
        main_fn,
        process_fn,
        create_fn,
        future_fn,
    )
):
    print()
    print("REQUIRED FUNCTIONS NOT RESOLVED")
    sys.exit(1)


# =============================================================================
# STATIC DICTIONARY / RETURN INSTRUCTION MAP
# =============================================================================

print()
print("=" * 100)
print("STEP 2 — CREATE_OUTCOME DICTIONARY / RETURN INSTRUCTION MAP")
print("=" * 100)

create_code = create_fn.__code__

interesting_ops = {
    "STORE_FAST",
    "STORE_SUBSCR",
    "BUILD_CONST_KEY_MAP",
    "BUILD_MAP",
    "BUILD_MAP_UNPACK",
    "BUILD_MAP_UNPACK_WITH_CALL",
    "RETURN_VALUE",
}

for instruction in dis.get_instructions(create_fn):

    if instruction.opname in interesting_ops:
        print(
            f"OFFSET={instruction.offset:<6} "
            f"LINE={str(instruction.starts_line):<6} "
            f"OP={instruction.opname:<30} "
            f"ARG={str(instruction.arg):<5} "
            f"ARGVAL={instruction.argval!r}"
        )


# =============================================================================
# IDENTITY HELPERS
# =============================================================================

def object_id(value):
    try:
        return id(value)
    except Exception:
        return None


def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception as exc:
        text = f"<repr-error:{type(exc).__name__}>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def is_price_candidate(value):
    """
    Future prices are expected to be scalar numeric values or None.
    """

    if value is None:
        return True

    return isinstance(
        value,
        (int, float)
    )


def contains_identity(container, target_id):
    """
    Recursively inspect dictionaries/lists/tuples/sets for the exact object
    identity of the future-price object.

    No equality comparison is used for the primary identity test.
    """

    seen = set()

    def walk(obj, path, depth=0):

        if depth > 12:
            return

        oid = id(obj)

        if oid == target_id:
            return path

        if oid in seen:
            return

        seen.add(oid)

        if isinstance(obj, dict):

            for key, value in obj.items():

                result = walk(
                    value,
                    path + [f"[{key!r}]"],
                    depth + 1
                )

                if result is not None:
                    return result

        elif isinstance(obj, (list, tuple)):

            for index, value in enumerate(obj):

                result = walk(
                    value,
                    path + [f"[{index}]"],
                    depth + 1
                )

                if result is not None:
                    return result

        elif isinstance(obj, set):

            for index, value in enumerate(obj):

                result = walk(
                    value,
                    path + [f"{{set:{index}}}"],
                    depth + 1
                )

                if result is not None:
                    return result

        return None

    return walk(container, [])


# =============================================================================
# FRAME TRACE
# =============================================================================

TARGET_CODE_OBJECTS = {
    main_fn.__code__,
    process_fn.__code__,
    create_fn.__code__,
    future_fn.__code__,
}


def trace_function_name(frame):
    return frame.f_code.co_name


def trace_event(frame, event, arg):

    name = trace_function_name(frame)

    if event == "call":

        if name == "main":
            stats["main_calls"] += 1

        elif name == "process_signals":
            stats["process_signals_calls"] += 1

        elif name == "create_outcome":
            stats["create_outcome_calls"] += 1

        elif name == "find_future_price":
            stats["find_future_price_calls"] += 1

        active_frames[id(frame)] = {
            "name": name,
            "frame": frame,
            "future_price_ids": [],
        }

        return trace_function

    if event == "return":

        if name == "find_future_price":

            stats["find_future_price_returns"] += 1

            future_price_objects.append({
                "id": id(arg),
                "type": type(arg).__name__,
                "value": safe_repr(arg),
                "frame_id": id(frame),
                "line": frame.f_lineno,
            })

            active = active_frames.get(id(frame))

            if active is not None:
                active["return_id"] = id(arg)

        elif name == "create_outcome":

            stats["create_outcome_returns"] += 1

            return_id = id(arg)

            snapshot = {
                "id": return_id,
                "type": type(arg).__name__,
                "value": safe_repr(arg, 2000),
                "frame_id": id(frame),
                "line": frame.f_lineno,
            }

            return_structures.append(snapshot)
            stats["return_structure_snapshots"] += 1

            active = active_frames.get(id(frame))

            if active is not None:
                active["return_id"] = return_id

        elif name == "main":
            stats["main_returns"] += 1

        active_frames.pop(id(frame), None)

        return None

    return trace_function


# =============================================================================
# LINE-LEVEL EXACT PRICE FLOW
# =============================================================================

def trace_function(frame, event, arg):

    name = frame.f_code.co_name

    if event == "line":

        if name == "find_future_price":

            return trace_function

        if name == "create_outcome":

            locals_copy = {}

            try:
                locals_copy = dict(frame.f_locals)
            except Exception:
                locals_copy = {}

            # -------------------------------------------------------------
            # EXACT LOCAL PRICE OBJECT
            # -------------------------------------------------------------

            if "price" in locals_copy:

                price = locals_copy.get("price")

                price_id = id(price)

                for item in future_price_objects:

                    if item["id"] == price_id:

                        stats["price_identity_matches"] += 1

                        observation = {
                            "line": frame.f_lineno,
                            "price_id": price_id,
                            "type": type(price).__name__,
                            "value": safe_repr(price),
                        }

                        price_local_objects.append(observation)

                        break

            # -------------------------------------------------------------
            # DICTIONARY IDENTITY
            # -------------------------------------------------------------

            price = locals_copy.get("price")

            if price is not None:

                price_id = id(price)

                for dictionary_name in (
                    "prices",
                    "returns",
                    "outcomes",
                ):

                    dictionary = locals_copy.get(dictionary_name)

                    if isinstance(dictionary, dict):

                        for key, value in dictionary.items():

                            if id(value) == price_id:

                                stats["dictionary_identity_matches"] += 1

                                match = {
                                    "line": frame.f_lineno,
                                    "dictionary": dictionary_name,
                                    "key": key,
                                    "price_id": price_id,
                                    "value": safe_repr(value),
                                }

                                dictionary_matches.append(match)

            # -------------------------------------------------------------
            # FINAL RETURN STRUCTURE IDENTITY
            # -------------------------------------------------------------

            for return_structure in return_structures:

                structure_repr = return_structure.get("value")

                if structure_repr is None:
                    continue

        return trace_function

    return trace_function


# =============================================================================
# COMBINED TRACE
# =============================================================================

def global_trace(frame, event, arg):

    if frame.f_code in TARGET_CODE_OBJECTS:
        return trace_function(frame, event, arg)

    return None


# =============================================================================
# EXECUTE GENUINE PRODUCTION ENTRYPOINT
# =============================================================================

print()
print("=" * 100)
print("STEP 3 — GENUINE PRODUCTION EXECUTION")
print("=" * 100)
print("ENTRYPOINT                  : main()")
print("EXECUTION MODE              : DIRECT FUNCTION INVOCATION")
print("TRACE MODE                  : CPYTHON sys.settrace")
print("WRITE MODE                  : READ-ONLY")
print("=" * 100)


start_time = time.time()

old_trace = sys.gettrace()

try:

    sys.settrace(global_trace)

    try:
        main_result = main_fn()

    except Exception as exc:

        stats["runtime_exceptions"] += 1

        print()
        print("=" * 100)
        print("TRACE EXCEPTION")
        print("=" * 100)
        print(
            f"{type(exc).__name__} | "
            f"{exc!r}"
        )

        main_result = None

finally:

    sys.settrace(old_trace)


# =============================================================================
# STEP 4 — FUTURE PRICE RETURNS
# =============================================================================

print()
print("=" * 100)
print("STEP 4 — CAPTURED FIND_FUTURE_PRICE RETURNS")
print("=" * 100)

if not future_price_objects:

    print("NONE")

else:

    for index, item in enumerate(
        future_price_objects,
        start=1
    ):

        print(
            f"{index:03d} | "
            f"ID={item['id']} | "
            f"TYPE={item['type']} | "
            f"VALUE={item['value']}"
        )


# =============================================================================
# STEP 5 — PRICE LOCAL IDENTITY
# =============================================================================

print()
print("=" * 100)
print("STEP 5 — EXACT PRICE LOCAL IDENTITY")
print("=" * 100)

if not price_local_objects:

    print("NO EXACT PRICE IDENTITY MATCHES")

else:

    for item in price_local_objects[:200]:

        print(
            f"LINE={item['line']} | "
            f"PRICE_ID={item['price_id']} | "
            f"TYPE={item['type']} | "
            f"VALUE={item['value']}"
        )

    if len(price_local_objects) > 200:
        print(
            f"... {len(price_local_objects) - 200} "
            f"additional observations omitted"
        )


# =============================================================================
# STEP 6 — DICTIONARY IDENTITY
# =============================================================================

print()
print("=" * 100)
print("STEP 6 — EXACT DICTIONARY IDENTITY")
print("=" * 100)

if not dictionary_matches:

    print("NO EXACT DICTIONARY IDENTITY MATCH")

else:

    for item in dictionary_matches[:300]:

        print(
            f"LINE={item['line']} | "
            f"DICT={item['dictionary']} | "
            f"KEY={item['key']!r} | "
            f"PRICE_ID={item['price_id']} | "
            f"VALUE={item['value']}"
        )

    if len(dictionary_matches) > 300:
        print(
            f"... {len(dictionary_matches) - 300} "
            f"additional dictionary matches omitted"
        )


# =============================================================================
# STEP 7 — RETURN STRUCTURES
# =============================================================================

print()
print("=" * 100)
print("STEP 7 — CREATE_OUTCOME RETURN STRUCTURES")
print("=" * 100)

if not return_structures:

    print("NONE")

else:

    for index, item in enumerate(
        return_structures,
        start=1
    ):

        print(
            f"RETURN {index:03d} | "
            f"TYPE={item['type']} | "
            f"ID={item['id']} | "
            f"VALUE={item['value']}"
        )


# =============================================================================
# STEP 8 — RETURN IDENTITY LOCALIZATION
# =============================================================================

print()
print("=" * 100)
print("STEP 8 — FINAL RETURN IDENTITY LOCALIZATION")
print("=" * 100)

future_ids = {
    item["id"]
    for item in future_price_objects
}

localized_return_matches = []

for structure in return_structures:

    # The actual return object cannot be reconstructed from repr.
    # Therefore identity matching is performed during execution whenever
    # the frame-local return object is available.
    #
    # This section intentionally reports only observations that were captured
    # without inventing equality matches.

    if structure["id"] in future_ids:

        stats["return_identity_matches"] += 1

        localized_return_matches.append(structure)


if localized_return_matches:

    for item in localized_return_matches:

        print(
            f"RETURN_IDENTITY_MATCH | "
            f"RETURN_ID={item['id']} | "
            f"TYPE={item['type']}"
        )

else:

    print("NO EXACT FUTURE-PRICE RETURN OBJECT IDENTITY MATCH")


# =============================================================================
# STEP 9 — MAIN RESULT
# =============================================================================

print()
print("=" * 100)
print("STEP 9 — MAIN RESULT")
print("=" * 100)

print(
    "MAIN RETURN                 : "
    f"TYPE={type(main_result).__name__} "
    f"VALUE={safe_repr(main_result, 1000)}"
)


# =============================================================================
# STEP 10 — SAFETY
# =============================================================================

print()
print("=" * 100)
print("STEP 10 — SAFETY VERIFICATION")
print("=" * 100)

print(
    "BLOCKED WRITE OPERATIONS      :",
    stats["blocked_write_attempts"]
)

print("PRODUCTION SOURCE MODIFIED    : NONE")
print("PRODUCTION FORMULA MODIFIED   : NONE")
print("PRODUCTION MAIN MODIFIED      : NONE")
print("DATABASE WRITE PERMITTED      : NO")


# =============================================================================
# STEP 11 — FINAL SUMMARY
# =============================================================================

print()
print("=" * 100)
print("STEP 11 — FINAL FORENSIC SUMMARY")
print("=" * 100)

print(
    "MAIN CALLS                  :",
    stats["main_calls"]
)

print(
    "PROCESS_SIGNALS CALLS       :",
    stats["process_signals_calls"]
)

print(
    "CREATE_OUTCOME CALLS        :",
    stats["create_outcome_calls"]
)

print(
    "FIND_FUTURE_PRICE CALLS     :",
    stats["find_future_price_calls"]
)

print(
    "FIND_FUTURE_PRICE RETURNS   :",
    stats["find_future_price_returns"]
)

print(
    "CREATE_OUTCOME RETURNS      :",
    stats["create_outcome_returns"]
)

print(
    "PRICE IDENTITY MATCHES      :",
    stats["price_identity_matches"]
)

print(
    "DICTIONARY IDENTITY MATCHES :",
    stats["dictionary_identity_matches"]
)

print(
    "FINAL RETURN IDENTITY       :",
    stats["return_identity_matches"]
)

print(
    "RETURN STRUCTURE SNAPSHOTS  :",
    stats["return_structure_snapshots"]
)

print(
    "RUNTIME EXCEPTIONS          :",
    stats["runtime_exceptions"]
)

print(
    "BLOCKED WRITE ATTEMPTS      :",
    stats["blocked_write_attempts"]
)


# =============================================================================
# FORENSIC CONCLUSION
# =============================================================================

print()
print("=" * 100)
print("FORENSIC CONCLUSION")
print("-" * 100)


if stats["find_future_price_returns"] == 0:

    status = "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"

    meaning = (
        "The genuine production runtime did not produce an observed "
        "find_future_price() return."
    )

    frontier = (
        "Resolve the runtime boundary before continuing exact "
        "price identity localization."
    )

elif stats["price_identity_matches"] == 0:

    status = "FIND_FUTURE_PRICE_RETURN_NOT_LOCALIZED"

    meaning = (
        "The genuine future-price return was observed, but exact "
        "identity localization into create_outcome().price was not established."
    )

    frontier = (
        "Trace the create_outcome() frame at the STORE_FAST / "
        "STORE_SUBSCR instruction boundary."
    )

elif stats["dictionary_identity_matches"] == 0:

    status = "FIND_FUTURE_PRICE_DICTIONARY_IDENTITY_UNRESOLVED"

    meaning = (
        "The genuine future-price object reached the local price variable, "
        "but exact identity preservation into the prices dictionary was "
        "not established."
    )

    frontier = (
        "Trace the exact STORE_SUBSCR instruction at the prices[label] "
        "assignment boundary."
    )

else:

    status = "FIND_FUTURE_PRICE_DICTIONARY_IDENTITY_LOCALIZED"

    meaning = (
        "The genuine future-price object was observed, localized into "
        "create_outcome().price, and observed entering a downstream "
        "dictionary value by exact object identity."
    )

    frontier = (
        "Trace the same object identity from the localized dictionary "
        "through final return construction."
    )


print("STATUS                      :", status)
print("MEANING                     :", meaning)
print("NEXT FRONTIER               :", frontier)

print()
print("DATABASE_WRITES             : NONE")
print("ENGINE_MODIFIED             : NONE")
print("PRODUCTION_SOURCE_MODIFIED  : NONE")
print("INSERT                      : NONE")
print("UPDATE                      : NONE")
print("DELETE                      : NONE")
print("ALTER                       : NONE")
print("CREATE                      : NONE")
print("DROP                        : NONE")
print("COMMIT                      : NONE")

elapsed = time.time() - start_time

print()
print("=" * 100)
print(f"ELAPSED SECONDS              : {elapsed:.3f}")
print("=" * 100)
print("AUDIT COMPLETE")