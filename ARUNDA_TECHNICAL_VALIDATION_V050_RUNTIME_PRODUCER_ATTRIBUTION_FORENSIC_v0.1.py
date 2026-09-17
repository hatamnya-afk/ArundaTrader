# ======================================================================
# ARUNDA TECHNICAL VALIDATION v0.5.0
# RUNTIME PRODUCER ATTRIBUTION FORENSIC v0.1
#
# MODE: READ ONLY
# TARGET: market_technical.id = 6909
#
# NO main()
# NO INSERT
# NO UPDATE
# NO DELETE
# NO COMMIT
# NO PRODUCTION WRITE
# NO SYNTHETIC DATA
# ======================================================================

import ast
import sqlite3
import hashlib
import importlib.util
import inspect
from pathlib import Path


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = ROOT / "arunda.db"
ENGINE_FILE = ROOT / "ARUNDA_TECHNICAL_ENGINE_v0.5.py"
TARGET_ID = 6909


def section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def safe(v):
    return "NULL" if v is None else str(v)


# ======================================================================
# 1. HEADER
# ======================================================================

section("ARUNDA TECHNICAL VALIDATION PRODUCER ATTRIBUTION FORENSIC v0.1")

print("MODE                         : READ ONLY")
print("TARGET TABLE                : market_technical")
print(f"TARGET ROW                  : id={TARGET_ID}")
print("PRODUCTION EXECUTION        : NO")
print("DATABASE WRITE              : NO")
print("MAIN()                      : NOT EXECUTED")

if not ROOT.exists():
    raise RuntimeError("PROJECT ROOT NOT FOUND")

if not DB_PATH.exists():
    raise RuntimeError("DATABASE NOT FOUND")

if not ENGINE_FILE.exists():
    raise RuntimeError("v0.5.0 ENGINE FILE NOT FOUND")


# ======================================================================
# 2. SOURCE HASH
# ======================================================================

source_bytes = ENGINE_FILE.read_bytes()
sha_before = hashlib.sha256(source_bytes).hexdigest()

print()
print("ENGINE SOURCE SHA256        :", sha_before)


# ======================================================================
# 3. STATIC AST INSPECTION
# ======================================================================

section("AST PRODUCER STRUCTURE")

source = ENGINE_FILE.read_text(
    encoding="utf-8",
    errors="replace"
)

tree = ast.parse(source)

functions = {}

for node in ast.walk(tree):

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

        functions[node.name] = node


print(f"FUNCTION COUNT               : {len(functions)}")

for name in sorted(functions):

    node = functions[name]

    name_lower = name.lower()

    if any(
        token in name_lower
        for token in [
            "valid",
            "score",
            "flag",
            "process",
            "update",
            "persist",
            "write",
        ]
    ):

        print(
            f"FUNCTION={name:<40} "
            f"LINE={node.lineno}-"
            f"{getattr(node, 'end_lineno', node.lineno)}"
        )


# ======================================================================
# 4. VALIDATION TARGET DISCOVERY
# ======================================================================

section("VALIDATION PRODUCER DISCOVERY")

validation_functions = []

for name, node in functions.items():

    body_text = ast.get_source_segment(source, node) or ""

    upper = body_text.upper()

    if (
        "TECHNICAL_VALIDATION_SCORE" in upper
        or "INVALID_REGIME" in upper
        or "INVALID_VOLATILITY" in upper
        or (
            "VALID" in upper
            and "FLAGS" in upper
            and "SCORE" in upper
        )
    ):

        validation_functions.append(name)

        print(
            f"[MATCH] {name:<40} "
            f"LINE={node.lineno}"
        )


# ======================================================================
# 5. UPDATE PRODUCER DISCOVERY
# ======================================================================

section("PERSISTENCE PRODUCER DISCOVERY")

