# market_microstructure_engine.py
# ARUNDA MARKET MICROSTRUCTURE ENGINE v0.1

import sqlite3
import time
from datetime import datetime, timezone

DB_PATH = "arunda.db"
INTERVAL = 60


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def connect_db():
    return sqlite3.connect(DB_PATH)


def ensure_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_microstructure (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price REAL,
            market_cap REAL,
            volume_24h REAL,
            change_1h REAL,
            change_24h REAL,
            liquidity_proxy REAL,
            volatility_proxy REAL,
            momentum_proxy REAL,
            market_pressure_proxy REAL,
            data_source TEXT,
            engine_version TEXT
        )
    """)

    conn.commit()


def detect_history_table(conn):
    tables = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
    """).fetchall()

    names = {row[0] for row in tables}

    if "market_history" not in names:
        raise RuntimeError("market_history table not found.")

    return "market_history"


def get_columns(conn, table):
    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return {row[1] for row in rows}


def choose_column(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def load_latest_market_data(conn, table):
    columns = get_columns(conn, table)

    symbol_col = choose_column(
        columns,
        ["symbol", "asset", "ticker"]
    )

    price_col = choose_column(
        columns,
        ["price", "close"]
    )

    timestamp_col = choose_column(
        columns,
        ["timestamp", "created_at", "source_timestamp"]
    )

    market_cap_col = choose_column(
        columns,
        ["market_cap"]
    )

    volume_col = choose_column(
        columns,
        ["volume_24h", "volume"]
    )

    change_1h_col = choose_column(
        columns,
        ["change_1h"]
    )

    change_24h_col = choose_column(
        columns,
        ["change_24h"]
    )

    if not symbol_col:
        raise RuntimeError("market_history has no symbol column.")

    if not price_col:
        raise RuntimeError("market_history has no price/close column.")

    if not timestamp_col:
        raise RuntimeError("market_history has no timestamp column.")

    optional = {
        "market_cap": market_cap_col,
        "volume_24h": volume_col,
        "change_1h": change_1h_col,
        "change_24h": change_24h_col,
    }

    select_parts = [
        f'"{symbol_col}" AS symbol',
        f'"{price_col}" AS price',
        f'"{timestamp_col}" AS timestamp',
    ]

    for alias, column in optional.items():
        if column:
            select_parts.append(f'"{column}" AS {alias}')
        else:
            select_parts.append(f"NULL AS {alias}")

    query = f"""
        SELECT {", ".join(select_parts)}
        FROM "{table}"
        WHERE rowid IN (
            SELECT MAX(rowid)
            FROM "{table}"
            GROUP BY "{symbol_col}"
        )
        ORDER BY "{symbol_col}"
    """

    return conn.execute(query).fetchall()


def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def calculate_microstructure_features(row):
    symbol, price, timestamp, market_cap, volume_24h, change_1h, change_24h = row

    price = safe_float(price)
    market_cap = safe_float(market_cap)
    volume_24h = safe_float(volume_24h)
    change_1h = safe_float(change_1h)
    change_24h = safe_float(change_24h)

    liquidity_proxy = None
    volatility_proxy = None
    momentum_proxy = None
    pressure_proxy = None

    if market_cap and market_cap > 0 and volume_24h is not None:
        liquidity_proxy = volume_24h / market_cap

    if change_1h is not None:
        volatility_proxy = abs(change_1h)

    if change_1h is not None and change_24h is not None:
        momentum_proxy = (
            0.60 * change_1h +
            0.40 * (change_24h / 24.0)
        )

        pressure_proxy = (
            change_1h * 0.70 +
            change_24h * 0.30
        )

    return (
        timestamp or utc_now(),
        symbol,
        price,
        market_cap,
        volume_24h,
        change_1h,
        change_24h,
        liquidity_proxy,
        volatility_proxy,
        momentum_proxy,
        pressure_proxy,
        "CMC_HISTORICAL",
        "MARKET_MICROSTRUCTURE_v0.1",
    )


def write_features(conn, features):
    inserted = 0
    updated = 0

    for feature in features:
        (
            timestamp,
            symbol,
            price,
            market_cap,
            volume_24h,
            change_1h,
            change_24h,
            liquidity_proxy,
            volatility_proxy,
            momentum_proxy,
            pressure_proxy,
            source,
            version,
        ) = feature

        existing = conn.execute("""
            SELECT id
            FROM market_microstructure
            WHERE symbol = ?
              AND timestamp = ?
            LIMIT 1
        """, (symbol, timestamp)).fetchone()

        if existing:
            conn.execute("""
                UPDATE market_microstructure
                SET
                    price = ?,
                    market_cap = ?,
                    volume_24h = ?,
                    change_1h = ?,
                    change_24h = ?,
                    liquidity_proxy = ?,
                    volatility_proxy = ?,
                    momentum_proxy = ?,
                    market_pressure_proxy = ?,
                    data_source = ?,
                    engine_version = ?
                WHERE id = ?
            """, (
                price,
                market_cap,
                volume_24h,
                change_1h,
                change_24h,
                liquidity_proxy,
                volatility_proxy,
                momentum_proxy,
                pressure_proxy,
                source,
                version,
                existing[0],
            ))

            updated += 1

        else:
            conn.execute("""
                INSERT INTO market_microstructure (
                    timestamp,
                    symbol,
                    price,
                    market_cap,
                    volume_24h,
                    change_1h,
                    change_24h,
                    liquidity_proxy,
                    volatility_proxy,
                    momentum_proxy,
                    market_pressure_proxy,
                    data_source,
                    engine_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, feature)

            inserted += 1

    conn.commit()

    return inserted, updated


def print_recent(conn):
    rows = conn.execute("""
        SELECT
            symbol,
            timestamp,
            price,
            liquidity_proxy,
            volatility_proxy,
            momentum_proxy,
            market_pressure_proxy
        FROM market_microstructure
        ORDER BY timestamp DESC, symbol
        LIMIT 20
    """).fetchall()

    print()
    print("=" * 125)
    print("RECENT MICROSTRUCTURE FEATURES")
    print("=" * 125)
    print(
        f"{'SYMBOL':<10}"
        f"{'PRICE':>16}"
        f"{'LIQ':>12}"
        f"{'VOL':>12}"
        f"{'MOM':>12}"
        f"{'PRESSURE':>12}"
    )
    print("-" * 125)

    for row in rows:
        symbol, timestamp, price, liq, vol, mom, pressure = row

        def fmt(value):
            return "NONE" if value is None else f"{value:.6f}"

        print(
            f"{symbol:<10}"
            f"{fmt(price):>16}"
            f"{fmt(liq):>12}"
            f"{fmt(vol):>12}"
            f"{fmt(mom):>12}"
            f"{fmt(pressure):>12}"
        )


def run_cycle(cycle):
    start = time.time()

    print()
    print("=" * 82)
    print(f"MICROSTRUCTURE COLLECTION CYCLE #{cycle}")
    print(f"Time : {utc_now()}")
    print("=" * 82)

    conn = connect_db()

    try:
        ensure_schema(conn)

        history_table = detect_history_table(conn)

        rows = load_latest_market_data(
            conn,
            history_table
        )

        print(f"Historical Assets : {len(rows)}")

        features = []

        for row in rows:
            try:
                features.append(
                    calculate_microstructure_features(row)
                )
            except Exception:
                continue

        inserted, updated = write_features(
            conn,
            features
        )

        total = conn.execute("""
            SELECT COUNT(*)
            FROM market_microstructure
        """).fetchone()[0]

        runtime = time.time() - start

        print()
        print("=" * 82)
        print("MICROSTRUCTURE CYCLE SUMMARY")
        print("=" * 82)
        print(f"Assets Read       : {len(rows)}")
        print(f"Features Generated: {len(features)}")
        print(f"Inserted          : {inserted}")
        print(f"Updated           : {updated}")
        print(f"Total Records     : {total}")
        print(f"Runtime           : {runtime:.2f} sec")
        print("=" * 82)

        print_recent(conn)

        return True

    finally:
        conn.close()


def main():
    print("=" * 82)
    print("        ARUNDA MARKET MICROSTRUCTURE ENGINE v0.1")
    print("=" * 82)
    print("Source          : CMC HISTORICAL DATA")
    print("Database        : arunda.db")
    print("Mode            : MICROSTRUCTURE FEATURE EXTRACTION")
    print("Liquidity       : PROXY ONLY")
    print("Pressure        : PROXY ONLY")
    print("Order Book      : NOT USED")
    print("Whale Data      : NOT USED")
    print("Ranking         : NOT USED")
    print("Opportunity     : NOT USED")
    print("Signal          : NOT USED")
    print("Prediction      : NOT USED")
    print("Risk            : NOT USED")
    print("Execution       : NOT USED")
    print("=" * 82)

    cycle = 0
    successful = 0
    failed = 0

    try:
        while True:
            cycle += 1

            try:
                if run_cycle(cycle):
                    successful += 1
            except Exception as exc:
                failed += 1

                print()
                print("=" * 82)
                print("MICROSTRUCTURE ENGINE ERROR")
                print("=" * 82)
                print(f"{type(exc).__name__}: {exc}")
                print("=" * 82)

            print()
            print("=" * 82)
            print("MICROSTRUCTURE ENGINE STATUS")
            print("=" * 82)
            print(f"Total Cycles : {cycle}")
            print(f"Successful   : {successful}")
            print(f"Failed       : {failed}")
            print(f"Interval     : {INTERVAL} seconds")
            print("Intelligence : NOT USED")
            print("Ranking      : NOT USED")
            print("Signal       : NOT USED")
            print("Risk         : NOT USED")
            print("Execution    : NOT USED")
            print("=" * 82)

            print()
            print(f"Waiting {INTERVAL} seconds...")

            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print()
        print("=" * 82)
        print("       ARUNDA MARKET MICROSTRUCTURE ENGINE STOPPED")
        print("=" * 82)
        print(f"Total Cycles : {cycle}")
        print(f"Successful   : {successful}")
        print(f"Failed       : {failed}")
        print("Database     : PRESERVED")
        print("Reason       : USER INTERRUPT")
        print("=" * 82)


if __name__ == "__main__":
    main()
