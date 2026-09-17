# -*- coding: utf-8 -*-

import os
import sys
import ast
import sqlite3
import runpy
import time
import traceback


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

TARGET_FILE = os.path.join(
    PROJECT_DIR,
    "signal_outcome_engine.py"
)

DB_FILE = os.path.join(
    PROJECT_DIR,
    "arunda.db"
)

CREATE_NAME = "create_outcome"
FUTURE_NAME = "find_future_price"

WRITE_PREFIXES = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "CREATE",
    "DROP",
    "REPLACE",
    "VACUUM",
    "REINDEX",
    "ATTACH",
    "DETACH",
)


# =============================================================================
# STATE
# =============================================================================

STATE = {
    "create_calls": 0,
    "create_returns": 0,

    "future_calls": 0,
    "future_returns": 0,

    "runtime_exceptions": 0,
    "blocked_writes": 0,

    "future_records": [],
    "price_observations": [],
    "container_observations": [],
    "return_records": [],

    "assignment_events": [],
    "return_events": [],

    "source_modified": False,
}


# =============================================================================
# HELPERS
# =============================================================================

def safe_repr(value, limit=700):

    try:
        text = repr(value)
    except Exception:
        text = "<unrepresentable>"

    if len(text) > limit:
        return text[:limit] + "...<truncated>"

    return text


def value_type(value):

    try:
        return type(value).__name__
    except Exception:
        return "<unknown>"


def object_id(value):

    try:
        return id(value)
    except Exception:
        return None


def is_container(value):

    return isinstance(
        value,
        (dict, list, tuple, set)
    )


def scalar_equal(a, b):

    if a is b:
        return True

    try:
        if is_container(a) or is_container(b):
            return False

        return a == b

    except Exception:
        return False


# =============================================================================
# STATIC ANALYSIS
# =============================================================================

def static_resolution():

    print("=" * 100)
    print("STEP 1 — STATIC DICTIONARY / RETURN RESOLUTION")
    print("=" * 100)

    with open(
        TARGET_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        source = f.read()

    tree = ast.parse(
        source,
        filename=TARGET_FILE
    )

    create_node = None
    future_node = None

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.FunctionDef
        ):

            if node.name == CREATE_NAME:
                create_node = node

            elif node.name == FUTURE_NAME:
                future_node = node

    if create_node is None:
        raise RuntimeError(
            "create_outcome() not found"
        )

    if future_node is None:
        raise RuntimeError(
            "find_future_price() not found"
        )

    print(
        f"TARGET FILE              : "
        f"{TARGET_FILE}"
    )

    print(
        "CREATE_OUTCOME           : FOUND"
    )

    print(
        "FIND_FUTURE_PRICE        : FOUND"
    )

    print()

    print(
        "CREATE_OUTCOME ASSIGNMENTS"
    )

    print("-" * 100)

    for node in ast.walk(create_node):

        if not isinstance(
            node,
            ast.Assign
        ):
            continue

        targets = []

        for target in node.targets:

            try:
                targets.append(
                    ast.unparse(target)
                )

            except Exception:
                targets.append(
                    "<target>"
                )

        try:
            expression = ast.unparse(
                node.value
            )

        except Exception:
            expression = "<expression>"

        expression = " ".join(
            expression.split()
        )

        print(
            f"LINE={node.lineno:<5} | "
            f"TARGET={','.join(targets):<35} | "
            f"VALUE={expression}"
        )

    print()

    print(
        "CREATE_OUTCOME RETURN EXPRESSIONS"
    )

    print("-" * 100)

    for node in ast.walk(create_node):

        if isinstance(
            node,
            ast.Return
        ):

            try:
                expression = ast.unparse(
                    node.value
                )

            except Exception:
                expression = "<return>"

            expression = " ".join(
                expression.split()
            )

            print(
                f"LINE={node.lineno:<5} | "
                f"RETURN={expression}"
            )

    print()

    print(
        "DICTIONARY LITERALS INSIDE CREATE_OUTCOME"
    )

    print("-" * 100)

    for node in ast.walk(create_node):

        if isinstance(
            node,
            ast.Dict
        ):

            try:
                expression = ast.unparse(node)

            except Exception:
                expression = "<dict>"

            expression = " ".join(
                expression.split()
            )

            print(
                f"LINE={node.lineno:<5} | "
                f"DICT={expression}"
            )

    return source


# =============================================================================
# WRITE-NEUTRALIZED SQLITE
# =============================================================================

_ORIGINAL_CONNECT = sqlite3.connect