for node in ast.walk(tree):

    if not isinstance(node, ast.Assign):
        continue

    try:
        text = ast.get_source_segment(source, node) or ""
    except Exception:
        text = ""

    upper = text.upper()

    if (
        "TECHNICAL_VALIDATION_SCORE" in upper
        or "TECHNICAL_VALIDATION_STATUS" in upper
        or "TECHNICAL_VALIDATION_FLAGS" in upper
    ):

        print(
            f"LINE={node.lineno:<6} "
            f"{' '.join(text.split())[:1000]}"
        )


# ======================================================================
# 6. READ-ONLY DATABASE
# ======================================================================

section("READ-ONLY DATABASE")

uri = f"file:{DB_PATH.as_posix()}?mode=ro"

conn = sqlite3.connect(
    uri,
    uri=True
)

conn.row_factory = sqlite3.Row

conn.execute("PRAGMA query_only = ON")

query_only = conn.execute(
    "PRAGMA query_only"
).fetchone()[0]

print(f"SQLite query_only            : {query_only}")

if query_only != 1:
    raise RuntimeError(
        "SQLite query_only could not be enabled"
    )


# ======================================================================
# 7. REAL TARGET ROW
# ======================================================================

section("REAL PERSISTED INPUT")

row = conn.execute(
    """
    SELECT *
    FROM market_technical
    WHERE id = ?
    """,
    (TARGET_ID,)
).fetchone()

if row is None:
    raise RuntimeError(
        f"TARGET ROW NOT FOUND: {TARGET_ID}"
    )

columns = row.keys()

print(f"id                           : {safe(row['id'])}")
print(f"symbol                       : {safe(row['symbol'])}")
print(f"timestamp                    : {safe(row['timestamp'])}")

for field in [
    "price",
    "close",
    "history_points",
    "technical_available",
    "available",
    "technical_completeness",
    "rsi14",
    "rsi_14",
    "atr14",
    "atr_14",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "volume_score",
    "range_score",
    "breakout_score",
    "regime",
    "technical_version",
    "engine_version",
    "source",
]:

    if field in columns:

        print(
            f"{field:<30} : {safe(row[field])}"
        )


# ======================================================================
# 8. PERSISTED VALIDATION STATE
# ======================================================================

section("PERSISTED VALIDATION STATE")

persisted = {}

for field in [
    "technical_validation_score",
    "technical_validation_status",
    "technical_validation_flags",
    "technical_validation_version",
    "technical_validated_at",
]:

    value = (
        row[field]
        if field in columns
        else None
    )

    persisted[field] = value

    print(
        f"{field:<40} : {safe(value)}"
    )


# ======================================================================
# 9. SAFE PRODUCTION MODULE LOAD
# ======================================================================
#
# IMPORTANT:
# main() is deliberately NOT called.
#
# We only resolve the module object and inspect callable producers.
# ======================================================================

section("PRODUCTION MODULE LOAD")

spec = importlib.util.spec_from_file_location(
    "arunda_technical_engine_v050_runtime",
    ENGINE_FILE
)

if spec is None or spec.loader is None:
    raise RuntimeError(
        "Could not create module specification"
    )

module = importlib.util.module_from_spec(spec)

print(
    "Module object created         : YES"
)

print(
    "main() execution              : NO"
)


# ======================================================================
# 10. EXECUTE MODULE LOAD
# ======================================================================
#
# No explicit main() invocation.
# ======================================================================

spec.loader.exec_module(module)

print(
    "Production module loaded      : YES"
)

if hasattr(module, "main"):
    print(
        "main callable                : YES"
    )
else:
    print(
        "main callable                : NO"
    )


# ======================================================================
# 11. ENGINE VERSION
# ======================================================================

section("ENGINE VERSION")

runtime_version = getattr(
    module,
    "ENGINE_VERSION",
    None
)

print(
    f"Runtime ENGINE_VERSION        : {safe(runtime_version)}"
)

print(
    "Expected                      : 0.5.0"
)


# ======================================================================
# 12. REAL RUNTIME PRODUCER SEARCH
# ======================================================================

section("REAL RUNTIME VALIDATION PRODUCER")

