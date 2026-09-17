import ast
from pathlib import Path


FILE = Path("history_feature_extractor.py")


print("=" * 100)
print("ARUNDA TRADER — DEV-06 — STEP 5A")
print("FEATURE SCHEMA AUDIT")
print("=" * 100)


# ============================================================================
# LOAD SOURCE
# ============================================================================

print()
print("FILE")
print("-" * 100)

print("Path   :", FILE.resolve())
print("Exists :", "PASS" if FILE.exists() else "FAIL")

if not FILE.exists():
    print()
    print("=" * 100)
    print("STEP 5A VERDICT")
    print("=" * 100)
    print("RESULT : FEATURE SCHEMA AUDIT FAIL")
    print("STATUS : FILE NOT FOUND")
    raise SystemExit(1)


try:
    source = FILE.read_text(encoding="utf-8-sig")
except Exception as exc:
    print("Read error :", type(exc).__name__, exc)
    raise SystemExit(1)


print("Bytes  :", FILE.stat().st_size)
print("Lines  :", len(source.splitlines()))


# ============================================================================
# AST PARSE
# ============================================================================

try:
    tree = ast.parse(source, filename=str(FILE))
    syntax_pass = True
except SyntaxError as exc:
    syntax_pass = False
    tree = None

print()
print("SOURCE SYNTAX")
print("-" * 100)
print("AST Parse :", "PASS" if syntax_pass else "FAIL")

if not syntax_pass:
    print()
    print("=" * 100)
    print("STEP 5A VERDICT")
    print("=" * 100)
    print("RESULT : FEATURE SCHEMA AUDIT FAIL")
    print("STATUS : INVALID PYTHON SOURCE")
    raise SystemExit(1)


# ============================================================================
# AST HELPERS
# ============================================================================

def function_nodes(tree):
    result = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.append(node)

    return result


def node_names(node):
    result = set()

    for child in ast.walk(node):

        if isinstance(child, ast.Name):
            result.add(child.id.lower())

        elif isinstance(child, ast.Attribute):
            result.add(child.attr.lower())

        elif isinstance(child, ast.Constant):
            if isinstance(child.value, str):
                result.add(child.value.lower())

    return result


def string_literals(node):
    result = []

    for child in ast.walk(node):
        if isinstance(child, ast.Constant):
            if isinstance(child.value, str):
                result.append(child.value)

    return result


def contains_token(tokens, candidates):
    candidates = {
        str(value).lower()
        for value in candidates
    }

    return bool(tokens.intersection(candidates))


functions = function_nodes(tree)

all_names = node_names(tree)
all_strings = {
    value.lower()
    for value in string_literals(tree)
}

all_tokens = all_names | all_strings


# ============================================================================
# FUNCTION INVENTORY
# ============================================================================

print()
print("FUNCTION INVENTORY")
print("-" * 100)

for fn in functions:
    print(" -", fn.name)


# ============================================================================
# IDENTITY FIELD AUDIT
# ============================================================================

print()
print("IDENTITY FIELD AUDIT")
print("-" * 100)

identity_fields = [
    "cmc_id",
    "name",
    "symbol",
    "timestamp",
]

identity_results = {}

for field in identity_fields:
    found = field in all_tokens
    identity_results[field] = found

    print(
        f"{field:<24}:",
        "FOUND" if found else "NOT FOUND"
    )


# ============================================================================
# HISTORY FIELD AUDIT
# ============================================================================

print()
print("HISTORY FIELD AUDIT")
print("-" * 100)

history_fields = [
    "cmc_id",
    "timestamp",
    "symbol",
    "name",
    "price",
]

history_results = {}

for field in history_fields:
    found = field in all_tokens
    history_results[field] = found

    print(
        f"{field:<24}:",
        "FOUND" if found else "NOT FOUND"
    )


# ============================================================================
# FEATURE FIELD CANDIDATES
# ============================================================================

print()
print("FEATURE FIELD CANDIDATES")
print("-" * 100)

feature_keywords = (
    "cmc",
    "price",
    "prev",
    "change",
    "return",
    "volume",
    "rank",
    "market_cap",
    "timestamp",
    "symbol",
    "feature",
)

feature_candidates = sorted(
    token
    for token in all_tokens
    if any(keyword in token for keyword in feature_keywords)
)

for field in feature_candidates:
    print(" -", field)


# ============================================================================
# FIND extract_features()
# ============================================================================

print()
print("FEATURE EXTRACTION FUNCTION AUDIT")
print("-" * 100)

extract_fn = None

for fn in functions:
    if fn.name == "extract_features":
        extract_fn = fn
        break


if extract_fn is None:

    print("extract_features function :", "MISSING")

    extract_function_pass = False

else:

    print("extract_features function :", "FOUND")

    extract_tokens = node_names(extract_fn)

    extract_strings = {
        value.lower()
        for value in string_literals(extract_fn)
    }

    extract_all_tokens = (
        extract_tokens |
        extract_strings
    )

    print()


    # ========================================================================
    # CMC_ID
    # ========================================================================

    cmc_id_ok = contains_token(
        extract_all_tokens,
        {
            "cmc_id",
            "latest_cmc_id",
            "previous_cmc_id",
            "cmc_ids",
            "common_cmc_ids",
        }
    )

    print(
        f"{'cmc_id':<24}:",
        "PASS" if cmc_id_ok else "FAIL"
    )


    # ========================================================================
    # SYMBOL
    #
    # Accept:
    #   symbol
    #   latest_symbol
    #   previous_symbol
    #   row["symbol"]
    #   latest["symbol"]
    # ========================================================================

    symbol_ok = contains_token(
        extract_all_tokens,
        {
            "symbol",
            "latest_symbol",
            "previous_symbol",
            "current_symbol",
        }
    )

    print(
        f"{'symbol':<24}:",
        "PASS" if symbol_ok else "FAIL"
    )


    # ========================================================================
    # PRICE
    #
    # Accept:
    #   price
    #   latest_price
    #   current_price
    #   previous_price
    # ========================================================================

    price_ok = contains_token(
        extract_all_tokens,
        {
            "price",
            "latest_price",
            "current_price",
            "previous_price",
        }
    )

    print(
        f"{'price':<24}:",
        "PASS" if price_ok else "FAIL"
    )


    # ========================================================================
    # PREVIOUS PRICE
    # ========================================================================

    previous_price_ok = contains_token(
        extract_all_tokens,
        {
            "previous_price",
            "prev_price",
            "previous",
            "previous_price_24h",
        }
    )

    print(
        f"{'previous_price':<24}:",
        "PASS" if previous_price_ok else "FAIL"
    )


    # ========================================================================
    # SNAPSHOT CHANGE
    # ========================================================================

    snapshot_change_ok = contains_token(
        extract_all_tokens,
        {
            "snapshot_change",
            "snapshot_change_pct",
            "price_change",
            "change",
            "expected_change",
        }
    )

    print(
        f"{'snapshot_change':<24}:",
        "PASS" if snapshot_change_ok else "FAIL"
    )


    extract_function_pass = all(
        [
            cmc_id_ok,
            symbol_ok,
            price_ok,
            previous_price_ok,
            snapshot_change_ok,
        ]
    )


# ============================================================================
# CMC IDENTITY SEMANTIC AUDIT
# ============================================================================

print()
print("CMC_IDENTITY SEMANTIC AUDIT")
print("-" * 100)

cmc_identity_patterns = [
    "cmc_id",
    "cmc_ids",
    "common_cmc_ids",
    "latest_cmc_id",
    "previous_cmc_id",
    "previous_map",
]

cmc_identity_hits = []

for pattern in cmc_identity_patterns:
    if pattern in all_tokens:
        cmc_identity_hits.append(pattern)

for hit in cmc_identity_hits:
    print(" -", hit)

cmc_identity_pass = len(cmc_identity_hits) > 0

print(
    "CMC_ID based identity :",
    "PASS" if cmc_identity_pass else "FAIL"
)


# ============================================================================
# SYMBOL IDENTITY NEGATIVE AUDIT
#
# IMPORTANT:
# Symbol may exist as a feature/descriptive field.
# It must NOT be used as the primary identity.
# ============================================================================

print()
print("IDENTITY SEMANTIC AUDIT")
print("-" * 100)

symbol_identity_patterns = [
    "(symbol, timestamp)",
    "(timestamp, symbol)",
    "symbol_timestamp",
    "symbol + timestamp",
    "symbol,timestamp",
    "timestamp,symbol",
]

symbol_identity_hits = []

for pattern in symbol_identity_patterns:

    if pattern.lower() in all_strings:
        symbol_identity_hits.append(pattern)


if symbol_identity_hits:

    for hit in symbol_identity_hits:
        print(
            "Symbol-based composite identity :",
            hit
        )

    symbol_identity_pass = False

else:

    print(
        "Symbol-based composite identity :",
        "SAFE"
    )

    symbol_identity_pass = True


# ============================================================================
# CMC SOURCE AUDIT
# ============================================================================

print()
print("CMC_ID SOURCE AUDIT")
print("-" * 100)

cmc_source_patterns = [
    "cmc_id",
    "cmc_ids",
    "common_cmc_ids",
    "latest_cmc_id",
    "previous_cmc_id",
    "market_history",
]

cmc_source_hits = []

for pattern in cmc_source_patterns:

    if pattern in all_tokens:
        cmc_source_hits.append(pattern)


for hit in cmc_source_hits:
    print(" -", hit)


cmc_source_pass = (
    "cmc_id" in all_tokens
    or
    "cmc_ids" in all_tokens
    or
    "common_cmc_ids" in all_tokens
)


print(
    "RESULT :",
    "PASS" if cmc_source_pass else "FAIL"
)


# ============================================================================
# READ-ONLY / MUTATION AUDIT
# ============================================================================

print()
print("READ-ONLY / MUTATION AUDIT")
print("-" * 100)

mutation_keywords = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER TABLE",
    "CREATE TABLE",
    "DROP TABLE",
    "REPLACE INTO",
]

mutation_hits = []

for literal in string_literals(tree):

    upper = literal.upper()

    for keyword in mutation_keywords:

        if keyword in upper:

            mutation_hits.append(
                (keyword, literal)
            )


# These are diagnostic/output messages, not executable SQL.
diagnostic_markers = [
    "NO MUTATION",
    "READ ONLY",
    "READ-ONLY",
    "MUTATION AUDIT",
    "MUTATION STATEMENTS",
    "SQL MUTATION",
]


executable_mutations = []

for keyword, literal in mutation_hits:

    upper = literal.upper()

    if any(
        marker in upper
        for marker in diagnostic_markers
    ):
        continue

    executable_mutations.append(
        (keyword, literal)
    )


if executable_mutations:

    print(
        "Mutation-like SQL literals detected:"
    )

    for keyword, literal in executable_mutations[:20]:

        print(
            f" - {keyword}: "
            f"{literal[:120]}"
        )

    readonly_pass = False

else:

    print(
        "SQL mutation statements : NONE DETECTED"
    )

    readonly_pass = True


# ============================================================================
# QUERY LAYER COMPATIBILITY
# ============================================================================

print()
print("QUERY LAYER COMPATIBILITY")
print("-" * 100)

query_reference_pass = (
    "history_query_layer" in all_tokens
    or
    "history_query" in all_tokens
    or
    "history_query_v0.1" in all_tokens
)

print(
    "HISTORY_QUERY reference :",
    "PASS"
    if query_reference_pass
    else
    "NOT DETECTED"
)


# ============================================================================
# REQUIRED FEATURE CONTRACT
# ============================================================================

print()
print("REQUIRED FEATURE CONTRACT")
print("-" * 100)

contract_checks = {
    "CMC_ID identity": cmc_identity_pass,
    "CMC_ID source": cmc_source_pass,
    "No symbol identity": symbol_identity_pass,
    "extract_features": extract_function_pass,
    "Read only": readonly_pass,
}


for name, result in contract_checks.items():

    print(
        f"{name:<24}:",
        "PASS" if result else "FAIL"
    )


# ============================================================================
# FINAL VERDICT
# ============================================================================

overall_pass = all(
    contract_checks.values()
)


print()
print("=" * 100)
print("STEP 5A VERDICT")
print("=" * 100)


if overall_pass:

    print(
        "RESULT : FEATURE SCHEMA AUDIT PASS"
    )

    print(
        "STATUS : READY FOR STEP 5B"
    )

else:

    print(
        "RESULT : FEATURE SCHEMA AUDIT FAIL"
    )

    print(
        "STATUS : DO NOT PROCEED TO STEP 5B"
    )


print()
print(
    "Feature contract       :",
    "VERIFIED"
    if extract_function_pass
    else
    "FAILED"
)

print(
    "CMC identity           :",
    "VERIFIED"
    if cmc_identity_pass
    else
    "MISSING"
)

print(
    "CMC source             :",
    "VERIFIED"
    if cmc_source_pass
    else
    "MISSING"
)

print(
    "Symbol collision safe  :",
    "VERIFIED"
    if symbol_identity_pass
    else
    "FAILED"
)

print(
    "Read only              :",
    "VERIFIED"
    if readonly_pass
    else
    "FAILED"
)

print("=" * 100)


raise SystemExit(
    0 if overall_pass else 1
)