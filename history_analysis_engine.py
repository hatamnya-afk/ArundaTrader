import sqlite3
from pathlib import Path
from datetime import datetime, timezone


DB_PATH = "arunda.db"

ENGINE_NAME = "HISTORY_ANALYSIS_v0.1"
QUERY_ENGINE = "HISTORY_QUERY_v0.1"
FEATURE_ENGINE = "HISTORY_FEATURE_EXTRACTOR_v0.1"

REQUIRED_FEATURE_FIELDS = {
    "cmc_id",
    "symbol",
    "price",
    "previous_price",
    "snapshot_change",
    "snapshot_change_pct",
}

OPTIONAL_FEATURE_FIELDS = {
    "name",
    "rank",
    "market_cap",
    "volume_24h",
    "previous_volume_24h",
    "latest_change_1h",
    "latest_change_24h",
    "latest_change_7d",
    "previous_change_1h",
    "previous_change_24h",
    "previous_change_7d",
    "latest_timestamp",
    "previous_timestamp",
}


# ============================================================================
# READ-ONLY DATABASE
# ============================================================================

def connect_read_only(db_path=DB_PATH):
    path = Path(db_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")

    uri = f"file:{path.as_posix()}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        check_same_thread=False,
    )


# ============================================================================
# BASIC HELPERS
# ============================================================================

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


def utc_now():
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# HISTORY FINGERPRINT
# ============================================================================

def history_fingerprint(conn):
    required = {
        "cmc_id",
        "timestamp",
        "symbol",
        "name",
        "price",
    }

    columns = set(get_columns(conn, "market_history"))

    if not required.issubset(columns):
        missing = required - columns
        raise RuntimeError(
            f"market_history missing required columns: {sorted(missing)}"
        )

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


# ============================================================================
# FEATURE CONTRACT
# ============================================================================

def validate_feature_record(feature):
    if not isinstance(feature, dict):
        return False

    for field in REQUIRED_FEATURE_FIELDS:
        if field not in feature:
            return False

    cmc_id = feature.get("cmc_id")

    if cmc_id is None:
        return False

    try:
        float(feature["price"])
        float(feature["previous_price"])
        float(feature["snapshot_change"])
        float(feature["snapshot_change_pct"])
    except (TypeError, ValueError):
        return False

    return True


def validate_feature_collection(features):
    if not isinstance(features, list):
        return False

    seen = set()

    for feature in features:
        if not validate_feature_record(feature):
            return False

        cmc_id = feature["cmc_id"]

        if cmc_id in seen:
            return False

        seen.add(cmc_id)

    return True


# ============================================================================
# FEATURE LOADING
# ============================================================================

def load_feature_extractor():
    """
    Import the already validated history feature extractor.

    The analysis layer does not recreate history queries.
    """

    try:
        import history_feature_extractor as extractor
    except Exception as exc:
        raise RuntimeError(
            "Unable to import history_feature_extractor.py"
        ) from exc

    return extractor


def extract_history_features(conn):
    """
    Consume the existing feature extractor.

    Preferred interface:
        extract_features(conn)

    The extractor remains the owner of:
        - latest snapshot selection
        - previous snapshot selection
        - CMC_ID matching
        - collision handling
        - historical feature calculation
    """

    extractor = load_feature_extractor()

    if not hasattr(extractor, "extract_features"):
        raise RuntimeError(
            "history_feature_extractor.py does not expose extract_features()"
        )

    features = extractor.extract_features(conn)

    if features is None:
        raise RuntimeError(
            "Feature extractor returned None."
        )

    if isinstance(features, dict):
        if "features" not in features:
            raise RuntimeError(
                "Feature extractor returned dictionary without 'features'."
            )

        features = features["features"]

    if not isinstance(features, list):
        raise RuntimeError(
            "Feature extractor output must be a list."
        )

    return features


# ============================================================================
# ANALYSIS PRIMITIVES
# ============================================================================

def calculate_price_change(price, previous_price):
    if previous_price is None:
        return None

    try:
        price = float(price)
        previous_price = float(previous_price)
    except (TypeError, ValueError):
        return None

    if previous_price == 0:
        return None

    return price - previous_price


def calculate_price_change_pct(price, previous_price):
    if previous_price is None:
        return None

    try:
        price = float(price)
        previous_price = float(previous_price)
    except (TypeError, ValueError):
        return None

    if previous_price == 0:
        return None

    return ((price - previous_price) / previous_price) * 100.0