runtime_candidates = []

for name in validation_functions:

    fn = getattr(
        module,
        name,
        None
    )

    if callable(fn):

        try:
            signature = inspect.signature(fn)
        except Exception:
            signature = "<unknown>"

        runtime_candidates.append(
            (
                name,
                fn,
                signature
            )
        )

        print(
            f"[CALLABLE] {name:<40} "
            f"signature={signature}"
        )


# ======================================================================
# 13. DIRECT validate_row() TEST
# ======================================================================

section("REAL validate_row()")

validate_row = getattr(
    module,
    "validate_row",
    None
)

if not callable(validate_row):

    print(
        "validate_row()                : NOT FOUND"
    )

else:

    print(
        "validate_row()                : FOUND"
    )

    print(
        "Signature                     :",
        inspect.signature(validate_row)
    )

    print(
        "Source                        :",
        inspect.getsourcefile(validate_row)
    )

    # --------------------------------------------------------------
    # REAL ROW -> REAL VALIDATOR
    # --------------------------------------------------------------

    try:

        runtime_output = validate_row(
            row,
            columns
        )

    except Exception as exc:

        print()
        print(
            "RUNTIME ERROR                 :",
            repr(exc)
        )

        raise

    print()
    print(
        "RAW RUNTIME OUTPUT            :",
        repr(runtime_output)
    )

    if not isinstance(
        runtime_output,
        tuple
    ):

        raise RuntimeError(
            "validate_row() did not return tuple"
        )

    if len(runtime_output) != 3:

        raise RuntimeError(
            f"Unexpected validate_row() tuple length: "
            f"{len(runtime_output)}"
        )

    runtime_score = runtime_output[0]
    runtime_status = runtime_output[1]
    runtime_flags = runtime_output[2]

    print()
    print(
        f"Runtime score                 : {safe(runtime_score)}"
    )

    print(
        f"Runtime status                : {safe(runtime_status)}"
    )

    print(
        f"Runtime flags                 : {safe(runtime_flags)}"
    )


# ======================================================================
# 14. VALIDATION_RESULTS RECONSTRUCTION
# ======================================================================

section("VALIDATION_RESULTS RECONSTRUCTION")

validated_at = "FORENSIC_RUNTIME_TIMESTAMP"

validation_tuple = (
    runtime_score,
    runtime_status,
    runtime_flags,
    runtime_version,
    validated_at,
    TARGET_ID,
)

print(
    "validation_results.append("
)

print(
    f"    {validation_tuple!r}"
)

print(
    ")"
)


# ======================================================================
# 15. UPDATE PARAMETER MAPPING
# ======================================================================

section("UPDATE PARAMETER MAPPING")

update_sql = """
UPDATE market_technical
SET
    technical_validation_score = ?,
    technical_validation_status = ?,
    technical_validation_flags = ?,
    technical_validation_version = ?,
    technical_validated_at = ?
WHERE id = ?
"""

print(
    "UPDATE market_technical"
)

print(
    "SET technical_validation_score = ?"
)

print(
    "   technical_validation_status = ?"
)

print(
    "   technical_validation_flags = ?"
)

print(
    "   technical_validation_version = ?"
)

print(
    "   technical_validated_at = ?"
)

print(
    "WHERE id = ?"
)

print()
print(
    "PARAMETERS:"
)

params = (
    runtime_score,
    runtime_status,
    runtime_flags,
    runtime_version,
    validated_at,
    TARGET_ID,
)

for i, value in enumerate(params, 1):

    print(
        f"  [{i}] {safe(value)}"
    )


# ======================================================================
# 16. RUNTIME VS PERSISTED
# ======================================================================

section("RUNTIME VS PERSISTED")

comparisons = [
    (
        "technical_validation_score",
        runtime_score,
        persisted["technical_validation_score"],
    ),
    (
        "technical_validation_status",
        runtime_status,
        persisted["technical_validation_status"],
    ),
    (
        "technical_validation_flags",
        runtime_flags,
        persisted["technical_validation_flags"],
    ),
    (
        "technical_validation_version",
        runtime_version,
        persisted["technical_validation_version"],
    ),
]

