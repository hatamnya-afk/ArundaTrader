import sqlite3
from datetime import datetime, timedelta

DB = "arunda.db"

HORIZONS = {
    5: "price_5m",
    15: "price_15m",
    30: "price_30m",
    60: "price_60m",
}


def parse_time(value):
    return datetime.fromisoformat(value)


def find_price(cur, market, target_time):
    row = cur.execute("""
        SELECT price, timestamp
        FROM market_records
        WHERE market = ?
          AND timestamp >= ?
        ORDER BY timestamp ASC
        LIMIT 1
    """, (market, target_time.isoformat())).fetchone()

    if row:
        return row[0], row[1]

    return None, None


def calculate_return(entry, exit_price):
    if entry is None or exit_price is None or entry == 0:
        return None

    return ((exit_price - entry) / entry) * 100.0


def main():

    print("=" * 80)
    print("              ARUNDA OUTCOME ENGINE v0.1")
    print("=" * 80)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    signals = cur.execute("""
        SELECT
            id,
            timestamp,
            market,
            entry_price
        FROM hunter_signals
        WHERE id NOT IN (
            SELECT signal_id
            FROM signal_outcomes
        )
        ORDER BY id ASC
    """).fetchall()

    print(f"\nPending signals : {len(signals)}")

    processed = 0
    waiting = 0

    for signal_id, timestamp, market, entry_price in signals:

        signal_time = parse_time(timestamp)

        prices = {}
        returns = {}

        complete = True

        for minutes in HORIZONS:

            target = signal_time + timedelta(minutes=minutes)

            price, actual_time = find_price(
                cur,
                market,
                target
            )

            prices[minutes] = price

            if price is None:
                complete = False

            returns[minutes] = calculate_return(
                entry_price,
                price
            )

        # هنوز اطلاعات کافی نداریم
        if not complete:
            waiting += 1
            continue

        all_returns = [
            r for r in returns.values()
            if r is not None
        ]

        max_gain = max(all_returns)
        max_drawdown = min(all_returns)

        # ساده‌ترین outcome فعلی
        if returns[60] > 0:
            outcome = "WIN"
        elif returns[60] < 0:
            outcome = "LOSS"
        else:
            outcome = "FLAT"

        cur.execute("""
            INSERT INTO signal_outcomes (
                signal_id,
                timestamp,
                market,
                entry_price,

                price_5m,
                price_15m,
                price_30m,
                price_60m,

                return_5m,
                return_15m,
                return_30m,
                return_60m,

                max_gain,
                max_drawdown,

                outcome
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal_id,
            timestamp,
            market,
            entry_price,

            prices[5],
            prices[15],
            prices[30],
            prices[60],

            returns[5],
            returns[15],
            returns[30],
            returns[60],

            max_gain,
            max_drawdown,

            outcome
        ))

        processed += 1

        print(
            f"{market:12} | "
            f"Entry {entry_price:,.4f} | "
            f"5m {returns[5]:7.3f}% | "
            f"15m {returns[15]:7.3f}% | "
            f"30m {returns[30]:7.3f}% | "
            f"60m {returns[60]:7.3f}% | "
            f"{outcome}"
        )

    conn.commit()

    print("\n" + "=" * 80)
    print("OUTCOME ENGINE COMPLETE")
    print("=" * 80)

    print(f"Processed : {processed}")
    print(f"Waiting   : {waiting}")

    total = cur.execute("""
        SELECT COUNT(*)
        FROM signal_outcomes
    """).fetchone()[0]

    print(f"Outcomes  : {total}")

    conn.close()


if __name__ == "__main__":
    main()