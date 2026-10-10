import os
import sqlite3
import time
import json
import importlib.util
from datetime import datetime, timezone

import requests


# ============================================================================
# ARUNDA MARKET SNAPSHOT ENGINE v0.6
# ============================================================================
#
# PURPOSE
# -------
# دریافت و ذخیره REAL MARKET DATA از CoinMarketCap
#
# CP7-G ADDITION
# --------------
# Expose the REAL CURRENT-RUN market snapshot payload through stdout.
#
# IMPORTANT
# ---------
# This identity payload:
#     - contains only real same-cycle market data
#     - does not create an ID
#     - does not use DB row IDs
#     - does not use UUID/random values
#     - does not use timestamp as an ID
#     - does not modify database schema
#     - does not modify market-data business logic
#
# The pipeline consumes this payload and creates the deterministic
# SHA-256 snapshot identity.
#
# ============================================================================


# ============================================================================
# CONFIG
# ============================================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "arunda.db"
)

CONTRACT_FILE = os.path.join(
    BASE_DIR,
    "ARUNDA_LAUNCH_DATA_CONTRACT_v0.1.py"
)

SOURCE = "COINMARKETCAP"

TIMEFRAME = "SNAPSHOT"

ENGINE_VERSION = "MARKET_SNAPSHOT_CMC_v0.6"

CMC_URL = (
    "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
)

REQUEST_TIMEOUT = 15


# ============================================================================
# TEST UNIVERSE
# ============================================================================

ASSETS = {
    "BTC": 1,
    "ETH": 1027,
    "SOL": 5426,
    "XRP": 52,
    "ADA": 2010,
    "DOGE": 74,
    "SHIB": 5994,
    "LINK": 1975,
    "AVAX": 5805,
    "DOT": 6636,
    "LTC": 2,
    "UNI": 7083,
    "AAVE": 7278,
    "SUI": 20947,
    "NEAR": 6535,
}


# ============================================================================
# LAUNCH CONTRACT LOADER
# ============================================================================

