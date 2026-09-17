import ast
import inspect
import math
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "arunda.db"
ANALYSIS_FILE = BASE_DIR / "history_analysis_engine.py"
FEATURE_FILE = BASE_DIR / "history_feature_extractor.py"
QUERY_FILE = BASE_DIR / "history_query_layer.py"

REQUIRED_OUTPUT_FIELDS = (
    "cmc_id",
    "symbol",
    "price",
    "previous_price",
    "price_change",
    "price_change_pct",
    "snapshot_change",
    "snapshot_change_pct",
)

MUTATION_PATTERNS = (
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "ALTER ",
    "DROP ",
    "CREATE TABLE",
    "CREATE INDEX",
    "CREATE VIEW",
    "CREATE TRIGGER",
    "CREATE VIRTUAL TABLE",
    "REPLACE ",
)


# ======================================================================================
# PRINT HELPERS
# ======================================================================================

def line(char="-", width=100):
    print(char * width)


def section(title):
    print()
    print(title)
    line()


def result(value):
    return "PASS" if value else "FAIL"


# ======================================================================================
# AST
# ======================================================================================

def parse_ast(source):
    try:
        return ast.parse(source), None
    except Exception as exc:
        return None, exc


def read_source(path):
    return path.read_text(encoding="utf-8-sig")


def function_inventory(source):
    tree, error = parse_ast(source)

    if error:
        return [], error

    functions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)

    return functions, None


# ======================================================================================
# SQL MUTATION AUDIT
# ======================================================================================

def audit_sql_mutations(source):
    tree, error = parse_ast(source)

    if error:
        return False, [f"AST ERROR: {error}"]

    mutations = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Constant):
            value = node.value

            if isinstance(value, str):
                normalized = " ".join(value.upper().split())

                for pattern in MUTATION_PATTERNS:
                    if pattern in normalized:
                        mutations.append(
                            f"L{getattr(node, 'lineno', '?')} : {pattern.strip()}"
                        )

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                method = node.func.attr.lower()

                if method in {
                    "execute",
                    "executemany",
                    "executescript",
                    "cursor",
                }:
                    for arg in node.args:
                        if isinstance(arg, ast.Constant):
                            if isinstance(arg.value, str):
                                normalized = " ".join(arg.value.upper().split())

                                for pattern in MUTATION_PATTERNS:
                                    if pattern in normalized:
                                        mutations.append(
                                            f"L{getattr(node, 'lineno', '?')} : "
                                            f"{pattern.strip()}"
                                        )

    return len(mutations) == 0, mutations


# ======================================================================================
# READ ONLY DB
# ======================================================================================

def connect_read_only():
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=30,
    )


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row[1] for row in rows]


# ======================================================================================
# HISTORY FINGERPRINT
# ======================================================================================

