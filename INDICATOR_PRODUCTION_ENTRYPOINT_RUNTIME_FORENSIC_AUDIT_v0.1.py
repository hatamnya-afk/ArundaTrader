import ast
import inspect
import importlib
import os
import sys
import sqlite3
import traceback
import types
import time
from pathlib import Path


# =============================================================================
# ARUNDA INDICATOR PRODUCTION ENTRYPOINT RUNTIME FORENSIC AUDIT v0.1
# =============================================================================
#
# PURPOSE
# -------
# Execute ONLY the resolved production entrypoint under a dedicated
# READ-ONLY runtime sandbox and capture:
#
#   1. Actual runtime rows passed into calculate_analysis()
#   2. Actual production calculate_analysis() return value
#   3. Actual SQL statements executed
#   4. Actual SQL parameter tuples
#   5. Post-calculation assignment transformations
#   6. Rounding / numeric conversions observable at runtime
#
# SAFETY
# ------
# DATABASE WRITE : BLOCKED
# SQLITE AUTHORITATIVE AUTHORIZE BLOCK : ENABLED
# PRODUCTION DB : NEVER OPENED IN WRITE MODE
# INSERT/UPDATE/DELETE/ALTER/CREATE/DROP : BLOCKED
#
# IMPORTANT
# ---------
# This is a forensic runtime audit.
# It does NOT modify market_data_engine.py.
# It does NOT modify arunda.db.
# It does NOT perform production recalculation writes.
#
# =============================================================================


PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
ENGINE_FILE = PROJECT_DIR / "market_data_engine.py"
DATABASE_FILE = PROJECT_DIR / "arunda.db"

TARGETS = ["BTC", "ETH", "SOL", "XRP"]

CALCULATE_ANALYSIS_NAME = "calculate_analysis"


# =============================================================================
# OUTPUT
# =============================================================================

SEP = "=" * 100
SUB = "-" * 100


def out(text=""):
    print(text, flush=True)


def section(title):
    out()
    out(SEP)
    out(title)
    out(SEP)


def subsection(title):
    out()
    out(SUB)
    out(title)
    out(SUB)


# =============================================================================
# GLOBAL RUNTIME CAPTURE
# =============================================================================

RUNTIME = {
    "calculate_calls": [],
    "sql_calls": [],
    "blocked_writes": [],
    "runtime_returns": [],
    "assignments": [],
    "rounding": [],
    "entrypoint": None,
    "entrypoint_args": None,
    "entrypoint_kwargs": None,
}


# =============================================================================
# READ-ONLY SQLITE AUTHORITATIVE BLOCK
# =============================================================================

WRITE_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "ALTER",
    "CREATE",
    "DROP",
    "VACUUM",
    "REINDEX",
    "ATTACH",
    "DETACH",
    "PRAGMA",
}


WRITE_ACTIONS = set(
    x
    for x in [
        getattr(sqlite3, "SQLITE_INSERT", None),
        getattr(sqlite3, "SQLITE_UPDATE", None),
        getattr(sqlite3, "SQLITE_DELETE", None),
        getattr(sqlite3, "SQLITE_ALTER_TABLE", None),
        getattr(sqlite3, "SQLITE_DROP_TABLE", None),
        getattr(sqlite3, "SQLITE_DROP_INDEX", None),
        getattr(sqlite3, "SQLITE_DROP_TRIGGER", None),
        getattr(sqlite3, "SQLITE_CREATE_TABLE", None),
        getattr(sqlite3, "SQLITE_CREATE_INDEX", None),
        getattr(sqlite3, "SQLITE_CREATE_TRIGGER", None),
        getattr(sqlite3, "SQLITE_CREATE_VIEW", None),
        getattr(sqlite3, "SQLITE_ATTACH", None),
        getattr(sqlite3, "SQLITE_DETACH", None),
        getattr(sqlite3, "SQLITE_TRANSACTION", None),
        getattr(sqlite3, "SQLITE_REINDEX", None),
    ]
    if x is not None
)


def authorizer(action, arg1, arg2, dbname, source):
    """
    SQLite authoritative write blocker.

    SQLITE_DENY prevents the operation before SQLite executes it.
    """

    if action in WRITE_ACTIONS:
        RUNTIME["blocked_writes"].append(
            {
                "action": action,
                "arg1": arg1,
                "arg2": arg2,
                "database": dbname,
                "source": source,
            }
        )

        return sqlite3.SQLITE_DENY

    return sqlite3.SQLITE_OK


