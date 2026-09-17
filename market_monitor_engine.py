import os
import sqlite3
import time
from datetime import datetime, timezone

import requests


# ============================================================================
# ARUNDA MARKET MONITOR ENGINE v0.2
# ============================================================================

DB_PATH = "arunda.db"

CMC_URL = (
    "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
)

INTERVAL_SECONDS = 60
BATCH_SIZE = 100
REQUEST_TIMEOUT = 20

ENGINE_VERSION = "MARKET_MONITOR_CMC_v0.2"


# ============================================================================
# CONFIG
# ============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_api_key():
    key = os.getenv("CMC_API_KEY")

    if not key:
        raise RuntimeError(
            "CMC_API_KEY environment variable is not set."
        )

    return key


# ============================================================================
# DATABASE
# ============================================================================

def connect_database():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_universe(conn):

    rows = conn.execute(
        """
        SELECT
            rank,
            symbol,
            name,
            is_active
        FROM market_universe
        WHERE is_active = 1
        ORDER BY rank ASC
        """
    ).fetchall()

    return rows


# ============================================================================
# CMC
# ============================================================================

def fetch_quotes(symbols):

    api_key = get_api_key()

    headers = {
        "X-CMC_PRO_API_KEY": api_key,
        "Accept": "application/json",
    }

    params = {
        "symbol": ",".join(symbols),
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
        time.perf_counter() - started
    ) * 1000.0

    response.raise_for_status()

    payload = response.json()

    return payload.get("data", {}), latency_ms


# ============================================================================
# NORMALIZATION
# ============================================================================

def build_snapshot(item, monitor_timestamp):

    quote = (
        item
        .get("quote", {})
        .get("USD", {})
    )

    price = quote.get("price")

    if price is None:
        return None

    return {
        "timestamp": monitor_timestamp,
        "rank": item.get("cmc_rank"),
        "symbol": item.get("symbol"),
        "name": item.get("name"),

        "price": price,

        "market_cap": quote.get(
            "market_cap"
        ),

        "volume_24h": quote.get(
            "volume_24h"
        ),

        "change_1h": quote.get(
            "percent_change_1h"
        ),

        "change_24h": quote.get(
            "percent_change_24h"
        ),

        "change_7d": quote.get(
            "percent_change_7d"
        ),

        "data_status": "AVAILABLE",

        "source": "COINMARKETCAP",

        "engine_version": ENGINE_VERSION,
    }


# ============================================================================
# MEMORY MONITOR
# ============================================================================

def monitor_cycle(universe):

    monitor_timestamp = utc_now()

    symbols = [
        row["symbol"]
        for row in universe
        if row["symbol"]
    ]

    snapshots = []

    batches = [
        symbols[i:i + BATCH_SIZE]
        for i in range(
            0,
            len(symbols),
            BATCH_SIZE,
        )
    ]

    total_latency = 0.0
    successful_batches = 0
    failed_batches = 0

    for index, batch in enumerate(batches, start=1):

        try:

            data, latency_ms = fetch_quotes(
                batch
            )

            total_latency += latency_ms
            successful_batches += 1

            for symbol in batch:

                item = data.get(symbol)

                if not item:
                    continue

                snapshot = build_snapshot(
                    item,
                    monitor_timestamp,
                )

                if snapshot:
                    snapshots.append(
                        snapshot
                    )

        except Exception as exc:

            failed_batches += 1

            print(
                f"BATCH {index}/{len(batches)} ERROR : "
                f"{type(exc).__name__}: {exc}"
            )

    return {
        "timestamp": monitor_timestamp,
        "snapshots": snapshots,
        "total_assets": len(symbols),
        "available_assets": len(snapshots),
        "successful_batches": successful_batches,
        "failed_batches": failed_batches,
        "latency_ms": total_latency,
    }


# ============================================================================
# DISPLAY
# ============================================================================