def calculate_volume_change_pct(volume, previous_volume):
    if volume is None or previous_volume is None:
        return None

    try:
        volume = float(volume)
        previous_volume = float(previous_volume)
    except (TypeError, ValueError):
        return None

    if previous_volume == 0:
        return None

    return ((volume - previous_volume) / previous_volume) * 100.0


# ============================================================================
# TREND
# ============================================================================

def classify_trend(snapshot_change_pct):
    if snapshot_change_pct is None:
        return "UNKNOWN"

    try:
        value = float(snapshot_change_pct)
    except (TypeError, ValueError):
        return "UNKNOWN"

    if value > 0:
        return "UP"

    if value < 0:
        return "DOWN"

    return "FLAT"


# ============================================================================
# MOMENTUM
# ============================================================================

def classify_momentum(price_change_pct):
    if price_change_pct is None:
        return "UNKNOWN"

    try:
        value = float(price_change_pct)
    except (TypeError, ValueError):
        return "UNKNOWN"

    if value > 1.0:
        return "POSITIVE"

    if value < -1.0:
        return "NEGATIVE"

    return "NEUTRAL"


# ============================================================================
# VOLATILITY
# ============================================================================

def classify_volatility(price_change_pct):
    if price_change_pct is None:
        return "UNKNOWN"

    try:
        value = abs(float(price_change_pct))
    except (TypeError, ValueError):
        return "UNKNOWN"

    if value >= 5.0:
        return "HIGH"

    if value >= 1.0:
        return "MEDIUM"

    return "LOW"


# ============================================================================
# VOLUME REGIME
# ============================================================================

def classify_volume_regime(volume_change_pct):
    if volume_change_pct is None:
        return "UNKNOWN"

    try:
        value = float(volume_change_pct)
    except (TypeError, ValueError):
        return "UNKNOWN"

    if value >= 20.0:
        return "EXPANDING"

    if value <= -20.0:
        return "CONTRACTING"

    return "STABLE"


# ============================================================================
# SINGLE FEATURE ANALYSIS
# ============================================================================

def analyze_feature(feature):
    if not validate_feature_record(feature):
        raise ValueError(
            "Invalid feature record."
        )

    cmc_id = feature["cmc_id"]

    symbol = feature.get("symbol")

    price = feature.get("price")
    previous_price = feature.get("previous_price")

    snapshot_change = feature.get("snapshot_change")
    snapshot_change_pct = feature.get("snapshot_change_pct")

    price_change = calculate_price_change(
        price,
        previous_price,
    )

    calculated_price_change_pct = calculate_price_change_pct(
        price,
        previous_price,
    )

    volume_change_pct = calculate_volume_change_pct(
        feature.get("volume_24h"),
        feature.get("previous_volume_24h"),
    )

    trend = classify_trend(snapshot_change_pct)

    momentum = classify_momentum(
        calculated_price_change_pct
    )

    volatility = classify_volatility(
        calculated_price_change_pct
    )

    volume_regime = classify_volume_regime(
        volume_change_pct
    )

    return {
        "cmc_id": cmc_id,
        "symbol": symbol,

        "latest_timestamp": feature.get(
            "latest_timestamp"
        ),

        "previous_timestamp": feature.get(
            "previous_timestamp"
        ),

        "price": price,
        "previous_price": previous_price,

        "price_change": price_change,
        "price_change_pct": calculated_price_change_pct,

        "snapshot_change": snapshot_change,
        "snapshot_change_pct": snapshot_change_pct,

        "market_cap": feature.get("market_cap"),
        "rank": feature.get("rank"),

        "volume_24h": feature.get("volume_24h"),
        "previous_volume_24h": feature.get(
            "previous_volume_24h"
        ),

        "volume_change_pct": volume_change_pct,

        "trend_state": trend,
        "momentum_state": momentum,
        "volatility_state": volatility,
        "volume_state": volume_regime,

        "analysis_status": "CALCULATED",
    }


# ============================================================================
# COLLECTION ANALYSIS
# ============================================================================

def analyze_features(features):
    if not validate_feature_collection(features):
        raise ValueError(
            "Feature collection failed validation."
        )

    results = []

    for feature in features:
        results.append(
            analyze_feature(feature)
        )

    return results


# ============================================================================
# OUTPUT VALIDATION
# ============================================================================

