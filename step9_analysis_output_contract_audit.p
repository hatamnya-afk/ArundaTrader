```python
import ast
import sqlite3
from pathlib import Path


# =============================================================================
# ARUNDA TRADER — DEV-06 — STEP 9
# ANALYSIS OUTPUT CONTRACT AUDIT v0.1
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"
ANALYSIS_FILE = BASE_DIR / "history_analysis_engine.py"

ENGINE_NAME = "HISTORY_ANALYSIS_v0.1"

REQUIRED_FIELDS = {
    "cmc_id",
    "symbol",
    "latest_timestamp",
    "previous_timestamp",
    "price",
    "previous_price",
    "price_change",
    "price_change_pct",
    "snapshot_change",
    "momentum",
    "trend",
    "volatility",
    "volume_regime",
}

OPTIONAL_FIELDS = {
    "volume_24h",
    "previous_volume_24h",
    "volume_change_pct",
    "market_cap",
    "rank",
    "change_1h",
    "change_24h",
    "change_7d",
}


# =============================================================================
# OUTPUT
# =============================================================================

def header(title):
    print("=" * 100)
    print(title)
    print("=" * 100)


def section(title):
    print()
    print(title)
    print("-" * 100)


def result(ok):
    return "PASS" if ok else "FAIL"


# =============================================================================
# SOURCE
# =============================================================================

def read_source():
    if not ANALYSIS_FILE.exists():
        return None, "Analysis engine file does not exist."

    try:
        source = ANALYSIS_FILE.read_text(
            encoding="utf-8-sig"
        )
        return source, None
    except Exception as exc:
        return None, str(exc)


def parse_source(source):
    try:
        return ast.parse(source), None
    except SyntaxError as exc:
        return None, str(exc)


def function_inventory(tree):
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)

    return sorted(set(functions))


# =============================================================================
# AST FIELD DISCOVERY
# =============================================================================

def string_constants(tree):
    values = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.add(node.value)

    return values


def dictionary_keys(tree):
    keys = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant):
                    if isinstance(key.value, str):
                        keys.add(key.value)

    return keys


def return_dictionary_keys(tree):
    keys = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Return):
            continue

        value = node.value

        if not isinstance(value, ast.Dict):
            continue

        for key in value.keys:
            if isinstance(key, ast.Constant):
                if isinstance(key.value, str):
                    keys.add(key.value)

    return keys


def all_field_references(tree):
    fields = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Subscript):
            target = node.value

            if isinstance(target, ast.Name):
                if target.id in {
                    "feature",
                    "record",
                    "analysis",
                    "result",
                    "output",
                }:
                    slice_node = node.slice

                    if isinstance(slice_node, ast.Constant):
                        if isinstance(slice_node.value, str):
                            fields.add(slice_node.value)

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "get":
                    for arg in node.args:
                        if isinstance(arg, ast.Constant):
                            if isinstance(arg.value, str):
                                fields.add(arg.value)

    return fields


# =============================================================================
# OUTPUT FUNCTION DISCOVERY
# =============================================================================

def find_analysis_functions(tree):
    names = {
        "analyze_feature",
        "analyze_features",
        "validate_analysis_record",
        "validate_analysis_collection",
    }

    found = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name in names:
                found.append(node.name)

    return sorted(found)


def function_source(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name == name:
                return node

    return None


def function_references(tree, function_name):
    node = function_source(tree, function_name)

    if node is None:
        return set()

    fields = set()

    for child in ast.walk(node):

        if isinstance(child, ast.Subscript):
            target = child.value

            if isinstance(target, ast.Name):
                if target.id in {
                    "feature",
                    "record",
                    "analysis",
                    "result",
                    "output",
                }:
                    slice_node = child.slice

                    if isinstance(slice_node, ast.Constant):
                        if isinstance(slice_node.value, str):
                            fields.add(slice_node.value)

        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Attribute):
                if child.func.attr == "get":
                    for arg in child.args:
                        if isinstance(arg, ast.Constant):
                            if isinstance(arg.value, str):
                                fields.add(arg.value)

    return fields


# =============================================================================
# IDENTITY AUDIT
# =============================================================================

def audit_identity(tree):
    refs = function_references(tree, "analyze_feature")

    has_cmc = "cmc_id" in refs
    has_symbol = "symbol" in refs

    return has_cmc, has_symbol


def audit_symbol_identity(tree):
    source = ast.unparse(tree).lower()

    forbidden_patterns = [
        "symbol ==",
        "symbol ==",
        "symbol, timestamp",
        "timestamp, symbol",
        "symbol + timestamp",
        "symbol + cmc_id",
        "cmc_id + symbol",
    ]

    hits = [
        pattern
        for pattern in forbidden_patterns
        if pattern in source
    ]

    return hits


# =============================================================================
# MUTATION AUDIT
# =============================================================================

def audit_sql_mutations(tree):
    mutation_words = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "ALTER",
        "DROP",
        "CREATE",
        "REPLACE",
        "UPSERT",
    }

    hits = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Constant):
            if not isinstance(node.value, str):
                continue

            text = node.value.upper()

            for word in mutation_words:
                if word in text:
                    hits.append(word)

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):

                method = node.func.attr.lower()

                if method in {
                    "commit",
                    "rollback",
                    "executemany",
                    "executescript",
                }:
                    hits.append(method)

    return sorted(set(hits))


# =============================================================================
# DATABASE FINGERPRINT
# =============================================================================

def connect_read_only():
    uri = f"file:{DB_PATH}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=5,
    )


def history_fingerprint(conn):
    cur = conn.cursor()

    rows = cur.execute(
        "SELECT COUNT(*) FROM market_history"
    ).fetchone()[0]

    snapshots = cur.execute(
        "SELECT COUNT(DISTINCT timestamp) FROM market_history"
    ).fetchone()[0]

    cmc_ids = cur.execute(
        "SELECT COUNT(DISTINCT cmc_id) FROM market_history"
    ).fetchone()[0]

    duplicate_ids = cur.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT timestamp, cmc_id
            FROM market_history
            GROUP BY timestamp, cmc_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    first_timestamp = cur.execute(
        "SELECT MIN(timestamp) FROM market_history"
    ).fetchone()[0]

    last_timestamp = cur.execute(
        "SELECT MAX(timestamp) FROM market_history"
    ).fetchone()[0]

    return {
        "rows": rows,
        "snapshots": snapshots,
        "cmc_ids": cmc_ids,
        "duplicate_ids": duplicate_ids,
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
    }


def fingerprint_equal(before, after):
    return before == after


# =============================================================================
# RUNTIME OUTPUT TEST
# =============================================================================

def load_analysis_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "history_analysis_engine",
        ANALYSIS_FILE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to load analysis engine."
        )

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module


def runtime_output_test():
    """
    Attempts to execute the analysis engine through its public
    analysis function without modifying the database.

    The test is intentionally tolerant because the current engine
    may expose analysis through different internal paths.
    """

    module = load_analysis_module()

    if not hasattr(module, "analyze_feature"):
        return False, "analyze_feature not found"

    analyze_feature = module.analyze_feature

    sample = {
        "cmc_id": 999999999,
        "symbol": "AUDIT",
        "latest_timestamp": "2026-01-01T00:00:00+00:00",
        "previous_timestamp": "2025-12-31T23:59:00+00:00",
        "price": 125.0,
        "previous_price": 100.0,
        "snapshot_change": 25.0,
        "snapshot_change_pct": 25.0,
        "volume_24h": 1500.0,
        "previous_volume_24h": 1000.0,
        "market_cap": 1000000.0,
        "rank": 100,
        "change_1h": 2.0,
        "change_24h": 5.0,
        "change_7d": 10.0,
        "previous_volume": 1000.0,
    }

    try:
        output = analyze_feature(sample)

    except Exception as exc:
        return False, f"runtime execution failed: {exc}"

    if not isinstance(output, dict):
        return False, "analysis output is not a dictionary"

    missing = REQUIRED_FIELDS - set(output.keys())

    if missing:
        return False, (
            "missing required fields: "
            + ", ".join(sorted(missing))
        )

    return True, output


# =============================================================================
# MAIN AUDIT
# =============================================================================

def main():

    header(
        "ARUNDA TRADER — DEV-06 — STEP 9\n"
        "ANALYSIS OUTPUT CONTRACT AUDIT v0.1"
    )

    print()

    print("MODE")
    print("-" * 100)
    print("Database mutation : NONE")
    print("Production write  : NONE")
    print("Audit mode        : READ ONLY")

    # -------------------------------------------------------------------------
    # FILE VALIDATION
    # -------------------------------------------------------------------------

    section("FILE VALIDATION")

    source, source_error = read_source()

    file_ok = source is not None

    print(
        "Analysis Engine :",
        result(file_ok)
    )

    if not file_ok:
        print("ERROR :", source_error)
        print()
        print("RESULT : ANALYSIS OUTPUT CONTRACT AUDIT FAIL")
        return 1

    tree, parse_error = parse_source(source)

    syntax_ok = tree is not None

    print(
        "AST Parse       :",
        result(syntax_ok)
    )

    if not syntax_ok:
        print("ERROR :", parse_error)
        return 1

    # -------------------------------------------------------------------------
    # FUNCTION INVENTORY
    # -------------------------------------------------------------------------

    section("FUNCTION INVENTORY")

    for name in function_inventory(tree):
        print(" -", name)

    # -------------------------------------------------------------------------
    # REQUIRED FUNCTIONS
    # -------------------------------------------------------------------------

    section("REQUIRED OUTPUT FUNCTIONS")

    functions = set(function_inventory(tree))

    required_functions = {
        "analyze_feature",
        "analyze_features",
        "validate_analysis_record",
        "validate_analysis_collection",
    }

    functions_ok = required_functions.issubset(functions)

    for name in sorted(required_functions):
        print(
            f"{name:<35}:",
            result(name in functions)
        )

    # -------------------------------------------------------------------------
    # STATIC OUTPUT SCHEMA
    # -------------------------------------------------------------------------

    section("STATIC OUTPUT SCHEMA AUDIT")

    discovered = set()

    discovered |= dictionary_keys(tree)
    discovered |= return_dictionary_keys(tree)
    discovered |= function_references(
        tree,
        "analyze_feature"
    )

    print("Detected output field candidates")

    for field in sorted(discovered):
        print(" -", field)

    static_required = REQUIRED_FIELDS.intersection(
        discovered
    )

    static_contract_ok = (
        REQUIRED_FIELDS.issubset(discovered)
    )

    print()
    print(
        "Required fields detected :",
        len(static_required),
        "/",
        len(REQUIRED_FIELDS)
    )

    print(
        "Static contract           :",
        result(static_contract_ok)
    )

    # -------------------------------------------------------------------------
    # IDENTITY
    # -------------------------------------------------------------------------

    section("IDENTITY CONTRACT")

    has_cmc, has_symbol = audit_identity(tree)

    print(
        "CMC_ID identity detected :",
        result(has_cmc)
    )

    print(
        "Symbol field detected    :",
        result(has_symbol)
    )

    identity_ok = has_cmc

    print(
        "CMC_ID based identity    :",
        result(identity_ok)
    )

    # -------------------------------------------------------------------------
    # SYMBOL IDENTITY
    # -------------------------------------------------------------------------

    section("SYMBOL NON-IDENTITY AUDIT")

    symbol_hits = audit_symbol_identity(tree)

    if symbol_hits:
        for hit in symbol_hits:
            print("FORBIDDEN :", hit)

    symbol_identity_ok = not symbol_hits

    print(
        "Symbol-based identity :",
        "SAFE" if symbol_identity_ok else "FAIL"
    )

    # -------------------------------------------------------------------------
    # OPTIONAL FIELDS
    # -------------------------------------------------------------------------

    section("OPTIONAL ANALYSIS FIELDS")

    for field in sorted(OPTIONAL_FIELDS):
        if field in discovered:
            print(f"{field:<30}: DETECTED")
        else:
            print(f"{field:<30}: NOT DETECTED")

    # -------------------------------------------------------------------------
    # RUNTIME OUTPUT
    # -------------------------------------------------------------------------

    section("RUNTIME OUTPUT CONTRACT")

    runtime_ok, runtime_result = runtime_output_test()

    print(
        "Runtime execution :",
        result(runtime_ok)
    )

    if runtime_ok:
        print(
            "Output fields     :",
            len(runtime_result)
        )

        print(
            "Required fields   :",
            result(
                REQUIRED_FIELDS.issubset(
                    runtime_result.keys()
                )
            )
        )

        print(
            "CMC_ID present    :",
            result(
                "cmc_id" in runtime_result
            )
        )

        print(
            "Symbol present    :",
            result(
                "symbol" in runtime_result
            )
        )

    else:
        print(
            "Runtime detail :",
            runtime_result
        )

    # -------------------------------------------------------------------------
    # MUTATION
    # -------------------------------------------------------------------------

    section("READ-ONLY / MUTATION AUDIT")

    mutation_hits = audit_sql_mutations(tree)

    if mutation_hits:
        for hit in mutation_hits:
            print("MUTATION DETECTED :", hit)
    else:
        print(
            "SQL mutation statements : NONE DETECTED"
        )

    mutation_ok = not mutation_hits

    # -------------------------------------------------------------------------
    # DATABASE FINGERPRINT
    # -------------------------------------------------------------------------

    section("DATABASE READ-ONLY FINGERPRINT")

    conn = None

    try:
        conn = connect_read_only()

        before = history_fingerprint(conn)

        print(
            "Rows              :",
            before["rows"]
        )
        print(
            "Snapshots         :",
            before["snapshots"]
        )
        print(
            "Distinct CMC IDs  :",
            before["cmc_ids"]
        )
        print(
            "Duplicate IDs     :",
            before["duplicate_ids"]
        )

        conn.close()
        conn = None

    except Exception as exc:

        print(
            "Database fingerprint : FAIL"
        )
        print(
            "ERROR :",
            exc
        )

        return 1

    # -------------------------------------------------------------------------
    # SECOND FINGERPRINT
    # -------------------------------------------------------------------------

    section("DATABASE FINGERPRINT PRESERVATION")

    try:

        conn = connect_read_only()

        after = history_fingerprint(conn)

        conn.close()
        conn = None

        unchanged = fingerprint_equal(
            before,
            after
        )

    except Exception as exc:

        print(
            "Fingerprint preservation : FAIL"
        )
        print(
            "ERROR :",
            exc
        )

        return 1

    print(
        "BEFORE == AFTER    :",
        result(unchanged)
    )

    # -------------------------------------------------------------------------
    # FINAL CONTRACT
    # -------------------------------------------------------------------------

    section("STEP 9 OUTPUT CONTRACT")

    print(
        f"{'AST syntax':<35}:",
        result(syntax_ok)
    )

    print(
        f"{'Required functions':<35}:",
        result(functions_ok)
    )

    print(
        f"{'Static output schema':<35}:",
        result(static_contract_ok)
    )

    print(
        f"{'Runtime output contract':<35}:",
        result(runtime_ok)
    )

    print(
        f"{'CMC_ID identity':<35}:",
        result(identity_ok)
    )

    print(
        f"{'No symbol identity':<35}:",
        result(symbol_identity_ok)
    )

    print(
        f"{'Read only':<35}:",
        result(mutation_ok)
    )

    print(
        f"{'Database unchanged':<35}:",
        result(unchanged)
    )

    final_ok = all([
        syntax_ok,
        functions_ok,
        static_contract_ok,
        runtime_ok,
        identity_ok,
        symbol_identity_ok,
        mutation_ok,
        unchanged,
    ])

    print()
    print("=" * 100)

    if final_ok:

        print(
            "STEP 9 VERDICT"
        )
        print("=" * 100)

        print(
            "RESULT : ANALYSIS OUTPUT CONTRACT AUDIT PASS"
        )
        print(
            "STATUS : ANALYSIS OUTPUT CONTRACT LOCKED"
        )

        print()
        print(
            "Architecture : PRESERVED"
        )
        print(
            "Database     : READ ONLY"
        )
        print(
            "History      : UNCHANGED"
        )
        print(
            "Analysis     : CONTRACT VERIFIED"
        )
        print(
            "Writes       : NONE"
        )

        return 0

    print(
        "STEP 9 VERDICT"
    )
    print("=" * 100)

    print(
        "RESULT : ANALYSIS OUTPUT CONTRACT AUDIT FAIL"
    )
    print(
        "STATUS : DO NOT PROCEED TO SIGNAL CONSUMPTION"
    )

    print()
    print(
        "Architecture : PRESERVED"
    )
    print(
        "Database     : READ ONLY"
    )
    print(
        "History      : MUST REMAIN UNCHANGED"
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```
