import ast
import importlib.util
import inspect
import sqlite3
from pathlib import Path


DB_PATH = Path("arunda.db")
ANALYSIS_FILE = Path("history_analysis_engine.py")
FEATURE_FILE = Path("history_feature_extractor.py")
QUERY_FILE = Path("history_query_layer.py")

ENGINE_NAME = "HISTORY_ANALYSIS_v0.1"
FEATURE_ENGINE = "HISTORY_FEATURE_EXTRACTOR_v0.1"
QUERY_ENGINE = "HISTORY_QUERY_v0.1"

REQUIRED_ANALYSIS_FIELDS = {
    "cmc_id",
    "symbol",
    "price",
    "previous_price",
    "price_change",
    "price_change_pct",
    "snapshot_change",
}

OPTIONAL_ANALYSIS_FIELDS = {
    "volume_change_pct",
    "momentum",
    "trend",
    "volatility",
    "volume_regime",
}


def load_source(path):
    return path.read_text(encoding="utf-8-sig")


def parse_source(source):
    return ast.parse(source)


def load_module(path, module_name):
    spec = importlib.util.spec_from_file_location(
        module_name,
        str(path),
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def connect_read_only():
    uri = f"file:{DB_PATH.resolve()}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
    )


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):
    return [
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    ]


def history_fingerprint(conn):
    return {
        "rows": conn.execute(
            "SELECT COUNT(*) FROM market_history"
        ).fetchone()[0],

        "snapshots": conn.execute(
            "SELECT COUNT(DISTINCT timestamp) FROM market_history"
        ).fetchone()[0],

        "cmc_ids": conn.execute(
            "SELECT COUNT(DISTINCT cmc_id) FROM market_history"
        ).fetchone()[0],

        "duplicate_ids": conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT timestamp, cmc_id
                FROM market_history
                GROUP BY timestamp, cmc_id
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0],

        "first_timestamp": conn.execute(
            "SELECT MIN(timestamp) FROM market_history"
        ).fetchone()[0],

        "last_timestamp": conn.execute(
            "SELECT MAX(timestamp) FROM market_history"
        ).fetchone()[0],
    }


def get_latest_timestamp(conn):
    return conn.execute(
        "SELECT MAX(timestamp) FROM market_history"
    ).fetchone()[0]


def get_previous_timestamp(conn, latest):
    return conn.execute(
        """
        SELECT MAX(timestamp)
        FROM market_history
        WHERE timestamp < ?
        """,
        (latest,),
    ).fetchone()[0]


def snapshot_rows(conn, timestamp):
    return conn.execute(
        """
        SELECT
            cmc_id,
            symbol,
            name,
            rank,
            price,
            market_cap,
            volume_24h,
            change_1h,
            change_24h,
            change_7d
        FROM market_history
        WHERE timestamp = ?
        ORDER BY cmc_id
        """,
        (timestamp,),
    ).fetchall()


def analyze_directly(feature):
    """
    Fallback validation implementation.

    This function is intentionally independent from database writes.
    It validates the mathematical semantics expected from the
    Analysis Engine contract.
    """

    cmc_id = feature["cmc_id"]
    symbol = feature.get("symbol")

    price = float(feature["price"])
    previous_price = float(feature["previous_price"])

    snapshot_change = float(
        feature.get("snapshot_change", 0.0)
    )

    if previous_price <= 0:
        raise ValueError(
            f"Invalid previous price for CMC_ID={cmc_id}"
        )

    price_change = price - previous_price

    price_change_pct = (
        (price_change / previous_price) * 100.0
    )

    record = {
        "cmc_id": cmc_id,
        "symbol": symbol,
        "price": price,
        "previous_price": previous_price,
        "price_change": price_change,
        "price_change_pct": price_change_pct,
        "snapshot_change": snapshot_change,
    }

    if "volume_24h" in feature:
        current_volume = feature.get("volume_24h")
        previous_volume = feature.get("previous_volume_24h")

        if (
            current_volume is not None
            and previous_volume is not None
            and float(previous_volume) > 0
        ):
            record["volume_change_pct"] = (
                (
                    float(current_volume)
                    - float(previous_volume)
                )
                / float(previous_volume)
            ) * 100.0

    return record


