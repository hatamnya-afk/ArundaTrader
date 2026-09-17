import ast
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

ANALYSIS_FILE = BASE_DIR / "history_analysis_engine.py"
FEATURE_FILE = BASE_DIR / "history_feature_extractor.py"
QUERY_FILE = BASE_DIR / "history_query_layer.py"
DB_FILE = BASE_DIR / "arunda.db"


EXPECTED_FEATURE_FIELDS = {
    "cmc_id",
    "symbol",
    "price",
    "previous_price",
    "snapshot_change",
}


FORBIDDEN_IDENTITY_PATTERNS = {
    "symbol, timestamp",
    "symbol,timestamp",
    "timestamp, symbol",
    "timestamp,symbol",
    "symbol + timestamp",
    "timestamp + symbol",
}


MUTATION_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "alter",
    "drop",
    "create",
    "replace",
}


def separator(char="-", length=100):
    print(char * length)


def read_source(path):
    if not path.exists():
        return None

    return path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )


def parse_ast(path):
    source = read_source(path)

    if source is None:
        return None, "FILE NOT FOUND"

    try:
        return ast.parse(
            source,
            filename=str(path),
        ), None

    except SyntaxError as exc:
        return None, f"{type(exc).__name__}: {exc}"


def parse_ast_from_source(source):
    if source is None:
        return None, "SOURCE NOT AVAILABLE"

    try:
        return ast.parse(source), None

    except SyntaxError as exc:
        return None, f"{type(exc).__name__}: {exc}"


def function_inventory(tree):
    if tree is None:
        return []

    return sorted(
        node.name
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
    )


def collect_string_constants(tree):
    values = set()

    if tree is None:
        return values

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                values.add(node.value.lower())

    return values


def collect_names(tree):
    values = set()

    if tree is None:
        return values

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            values.add(node.id.lower())

    return values


def source_contains_any(source, patterns):
    if not source:
        return set()

    lowered = source.lower()

    return {
        pattern
        for pattern in patterns
        if pattern.lower() in lowered
    }


def find_extract_features_contract(feature_source):
    if not feature_source:
        return set()

    source_lower = feature_source.lower()

    aliases = {
        "cmc_id": [
            "cmc_id",
            "cmc_ids",
            "common_cmc_ids",
        ],

        "symbol": [
            "symbol",
            "latest_symbol",
            "previous_symbol",
        ],

        "price": [
            "price",
            "latest_price",
        ],

        "previous_price": [
            "previous_price",
        ],

        "snapshot_change": [
            "snapshot_change",
            "snapshot_change_pct",
        ],
    }

    found = set()

    for field, candidates in aliases.items():

        if any(
            candidate.lower() in source_lower
            for candidate in candidates
        ):
            found.add(field)

    return found


def find_analysis_consumed_fields(analysis_source):

    if not analysis_source:
        return set()

    lowered = analysis_source.lower()

    candidates = {
        "cmc_id",
        "symbol",
        "price",
        "previous_price",
        "snapshot_change",
        "snapshot_change_pct",
        "change_1h",
        "change_24h",
        "change_7d",
        "market_cap",
        "volume_24h",
        "rank",
        "latest_price",
        "previous_volume",
        "previous_volume_24h",
    }

    return {
        candidate
        for candidate in candidates
        if candidate.lower() in lowered
    }


def find_feature_access_patterns(analysis_source):

    if not analysis_source:
        return []

    lines = analysis_source.splitlines()

    matches = []

    for number, line in enumerate(
        lines,
        start=1,
    ):

        lowered = line.lower()

        if (
            "feature[" in lowered
            or "features[" in lowered
            or "feature.get(" in lowered
            or "features.get(" in lowered
        ):

            matches.append(
                (
                    number,
                    line.strip(),
                )
            )

    return matches


def extract_sql_text(node):

    if not isinstance(node, ast.Call):
        return None

    if not isinstance(
        node.func,
        ast.Attribute,
    ):
        return None

    if node.func.attr.lower() not in {
        "execute",
        "executemany",
        "executescript",
    }:
        return None

    if not node.args:
        return None

    argument = node.args[0]

    if isinstance(
        argument,
        ast.Constant,
    ):
        if isinstance(
            argument.value,
            str,
        ):
            return argument.value

    if isinstance(
        argument,
        ast.JoinedStr,
    ):
        parts = []

        for value in argument.values:

            if isinstance(
                value,
                ast.Constant,
            ):
                if isinstance(
                    value.value,
                    str,
                ):
                    parts.append(value.value)

        return " ".join(parts)

    return None


def audit_sql_mutations(source):

    if not source:
        return [
            "SOURCE_NOT_AVAILABLE"
        ]

    tree, error = parse_ast_from_source(
        source
    )

    if error:
        return [
            "AST_PARSE_ERROR"
        ]

    mutations = []

    for node in ast.walk(tree):

        sql = extract_sql_text(node)

        if not sql:
            continue

        normalized = (
            sql
            .strip()
            .lower()
        )

        tokens = normalized.split()

        if not tokens:
            continue

        first_word = tokens[0]

        if first_word in MUTATION_KEYWORDS:

            mutations.append(
                f"{first_word.upper()} SQL"
            )

    return mutations


def audit_database_read_only():

    if not DB_FILE.exists():

        return {
            "exists": False,
            "rows": None,
            "snapshots": None,
            "cmc_ids": None,
            "duplicate_ids": None,
        }

    conn = sqlite3.connect(
        f"file:{DB_FILE}?mode=ro",
        uri=True,
    )

    try:

        table = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name='market_history'
            """
        ).fetchone()

        if table is None:

            return {
                "exists": True,
                "rows": None,
                "snapshots": None,
                "cmc_ids": None,
                "duplicate_ids": None,
            }

        rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_history
            """
        ).fetchone()[0]

        snapshots = conn.execute(
            """
            SELECT COUNT(DISTINCT timestamp)
            FROM market_history
            """
        ).fetchone()[0]

        cmc_ids = conn.execute(
            """
            SELECT COUNT(DISTINCT cmc_id)
            FROM market_history
            """
        ).fetchone()[0]

        duplicate_ids = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    timestamp,
                    cmc_id
                FROM market_history
                GROUP BY
                    timestamp,
                    cmc_id
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        return {
            "exists": True,
            "rows": rows,
            "snapshots": snapshots,
            "cmc_ids": cmc_ids,
            "duplicate_ids": duplicate_ids,
        }

    finally:
        conn.close()


def audit_query_reference(
    analysis_source
):

    if not analysis_source:
        return False

    lowered = analysis_source.lower()

    return (
        "history_query" in lowered
        or
        "history_query_v0.1" in lowered
        or
        "history query" in lowered
    )


