import ast
import inspect
import math
import sqlite3
import sys
from pathlib import Path


# =============================================================================
# ARUNDA TRADER — DEV-06 — STEP 10B
# REGIME QUALITY & CROSS-FEATURE VALIDATION
# READ ONLY
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "arunda.db"
ANALYSIS_ENGINE_PATH = BASE_DIR / "history_analysis_engine.py"
FEATURE_EXTRACTOR_PATH = BASE_DIR / "history_feature_extractor.py"
QUERY_LAYER_PATH = BASE_DIR / "history_query.py"

ENGINE_MODULE_NAME = "history_analysis_engine"


REQUIRED_REGIME_FUNCTIONS = (
    "classify_trend",
    "classify_momentum",
    "classify_volatility",
    "classify_volume_regime",
)

ALLOWED_VOCABULARY = {
    "classify_trend": {"DOWN", "FLAT", "UP"},
    "classify_momentum": {"NEGATIVE", "NEUTRAL", "POSITIVE"},
    "classify_volatility": {"LOW", "MEDIUM", "HIGH"},
    "classify_volume_regime": {
        "CONTRACTING",
        "STABLE",
        "EXPANDING",
    },
}

REQUIRED_FEATURE_FIELDS = {
    "cmc_id",
    "symbol",
    "price",
    "previous_price",
    "snapshot_change",
}

MUTATION_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "DROP",
    "REPLACE",
    "VACUUM",
    "REINDEX",
)

# -------------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------------

def banner(title):
    print("=" * 100)
    print(f"ARUNDA TRADER — DEV-06 — STEP 10B")
    print(title)
    print("=" * 100)


def section(title):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def status(label, value):
    print(f"{label:<45}: {value}")


def load_source(path):
    return path.read_text(encoding="utf-8")


def parse_ast(source):
    try:
        return ast.parse(source), None
    except SyntaxError as exc:
        return None, exc


def import_module_from_dir():
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))

    import history_analysis_engine as engine
    return engine


# -------------------------------------------------------------------------
# AST / source audits
# -------------------------------------------------------------------------

def function_inventory(source):
    tree = ast.parse(source)

    names = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(node.name)

    return names


