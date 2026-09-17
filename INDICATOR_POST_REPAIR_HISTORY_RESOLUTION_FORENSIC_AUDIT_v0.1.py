import sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arunda.db"

TARGET_SYMBOLS = ["BTC", "ETH", "SOL", "XRP"]
TARGET_IDS = {
    "BTC": 1706,
    "ETH": 1707,
    "SOL": 1708,
    "XRP": 1709,
}

print("=" * 100)
print("ARUNDA INDICATOR POST-REPAIR HISTORY RESOLUTION FORENSIC AUDIT v0.1")
print("=" * 100)
print("MODE                  : READ ONLY")
print("DATABASE WRITE        : NONE")
print("ENGINE WRITE          : NONE")
print("FORMULA WRITE         : NONE")
print("PRODUCTION RECALCULATION : NONE")
print("PURPOSE               : FORENSIC HISTORY RESOLUTION ONLY")
print("=" * 100)


def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def get_columns(conn, table_name):
    return [
        row[1]
        for row in conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    ]


def print_section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def parse_time(value):
    if value is None:
        return None

    text = str(value).strip()

    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt
    except Exception:
        return None


def normalize_time(value):
    dt = parse_time(value)

    if dt is None:
        return None

    return dt.astimezone(timezone.utc)


def history_rows(conn, symbol):
    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            cmc_id,
            symbol,
            name,
            price,
            source,
            source_timestamp,
            engine_version,
            created_at
        FROM market_history
        WHERE symbol = ?
        ORDER BY timestamp ASC, id ASC
        """,
        (symbol,),
    ).fetchall()

    return rows


def print_history_schema(conn):
    print_section("STEP 1 — HISTORY SCHEMA")

    columns = get_columns(conn, "market_history")

    print(f"HISTORY TABLE       : market_history")
    print(f"COLUMN COUNT        : {len(columns)}")
    print()
    print("COLUMNS")
    print("-" * 100)

    for column in columns:
        print(f"  {column}")


def resolve_latest_market_data(conn, symbol):
    row = conn.execute(
        """
        SELECT
            id,
            symbol,
            source_timestamp,
            engine_version,
            close,
            ema20,
            ema50,
            rsi14
        FROM market_data
        WHERE symbol = ?
        ORDER BY source_timestamp DESC, id DESC
        LIMIT 1
        """,
        (symbol,),
    ).fetchone()

    return row


def analyze_symbol(conn, symbol):
    print_section(f"SYMBOL : {symbol}")

    md = resolve_latest_market_data(conn, symbol)

    if md is None:
        print("MARKET_DATA STATUS : NOT FOUND")
        return {
            "symbol": symbol,
            "status": "UNRESOLVED",
        }

    md_id, md_symbol, source_time, engine_version, close, ema20, ema50, rsi14 = md

    print(f"MARKET_DATA ID      : {md_id}")
    print(f"SOURCE TIME         : {source_time}")
    print(f"ENGINE VERSION      : {engine_version}")
    print(f"CLOSE               : {close}")
    print(f"EMA20               : {ema20}")
    print(f"EMA50               : {ema50}")
    print(f"RSI14               : {rsi14}")

    rows = history_rows(conn, symbol)

    print()
    print("HISTORY INVENTORY")
    print("-" * 100)
    print(f"TOTAL HISTORY ROWS  : {len(rows)}")

    if not rows:
        print("HISTORY STATUS      : NO ROWS")
        return {
            "symbol": symbol,
            "status": "UNRESOLVED",
        }

    timestamps = [row[1] for row in rows]

    parsed_times = [
        normalize_time(value)
        for value in timestamps
        if normalize_time(value) is not None
    ]

    print(f"VALID TIMESTAMPS    : {len(parsed_times)}")

    if parsed_times:
        print(
            f"FIRST TIMESTAMP     : "
            f"{parsed_times[0].isoformat()}"
        )
        print(
            f"LAST TIMESTAMP      : "
            f"{parsed_times[-1].isoformat()}"
        )

    print()
    print("HISTORY IDENTITY")
    print("-" * 100)

    distinct_cmc = sorted(
        {
            row[2]
            for row in rows
            if row[2] is not None
        },
        key=lambda x: str(x),
    )

    distinct_symbols = sorted(
        {
            row[3]
            for row in rows
            if row[3] is not None
        }
    )

    distinct_names = sorted(
        {
            row[4]
            for row in rows
            if row[4] is not None
        }
    )

    print(f"DISTINCT CMC_ID    : {len(distinct_cmc)}")
    print(f"DISTINCT SYMBOL     : {len(distinct_symbols)}")
    print(f"DISTINCT NAME       : {len(distinct_names)}")

    print()
    print("TIMESTAMP DISTRIBUTION")
    print("-" * 100)

    timestamp_groups = conn.execute(
        """
        SELECT
            timestamp,
            COUNT(*) AS cnt,
            COUNT(DISTINCT cmc_id) AS distinct_cmc,
            COUNT(DISTINCT symbol) AS distinct_symbol
        FROM market_history
        WHERE symbol = ?
        GROUP BY timestamp
        ORDER BY timestamp ASC
        """,
        (symbol,),
    ).fetchall()

    print(f"SNAPSHOTS           : {len(timestamp_groups)}")

    if timestamp_groups:
        counts = [row[1] for row in timestamp_groups]

        print(f"MIN ROWS/SNAPSHOT   : {min(counts)}")
        print(f"MAX ROWS/SNAPSHOT   : {max(counts)}")

        print()
        print("FIRST 5 SNAPSHOTS")
        print("-" * 100)

        for row in timestamp_groups[:5]:
            print(
                f"TIMESTAMP={row[0]} | "
                f"ROWS={row[1]} | "
                f"DISTINCT_CMC={row[2]} | "
                f"DISTINCT_SYMBOL={row[3]}"
            )

        print()
        print("LAST 5 SNAPSHOTS")
        print("-" * 100)

        for row in timestamp_groups[-5:]:
            print(
                f"TIMESTAMP={row[0]} | "
                f"ROWS={row[1]} | "
                f"DISTINCT_CMC={row[2]} | "
                f"DISTINCT_SYMBOL={row[3]}"
            )

    print()
    print("MARKET_DATA ↔ HISTORY TIME RESOLUTION")
    print("-" * 100)

    latest_md_time = normalize_time(source_time)

    exact_rows = []
    if latest_md_time is not None:
        for row in rows:
            history_time = normalize_time(row[1])

            if history_time == latest_md_time:
                exact_rows.append(row)

    print(f"MARKET_DATA TIME    : {source_time}")
    print(f"EXACT HISTORY ROWS  : {len(exact_rows)}")

    if exact_rows:
        for row in exact_rows[:10]:
            print(
                f"  HISTORY ID={row[0]} | "
                f"TIMESTAMP={row[1]} | "
                f"CMC_ID={row[2]} | "
                f"SYMBOL={row[3]} | "
                f"PRICE={row[5]}"
            )
    else:
        print("  [NONE] Exact timestamp match not found")

    print()
    print("HISTORY PRICE VALIDITY")
    print("-" * 100)

    valid_price = 0
    invalid_price = 0

    for row in rows:
        price = row[5]

        try:
            value = float(price)
            if value > 0:
                valid_price += 1
            else:
                invalid_price += 1
        except Exception:
            invalid_price += 1

    print(f"VALID POSITIVE PRICE : {valid_price}")
    print(f"INVALID PRICE        : {invalid_price}")

    print()
    print("SOURCE / ENGINE DISTRIBUTION")
    print("-" * 100)

    source_rows = conn.execute(
        """
        SELECT
            COALESCE(source, '<NULL>') AS source_name,
            COALESCE(engine_version, '<NULL>') AS engine_name,
            COUNT(*) AS cnt
        FROM market_history
        WHERE symbol = ?
        GROUP BY source_name, engine_name
        ORDER BY cnt DESC
        """,
        (symbol,),
    ).fetchall()

    for row in source_rows:
        print(
            f"SOURCE={row[0]} | "
            f"ENGINE={row[1]} | "
            f"ROWS={row[2]}"
        )

    print()
    print("CMC_ID CONSISTENCY")
    print("-" * 100)

    cmc_rows = conn.execute(
        """
        SELECT
            cmc_id,
            COUNT(*) AS cnt,
            MIN(timestamp) AS first_timestamp,
            MAX(timestamp) AS last_timestamp
        FROM market_history
        WHERE symbol = ?
        GROUP BY cmc_id
        ORDER BY cnt DESC
        """,
        (symbol,),
    ).fetchall()

    for row in cmc_rows[:20]:
        print(
            f"CMC_ID={row[0]} | "
            f"ROWS={row[1]} | "
            f"FIRST={row[2]} | "
            f"LAST={row[3]}"
        )

    print()
    print("POST-REPAIR LOOKBACK WINDOWS")
    print("-" * 100)

    target_timestamp = latest_md_time

    if target_timestamp is not None:
        windows = [64, 122, 706]

        for window in windows:
            eligible = []

            for row in rows:
                dt = normalize_time(row[1])

                if dt is None:
                    continue

                if dt <= target_timestamp:
                    eligible.append((dt, row))

            selected = eligible[-window:]

            print(
                f"LOOKBACK {window:>3} : "
                f"{len(selected):>3} rows"
            )

            if selected:
                print(
                    f"  FIRST={selected[0][0].isoformat()} | "
                    f"LAST={selected[-1][0].isoformat()}"
                )

    print()
    print("HISTORY RESOLUTION VERDICT")
    print("-" * 100)

    status = "RESOLVED"

    reasons = []

    if len(rows) == 0:
        status = "UNRESOLVED"
        reasons.append("NO_HISTORY")

    if len(parsed_times) != len(rows):
        status = "PARTIAL"
        reasons.append("INVALID_TIMESTAMPS")

    if invalid_price > 0:
        status = "PARTIAL"
        reasons.append("INVALID_PRICES")

    if len(exact_rows) == 0:
        status = "PARTIAL"
        reasons.append("NO_EXACT_TARGET_TIMESTAMP")

    if not reasons:
        reasons.append("HISTORY_RESOLUTION_COMPLETE")

    print(f"STATUS              : {status}")

    for reason in reasons:
        print(f"REASON              : {reason}")

    return {
        "symbol": symbol,
        "status": status,
        "history_count": len(rows),
        "valid_timestamps": len(parsed_times),
        "exact_rows": len(exact_rows),
    }


def main():
    if not DB_PATH.exists():
        print()
        print("DATABASE FOUND       : False")
        print("STATUS               : ABORTED")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        print_section("STEP 1 — DATABASE RESOLUTION")

        print(f"DATABASE PATH        : {DB_PATH}")
        print(f"DATABASE FOUND       : {DB_PATH.exists()}")

        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]

        print(f"TABLE COUNT          : {len(tables)}")
        print(f"MARKET_DATA          : {'FOUND' if 'market_data' in tables else 'MISSING'}")
        print(f"MARKET_HISTORY       : {'FOUND' if 'market_history' in tables else 'MISSING'}")

        if "market_data" not in tables or "market_history" not in tables:
            print("STATUS               : ABORTED")
            return

        print_history_schema(conn)

        print_section("STEP 2 — SYMBOL HISTORY RESOLUTION")

        results = []

        for symbol in TARGET_SYMBOLS:
            result = analyze_symbol(conn, symbol)
            results.append(result)

        print_section("FINAL HISTORY RESOLUTION FORENSIC SUMMARY")

        print(f"TARGETS CHECKED      : {len(results)}")
        print(
            f"RESOLVED             : "
            f"{sum(1 for r in results if r.get('status') == 'RESOLVED')}"
        )
        print(
            f"PARTIAL              : "
            f"{sum(1 for r in results if r.get('status') == 'PARTIAL')}"
        )
        print(
            f"UNRESOLVED           : "
            f"{sum(1 for r in results if r.get('status') == 'UNRESOLVED')}"
        )

        print()
        print("TARGET MATRIX")
        print("-" * 100)

        for result in results:
            print(
                f"  [{result.get('status', 'UNKNOWN'):>10}] : "
                f"{result['symbol']}"
            )

        unresolved = [
            r for r in results
            if r.get("status") != "RESOLVED"
        ]

        print()
        print("=" * 100)
        print("FORENSIC CONCLUSION")
        print("=" * 100)

        if unresolved:
            print("STATUS                  : HISTORY_RESOLUTION_INCOMPLETE")
            print(
                "REASON                  : "
                "ONE OR MORE HISTORY RESOLUTION PATHS REQUIRE FURTHER FORENSICS"
            )
            print(
                "NEXT FRONTIER           : "
                "INSPECT ONLY THE UNRESOLVED HISTORY COMPONENTS"
            )
        else:
            print("STATUS                  : HISTORY_RESOLUTION_RESOLVED")
            print(
                "REASON                  : "
                "ALL TARGET HISTORY PATHS ARE RESOLVED"
            )
            print(
                "NEXT FRONTIER           : "
                "DETERMINE EXACT PRODUCTION LOOKBACK / INPUT PATH"
            )

        print()
        print("DATABASE WRITE OPERATIONS : NONE")
        print("ENGINE MODIFICATIONS      : NONE")
        print("FORMULA WRITE             : NONE")
        print("PRODUCTION RECALCULATION  : NONE")
        print("AUDIT COMPLETE")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
