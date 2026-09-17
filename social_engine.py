import sqlite3
import os
import requests
import time

DB = "arunda.db"

LUNAR_URL = "https://lunarcrush.com/api4/public"
API_KEY = os.getenv("LUNARCRUSH_API_KEY")


def get_symbols():
    conn = sqlite3.connect(DB)

    rows = conn.execute("""
        SELECT DISTINCT asset
        FROM market_records
        WHERE asset IS NOT NULL
        ORDER BY asset
    """).fetchall()

    conn.close()

    return [r[0] for r in rows]


def normalize_symbol(asset):
    if not asset:
        return ""

    symbol = asset.upper()

    if "_" in symbol:
        symbol = symbol.split("_")[0]

    return symbol


def get_lunar(symbol):
    if not API_KEY:
        return {
            "available": False,
            "reason": "API_KEY_MISSING"
        }

    url = f"{LUNAR_URL}/coins/{symbol}/v1"

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        if response.status_code != 200:
            return {
                "available": False,
                "reason": f"HTTP_{response.status_code}"
            }

        payload = response.json()
        data = payload.get("data", {})

        return {
            "available": True,
            "galaxy": data.get("galaxy_score"),
            "social_volume": data.get("social_volume"),
            "social_score": data.get("social_score"),
            "social_contributors": data.get("social_contributors"),
            "social_engagement": data.get("social_engagement"),
            "alt_rank": data.get("alt_rank")
        }

    except Exception as e:
        return {
            "available": False,
            "reason": type(e).__name__
        }


def score_social(data):
    if not data.get("available"):
        return 50.0, "FALLBACK"

    values = []

    for key in [
        "social_score",
        "social_volume",
        "social_contributors",
        "social_engagement"
    ]:
        value = data.get(key)

        if value is not None:
            try:
                values.append(float(value))
            except:
                pass

    if not values:
        galaxy = data.get("galaxy")

        if galaxy is not None:
            try:
                return max(0, min(100, float(galaxy))), "GALAXY_FALLBACK"
            except:
                pass

        return 50.0, "FALLBACK"

    # --------------------------------------------------------
    # TEMPORARY NORMALIZATION
    # --------------------------------------------------------
    # Until enough historical social data exists,
    # use Galaxy as the primary 0-100 normalized signal.
    # Raw social fields are reported for diagnosis only.

    galaxy = data.get("galaxy")

    if galaxy is not None:
        try:
            galaxy = float(galaxy)

            if 0 <= galaxy <= 100:
                return galaxy, "GALAXY"
        except:
            pass

    return 50.0, "FALLBACK"


def main():

    print()
    print("=" * 80)
    print("             ARUNDA SOCIAL ENGINE AUDIT / REPAIR v0.1")
    print("=" * 80)

    symbols = get_symbols()

    print()
    print("Markets :", len(symbols))

    if not symbols:
        print("No markets found.")
        return

    stats = {
        "LIVE": 0,
        "GALAXY_FALLBACK": 0,
        "FALLBACK": 0,
        "ERROR": 0
    }

    print()
    print("SOCIAL DATA")
    print("-" * 80)

    for i, asset in enumerate(symbols, 1):

        symbol = normalize_symbol(asset)

        data = get_lunar(symbol)

        score, source = score_social(data)

        if source in stats:
            stats[source] += 1
        elif not data.get("available"):
            stats["ERROR"] += 1

        print(
            f"{i:02d} | "
            f"{asset:12} | "
            f"SOC {score:6.2f} | "
            f"SOURCE {source:16}"
        )

        if data.get("available"):

            print(
                f"    Galaxy={data.get('galaxy')} "
                f"SocialScore={data.get('social_score')} "
                f"SocialVolume={data.get('social_volume')} "
                f"Contributors={data.get('social_contributors')}"
            )

        else:

            print(
                f"    Reason={data.get('reason')}"
            )

        time.sleep(0.15)

    print()
    print("=" * 80)
    print("SOCIAL ENGINE DIAGNOSTIC")
    print("=" * 80)

    print()
    print(
        f"LIVE / GALAXY : "
        f"{stats['LIVE'] + stats['GALAXY_FALLBACK']}"
    )

    print(
        f"FALLBACK      : "
        f"{stats['FALLBACK']}"
    )

    print(
        f"ERROR         : "
        f"{stats['ERROR']}"
    )

    print()
    print("DATABASE MODIFIED : NO")

    print()
    print("=" * 80)
    print("SOCIAL AUDIT COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()