class NeutralizedCursor:

    def __init__(self, cursor):

        self._cursor = cursor

    def execute(
        self,
        sql,
        parameters=()
    ):

        sql_text = str(sql).strip()
        upper = sql_text.upper()

        if any(
            upper.startswith(prefix)
            for prefix in WRITE_PREFIXES
        ):

            STATE["blocked_writes"] += 1

            return self

        self._cursor.execute(
            sql,
            parameters
        )

        return self

    def executemany(
        self,
        sql,
        parameters
    ):

        sql_text = str(sql).strip()
        upper = sql_text.upper()

        if any(
            upper.startswith(prefix)
            for prefix in WRITE_PREFIXES
        ):

            STATE["blocked_writes"] += 1

            return self

        self._cursor.executemany(
            sql,
            parameters
        )

        return self

    def executescript(
        self,
        script
    ):

        STATE["blocked_writes"] += 1

        return self

    def fetchone(self):

        return self._cursor.fetchone()

    def fetchall(self):

        return self._cursor.fetchall()

    def fetchmany(
        self,
        size=None
    ):

        if size is None:
            return self._cursor.fetchmany()

        return self._cursor.fetchmany(size)

    @property
    def description(self):

        return self._cursor.description

    @property
    def rowcount(self):

        return self._cursor.rowcount

    @property
    def lastrowid(self):

        return self._cursor.lastrowid

    def close(self):

        return self._cursor.close()

    def __iter__(self):

        return iter(self._cursor)

    def __getattr__(self, name):

        return getattr(
            self._cursor,
            name
        )


class NeutralizedConnection:

    def __init__(
        self,
        connection
    ):

        self._connection = connection

    def cursor(self):

        return NeutralizedCursor(
            self._connection.cursor()
        )

    def execute(
        self,
        sql,
        parameters=()
    ):

        cursor = NeutralizedCursor(
            self._connection.cursor()
        )

        return cursor.execute(
            sql,
            parameters
        )

    def executemany(
        self,
        sql,
        parameters
    ):

        cursor = NeutralizedCursor(
            self._connection.cursor()
        )

        return cursor.executemany(
            sql,
            parameters
        )

    def executescript(
        self,
        script
    ):

        STATE["blocked_writes"] += 1

        return None

    def commit(self):

        STATE["blocked_writes"] += 1

        return None

    def rollback(self):

        return None

    def close(self):

        return self._connection.close()

    def __enter__(self):

        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb
    ):

        self.close()

        return False

    def __getattr__(self, name):

        return getattr(
            self._connection,
            name
        )


def forensic_connect(
    database,
    *args,
    **kwargs
):

    database = os.path.abspath(
        str(database)
    )

    uri = (
        "file:"
        + database.replace("\\", "/")
        + "?mode=ro"
    )

    connection = _ORIGINAL_CONNECT(
        uri,
        uri=True
    )

    connection.row_factory = sqlite3.Row

    return NeutralizedConnection(
        connection
    )


# =============================================================================
# VALUE SNAPSHOT
# =============================================================================

def snapshot_locals(frame):

    result = {}

    try:

        for name, value in frame.f_locals.items():

            result[name] = {
                "id": object_id(value),
                "type": value_type(value),
                "repr": safe_repr(value),
            }

    except Exception:
        pass

    return result


# =============================================================================
# TRACE
# =============================================================================

