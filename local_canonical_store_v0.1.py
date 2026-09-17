# C:\Users\ASUS\ArundaTrader\public_market_data_fabric\local_canonical_store_v0.1.py

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


ENGINE = "LOCAL_CANONICAL_STORE_v0.1"

# ============================================================
# HARD BOUNDARY
# ============================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCTION_DB = PROJECT_ROOT / "arunda.db"

FABRIC_DIR = PROJECT_ROOT / "public_market_data_fabric"
STORAGE_PATH = FABRIC_DIR / "canonical_store_v0.1.sqlite"

DB_WRITES_PRODUCTION = 0
PRODUCTION_DB_TOUCHED = False
EXECUTION = "DISABLED"
CANONICAL_OHLCV_COMMITTED = False


# ============================================================
# REAL PDF-04 / PDF-05 CANONICAL CANDLE
# ============================================================

REAL_CANDLE = {
    "asset": "SOL",
    "symbol": "SOL/USDC",
    "timestamp": 1788822000,
    "timeframe": "1h",
    "open": 103.9433519613302,
    "high": 103.9433519613302,
    "low": 103.93748844263929,
    "close": 103.93748844263929,
    "volume": 109.97541,

    "source_id": "SOLANA_MAINNET_RAYDIUM_AMM_V4",
    "source_type": "DEX_ONCHAIN",

    # PDF-05 source timestamp = canonical source timestamp.
    "source_timestamp": 1788822000,

    # Retrieval metadata for this local verification run.
    # It is provenance metadata, not market data.
    "retrieved_at": datetime.now(timezone.utc).isoformat(),

    "observation_count": 2,

    "observation_signatures": [
        "2m1fkxJhf2QDhqQZfd4Vb8xiYMGHraKgDVUh84mrQS6R6y9EoDJjiZzthC4vyt4fdYURtRxwcf2XrWsTvJQZatn",
        "2eNmAjMYRWUcrJyCwdex2JtVy3Yxo1549pHEEFjJNjvCsKLVGhkmqNhW6bz8Wrfa47hLsfRKzur1RaEs4P8DKYbA",
    ],

    "observation_slots": [
        445186108,
        445186115,
    ],

    "pool": "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",

    "raydium_instruction": {
        "program_id": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
        "observations": [
            {
                "group": 3,
                "position": 5,
                "data": "9mXzHTFUufwuPjERJWfrwTV",
            },
            {
                "group": 4,
                "position": 10,
                "data": "9vG8YrqrBwUiB58scjSXySw",
            },
        ],
    },

    "price_unit": "USDC_PER_SOL",
}


