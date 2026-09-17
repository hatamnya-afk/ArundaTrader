# ================================================================
# ARUNDA MARKET WHALE ENGINE v0.1
# ================================================================
# Purpose:
#   Raw whale / large-transfer data collection
#
# Intelligence : NOT USED
# Sentiment    : NOT USED
# Ranking      : NOT USED
# Opportunity  : NOT USED
# Signal       : NOT USED
# Prediction   : NOT USED
# Risk         : NOT USED
# Execution    : NOT USED
#
# Provider:
#   Whale Alert API (optional)
#
# Design:
#   Provider-Agnostic
#   Self-Healing SQLite Schema
#   No trading decision
# ================================================================

import os
import sys
import time
import hashlib
import sqlite3
from datetime import datetime, timezone

import requests


DB_PATH = "arunda.db"

API_KEY = os.getenv("WHALE_ALERT_API_KEY", "").strip()

# Whale Alert API base
API_BASE = "https://api.whale-alert.io/v1"

# We deliberately start conservatively.
MIN_VALUE_USD = 500_000

# Look back window for every cycle.
LOOKBACK_SECONDS = 600

# API request timeout.
TIMEOUT = 20


# ================================================================
# UTILITIES
# ================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value):
    return hashlib.sha256(
        str(value).encode("utf-8", errors="ignore")
    ).hexdigest()


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


# ================================================================
# DATABASE
# ================================================================

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def ensure_schema(conn):

    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_whale (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            timestamp TEXT,
            symbol TEXT,
            blockchain TEXT,

            transaction_type TEXT,

            amount REAL,
            amount_usd REAL,

            tx_hash TEXT,

            from_address TEXT,
            from_owner TEXT,
            from_owner_type TEXT,

            to_address TEXT,
            to_owner TEXT,
            to_owner_type TEXT,

            direction TEXT,

            source TEXT,
            source_timestamp TEXT,

            content_hash TEXT,

            created_at TEXT,
            engine_version TEXT
        )
    """)

    required_columns = {
        "timestamp": "TEXT",
        "symbol": "TEXT",
        "blockchain": "TEXT",
        "transaction_type": "TEXT",
        "amount": "REAL",
        "amount_usd": "REAL",
        "tx_hash": "TEXT",
        "from_address": "TEXT",
        "from_owner": "TEXT",
        "from_owner_type": "TEXT",
        "to_address": "TEXT",
        "to_owner": "TEXT",
        "to_owner_type": "TEXT",
        "direction": "TEXT",
        "source": "TEXT",
        "source_timestamp": "TEXT",
        "content_hash": "TEXT",
        "created_at": "TEXT",
        "engine_version": "TEXT",
    }

    existing = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(market_whale)"
        ).fetchall()
    }

    added = []

    for column, dtype in required_columns.items():
        if column not in existing:
            conn.execute(
                f"ALTER TABLE market_whale ADD COLUMN {column} {dtype}"
            )
            added.append(column)

    conn.commit()

    return added


def count_records(conn):
    return conn.execute(
        "SELECT COUNT(*) FROM market_whale"
    ).fetchone()[0]


# ================================================================
# OWNER / FLOW CLASSIFICATION
# ================================================================

def classify_direction(from_type, to_type):

    from_type = (from_type or "").lower()
    to_type = (to_type or "").lower()

    if from_type == "exchange" and to_type != "exchange":
        return "EXCHANGE_OUTFLOW"

    if from_type != "exchange" and to_type == "exchange":
        return "EXCHANGE_INFLOW"

    if from_type == "exchange" and to_type == "exchange":
        return "EXCHANGE_TO_EXCHANGE"

    return "WALLET_TO_WALLET"


# ================================================================
# WHALE ALERT API
# ================================================================

def fetch_whale_transactions():

    if not API_KEY:
        return {
            "status": "NO_API_KEY",
            "transactions": []
        }

    now = int(time.time())
    start = now - LOOKBACK_SECONDS

    url = f"{API_BASE}/transactions"

    params = {
        "api_key": API_KEY,
        "start": start,
        "end": now,
        "min_value": MIN_VALUE_USD,
        "limit": 100,
    }

    started = time.perf_counter()

    response = requests.get(
        url,
        params=params,
        timeout=TIMEOUT
    )

    latency = int(
        (time.perf_counter() - started) * 1000
    )

    response.raise_for_status()

    payload = response.json()

    transactions = payload.get("transactions", [])

    return {
        "status": "SUCCESS",
        "transactions": transactions,
        "latency": latency,
        "raw": payload
    }


# ================================================================
# NORMALIZATION
# ================================================================

def normalize_transaction(tx):

    timestamp = safe_int(tx.get("timestamp"))

    if timestamp > 0:
        timestamp_iso = datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc
        ).isoformat()
    else:
        timestamp_iso = utc_now()

    blockchain = tx.get("blockchain") or "UNKNOWN"
    symbol = tx.get("symbol") or "UNKNOWN"

    transaction_type = (
        tx.get("transaction_type")
        or "transfer"
    )

    amount = safe_float(tx.get("amount"))
    amount_usd = safe_float(tx.get("amount_usd"))

    tx_hash = tx.get("hash") or ""

    from_data = tx.get("from") or {}
    to_data = tx.get("to") or {}

    from_address = from_data.get("address") or ""
    from_owner = from_data.get("owner") or ""
    from_owner_type = from_data.get("owner_type") or "unknown"

    to_address = to_data.get("address") or ""
    to_owner = to_data.get("owner") or ""
    to_owner_type = to_data.get("owner_type") or "unknown"

    direction = classify_direction(
        from_owner_type,
        to_owner_type
    )

    unique_material = "|".join([
        str(timestamp),
        str(blockchain),
        str(symbol),
        str(tx_hash),
        str(amount),
        str(amount_usd),
        str(from_address),
        str(to_address),
    ])

    content_hash = sha256_text(unique_material)

    return {
        "timestamp": timestamp_iso,
        "symbol": symbol.upper(),
        "blockchain": blockchain,
        "transaction_type": transaction_type,

        "amount": amount,
        "amount_usd": amount_usd,

        "tx_hash": tx_hash,

        "from_address": from_address,
        "from_owner": from_owner,
        "from_owner_type": from_owner_type,

        "to_address": to_address,
        "to_owner": to_owner,
        "to_owner_type": to_owner_type,

        "direction": direction,

        "source": "WHALE_ALERT",
        "source_timestamp": timestamp_iso,

        "content_hash": content_hash,

        "created_at": utc_now(),
        "engine_version": "MARKET_WHALE_v0.1"
    }


# ================================================================
# DATABASE INSERT
# ================================================================

def insert_transaction(conn, data):

    exists = conn.execute(
        """
        SELECT 1
        FROM market_whale
        WHERE content_hash = ?
        LIMIT 1
        """,
        (data["content_hash"],)
    ).fetchone()

    if exists:
        return False

    conn.execute("""
        INSERT INTO market_whale (
            timestamp,
            symbol,
            blockchain,
            transaction_type,
            amount,
            amount_usd,
            tx_hash,
            from_address,
            from_owner,
            from_owner_type,
            to_address,
            to_owner,
            to_owner_type,
            direction,
            source,
            source_timestamp,
            content_hash,
            created_at,
            engine_version
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, (
        data["timestamp"],
        data["symbol"],
        data["blockchain"],
        data["transaction_type"],
        data["amount"],
        data["amount_usd"],
        data["tx_hash"],
        data["from_address"],
        data["from_owner"],
        data["from_owner_type"],
        data["to_address"],
        data["to_owner"],
        data["to_owner_type"],
        data["direction"],
        data["source"],
        data["source_timestamp"],
        data["content_hash"],
        data["created_at"],
        data["engine_version"],
    ))

    return True