def trace_function(
    frame,
    event,
    arg
):

    try:

        filename = os.path.abspath(
            frame.f_code.co_filename
        )

        if filename != os.path.abspath(
            TARGET_FILE
        ):

            return trace_function

        function_name = (
            frame.f_code.co_name
        )

        # ---------------------------------------------------------------------
        # CREATE_OUTCOME
        # ---------------------------------------------------------------------

        if function_name == CREATE_NAME:

            if event == "call":

                STATE["create_calls"] += 1

                STATE["assignment_events"].append(
                    {
                        "event": "create_call",
                        "line": frame.f_lineno,
                    }
                )

                return trace_function

            if event == "line":

                locals_now = frame.f_locals

                # Exact price object
                if "price" in locals_now:

                    price = locals_now["price"]

                    STATE[
                        "price_observations"
                    ].append(
                        {
                            "line": frame.f_lineno,
                            "id": object_id(price),
                            "type": value_type(price),
                            "value": price,
                        }
                    )

                # prices container
                if "prices" in locals_now:

                    prices = locals_now["prices"]

                    STATE[
                        "container_observations"
                    ].append(
                        {
                            "name": "prices",
                            "line": frame.f_lineno,
                            "id": object_id(prices),
                            "type": value_type(prices),
                            "value": prices,
                        }
                    )

                # returns container
                if "returns" in locals_now:

                    returns = locals_now["returns"]

                    STATE[
                        "container_observations"
                    ].append(
                        {
                            "name": "returns",
                            "line": frame.f_lineno,
                            "id": object_id(returns),
                            "type": value_type(returns),
                            "value": returns,
                        }
                    )

                # outcomes container
                if "outcomes" in locals_now:

                    outcomes = locals_now["outcomes"]

                    STATE[
                        "container_observations"
                    ].append(
                        {
                            "name": "outcomes",
                            "line": frame.f_lineno,
                            "id": object_id(outcomes),
                            "type": value_type(outcomes),
                            "value": outcomes,
                        }
                    )

                return trace_function

            if event == "return":

                STATE["create_returns"] += 1

                STATE["return_records"].append(
                    {
                        "number": (
                            STATE["create_returns"]
                        ),
                        "id": object_id(arg),
                        "type": value_type(arg),
                        "value": arg,
                        "locals": snapshot_locals(frame),
                    }
                )

                return trace_function

        # ---------------------------------------------------------------------
        # FIND_FUTURE_PRICE
        # ---------------------------------------------------------------------

        if function_name == FUTURE_NAME:

            if event == "call":

                STATE["future_calls"] += 1

                return trace_function

            if event == "return":

                STATE["future_returns"] += 1

                STATE["future_records"].append(
                    {
                        "number": (
                            STATE["future_returns"]
                        ),
                        "id": object_id(arg),
                        "type": value_type(arg),
                        "value": arg,
                    }
                )

                return trace_function

    except Exception:
        return trace_function

    return trace_function


# =============================================================================
# EXECUTION
# =============================================================================

def execute_runtime():

    print()
    print("=" * 100)
    print("STEP 2 — WRITE-NEUTRALIZED PRODUCTION RUNTIME")
    print("=" * 100)

    print(
        "Production source mutation : NONE"
    )

    print(
        "Production DB writes       : BLOCKED"
    )

    print(
        "SQLite SELECT              : ALLOWED"
    )

    print(
        "SQLite row_factory         : sqlite3.Row"
    )

    print(
        "COMMIT                     : NEUTRALIZED"
    )

    print()

    original_connect = sqlite3.connect
    original_trace = sys.gettrace()

    try:

        sqlite3.connect = forensic_connect

        sys.settrace(
            trace_function
        )

        namespace = runpy.run_path(
            TARGET_FILE,
            run_name=(
                "__arunda_forensic_runtime__"
            )
        )

        main_func = namespace.get(
            "main"
        )

        if not callable(main_func):

            raise RuntimeError(
                "Production main() not found."
            )

        main_func()

    except Exception as exc:

        STATE[
            "runtime_exceptions"
        ] += 1

        print("=" * 100)
        print("PRODUCTION RUNTIME ERROR")
        print("=" * 100)

        print(
            f"{type(exc).__name__}"
            f"({exc!r})"
        )

        print()

        traceback.print_exc()

    finally:

        sys.settrace(
            original_trace
        )

        sqlite3.connect = (
            original_connect
        )


# =============================================================================
# FUTURE PRICE REPORT
# =============================================================================

def report_future_values():

    print()
    print("=" * 100)
    print("STEP 3 — FUTURE PRICE RETURNS")
    print("=" * 100)

    if not STATE["future_records"]:

        print("NONE")

        return

    for item in STATE[
        "future_records"
    ]:

        print(
            f"{item['number']:03d} | "
            f"TYPE={item['type']} | "
            f"VALUE={safe_repr(item['value'])} | "
            f"OBJECT_ID={item['id']}"
        )


# =============================================================================
# IDENTITY LOCALIZATION
# =============================================================================

def report_identity_flow():

    print()
    print("=" * 100)
    print("STEP 4 — OBJECT IDENTITY FLOW")
    print("=" * 100)

    if not STATE["future_records"]:

        print(
            "NO FUTURE PRICE RETURNS"
        )

        return 0

    matches = 0

    for future in STATE[
        "future_records"
    ]:

        future_id = future["id"]
        future_value = future["value"]
        future_number = future["number"]

        for observation in STATE[
            "price_observations"
        ]:

            if (
                observation["id"]
                == future_id
            ):

                matches += 1

                if matches <= 150:

                    print(
                        "PRICE OBJECT MATCH | "
                        f"RETURN={future_number} | "
                        f"LINE={observation['line']} | "
                        f"OBJECT_ID={future_id} | "
                        f"VALUE={safe_repr(future_value)}"
                    )

    print()
    print(
        f"PRICE OBJECT ID MATCHES : "
        f"{matches}"
    )

    return matches