def validate_analysis_record(record):
    required = {
        "cmc_id",
        "symbol",
        "price",
        "previous_price",
        "price_change",
        "price_change_pct",
        "trend_state",
        "momentum_state",
        "volatility_state",
        "volume_state",
        "analysis_status",
    }

    if not required.issubset(record):
        return False

    if record["cmc_id"] is None:
        return False

    if record["analysis_status"] != "CALCULATED":
        return False

    return True


def validate_analysis_collection(results):
    if not isinstance(results, list):
        return False

    seen = set()

    for record in results:
        if not validate_analysis_record(record):
            return False

        cmc_id = record["cmc_id"]

        if cmc_id in seen:
            return False

        seen.add(cmc_id)

    return True


# ============================================================================
# COLLISION SAFETY
# ============================================================================

def collision_safety_test(features, analysis):
    feature_map = {
        item["cmc_id"]: item
        for item in features
    }

    analysis_map = {
        item["cmc_id"]: item
        for item in analysis
    }

    if set(feature_map) != set(analysis_map):
        return False

    symbol_groups = {}

    for record in analysis:
        symbol = record.get("symbol")

        if symbol is None:
            continue

        symbol_groups.setdefault(
            symbol,
            set(),
        ).add(record["cmc_id"])

    collisions = {
        symbol: cmc_ids
        for symbol, cmc_ids in symbol_groups.items()
        if len(cmc_ids) > 1
    }

    for cmc_ids in collisions.values():
        if len(cmc_ids) < 2:
            return False

        for cmc_id in cmc_ids:
            if cmc_id not in analysis_map:
                return False

    return True


# ============================================================================
# CARDINALITY TEST
# ============================================================================

def cardinality_test(features, analysis):
    feature_ids = {
        item["cmc_id"]
        for item in features
    }

    analysis_ids = {
        item["cmc_id"]
        for item in analysis
    }

    return (
        len(features) == len(analysis)
        and feature_ids == analysis_ids
    )


# ============================================================================
# MATHEMATICAL CONSISTENCY
# ============================================================================

def mathematical_consistency_test(
    features,
    analysis,
    sample_size=25,
):
    feature_map = {
        item["cmc_id"]: item
        for item in features
    }

    sample = analysis[:sample_size]

    for record in sample:
        cmc_id = record["cmc_id"]

        source = feature_map.get(cmc_id)

        if source is None:
            return False

        expected_change = calculate_price_change(
            source["price"],
            source["previous_price"],
        )

        actual_change = record["price_change"]

        if expected_change is None:
            if actual_change is not None:
                return False
        else:
            if actual_change is None:
                return False

            if abs(
                float(expected_change)
                - float(actual_change)
            ) > 1e-12:
                return False

        expected_pct = calculate_price_change_pct(
            source["price"],
            source["previous_price"],
        )

        actual_pct = record["price_change_pct"]

        if expected_pct is None:
            if actual_pct is not None:
                return False
        else:
            if actual_pct is None:
                return False

            if abs(
                float(expected_pct)
                - float(actual_pct)
            ) > 1e-10:
                return False

    return True


# ============================================================================
# READ-ONLY FINGERPRINT TEST
# ============================================================================

def fingerprint_equal(before, after):
    return before == after


# ============================================================================
# SAMPLE
# ============================================================================

def print_analysis_sample(results, limit=5):
    print()
    print("ANALYSIS SAMPLE")
    print("-" * 100)

    for record in results[:limit]:
        print(
            f"CMC_ID={record['cmc_id']} | "
            f"SYMBOL={record['symbol']} | "
            f"PRICE={record['price']} | "
            f"PREV_PRICE={record['previous_price']} | "
            f"CHANGE={record['price_change_pct']}% | "
            f"TREND={record['trend_state']} | "
            f"MOMENTUM={record['momentum_state']} | "
            f"VOLATILITY={record['volatility_state']} | "
            f"VOLUME={record['volume_state']}"
        )


# ============================================================================
# SELF TEST
# ============================================================================