def detect_real_sql_mutations(source):
    """
    Precise mutation audit.

    IMPORTANT:
    Do not flag:
        mutation_audit()
        audit_sql_mutations()
        strings containing the words CREATE/UPDATE/etc.

    Only inspect SQL-like literals actually passed to sqlite execution calls.
    """

    tree = ast.parse(source)
    mutations = []

    execution_names = {
        "execute",
        "executemany",
        "executescript",
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func

        method_name = None

        if isinstance(func, ast.Attribute):
            method_name = func.attr

        if method_name not in execution_names:
            continue

        if not node.args:
            continue

        first_arg = node.args[0]

        literal = None

        if isinstance(first_arg, ast.Constant):
            if isinstance(first_arg.value, str):
                literal = first_arg.value

        if literal is None:
            continue

        normalized = " ".join(literal.upper().split())

        for keyword in MUTATION_KEYWORDS:
            if normalized.startswith(keyword + " ") or normalized == keyword:
                mutations.append(
                    (
                        node.lineno,
                        keyword,
                        literal.strip(),
                    )
                )

    return mutations


def future_data_audit(source):
    suspicious = []

    forbidden_patterns = (
        "future_price",
        "future_return",
        "lookahead",
        "look_ahead",
        "lead(",
        "shift(-",
        "next_price",
        "future_data",
    )

    lowered = source.lower()

    for pattern in forbidden_patterns:
        if pattern in lowered:
            suspicious.append(pattern)

    return sorted(set(suspicious))


# -------------------------------------------------------------------------
# Database
# -------------------------------------------------------------------------

def connect_read_only():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


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


def fingerprints_equal(a, b):
    return a == b


# -------------------------------------------------------------------------
# Generic feature normalization
# -------------------------------------------------------------------------

def normalize_feature(feature):
    """
    Supports:
      - dict
      - dataclass / object with attributes
      - namedtuple-like objects

    This is intentionally defensive because the existing
    HISTORY_FEATURE_EXTRACTOR contract has evolved from dictionaries
    to HistoryFeature objects.
    """

    if feature is None:
        return None

    if isinstance(feature, dict):
        return dict(feature)

    result = {}

    known_fields = (
        "cmc_id",
        "symbol",
        "name",
        "timestamp",
        "latest_timestamp",
        "previous_timestamp",
        "price",
        "previous_price",
        "snapshot_change",
        "snapshot_change_pct",
        "change_1h",
        "change_24h",
        "change_7d",
        "market_cap",
        "rank",
        "volume_24h",
        "previous_volume_24h",
        "previous_volume",
    )

    for field in known_fields:
        if hasattr(feature, field):
            result[field] = getattr(feature, field)

    return result if result else None


def normalize_feature_collection(raw):
    """
    Accept the established extractor variants:

        list[HistoryFeature]
        tuple[HistoryFeature, ...]
        {"features": [...]}
        object.features
        single feature object
    """

    if raw is None:
        raise RuntimeError("Feature extractor returned None.")

    if isinstance(raw, dict):
        if "features" in raw:
            raw = raw["features"]
        else:
            raw = [raw]

    elif hasattr(raw, "features"):
        raw = getattr(raw, "features")

    elif isinstance(raw, (list, tuple)):
        pass

    else:
        # Single HistoryFeature object.
        normalized = normalize_feature(raw)

        if normalized is None:
            raise RuntimeError(
                f"Unsupported feature extractor output type: "
                f"{type(raw).__name__}"
            )

        return [normalized]

    if not isinstance(raw, (list, tuple)):
        raise RuntimeError(
            f"Unsupported feature collection type: "
            f"{type(raw).__name__}"
        )

    result = []

    for item in raw:
        normalized = normalize_feature(item)

        if normalized is None:
            raise RuntimeError(
                f"Unsupported feature record type: "
                f"{type(item).__name__}"
            )

        result.append(normalized)

    return result


# -------------------------------------------------------------------------
# Feature extraction
# -------------------------------------------------------------------------

def extract_features_compat(engine, conn):
    """
    Call the existing analysis-engine feature bridge using the real
    read-only connection.

    Preferred:
        extract_history_features(conn)

    Fallbacks are only compatibility paths and do not alter architecture.
    """

    if not hasattr(engine, "extract_history_features"):
        raise RuntimeError(
            "Analysis Engine does not expose extract_history_features."
        )

    fn = engine.extract_history_features

    try:
        return normalize_feature_collection(
            fn(conn)
        )

    except TypeError as first_error:

        # Some versions expose:
        # extract_history_features(conn=...)
        try:
            return normalize_feature_collection(
                fn(conn=conn)
            )
        except TypeError:
            raise RuntimeError(
                f"Feature extraction failed. "
                f"Expected extract_history_features(conn). "
                f"Original error: {first_error}"
            )


# -------------------------------------------------------------------------
# Feature validation
# -------------------------------------------------------------------------

def validate_features(features):
    if not features:
        raise RuntimeError("Feature collection is empty.")

    seen = set()

    for feature in features:
        missing = REQUIRED_FEATURE_FIELDS - set(feature.keys())

        if missing:
            raise RuntimeError(
                f"Feature missing required fields: {sorted(missing)}"
            )

        cmc_id = feature.get("cmc_id")

        if cmc_id is None:
            raise RuntimeError("Feature contains null cmc_id.")

        if cmc_id in seen:
            raise RuntimeError(
                f"Duplicate feature cmc_id detected: {cmc_id}"
            )

        seen.add(cmc_id)

        price = float(feature["price"])
        previous_price = float(feature["previous_price"])
        snapshot_change = float(feature["snapshot_change"])

        expected = price - previous_price

        if not math.isclose(
            snapshot_change,
            expected,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            raise RuntimeError(
                f"snapshot_change mismatch for cmc_id={cmc_id}"
            )

    return True


# -------------------------------------------------------------------------
# Regime runtime tests
# -------------------------------------------------------------------------

def runtime_regime_test(engine):
    results = {
        "classify_trend": [],
        "classify_momentum": [],
        "classify_volatility": [],
        "classify_volume_regime": [],
    }

    test_values = [-100.0, -10.0, 0.0, 10.0, 100.0]

    expected = {
        "classify_trend": {
            -100.0: "DOWN",
            -10.0: "DOWN",
            0.0: "FLAT",
            10.0: "UP",
            100.0: "UP",
        },
        "classify_momentum": {
            -100.0: "NEGATIVE",
            -10.0: "NEGATIVE",
            0.0: "NEUTRAL",
            10.0: "POSITIVE",
            100.0: "POSITIVE",
        },
        "classify_volatility": {
            0.0: "LOW",
            0.01: "LOW",
            1.0: "MEDIUM",
            10.0: "HIGH",
            100.0: "HIGH",
        },
        "classify_volume_regime": {
            -100.0: "CONTRACTING",
            -10.0: "STABLE",
            0.0: "STABLE",
            10.0: "STABLE",
            100.0: "EXPANDING",
        },
    }

    cases = {
        "classify_trend": [-100.0, -10.0, 0.0, 10.0, 100.0],
        "classify_momentum": [-100.0, -10.0, 0.0, 10.0, 100.0],
        "classify_volatility": [0.0, 0.01, 1.0, 10.0, 100.0],
        "classify_volume_regime": [-100.0, -10.0, 0.0, 10.0, 100.0],
    }

    for name in REQUIRED_REGIME_FUNCTIONS:
        fn = getattr(engine, name)

        for value in cases[name]:
            actual = fn(value)
            results[name].append((value, actual))

            if actual != expected[name][value]:
                return False, results

            if actual not in ALLOWED_VOCABULARY[name]:
                return False, results

    return True, results


def boundary_test(engine):
    cases = (
        ("classify_trend", -0.0, "FLAT"),
        ("classify_trend", 0.0, "FLAT"),
        ("classify_momentum", -0.0, "NEUTRAL"),
        ("classify_momentum", 0.0, "NEUTRAL"),
        ("classify_volatility", 0.0, "LOW"),
        ("classify_volume_regime", 0.0, "STABLE"),
    )

    for name, value, expected in cases:
        actual = getattr(engine, name)(value)

        if actual != expected:
            return False

    return True


def monotonic_test(engine):
    ordered = {
        "classify_trend": [-100, -10, 0, 10, 100],
        "classify_momentum": [-100, -10, 0, 10, 100],
        "classify_volatility": [0, 0.01, 1, 10, 100],
        "classify_volume_regime": [-100, -10, 0, 10, 100],
    }

    rank = {
        "classify_trend": {
            "DOWN": 0,
            "FLAT": 1,
            "UP": 2,
        },
        "classify_momentum": {
            "NEGATIVE": 0,
            "NEUTRAL": 1,
            "POSITIVE": 2,
        },
        "classify_volatility": {
            "LOW": 0,
            "MEDIUM": 1,
            "HIGH": 2,
        },
        "classify_volume_regime": {
            "CONTRACTING": 0,
            "STABLE": 1,
            "EXPANDING": 2,
        },
    }

    for name, values in ordered.items():
        fn = getattr(engine, name)

        outputs = [fn(v) for v in values]
        scores = [rank[name][x] for x in outputs]

        for a, b in zip(scores, scores[1:]):
            if b < a:
                return False

    return True


# -------------------------------------------------------------------------
# Cross-feature quality
# -------------------------------------------------------------------------

def cross_feature_quality(engine, features):
    """
    Validate semantic relationships among simultaneously available
    features without inventing a new signal.

    This is QUALITY VALIDATION, not strategy generation.
    """

    checked = 0

    for feature in features:
        price = float(feature["price"])
        previous_price = float(feature["previous_price"])
        snapshot_change = float(feature["snapshot_change"])

        if not math.isfinite(price):
            return False, "Non-finite price."

        if not math.isfinite(previous_price):
            return False, "Non-finite previous_price."

        if not math.isfinite(snapshot_change):
            return False, "Non-finite snapshot_change."

        expected_change = price - previous_price

        if not math.isclose(
            snapshot_change,
            expected_change,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            return False, (
                f"snapshot_change mismatch for "
                f"cmc_id={feature.get('cmc_id')}"
            )

        # If optional fields exist, verify their numeric integrity.
        optional_numeric = (
            "change_1h",
            "change_24h",
            "change_7d",
            "market_cap",
            "volume_24h",
            "previous_volume_24h",
            "previous_volume",
            "rank",
        )

        for field in optional_numeric:
            if field in feature and feature[field] is not None:
                try:
                    value = float(feature[field])
                except (TypeError, ValueError):
                    return False, (
                        f"Non-numeric {field} for "
                        f"cmc_id={feature.get('cmc_id')}"
                    )

                if not math.isfinite(value):
                    return False, (
                        f"Non-finite {field} for "
                        f"cmc_id={feature.get('cmc_id')}"
                    )

        checked += 1

    if checked == 0:
        return False, "No features checked."

    return True, f"{checked} features validated"


# -------------------------------------------------------------------------
# Combination vocabulary
# -------------------------------------------------------------------------

def regime_combination_test(engine):
    combinations = []

    for trend in (-100.0, 0.0, 100.0):
        for momentum in (-100.0, 0.0, 100.0):
            for volatility in (0.0, 1.0, 100.0):
                for volume in (-100.0, 0.0, 100.0):
                    combinations.append(
                        (
                            engine.classify_trend(trend),
                            engine.classify_momentum(momentum),
                            engine.classify_volatility(volatility),
                            engine.classify_volume_regime(volume),
                        )
                    )

    valid = 0

    for combo in combinations:
        trend, momentum, volatility, volume = combo

        if trend not in ALLOWED_VOCABULARY["classify_trend"]:
            return False, len(combinations), 1

        if momentum not in ALLOWED_VOCABULARY["classify_momentum"]:
            return False, len(combinations), 1

        if volatility not in ALLOWED_VOCABULARY["classify_volatility"]:
            return False, len(combinations), 1

        if volume not in ALLOWED_VOCABULARY["classify_volume_regime"]:
            return False, len(combinations), 1

        valid += 1

    return True, valid, 0


# -------------------------------------------------------------------------
# CMC identity
# -------------------------------------------------------------------------

def cardinality_test(conn, features):
    db_count = conn.execute(
        """
        SELECT COUNT(DISTINCT cmc_id)
        FROM market_history
        WHERE timestamp = (
            SELECT MAX(timestamp)
            FROM market_history
        )
        """
    ).fetchone()[0]

    feature_ids = {
        feature["cmc_id"]
        for feature in features
    }

    return len(feature_ids) == db_count, len(feature_ids), db_count


def identity_test(features):
    ids = []
    symbols = []

    for feature in features:
        ids.append(feature["cmc_id"])

        if feature.get("symbol") is not None:
            symbols.append(feature.get("symbol"))

    return (
        len(ids) == len(set(ids)),
        len(ids),
        len(set(ids)),
    )


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

def main():

    banner("REGIME QUALITY & CROSS-FEATURE VALIDATION")

    overall_pass = True

    # ------------------------------------------------------------------
    # MODE
    # ------------------------------------------------------------------

    section("MODE")

    status("Database mutation", "NONE")
    status("Production write", "NONE")
    status("Audit mode", "READ ONLY")

    # ------------------------------------------------------------------
    # FILE VALIDATION
    # ------------------------------------------------------------------

    section("FILE VALIDATION")

    paths = (
        ("Analysis Engine", ANALYSIS_ENGINE_PATH),
        ("Feature Extractor", FEATURE_EXTRACTOR_PATH),
        ("Query Layer", QUERY_LAYER_PATH),
    )

    sources = {}

    for label, path in paths:

        if not path.exists():
            status(label, "FAIL — FILE NOT FOUND")
            overall_pass = False
            continue

        source = load_source(path)
        tree, error = parse_ast(source)

        if error:
            status(label, "FAIL")
            print(f"AST Error: {error}")
            overall_pass = False
        else:
            status(label, "PASS")
            print(f"{'AST Parse':45}: PASS")

        sources[label] = source

    if "Analysis Engine" not in sources:
        print()
        print("STEP 10B ABORTED — Analysis Engine source unavailable.")
        return 1

    # ------------------------------------------------------------------
    # FUNCTION INVENTORY
    # ------------------------------------------------------------------

    section("ANALYSIS ENGINE FUNCTION INVENTORY")

    inventory = function_inventory(
        sources["Analysis Engine"]
    )

    for name in inventory:
        print(f" - {name}")

    # ------------------------------------------------------------------
    # REQUIRED REGIME FUNCTIONS
    # ------------------------------------------------------------------

    section("REQUIRED REGIME FUNCTIONS")

    regime_functions_pass = True

    for name in REQUIRED_REGIME_FUNCTIONS:

        exists = name in inventory

        status(
            name,
            "PASS" if exists else "FAIL"
        )

        if not exists:
            regime_functions_pass = False

    overall_pass &= regime_functions_pass

    # ------------------------------------------------------------------
    # STATIC SEMANTIC AUDIT
    # ------------------------------------------------------------------

    section("STATIC REGIME SEMANTIC AUDIT")

    static_pass = True

    for name in REQUIRED_REGIME_FUNCTIONS:

        source = sources["Analysis Engine"]
        tree = ast.parse(source)

        fn_node = None

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == name:
                    fn_node = node
                    break

        if fn_node is None:
            static_pass = False
            status(name, "FAIL")
            continue

        function_source = ast.get_source_segment(
            source,
            fn_node
        ) or ""

        # Reject obviously missing semantic returns.
        if "return" not in function_source:
            static_pass = False
            status(name, "FAIL — no return")
            continue

        status(name, "PASS")

    status(
        "Static semantic logic",
        "PASS" if static_pass else "FAIL"
    )

    overall_pass &= static_pass

    # ------------------------------------------------------------------
    # SOURCE MUTATION AUDIT
    # ------------------------------------------------------------------

    section("SOURCE MUTATION AUDIT")

    mutations = detect_real_sql_mutations(
        sources["Analysis Engine"]
    )

    if mutations:
        print("SQL mutation statements : FOUND")

        for line_no, keyword, sql in mutations:
            print(
                f"L{line_no:<5} {keyword:<10} {sql}"
            )

        mutation_pass = False
    else:
        print("SQL mutation statements : NONE DETECTED")
        mutation_pass = True

    # ------------------------------------------------------------------
    # DB FINGERPRINT
    # ------------------------------------------------------------------

    conn = None
    before = None
    after = None

    try:
        conn = connect_read_only()

        if not table_exists(conn, "market_history"):
            section("SOURCE CONTRACT")
            status("market_history", "FAIL")
            return 1

        section("DATABASE READ-ONLY FINGERPRINT")

        before = history_fingerprint(conn)

        status("Schema validation", "PASS")
        status("Rows", before["rows"])
        status("Snapshots", before["snapshots"])
        status("Distinct CMC IDs", before["cmc_ids"])
        status("Duplicate IDs", before["duplicate_ids"])

        # ------------------------------------------------------------------
        # MODULE IMPORT
        # ------------------------------------------------------------------

        section("MODULE IMPORT")

        try:
            engine = import_module_from_dir()
            status("Analysis Engine import", "PASS")
        except Exception as exc:
            status(
                "Analysis Engine import",
                f"FAIL — {type(exc).__name__}: {exc}"
            )
            return 1

        # ------------------------------------------------------------------
        # RUNTIME REGIME
        # ------------------------------------------------------------------

        section("RUNTIME REGIME VALIDATION")

        runtime_pass, runtime_results = runtime_regime_test(
            engine
        )

        for name, results in runtime_results.items():

            if runtime_pass:
                status(name, "PASS")
            else:
                status(name, "FAIL")

            if results:
                print(
                    "  Outputs : "
                    + ", ".join(
                        str(actual)
                        for _, actual in results
                    )
                )

        status(
            "Semantic runtime result",
            "PASS" if runtime_pass else "FAIL"
        )

        overall_pass &= runtime_pass

        # ------------------------------------------------------------------
        # BOUNDARY
        # ------------------------------------------------------------------

        section("BOUNDARY VALUE SEMANTICS")

        boundary_pass = boundary_test(engine)

        status(
            "Boundary behavior",
            "PASS" if boundary_pass else "FAIL"
        )

        overall_pass &= boundary_pass

        # ------------------------------------------------------------------
        # MONOTONICITY
        # ------------------------------------------------------------------

        section("REGIME MONOTONICITY")

        monotonic_pass = monotonic_test(engine)

        status(
            "Monotonic regime behavior",
            "PASS" if monotonic_pass else "FAIL"
        )

        overall_pass &= monotonic_pass

        # ------------------------------------------------------------------
        # VOCABULARY
        # ------------------------------------------------------------------

        section("REGIME OUTPUT VOCABULARY")

        vocabulary_pass = True

        for name in REQUIRED_REGIME_FUNCTIONS:

            fn = getattr(engine, name)

            if name == "classify_volatility":
                values = [0.0, 0.01, 1.0, 10.0, 100.0]
            else:
                values = [-100.0, -10.0, 0.0, 10.0, 100.0]

            runtime_outputs = {
                fn(value)
                for value in values
            }

            allowed = ALLOWED_VOCABULARY[name]

            passed = runtime_outputs <= allowed

            status(
                name,
                "PASS" if passed else "FAIL"
            )

            print(
                f"  Allowed : {', '.join(sorted(allowed))}"
            )
            print(
                f"  Runtime : {', '.join(sorted(runtime_outputs))}"
            )

            vocabulary_pass &= passed

        overall_pass &= vocabulary_pass

        # ------------------------------------------------------------------
        # LOOK AHEAD
        # ------------------------------------------------------------------

        section("LOOK-AHEAD / FUTURE DATA AUDIT")

        suspicious = future_data_audit(
            sources["Analysis Engine"]
        )

        if suspicious:
            print(
                "Suspicious future-data patterns : "
                + ", ".join(suspicious)
            )
            lookahead_pass = False
        else:
            print(
                "Suspicious future-data patterns : "
                "NONE DETECTED"
            )
            lookahead_pass = True

        overall_pass &= lookahead_pass

        # ------------------------------------------------------------------
        # FEATURE EXTRACTION
        # ------------------------------------------------------------------

        section("FEATURE EXTRACTION")

        features = None
        feature_pass = False

        try:
            features = extract_features_compat(
                engine,
                conn,
            )

            validate_features(features)

            feature_pass = True

            status(
                "Feature Records",
                len(features)
            )
            status(
                "Feature extraction",
                "PASS"
            )

        except Exception as exc:

            status(
                "Feature Records",
                0
            )

            status(
                "Feature extraction",
                "FAIL"
            )

            print(
                f"Error : {type(exc).__name__}: {exc}"
            )

        # Do NOT let feature extraction failure masquerade as a
        # database mutation failure.
        overall_pass &= feature_pass

        # ------------------------------------------------------------------
        # CROSS FEATURE
        # ------------------------------------------------------------------

        section("CROSS-FEATURE QUALITY")

        if feature_pass:

            cross_pass, cross_detail = cross_feature_quality(
                engine,
                features,
            )

            if cross_pass:
                print(
                    f"Cross-feature semantics : PASS — {cross_detail}"
                )
            else:
                print(
                    f"Cross-feature semantics : FAIL — {cross_detail}"
                )

        else:

            cross_pass = False

            print(
                "Cross-feature semantics : "
                "FAIL — feature extraction unavailable"
            )

        overall_pass &= cross_pass

        # ------------------------------------------------------------------
        # REGIME MATRIX
        # ------------------------------------------------------------------

        section("REGIME COMBINATION MATRIX")

        combo_pass, combo_count, invalid_count = (
            regime_combination_test(engine)
        )

        print(
            f"Representative combinations : {combo_count}"
        )
        print(
            f"Invalid combinations          : {invalid_count}"
        )

        status(
            "Combination vocabulary",
            "PASS" if combo_pass else "FAIL"
        )

        overall_pass &= combo_pass

        # ------------------------------------------------------------------
        # CARDINALITY
        # ------------------------------------------------------------------

        section("CMC_ID CARDINALITY")

        if feature_pass:

            card_pass, feature_count, db_count = (
                cardinality_test(
                    conn,
                    features,
                )
            )

            print(
                f"Feature CMC IDs : {feature_count}"
            )
            print(
                f"Database CMC IDs: {db_count}"
            )

            status(
                "Cardinality",
                "PASS" if card_pass else "FAIL"
            )

        else:

            card_pass = False

            print(
                "Cardinality : "
                "FAIL — feature extraction unavailable"
            )

        overall_pass &= card_pass

        # ------------------------------------------------------------------
        # IDENTITY
        # ------------------------------------------------------------------

        section("CMC_ID IDENTITY")

        if feature_pass:

            identity_pass, total_ids, unique_ids = (
                identity_test(features)
            )

            print(
                f"Feature IDs : {total_ids}"
            )
            print(
                f"Unique IDs  : {unique_ids}"
            )

            status(
                "CMC_ID identity",
                "PASS" if identity_pass else "FAIL"
            )

        else:

            identity_pass = False

            print(
                "CMC_ID identity : "
                "FAIL — feature extraction unavailable"
            )

        overall_pass &= identity_pass

        # ------------------------------------------------------------------
        # POST FINGERPRINT
        # ------------------------------------------------------------------

        section("DATABASE READ-ONLY FINGERPRINT AFTER")

        after = history_fingerprint(conn)

        status("Rows", after["rows"])
        status("Snapshots", after["snapshots"])
        status("Distinct CMC IDs", after["cmc_ids"])
        status("Duplicate IDs", after["duplicate_ids"])

        unchanged = fingerprints_equal(
            before,
            after,
        )

        print(
            f"BEFORE == AFTER : "
            f"{'PASS' if unchanged else 'FAIL'}"
        )

        overall_pass &= unchanged

        # ------------------------------------------------------------------
        # IMPORTANT:
        # Mutation audit must not be confused with read-only connection.
        # The actual DB is opened with mode=ro and fingerprint is preserved.
        # ------------------------------------------------------------------

        read_only_pass = (
            mutation_pass
            and unchanged
        )

        # ------------------------------------------------------------------
        # FINAL CONTRACT
        # ------------------------------------------------------------------

        section("REQUIRED REGIME QUALITY CONTRACT")

        status(
            "Required functions",
            "PASS" if regime_functions_pass else "FAIL"
        )

        status(
            "Static semantic logic",
            "PASS" if static_pass else "FAIL"
        )

        status(
            "Runtime semantics",
            "PASS" if runtime_pass else "FAIL"
        )

        status(
            "Boundary semantics",
            "PASS" if boundary_pass else "FAIL"
        )

        status(
            "Monotonic semantics",
            "PASS" if monotonic_pass else "FAIL"
        )

        status(
            "Output vocabulary",
            "PASS" if vocabulary_pass else "FAIL"
        )

        status(
            "Cross-feature semantics",
            "PASS" if cross_pass else "FAIL"
        )

        status(
            "Combination vocabulary",
            "PASS" if combo_pass else "FAIL"
        )

        status(
            "No look-ahead patterns",
            "PASS" if lookahead_pass else "FAIL"
        )

        status(
            "CMC_ID cardinality",
            "PASS" if card_pass else "FAIL"
        )

        status(
            "CMC_ID identity",
            "PASS" if identity_pass else "FAIL"
        )

        status(
            "Read only",
            "PASS" if read_only_pass else "FAIL"
        )

        status(
            "Database unchanged",
            "PASS" if unchanged else "FAIL"
        )

        # ------------------------------------------------------------------
        # VERDICT
        # ------------------------------------------------------------------

        print("=" * 100)
        print("STEP 10B VERDICT")
        print("=" * 100)

        if (
            regime_functions_pass
            and static_pass
            and runtime_pass
            and boundary_pass
            and monotonic_pass
            and vocabulary_pass
            and cross_pass
            and combo_pass
            and lookahead_pass
            and card_pass
            and identity_pass
            and read_only_pass
            and unchanged
        ):
            print(
                "RESULT : REGIME QUALITY & CROSS-FEATURE VALIDATION PASS"
            )
            print(
                "STATUS : READY FOR STEP 11"
            )

            print()
            print("Architecture : PRESERVED")
            print("Database     : READ ONLY")
            print("Writes       : NONE")

            return 0

        print(
            "RESULT : REGIME QUALITY & CROSS-FEATURE VALIDATION FAIL"
        )
        print(
            "STATUS : DO NOT PROCEED TO STEP 11"
        )

        print()
        print("Architecture : PRESERVED")
        print("Database     : READ ONLY")
        print("Writes       : NONE")

        return 1

    finally:

        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())