# =============================================================================
# CONTAINER FLOW
# =============================================================================

def report_container_flow():

    print()
    print("=" * 100)
    print("STEP 5 — DICTIONARY / CONTAINER OBJECT FLOW")
    print("=" * 100)

    if not STATE[
        "container_observations"
    ]:

        print("NO CONTAINER OBSERVATIONS")

        return

    printed = set()

    for observation in STATE[
        "container_observations"
    ]:

        name = observation["name"]
        line = observation["line"]
        value = observation["value"]

        if not isinstance(
            value,
            dict
        ):

            continue

        for key, child in value.items():

            child_id = object_id(child)

            for future in STATE[
                "future_records"
            ]:

                same_identity = (
                    child_id
                    == future["id"]
                )

                same_scalar = (
                    not isinstance(
                        child,
                        (dict, list, tuple, set)
                    )
                    and scalar_equal(
                        child,
                        future["value"]
                    )
                )

                if (
                    same_identity
                    or same_scalar
                ):

                    signature = (
                        name,
                        line,
                        repr(key),
                        future["number"],
                    )

                    if signature in printed:
                        continue

                    printed.add(signature)

                    print(
                        "CONTAINER MATCH | "
                        f"CONTAINER={name} | "
                        f"LINE={line} | "
                        f"KEY={safe_repr(key)} | "
                        f"FUTURE_RETURN={future['number']} | "
                        f"CHILD_ID={child_id} | "
                        f"VALUE={safe_repr(child)}"
                    )


# =============================================================================
# RETURN OBJECT IDENTITY
# =============================================================================

def report_return_identity():

    print()
    print("=" * 100)
    print("STEP 6 — FINAL RETURN OBJECT IDENTITY")
    print("=" * 100)

    if not STATE[
        "return_records"
    ]:

        print(
            "NO CREATE_OUTCOME RETURNS"
        )

        return 0

    matches = 0

    for record in STATE[
        "return_records"
    ]:

        returned = record["value"]

        for future in STATE[
            "future_records"
        ]:

            target = future["value"]

            # -------------------------------------------------------------
            # Direct identity
            # -------------------------------------------------------------

            if (
                returned is target
            ):

                matches += 1

                print(
                    "FINAL RETURN IDENTITY MATCH | "
                    f"CREATE_RETURN={record['number']} | "
                    f"FUTURE_RETURN={future['number']} | "
                    f"OBJECT_ID={object_id(target)}"
                )

                continue

            # -------------------------------------------------------------
            # Recursive structural search
            # -------------------------------------------------------------

            paths = locate_value(
                returned,
                target
            )

            for path in paths:

                matches += 1

                print(
                    "FINAL RETURN PATH MATCH | "
                    f"CREATE_RETURN={record['number']} | "
                    f"FUTURE_RETURN={future['number']} | "
                    f"PATH={path} | "
                    f"VALUE={safe_repr(target)}"
                )

    print()

    print(
        f"FINAL RETURN MATCHES : {matches}"
    )

    return matches


# =============================================================================
# RECURSIVE PATH LOCATOR
# =============================================================================

def locate_value(
    root,
    target,
    path="ROOT",
    depth=0,
    seen=None
):

    if seen is None:
        seen = set()

    if depth > 20:
        return []

    try:

        identity = id(root)

        if identity in seen:
            return []

        seen.add(identity)

    except Exception:
        pass

    paths = []

    # Exact identity.
    if root is target:

        paths.append(
            path
        )

    # Scalar equality.
    elif (
        not isinstance(
            root,
            (dict, list, tuple, set)
        )
        and not isinstance(
            target,
            (dict, list, tuple, set)
        )
    ):

        try:

            if root == target:

                paths.append(
                    path
                )

        except Exception:
            pass

    # Dictionary.
    if isinstance(
        root,
        dict
    ):

        for key, child in root.items():

            child_path = (
                f"{path}"
                f"[{safe_repr(key)}]"
            )

            paths.extend(
                locate_value(
                    child,
                    target,
                    child_path,
                    depth + 1,
                    seen
                )
            )

    # List / tuple / set.
    elif isinstance(
        root,
        (list, tuple, set)
    ):

        try:

            iterable = enumerate(root)

        except Exception:

            iterable = []

        for index, child in iterable:

            child_path = (
                f"{path}"
                f"[{index}]"
            )

            paths.extend(
                locate_value(
                    child,
                    target,
                    child_path,
                    depth + 1,
                    seen
                )
            )

    return paths