# ============================================================
# STORAGE SCHEMA
# ============================================================

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS canonical_ohlcv (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    asset TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    timeframe TEXT NOT NULL,

    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,

    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_timestamp INTEGER NOT NULL,
    retrieved_at TEXT NOT NULL,

    observation_count INTEGER NOT NULL,
    observation_signatures TEXT NOT NULL,
    observation_slots TEXT NOT NULL,

    pool TEXT,
    raydium_instruction TEXT,
    price_unit TEXT,

    canonical_payload TEXT NOT NULL,

    UNIQUE(asset, symbol, timestamp, timeframe)
);
"""


# ============================================================
# DETERMINISTIC SERIALIZATION
# ============================================================

def canonical_bytes(candle: dict) -> bytes:
    payload = {
        "asset": candle["asset"],
        "symbol": candle["symbol"],
        "timestamp": candle["timestamp"],
        "timeframe": candle["timeframe"],
        "open": candle["open"],
        "high": candle["high"],
        "low": candle["low"],
        "close": candle["close"],
        "volume": candle["volume"],
        "source_id": candle["source_id"],
        "source_type": candle["source_type"],
        "source_timestamp": candle["source_timestamp"],
        "retrieved_at": candle["retrieved_at"],
        "observation_count": candle["observation_count"],
        "observation_signatures": candle["observation_signatures"],
        "observation_slots": candle["observation_slots"],
        "pool": candle["pool"],
        "raydium_instruction": candle["raydium_instruction"],
        "price_unit": candle["price_unit"],
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


# ============================================================
# INSERT
# ============================================================

def insert_candle(conn: sqlite3.Connection, candle: dict) -> bool:
    payload = canonical_bytes(candle).decode("utf-8")

    try:
        conn.execute(
            """
            INSERT INTO canonical_ohlcv (
                asset,
                symbol,
                timestamp,
                timeframe,
                open,
                high,
                low,
                close,
                volume,
                source_id,
                source_type,
                source_timestamp,
                retrieved_at,
                observation_count,
                observation_signatures,
                observation_slots,
                pool,
                raydium_instruction,
                price_unit,
                canonical_payload
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candle["asset"],
                candle["symbol"],
                candle["timestamp"],
                candle["timeframe"],
                candle["open"],
                candle["high"],
                candle["low"],
                candle["close"],
                candle["volume"],
                candle["source_id"],
                candle["source_type"],
                candle["source_timestamp"],
                candle["retrieved_at"],
                candle["observation_count"],
                json.dumps(
                    candle["observation_signatures"],
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                json.dumps(
                    candle["observation_slots"],
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                candle["pool"],
                json.dumps(
                    candle["raydium_instruction"],
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                candle["price_unit"],
                payload,
            ),
        )

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        conn.rollback()
        return False


# ============================================================
# READ BACK
# ============================================================

def read_back(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        """
        SELECT
            asset,
            symbol,
            timestamp,
            timeframe,
            open,
            high,
            low,
            close,
            volume,
            source_id,
            source_type,
            source_timestamp,
            retrieved_at,
            observation_count,
            observation_signatures,
            observation_slots,
            pool,
            raydium_instruction,
            price_unit,
            canonical_payload
        FROM canonical_ohlcv
        ORDER BY id
        LIMIT 1
        """
    ).fetchone()

    if row is None:
        return None

    (
        asset,
        symbol,
        timestamp,
        timeframe,
        open_,
        high,
        low,
        close,
        volume,
        source_id,
        source_type,
        source_timestamp,
        retrieved_at,
        observation_count,
        observation_signatures,
        observation_slots,
        pool,
        raydium_instruction,
        price_unit,
        canonical_payload,
    ) = row

    return {
        "asset": asset,
        "symbol": symbol,
        "timestamp": timestamp,
        "timeframe": timeframe,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "source_id": source_id,
        "source_type": source_type,
        "source_timestamp": source_timestamp,
        "retrieved_at": retrieved_at,
        "observation_count": observation_count,
        "observation_signatures": json.loads(observation_signatures),
        "observation_slots": json.loads(observation_slots),
        "pool": pool,
        "raydium_instruction": json.loads(raydium_instruction),
        "price_unit": price_unit,
        "canonical_payload": canonical_payload,
    }


# ============================================================
# VALUE-LEVEL COMPARISON
# ============================================================

def value_level_match(original: dict, stored: dict) -> bool:
    keys = [
        "asset",
        "symbol",
        "timestamp",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source_id",
        "source_type",
        "source_timestamp",
        "retrieved_at",
        "observation_count",
        "observation_signatures",
        "observation_slots",
        "pool",
        "raydium_instruction",
        "price_unit",
    ]

    return all(original[k] == stored[k] for k in keys)


def provenance_match(original: dict, stored: dict) -> bool:
    keys = [
        "source_id",
        "source_type",
        "source_timestamp",
        "retrieved_at",
        "observation_count",
        "observation_signatures",
        "observation_slots",
        "pool",
        "raydium_instruction",
    ]

    return all(original[k] == stored[k] for k in keys)


# ============================================================
# MAIN VERIFICATION
# ============================================================

def main():

    # --------------------------------------------------------
    # HARD SAFETY ASSERTIONS
    # --------------------------------------------------------

    if not PRODUCTION_DB.exists():
        print("PRODUCTION_DB_PRESENT=False")
    else:
        print("PRODUCTION_DB_PRESENT=True")

    # Explicitly do not open, inspect, migrate, or write arunda.db.
    print("PRODUCTION_DB_ACCESS=NONE")

    FABRIC_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # ISOLATED STORAGE
    # --------------------------------------------------------

    conn = sqlite3.connect(str(STORAGE_PATH))

    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(CREATE_SQL)

        # ----------------------------------------------------
        # INPUT
        # ----------------------------------------------------

        input_count = 1

        original_bytes = canonical_bytes(REAL_CANDLE)

        # ----------------------------------------------------
        # FIRST INSERT
        # ----------------------------------------------------

        first_insert = insert_candle(conn, REAL_CANDLE)

        stored_count = conn.execute(
            "SELECT COUNT(*) FROM canonical_ohlcv"
        ).fetchone()[0]

        # ----------------------------------------------------
        # READ BACK
        # ----------------------------------------------------

        read_back_candle = read_back(conn)

        candles_read_back = (
            1 if read_back_candle is not None else 0
        )

        if read_back_candle is None:
            read_back_match = False
            provenance_ok = False
            byte_match = False
        else:
            read_back_match = value_level_match(
                REAL_CANDLE,
                read_back_candle,
            )

            provenance_ok = provenance_match(
                REAL_CANDLE,
                read_back_candle,
            )

            stored_payload_bytes = (
                read_back_candle["canonical_payload"]
                .encode("utf-8")
            )

            byte_match = (
                original_bytes == stored_payload_bytes
            )

        # ----------------------------------------------------
        # DUPLICATE INSERT
        # ----------------------------------------------------

        duplicate_insert = insert_candle(
            conn,
            REAL_CANDLE,
        )

        count_after_duplicate = conn.execute(
            "SELECT COUNT(*) FROM canonical_ohlcv"
        ).fetchone()[0]

        duplicate_protection = (
            duplicate_insert is False
            and count_after_duplicate == stored_count
        )

        # ----------------------------------------------------
        # FINAL READ-BACK
        # ----------------------------------------------------

        final_read = read_back(conn)

        final_read_ok = (
            final_read is not None
            and value_level_match(
                REAL_CANDLE,
                final_read,
            )
            and provenance_match(
                REAL_CANDLE,
                final_read,
            )
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        verified = (
            first_insert is True
            and stored_count == 1
            and candles_read_back == 1
            and read_back_match
            and provenance_ok
            and byte_match
            and duplicate_protection
            and final_read_ok
        )

        status = (
            "LOCAL_CANONICAL_STORE_VERIFIED"
            if verified
            else "FAIL_CLOSED"
        )

        # ----------------------------------------------------
        # RUNTIME EVIDENCE
        # ----------------------------------------------------

        print()
        print("===== PDF-08 LOCAL CANONICAL STORE RUNTIME EVIDENCE =====")
        print(f"STATUS={status}")
        print("STORAGE_TYPE=SQLITE_LOCAL_FABRIC")
        print(f"STORAGE_LOCATION={STORAGE_PATH}")
        print(f"STORAGE_ISOLATED={STORAGE_PATH != PRODUCTION_DB}")
        print(f"CANONICAL_CANDLES_INPUT={input_count}")
        print(f"CANDLES_STORED={stored_count}")
        print(f"CANDLES_READ_BACK={candles_read_back}")
        print(f"READ_BACK_MATCH={read_back_match and byte_match}")
        print(f"PROVENANCE_MATCH={provenance_ok}")
        print(f"DUPLICATE_PROTECTION={duplicate_protection}")
        print("REAL_DATA=True")
        print("SYNTHETIC=False")
        print("INTERPOLATION=False")
        print("FILL=False")
        print("BACKFILL=False")
        print("PADDING=False")
        print("BLENDING=False")
        print(f"DB_WRITES_PRODUCTION={DB_WRITES_PRODUCTION}")
        print(f"PRODUCTION_DB_TOUCHED={PRODUCTION_DB_TOUCHED}")
        print(f"EXECUTION={EXECUTION}")
        print(
            f"CANONICAL_OHLCV_COMMITTED="
            f"{CANONICAL_OHLCV_COMMITTED}"
        )
        print(f"FAIL_CLOSED={not verified}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()