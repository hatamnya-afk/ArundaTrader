import requests

MARKETS_URL = "https://api.bitpin.ir/v1/mkt/markets/"

# دارایی‌هایی که برای شکار حرکت معمولاً نمی‌خواهیم
EXCLUDED_CODES = {
    "USDT",
    "USDC",
    "DAI",
    "FDUSD",
    "TUSD",
    "WBTC",
    "WETH",
}


def get_markets():
    r = requests.get(MARKETS_URL, timeout=10)
    r.raise_for_status()
    return r.json()["results"]


def get_change(market):
    """
    تلاش می‌کنیم تغییر 24h را از داده بازار استخراج کنیم.
    """
    info = market.get("order_book_info") or {}

    change = info.get("change")

    if change is not None:
        return float(change)

    price_info = market.get("price_info") or {}
    change = price_info.get("change")

    if change is not None:
        return float(change)

    return 0.0


def build_candidates(markets):

    candidates = []

    for m in markets:

        if not m.get("tradable"):
            continue

        if m.get("suspended"):
            continue

        currency = m.get("currency1") or {}

        code = currency.get("code")

        if not code:
            continue

        if code in EXCLUDED_CODES:
            continue

        volume = float(m.get("volume_24h") or 0)
        price = float(m.get("price") or 0)

        if volume <= 0 or price <= 0:
            continue

        change = get_change(m)

        # امتیاز اولیه:
        # حجم = قابلیت معامله
        # تغییر = وجود حرکت
        volume_score = min(volume / 1e12 * 10, 60)

        momentum_score = min(abs(change) * 20, 40)

        opportunity_score = volume_score + momentum_score

        candidates.append({
            "id": m["id"],
            "code": m["code"],
            "asset": code,
            "price": price,
            "volume": volume,
            "change": change,
            "score": opportunity_score,
            "high_risk": currency.get("high_risk", False),
        })

    return candidates


markets = get_markets()

candidates = build_candidates(markets)

candidates.sort(
    key=lambda x: x["score"],
    reverse=True
)

print()
print("================================================")
print("           ARUNDA HUNTER v0.2")
print("================================================")
print()
print(f"Markets received : {len(markets)}")
print(f"Candidates       : {len(candidates)}")
print()

print(
    f"{'#':>3} "
    f"{'MARKET':<14} "
    f"{'CHANGE':>10} "
    f"{'VOLUME':>20} "
    f"{'SCORE':>8}"
)

print("-" * 65)

for i, c in enumerate(candidates[:50], 1):

    print(
        f"{i:>3} "
        f"{c['code']:<14} "
        f"{c['change']*100:>9.3f}% "
        f"{c['volume']:>20,.0f} "
        f"{c['score']:>8.2f}"
    )

print()
print("================================================")