import sqlite3

conn = sqlite3.connect("arunda.db")
conn.row_factory = sqlite3.Row

print("=" * 78)
print("READ-ONLY FUSION DIAGNOSTIC")
print("=" * 78)

print()
print("--- MARKET DATA ---")

rows = conn.execute("""
    SELECT symbol, technical_score, timestamp
    FROM market_data
    WHERE symbol IN ('BTC', 'ETH', 'SOL', 'XRP')
    ORDER BY id DESC
""").fetchall()

if not rows:
    print("NO MARKET DATA ROWS FOUND")
else:
    for row in rows:
        print(dict(row))

print()
print("--- POSITIONING ---")

rows = conn.execute("""
    SELECT market, symbol, positioning_score, timestamp
    FROM positioning_data
    WHERE market IN ('BTC', 'ETH', 'SOL', 'XRP')
       OR symbol IN ('BTC', 'ETH', 'SOL', 'XRP')
    ORDER BY id DESC
""").fetchall()

if not rows:
    print("NO POSITIONING ROWS FOUND")
else:
    for row in rows:
        print(dict(row))

print()
print("--- FUSION LATEST ---")

rows = conn.execute("""
    SELECT
        asset,
        market_score,
        positioning_score,
        news_score,
        fused_score,
        confidence,
        direction,
        entry_price,
        timestamp
    FROM fusion_signals
    ORDER BY id DESC
    LIMIT 4
""").fetchall()

if not rows:
    print("NO FUSION ROWS FOUND")
else:
    for row in rows:
        print(dict(row))

print()
print("=" * 78)
print("READ-ONLY DIAGNOSTIC COMPLETE")
print("=" * 78)

conn.close()