def print_monitor_table(result):

    snapshots = result["snapshots"]

    print()

    print(
        "LIVE MARKET MONITOR"
    )

    print(
        "-" * 110
    )

    print(
        f"{'RANK':<7}"
        f"{'SYMBOL':<9}"
        f"{'PRICE':>16}"
        f"{'1H %':>10}"
        f"{'24H %':>10}"
        f"{'VOL 24H':>18}"
        f"{'STATUS':>12}"
    )

    print(
        "-" * 110
    )

    for item in snapshots[:50]:

        rank = item["rank"]

        rank_text = (
            str(rank)
            if rank is not None
            else "-"
        )

        price = item["price"]

        change_1h = item["change_1h"]
        change_24h = item["change_24h"]

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

        volume = item["volume_24h"]

        volume_text = (
            f"{volume:,.0f}"
            if volume is not None
            else "N/A"
        )

        print(
            f"{rank_text:<7}"
            f"{item['symbol']:<9}"
            f"{price:>16,.8f}"
            f"{h1:>10}"
            f"{h24:>10}"
            f"{volume_text:>18}"
            f"{item['data_status']:>12}"
        )


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 78)

    print(
        "             ARUNDA MARKET MONITOR ENGINE v0.2"
    )

    print("=" * 78)

    print(
        f"Source          : COINMARKETCAP"
    )

    print(
        f"Database        : {DB_PATH}"
    )

    print(
        f"Interval        : {INTERVAL_SECONDS} seconds"
    )

    print(
        "Mode            : LIVE MARKET MONITOR"
    )

    print(
        "Storage         : MEMORY ONLY"
    )

    print(
        "Database Writes : NONE"
    )

    print(
        "Ranking         : NOT USED"
    )

    print(
        "Opportunity     : NOT USED"
    )

    print(
        "Signal          : NOT USED"
    )

    print(
        "Risk            : NOT USED"
    )

    print(
        "Execution       : NOT USED"
    )

    print("=" * 78)

    conn = None

    total_cycles = 0
    successful_cycles = 0
    failed_cycles = 0

    try:

        conn = connect_database()

        print()
        print(
            "Loading active market universe..."
        )

        universe = get_universe(
            conn
        )

        if not universe:

            raise RuntimeError(
                "No active assets found in market_universe."
            )

        print(
            f"Universe Assets : {len(universe)}"
        )

        print(
            "Universe Status : READY"
        )

        print()

        print(
            "Live monitoring ACTIVE."
        )

        print(
            "Press Ctrl+C to stop."
        )

        while True:

            total_cycles += 1

            cycle_started = time.perf_counter()

            print()
            print("=" * 78)

            print(
                f"MONITOR CYCLE #{total_cycles}"
            )

            print(
                f"Time : {utc_now()}"
            )

            print("=" * 78)

            try:

                result = monitor_cycle(
                    universe
                )

                successful_cycles += 1

                runtime = (
                    time.perf_counter()
                    - cycle_started
                )

                print_monitor_table(
                    result
                )

                print()

                print("=" * 78)

                print(
                    "MONITOR CYCLE SUMMARY"
                )

                print("=" * 78)

                print(
                    f"Universe Assets     : "
                    f"{result['total_assets']}"
                )

                print(
                    f"Available Assets    : "
                    f"{result['available_assets']}"
                )

                print(
                    f"Unavailable Assets  : "
                    f"{result['total_assets'] - result['available_assets']}"
                )

                print(
                    f"Successful Batches  : "
                    f"{result['successful_batches']}"
                )

                print(
                    f"Failed Batches      : "
                    f"{result['failed_batches']}"
                )

                print(
                    f"CMC Latency Total   : "
                    f"{result['latency_ms']:.0f} ms"
                )

                print(
                    f"Cycle Runtime       : "
                    f"{runtime:.2f} sec"
                )

                print(
                    f"Data Timestamp      : "
                    f"{result['timestamp']}"
                )

                print(
                    "Database Writes     : NONE"
                )

                print("=" * 78)

            except Exception as exc:

                failed_cycles += 1

                print()

                print(
                    "MONITOR CYCLE ERROR"
                )

                print(
                    f"{type(exc).__name__}: {exc}"
                )

            print()

            print("=" * 78)

            print(
                "MONITOR STATUS"
            )

            print("=" * 78)

            print(
                f"Total Cycles      : "
                f"{total_cycles}"
            )

            print(
                f"Successful        : "
                f"{successful_cycles}"
            )

            print(
                f"Failed            : "
                f"{failed_cycles}"
            )

            print(
                f"Universe          : "
                f"{len(universe)}"
            )

            print(
                f"Interval          : "
                f"{INTERVAL_SECONDS} seconds"
            )

            print(
                "Analysis          : NOT USED"
            )

            print(
                "Ranking           : NOT USED"
            )

            print(
                "Opportunity       : NOT USED"
            )

            print(
                "Signal            : NOT USED"
            )

            print(
                "Risk              : NOT USED"
            )

            print(
                "Execution         : NOT USED"
            )

            print("=" * 78)

            print()

            print(
                f"Waiting {INTERVAL_SECONDS} seconds..."
            )

            time.sleep(
                INTERVAL_SECONDS
            )

    except KeyboardInterrupt:

        print()

        print("=" * 78)

        print(
            "       ARUNDA MARKET MONITOR ENGINE STOPPED"
        )

        print("=" * 78)

        print(
            f"Total Cycles      : {total_cycles}"
        )

        print(
            f"Successful        : {successful_cycles}"
        )

        print(
            f"Failed            : {failed_cycles}"
        )

        print(
            "Database          : PRESERVED"
        )

        print(
            "Database Writes   : NONE"
        )

        print(
            "Reason            : USER INTERRUPT"
        )

        print("=" * 78)

        return 0

    except Exception as exc:

        print()

        print("=" * 78)

        print(
            "       ARUNDA MARKET MONITOR ENGINE ERROR"
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
