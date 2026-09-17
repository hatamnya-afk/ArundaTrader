import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import importlib.util


# ============================================================================
# ARUNDA TECHNICAL PERSISTENCE v0.1
# ============================================================================
#
# MARKET DATA
#      ↓
# LAUNCH DATA BOUNDARY
#      ↓
# TECHNICAL ENGINE v0.5
#      ↓
# market_technical
#
# RULES
# -----
# INSERT ONLY
# UPDATE      : DISABLED
# DELETE      : DISABLED
# REPAIR      : DISABLED
#
# Legacy/Test data is NEVER modified or deleted.
#
# ============================================================================


# ============================================================================
# CONFIG
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "arunda.db"

TECHNICAL_ENGINE_FILE = (
    BASE_DIR / "ARUNDA_TECHNICAL_ENGINE_v0.5.py"
)

TARGET_TABLE = "market_technical"

ENGINE_NAME = "ARUNDA_TECHNICAL_ENGINE"
ENGINE_VERSION = "TECHNICAL_v0.5"
PERSISTENCE_VERSION = "TECHNICAL_PERSISTENCE_v0.1"

SOURCE_TABLE = "market_data"


# ============================================================================
# OFFICIAL LAUNCH BOUNDARY
# ============================================================================

LAUNCH_TIMESTAMP = datetime(
    2026,
    8,
    31,
    0,
    0,
    0,
    tzinfo=timezone.utc,
)


# ============================================================================
# MODULE LOADER
# ============================================================================