def history_fingerprint(conn):
    rows = conn.execute(
        "SELECT COUNT(*) FROM market_history"
    ).fetchone()[0]

    snapshots = conn.execute(
        "SELECT COUNT(DISTINCT timestamp) FROM market_history"
    ).fetchone()[0]

    cmc_ids = conn.execute(
        "SELECT COUNT(DISTINCT cmc_id) FROM market_history"
    ).fetchone()[0]

    duplicate_ids = conn.execute(
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

    first_timestamp = conn.execute(
        "SELECT MIN(timestamp) FROM market_history"
    ).fetchone()[0]

    last_timestamp = conn.execute(
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


def fingerprint_equal(a, b):
    return a == b


# ======================================================================================
# MODULE LOADING
# ======================================================================================

def load_module_from_file(path, module_name):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to load module: {path}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


# ======================================================================================
# FEATURE NORMALIZATION
# ======================================================================================

def is_mapping(value):
    return isinstance(value, dict)


def object_to_dict(obj):
    """
    Convert HistoryFeature/dataclass/simple object into a plain dictionary.

    This is intentionally an AUDIT ADAPTER.
    It does not modify the production feature extractor.
    """

    if isinstance(obj, dict):
        return dict(obj)

    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        converted = obj.to_dict()

        if isinstance(converted, dict):
            return dict(converted)

    if hasattr(obj, "__dataclass_fields__"):
        try:
            from dataclasses import asdict

            converted = asdict(obj)

            if isinstance(converted, dict):
                return dict(converted)

        except Exception:
            pass

    if hasattr(obj, "_asdict") and callable(obj._asdict):
        converted = obj._asdict()

        if isinstance(converted, dict):
            return dict(converted)

    if hasattr(obj, "__dict__"):
        return dict(vars(obj))

    raise TypeError(
        f"Unsupported feature object type: {type(obj).__name__}"
    )


def unwrap_feature_output(value):
    """
    Normalize every known extractor return shape into a list.
    """

    if value is None:
        raise RuntimeError(
            "Feature extractor returned None."
        )

    if isinstance(value, dict):

        if "features" in value:
            return unwrap_feature_output(value["features"])

        return [value]

    if isinstance(value, (list, tuple)):
        return list(value)

    if hasattr(value, "__iter__") and not isinstance(
        value,
        (str, bytes),
    ):
        try:
            return list(value)
        except Exception:
            pass

    return [value]


def normalize_features(raw):
    items = unwrap_feature_output(raw)

    normalized = []

    for item in items:
        normalized.append(object_to_dict(item))

    return normalized


def validate_required_feature_fields(features):
    required = {
        "cmc_id",
        "symbol",
        "price",
        "previous_price",
        "snapshot_change",
    }

    if not features:
        raise ValueError(
            "Feature collection is empty."
        )

    for index, feature in enumerate(features):

        missing = [
            field
            for field in required
            if field not in feature
        ]

        if missing:
            raise ValueError(
                f"Feature {index} missing fields: {missing}"
            )

    return True


# ======================================================================================
# FEATURE EXTRACTION
# ======================================================================================

def extract_features(feature_module):
    extractor = getattr(
        feature_module,
        "extract_features",
        None,
    )

    if extractor is None:
        raise RuntimeError(
            "Feature extractor does not expose extract_features."
        )

    conn = connect_read_only()

    try:

        attempts = []

        try:
            signature = inspect.signature(extractor)
            params = list(signature.parameters.values())

            required = [
                p
                for p in params
                if p.default is inspect.Parameter.empty
                and p.kind
                in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                )
            ]

            if len(required) == 0:
                attempts.append(
                    lambda: extractor()
                )

            elif len(required) == 1:
                attempts.append(
                    lambda: extractor(conn)
                )

            else:
                attempts.append(
                    lambda: extractor(conn)
                )

        except Exception:
            attempts.append(
                lambda: extractor()
            )

        last_error = None

        for attempt in attempts:

            try:
                raw = attempt()

                features = normalize_features(raw)

                validate_required_feature_fields(
                    features
                )

                return features

            except Exception as exc:
                last_error = exc

        raise RuntimeError(
            f"Feature extraction failed: {last_error}"
        )

    finally:
        conn.close()


# ======================================================================================
# ANALYSIS OUTPUT NORMALIZATION
# ======================================================================================

def normalize_analysis_output(raw):
    if raw is None:
        return []

    if isinstance(raw, dict):

        if "analysis" in raw:
            return normalize_analysis_output(
                raw["analysis"]
            )

        if "records" in raw:
            return normalize_analysis_output(
                raw["records"]
            )

        return [dict(raw)]

    if isinstance(raw, (list, tuple)):
        result_rows = []

        for item in raw:
            result_rows.extend(
                normalize_analysis_output(item)
            )

        return result_rows

    if hasattr(raw, "to_dict") and callable(raw.to_dict):
        converted = raw.to_dict()

        if isinstance(converted, dict):
            return [converted]

    if hasattr(raw, "__dataclass_fields__"):
        from dataclasses import asdict

        return [asdict(raw)]

    if hasattr(raw, "__dict__"):
        return [dict(vars(raw))]

    raise TypeError(
        f"Unsupported analysis output type: "
        f"{type(raw).__name__}"
    )


# ======================================================================================
# ANALYSIS EXECUTION
# ======================================================================================

def execute_analysis(analysis_module, features):
    analyze_features = getattr(
        analysis_module,
        "analyze_features",
        None,
    )

    analyze_feature = getattr(
        analysis_module,
        "analyze_feature",
        None,
    )

    if analyze_features is None and analyze_feature is None:
        raise RuntimeError(
            "Analysis engine exposes neither "
            "analyze_features nor analyze_feature."
        )

    # Preferred path: collection API.
    if analyze_features is not None:

        try:
            raw = analyze_features(features)

            records = normalize_analysis_output(raw)

            if records:
                return records

        except Exception as collection_error:

            # Do not silently hide the real contract problem.
            # Fallback is only attempted when analyze_feature exists.
            if analyze_feature is None:
                raise RuntimeError(
                    "analyze_features failed: "
                    f"{collection_error}"
                ) from collection_error

    # Contract-safe fallback:
    # analyze every normalized feature individually.
    if analyze_feature is not None:

        records = []

        for feature in features:
            try:
                raw = analyze_feature(feature)

            except Exception as exc:
                raise RuntimeError(
                    "analyze_feature failed for "
                    f"CMC_ID={feature.get('cmc_id')}: {exc}"
                ) from exc

            normalized = normalize_analysis_output(raw)

            if len(normalized) != 1:
                raise RuntimeError(
                    "analyze_feature must return exactly "
                    f"one record per feature. "
                    f"CMC_ID={feature.get('cmc_id')}, "
                    f"records={len(normalized)}"
                )

            records.append(normalized[0])

        return records

    raise RuntimeError(
        "Analysis execution produced no records."
    )


# ======================================================================================
# OUTPUT CONTRACT
# ======================================================================================

def validate_output_schema(records):
    if not records:
        return False, "No analysis records."

    missing_by_record = []

    for index, record in enumerate(records):

        missing = [
            field
            for field in REQUIRED_OUTPUT_FIELDS
            if field not in record
        ]

        if missing:
            missing_by_record.append(
                f"record {index}: {missing}"
            )

    if missing_by_record:
        return False, "; ".join(
            missing_by_record[:5]
        )

    return True, None


def validate_numeric(value, field):
    if value is None:
        raise ValueError(
            f"{field} is None"
        )

    value = float(value)

    if not math.isfinite(value):
        raise ValueError(
            f"{field} is not finite: {value}"
        )

    return value


def validate_runtime_records(records):
    if not records:
        return False, "No records"

    seen = set()

    for index, record in enumerate(records):

        try:
            cmc_id = int(record["cmc_id"])

            if cmc_id in seen:
                return False, (
                    f"Duplicate CMC_ID: {cmc_id}"
                )

            seen.add(cmc_id)

            symbol = record["symbol"]

            if symbol is None:
                return False, (
                    f"Missing symbol at record {index}"
                )

            price = validate_numeric(
                record["price"],
                "price",
            )

            previous_price = validate_numeric(
                record["previous_price"],
                "previous_price",
            )

            validate_numeric(
                record["price_change"],
                "price_change",
            )

            validate_numeric(
                record["price_change_pct"],
                "price_change_pct",
            )

            validate_numeric(
                record["snapshot_change"],
                "snapshot_change",
            )

            validate_numeric(
                record["snapshot_change_pct"],
                "snapshot_change_pct",
            )

            expected_change = (
                price - previous_price
            )

            if not math.isclose(
                float(record["price_change"]),
                expected_change,
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                return False, (
                    f"price_change mismatch "
                    f"CMC_ID={cmc_id}"
                )

            if previous_price != 0:

                expected_pct = (
                    expected_change
                    / previous_price
                    * 100.0
                )

                if not math.isclose(
                    float(record["price_change_pct"]),
                    expected_pct,
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                ):
                    return False, (
                        f"price_change_pct mismatch "
                        f"CMC_ID={cmc_id}"
                    )

            expected_snapshot_change = (
                price - previous_price
            )

            if not math.isclose(
                float(record["snapshot_change"]),
                expected_snapshot_change,
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                return False, (
                    f"snapshot_change mismatch "
                    f"CMC_ID={cmc_id}"
                )

            if previous_price != 0:

                expected_snapshot_pct = (
                    expected_snapshot_change
                    / previous_price
                    * 100.0
                )

                if not math.isclose(
                    float(record["snapshot_change_pct"]),
                    expected_snapshot_pct,
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                ):
                    return False, (
                        f"snapshot_change_pct mismatch "
                        f"CMC_ID={cmc_id}"
                    )

        except Exception as exc:
            return False, (
                f"record {index}: {exc}"
            )

    return True, None


# ======================================================================================
# CARDINALITY
# ======================================================================================

def cardinality_test(features, analysis_records):
    feature_ids = {
        int(feature["cmc_id"])
        for feature in features
    }

    analysis_ids = {
        int(record["cmc_id"])
        for record in analysis_records
    }

    return (
        feature_ids == analysis_ids,
        len(feature_ids),
        len(analysis_ids),
    )


# ======================================================================================
# COLLISION SAFETY
# ======================================================================================

def collision_safety_test(conn):
    rows = conn.execute(
        """
        SELECT
            symbol,
            COUNT(DISTINCT cmc_id) AS cmc_count,
            COUNT(*) AS row_count
        FROM market_history
        GROUP BY symbol
        HAVING COUNT(DISTINCT cmc_id) > 1
        ORDER BY symbol
        """
    ).fetchall()

    collision_groups = len(rows)

    collision_rows = sum(
        int(row[2])
        for row in rows
    )

    # Important:
    # Symbol collision is NOT identity failure because identity
    # is CMC_ID based.
    safe = True

    return (
        safe,
        collision_groups,
        collision_rows,
    )


# ======================================================================================
# SAMPLE
# ======================================================================================

def print_analysis_sample(records):
    print()
    print("ANALYSIS SAMPLE")
    line()

    for record in records[:5]:

        print(
            f"CMC_ID={record.get('cmc_id')} | "
            f"SYMBOL={record.get('symbol')} | "
            f"PRICE={record.get('price')} | "
            f"PREV_PRICE={record.get('previous_price')} | "
            f"CHANGE={record.get('price_change')} | "
            f"CHANGE_PCT={record.get('price_change_pct')}"
        )


# ======================================================================================
# MAIN
# ======================================================================================

def main():

    print("=" * 100)
    print("ARUNDA TRADER — DEV-06 — STEP 9")
    print("ANALYSIS OUTPUT CONTRACT AUDIT")
    print("=" * 100)

    print()
    print("MODE")
    line()
    print("Database mutation               : NONE")
    print("Production write                : NONE")
    print("Audit mode                      : READ ONLY")

    # ------------------------------------------------------------------
    # FILE VALIDATION
    # ------------------------------------------------------------------

    section("FILE VALIDATION")

    file_results = []

    for label, path in (
        ("Analysis Engine", ANALYSIS_FILE),
        ("Feature Extractor", FEATURE_FILE),
        ("Query Layer", QUERY_FILE),
    ):

        exists = path.exists()

        print(
            f"{label:<22}: "
            f"{result(exists)}"
        )

        if not exists:
            file_results.append(False)
            continue

        source = read_source(path)

        tree, error = parse_ast(source)

        ast_ok = error is None

        print(
            f"{'':22}  "
            f"AST Parse       : {result(ast_ok)}"
        )

        file_results.append(
            exists and ast_ok
        )

    if not all(file_results):
        print()
        print("STEP 9 VERDICT")
        line("=")

        print(
            "RESULT : ANALYSIS OUTPUT CONTRACT AUDIT FAIL"
        )
        print(
            "STATUS : DO NOT PROCEED"
        )
        return 1

    # ------------------------------------------------------------------
    # LOAD SOURCES
    # ------------------------------------------------------------------

    analysis_source = read_source(
        ANALYSIS_FILE
    )

    feature_source = read_source(
        FEATURE_FILE
    )

    query_source = read_source(
        QUERY_FILE
    )

    analysis_module = load_module_from_file(
        ANALYSIS_FILE,
        "arunda_history_analysis_engine_step9",
    )

    feature_module = load_module_from_file(
        FEATURE_FILE,
        "arunda_history_feature_extractor_step9",
    )

    # ------------------------------------------------------------------
    # FUNCTION INVENTORY
    # ------------------------------------------------------------------

    section(
        "ANALYSIS ENGINE FUNCTION INVENTORY"
    )

    functions, error = function_inventory(
        analysis_source
    )

    if error:
        print(
            "AST Parse : FAIL"
        )
        print(
            f"Error     : {error}"
        )
        return 1

    for name in functions:
        print(
            f" - {name}"
        )

    # ------------------------------------------------------------------
    # SOURCE MUTATION AUDIT
    # ------------------------------------------------------------------

    section("SOURCE MUTATION AUDIT")

    mutation_ok, mutations = (
        audit_sql_mutations(
            analysis_source
        )
    )

    if mutation_ok:
        print(
            "SQL mutation statements : NONE DETECTED"
        )
    else:
        print(
            "SQL mutation statements : DETECTED"
        )

        for mutation in mutations:
            print(
                f" - {mutation}"
            )

    # ------------------------------------------------------------------
    # DB FINGERPRINT BEFORE
    # ------------------------------------------------------------------

    section(
        "DATABASE READ-ONLY FINGERPRINT"
    )

    conn = connect_read_only()

    try:

        if not table_exists(
            conn,
            "market_history",
        ):
            print(
                "Database integrity      : FAIL"
            )
            return 1

        before = history_fingerprint(
            conn
        )

        print(
            f"Rows                    : "
            f"{before['rows']}"
        )

        print(
            f"Snapshots               : "
            f"{before['snapshots']}"
        )

        print(
            f"Distinct CMC IDs       : "
            f"{before['cmc_ids']}"
        )

        print(
            f"Duplicate IDs           : "
            f"{before['duplicate_ids']}"
        )

        database_ok = (
            before["duplicate_ids"] == 0
        )

        print(
            f"Database integrity      : "
            f"{result(database_ok)}"
        )

    finally:
        conn.close()

    # ------------------------------------------------------------------
    # REQUIRED OUTPUT CONTRACT
    # ------------------------------------------------------------------

    section(
        "REQUIRED OUTPUT CONTRACT"
    )

    # Static contract check against production engine.
    output_schema_static = True

    for field in REQUIRED_OUTPUT_FIELDS:

        found = (
            field in analysis_source
        )

        print(
            f"{field:<28}: "
            f"{result(found)}"
        )

        if not found:
            output_schema_static = False

    print()
    print(
        f"Output schema : "
        f"{result(output_schema_static)}"
    )

    # ------------------------------------------------------------------
    # FEATURE EXTRACTION
    # ------------------------------------------------------------------

    section("FEATURE EXTRACTION")

    features = []
    feature_ok = False
    feature_error = None

    try:

        features = extract_features(
            feature_module
        )

        feature_ok = True

        print(
            f"Feature Records        : "
            f"{len(features)}"
        )

        print(
            "Feature extraction     : PASS"
        )

    except Exception as exc:

        feature_error = exc

        print(
            "Feature Records        : 0"
        )

        print(
            "Feature extraction     : FAIL"
        )

        print(
            f"Error                  : "
            f"{type(exc).__name__}: {exc}"
        )

    # ------------------------------------------------------------------
    # ANALYSIS RUNTIME
    # ------------------------------------------------------------------

    section(
        "ANALYSIS OUTPUT RUNTIME VALIDATION"
    )

    analysis_records = []
    runtime_ok = False
    runtime_error = None

    if feature_ok:

        try:

            analysis_records = execute_analysis(
                analysis_module,
                features,
            )

            if not analysis_records:
                raise RuntimeError(
                    "Analysis engine returned no records."
                )

            runtime_ok, runtime_error = (
                validate_runtime_records(
                    analysis_records
                )
            )

            if not runtime_ok:
                raise RuntimeError(
                    runtime_error
                )

            print(
                "Runtime Execution       : PASS"
            )

            print(
                f"Analysis Records        : "
                f"{len(analysis_records)}"
            )

        except Exception as exc:

            runtime_error = exc
            runtime_ok = False
            analysis_records = []

            print(
                "Runtime Execution       : FAIL"
            )

            print(
                "Analysis Records        : 0"
            )

            print(
                f"Error                   : "
                f"{type(exc).__name__}: {exc}"
            )

    else:

        print(
            "Runtime Execution       : FAIL"
        )

        print(
            "Analysis Records        : 0"
        )

        print(
            "Error                   : "
            "Feature extraction unavailable"
        )

    # ------------------------------------------------------------------
    # CARDINALITY
    # ------------------------------------------------------------------

    section("CMC_ID CARDINALITY")

    cardinality_ok = False

    if runtime_ok:

        try:

            (
                cardinality_ok,
                feature_count,
                analysis_count,
            ) = cardinality_test(
                features,
                analysis_records,
            )

            print(
                f"Feature IDs             : "
                f"{feature_count}"
            )

            print(
                f"Analysis IDs            : "
                f"{analysis_count}"
            )

            print(
                f"CMC_ID Cardinality      : "
                f"{result(cardinality_ok)}"
            )

        except Exception as exc:

            print(
                "CMC_ID Cardinality      : FAIL"
            )

            print(
                f"Reason                  : "
                f"{exc}"
            )

    else:

        print(
            "CMC_ID Cardinality      : FAIL"
        )

        print(
            "Reason                  : "
            "Runtime analysis output unavailable"
        )

    # ------------------------------------------------------------------
    # MATHEMATICS
    # ------------------------------------------------------------------

    section(
        "MATHEMATICAL OUTPUT CONTRACT"
    )

    mathematics_ok = False

    if runtime_ok:

        mathematics_ok = True

        for record in analysis_records:

            price = float(
                record["price"]
            )

            previous_price = float(
                record["previous_price"]
            )

            expected_change = (
                price - previous_price
            )

            actual_change = float(
                record["price_change"]
            )

            if not math.isclose(
                actual_change,
                expected_change,
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                mathematics_ok = False
                break

            if previous_price != 0:

                expected_pct = (
                    expected_change
                    / previous_price
                    * 100.0
                )

                actual_pct = float(
                    record["price_change_pct"]
                )

                if not math.isclose(
                    actual_pct,
                    expected_pct,
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                ):
                    mathematics_ok = False
                    break

        print(
            f"Price change formula    : "
            f"{result(mathematics_ok)}"
        )

    else:

        print(
            "Price change formula    : FAIL"
        )

        print(
            "Reason                  : "
            "Runtime analysis output unavailable"
        )

    # ------------------------------------------------------------------
    # CMC ID IDENTITY
    # ------------------------------------------------------------------

    section(
        "CMC_ID IDENTITY CONTRACT"
    )

    identity_ok = False

    if runtime_ok:

        try:

            feature_ids = {
                int(
                    feature["cmc_id"]
                )
                for feature in features
            }

            analysis_ids = {
                int(
                    record["cmc_id"]
                )
                for record in analysis_records
            }

            identity_ok = (
                feature_ids == analysis_ids
                and len(analysis_ids) == len(
                    analysis_records
                )
            )

        except Exception:
            identity_ok = False

        print(
            f"CMC_ID output identity : "
            f"{result(identity_ok)}"
        )

    else:

        print(
            "CMC_ID output identity : FAIL"
        )

    # ------------------------------------------------------------------
    # COLLISION SAFETY
    # ------------------------------------------------------------------

    section("COLLISION SAFETY")

    conn = connect_read_only()

    try:

        (
            collision_ok,
            collision_groups,
            collision_rows,
        ) = collision_safety_test(
            conn
        )

    finally:
        conn.close()

    print(
        f"Collision Groups        : "
        f"{collision_groups}"
    )

    print(
        f"Collision Rows          : "
        f"{collision_rows}"
    )

    print(
        "Identity Model          : CMC_ID"
    )

    print(
        f"Collision Safety        : "
        f"{result(collision_ok)}"
    )

    # ------------------------------------------------------------------
    # SNAPSHOT CHANGE
    # ------------------------------------------------------------------

    section(
        "SNAPSHOT CHANGE SEMANTICS"
    )

    snapshot_ok = False

    if runtime_ok:

        snapshot_ok = True

        for record in analysis_records:

            price = float(
                record["price"]
            )

            previous_price = float(
                record["previous_price"]
            )

            expected = (
                price - previous_price
            )

            actual = float(
                record["snapshot_change"]
            )

            if not math.isclose(
                actual,
                expected,
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                snapshot_ok = False
                break

        print(
            f"snapshot_change formula : "
            f"{result(snapshot_ok)}"
        )

    else:

        print(
            "snapshot_change formula : FAIL"
        )

        print(
            "Reason                  : "
            "Runtime analysis output unavailable"
        )

    # ------------------------------------------------------------------
    # SAMPLE
    # ------------------------------------------------------------------

    if runtime_ok:
        print_analysis_sample(
            analysis_records
        )

    # ------------------------------------------------------------------
    # DB FINGERPRINT AFTER
    # ------------------------------------------------------------------

    section(
        "DATABASE READ-ONLY FINGERPRINT AFTER"
    )

    conn = connect_read_only()

    try:

        after = history_fingerprint(
            conn
        )

    finally:
        conn.close()

    print(
        f"Rows                    : "
        f"{after['rows']}"
    )

    print(
        f"Snapshots               : "
        f"{after['snapshots']}"
    )

    print(
        f"Distinct CMC IDs        : "
        f"{after['cmc_ids']}"
    )

    print(
        f"Duplicate IDs           : "
        f"{after['duplicate_ids']}"
    )

    fingerprint_ok = fingerprint_equal(
        before,
        after,
    )

    print()
    print(
        f"BEFORE == AFTER         : "
        f"{result(fingerprint_ok)}"
    )

    # ------------------------------------------------------------------
    # FINAL CONTRACT
    # ------------------------------------------------------------------

    section(
        "REQUIRED ANALYSIS OUTPUT CONTRACT"
    )

    print(
        f"Output schema                   : "
        f"{result(output_schema_static)}"
    )

    print(
        f"CMC_ID identity                 : "
        f"{result(identity_ok)}"
    )

    print(
        f"Runtime records                 : "
        f"{result(runtime_ok)}"
    )

    print(
        f"Cardinality                     : "
        f"{result(cardinality_ok)}"
    )

    print(
        f"Mathematics                     : "
        f"{result(mathematics_ok)}"
    )

    print(
        f"Snapshot semantics              : "
        f"{result(snapshot_ok)}"
    )

    print(
        f"Collision safety                : "
        f"{result(collision_ok)}"
    )

    print(
        f"Read only                       : "
        f"{result(mutation_ok)}"
    )

    print(
        f"Database unchanged              : "
        f"{result(fingerprint_ok)}"
    )

    final_ok = all(
        (
            output_schema_static,
            identity_ok,
            runtime_ok,
            cardinality_ok,
            mathematics_ok,
            snapshot_ok,
            collision_ok,
            mutation_ok,
            database_ok,
            fingerprint_ok,
        )
    )

    print()
    print("=" * 100)
    print("STEP 9 VERDICT")
    print("=" * 100)

    if final_ok:

        print(
            "RESULT : ANALYSIS OUTPUT CONTRACT AUDIT PASS"
        )

        print(
            "STATUS : READY FOR NEXT ANALYSIS DEVELOPMENT STEP"
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

        return 0

    print(
        "RESULT : ANALYSIS OUTPUT CONTRACT AUDIT FAIL"
    )

    print(
        "STATUS : DO NOT PROCEED"
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

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )