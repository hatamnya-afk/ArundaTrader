import os
import sqlite3
import time
from datetime import datetime, timezone

import requests


# ============================================================================
# ARUNDA MARKET UNIVERSE ENGINE v0.3.1
# ============================================================================

DB_PATH = "arunda.db"

SOURCE = "COINMARKETCAP"
ENGINE_VERSION = "MARKET_UNIVERSE_CMC_v0.3.1"

CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"

BATCH_SIZE = 500
MAX_PAGES = 20
MAX_ASSETS = 10000

REQUEST_TIMEOUT = 30


# ============================================================================
# DATABASE
# ============================================================================

def connect_database():

    conn = sqlite3.connect(DB_PATH)

    conn.execute("PRAGMA journal_mode=WAL")

    return conn


# ============================================================================
# SCHEMA
# ============================================================================

REQUIRED_COLUMNS = {
    "cmc_id": "INTEGER",
    "name": "TEXT",
    "symbol": "TEXT",
    "slug": "TEXT",
    "cmc_rank": "INTEGER",
    "price": "REAL",
    "market_cap": "REAL",
    "volume_24h": "REAL",
    "percent_change_1h": "REAL",
    "percent_change_24h": "REAL",
    "percent_change_7d": "REAL",
    "circulating_supply": "REAL",
    "total_supply": "REAL",
    "max_supply": "REAL",
    "num_market_pairs": "INTEGER",
    "date_added": "TEXT",
    "last_updated": "TEXT",
    "is_active": "INTEGER",
    "source": "TEXT",
    "engine_version": "TEXT",
    "updated_at": "TEXT",
}