# ================================================================
# DISPLAY
# ================================================================

def print_recent(conn):

    rows = conn.execute("""
        SELECT
            symbol,
            blockchain,
            timestamp,
            amount_usd,
            direction,
            from_owner,
            to_owner,
            transaction_type
        FROM market_whale
        ORDER BY id DESC
        LIMIT 20
    """).fetchall()

    print()
    print("=" * 150)
    print("RECENT WHALE ACTIVITY")
    print("=" * 150)

    if not rows:
        print("No whale records available.")
        return

    print(
        f"{'SYMBOL':<10}"
        f"{'CHAIN':<13}"
        f"{'TIMESTAMP':<28}"
        f"{'VALUE USD':>16}"
        f"{'DIRECTION':<23}"
        f"{'FROM':<18}"
        f"{'TO':<18}"
    )

    print("-" * 150)

    for row in rows:

        (
            symbol,
            blockchain,
            timestamp,
            amount_usd,
            direction,
            from_owner,
            to_owner,
            tx_type
        ) = row

        from_owner = from_owner or "unknown"
        to_owner = to_owner or "unknown"

        print(
            f"{str(symbol)[:9]:<10}"
            f"{str(blockchain)[:12]:<13}"
            f"{str(timestamp)[:27]:<28}"
            f"{amount_usd:>16,.0f}"
            f"{str(direction)[:22]:<23}"
            f"{str(from_owner)[:17]:<18}"
            f"{str(to_owner)[:17]:<18}"
        )


# ================================================================
# MAIN CYCLE
# ================================================================

