import requests
import sqlite3
import time
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_FILE = "arunda.db"

MARKETS_URL = "https://api.bitpin.ir/v1/mkt/markets/"
ORDERBOOK_URL = "https://api.bitpin.ir/v4/mth/orderbook/{market_id}/?limit=50"

INTERVAL = 15
MAX_WORKERS = 10
TOP_MARKETS = 50

EXCLUDED = {
    "USDT",
    "USDC",
    "USDE",
    "DAI",
    "FDUSD",
    "TUSD",
    "USDD",
    "WBTC",
    "BTCB",
}


# =========================================================
# DATABASE
# =========================================================

def get_connection():

    conn = sqlite3.connect(
        DB_FILE,
        timeout=30
    )

    return conn


def prepare_database(conn):

    columns = [
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(market_records)"
        ).fetchall()
    ]

    if "snapshot_id" not in columns:

        conn.execute(
            """
            ALTER TABLE market_records
            ADD COLUMN snapshot_id TEXT
            """
        )

    if "collection_ms" not in columns:

        conn.execute(
            """
            ALTER TABLE market_records
            ADD COLUMN collection_ms REAL
            """
        )

    conn.commit()


# =========================================================
# MARKET DATA
# =========================================================

def get_markets():

    r = requests.get(
        MARKETS_URL,
        timeout=10
    )

    r.raise_for_status()

    return r.json()["results"]


# =========================================================
# ORDER BOOK
# =========================================================

def fetch_orderbook(market):

    market_id = market["id"]

    try:

        start = time.perf_counter()

        url = ORDERBOOK_URL.format(
            market_id=market_id
        )

        r = requests.get(
            url,
            timeout=5
        )

        r.raise_for_status()

        ob = r.json()

        elapsed = (
            time.perf_counter() - start
        ) * 1000

        return market, ob, elapsed, None

    except Exception as e:

        return market, None, 0, str(e)


# =========================================================
# ORDER BOOK ANALYSIS
# =========================================================

def analyze_orderbook(ob):

    bids = ob.get("bids", [])
    asks = ob.get("asks", [])

    if not bids or not asks:
        return None

    try:

        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])

        if best_bid <= 0:
            return None

        if best_ask <= 0:
            return None

        if best_ask <= best_bid:
            return None

        bid_volume = sum(
            float(x[1])
            for x in bids
        )

        ask_volume = sum(
            float(x[1])
            for x in asks
        )

        if bid_volume <= 0:
            return None

        if ask_volume <= 0:
            return None

        mid = (
            best_bid + best_ask
        ) / 2

        spread_pct = (
            (best_ask - best_bid)
            / mid
        ) * 100

        if spread_pct < 0:
            return None

        if spread_pct > 10:
            return None

        pressure = (
            bid_volume
            /
            (bid_volume + ask_volume)
        ) * 100

        return {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid": mid,
            "spread_pct": spread_pct,
            "bid_volume": bid_volume,
            "ask_volume": ask_volume,
            "pressure": pressure,
        }

    except (
        ValueError,
        TypeError,
        IndexError
    ):

        return None


# =========================================================
# HUNTER SCORE
# =========================================================

def hunter_score(
    change,
    volume,
    pressure,
    spread
):

    score = 0.0

    # Momentum
    if change >= 5:
        score += 20
    elif change >= 2:
        score += 15
    elif change > 0:
        score += 8

    # Volume
    if volume >= 100_000_000_000:
        score += 20
    elif volume >= 10_000_000_000:
        score += 15
    elif volume >= 1_000_000_000:
        score += 10

    # Pressure
    if pressure >= 65:
        score += 25
    elif pressure >= 60:
        score += 20
    elif pressure >= 55:
        score += 12
    elif pressure >= 50:
        score += 5

    # Spread
    if spread <= 0.20:
        score += 20
    elif spread <= 0.50:
        score += 12
    elif spread <= 1:
        score += 5

    return round(score, 3)


# =========================================================
# BUILD RECORD
# =========================================================

def build_record(
    market,
    ob_data,
    snapshot_id,
    collection_ms
):

    code = market["code"]

    asset = market[
        "currency1"
    ]["code"]

    price = float(
        market.get("price", 0)
    )

    change = float(
        market.get("change", 0)
    )

    volume = float(
        market.get("volume_24h", 0)
    )

    score = hunter_score(
        change,
        volume,
        ob_data["pressure"],
        ob_data["spread_pct"]
    )

    timestamp = datetime.now().isoformat()

    return (
        timestamp,
        code,
        asset,
        price,
        change,
        volume,
        ob_data["best_bid"],
        ob_data["best_ask"],
        ob_data["mid"],
        ob_data["spread_pct"],
        ob_data["bid_volume"],
        ob_data["ask_volume"],
        ob_data["pressure"],
        score,
        snapshot_id,
        collection_ms
    )