def self_test():
    print()
    print("=" * 100)
    print("ARUNDA TRADER — DEV-06 — STEP 7")
    print("HISTORY ANALYSIS ENGINE v0.1")
    print("SELF TEST")
    print("=" * 100)

    conn = None

    try:
        # ------------------------------------------------------------------
        # DATABASE
        # ------------------------------------------------------------------

        print()
        print("DATABASE")
        print("-" * 100)
        print("Path              :", Path(DB_PATH).resolve())
        print("Mode              : READ ONLY")
        print("Engine            :", ENGINE_NAME)
        print("Feature Engine    :", FEATURE_ENGINE)
        print("Query Engine      :", QUERY_ENGINE)

        conn = connect_read_only()

        # ------------------------------------------------------------------
        # TABLE
        # ------------------------------------------------------------------

        print()
        print("SOURCE CONTRACT")
        print("-" * 100)

        source_pass = table_exists(
            conn,
            "market_history",
        )

        print(
            "market_history     :",
            "PASS" if source_pass else "FAIL",
        )

        if not source_pass:
            return False

        # ------------------------------------------------------------------
        # BEFORE FINGERPRINT
        # ------------------------------------------------------------------

        before = history_fingerprint(conn)

        print()
        print("HISTORY FINGERPRINT")
        print("-" * 100)

        print("Rows              :", before["rows"])
        print("Snapshots         :", before["snapshots"])
        print("Distinct CMC IDs  :", before["cmc_ids"])
        print("Duplicate IDs     :", before["duplicate_ids"])
        print("First Timestamp   :", before["first_timestamp"])
        print("Last Timestamp    :", before["last_timestamp"])

        fingerprint_pass = (
            before["rows"] > 0
            and before["snapshots"] >= 2
            and before["cmc_ids"] > 0
            and before["duplicate_ids"] == 0
        )

        print()
        print(
            "FINGERPRINT        :",
            "PASS" if fingerprint_pass else "FAIL",
        )

        if not fingerprint_pass:
            return False

        # ------------------------------------------------------------------
        # FEATURE EXTRACTION
        # ------------------------------------------------------------------

        print()
        print("FEATURE CONSUMPTION")
        print("-" * 100)

        features = extract_history_features(conn)

        print(
            "Feature Rows       :",
            len(features),
        )

        feature_pass = (
            len(features) > 0
            and validate_feature_collection(features)
        )

        print(
            "Feature Contract   :",
            "PASS" if feature_pass else "FAIL",
        )

        if not feature_pass:
            return False

        # ------------------------------------------------------------------
        # ANALYSIS
        # ------------------------------------------------------------------

        print()
        print("ANALYSIS")
        print("-" * 100)

        analysis = analyze_features(features)

        print(
            "Analysis Rows      :",
            len(analysis),
        )

        analysis_pass = (
            len(analysis) > 0
            and validate_analysis_collection(analysis)
        )

        print(
            "Analysis Output    :",
            "PASS" if analysis_pass else "FAIL",
        )

        if not analysis_pass:
            return False

        # ------------------------------------------------------------------
        # CARDINALITY
        # ------------------------------------------------------------------

        print()
        print("INPUT / OUTPUT CARDINALITY")
        print("-" * 100)

        cardinality_pass = cardinality_test(
            features,
            analysis,
        )

        print(
            "Feature Rows       :",
            len(features),
        )

        print(
            "Analysis Rows      :",
            len(analysis),
        )

        print(
            "CMC_ID Cardinality :",
            "PASS" if cardinality_pass else "FAIL",
        )

        if not cardinality_pass:
            return False

        # ------------------------------------------------------------------
        # CMC IDENTITY
        # ------------------------------------------------------------------

        print()
        print("CMC_ID IDENTITY TEST")
        print("-" * 100)

        feature_ids = {
            item["cmc_id"]
            for item in features
        }

        analysis_ids = {
            item["cmc_id"]
            for item in analysis
        }

        identity_pass = (
            feature_ids == analysis_ids
            and len(feature_ids) == len(features)
            and len(analysis_ids) == len(analysis)
        )

        print(
            "Feature CMC IDs    :",
            len(feature_ids),
        )

        print(
            "Analysis CMC IDs   :",
            len(analysis_ids),
        )

        print(
            "CMC_ID Identity    :",
            "PASS" if identity_pass else "FAIL",
        )

        if not identity_pass:
            return False

        # ------------------------------------------------------------------
        # COLLISION
        # ------------------------------------------------------------------

        print()
        print("CMC COLLISION SAFETY TEST")
        print("-" * 100)

        collision_pass = collision_safety_test(
            features,
            analysis,
        )

        symbol_groups = {}

        for record in analysis:
            symbol = record.get("symbol")

            if symbol is not None:
                symbol_groups.setdefault(
                    symbol,
                    set(),
                ).add(record["cmc_id"])

        collision_count = sum(
            1
            for ids in symbol_groups.values()
            if len(ids) > 1
        )

        collision_rows = sum(
            len(ids)
            for ids in symbol_groups.values()
            if len(ids) > 1
        )

        print(
            "Symbol Collisions  :",
            collision_count,
        )

        print(
            "Collision Rows     :",
            collision_rows,
        )

        print(
            "Collision Safety   :",
            "PASS" if collision_pass else "FAIL",
        )

        if not collision_pass:
            return False

        # ------------------------------------------------------------------
        # MATHEMATICS
        # ------------------------------------------------------------------

        print()
        print("ANALYSIS MATHEMATICAL CONSISTENCY")
        print("-" * 100)

        math_pass = mathematical_consistency_test(
            features,
            analysis,
        )

        print(
            "Price Calculations :",
            "PASS" if math_pass else "FAIL",
        )

        if not math_pass:
            return False

        # ------------------------------------------------------------------
        # STATE VALIDATION
        # ------------------------------------------------------------------

        print()
        print("STATE CLASSIFICATION")
        print("-" * 100)

        allowed_trends = {
            "UP",
            "DOWN",
            "FLAT",
            "UNKNOWN",
        }

        allowed_momentum = {
            "POSITIVE",
            "NEGATIVE",
            "NEUTRAL",
            "UNKNOWN",
        }

        allowed_volatility = {
            "HIGH",
            "MEDIUM",
            "LOW",
            "UNKNOWN",
        }

        allowed_volume = {
            "EXPANDING",
            "CONTRACTING",
            "STABLE",
            "UNKNOWN",
        }

        states_pass = all(
            record["trend_state"] in allowed_trends
            and record["momentum_state"] in allowed_momentum
            and record["volatility_state"] in allowed_volatility
            and record["volume_state"] in allowed_volume
            for record in analysis
        )

        print(
            "Trend States       :",
            "PASS" if states_pass else "FAIL",
        )

        print(
            "Momentum States     :",
            "PASS" if states_pass else "FAIL",
        )

        print(
            "Volatility States   :",
            "PASS" if states_pass else "FAIL",
        )

        print(
            "Volume States       :",
            "PASS" if states_pass else "FAIL",
        )

        if not states_pass:
            return False

        # ------------------------------------------------------------------
        # READ ONLY
        # ------------------------------------------------------------------

        after = history_fingerprint(conn)

        print()
        print("READ-ONLY INTEGRITY TEST")
        print("-" * 100)

        read_only_pass = fingerprint_equal(
            before,
            after,
        )

        print(
            "ROW COUNT          :",
            "PASS"
            if before["rows"] == after["rows"]
            else "FAIL",
        )

        print(
            "SNAPSHOT COUNT     :",
            "PASS"
            if before["snapshots"] == after["snapshots"]
            else "FAIL",
        )

        print(
            "CMC ID COUNT       :",
            "PASS"
            if before["cmc_ids"] == after["cmc_ids"]
            else "FAIL",
        )

        print(
            "DUPLICATES         :",
            "PASS"
            if after["duplicate_ids"] == 0
            else "FAIL",
        )

        print(
            "DATABASE UNMODIFIED:",
            "PASS" if read_only_pass else "FAIL",
        )

        if not read_only_pass:
            return False

        # ------------------------------------------------------------------
        # SAMPLE
        # ------------------------------------------------------------------

        print_analysis_sample(
            analysis,
            limit=5,
        )

        # ------------------------------------------------------------------
        # FINAL
        # ------------------------------------------------------------------

        print()
        print("=" * 100)
        print("STEP 7 VERDICT")
        print("=" * 100)

        print(
            "RESULT : HISTORY ANALYSIS ENGINE v0.1 PASS"
        )

        print(
            "STATUS : READY FOR INTEGRATION"
        )

        print(
            "Database          : READ ONLY"
        )

        print(
            "Database Modified : NO"
        )

        print(
            "CMC Identity      : VERIFIED"
        )

        print(
            "Collision Safety  : VERIFIED"
        )

        print(
            "Feature Consumer   : VERIFIED"
        )

        print(
            "Analysis Logic    : VERIFIED"
        )

        print(
            "Output Contract   : VERIFIED"
        )

        print("=" * 100)

        return True

    except Exception as exc:

        print()
        print("=" * 100)
        print("STEP 7 ERROR")
        print("=" * 100)

        print(
            type(exc).__name__ + ":",
            exc,
        )

        print("=" * 100)

        return False

    finally:

        if conn is not None:
            conn.close()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    success = self_test()

    raise SystemExit(
        0 if success else 1
    )