def load_launch_contract():

    spec = importlib.util.spec_from_file_location(
        "arunda_launch_data_contract_runtime",
        CONTRACT_FILE
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to load Launch Data Contract."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    import sys

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


# ============================================================================
# LOAD CONTRACT
# ============================================================================

LAUNCH_CONTRACT = load_launch_contract()


# ============================================================================
# LAUNCH TIMESTAMP
# ============================================================================

def get_launch_timestamp():

    value = getattr(
        LAUNCH_CONTRACT,
        "LAUNCH_TIMESTAMP",
        None
    )

    if value is None:
        raise RuntimeError(
            "LAUNCH_TIMESTAMP is not defined."
        )

    if isinstance(
        value,
        datetime
    ):

        timestamp = value

    elif isinstance(
        value,
        str
    ):

        timestamp = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

    else:

        raise RuntimeError(
            "Invalid LAUNCH_TIMESTAMP type."
        )

    if timestamp.tzinfo is None:
        raise RuntimeError(
            "LAUNCH_TIMESTAMP must be timezone-aware."
        )

    return timestamp.astimezone(
        timezone.utc
    )


LAUNCH_TIMESTAMP = get_launch_timestamp()


# ============================================================================
# CURRENT TIME
# ============================================================================

def utc_now():

    return datetime.now(
        timezone.utc
    )


# ============================================================================
# TIMESTAMP PARSER
# ============================================================================

def parse_timestamp(value):

    if value is None:
        raise ValueError(
            "Timestamp is None."
        )

    if isinstance(
        value,
        datetime
    ):

        timestamp = value

    elif isinstance(
        value,
        str
    ):

        timestamp = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

    else:

        raise ValueError(
            f"Unsupported timestamp type: "
            f"{type(value).__name__}"
        )

    if timestamp.tzinfo is None:
        raise ValueError(
            "Timestamp must be timezone-aware."
        )

    return timestamp.astimezone(
        timezone.utc
    )


# ============================================================================
# PRODUCTION TIMESTAMP VALIDATION
# ============================================================================

def is_post_launch(timestamp):

    timestamp = parse_timestamp(
        timestamp
    )

    return timestamp >= LAUNCH_TIMESTAMP


# ============================================================================
# PROVENANCE VALIDATION
# ============================================================================

def is_production_provenance():

    return SOURCE == "COINMARKETCAP"


# ============================================================================
# PRODUCTION DATA DECISION
# ============================================================================

def production_data_allowed(
    timestamp
):

    parsed = parse_timestamp(
        timestamp
    )

    if not is_production_provenance():
        return False

    if parsed < LAUNCH_TIMESTAMP:
        return False

    return True


# ============================================================================
# DATABASE
# ============================================================================

def connect_database():

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.execute(
        "PRAGMA journal_mode=WAL"
    )

    return conn


# ============================================================================
# SCHEMA
# ============================================================================

def ensure_schema(conn):

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS market_data (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            timestamp TEXT,
            symbol TEXT,
            timeframe TEXT,

            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,

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

            price_change_1h REAL,
            price_change_24h REAL,

            market_cap REAL,
            volume_24h REAL,

            source_latency_ms REAL,

            engine_version TEXT
        )
        """
    )

    conn.commit()


# ============================================================================
# API KEY
# ============================================================================

def get_api_key():

    key = os.getenv(
        "CMC_API_KEY"
    )

    if not key:

        raise RuntimeError(
            "CMC_API_KEY environment variable is not set."
        )

    return key


# ============================================================================
# CMC REQUEST
# ============================================================================

def fetch_cmc():

    api_key = get_api_key()

    symbols = ",".join(
        ASSETS.keys()
    )

    headers = {

        "X-CMC_PRO_API_KEY": api_key,

        "Accept": "application/json",
    }

    params = {

        "symbol": symbols,

        "convert": "USD",
    }

    started = time.perf_counter()

    response = requests.get(

        CMC_URL,

        headers=headers,

        params=params,

        timeout=REQUEST_TIMEOUT,
    )

    latency_ms = (

        time.perf_counter()
        - started

    ) * 1000.0

    response.raise_for_status()

    payload = response.json()

    return payload, latency_ms


# ============================================================================
# EXTRACTION
# ============================================================================

def extract_assets(payload):

    result = []

    data = payload.get(
        "data",
        {}
    )

    for symbol in ASSETS:

        item = data.get(
            symbol
        )

        if not item:
            continue

        quote = (
            item
            .get(
                "quote",
                {}
            )
            .get(
                "USD",
                {}
            )
        )

        price = quote.get(
            "price"
        )

        change_1h = quote.get(
            "percent_change_1h"
        )

        change_24h = quote.get(
            "percent_change_24h"
        )

        market_cap = quote.get(
            "market_cap"
        )

        volume_24h = quote.get(
            "volume_24h"
        )

        source_timestamp = item.get(
            "last_updated"
        )

        if source_timestamp is None:

            raise RuntimeError(
                f"Missing source timestamp for {symbol}"
            )

        result.append({

            "symbol": symbol,

            "price": price,

            "change_1h": change_1h,

            "change_24h": change_24h,

            "market_cap": market_cap,

            "volume_24h": volume_24h,

            "source_timestamp":
                source_timestamp,
        })

    return result


# ============================================================================
# VALIDATION
# ============================================================================

def validate_asset_data(data):

    symbol = data.get(
        "symbol"
    )

    if symbol not in ASSETS:

        raise RuntimeError(
            f"Unexpected asset: {symbol}"
        )

    price = data.get(
        "price"
    )

    if price is None:

        raise RuntimeError(
            f"Missing price for {symbol}"
        )

    price = float(
        price
    )

    if price <= 0:

        raise RuntimeError(
            f"Invalid price for {symbol}: {price}"
        )

    source_timestamp = parse_timestamp(
        data.get(
            "source_timestamp"
        )
    )

    if not production_data_allowed(
        source_timestamp
    ):

        raise RuntimeError(
            f"Source timestamp is before launch for {symbol}"
        )

    return True


# ============================================================================
# CP7-G CURRENT RUNTIME SNAPSHOT PAYLOAD
# ============================================================================
#
# This is NOT an ID.
#
# It is the exact same-cycle real market payload from this producer.
#
# No DB IDs.
# No random values.
# No generated values.
# No timestamp-as-ID.
#
# ============================================================================

def build_current_runtime_snapshot_payload(
    assets,
    timestamp
):

    if not isinstance(
        assets,
        list
    ):

        raise RuntimeError(
            "CP7-G: assets payload must be a list."
        )

    if len(assets) != len(ASSETS):

        raise RuntimeError(
            "CP7-G: current runtime snapshot must "
            f"contain exactly {len(ASSETS)} assets. "
            f"Received {len(assets)}."
        )

    returned_symbols = []

    snapshot_assets = []

    for data in assets:

        validate_asset_data(
            data
        )

        symbol = data["symbol"]

        returned_symbols.append(
            symbol
        )

        snapshot_assets.append({

            "asset": symbol,

            "timestamp": timestamp,

            "price": data["price"],

            "change_1h": data["change_1h"],

            "change_24h": data["change_24h"],

            "market_cap": data["market_cap"],

            "volume_24h": data["volume_24h"],
        })

    expected_symbols = set(
        ASSETS.keys()
    )

    actual_symbols = set(
        returned_symbols
    )

    missing = sorted(
        expected_symbols
        -
        actual_symbols
    )

    extra = sorted(
        actual_symbols
        -
        expected_symbols
    )

    duplicates = sorted(
        {
            symbol
            for symbol in returned_symbols
            if returned_symbols.count(symbol) > 1
        }
    )

    if missing or extra or duplicates:

        raise RuntimeError(
            "CP7-G: current runtime snapshot "
            "asset coverage failure: "
            f"missing={missing}, "
            f"extra={extra}, "
            f"duplicates={duplicates}"
        )

    return {
        "runtime_source": "CURRENT_SUBPROCESS_RUN",

        "engine_version": ENGINE_VERSION,

        "source": SOURCE,

        "timeframe": TIMEFRAME,

        "timestamp": timestamp,

        "assets": snapshot_assets,
    }


# ============================================================================
# CP7-G RUNTIME SNAPSHOT EMITTER
# ============================================================================

def emit_current_runtime_snapshot(
    snapshot_payload
):

    print(
        "ARUNDA_CURRENT_RUNTIME_SNAPSHOT="
        +
        json.dumps(
            snapshot_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


# ============================================================================
# DUPLICATE CHECK
# ============================================================================

def record_exists(

    conn,
    symbol,
    timestamp
):

    row = conn.execute(

        """
        SELECT 1
        FROM market_data

        WHERE
            symbol = ?
            AND timestamp = ?
            AND source = ?
            AND timeframe = ?

        LIMIT 1
        """,

        (
            symbol,
            timestamp,
            SOURCE,
            TIMEFRAME,
        ),
    ).fetchone()

    return row is not None


# ============================================================================
# INSERT SNAPSHOT
# ============================================================================

def insert_snapshot(

    conn,
    symbol,
    timestamp,
    data,
    latency_ms
):

    if not production_data_allowed(
        timestamp
    ):

        return "BLOCKED"

    if record_exists(

        conn,
        symbol,
        timestamp
    ):

        return "DUPLICATE"

    conn.execute(

        """
        INSERT INTO market_data (

            timestamp,
            symbol,
            timeframe,

            open,
            high,
            low,
            close,
            volume,

            source,
            source_timestamp,

            price_change_1h,
            price_change_24h,

            market_cap,
            volume_24h,

            source_latency_ms,

            engine_version
        )

        VALUES (

            ?, ?, ?,

            ?, ?, ?, ?, ?,

            ?, ?,

            ?, ?,

            ?, ?,

            ?, ?
        )
        """,

        (

            timestamp,

            symbol,

            TIMEFRAME,

            data["price"],
            data["price"],
            data["price"],
            data["price"],

            data["volume_24h"],

            SOURCE,

            data["source_timestamp"],

            data["change_1h"],
            data["change_24h"],

            data["market_cap"],
            data["volume_24h"],

            latency_ms,

            ENGINE_VERSION,
        ),
    )

    return "INSERTED"


# ============================================================================
# COUNT
# ============================================================================

def count_records(conn):

    row = conn.execute(

        """
        SELECT COUNT(*)
        FROM market_data

        WHERE
            source = ?
            AND timeframe = ?
        """,

        (
            SOURCE,
            TIMEFRAME,
        ),
    ).fetchone()

    return int(
        row[0]
    )


def count_symbol_records(

    conn,
    symbol
):

    row = conn.execute(

        """
        SELECT COUNT(*)
        FROM market_data

        WHERE
            source = ?
            AND timeframe = ?
            AND symbol = ?
        """,

        (
            SOURCE,
            TIMEFRAME,
            symbol,
        ),
    ).fetchone()

    return int(
        row[0]
    )


# ============================================================================
# DISPLAY
# ============================================================================

def show_universe_status(conn):

    print()

    print(
        "SNAPSHOT HISTORY BY ASSET"
    )

    print(
        "-" * 78
    )

    for symbol in ASSETS:

        count = count_symbol_records(
            conn,
            symbol
        )

        print(

            f"{symbol:<6} | "
            f"SNAPSHOTS={count:<5} | "
            f"STATUS={'COLLECTING' if count < 60 else 'READY'}"
        )


def show_recent_snapshots(conn):

    rows = conn.execute(

        """
        SELECT

            symbol,
            timestamp,
            close,
            price_change_1h,
            price_change_24h,
            source

        FROM market_data

        WHERE
            source = ?
            AND timeframe = ?

        ORDER BY id DESC

        LIMIT 20
        """,

        (
            SOURCE,
            TIMEFRAME,
        ),
    ).fetchall()

    print()

    print(
        "RECENT MARKET SNAPSHOTS"
    )

    print(
        "-" * 100
    )

    if not rows:

        print(
            "NO SNAPSHOT RECORDS"
        )

        return

    for row in rows:

        symbol = row[0]

        timestamp = row[1]

        close = row[2]

        change_1h = row[3]

        change_24h = row[4]

        h1 = (

            f"{change_1h:+.2f}%"

            if change_1h is not None

            else "N/A"
        )

        h24 = (

            f"{change_24h:+.2f}%"

            if change_24h is not None

            else "N/A"
        )

        print(

            f"{symbol:<6} | "
            f"{timestamp} | "
            f"{close:>18,.6f} | "
            f"1H {h1:>9} | "
            f"24H {h24:>9}"
        )


# ============================================================================
# MAIN
# ============================================================================

def main():

    started_total = time.perf_counter()

    print(
        "=" * 78
    )

    print(
        "          ARUNDA MARKET SNAPSHOT ENGINE v0.6"
    )

    print(
        "=" * 78
    )

    print(
        f"Source            : {SOURCE}"
    )

    print(
        f"Database          : {DB_PATH}"
    )

    print(
        f"Universe           : {len(ASSETS)} assets"
    )

    print(
        "Universe Mode      : TEST / EXTENSIBLE"
    )

    print(
        f"Timeframe          : {TIMEFRAME}"
    )

    print(
        "Purpose            : REAL MARKET DATA COLLECTION"
    )

    print(
        "Analysis           : NOT USED"
    )

    print(
        "Signal             : NOT USED"
    )

    print(
        "Risk               : NOT USED"
    )

    print(
        "Execution          : NOT USED"
    )

    print(
        f"Launch Boundary    : "
        f"{LAUNCH_TIMESTAMP.isoformat()}"
    )

    print(
        "Provenance         : PRODUCTION"
    )

    print(
        "Legacy Data        : BLOCKED / UNMODIFIED"
    )

    print(
        "=" * 78
    )

    conn = None

    try:

        conn = connect_database()

        print()

        print(
            "Checking market-data schema..."
        )

        ensure_schema(
            conn
        )

        before = count_records(
            conn
        )

        print(
            f"Existing snapshots : {before}"
        )

        print()

        print(
            "Current UTC         : "
            f"{utc_now().isoformat()}"
        )

        print(
            "Launch status       : "
            + (
                "LIVE / POST-LAUNCH"
                if utc_now() >= LAUNCH_TIMESTAMP
                else "TEST / PRE-LAUNCH"
            )
        )

        print()

        print(
            "Fetching REAL CMC market data..."
        )

        payload, latency_ms = fetch_cmc()

        print(

            f"CMC API : ONLINE | "
            f"Latency {latency_ms:.0f} ms"
        )

        assets = extract_assets(
            payload
        )

        print()

        print(
            f"CMC assets returned : {len(assets)}"
        )

        print(
            f"Expected assets     : {len(ASSETS)}"
        )

        print()

        print(

            f"{'ASSET':<8}"
            f"{'PRICE':>20}"
            f"{'1H %':>11}"
            f"{'24H %':>11}"
            f"{'HISTORY':>12}"
            f"{'STATUS':>18}"
        )

        print(
            "-" * 92
        )

        inserted = 0

        duplicates = 0

        blocked = 0

        errors = 0

        missing = 0

        # ====================================================================
        # ONE AUTHORITATIVE CURRENT CYCLE TIMESTAMP
        # ====================================================================

        timestamp = utc_now().isoformat()

        returned_symbols = set()

        # ====================================================================
        # HARD LAUNCH CHECK
        # ====================================================================

        if not production_data_allowed(
            timestamp
        ):

            print()

            print(
                "LAUNCH BOUNDARY STATUS : BLOCKED"
            )

            print(
                "Current timestamp is before LAUNCH_TIMESTAMP."
            )

            print(
                "No market_data rows will be written."
            )

            print()

            return 0

        # ====================================================================
        # CP7-G CURRENT RUNTIME SNAPSHOT
        # ====================================================================
        #
        # Build and expose identity source BEFORE DB insertion.
        #
        # The payload contains only real same-cycle data.
        #
        # ====================================================================

        current_runtime_snapshot = (
            build_current_runtime_snapshot_payload(
                assets,
                timestamp
            )
        )

        emit_current_runtime_snapshot(
            current_runtime_snapshot
        )

        # ====================================================================
        # INSERT
        # ====================================================================

        for data in assets:

            symbol = data["symbol"]

            returned_symbols.add(
                symbol
            )

            try:

                # Existing validation retained.
                validate_asset_data(
                    data
                )

                result = insert_snapshot(

                    conn,

                    symbol,

                    timestamp,

                    data,

                    latency_ms,
                )

                history = count_symbol_records(

                    conn,
                    symbol
                )

                if result == "INSERTED":

                    inserted += 1

                    status = "INSERTED"

                elif result == "DUPLICATE":

                    duplicates += 1

                    status = "DUPLICATE"

                else:

                    blocked += 1

                    status = "BLOCKED"

                change_1h = data["change_1h"]

                change_24h = data["change_24h"]

                h1 = (

                    f"{float(change_1h):.2f}%"

                    if change_1h is not None

                    else "N/A"
                )

                h24 = (

                    f"{float(change_24h):.2f}%"

                    if change_24h is not None

                    else "N/A"
                )

                print(

                    f"{symbol:<8}"

                    f"{float(data['price']):>20,.6f}"

                    f"{h1:>11}"

                    f"{h24:>11}"

                    f"{history:>12}"

                    f"{status:>18}"
                )

            except Exception as exc:

                errors += 1

                print(

                    f"{symbol:<8}"
                    f"ERROR | {type(exc).__name__}: {exc}"
                )

        # ====================================================================
        # MISSING
        # ====================================================================

        missing_symbols = (

            set(ASSETS.keys())
            -
            returned_symbols
        )

        for symbol in sorted(
            missing_symbols
        ):

            missing += 1

            history = count_symbol_records(

                conn,
                symbol
            )

            print(

                f"{symbol:<8}"
                f"{'N/A':>20}"
                f"{'N/A':>11}"
                f"{'N/A':>11}"
                f"{history:>12}"
                f"{'CMC_MISSING':>18}"
            )

        conn.commit()

        after = count_records(
            conn
        )

        elapsed = (

            time.perf_counter()
            - started_total
        )

        print()

        print(
            "=" * 78
        )

        print(
            "              SNAPSHOT ENGINE SUMMARY"
        )

        print(
            "=" * 78
        )

        print(
            f"Expected Assets      : {len(ASSETS)}"
        )

        print(
            f"CMC Returned         : {len(assets)}"
        )

        print(
            f"Inserted             : {inserted}"
        )

        print(
            f"Duplicates           : {duplicates}"
        )

        print(
            f"Launch Blocked       : {blocked}"
        )

        print(
            f"Missing              : {missing}"
        )

        print(
            f"Errors               : {errors}"
        )

        print(
            f"Records Before       : {before}"
        )

        print(
            f"Records After        : {after}"
        )

        print(
            f"Records New          : {inserted}"
        )

        print(
            f"CMC Latency          : {latency_ms:.0f} ms"
        )

        print(
            f"Run Time             : {elapsed:.2f} sec"
        )

        print(
            f"Launch Boundary      : "
            f"{LAUNCH_TIMESTAMP.isoformat()}"
        )

        print(
            "Legacy Modification  : NONE"
        )

        print(
            f"Engine               : {ENGINE_VERSION}"
        )

        print(
            "=" * 78
        )

        show_universe_status(
            conn
        )

        show_recent_snapshots(
            conn
        )

        print()

        print(
            "=" * 78
        )

        print(
            "          MARKET SNAPSHOT ENGINE v0.6 COMPLETE"
        )

        print(
            "=" * 78
        )

        if errors == 0 and inserted > 0:

            print(
                "SNAPSHOT STATUS : SUCCESS"
            )

        elif (
            errors == 0
            and inserted == 0
            and blocked == 0
        ):

            print(
                "SNAPSHOT STATUS : NO NEW DATA"
            )

        elif inserted > 0:

            print(
                "SNAPSHOT STATUS : PARTIAL"
            )

        else:

            print(
                "SNAPSHOT STATUS : FAILED"
            )

        print(
            "=" * 78
        )

        return 0

    except Exception as exc:

        print()

        print(
            "=" * 78
        )

        print(
            "          MARKET SNAPSHOT ENGINE ERROR"
        )

        print(
            "=" * 78
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print(
            "=" * 78
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