def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — DEV-06 — STEP 7A"
    )
    print(
        "ANALYSIS CONSUMER CONTRACT AUDIT"
    )
    print("=" * 100)

    print()
    print("MODE")
    separator()

    print(
        "Database mutation : NONE"
    )

    print(
        "Production write  : NONE"
    )

    print(
        "Audit mode        : READ ONLY"
    )

    # ================================================================
    # FILE VALIDATION
    # ================================================================

    print()
    print("FILE VALIDATION")
    separator()

    files = {
        "Analysis Engine":
            ANALYSIS_FILE,

        "Feature Extractor":
            FEATURE_FILE,

        "Query Layer":
            QUERY_FILE,
    }

    parsed = {}

    for label, path in files.items():

        exists = path.exists()

        print(
            f"{label:<22} : ",
            end="",
        )

        if not exists:

            print("FAIL")

            parsed[label] = None

            continue

        print("PASS")

        tree, error = parse_ast(
            path
        )

        print(
            f"{'':25}"
            f"AST Parse       : ",
            "PASS"
            if tree is not None
            else "FAIL",
        )

        if error:

            print(
                f"{'':25}"
                f"Error           : {error}"
            )

        parsed[label] = tree

    # ================================================================
    # FUNCTION INVENTORY
    # ================================================================

    print()
    print(
        "ANALYSIS ENGINE FUNCTION INVENTORY"
    )
    separator()

    analysis_tree = parsed[
        "Analysis Engine"
    ]

    functions = function_inventory(
        analysis_tree
    )

    if functions:

        for name in functions:
            print(" -", name)

    else:

        print(
            " - NONE DETECTED"
        )

    # ================================================================
    # SOURCES
    # ================================================================

    analysis_source = read_source(
        ANALYSIS_FILE
    )

    feature_source = read_source(
        FEATURE_FILE
    )

    query_source = read_source(
        QUERY_FILE
    )

    # ================================================================
    # FEATURE CONTRACT
    # ================================================================

    feature_fields = (
        find_extract_features_contract(
            feature_source
        )
    )

    print()
    print(
        "FEATURE EXTRACTOR CONTRACT"
    )
    separator()

    print(
        "Expected feature fields"
    )

    for field in sorted(
        EXPECTED_FEATURE_FIELDS
    ):
        print(
            " -",
            field,
        )

    print()
    print(
        "Detected feature semantics"
    )

    for field in sorted(
        feature_fields
    ):
        print(
            " -",
            field,
        )

    feature_contract_pass = (
        EXPECTED_FEATURE_FIELDS
        .issubset(
            feature_fields
        )
    )

    print()
    print(
        "Feature extractor contract :",
        "PASS"
        if feature_contract_pass
        else "FAIL",
    )

    # ================================================================
    # ANALYSIS CONSUMPTION
    # ================================================================

    consumed_fields = (
        find_analysis_consumed_fields(
            analysis_source
        )
    )

    print()
    print(
        "ANALYSIS FEATURE CONSUMPTION"
    )
    separator()

    if consumed_fields:

        for field in sorted(
            consumed_fields
        ):
            print(
                " -",
                field,
            )

    else:

        print(
            " - NONE DETECTED"
        )

    required_consumed = {
        "cmc_id",
        "symbol",
        "price",
        "previous_price",
        "snapshot_change",
    }

    missing_consumed = (
        required_consumed
        - consumed_fields
    )

    additional_consumed = (
        consumed_fields
        - required_consumed
    )

    print()
    print(
        "Required feature fields consumed :",
        "PASS"
        if not missing_consumed
        else "FAIL",
    )

    if missing_consumed:

        print(
            "Missing:",
            ", ".join(
                sorted(
                    missing_consumed
                )
            ),
        )

    if additional_consumed:

        print()
        print(
            "Additional feature references detected:"
        )

        for field in sorted(
            additional_consumed
        ):
            print(
                " -",
                field,
            )

    # ================================================================
    # ACCESS PATTERN
    # ================================================================

    print()
    print(
        "FEATURE ACCESS PATTERN AUDIT"
    )
    separator()

    access_patterns = (
        find_feature_access_patterns(
            analysis_source
        )
    )

    if access_patterns:

        for number, line in access_patterns:

            print(
                f"L{number:<5} {line}"
            )

    else:

        print(
            "No dictionary feature access detected."
        )

    # ================================================================
    # IDENTITY
    # ================================================================

    print()
    print(
        "IDENTITY CONTRACT AUDIT"
    )
    separator()

    analysis_names = collect_names(
        analysis_tree
    )

    analysis_strings = (
        collect_string_constants(
            analysis_tree
        )
    )

    cmc_detected = (
        "cmc_id"
        in analysis_names
        or
        "cmc_id"
        in analysis_strings
        or
        "cmc_ids"
        in analysis_names
        or
        "cmc_ids"
        in analysis_strings
    )

    symbol_detected = (
        "symbol"
        in analysis_names
        or
        "symbol"
        in analysis_strings
    )

    timestamp_detected = (
        "timestamp"
        in analysis_names
        or
        "timestamp"
        in analysis_strings
    )

    print(
        "CMC_ID identity detected       :",
        "PASS"
        if cmc_detected
        else "FAIL",
    )

    print(
        "Symbol field detected          :",
        "PASS"
        if symbol_detected
        else "WARN",
    )

    print(
        "Timestamp field detected       :",
        "PASS"
        if timestamp_detected
        else "WARN",
    )

    forbidden_patterns = (
        source_contains_any(
            analysis_source,
            FORBIDDEN_IDENTITY_PATTERNS,
        )
    )

    print(
        "Symbol/timestamp identity      :",
        "FAIL"
        if forbidden_patterns
        else "SAFE",
    )

    if forbidden_patterns:

        for pattern in sorted(
            forbidden_patterns
        ):
            print(
                " - FORBIDDEN:",
                pattern,
            )

    # ================================================================
    # QUERY LAYER
    # ================================================================

    print()
    print(
        "QUERY LAYER COMPATIBILITY"
    )
    separator()

    query_pass = (
        audit_query_reference(
            analysis_source
        )
    )

    print(
        "HISTORY_QUERY reference :",
        "PASS"
        if query_pass
        else "FAIL",
    )

    # ================================================================
    # READ ONLY
    # ================================================================

    print()
    print(
        "READ-ONLY / MUTATION AUDIT"
    )
    separator()

    analysis_mutations = (
        audit_sql_mutations(
            analysis_source
        )
    )

    feature_mutations = (
        audit_sql_mutations(
            feature_source
        )
    )

    query_mutations = (
        audit_sql_mutations(
            query_source
        )
    )

    mutations = (
        analysis_mutations
        + feature_mutations
        + query_mutations
    )

    if mutations:

        print(
            "SQL mutation statements : FAIL"
        )

        for mutation in mutations:

            print(
                " -",
                mutation,
            )

        readonly_pass = False

    else:

        print(
            "SQL mutation statements : "
            "NONE DETECTED"
        )

        readonly_pass = True

    # ================================================================
    # DATABASE
    # ================================================================

    print()
    print(
        "DATABASE READ-ONLY FINGERPRINT"
    )
    separator()

    db = audit_database_read_only()

    if not db["exists"]:

        print(
            "Database : FAIL"
        )

        db_pass = False

    elif db["rows"] is None:

        print(
            "market_history : FAIL"
        )

        db_pass = False

    else:

        print(
            f"Rows              : "
            f"{db['rows']}"
        )

        print(
            f"Snapshots         : "
            f"{db['snapshots']}"
        )

        print(
            f"Distinct CMC IDs  : "
            f"{db['cmc_ids']}"
        )

        print(
            f"Duplicate IDs     : "
            f"{db['duplicate_ids']}"
        )

        db_pass = (
            db["duplicate_ids"] == 0
            and db["cmc_ids"] > 0
            and db["rows"] > 0
        )

    print()
    print(
        "DATABASE READ ONLY :",
        "PASS"
        if db_pass
        else "FAIL",
    )

    # ================================================================
    # FINAL CONTRACT
    # ================================================================

    print()
    print(
        "REQUIRED ANALYSIS CONSUMER CONTRACT"
    )
    separator()

    checks = {
        "Feature extractor contract":
            feature_contract_pass,

        "Required feature consumption":
            not missing_consumed,

        "CMC_ID identity":
            cmc_detected,

        "No symbol/timestamp identity":
            not forbidden_patterns,

        "Query layer compatibility":
            query_pass,

        "Read only":
            readonly_pass,

        "Database integrity":
            db_pass,
    }

    for name, status in checks.items():

        print(
            f"{name:<36} :",
            "PASS"
            if status
            else "FAIL",
        )

    overall = all(
        checks.values()
    )

    print()
    print("=" * 100)
    print(
        "STEP 7A VERDICT"
    )
    print("=" * 100)

    if overall:

        print(
            "RESULT : "
            "ANALYSIS CONSUMER CONTRACT AUDIT PASS"
        )

        print(
            "STATUS : "
            "READY FOR STEP 7 ANALYSIS ENGINE VALIDATION"
        )

    else:

        print(
            "RESULT : "
            "ANALYSIS CONSUMER CONTRACT AUDIT FAIL"
        )

        print(
            "STATUS : "
            "DO NOT PROCEED WITH ANALYSIS ENGINE VALIDATION"
        )

    print()
    print(
        "Architecture : PRESERVED"
    )

    print(
        "Database     : READ ONLY"
    )

    print(
        "Writes       : NONE"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()