# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

FABRIC_DB = (
    PROJECT_ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)

TIMEFRAME = "1h"

MARKETS = [
    ("BTC", "BTC/USDT", "KUCOIN_SPOT:BTC-USDT"),
    ("ETH", "ETH/USDT", "KUCOIN_SPOT:ETH-USDT"),
    ("SOL", "SOL/USDT", "KUCOIN_SPOT:SOL-USDT"),
    ("XRP", "XRP/USDT", "KUCOIN_SPOT:XRP-USDT"),
    ("ADA", "ADA/USDT", "KUCOIN_SPOT:ADA-USDT"),
    ("DOGE", "DOGE/USDT", "KUCOIN_SPOT:DOGE-USDT"),
    ("SHIB", "SHIB/USDT", "KUCOIN_SPOT:SHIB-USDT"),
    ("LINK", "LINK/USDT", "KUCOIN_SPOT:LINK-USDT"),
    ("AVAX", "AVAX/USDT", "KUCOIN_SPOT:AVAX-USDT"),
    ("DOT", "DOT/USDT", "KUCOIN_SPOT:DOT-USDT"),
    ("LTC", "LTC/USDT", "KUCOIN_SPOT:LTC-USDT"),
    ("UNI", "UNI/USDT", "KUCOIN_SPOT:UNI-USDT"),
    ("AAVE", "AAVE/USDT", "KUCOIN_SPOT:AAVE-USDT"),
    ("SUI", "SUI/USDT", "KUCOIN_SPOT:SUI-USDT"),
    ("NEAR", "NEAR/USDT", "KUCOIN_SPOT:NEAR-USDT"),
]


def check(condition, label):
    return label if not condition else None


def main():

    print("ARUNDA TRADER — FABRIC PROVENANCE DIAGNOSTIC v0.1")
    print("MODE=READ_ONLY")
    print(f"FABRIC_DB={FABRIC_DB}")
    print("DB_WRITES=0")
    print("PRODUCTION_DB_TOUCHED=False")
    print()

    if not FABRIC_DB.exists():
        print("STATUS=FAIL")
        print("ERROR=FABRIC_DB_NOT_FOUND")
        return 1

    conn = sqlite3.connect(str(FABRIC_DB))
    conn.row_factory = sqlite3.Row

    try:

        total_rows = 0
        invalid_rows = 0

        counters = {
            "ASSET": 0,
            "SYMBOL": 0,
            "TIMEFRAME": 0,
            "SOURCE_ID": 0,
            "SOURCE_TYPE": 0,
            "SOURCE_TIMESTAMP": 0,
            "RETRIEVED_AT": 0,
            "OBSERVATION_COUNT": 0,
            "OBSERVATION_SIGNATURES": 0,
            "OBSERVATION_SLOTS": 0,
            "PRICE_UNIT": 0,
            "DUPLICATE_TIMESTAMP": 0,
        }

        print("===== MARKET PROVENANCE =====")

        for asset, symbol, expected_source_id in MARKETS:

            rows = conn.execute(
                """
                SELECT
                    id,
                    asset,
                    symbol,
                    timestamp,
                    timeframe,
                    source_id,
                    source_type,
                    source_timestamp,
                    retrieved_at,
                    observation_count,
                    observation_signatures,
                    observation_slots,
                    price_unit
                FROM canonical_ohlcv
                WHERE asset = ?
                  AND symbol = ?
                  AND timeframe = ?
                ORDER BY timestamp
                """,
                (asset, symbol, TIMEFRAME),
            ).fetchall()

            print()
            print(
                f"MARKET={asset} {symbol} "
                f"ROWS={len(rows)}"
            )

            source_ids = sorted(
                set(str(r["source_id"]) for r in rows)
            )

            source_types = sorted(
                set(str(r["source_type"]) for r in rows)
            )

            price_units = sorted(
                set(str(r["price_unit"]) for r in rows)
            )

            print(f"SOURCE_IDS={source_ids}")
            print(f"SOURCE_TYPES={source_types}")
            print(f"PRICE_UNITS={price_units}")

            seen = set()

            market_invalid = 0

            for row in rows:

                total_rows += 1

                ts = int(row["timestamp"])

                reasons = []

                if row["asset"] != asset:
                    reasons.append("ASSET")

                if row["symbol"] != symbol:
                    reasons.append("SYMBOL")

                if row["timeframe"] != TIMEFRAME:
                    reasons.append("TIMEFRAME")

                if row["source_id"] != expected_source_id:
                    reasons.append("SOURCE_ID")

                if row["source_type"] != "CEX_PUBLIC_API":
                    reasons.append("SOURCE_TYPE")

                if row["source_timestamp"] != ts:
                    reasons.append("SOURCE_TIMESTAMP")

                if not row["retrieved_at"]:
                    reasons.append("RETRIEVED_AT")

                if int(row["observation_count"]) != 1:
                    reasons.append("OBSERVATION_COUNT")

                if not row["observation_signatures"]:
                    reasons.append("OBSERVATION_SIGNATURES")

                if not row["observation_slots"]:
                    reasons.append("OBSERVATION_SLOTS")

                if row["price_unit"] != "USDT_PER_ASSET":
                    reasons.append("PRICE_UNIT")

                if ts in seen:
                    reasons.append("DUPLICATE_TIMESTAMP")
                else:
                    seen.add(ts)

                if reasons:

                    invalid_rows += 1
                    market_invalid += 1

                    for reason in reasons:
                        counters[reason] += 1

                    print(
                        "INVALID "
                        f"ID={row['id']} "
                        f"TS={ts} "
                        f"REASONS={','.join(reasons)} "
                        f"SOURCE_ID={row['source_id']} "
                        f"SOURCE_TYPE={row['source_type']} "
                        f"OBS_COUNT={row['observation_count']} "
                        f"PRICE_UNIT={row['price_unit']}"
                    )

            print(
                f"MARKET_INVALID_ROWS={market_invalid}"
            )

        print()
        print("===== DIAGNOSTIC SUMMARY =====")

        print(f"TOTAL_ROWS={total_rows}")
        print(f"INVALID_ROWS={invalid_rows}")

        for key, value in counters.items():
            print(f"FAIL_{key}={value}")

        print()
        print("===== SOURCE DISTRIBUTION =====")

        rows = conn.execute(
            """
            SELECT
                source_id,
                source_type,
                price_unit,
                COUNT(*) AS n
            FROM canonical_ohlcv
            WHERE timeframe = ?
            GROUP BY
                source_id,
                source_type,
                price_unit
            ORDER BY source_id
            """,
            (TIMEFRAME,),
        ).fetchall()

        for row in rows:
            print(
                f"SOURCE={row['source_id']} "
                f"TYPE={row['source_type']} "
                f"PRICE_UNIT={row['price_unit']} "
                f"ROWS={row['n']}"
            )

        print()
        print("===== RESULT =====")

        if invalid_rows == 0:
            print("PROVENANCE_VALID=True")
            print("STATUS=PASS")
        else:
            print("PROVENANCE_VALID=False")
            print("STATUS=DIAGNOSTIC_COMPLETE")

        print("READ_ONLY=True")
        print("DB_WRITES=0")
        print("PRODUCTION_DB_TOUCHED=False")

        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())