# =============================================================================
# SOURCE INTEGRITY
# =============================================================================

def verify_source(
    original_source
):

    try:

        with open(
            TARGET_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            current_source = f.read()

        STATE[
            "source_modified"
        ] = (
            current_source
            != original_source
        )

    except Exception:

        STATE[
            "source_modified"
        ] = True


# =============================================================================
# FINAL SUMMARY
# =============================================================================

def final_summary(
    identity_matches,
    final_matches
):

    print()
    print("=" * 100)
    print("STEP 7 — FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(
        f"CREATE_OUTCOME CALLS        : "
        f"{STATE['create_calls']}"
    )

    print(
        f"FIND_FUTURE_PRICE CALLS     : "
        f"{STATE['future_calls']}"
    )

    print(
        f"FIND_FUTURE_PRICE RETURNS   : "
        f"{STATE['future_returns']}"
    )

    print(
        f"CREATE_OUTCOME RETURNS      : "
        f"{STATE['create_returns']}"
    )

    print(
        f"PRICE OBJECT ID MATCHES     : "
        f"{identity_matches}"
    )

    print(
        f"FINAL RETURN MATCHES        : "
        f"{final_matches}"
    )

    print(
        f"RUNTIME EXCEPTIONS          : "
        f"{STATE['runtime_exceptions']}"
    )

    print(
        f"BLOCKED WRITE OPERATIONS    : "
        f"{STATE['blocked_writes']}"
    )

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("-" * 100)

    if STATE[
        "future_returns"
    ] == 0:

        status = (
            "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
        )

        meaning = (
            "The production runtime did not "
            "reach find_future_price()."
        )

        frontier = (
            "Resolve the production runtime boundary."
        )

    elif identity_matches == 0:

        status = (
            "FIND_FUTURE_PRICE_PRICE_OBJECT_NOT_FOLLOWED"
        )

        meaning = (
            "The genuine return was captured, "
            "but object identity was not observed "
            "inside create_outcome().price."
        )

        frontier = (
            "Trace frame assignment at the exact "
            "CALL/LINE boundary."
        )

    elif final_matches == 0:

        status = (
            "FIND_FUTURE_PRICE_FINAL_RETURN_PACKING_UNRESOLVED"
        )

        meaning = (
            "The future-price object was followed "
            "into the local price variable, but "
            "its path into the final return structure "
            "was not established."
        )

        frontier = (
            "Trace dictionary/object construction "
            "and return packing at instruction boundary."
        )

    else:

        status = (
            "FIND_FUTURE_PRICE_FINAL_RETURN_PACKING_LOCALIZED"
        )

        meaning = (
            "The genuine future-price return was "
            "followed by object identity/path into "
            "the final returned structure."
        )

        frontier = (
            "Compare exact preservation versus "
            "any transformation across invocations."
        )

    print(
        f"STATUS                      : {status}"
    )

    print(
        f"MEANING                     : {meaning}"
    )

    print(
        f"NEXT FRONTIER               : {frontier}"
    )

    print()

    print(
        "DATABASE_WRITES             : NONE"
    )

    print(
        "ENGINE_MODIFIED             : NONE"
    )

    print(
        "PRODUCTION_SOURCE_MODIFIED  : "
        f"{'YES' if STATE['source_modified'] else 'NONE'}"
    )

    print(
        "INSERT                      : NONE"
    )

    print(
        "UPDATE                      : NONE"
    )

    print(
        "DELETE                      : NONE"
    )

    print(
        "ALTER                       : NONE"
    )

    print(
        "CREATE                      : NONE"
    )

    print(
        "DROP                        : NONE"
    )

    print(
        "COMMIT                      : NONE"
    )

    print("=" * 100)


# =============================================================================
# MAIN
# =============================================================================

def main():

    started = time.perf_counter()

    original_source = (
        static_resolution()
    )

    execute_runtime()

    report_future_values()

    identity_matches = (
        report_identity_flow()
    )

    report_container_flow()

    final_matches = (
        report_return_identity()
    )

    verify_source(
        original_source
    )

    final_summary(
        identity_matches,
        final_matches
    )

    elapsed = (
        time.perf_counter()
        - started
    )

    print("=" * 100)

    print(
        f"ELAPSED SECONDS              : "
        f"{elapsed:.3f}"
    )

    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":

    main()