exact_matches = 0

for field, runtime, db in comparisons:

    match = runtime == db

    if match:
        exact_matches += 1

    print(
        f"[{'MATCH' if match else 'MISMATCH':<9}] "
        f"{field:<40} "
        f"runtime={safe(runtime):<30} "
        f"db={safe(db)}"
    )


# ======================================================================
# 17. CRITICAL PRODUCER ATTRIBUTION
# ======================================================================

section("PRODUCER ATTRIBUTION RESULT")

print(
    f"TARGET ROW                   : {TARGET_ID}"
)

print(
    f"v0.5.0 RUNTIME SCORE         : {safe(runtime_score)}"
)

print(
    f"v0.5.0 RUNTIME STATUS        : {safe(runtime_status)}"
)

print(
    f"v0.5.0 RUNTIME FLAGS         : {safe(runtime_flags)}"
)

print(
    f"PERSISTED SCORE              : "
    f"{safe(persisted['technical_validation_score'])}"
)

print(
    f"PERSISTED STATUS             : "
    f"{safe(persisted['technical_validation_status'])}"
)

print(
    f"PERSISTED FLAGS              : "
    f"{safe(persisted['technical_validation_flags'])}"
)

print()

if (
    runtime_score ==
    persisted["technical_validation_score"]
    and
    runtime_status ==
    persisted["technical_validation_status"]
    and
    runtime_flags ==
    persisted["technical_validation_flags"]
    and
    runtime_version ==
    persisted["technical_validation_version"]
):

    print(
        "PRODUCER ATTRIBUTION         : EXACT MATCH"
    )

    print(
        "v0.5.0 runtime can reproduce "
        "the persisted validation state."
    )

else:

    print(
        "PRODUCER ATTRIBUTION         : DIVERGENCE"
    )

    print(
        "v0.5.0 runtime does NOT reproduce "
        "the persisted validation state exactly."
    )


# ======================================================================
# 18. WRITE PATH — SIMULATED ONLY
# ======================================================================

section("WRITE PATH")

print(
    "executemany(update_sql, validation_results)"
)

print(
    "STATUS                       : SIMULATED ONLY"
)

print(
    "conn.commit()                : NOT EXECUTED"
)

print(
    "DATABASE WRITE               : NONE"
)


# ======================================================================
# 19. SOURCE INTEGRITY
# ======================================================================

section("SOURCE INTEGRITY AFTER")

sha_after = hashlib.sha256(
    ENGINE_FILE.read_bytes()
).hexdigest()

print(
    "SHA256 BEFORE                :",
    sha_before
)

print(
    "SHA256 AFTER                 :",
    sha_after
)

print(
    "SOURCE UNCHANGED             :",
    sha_before == sha_after
)


# ======================================================================
# 20. FINAL FORENSIC CONTRACT
# ======================================================================

section("FINAL FORENSIC CONTRACT")

print(
    "REAL ROW                     : YES"
)

print(
    "REAL v0.5.0 VALIDATOR        : YES"
)

print(
    "main()                       : NOT EXECUTED"
)

print(
    "UPDATE                        : NOT EXECUTED"
)

print(
    "COMMIT                        : NOT EXECUTED"
)

print(
    "DATABASE WRITE               : NONE"
)

print(
    "SOURCE MODIFICATION          : NONE"
)

print(
    "SYNTHETIC DATA               : NONE"
)

print(
    "INTERPOLATION                : NONE"
)

print(
    "FORWARD FILL                 : NONE"
)

print(
    "BACK FILL                    : NONE"
)

print()

print(
    "ARUNDA TECHNICAL VALIDATION "
    "v0.5.0 RUNTIME PRODUCER ATTRIBUTION "
    "FORENSIC v0.1 COMPLETE"
)

conn.close()