def ensure_schema(conn):

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS market_universe (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cmc_id INTEGER,
            name TEXT,
            symbol TEXT,
            slug TEXT,
            cmc_rank INTEGER,
            price REAL,
            market_cap REAL,
            volume_24h REAL,
            percent_change_1h REAL,
            percent_change_24h REAL,
            percent_change_7d REAL,
            circulating_supply REAL,
            total_supply REAL,
            max_supply REAL,
            num_market_pairs INTEGER,
            date_added TEXT,
            last_updated TEXT,
            is_active INTEGER,
            source TEXT,
            engine_version TEXT,
            updated_at TEXT
        )
        """
    )

    existing_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(market_universe)"
        ).fetchall()
    }

    added = 0

    for column, column_type in REQUIRED_COLUMNS.items():

        if column not in existing_columns:

            conn.execute(
                f"""
                ALTER TABLE market_universe
                ADD COLUMN {column} {column_type}
                """
            )

            added += 1

    conn.commit()

    return added


# ============================================================================
# API KEY
# ============================================================================

def get_api_key():

    key = os.getenv("CMC_API_KEY")

    if not key:

        raise RuntimeError(
            "CMC_API_KEY environment variable is not set."
        )

    return key


# ============================================================================
# CMC REQUEST
# ============================================================================

def fetch_page(api_key, start, limit):

    headers = {
        "X-CMC_PRO_API_KEY": api_key,
        "Accept": "application/json",
        "User-Agent": "ArundaTrader/0.3.1",
    }

    # IMPORTANT:
    # Keep this request minimal.
    # No aux / cryptocurrency_type parameters.
    # They are not required for Universe Discovery.

    params = {
        "start": start,
        "limit": limit,
        "convert": "USD",
        "sort": "market_cap",
        "sort_dir": "desc",
    }

    started = time.perf_counter()

    response = requests.get(
        CMC_URL,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    latency_ms = (
        time.perf_counter() - started
    ) * 1000.0

    if response.status_code != 200:

        try:
            error_payload = response.json()

            error_text = (
                error_payload
                .get("status", {})
                .get("error_message")
            )

        except Exception:

            error_text = response.text[:500]

        raise RuntimeError(
            f"CMC HTTP {response.status_code}: {error_text}"
        )

    payload = response.json()

    return payload, latency_ms


# ============================================================================
# UPSERT
# ============================================================================

def upsert_asset(conn, item):

    quote = (
        item
        .get("quote", {})
        .get("USD", {})
    )

    now = datetime.now(
        timezone.utc
    ).isoformat()

    cmc_id = item.get("id")

    existing = conn.execute(
        """
        SELECT id
        FROM market_universe
        WHERE cmc_id = ?
        LIMIT 1
        """,
        (cmc_id,)
    ).fetchone()

    values = (
        item.get("name"),
        item.get("symbol"),
        item.get("slug"),
        item.get("cmc_rank"),

        quote.get("price"),
        quote.get("market_cap"),
        quote.get("volume_24h"),

        quote.get("percent_change_1h"),
        quote.get("percent_change_24h"),
        quote.get("percent_change_7d"),

        item.get("circulating_supply"),
        item.get("total_supply"),
        item.get("max_supply"),

        item.get("num_market_pairs"),

        item.get("date_added"),
        item.get("last_updated"),

        1,

        SOURCE,
        ENGINE_VERSION,
        now,
    )

    if existing:

        conn.execute(
            """
            UPDATE market_universe

            SET
                name = ?,
                symbol = ?,
                slug = ?,
                cmc_rank = ?,
                price = ?,
                market_cap = ?,
                volume_24h = ?,
                percent_change_1h = ?,
                percent_change_24h = ?,
                percent_change_7d = ?,
                circulating_supply = ?,
                total_supply = ?,
                max_supply = ?,
                num_market_pairs = ?,
                date_added = ?,
                last_updated = ?,
                is_active = ?,
                source = ?,
                engine_version = ?,
                updated_at = ?

            WHERE cmc_id = ?
            """,
            values + (cmc_id,)
        )

        return "UPDATED"

    conn.execute(
        """
        INSERT INTO market_universe (

            cmc_id,
            name,
            symbol,
            slug,
            cmc_rank,

            price,
            market_cap,
            volume_24h,

            percent_change_1h,
            percent_change_24h,
            percent_change_7d,

            circulating_supply,
            total_supply,
            max_supply,

            num_market_pairs,

            date_added,
            last_updated,

            is_active,

            source,
            engine_version,
            updated_at

        )

        VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?,
            ?, ?,
            ?,
            ?, ?, ?
        )
        """,
        (
            cmc_id,
            *values
        )
    )

    return "INSERTED"


# ============================================================================
# COUNTS
# ============================================================================

def get_counts(conn):

    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_universe
        """
    ).fetchone()[0]

    active = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_universe
        WHERE is_active = 1
        """
    ).fetchone()[0]

    return total, active


# ============================================================================
# DISPLAY
# ============================================================================

def show_top_assets(conn):

    rows = conn.execute(
        """
        SELECT
            cmc_rank,
            symbol,
            name,
            price,
            market_cap,
            volume_24h
        FROM market_universe
        WHERE is_active = 1
        ORDER BY cmc_rank ASC
        LIMIT 30
        """
    ).fetchall()

    print()

    print(
        "TOP UNIVERSE ASSETS"
    )

    print(
        "-" * 110
    )

    print(
        f"{'RANK':<7}"
        f"{'SYMBOL':<10}"
        f"{'NAME':<25}"
        f"{'PRICE':>15}"
        f"{'MARKET CAP':>20}"
        f"{'VOLUME 24H':>20}"
    )

    print(
        "-" * 110
    )

    for row in rows:

        rank = row[0]
        symbol = row[1] or ""
        name = row[2] or ""

        price = row[3]
        market_cap = row[4]
        volume = row[5]

        price_text = (
            f"{price:,.8f}"
            if price is not None
            else "N/A"
        )

        market_cap_text = (
            f"{market_cap:,.0f}"
            if market_cap is not None
            else "N/A"
        )

        volume_text = (
            f"{volume:,.0f}"
            if volume is not None
            else "N/A"
        )

        print(
            f"{str(rank):<7}"
            f"{symbol:<10}"
            f"{name[:24]:<25}"
            f"{price_text:>15}"
            f"{market_cap_text:>20}"
            f"{volume_text:>20}"
        )


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 78)

    print(
        "             ARUNDA MARKET UNIVERSE ENGINE v0.3.1"
    )

    print("=" * 78)

    print(
        f"Source         : {SOURCE}"
    )

    print(
        f"Database       : {DB_PATH}"
    )

    print(
        "Universe Scope : BROAD CRYPTO MARKET"
    )

    print(
        f"Batch Size     : {BATCH_SIZE}"
    )

    print(
        f"Max Pages      : {MAX_PAGES}"
    )

    print(
        f"Max Assets     : {MAX_ASSETS}"
    )

    print(
        "Mode           : PAGINATED DISCOVERY"
    )

    print(
        "Ranking        : NOT USED"
    )

    print(
        "Opportunity    : NOT USED"
    )

    print(
        "Signal         : NOT USED"
    )

    print(
        "Risk           : NOT USED"
    )

    print(
        "Execution      : NOT USED"
    )

    print("=" * 78)

    started_total = time.perf_counter()

    conn = None

    pages_successful = 0
    pages_failed = 0
    assets_returned = 0
    inserted = 0
    updated = 0

    try:

        conn = connect_database()

        print()

        print(
            "Checking universe schema..."
        )

        schema_added = ensure_schema(
            conn
        )

        print(
            f"Schema columns added : {schema_added}"
        )

        total_before, active_before = get_counts(
            conn
        )

        print(
            f"Existing Universe : {total_before}"
        )

        print()

        print(
            "Checking CMC API..."
        )

        api_key = get_api_key()

        print(
            "CMC API KEY : AVAILABLE"
        )

        print()

        print(
            "Starting paginated discovery..."
        )

        for page in range(
            1,
            MAX_PAGES + 1
        ):

            if assets_returned >= MAX_ASSETS:

                print(
                    "Maximum asset limit reached."
                )

                break

            start = (
                (page - 1)
                * BATCH_SIZE
            ) + 1

            remaining = (
                MAX_ASSETS
                - assets_returned
            )

            limit = min(
                BATCH_SIZE,
                remaining
            )

            print()

            print(
                "-" * 78
            )

            print(
                f"PAGE {page}/{MAX_PAGES} "
                f"| START={start} "
                f"| LIMIT={limit}"
            )

            try:

                payload, latency_ms = fetch_page(
                    api_key,
                    start,
                    limit
                )

                data = payload.get(
                    "data",
                    []
                )

                if not data:

                    print(
                        "CMC returned no more assets."
                    )

                    break

                print(
                    f"CMC Returned : {len(data)}"
                )

                print(
                    f"Latency      : {latency_ms:.0f} ms"
                )

                page_inserted = 0
                page_updated = 0

                for item in data:

                    status = upsert_asset(
                        conn,
                        item
                    )

                    assets_returned += 1

                    if status == "INSERTED":

                        inserted += 1
                        page_inserted += 1

                    else:

                        updated += 1
                        page_updated += 1

                conn.commit()

                pages_successful += 1

                print(
                    f"Page Inserted : {page_inserted}"
                )

                print(
                    f"Page Updated  : {page_updated}"
                )

            except Exception as exc:

                pages_failed += 1

                print()

                print(
                    f"PAGE {page} ERROR"
                )

                print(
                    f"{type(exc).__name__}: {exc}"
                )

                print(
                    "Existing universe preserved."
                )

                break

        total_after, active_after = get_counts(
            conn
        )

        elapsed = (
            time.perf_counter()
            - started_total
        )

        print()

        print("=" * 78)

        print(
            "              MARKET UNIVERSE SUMMARY"
        )

        print("=" * 78)

        print(
            f"Pages Successful : {pages_successful}"
        )

        print(
            f"Pages Failed     : {pages_failed}"
        )

        print(
            f"Assets Returned  : {assets_returned}"
        )

        print(
            f"Inserted         : {inserted}"
        )

        print(
            f"Updated          : {updated}"
        )

        print(
            f"Universe Before  : {total_before}"
        )

        print(
            f"Universe Records : {total_after}"
        )

        print(
            f"Active Assets    : {active_after}"
        )

        print(
            f"Run Time         : {elapsed:.2f} sec"
        )

        print(
            f"Engine           : {ENGINE_VERSION}"
        )

        print("=" * 78)

        show_top_assets(
            conn
        )

        print()

        print("=" * 78)

        print(
            "             MARKET UNIVERSE ENGINE COMPLETE"
        )

        print("=" * 78)

        if pages_successful > 0:

            print(
                "UNIVERSE STATUS : SUCCESS"
            )

        else:

            print(
                "UNIVERSE STATUS : FAILED"
            )

        print("=" * 78)

        return 0 if pages_successful > 0 else 1

    except Exception as exc:

        print()

        print("=" * 78)

        print(
            "             MARKET UNIVERSE ENGINE ERROR"
        )

        print("=" * 78)

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print("=" * 78)

        return 1

    finally:

        if conn is not None:

            conn.close()


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