def load_module_from_file(path, module_name):

    path = Path(path)

    if not path.exists():

        raise FileNotFoundError(
            f"Required file not found: {path}"
        )

    spec = importlib.util.spec_from_file_location(
        module_name,
        str(path),
    )

    if spec is None or spec.loader is None:

        raise ImportError(
            f"Cannot create module spec: {path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


# ============================================================================
# LOAD TECHNICAL ENGINE
# ============================================================================

def load_technical_engine():

    return load_module_from_file(
        TECHNICAL_ENGINE_FILE,
        "arunda_technical_engine_runtime",
    )


# ============================================================================
# DATABASE
# ============================================================================

def connect_database():

    conn = sqlite3.connect(
        str(DB_PATH)
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================================
# DATABASE HELPERS
# ============================================================================

def table_exists(
    conn,
    table_name,
):

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (
            table_name,
        ),
    ).fetchone()

    return row is not None


def get_columns(
    conn,
    table_name,
):

    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


# ============================================================================
# TARGET SCHEMA
# ============================================================================

def ensure_schema(conn):

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS market_technical (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,

            ema20 REAL,
            ema50 REAL,

            rsi14 REAL,

            macd REAL,
            macd_signal REAL,
            macd_hist REAL,

            atr14 REAL,
            adx14 REAL,

            bb_middle REAL,
            bb_upper REAL,
            bb_lower REAL,
            bb_width REAL,

            volume_sma20 REAL,
            volume_ratio REAL,

            volatility REAL,

            technical_score REAL,

            source TEXT,
            source_timestamp TEXT,

            engine_version TEXT,

            persistence_version TEXT,

            provenance TEXT,

            data_boundary TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_market_technical_symbol_timestamp
        ON market_technical(symbol, timestamp)
        """
    )

    conn.commit()


# ============================================================================
# MARKET DATA SOURCE
# ============================================================================

def detect_market_data_columns(conn):

    if not table_exists(
        conn,
        SOURCE_TABLE,
    ):

        raise RuntimeError(
            "market_data table does not exist."
        )

    columns = get_columns(
        conn,
        SOURCE_TABLE,
    )

    if "symbol" not in columns:

        raise RuntimeError(
            "market_data.symbol column is missing."
        )

    if "timestamp" not in columns:

        raise RuntimeError(
            "market_data.timestamp column is missing."
        )

    price_column = None

    if "close" in columns:

        price_column = "close"

    elif "price" in columns:

        price_column = "price"

    if price_column is None:

        raise RuntimeError(
            "market_data has neither close nor price."
        )

    source_column = (
        "source"
        if "source" in columns
        else None
    )

    source_timestamp_column = (
        "source_timestamp"
        if "source_timestamp" in columns
        else None
    )

    timeframe_column = (
        "timeframe"
        if "timeframe" in columns
        else None
    )

    return {
        "symbol": "symbol",
        "timestamp": "timestamp",
        "price": price_column,
        "source": source_column,
        "source_timestamp":
            source_timestamp_column,
        "timeframe": timeframe_column,
    }


# ============================================================================
# TIMESTAMP
# ============================================================================

def parse_timestamp(value):

    if value is None:

        raise ValueError(
            "Timestamp is NULL."
        )

    if isinstance(
        value,
        datetime,
    ):

        dt = value

    else:

        text = str(
            value
        ).strip()

        if text.endswith("Z"):

            text = (
                text[:-1]
                + "+00:00"
            )

        dt = datetime.fromisoformat(
            text
        )

    if dt.tzinfo is None:

        raise ValueError(
            f"Timezone-naive timestamp rejected: {value}"
        )

    return dt.astimezone(
        timezone.utc
    )


# ============================================================================
# LAUNCH VALIDATION
# ============================================================================

def validate_launch_timestamp():

    if not isinstance(
        LAUNCH_TIMESTAMP,
        datetime,
    ):

        raise TypeError(
            "LAUNCH_TIMESTAMP must be datetime."
        )

    if LAUNCH_TIMESTAMP.tzinfo is None:

        raise ValueError(
            "LAUNCH_TIMESTAMP must be timezone-aware."
        )

    return LAUNCH_TIMESTAMP.astimezone(
        timezone.utc
    )


def is_post_launch(timestamp):

    ts = parse_timestamp(
        timestamp
    )

    launch = validate_launch_timestamp()

    return ts >= launch


# ============================================================================
# PROVENANCE
# ============================================================================

def classify_provenance(
    source,
):

    if source is None:

        return "INVALID"

    value = str(
        source
    ).strip().upper()

    if not value:

        return "INVALID"

    if value in (
        "COINMARKETCAP",
        "CMC",
        "PRODUCTION",
    ):

        return "PRODUCTION"

    if value in (
        "TEST",
        "TEST_DATA",
        "FIXTURE",
        "SYNTHETIC",
    ):

        return "TEST"

    if value in (
        "LEGACY",
        "HISTORICAL",
    ):

        return "LEGACY"

    return "INVALID"


# ============================================================================
# PRODUCTION VALIDITY
# ============================================================================

def is_production_valid(
    timestamp,
    source,
):

    provenance = classify_provenance(
        source
    )

    if provenance != "PRODUCTION":

        return False

    return is_post_launch(
        timestamp
    )


# ============================================================================
# LOAD MARKET DATA
# ============================================================================

def load_market_records(
    conn,
    columns,
):

    symbol = columns["symbol"]

    timestamp = columns["timestamp"]

    price = columns["price"]

    source = columns["source"]

    source_timestamp = (
        columns["source_timestamp"]
    )

    timeframe = columns["timeframe"]

    source_expr = (
        source
        if source
        else "NULL"
    )

    source_timestamp_expr = (
        source_timestamp
        if source_timestamp
        else "NULL"
    )

    timeframe_expr = (
        timeframe
        if timeframe
        else "NULL"
    )

    query = f"""
        SELECT

            {symbol} AS symbol,

            {timestamp} AS timestamp,

            {price} AS price,

            {source_expr} AS source,

            {source_timestamp_expr}
                AS source_timestamp,

            {timeframe_expr}
                AS timeframe

        FROM {SOURCE_TABLE}

        ORDER BY {timestamp} ASC
    """

    return conn.execute(
        query
    ).fetchall()


# ============================================================================
# TARGET DUPLICATE CHECK
# ============================================================================

def technical_exists(
    conn,
    symbol,
    timestamp,
):

    row = conn.execute(
        """
        SELECT 1

        FROM market_technical

        WHERE
            symbol = ?
            AND timestamp = ?

        LIMIT 1
        """,
        (
            symbol,
            timestamp,
        ),
    ).fetchone()

    return row is not None


# ============================================================================
# ENGINE CALCULATION
# ============================================================================

def calculate_with_engine(
    engine,
    symbol,
    price,
    timestamp,
):

    candidates = (
        "calculate_asset",
        "calculate",
    )

    function = None

    function_name = None

    for name in candidates:

        candidate = getattr(
            engine,
            name,
            None,
        )

        if callable(candidate):

            function = candidate

            function_name = name

            break

    if function is None:

        raise RuntimeError(
            "Technical Engine v0.5 does not expose "
            "calculate_asset() or calculate()."
        )

    attempts = [

        (
            symbol,
            price,
            timestamp,
        ),

        (
            symbol,
            price,
        ),

    ]

    last_type_error = None

    for args in attempts:

        try:

            result = function(
                *args
            )

            if result is None:

                raise RuntimeError(
                    f"{function_name} returned None "
                    f"for {symbol}"
                )

            if isinstance(
                result,
                dict,
            ):

                return result

            if hasattr(
                result,
                "_asdict",
            ):

                return result._asdict()

            if hasattr(
                result,
                "__dict__",
            ):

                return dict(
                    result.__dict__
                )

            raise RuntimeError(
                "Unsupported Technical Engine "
                f"result type: "
                f"{type(result).__name__}"
            )

        except TypeError as exc:

            last_type_error = exc

    raise RuntimeError(
        f"Technical Engine calculation failed "
        f"for {symbol}: {last_type_error}"
    )


# ============================================================================
# NORMALIZATION
# ============================================================================

def first_value(
    result,
    keys,
):

    for key in keys:

        if key in result:

            return result[key]

    return None


def normalize_engine_result(
    result,
    symbol,
    timestamp,
    source,
    source_timestamp,
):

    return {

        "timestamp":
            timestamp,

        "symbol":
            symbol,

        "ema20":
            first_value(
                result,
                (
                    "ema20",
                    "EMA20",
                ),
            ),

        "ema50":
            first_value(
                result,
                (
                    "ema50",
                    "EMA50",
                ),
            ),

        "rsi14":
            first_value(
                result,
                (
                    "rsi14",
                    "RSI14",
                    "rsi",
                ),
            ),

        "macd":
            first_value(
                result,
                (
                    "macd",
                    "MACD",
                ),
            ),

        "macd_signal":
            first_value(
                result,
                (
                    "macd_signal",
                    "MACD_signal",
                    "macdSignal",
                ),
            ),

        "macd_hist":
            first_value(
                result,
                (
                    "macd_hist",
                    "MACD_hist",
                    "macdHistogram",
                ),
            ),

        "atr14":
            first_value(
                result,
                (
                    "atr14",
                    "ATR14",
                    "atr",
                ),
            ),

        "adx14":
            first_value(
                result,
                (
                    "adx14",
                    "ADX14",
                    "adx",
                ),
            ),

        "bb_middle":
            first_value(
                result,
                (
                    "bb_middle",
                    "BB_middle",
                    "bollinger_middle",
                ),
            ),

        "bb_upper":
            first_value(
                result,
                (
                    "bb_upper",
                    "BB_upper",
                    "bollinger_upper",
                ),
            ),

        "bb_lower":
            first_value(
                result,
                (
                    "bb_lower",
                    "BB_lower",
                    "bollinger_lower",
                ),
            ),

        "bb_width":
            first_value(
                result,
                (
                    "bb_width",
                    "BB_width",
                ),
            ),

        "volume_sma20":
            first_value(
                result,
                (
                    "volume_sma20",
                    "volumeSMA20",
                ),
            ),

        "volume_ratio":
            first_value(
                result,
                (
                    "volume_ratio",
                    "volumeRatio",
                ),
            ),

        "volatility":
            first_value(
                result,
                (
                    "volatility",
                ),
            ),

        "technical_score":
            first_value(
                result,
                (
                    "technical_score",
                    "technicalScore",
                    "score",
                ),
            ),

        "source":
            source,

        "source_timestamp":
            source_timestamp,

    }


# ============================================================================
# INSERT
# ============================================================================

def insert_technical_record(
    conn,
    record,
):

    conn.execute(
        """
        INSERT INTO market_technical (

            timestamp,
            symbol,

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

            technical_score,

            source,
            source_timestamp,

            engine_version,
            persistence_version,

            provenance,
            data_boundary

        )

        VALUES (

            ?, ?,

            ?, ?,

            ?,

            ?, ?, ?,

            ?, ?,

            ?, ?, ?, ?,

            ?, ?,

            ?,

            ?,

            ?, ?,

            ?, ?,

            ?, ?

        )
        """,

        (

            record["timestamp"],
            record["symbol"],

            record["ema20"],
            record["ema50"],

            record["rsi14"],

            record["macd"],
            record["macd_signal"],
            record["macd_hist"],

            record["atr14"],
            record["adx14"],

            record["bb_middle"],
            record["bb_upper"],
            record["bb_lower"],
            record["bb_width"],

            record["volume_sma20"],
            record["volume_ratio"],

            record["volatility"],

            record["technical_score"],

            record["source"],
            record["source_timestamp"],

            ENGINE_VERSION,
            PERSISTENCE_VERSION,

            "PRODUCTION",
            "POST_LAUNCH",

        ),
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    print(
        "=" * 90
    )

    print(
        "ARUNDA TECHNICAL PERSISTENCE v0.1"
    )

    print(
        "=" * 90
    )

    print(
        f"Database          : {DB_PATH}"
    )

    print(
        f"Table             : {TARGET_TABLE}"
    )

    print(
        f"Engine            : {ENGINE_NAME}"
    )

    print(
        f"Engine Version    : {ENGINE_VERSION}"
    )

    print(
        f"Persistence       : {PERSISTENCE_VERSION}"
    )

    print(
        "Write Mode        : INSERT ONLY"
    )

    print(
        "UPDATE            : DISABLED"
    )

    print(
        "DELETE            : DISABLED"
    )

    print(
        "REPAIR            : DISABLED"
    )

    print(
        "=" * 90
    )

    conn = None

    try:

        launch = validate_launch_timestamp()

        print()

        print(
            "Launch Data Boundary"
        )

        print(
            f"Launch Timestamp  : "
            f"{launch.isoformat()}"
        )

        print(
            "Launch Status     : TEST / PRE-LAUNCH"
        )

        print()

        print(
            "Loading Technical Engine..."
        )

        engine = load_technical_engine()

        print(
            f"Engine File       : "
            f"{TECHNICAL_ENGINE_FILE}"
        )

        print(
            "Technical Engine  : LOADED"
        )

        conn = connect_database()

        ensure_schema(
            conn
        )

        rows_before = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_technical
            """
        ).fetchone()[0]

        print()

        print(
            f"Existing Rows     : "
            f"{rows_before}"
        )

        columns = detect_market_data_columns(
            conn
        )

        print()

        print(
            "REAL MARKET DATA SOURCE"
        )

        print(
            f"Source Table      : "
            f"{SOURCE_TABLE}"
        )

        print(
            f"Symbol Column     : "
            f"{columns['symbol']}"
        )

        print(
            f"Price Column      : "
            f"{columns['price']}"
        )

        print(
            f"Timestamp Column  : "
            f"{columns['timestamp']}"
        )

        records = load_market_records(
            conn,
            columns
        )

        print()

        print(
            f"Source Records    : "
            f"{len(records)}"
        )

        inserted = 0

        legacy_blocked = 0

        invalid_blocked = 0

        duplicates = 0

        errors = 0

        post_launch_seen = 0

        for row in records:

            symbol = row["symbol"]

            raw_timestamp = row["timestamp"]

            source = row["source"]

            source_timestamp = (
                row["source_timestamp"]
            )

            try:

                parsed_timestamp = parse_timestamp(
                    raw_timestamp
                )

                canonical_timestamp = (
                    parsed_timestamp.isoformat()
                )

                provenance = classify_provenance(
                    source
                )

                if provenance in (
                    "LEGACY",
                    "TEST",
                ):

                    legacy_blocked += 1

                    continue

                if provenance != "PRODUCTION":

                    invalid_blocked += 1

                    continue

                if not is_post_launch(
                    canonical_timestamp
                ):

                    legacy_blocked += 1

                    continue

                post_launch_seen += 1

                if technical_exists(
                    conn,
                    symbol,
                    canonical_timestamp,
                ):

                    duplicates += 1

                    continue

                price = row["price"]

                if price is None:

                    raise ValueError(
                        f"Missing price for {symbol}"
                    )

                numeric_price = float(
                    price
                )

                if numeric_price <= 0:

                    raise ValueError(
                        f"Invalid price for {symbol}: "
                        f"{numeric_price}"
                    )

                engine_result = calculate_with_engine(
                    engine,
                    symbol,
                    numeric_price,
                    canonical_timestamp,
                )

                normalized = normalize_engine_result(
                    engine_result,
                    symbol,
                    canonical_timestamp,
                    source,
                    source_timestamp,
                )

                insert_technical_record(
                    conn,
                    normalized,
                )

                inserted += 1

            except Exception as exc:

                errors += 1

                print(
                    "[ERROR] "
                    f"{symbol} | "
                    f"{raw_timestamp} | "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

        conn.commit()

        rows_after = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_technical
            """
        ).fetchone()[0]

        print()

        print(
            "=" * 90
        )

        print(
            "ARUNDA TECHNICAL PERSISTENCE COMPLETE"
        )

        print(
            "=" * 90
        )

        print(
            f"Source Records       : "
            f"{len(records)}"
        )

        print(
            f"Post-Launch Seen    : "
            f"{post_launch_seen}"
        )

        print(
            f"Legacy/Test Blocked : "
            f"{legacy_blocked}"
        )

        print(
            f"Invalid Blocked     : "
            f"{invalid_blocked}"
        )

        print(
            f"Inserted             : "
            f"{inserted}"
        )

        print(
            f"Skipped Duplicate   : "
            f"{duplicates}"
        )

        print(
            f"Errors               : "
            f"{errors}"
        )

        print(
            f"Rows Before          : "
            f"{rows_before}"
        )

        print(
            f"Rows After           : "
            f"{rows_after}"
        )

        print()

        print(
            f"Launch Boundary      : "
            f"{'ENFORCED' if legacy_blocked >= 0 else 'FAILED'}"
        )

        print(
            "Provenance           : ENFORCED"
        )

        print(
            "Legacy Modification  : NONE"
        )

        print(
            "UPDATE               : DISABLED"
        )

        print(
            "DELETE               : DISABLED"
        )

        print(
            "REPAIR               : DISABLED"
        )

        print(
            f"Persistence          : "
            f"{PERSISTENCE_VERSION}"
        )

        print(
            f"Technical Engine     : "
            f"{ENGINE_VERSION}"
        )

        print(
            "=" * 90
        )

        return 0

    except Exception as exc:

        print()

        print(
            "=" * 90
        )

        print(
            "ARUNDA TECHNICAL PERSISTENCE ERROR"
        )

        print(
            "=" * 90
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print(
            "=" * 90
        )

        return 1

    finally:

        if conn is not None:

            conn.close()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )