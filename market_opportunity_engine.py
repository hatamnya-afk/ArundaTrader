import sqlite3
import math
from datetime import datetime, timezone

DB_PATH = "arunda.db"
ENGINE_VERSION = "MARKET_OPPORTUNITY_v0.2.1"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def safe_float(value, default=None):
    try:
        if value is None:
            return default
        value = float(value)
        if not math.isfinite(value):
            return default
        return value
    except (TypeError, ValueError):
        return default


def clamp(value, low=0.0, high=1.0):
    value = safe_float(value, 0.0)
    return max(low, min(high, value))


def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def get_columns(conn, table_name):
    return [
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    ]


def add_column(conn, table_name, column, column_type):
    if column not in get_columns(conn, table_name):
        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column} {column_type}"
        )
        return True
    return False


def normalize_score(value):
    value = safe_float(value)

    if value is None:
        return None

    if -1.0 <= value <= 1.0:
        return clamp((value + 1.0) / 2.0)

    return clamp(value / 100.0)


def ensure_schema(conn):
    if not table_exists(conn, "market_opportunity"):
        conn.execute(
            """
            CREATE TABLE market_opportunity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                opportunity_status TEXT,
                opportunity_score REAL,
                opportunity_confidence REAL,
                data_completeness REAL,
                technical_available INTEGER,
                news_available INTEGER,
                whale_available INTEGER,
                microstructure_available INTEGER,
                state_confidence REAL,
                opportunity_version TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
            """
        )
        return "CREATED", []

    columns = [
        ("name", "TEXT"),
        ("opportunity_status", "TEXT"),
        ("opportunity_score", "REAL"),
        ("opportunity_confidence", "REAL"),
        ("data_completeness", "REAL"),
        ("technical_available", "INTEGER"),
        ("news_available", "INTEGER"),
        ("whale_available", "INTEGER"),
        ("microstructure_available", "INTEGER"),
        ("state_confidence", "REAL"),
        ("opportunity_version", "TEXT"),
        ("created_at", "TEXT"),
        ("updated_at", "TEXT"),
    ]

    added = []

    for column, column_type in columns:
        if add_column(conn, "market_opportunity", column, column_type):
            added.append(column)

    return "EXISTING", added


def calculate_opportunity(row):
    technical = normalize_score(row.get("technical_score"))
    news = normalize_score(row.get("news_score"))
    whale = normalize_score(row.get("whale_score"))
    micro = normalize_score(row.get("microstructure_score"))
    state = normalize_score(row.get("state_score"))

    technical_available = int(bool(row.get("technical_available")))
    news_available = int(bool(row.get("news_available")))
    whale_available = int(bool(row.get("whale_available")))
    micro_available = int(bool(row.get("microstructure_available")))

    components = []

    if technical is not None and technical_available:
        components.append(technical)

    if news is not None and news_available:
        components.append(news)

    if whale is not None and whale_available:
        components.append(whale)

    if micro is not None and micro_available:
        components.append(micro)

    if state is not None:
        components.append(state)

    state_confidence = clamp(
        safe_float(row.get("state_confidence"), 0.0)
    )

    completeness = clamp(
        safe_float(row.get("data_completeness"), 0.0)
    )

    if not components:
        return {
            "status": "INSUFFICIENT_DATA",
            "score": 0.0,
            "confidence": 0.0,
        }

    score = clamp(sum(components) / len(components))

    coverage = len(components) / 5.0

    confidence = clamp(
        coverage * 0.55
        + state_confidence * 0.30
        + completeness * 0.15
    )

    if coverage < 0.40:
        status = "INSUFFICIENT_DATA"
    elif score >= 0.75 and confidence >= 0.60:
        status = "CANDIDATE"
    elif score >= 0.55 and confidence >= 0.40:
        status = "WATCH"
    else:
        status = "NEUTRAL"

    return {
        "status": status,
        "score": score,
        "confidence": confidence,
    }


def main():
    print("=" * 82)
    print("             ARUNDA MARKET OPPORTUNITY ENGINE v0.2.1")
    print("=" * 82)
    print("Source          : MARKET STATE")
    print("Database        : arunda.db")
    print("Mode            : OPPORTUNITY CANDIDATE DETECTION")
    print("Analysis        : UNIFIED STATE INTERPRETATION")
    print("Ranking         : NOT USED")
    print("Signal          : NOT USED")
    print("Prediction      : NOT USED")
    print("Risk            : NOT USED")
    print("Execution       : NOT USED")
    print("Writes          : market_opportunity")
    print("=" * 82)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        print("\nChecking database...")

        if not table_exists(conn, "market_state"):
            raise RuntimeError(
                "market_state table does not exist"
            )

        state_columns = get_columns(conn, "market_state")

        print("Market State Table : market_state")
        print(f"State Columns      : {len(state_columns)}")

        print("\nChecking opportunity schema...")

        schema_status, added = ensure_schema(conn)

        print(f"Opportunity Table   : {schema_status}")
        print(f"Schema Columns Added: {len(added)}")

        if added:
            print("Added Columns       : " + ", ".join(added))

        existing = conn.execute(
            "SELECT COUNT(*) FROM market_opportunity"
        ).fetchone()[0]

        print(
            f"Existing Opportunity Records : {existing}"
        )

        print("\nReading market state...")

        rows = conn.execute(
            """
            SELECT *
            FROM market_state
            ORDER BY timestamp, symbol
            """
        ).fetchall()

        print(f"Market State Rows : {len(rows)}")

        if not rows:
            print("\nNo market state records found.")
            return

        print("\nCalculating opportunity candidates...")
        print("\nWriting opportunity layer...")

        inserted = 0
        updated = 0
        candidates = 0
        watch = 0
        insufficient = 0
        neutral = 0

        for sqlite_row in rows:
            row = dict(sqlite_row)

            symbol = row.get("symbol")
            name = row.get("name")
            timestamp = row.get("timestamp") or now_utc()

            result = calculate_opportunity(row)

            status = result["status"]
            score = result["score"]
            confidence = result["confidence"]

            completeness = clamp(
                safe_float(
                    row.get("data_completeness"),
                    0.0
                )
            )

            technical_available = int(
                bool(row.get("technical_available"))
            )

            news_available = int(
                bool(row.get("news_available"))
            )

            whale_available = int(
                bool(row.get("whale_available"))
            )

            microstructure_available = int(
                bool(row.get("microstructure_available"))
            )

            state_confidence = clamp(
                safe_float(
                    row.get("state_confidence"),
                    0.0
                )
            )

            timestamp_now = now_utc()

            existing_row = conn.execute(
                """
                SELECT id
                FROM market_opportunity
                WHERE symbol = ?
                  AND timestamp = ?
                LIMIT 1
                """,
                (symbol, timestamp),
            ).fetchone()

            if existing_row:

                conn.execute(
                    """
                    UPDATE market_opportunity
                    SET
                        name = ?,
                        opportunity_status = ?,
                        opportunity_score = ?,
                        opportunity_confidence = ?,
                        data_completeness = ?,
                        technical_available = ?,
                        news_available = ?,
                        whale_available = ?,
                        microstructure_available = ?,
                        state_confidence = ?,
                        opportunity_version = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        status,
                        score,
                        confidence,
                        completeness,
                        technical_available,
                        news_available,
                        whale_available,
                        microstructure_available,
                        state_confidence,
                        ENGINE_VERSION,
                        timestamp_now,
                        existing_row["id"],
                    ),
                )

                updated += 1

            else:

                conn.execute(
                    """
                    INSERT INTO market_opportunity (
                        timestamp,
                        symbol,
                        name,
                        opportunity_status,
                        opportunity_score,
                        opportunity_confidence,
                        data_completeness,
                        technical_available,
                        news_available,
                        whale_available,
                        microstructure_available,
                        state_confidence,
                        opportunity_version,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?
                    )
                    """,
                    (
                        timestamp,
                        symbol,
                        name,
                        status,
                        score,
                        confidence,
                        completeness,
                        technical_available,
                        news_available,
                        whale_available,
                        microstructure_available,
                        state_confidence,
                        ENGINE_VERSION,
                        timestamp_now,
                        timestamp_now,
                    ),
                )

                inserted += 1

            if status == "CANDIDATE":
                candidates += 1
            elif status == "WATCH":
                watch += 1
            elif status == "INSUFFICIENT_DATA":
                insufficient += 1
            else:
                neutral += 1

        conn.commit()

        total_records = conn.execute(
            "SELECT COUNT(*) FROM market_opportunity"
        ).fetchone()[0]

        assets = conn.execute(
            """
            SELECT COUNT(DISTINCT symbol)
            FROM market_opportunity
            WHERE symbol IS NOT NULL
            """
        ).fetchone()[0]

        print("\n" + "=" * 82)
        print("             MARKET OPPORTUNITY ENGINE SUMMARY")
        print("=" * 82)
        print(f"Market State Rows      : {len(rows)}")
        print(f"Features Generated     : {len(rows)}")
        print(f"Inserted               : {inserted}")
        print(f"Updated                : {updated}")
        print(f"Opportunity Records    : {total_records}")
        print(f"Assets Evaluated       : {assets}")
        print(f"Candidates             : {candidates}")
        print(f"Watch                  : {watch}")
        print(f"Insufficient Data      : {insufficient}")
        print(f"Neutral                : {neutral}")
        print("=" * 82)

        recent = conn.execute(
            """
            SELECT
                symbol,
                opportunity_status,
                opportunity_score,
                opportunity_confidence,
                timestamp
            FROM market_opportunity
            ORDER BY
                CASE opportunity_status
                    WHEN 'CANDIDATE' THEN 1
                    WHEN 'WATCH' THEN 2
                    WHEN 'INSUFFICIENT_DATA' THEN 3
                    ELSE 4
                END,
                opportunity_score DESC,
                symbol ASC
            LIMIT 30
            """
        ).fetchall()

        print("\nRECENT OPPORTUNITY STATE")
        print("-" * 110)

        print(
            f"{'SYMBOL':<12}"
            f"{'STATUS':<22}"
            f"{'SCORE':<10}"
            f"{'CONF':<10}"
            f"TIMESTAMP"
        )

        print("-" * 110)

        for item in recent:
            print(
                f"{str(item['symbol']):<12}"
                f"{str(item['opportunity_status']):<22}"
                f"{safe_float(item['opportunity_score'], 0.0):<10.3f}"
                f"{safe_float(item['opportunity_confidence'], 0.0):<10.3f}"
                f"{item['timestamp']}"
            )

        print("\n" + "=" * 82)
        print(
            "       ARUNDA MARKET OPPORTUNITY ENGINE v0.2.1 COMPLETE"
        )
        print("=" * 82)
        print("OPPORTUNITY STATUS : SUCCESS")
        print("Candidate Layer     : ACTIVE")
        print("Ranking             : NOT USED")
        print("Signal              : NOT USED")
        print("Prediction          : NOT USED")
        print("Risk                : NOT USED")
        print("Execution           : NOT USED")
        print("=" * 82)

    except Exception as exc:
        conn.rollback()

        print("\n" + "=" * 82)
        print("             MARKET OPPORTUNITY ENGINE ERROR")
        print("=" * 82)
        print(f"{type(exc).__name__}: {exc}")
        print("=" * 82)

        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()