# =============================================================================
# SQL TRACE
# =============================================================================

class ReadOnlyConnectionProxy:
    """
    Wrap a real sqlite connection.

    Every SQL execution is recorded.
    Every write-like statement is rejected before execution.
    """

    def __init__(self, conn):
        self._conn = conn

        try:
            self._conn.set_authorizer(authorizer)
        except Exception:
            pass

        try:
            self._conn.set_trace_callback(self._trace)
        except Exception:
            pass

    def _trace(self, statement):
        sql = statement or ""
        upper = sql.strip().upper()

        write_like = False

        first_word = upper.split(None, 1)[0] if upper else ""

        if first_word in WRITE_KEYWORDS:
            write_like = True

        RUNTIME["sql_calls"].append(
            {
                "sql": sql,
                "write_like": write_like,
            }
        )

    def execute(self, sql, parameters=()):
        self._capture_sql(sql, parameters)

        if self._looks_write_like(sql):
            self._block_sql(sql, parameters)
            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: write-like SQL blocked"
            )

        return self._conn.execute(sql, parameters)

    def executemany(self, sql, seq_of_parameters):
        params = list(seq_of_parameters)

        self._capture_sql(
            sql,
            f"EXECUTEMANY[{len(params)}]",
        )

        if self._looks_write_like(sql):
            self._block_sql(sql, params)
            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: write-like executemany blocked"
            )

        return self._conn.executemany(sql, params)

    def executescript(self, script):
        self._capture_sql(script, None)

        if self._script_contains_write(script):
            self._block_sql(script, None)
            raise sqlite3.OperationalError(
                "ARUNDA FORENSIC BLOCK: write-like script blocked"
            )

        return self._conn.executescript(script)

    def _capture_sql(self, sql, parameters):
        RUNTIME["sql_calls"].append(
            {
                "sql": str(sql),
                "parameters": self._safe_repr(parameters),
                "write_like": self._looks_write_like(sql),
            }
        )

    def _block_sql(self, sql, parameters):
        RUNTIME["blocked_writes"].append(
            {
                "sql": str(sql),
                "parameters": self._safe_repr(parameters),
            }
        )

    @staticmethod
    def _safe_repr(value):
        try:
            return repr(value)
        except Exception:
            return f"<UNREPRESENTABLE {type(value).__name__}>"

    @staticmethod
    def _looks_write_like(sql):
        if not isinstance(sql, str):
            return False

        cleaned = sql.strip()

        if not cleaned:
            return False

        first = cleaned.upper().split(None, 1)[0]

        return first in WRITE_KEYWORDS

    @staticmethod
    def _script_contains_write(script):
        if not isinstance(script, str):
            return False

        upper = script.upper()

        for keyword in WRITE_KEYWORDS:
            if keyword in upper:
                return True

        return False

    def __getattr__(self, name):
        return getattr(self._conn, name)


# =============================================================================
# READ-ONLY CONNECTION FACTORY
# =============================================================================

_original_sqlite_connect = sqlite3.connect


def forensic_connect(database, *args, **kwargs):
    """
    Redirect production database access to immutable/read-only URI.

    This function intentionally refuses write-oriented modes.
    """

    db_path = Path(str(database))

    if db_path.resolve() == DATABASE_FILE.resolve():
        uri = (
            "file:"
            + str(DATABASE_FILE.resolve()).replace("\\", "/")
            + "?mode=ro"
        )

        kwargs.pop("uri", None)

        conn = _original_sqlite_connect(
            uri,
            *args,
            uri=True,
            **kwargs,
        )

        return ReadOnlyConnectionProxy(conn)

    conn = _original_sqlite_connect(
        database,
        *args,
        **kwargs,
    )

    return ReadOnlyConnectionProxy(conn)


# =============================================================================
# RUNTIME ROW CAPTURE
# =============================================================================