# =========================================================
# SAVE SNAPSHOT
# =========================================================

def save_records(conn, records):

    conn.executemany(
        """
        INSERT INTO market_records (

            timestamp,
            market,
            asset,
            price,
            change_24h,
            volume_24h,
            best_bid,
            best_ask,
            mid,
            spread_pct,
            bid_volume,
            ask_volume,
            pressure,
            hunter_score,
            snapshot_id,
            collection_ms

        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        records
    )

    conn.commit()


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("==============================================")
    print("       ARUNDA RECORDER v0.3")
    print("==============================================")
    print(
        f"Workers : {MAX_WORKERS}"
    )
    print(
        f"Markets : Top {TOP_MARKETS}"
    )
    print(
        f"Interval: {INTERVAL}s"
    )
    print("==============================================")

    conn = get_connection()

    prepare_database(conn)

    total_saved = 0
    total_rejected = 0
    snapshot_number = 0

    while True:

        cycle_start = time.perf_counter()

        try:

            markets = get_markets()

            candidates = []

            for m in markets:

                if not m.get("tradable"):
                    continue

                code = m.get(
                    "code",
                    ""
                )

                if not code.endswith("_IRT"):
                    continue

                asset = code.replace(
                    "_IRT",
                    ""
                )

                if asset in EXCLUDED:
                    continue

                candidates.append(m)

            candidates.sort(
                key=lambda x: float(
                    x.get(
                        "volume_24h",
                        0
                    )
                ),
                reverse=True
            )

            candidates = candidates[
                :TOP_MARKETS
            ]

            snapshot_number += 1

            snapshot_id = (
                datetime.now().strftime(
                    "%Y%m%d_%H%M%S"
                )
                + "_"
                + uuid.uuid4().hex[:6]
            )

            records = []

            rejected = 0

            print()
            print(
                f"[SNAPSHOT {snapshot_number}] "
                f"{snapshot_id}"
            )

            # -------------------------------------------------
            # CONCURRENT ORDER BOOK REQUESTS
            # -------------------------------------------------

            with ThreadPoolExecutor(
                max_workers=MAX_WORKERS
            ) as executor:

                futures = [
                    executor.submit(
                        fetch_orderbook,
                        market
                    )
                    for market in candidates
                ]

                for future in as_completed(
                    futures
                ):

                    market, ob, latency, error = (
                        future.result()
                    )

                    if error:

                        rejected += 1

                        print(
                            f"  REJECT "
                            f"{market['code']} "
                            f"API: {error}"
                        )

                        continue

                    ob_data = analyze_orderbook(
                        ob
                    )

                    if ob_data is None:

                        rejected += 1

                        print(
                            f"  REJECT "
                            f"{market['code']} "
                            f"INVALID BOOK"
                        )

                        continue

                    record = build_record(
                        market,
                        ob_data,
                        snapshot_id,
                        latency
                    )

                    records.append(
                        record
                    )

            # -------------------------------------------------
            # SAVE
            # -------------------------------------------------

            if records:

                save_records(
                    conn,
                    records
                )

            saved = len(records)

            total_saved += saved

            total_rejected += rejected

            elapsed = (
                time.perf_counter()
                - cycle_start
            )

            print()
            print(
                "----------------------------------------------"
            )

            print(
                f"Markets      : {len(markets)}"
            )

            print(
                f"Candidates   : {len(candidates)}"
            )

            print(
                f"Saved        : {saved}"
            )

            print(
                f"Rejected     : {rejected}"
            )

            print(
                f"Total Saved  : {total_saved}"
            )

            print(
                f"Cycle Time   : {elapsed:.2f}s"
            )

            if records:

                avg_latency = sum(
                    r[-1]
                    for r in records
                ) / len(records)

                print(
                    f"Avg API Time : "
                    f"{avg_latency:.1f} ms"
                )

            print(
                "----------------------------------------------"
            )

            # -------------------------------------------------
            # WAIT
            # -------------------------------------------------

            sleep_time = max(
                1,
                INTERVAL - elapsed
            )

            print(
                f"Next snapshot in "
                f"{sleep_time:.1f}s"
            )

            time.sleep(
                sleep_time
            )

        except KeyboardInterrupt:

            print()
            print(
                "=============================================="
            )
            print(
                "ARUNDA RECORDER STOPPED"
            )
            print(
                f"Total Saved   : {total_saved}"
            )
            print(
                f"Total Rejected: {total_rejected}"
            )
            print(
                "=============================================="
            )

            break

        except Exception as e:

            print()
            print(
                f"MAIN ERROR: {e}"
            )

            time.sleep(5)

    conn.close()


if __name__ == "__main__":
    main()