def run_cycle(conn, cycle_number):

    print()
    print("=" * 80)
    print(f"WHale COLLECTION CYCLE #{cycle_number}")
    print(f"Time : {utc_now()}")
    print("=" * 80)

    try:

        result = fetch_whale_transactions()

        status = result["status"]

        if status == "NO_API_KEY":

            print()
            print("WHALE PROVIDER STATUS : NOT CONFIGURED")
            print("WHALE_ALERT_API_KEY   : NOT SET")
            print()
            print(
                "No data collected."
            )
            print(
                "Engine remains ACTIVE and database is preserved."
            )

            return True

        transactions = result["transactions"]

        print()
        print(
            f"Provider Status : {status}"
        )
        print(
            f"Transactions Returned : {len(transactions)}"
        )

        if "latency" in result:
            print(
                f"Provider Latency : {result['latency']} ms"
            )

        inserted = 0
        duplicates = 0
        errors = 0

        for tx in transactions:

            try:

                data = normalize_transaction(tx)

                if insert_transaction(conn, data):
                    inserted += 1
                else:
                    duplicates += 1

            except Exception as exc:
                errors += 1
                print(
                    f"Transaction normalization error: {exc}"
                )

        conn.commit()

        print()
        print("=" * 80)
        print("WHALE CYCLE SUMMARY")
        print("=" * 80)
        print(
            f"Transactions Returned : {len(transactions)}"
        )
        print(
            f"Inserted              : {inserted}"
        )
        print(
            f"Duplicates            : {duplicates}"
        )
        print(
            f"Errors                : {errors}"
        )
        print(
            f"Whale Records         : {count_records(conn)}"
        )
        print("=" * 80)

        print_recent(conn)

        return True

    except requests.HTTPError as exc:

        print()
        print("=" * 80)
        print("WHALE PROVIDER HTTP ERROR")
        print("=" * 80)
        print(str(exc))

        try:
            print()
            print("Provider Response:")
            print(exc.response.text[:2000])
        except Exception:
            pass

        return False

    except requests.RequestException as exc:

        print()
        print("=" * 80)
        print("WHALE PROVIDER CONNECTION ERROR")
        print("=" * 80)
        print(str(exc))

        return False

    except Exception as exc:

        print()
        print("=" * 80)
        print("WHALE ENGINE ERROR")
        print("=" * 80)
        print(
            f"{type(exc).__name__}: {exc}"
        )

        return False


# ================================================================
# ENTRY POINT
# ================================================================

def main():

    print("=" * 80)
    print("          ARUNDA MARKET WHALE ENGINE v0.1")
    print("=" * 80)
    print("Source          : WHALE ALERT / PROVIDER AGNOSTIC")
    print(f"Database        : {DB_PATH}")
    print("Mode            : WHALE DATA COLLECTION")
    print("Minimum Value   : $500,000")
    print("Lookback        : 10 minutes")
    print("Interval        : 60 seconds")
    print("Intelligence    : NOT USED")
    print("Ranking         : NOT USED")
    print("Opportunity     : NOT USED")
    print("Signal          : NOT USED")
    print("Prediction      : NOT USED")
    print("Risk            : NOT USED")
    print("Execution       : NOT USED")
    print("Writes          : market_whale")
    print("=" * 80)

    conn = None

    try:

        conn = connect_db()

        print()
        print("Database           : CONNECTED")

        print("Checking whale schema...")

        added = ensure_schema(conn)

        print(
            f"Schema Columns Added : {len(added)}"
        )

        if added:
            print(
                "Added Columns        : "
                + ", ".join(added)
            )

        existing = count_records(conn)

        print(
            f"Existing Whale Records : {existing}"
        )

        if API_KEY:
            print()
            print(
                "WHALE_ALERT API KEY : AVAILABLE"
            )
        else:
            print()
            print(
                "WHALE_ALERT API KEY : NOT CONFIGURED"
            )
            print(
                "Provider collection will remain inactive."
            )

        print()
        print("Whale collection ACTIVE.")
        print("Press Ctrl+C to stop.")

        cycle = 0
        successful = 0
        failed = 0

        while True:

            cycle += 1

            success = run_cycle(
                conn,
                cycle
            )

            if success:
                successful += 1
            else:
                failed += 1

            print()
            print("=" * 80)
            print("WHALE ENGINE STATUS")
            print("=" * 80)
            print(
                f"Total Cycles       : {cycle}"
            )
            print(
                f"Successful         : {successful}"
            )
            print(
                f"Failed             : {failed}"
            )
            print(
                f"Whale Records      : {count_records(conn)}"
            )
            print(
                "Interval           : 60 seconds"
            )
            print(
                "Intelligence       : NOT USED"
            )
            print(
                "Signal             : NOT USED"
            )
            print(
                "Risk               : NOT USED"
            )
            print(
                "Execution          : NOT USED"
            )
            print("=" * 80)

            print()
            print("Waiting 60 seconds...")

            time.sleep(60)

    except KeyboardInterrupt:

        print()
        print("=" * 80)
        print("       ARUNDA MARKET WHALE ENGINE STOPPED")
        print("=" * 80)

        if conn:
            print(
                f"Total Whale Records : {count_records(conn)}"
            )

        print("Database            : PRESERVED")
        print("Reason              : USER INTERRUPT")
        print("=" * 80)

    finally:

        if conn:
            conn.close()


if __name__ == "__main__":
    main()