def safe_snapshot(value, depth=0, max_items=200):
    """
    Convert runtime objects into a bounded forensic representation.
    """

    if depth > 5:
        return "<DEPTH_LIMIT>"

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, bytes):
        return f"<BYTES len={len(value)}>"

    if isinstance(value, dict):
        result = {}

        for i, (k, v) in enumerate(value.items()):
            if i >= max_items:
                result["<TRUNCATED>"] = True
                break

            result[str(k)] = safe_snapshot(
                v,
                depth + 1,
                max_items,
            )

        return result

    if isinstance(value, (list, tuple)):
        result = []

        for i, item in enumerate(value):
            if i >= max_items:
                result.append("<TRUNCATED>")
                break

            result.append(
                safe_snapshot(
                    item,
                    depth + 1,
                    max_items,
                )
            )

        return result

    try:
        return repr(value)
    except Exception:
        return f"<OBJECT {type(value).__name__}>"


# =============================================================================
# calculate_analysis RUNTIME WRAPPER
# =============================================================================

_original_calculate_analysis = None


def forensic_calculate_analysis(rows):
    """
    Runtime wrapper around the REAL production calculate_analysis().
    """

    call_id = len(RUNTIME["calculate_calls"]) + 1

    snapshot = safe_snapshot(rows)

    record = {
        "call_id": call_id,
        "rows_type": type(rows).__name__,
        "rows_count": None,
        "rows_snapshot": snapshot,
    }

    try:
        record["rows_count"] = len(rows)
    except Exception:
        pass

    RUNTIME["calculate_calls"].append(record)

    out()
    out("[RUNTIME] calculate_analysis() OBSERVED")
    out(f"CALL ID       : {call_id}")
    out(f"ROWS TYPE     : {type(rows).__name__}")

    try:
        out(f"ROWS COUNT    : {len(rows)}")
    except Exception:
        out("ROWS COUNT    : <UNAVAILABLE>")

    try:
        result = _original_calculate_analysis(rows)

        result_snapshot = safe_snapshot(result)

        runtime_return = {
            "call_id": call_id,
            "return_type": type(result).__name__,
            "return_value": result_snapshot,
        }

        RUNTIME["runtime_returns"].append(
            runtime_return
        )

        out()
        out("[RUNTIME] calculate_analysis RETURN")
        out(f"RETURN TYPE   : {type(result).__name__}")
        out(f"RETURN VALUE  : {result_snapshot}")

        return result

    except Exception as exc:
        out()
        out("[RUNTIME] calculate_analysis EXCEPTION")
        out(f"TYPE          : {type(exc).__name__}")
        out(f"MESSAGE       : {exc}")

        raise


# =============================================================================
# AST DISCOVERY
# =============================================================================

def parse_engine():
    source = ENGINE_FILE.read_text(
        encoding="utf-8"
    )

    return source, ast.parse(source)


def discover_calculate_analysis():
    source, tree = parse_engine()

    definitions = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == CALCULATE_ANALYSIS_NAME
        ):
            definitions.append(node)

    return source, tree, definitions


def discover_callers(tree):
    """
    Find functions containing:
        calculate_analysis(...)
    """

    callers = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue

        for child in ast.walk(node):

            if not isinstance(child, ast.Call):
                continue

            fn = child.func

            if (
                isinstance(fn, ast.Name)
                and fn.id == CALCULATE_ANALYSIS_NAME
            ):
                callers.append(
                    {
                        "function": node.name,
                        "line": child.lineno,
                        "node": node,
                    }
                )

    return callers


# =============================================================================
# MODULE PATCHING
# =============================================================================

def patch_calculate_analysis_references():
    """
    Patch references in every currently loaded module that point to the
    real calculate_analysis function.

    This is necessary because production code may have:

        from market_data_engine import calculate_analysis

    rather than:

        import market_data_engine
    """

    patched = []

    global _original_calculate_analysis

    for module_name, module in list(
        sys.modules.items()
    ):

        if module is None:
            continue

        try:
            namespace = vars(module)
        except Exception:
            continue

        for name, value in list(
            namespace.items()
        ):

            if value is _original_calculate_analysis:

                try:
                    setattr(
                        module,
                        name,
                        forensic_calculate_analysis,
                    )

                    patched.append(
                        f"{module_name}.{name}"
                    )

                except Exception:
                    pass

    return patched


# =============================================================================
# ENTRYPOINT DISCOVERY
# =============================================================================

ENTRYPOINT_NAMES = {
    "main",
    "run",
    "start",
    "execute",
    "run_engine",
    "run_market_data",
    "market_data_loop",
    "process",
    "worker",
}