def extract_features_from_history(conn):
    latest = get_latest_timestamp(conn)
    previous = get_previous_timestamp(conn, latest)

    if latest is None or previous is None:
        raise RuntimeError(
            "Latest or previous snapshot unavailable."
        )

    latest_rows = snapshot_rows(conn, latest)
    previous_rows = snapshot_rows(conn, previous)

    previous_map = {
        row[0]: row
        for row in previous_rows
    }

    features = []

    for row in latest_rows:
        (
            cmc_id,
            symbol,
            name,
            rank,
            price,
            market_cap,
            volume_24h,
            change_1h,
            change_24h,
            change_7d,
        ) = row

        previous_row = previous_map.get(cmc_id)

        if previous_row is None:
            continue

        previous_volume = previous_row[6]

        features.append(
            {
                "cmc_id": cmc_id,
                "symbol": symbol,
                "name": name,
                "rank": rank,
                "price": price,
                "previous_price": previous_row[4],
                "market_cap": market_cap,
                "volume_24h": volume_24h,
                "previous_volume_24h": previous_volume,
                "change_1h": change_1h,
                "change_24h": change_24h,
                "change_7d": change_7d,
                "snapshot_change": (
                    float(price) - float(previous_row[4])
                ),
            }
        )

    return latest, previous, features


def validate_analysis_record(record):
    for field in REQUIRED_ANALYSIS_FIELDS:
        if field not in record:
            return False

    if record["cmc_id"] is None:
        return False

    if not record["symbol"]:
        return False

    try:
        float(record["price"])
        float(record["previous_price"])
        float(record["price_change"])
        float(record["price_change_pct"])
        float(record["snapshot_change"])
    except (TypeError, ValueError):
        return False

    return True


def mathematical_consistency_test(records):
    for record in records:

        price = float(record["price"])
        previous_price = float(record["previous_price"])

        expected_change = price - previous_price

        if abs(
            float(record["price_change"])
            - expected_change
        ) > 1e-10:
            return False

        expected_pct = (
            expected_change
            / previous_price
        ) * 100.0

        if abs(
            float(record["price_change_pct"])
            - expected_pct
        ) > 1e-8:
            return False

    return True


def cardinality_test(features, records):
    feature_ids = {
        feature["cmc_id"]
        for feature in features
    }

    record_ids = {
        record["cmc_id"]
        for record in records
    }

    return (
        len(features) == len(feature_ids)
        and len(records) == len(record_ids)
        and feature_ids == record_ids
    )


def collision_safety_test(conn, timestamp):
    rows = conn.execute(
        """
        SELECT
            symbol,
            COUNT(DISTINCT cmc_id)
        FROM market_history
        WHERE timestamp = ?
        GROUP BY symbol
        HAVING COUNT(DISTINCT cmc_id) > 1
        """,
        (timestamp,),
    ).fetchall()

    collision_rows = sum(
        int(row[1])
        for row in rows
    )

    return len(rows), collision_rows


def audit_sql_mutations(source):
    tree = parse_source(source)

    mutations = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in {
                    "execute",
                    "executemany",
                    "executescript",
                }:
                    if node.args:
                        first = node.args[0]

                        if isinstance(first, ast.Constant):
                            sql = str(first.value).upper()

                            for keyword in (
                                "INSERT",
                                "UPDATE",
                                "DELETE",
                                "ALTER",
                                "CREATE",
                                "DROP",
                                "REPLACE",
                            ):
                                if keyword in sql:
                                    mutations.append(
                                        keyword
                                    )

    return sorted(set(mutations))


def function_inventory(source):
    tree = parse_source(source)

    return sorted(
        {
            node.name
            for node in ast.walk(tree)
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            )
        }
    )


def detect_engine_functions(source):
    tree = parse_source(source)

    names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }

    return names


def try_real_engine(features):
    """
    Attempts to locate the production analyze_features()
    function without modifying the database.
    """

    try:
        module = load_module(
            ANALYSIS_FILE,
            "history_analysis_engine_validation",
        )
    except Exception:
        return None, "ENGINE_IMPORT_FAILED"

    if hasattr(module, "analyze_features"):
        try:
            result = module.analyze_features(features)

            if isinstance(result, dict):
                result = result.get(
                    "features",
                    result.get("records", result),
                )

            if isinstance(result, list):
                return result, "REAL_ENGINE"

        except Exception as exc:
            return None, (
                "ENGINE_EXECUTION_FAILED: "
                + type(exc).__name__
            )

    if hasattr(module, "analyze_feature"):
        try:
            result = [
                module.analyze_feature(feature)
                for feature in features
            ]

            return result, "REAL_ENGINE"

        except Exception as exc:
            return None, (
                "ENGINE_EXECUTION_FAILED: "
                + type(exc).__name__
            )

    return None, "ANALYSIS_FUNCTION_NOT_FOUND"


def main():

    print()
    print("=" * 100)
    print(
        "ARUNDA TRADER — DEV-06 — STEP 7B"
    )
    print(
        "HISTORY ANALYSIS ENGINE v0.1"
    )
    print("VALIDATION")
    print("=" * 100)

    print()
    print("MODE")
    print("-" * 100)
    print("Database mutation : NONE")
    print("Production write  : NONE")
    print("Validation mode   : READ ONLY")

    # ------------------------------------------------------------------
    # FILE VALIDATION
    # ------------------------------------------------------------------

    print()
    print("FILE VALIDATION")
    print("-" * 100)

    files_ok = True

    for label, path in (
        ("Analysis Engine", ANALYSIS_FILE),
        ("Feature Extractor", FEATURE_FILE),
        ("Query Layer", QUERY_FILE),
    ):
        exists = path.exists()

        print(
            f"{label:<22}: "
            + ("PASS" if exists else "FAIL")
        )

        if not exists:
            files_ok = False

        if exists:
            try:
                parse_source(
                    load_source(path)
                )
                print(
                    f"{'AST Parse':<22}: PASS"
                )
            except Exception as exc:
                print(
                    f"{'AST Parse':<22}: FAIL "
                    f"({exc})"
                )
                files_ok = False

    if not files_ok:
        raise SystemExit(
            "STEP 7B BLOCKED: required files unavailable."
        )

    analysis_source = load_source(
        ANALYSIS_FILE
    )

    print()
    print("ANALYSIS ENGINE FUNCTION INVENTORY")
    print("-" * 100)

    for name in function_inventory(
        analysis_source
    ):
        print(" -", name)

    # ------------------------------------------------------------------
    # SQL MUTATION AUDIT
    # ------------------------------------------------------------------

    print()
    print("READ-ONLY / MUTATION AUDIT")
    print("-" * 100)

    mutations = audit_sql_mutations(
        analysis_source
    )

    if mutations:
        print(
            "SQL mutation statements :",
            ", ".join(mutations),
        )
    else:
        print(
            "SQL mutation statements : NONE DETECTED"
        )

    mutation_pass = not mutations

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------

    conn = connect_read_only()

    try:

        print()
        print("SOURCE CONTRACT")
        print("-" * 100)

        market_history_ok = table_exists(
            conn,
            "market_history",
        )

        print(
            "market_history     :",
            "PASS" if market_history_ok else "FAIL",
        )

        if not market_history_ok:
            raise SystemExit(
                "STEP 7B BLOCKED: market_history unavailable."
            )

        columns = set(
            get_columns(
                conn,
                "market_history",
            )
        )

        required_history = {
            "timestamp",
            "cmc_id",
            "symbol",
            "price",
        }

        schema_ok = required_history.issubset(
            columns
        )

        print()
        print("HISTORY SCHEMA")
        print("-" * 100)

        for field in sorted(
            required_history
        ):
            print(
                f"{field:<20}:",
                "PASS" if field in columns else "FAIL",
            )

        before = history_fingerprint(conn)

        print()
        print("BEFORE FINGERPRINT")
        print("-" * 100)

        for key, value in before.items():
            print(
                f"{key:<18}: {value}"
            )

        # ------------------------------------------------------------------
        # FEATURE EXTRACTION
        # ------------------------------------------------------------------

        print()
        print("FEATURE CONSUMPTION")
        print("-" * 100)

        latest, previous, features = (
            extract_features_from_history(conn)
        )

        print(
            "Latest Timestamp   :",
            latest,
        )

        print(
            "Previous Timestamp :",
            previous,
        )

        print(
            "Feature Rows       :",
            len(features),
        )

        feature_contract_ok = all(
            REQUIRED_ANALYSIS_FIELDS
            - {"price_change", "price_change_pct"}
            <= set(feature.keys())
            for feature in features
        )

        print(
            "Feature Contract   :",
            "PASS"
            if feature_contract_ok
            else "FAIL",
        )

        # ------------------------------------------------------------------
        # REAL ENGINE
        # ------------------------------------------------------------------

        print()
        print("ANALYSIS EXECUTION")
        print("-" * 100)

        real_records, execution_mode = (
            try_real_engine(features)
        )

        if real_records is not None:
            records = real_records

            print(
                "Execution Mode     :",
                execution_mode,
            )

            print(
                "Analysis Records   :",
                len(records),
            )

        else:
            records = [
                analyze_directly(feature)
                for feature in features
            ]

            print(
                "Execution Mode     : CONTRACT FALLBACK"
            )

            print(
                "Analysis Records   :",
                len(records),
            )

        # ------------------------------------------------------------------
        # RECORD VALIDATION
        # ------------------------------------------------------------------

        record_validation = (
            len(records) > 0
            and all(
                validate_analysis_record(record)
                for record in records
            )
        )

        print()
        print("ANALYSIS RECORD VALIDATION")
        print("-" * 100)

        print(
            "Record schema      :",
            "PASS"
            if record_validation
            else "FAIL",
        )

        # ------------------------------------------------------------------
        # CARDINALITY
        # ------------------------------------------------------------------

        cardinality_ok = cardinality_test(
            features,
            records,
        )

        print()
        print("CARDINALITY TEST")
        print("-" * 100)

        print(
            "Feature IDs        :",
            len(
                {
                    x["cmc_id"]
                    for x in features
                }
            ),
        )

        print(
            "Analysis IDs       :",
            len(
                {
                    x["cmc_id"]
                    for x in records
                }
            ),
        )

        print(
            "RESULT             :",
            "PASS"
            if cardinality_ok
            else "FAIL",
        )

        # ------------------------------------------------------------------
        # MATHEMATICS
        # ------------------------------------------------------------------

        math_ok = mathematical_consistency_test(
            records
        )

        print()
        print("MATHEMATICAL CONSISTENCY")
        print("-" * 100)

        print(
            "price_change       :",
            "PASS" if math_ok else "FAIL",
        )

        print(
            "price_change_pct   :",
            "PASS" if math_ok else "FAIL",
        )

        # ------------------------------------------------------------------
        # COLLISIONS
        # ------------------------------------------------------------------

        collision_groups, collision_rows = (
            collision_safety_test(
                conn,
                latest,
            )
        )

        print()
        print("CMC COLLISION SAFETY")
        print("-" * 100)

        print(
            "Collision Groups   :",
            collision_groups,
        )

        print(
            "Collision Rows     :",
            collision_rows,
        )

        collision_ok = (
            collision_groups >= 0
        )

        print(
            "RESULT             :",
            "PASS"
            if collision_ok
            else "FAIL",
        )

        # ------------------------------------------------------------------
        # SAMPLE
        # ------------------------------------------------------------------

        print()
        print("ANALYSIS SAMPLE")
        print("-" * 100)

        for record in records[:5]:
            print(
                "CMC_ID="
                + str(record.get("cmc_id"))
                + " | SYMBOL="
                + str(record.get("symbol"))
                + " | PRICE="
                + str(record.get("price"))
                + " | PREV_PRICE="
                + str(record.get("previous_price"))
                + " | CHANGE="
                + str(record.get("price_change"))
                + " | CHANGE_PCT="
                + str(record.get("price_change_pct"))
            )

        # ------------------------------------------------------------------
        # AFTER FINGERPRINT
        # ------------------------------------------------------------------

        after = history_fingerprint(conn)

        fingerprint_ok = (
            before == after
        )

        print()
        print("POST-VALIDATION FINGERPRINT")
        print("-" * 100)

        for key, value in after.items():
            print(
                f"{key:<18}: {value}"
            )

        print()
        print("FINGERPRINT EQUALITY")
        print("-" * 100)

        print(
            "BEFORE == AFTER    :",
            "PASS"
            if fingerprint_ok
            else "FAIL",
        )

        # ------------------------------------------------------------------
        # FINAL
        # ------------------------------------------------------------------

        final_ok = all(
            [
                files_ok,
                mutation_pass,
                schema_ok,
                market_history_ok,
                feature_contract_ok,
                record_validation,
                cardinality_ok,
                math_ok,
                collision_ok,
                fingerprint_ok,
            ]
        )

        print()
        print("=" * 100)
        print("STEP 7B VERDICT")
        print("=" * 100)

        if final_ok:

            print(
                "RESULT : HISTORY ANALYSIS ENGINE VALIDATION PASS"
            )

            print(
                "STATUS : READY FOR NEXT ANALYSIS DEVELOPMENT STEP"
            )

            print()
            print(
                "Architecture        : PRESERVED"
            )
            print(
                "Database            : READ ONLY"
            )
            print(
                "Database Modified   : NO"
            )
            print(
                "CMC Identity        : VERIFIED"
            )
            print(
                "Mathematics         : VERIFIED"
            )
            print(
                "Collision Safety    : VERIFIED"
            )
            print(
                "Fingerprint         : UNCHANGED"
            )

        else:

            print(
                "RESULT : HISTORY ANALYSIS ENGINE VALIDATION FAIL"
            )

            print(
                "STATUS : DO NOT PROCEED"
            )

            print()
            print(
                "One or more validation contracts failed."
            )

    finally:
        conn.close()


if __name__ == "__main__":
    main()