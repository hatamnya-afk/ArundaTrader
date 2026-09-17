import sqlite3
import requests
import time
from datetime import datetime

DB = "arunda.db"

# ============================================================
# ARUNDA CATALYST ENGINE v0.1
# ============================================================

LUNAR_URL = "https://lunarcrush.com/api4/public/coins/{}/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# -----------------------------
# CONFIG
# -----------------------------

TOP_N = 50

# Weights
W_BOOK = 0.20
W_MOMENTUM = 0.20
W_SOCIAL = 0.15
W_VOLUME = 0.15
W_CATALYST = 0.20
W_GLOBAL = 0.10


# ============================================================
# DATABASE
# ============================================================

def load_markets():

    conn = sqlite3.connect(DB)

    query = """
        SELECT market,
               asset,
               price,
               change_24h,
               volume_24h,
               pressure,
               spread_pct,
               hunter_score
        FROM market_records
        WHERE id IN (
            SELECT MAX(id)
            FROM market_records
            GROUP BY market
        )
        ORDER BY hunter_score DESC
        LIMIT ?
    """

    rows = conn.execute(query, (TOP_N,)).fetchall()

    conn.close()

    return rows


# ============================================================
# LUNARCRUSH
# ============================================================

def lunar(symbol):

    try:

        url = LUNAR_URL.format(symbol)

        r = requests.get(
            url,
            headers=HEADERS,
            timeout=8
        )

        if r.status_code != 200:
            return {
                "galaxy": 50.0,
                "social": 50.0,
                "available": False
            }

        data = r.json().get("data", {})

        galaxy = data.get("galaxy_score")

        if galaxy is None:
            galaxy = 50.0

        return {
            "galaxy": float(galaxy),
            "social": float(galaxy),
            "available": True
        }

    except Exception:

        return {
            "galaxy": 50.0,
            "social": 50.0,
            "available": False
        }


# ============================================================
# NORMALIZATION
# ============================================================

def clamp(x, low=0, high=100):

    return max(low, min(high, x))


def momentum_score(change):

    """
    Convert 24h change into a momentum score.

    Positive momentum is rewarded,
    but extreme pumps are not automatically treated as good.
    """

    if change is None:
        return 50.0

    change = float(change)

    if change <= -10:
        return 20

    if change <= -5:
        return 30

    if change <= -2:
        return 40

    if change < 0:
        return 48

    if change < 1:
        return 55

    if change < 3:
        return 65

    if change < 6:
        return 75

    if change < 10:
        return 82

    # Extreme move
    return 70


def volume_score(volume, max_volume):

    if not volume or not max_volume:
        return 50

    ratio = volume / max_volume

    score = ratio * 100

    return clamp(score)


def book_score(pressure):

    if pressure is None:
        return 50

    return clamp(float(pressure))


# ============================================================
# CATALYST SCORE
# ============================================================

def catalyst_score(galaxy, change):

    """
    v0.1 proxy catalyst detector.

    Later this will be replaced by real news/event data.

    High social activity + price not yet overheated
    = potential early catalyst.
    """

    galaxy = float(galaxy)
    change = float(change or 0)

    score = galaxy

    # Social strength with muted price movement
    if galaxy >= 65 and -3 <= change <= 4:
        score += 15

    # Strong social + moderate positive movement
    elif galaxy >= 60 and 0 < change <= 8:
        score += 10

    # Large negative move with weak social
    elif change < -7 and galaxy < 45:
        score -= 10

    return clamp(score)


# ============================================================
# GLOBAL SCORE
# ============================================================

def global_score(asset):

    """
    Temporary global confirmation.

    BTC / ETH / SOL get neutral-positive baseline.
    Later this will be replaced with TradingView/global market data.
    """

    majors = {
        "BTC": 60,
        "ETH": 60,
        "SOL": 55
    }

    return majors.get(asset, 50)


# ============================================================
# CLASSIFICATION
# ============================================================

def classify(score, catalyst):

    if score >= 75 and catalyst >= 70:
        return "PRIME"

    if score >= 65:
        return "WATCH"

    if score >= 55:
        return "SETUP"

    return "IGNORE"


# ============================================================
# MAIN ENGINE
# ============================================================

def main():

    print()
    print("=" * 80)
    print("              ARUNDA CATALYST ENGINE v0.1")
    print("=" * 80)

    rows = load_markets()

    if not rows:

        print("No market data found.")
        return

    max_volume = max(
        float(x[4] or 0)
        for x in rows
    )

    results = []

    for row in rows:

        market = row[0]
        asset = row[1]

        price = float(row[2] or 0)
        change = float(row[3] or 0)
        volume = float(row[4] or 0)
        pressure = float(row[5] or 50)
        spread = float(row[6] or 0)
        hunter = float(row[7] or 50)

        # LunarCrush
        lc = lunar(asset)

        galaxy = lc["galaxy"]

        # Components
        book = book_score(pressure)

        momentum = momentum_score(change)

        social = clamp(galaxy)

        volume_s = volume_score(
            volume,
            max_volume
        )

        catalyst = catalyst_score(
            galaxy,
            change
        )

        global_s = global_score(asset)

        # -----------------------------------------
        # Fusion
        # -----------------------------------------

        final = (
            book * W_BOOK
            + momentum * W_MOMENTUM
            + social * W_SOCIAL
            + volume_s * W_VOLUME
            + catalyst * W_CATALYST
            + global_s * W_GLOBAL
        )

        final = clamp(final)

        classification = classify(
            final,
            catalyst
        )

        results.append({
            "market": market,
            "final": final,
            "book": book,
            "momentum": momentum,
            "social": social,
            "volume": volume_s,
            "catalyst": catalyst,
            "global": global_s,
            "class": classification
        })

        time.sleep(0.15)

    # ========================================================
    # SORT
    # ========================================================

    results.sort(
        key=lambda x: x["final"],
        reverse=True
    )

    print()
    print(
        f"{'MARKET':<14}"
        f"{'FINAL':>8}"
        f"{'BOOK':>8}"
        f"{'MOM':>8}"
        f"{'SOC':>8}"
        f"{'VOL':>8}"
        f"{'CAT':>8}"
        f"{'GLOBAL':>8}"
        f"  STATUS"
    )

    print("-" * 90)

    for i, r in enumerate(results, 1):

        print(
            f"{i:02d} | "
            f"{r['market']:<10} "
            f"{r['final']:>6.2f} "
            f"{r['book']:>7.1f} "
            f"{r['momentum']:>7.1f} "
            f"{r['social']:>7.1f} "
            f"{r['volume']:>7.1f} "
            f"{r['catalyst']:>7.1f} "
            f"{r['global']:>7.1f} "
            f" {r['class']}"
        )

    # ========================================================
    # PRIME
    # ========================================================

    primes = [
        r for r in results
        if r["class"] == "PRIME"
    ]

    watches = [
        r for r in results
        if r["class"] == "WATCH"
    ]

    print()
    print("=" * 80)
    print("ARUNDA HUNTER BOARD")
    print("=" * 80)

    print()
    print("PRIME OPPORTUNITIES")
    print("-" * 80)

    if primes:

        for r in primes[:10]:

            print(
                f"{r['market']:<12}"
                f" SCORE {r['final']:>6.2f}"
                f"  Catalyst {r['catalyst']:>5.1f}"
            )

    else:

        print("No PRIME opportunity detected.")

    print()
    print("WATCH LIST")
    print("-" * 80)

    for r in watches[:10]:

        print(
            f"{r['market']:<12}"
            f" SCORE {r['final']:>6.2f}"
            f"  Catalyst {r['catalyst']:>5.1f}"
        )

    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()