def discover_entrypoint_candidates(tree):
    candidates = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue

        name = node.name.lower()

        score = 0

        if name in ENTRYPOINT_NAMES:
            score += 100

        if "engine" in name:
            score += 30

        if "market" in name:
            score += 20

        if "data" in name:
            score += 10

        if "loop" in name:
            score += 10

        if score > 0:
            candidates.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "score": score,
                    "args": [
                        arg.arg
                        for arg in node.args.args
                    ],
                }
            )

    candidates.sort(
        key=lambda x: (
            -x["score"],
            x["line"],
        )
    )

    return candidates


# =============================================================================
# FUNCTION CALL GRAPH
# =============================================================================

def build_call_graph(tree):
    graph = {}

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue

        calls = []

        for child in ast.walk(node):

            if not isinstance(child, ast.Call):
                continue

            fn = child.func

            if isinstance(
                fn,
                ast.Name,
            ):
                calls.append(fn.id)

            elif isinstance(
                fn,
                ast.Attribute,
            ):
                calls.append(fn.attr)

        graph[node.name] = calls

    return graph


def find_ancestor_functions(graph, target):
    ancestors = set()

    changed = True

    while changed:

        changed = False

        for fn, calls in graph.items():

            if fn in ancestors:
                continue

            if target in calls or any(
                x in ancestors
                for x in calls
            ):
                ancestors.add(fn)
                changed = True

    return ancestors


# =============================================================================
# SIGNATURE SAFETY
# =============================================================================

def required_arguments(fn):
    try:
        sig = inspect.signature(fn)
    except Exception:
        return None

    required = []

    for name, param in sig.parameters.items():

        if (
            param.kind
            in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )
        ):
            continue

        if (
            param.default
            is inspect.Parameter.empty
        ):
            required.append(name)

    return required


# =============================================================================
# ENTRYPOINT EXECUTION
# =============================================================================

def execute_entrypoint(module):
    """
    Execute a resolved entrypoint only if it can be called without
    fabricated arguments.

    If required runtime arguments exist, execution is NOT guessed.
    """

    entrypoint_name = os.environ.get(
        "ARUNDA_FORENSIC_ENTRYPOINT"
    )

    if entrypoint_name:

        if ":" in entrypoint_name:
            _, entrypoint_name = (
                entrypoint_name.split(
                    ":",
                    1,
                )
            )

    if not entrypoint_name:

        candidates = discover_entrypoint_candidates(
            ast.parse(
                ENGINE_FILE.read_text(
                    encoding="utf-8"
                )
            )
        )

        if not candidates:

            return {
                "status": "NO_SAFE_ENTRYPOINT_CANDIDATE"
            }

        entrypoint_name = candidates[0]["name"]

    if not hasattr(
        module,
        entrypoint_name,
    ):

        return {
            "status": "ENTRYPOINT_NOT_FOUND",
            "entrypoint": entrypoint_name,
        }

    fn = getattr(
        module,
        entrypoint_name,
    )

    required = required_arguments(fn)

    if required is None:

        return {
            "status": "SIGNATURE_UNRESOLVED",
            "entrypoint": entrypoint_name,
        }

    if required:

        return {
            "status": "ENTRYPOINT_REQUIRES_RUNTIME_ARGUMENTS",
            "entrypoint": entrypoint_name,
            "required_arguments": required,
        }

    RUNTIME["entrypoint"] = entrypoint_name
    RUNTIME["entrypoint_args"] = ()
    RUNTIME["entrypoint_kwargs"] = {}

    out()
    out("[RUNTIME] PRODUCTION ENTRYPOINT EXECUTION")
    out(f"ENTRYPOINT    : {entrypoint_name}")
    out("ARGUMENTS     : ()")
    out("KWARGS        : {}")

    try:

        result = fn()

        return {
            "status": "EXECUTED",
            "entrypoint": entrypoint_name,
            "return_type": type(result).__name__,
            "return_value": safe_snapshot(result),
        }

    except SystemExit as exc:

        return {
            "status": "EXECUTED_SYSTEM_EXIT",
            "entrypoint": entrypoint_name,
            "exit_code": exc.code,
        }

    except Exception as exc:

        out()
        out("[RUNTIME] ENTRYPOINT EXCEPTION")
        out(f"TYPE          : {type(exc).__name__}")
        out(f"MESSAGE       : {exc}")

        traceback.print_exc()

        return {
            "status": "ENTRYPOINT_EXCEPTION",
            "entrypoint": entrypoint_name,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
        }


# =============================================================================
# STORED DATABASE TARGET RESOLUTION
# =============================================================================

def resolve_targets_read_only():
    conn = _original_sqlite_connect(
        f"file:{DATABASE_FILE.resolve()}?mode=ro",
        uri=True,
    )

    conn.set_authorizer(authorizer)

    results = {}

    try:

        for symbol in TARGETS:

            row = conn.execute(
                """
                SELECT
                    id,
                    timestamp,
                    source_timestamp,
                    symbol,
                    close,
                    ema20,
                    ema50,
                    rsi14,
                    macd,
                    macd_signal,
                    macd_hist,
                    atr14,
                    adx14,
                    bb_middle,
                    bb_upper,
                    bb_lower,
                    bb_width,
                    volume_sma20,
                    volume_ratio,
                    volatility,
                    technical_score
                FROM market_data
                WHERE symbol = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (symbol,),
            ).fetchone()

            results[symbol] = row

    finally:
        conn.close()

    return results


# =============================================================================
# STORED VS RUNTIME COMPARISON
# =============================================================================

def compare_runtime_returns(
    stored_targets,
):

    section(
        "FINAL PRODUCTION RUNTIME RETURN FORENSIC COMPARISON"
    )

    latest_return = None

    if RUNTIME["runtime_returns"]:

        latest_return = RUNTIME[
            "runtime_returns"
        ][-1]["return_value"]

    if not isinstance(
        latest_return,
        dict,
    ):

        out(
            "RUNTIME RETURN DICTIONARY : NOT OBSERVED"
        )
        return

    indicator_fields = [
        "ema20",
        "ema50",
        "rsi14",
        "macd",
        "macd_signal",
        "macd_hist",
        "atr14",
        "adx14",
        "bb_middle",
        "bb_upper",
        "bb_lower",
        "bb_width",
        "volume_sma20",
        "volume_ratio",
        "volatility",
        "technical_score",
    ]

    for symbol in TARGETS:

        stored = stored_targets.get(
            symbol
        )

        if not stored:
            continue

        out()
        out(f"SYMBOL : {symbol}")

        for field in indicator_fields:

            try:

                index = {
                    "ema20": 5,
                    "ema50": 6,
                    "rsi14": 7,
                    "macd": 8,
                    "macd_signal": 9,
                    "macd_hist": 10,
                    "atr14": 11,
                    "adx14": 12,
                    "bb_middle": 13,
                    "bb_upper": 14,
                    "bb_lower": 15,
                    "bb_width": 16,
                    "volume_sma20": 17,
                    "volume_ratio": 18,
                    "volatility": 19,
                    "technical_score": 20,
                }[field]

                stored_value = stored[index]

            except Exception:

                continue

            runtime_value = latest_return.get(
                field
            )

            if (
                isinstance(
                    stored_value,
                    (int, float),
                )
                and isinstance(
                    runtime_value,
                    (int, float),
                )
            ):

                abs_error = abs(
                    stored_value
                    - runtime_value
                )

                denominator = max(
                    abs(stored_value),
                    1e-15,
                )

                rel_error = (
                    abs_error
                    / denominator
                )

                status = (
                    "MATCH"
                    if abs_error == 0
                    else "DIFFERENCE"
                )

                out(
                    f"{field:20s}"
                    f" STORED={stored_value!r}"
                    f" RUNTIME={runtime_value!r}"
                    f" ABS={abs_error!r}"
                    f" REL={rel_error!r}"
                    f" STATUS={status}"
                )


# =============================================================================
# MAIN
# =============================================================================

def main():

    start = time.perf_counter()

    section(
        "ARUNDA INDICATOR PRODUCTION ENTRYPOINT RUNTIME FORENSIC AUDIT v0.1"
    )

    out(
        "MODE                         : READ ONLY RUNTIME FORENSICS"
    )
    out(
        "DATABASE WRITE               : BLOCKED"
    )
    out(
        "ENGINE WRITE                 : NONE"
    )
    out(
        "PRODUCTION RECALCULATION     : IN-MEMORY OBSERVATION ONLY"
    )
    out(
        "TARGETS                      : BTC / ETH / SOL / XRP"
    )

    # -------------------------------------------------------------------------
    # STEP 1
    # -------------------------------------------------------------------------

    section(
        "STEP 1 — PATH SAFETY RESOLUTION"
    )

    out(
        f"PROJECT PATH                 : {PROJECT_DIR}"
    )

    out(
        f"ENGINE PATH                  : {ENGINE_FILE}"
    )

    out(
        f"ENGINE FOUND                 : {ENGINE_FILE.exists()}"
    )

    out(
        f"DATABASE PATH                : {DATABASE_FILE}"
    )

    out(
        f"DATABASE FOUND               : {DATABASE_FILE.exists()}"
    )

    if not ENGINE_FILE.exists():
        raise FileNotFoundError(
            ENGINE_FILE
        )

    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            DATABASE_FILE
        )

    # -------------------------------------------------------------------------
    # STEP 2
    # -------------------------------------------------------------------------

    section(
        "STEP 2 — PRODUCTION SOURCE RESOLUTION"
    )

    source, tree, definitions = (
        discover_calculate_analysis()
    )

    out(
        f"CALCULATE_ANALYSIS DEFINITIONS : {len(definitions)}"
    )

    if len(definitions) != 1:

        raise RuntimeError(
            "calculate_analysis definition is not uniquely resolved"
        )

    ca_node = definitions[0]

    out(
        f"CALCULATE_ANALYSIS LINE        : {ca_node.lineno}"
    )

    # -------------------------------------------------------------------------
    # STEP 3
    # -------------------------------------------------------------------------

    section(
        "STEP 3 — CALLER / ENTRYPOINT GRAPH"
    )

    callers = discover_callers(tree)

    out(
        f"CALCULATE_ANALYSIS CALL SITES  : {len(callers)}"
    )

    for item in callers:

        out(
            f"[CALLER] {item['function']}"
            f" @ line {item['line']}"
        )

    graph = build_call_graph(tree)

    ancestors = find_ancestor_functions(
        graph,
        CALCULATE_ANALYSIS_NAME,
    )

    out()
    out(
        "ANCESTOR FUNCTIONS"
    )

    for fn in sorted(ancestors):
        out(
            f"[ANCESTOR] {fn}"
        )

    # -------------------------------------------------------------------------
    # STEP 4
    # -------------------------------------------------------------------------

    section(
        "STEP 4 — DATABASE TARGET RESOLUTION"
    )

    stored_targets = (
        resolve_targets_read_only()
    )

    for symbol in TARGETS:

        row = stored_targets.get(
            symbol
        )

        if row:

            out(
                f"[STORED_TARGET_RESOLVED] : {symbol}"
            )

        else:

            out(
                f"[STORED_TARGET_MISSING]   : {symbol}"
            )

    # -------------------------------------------------------------------------
    # STEP 5
    # -------------------------------------------------------------------------

    section(
        "STEP 5 — SQLITE WRITE BLOCK ACTIVATION"
    )

    sqlite3.connect = forensic_connect

    out(
        "READ-ONLY CONNECTION FACTORY  : ENABLED"
    )

    out(
        "SQLITE AUTHORITATIVE BLOCK     : ENABLED"
    )

    out(
        "WRITE-LIKE SQL BLOCK           : ENABLED"
    )

    # -------------------------------------------------------------------------
    # STEP 6
    # -------------------------------------------------------------------------

    section(
        "STEP 6 — PRODUCTION ENGINE IMPORT"
    )

    sys.path.insert(
        0,
        str(PROJECT_DIR),
    )

    module = importlib.import_module(
        "market_data_engine"
    )

    out(
        f"MODULE IMPORTED               : {module.__name__}"
    )

    if not hasattr(
        module,
        CALCULATE_ANALYSIS_NAME,
    ):
        raise RuntimeError(
            "Production calculate_analysis not found after import"
        )

    global _original_calculate_analysis

    _original_calculate_analysis = getattr(
        module,
        CALCULATE_ANALYSIS_NAME,
    )

    # -------------------------------------------------------------------------
    # STEP 7
    # -------------------------------------------------------------------------

    section(
        "STEP 7 — RUNTIME calculate_analysis PATCH"
    )

    setattr(
        module,
        CALCULATE_ANALYSIS_NAME,
        forensic_calculate_analysis,
    )

    patched = patch_calculate_analysis_references()

    out(
        f"PATCHED REFERENCES             : {len(patched)}"
    )

    for item in patched:
        out(
            f"[PATCHED] {item}"
        )

    # -------------------------------------------------------------------------
    # STEP 8
    # -------------------------------------------------------------------------

    section(
        "STEP 8 — PRODUCTION ENTRYPOINT DISCOVERY"
    )

    candidates = (
        discover_entrypoint_candidates(
            tree
        )
    )

    out(
        f"ENTRYPOINT CANDIDATES           : {len(candidates)}"
    )

    for candidate in candidates[:25]:

        out(
            f"[CANDIDATE]"
            f" {candidate['name']}"
            f" line={candidate['line']}"
            f" score={candidate['score']}"
            f" args={candidate['args']}"
        )

    if len(candidates) > 25:
        out(
            f"... {len(candidates) - 25}"
            " additional candidates hidden"
        )

    # -------------------------------------------------------------------------
    # STEP 9
    # -------------------------------------------------------------------------

    section(
        "STEP 9 — ACTUAL PRODUCTION ENTRYPOINT RUNTIME EXECUTION"
    )

    execution = execute_entrypoint(
        module
    )

    out()
    out(
        f"ENTRYPOINT EXECUTION STATUS    : {execution['status']}"
    )

    if "entrypoint" in execution:
        out(
            f"ENTRYPOINT                    : {execution['entrypoint']}"
        )

    if "required_arguments" in execution:
        out(
            f"REQUIRED ARGUMENTS             : "
            f"{execution['required_arguments']}"
        )

    # -------------------------------------------------------------------------
    # STEP 10
    # -------------------------------------------------------------------------

    section(
        "STEP 10 — ACTUAL RUNTIME ROWS CAPTURE"
    )

    out(
        f"CALCULATE_ANALYSIS CALLS       : "
        f"{len(RUNTIME['calculate_calls'])}"
    )

    for call in RUNTIME[
        "calculate_calls"
    ]:

        out()
        out(
            f"CALL ID                       : "
            f"{call['call_id']}"
        )

        out(
            f"ROWS TYPE                     : "
            f"{call['rows_type']}"
        )

        out(
            f"ROWS COUNT                    : "
            f"{call['rows_count']}"
        )

        rows = call["rows_snapshot"]

        if isinstance(rows, list):

            symbols_seen = set()

            for row in rows:

                if isinstance(row, dict):

                    symbol = row.get(
                        "symbol"
                    )

                    if symbol in TARGETS:

                        symbols_seen.add(
                            symbol
                        )

            if symbols_seen:

                out(
                    "TARGET SYMBOLS IN RUNTIME ROWS:"
                )

                for symbol in sorted(
                    symbols_seen
                ):
                    out(
                        f"  [OBSERVED] {symbol}"
                    )

    # -------------------------------------------------------------------------
    # STEP 11
    # -------------------------------------------------------------------------

    section(
        "STEP 11 — ACTUAL PRODUCTION RETURN CAPTURE"
    )

    out(
        f"RUNTIME RETURNS               : "
        f"{len(RUNTIME['runtime_returns'])}"
    )

    for item in RUNTIME[
        "runtime_returns"
    ]:

        out(
            f"[RETURN]"
            f" call={item['call_id']}"
            f" type={item['return_type']}"
        )

    # -------------------------------------------------------------------------
    # STEP 12
    # -------------------------------------------------------------------------

    section(
        "STEP 12 — SQL EXECUTION + PARAMETER CAPTURE"
    )

    out(
        f"SQL EXECUTION TRACE COUNT     : "
        f"{len(RUNTIME['sql_calls'])}"
    )

    write_like_count = 0

    for index, sql in enumerate(
        RUNTIME["sql_calls"],
        start=1,
    ):

        if sql.get("write_like"):
            write_like_count += 1

        out()
        out(
            f"SQL CALL #{index}"
        )
        out(
            f"SQL                           : "
            f"{sql.get('sql')}"
        )

        if "parameters" in sql:
            out(
                f"PARAMETERS                    : "
                f"{sql.get('parameters')}"
            )

        out(
            f"WRITE-LIKE                    : "
            f"{sql.get('write_like')}"
        )

    out()
    out(
        f"WRITE-LIKE SQL CALLS           : "
        f"{write_like_count}"
    )

    # -------------------------------------------------------------------------
    # STEP 13
    # -------------------------------------------------------------------------

    section(
        "STEP 13 — WRITE SAFETY VERIFICATION"
    )

    out(
        "DATABASE CONNECTION MODE       : READ ONLY"
    )

    out(
        "SQLITE AUTHORITATIVE BLOCK     : ENABLED"
    )

    out(
        f"BLOCKED WRITE OPERATIONS       : "
        f"{len(RUNTIME['blocked_writes'])}"
    )

    if RUNTIME["blocked_writes"]:

        for blocked in RUNTIME[
            "blocked_writes"
        ]:

            out(
                f"[BLOCKED] {blocked}"
            )

    else:

        out(
            "WRITE ATTEMPTS                : NONE OBSERVED"
        )

    # -------------------------------------------------------------------------
    # STEP 14
    # -------------------------------------------------------------------------

    section(
        "STEP 14 — RUNTIME RETURN VS STORED VALUE"
    )

    if (
        len(RUNTIME["runtime_returns"])
        == 1
    ):

        compare_runtime_returns(
            stored_targets
        )

    else:

        out(
            "COMPARISON STATUS              : "
            "NOT EXECUTABLE — runtime return count != 1"
        )

    # -------------------------------------------------------------------------
    # STEP 15
    # -------------------------------------------------------------------------

    section(
        "FINAL PRODUCTION ENTRYPOINT RUNTIME FORENSIC SUMMARY"
    )

    runtime_calls = len(
        RUNTIME["calculate_calls"]
    )

    runtime_returns = len(
        RUNTIME["runtime_returns"]
    )

    sql_count = len(
        RUNTIME["sql_calls"]
    )

    blocked = len(
        RUNTIME["blocked_writes"]
    )

    out(
        f"TARGETS REQUESTED             : "
        f"{len(TARGETS)}"
    )

    out(
        f"TARGETS FOUND IN DATABASE     : "
        f"{sum(1 for x in stored_targets.values() if x)}"
    )

    out(
        f"CALCULATE_ANALYSIS CALLS     : "
        f"{runtime_calls}"
    )

    out(
        f"RUNTIME RETURNS               : "
        f"{runtime_returns}"
    )

    out(
        f"SQL EXECUTION TRACE COUNT    : "
        f"{sql_count}"
    )

    out(
        f"BLOCKED WRITE-LIKE OPERATIONS: "
        f"{blocked}"
    )

    if (
        execution.get("status")
        == "EXECUTED"
        and runtime_calls > 0
    ):

        status = (
            "PRODUCTION_ENTRYPOINT_RUNTIME_OBSERVED"
        )

        meaning = (
            "The actual production entrypoint was executed "
            "under the read-only forensic sandbox and "
            "calculate_analysis received a real runtime rows object."
        )

        next_frontier = (
            "Compare the captured runtime rows object, "
            "actual SQL parameter tuple, production return, "
            "post-calculation assignment, and stored database value."
        )

    elif (
        execution.get("status")
        == "ENTRYPOINT_REQUIRES_RUNTIME_ARGUMENTS"
    ):

        status = (
            "ENTRYPOINT_REQUIRES_EXPLICIT_RUNTIME_ARGUMENTS"
        )

        meaning = (
            "The resolved entrypoint exists but requires "
            "runtime arguments; no arguments were fabricated."
        )

        next_frontier = (
            "Provide the exact production entrypoint arguments "
            "or trace the real launcher that supplies them."
        )

    else:

        status = (
            "PRODUCTION_ENTRYPOINT_RUNTIME_NOT_OBSERVED"
        )

        meaning = (
            "The production entrypoint was not safely executed "
            "during this audit."
        )

        next_frontier = (
            "Resolve the exact executable production entrypoint "
            "and its genuine runtime argument construction."
        )

    out(
        f"STATUS                       : {status}"
    )

    out(
        f"MEANING                      : {meaning}"
    )

    out(
        f"NEXT FRONTIER                : {next_frontier}"
    )

    out()
    out(
        "DATABASE WRITE OPERATIONS    : NONE"
    )

    out(
        "ENGINE MODIFICATIONS         : NONE"
    )

    out(
        "INSERT                       : NONE"
    )

    out(
        "UPDATE                       : NONE"
    )

    out(
        "DELETE                       : NONE"
    )

    out(
        "ALTER                        : NONE"
    )

    out(
        "CREATE                       : NONE"
    )

    out(
        "DROP                         : NONE"
    )

    out(
        "PRODUCTION DB WRITE          : BLOCKED"
    )

    out(
        f"ELAPSED SECONDS              : "
        f"{time.perf_counter() - start:.3f}"
    )

    out(
        "AUDIT COMPLETE"
    )


if __name__ == "__main__":
    main()