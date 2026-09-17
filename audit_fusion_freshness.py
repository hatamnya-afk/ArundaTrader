import sqlite3
from datetime import datetime, timezone

DB = "arunda.db"

ASSETS = ["BTC", "ETH", "SOL", "XRP"]

# Freshness thresholds
MARKET_MAX_AGE_MIN = 15
POSITIONING_MAX_AGE_MIN = 15
NEWS_MAX_AGE_MIN = 30

print("=" * 90)
print("ARUNDA FUSION INPUT FRESHNESS / HEALTH AUDIT")
print("=" * 90)
print("MODE       : READ ONLY")
print("DATABASE   : arunda.db")
print("WRITES     : NONE")
print("INSERT     : NONE")
print("UPDATE     : NONE")
print("DELETE     : NONE")
print("ALTER      : NONE")
print("=" * 90)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row


def table_exists(table):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table,),
    ).fetchone()
    return row is not None


def columns(table):
    return [
        r["name"]
        for r in conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    ]


def parse_ts(value):
    if value is None:
        return None

    text = str(value).strip()

    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


NOW = datetime.now(timezone.utc)

print()
print(f"AUDIT TIME UTC : {NOW.isoformat()}")
print()


# =====================================================================
# SCHEMA
# =====================================================================

print("=" * 90)
print("1. SCHEMA HEALTH")
print("=" * 90)

TABLES = [
    "market_data",
    "positioning_data",
    "news_signals",
]

for table in TABLES:

    exists = table_exists(table)

    print()
    print(f"[{table}]")

    if not exists:
        print("STATUS : MISSING TABLE")
        continue

    cols = columns(table)

    print("STATUS : EXISTS")
    print("COLUMNS:", ", ".join(cols))


# =====================================================================
# GENERIC HELPERS
# =====================================================================

def find_column(table, candidates):

    if not table_exists(table):
        return None

    cols = columns(table)

    lower_map = {
        c.lower(): c
        for c in cols
    }

    for candidate in candidates:

        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]

    return None


def latest_rows(table, asset_column):

    if not table_exists(table):
        return []

    if asset_column is None:
        return []

    timestamp_col = find_column(
        table,
        [
            "timestamp",
            "time",
            "datetime",
            "created_at",
            "updated_at",
        ],
    )

    if timestamp_col is None:
        return []

    score_col = find_column(
        table,
        [
            "technical_score",
            "positioning_score",
            "news_score",
            "score",
        ],
    )

    select_score = (
        f'"{score_col}" AS score'
        if score_col
        else
        "NULL AS score"
    )

    query = f"""
        SELECT
            "{asset_column}" AS asset,
            "{timestamp_col}" AS timestamp,
            {select_score}
        FROM "{table}"
        WHERE "{asset_column}" IN ({",".join("?" for _ in ASSETS)})
        ORDER BY rowid DESC
    """

    return conn.execute(
        query,
        ASSETS,
    ).fetchall()


def analyze_rows(
    table,
    asset_column,
    max_age_minutes,
):

    rows = latest_rows(
        table,
        asset_column,
    )

    latest = {}

    for row in rows:

        asset = row["asset"]

        if asset not in latest:
            latest[asset] = row

    result = {}

    for asset in ASSETS:

        row = latest.get(asset)

        if row is None:

            result[asset] = {
                "timestamp": None,
                "age": None,
                "score": None,
                "status": "MISSING",
            }

            continue

        timestamp = row["timestamp"]
        score = row["score"]

        dt = parse_ts(timestamp)

        if dt is None:

            result[asset] = {
                "timestamp": timestamp,
                "age": None,
                "score": score,
                "status": "INVALID_TIMESTAMP",
            }

            continue

        age_minutes = (
            NOW - dt
        ).total_seconds() / 60.0

        if score is None:

            status = "NO_SCORE"

        elif age_minutes > max_age_minutes:

            status = "STALE"

        else:

            status = "FRESH"

        result[asset] = {
            "timestamp": timestamp,
            "age": age_minutes,
            "score": score,
            "status": status,
        }

    return result


# =====================================================================
# MARKET
# =====================================================================

print()
print("=" * 90)
print("2. MARKET INPUT")
print("=" * 90)

market_asset_col = find_column(
    "market_data",
    [
        "symbol",
        "asset",
        "market",
    ],
)

print(f"ASSET COLUMN : {market_asset_col}")
print(f"MAX AGE      : {MARKET_MAX_AGE_MIN} minutes")

market_result = analyze_rows(
    "market_data",
    market_asset_col,
    MARKET_MAX_AGE_MIN,
)

for asset in ASSETS:

    x = market_result[asset]

    age = (
        "N/A"
        if x["age"] is None
        else f"{x['age']:.1f} min"
    )

    print(
        f"{asset:<6} | "
        f"STATUS={x['status']:<18} | "
        f"SCORE={str(x['score']):<12} | "
        f"AGE={age:<12} | "
        f"TS={x['timestamp']}"
    )


# =====================================================================
# POSITIONING
# =====================================================================

print()
print("=" * 90)
print("3. POSITIONING INPUT")
print("=" * 90)

positioning_asset_col = find_column(
    "positioning_data",
    [
        "market",
        "asset",
        "symbol",
    ],
)

print(f"ASSET COLUMN : {positioning_asset_col}")
print(f"MAX AGE      : {POSITIONING_MAX_AGE_MIN} minutes")

positioning_result = analyze_rows(
    "positioning_data",
    positioning_asset_col,
    POSITIONING_MAX_AGE_MIN,
)

for asset in ASSETS:

    x = positioning_result[asset]

    age = (
        "N/A"
        if x["age"] is None
        else f"{x['age']:.1f} min"
    )

    print(
        f"{asset:<6} | "
        f"STATUS={x['status']:<18} | "
        f"SCORE={str(x['score']):<12} | "
        f"AGE={age:<12} | "
        f"TS={x['timestamp']}"
    )


# =====================================================================
# NEWS
# =====================================================================

print()
print("=" * 90)
print("4. NEWS INPUT")
print("=" * 90)

news_asset_col = find_column(
    "news_signals",
    [
        "asset",
        "symbol",
        "market",
    ],
)

print(f"ASSET COLUMN : {news_asset_col}")
print(f"MAX AGE      : {NEWS_MAX_AGE_MIN} minutes")

news_result = analyze_rows(
    "news_signals",
    news_asset_col,
    NEWS_MAX_AGE_MIN,
)

for asset in ASSETS:

    x = news_result[asset]

    age = (
        "N/A"
        if x["age"] is None
        else f"{x['age']:.1f} min"
    )

    print(
        f"{asset:<6} | "
        f"STATUS={x['status']:<18} | "
        f"SCORE={str(x['score']):<12} | "
        f"AGE={age:<12} | "
        f"TS={x['timestamp']}"
    )


# =====================================================================
# ARM SUMMARY
# =====================================================================

def arm_summary(result):

    fresh = sum(
        x["status"] == "FRESH"
        for x in result.values()
    )

    stale = sum(
        x["status"] == "STALE"
        for x in result.values()
    )

    missing = sum(
        x["status"] == "MISSING"
        for x in result.values()
    )

    no_score = sum(
        x["status"] == "NO_SCORE"
        for x in result.values()
    )

    invalid = sum(
        x["status"] == "INVALID_TIMESTAMP"
        for x in result.values()
    )

    return (
        fresh,
        stale,
        missing,
        no_score,
        invalid,
    )


print()
print("=" * 90)
print("5. ARM HEALTH SUMMARY")
print("=" * 90)

arms = [
    ("MARKET", market_result),
    ("POSITIONING", positioning_result),
    ("NEWS", news_result),
]

for name, result in arms:

    fresh, stale, missing, no_score, invalid = (
        arm_summary(result)
    )

    if fresh == len(ASSETS):
        health = "HEALTHY"

    elif fresh > 0:
        health = "PARTIAL"

    else:
        health = "UNHEALTHY"

    print(
        f"{name:<14} | "
        f"HEALTH={health:<10} | "
        f"FRESH={fresh} | "
        f"STALE={stale} | "
        f"MISSING={missing} | "
        f"NO_SCORE={no_score} | "
        f"INVALID_TS={invalid}"
    )


# =====================================================================
# FUSION READINESS
# =====================================================================

print()
print("=" * 90)
print("6. FUSION INPUT READINESS")
print("=" * 90)

for asset in ASSETS:

    m = market_result[asset]
    p = positioning_result[asset]
    n = news_result[asset]

    available = []

    if m["status"] == "FRESH":
        available.append("MARKET")

    if p["status"] == "FRESH":
        available.append("POSITIONING")

    if n["status"] == "FRESH":
        available.append("NEWS")

    if len(available) == 3:
        readiness = "FULL"

    elif len(available) == 2:
        readiness = "PARTIAL-2"

    elif len(available) == 1:
        readiness = "PARTIAL-1"

    else:
        readiness = "UNAVAILABLE"

    print(
        f"{asset:<6} | "
        f"READINESS={readiness:<12} | "
        f"ACTIVE ARMS={','.join(available) if available else 'NONE'}"
    )


# =====================================================================
# RECENT ROW COUNTS
# =====================================================================

print()
print("=" * 90)
print("7. RECENT DATA VOLUME")
print("=" * 90)

for table in TABLES:

    if not table_exists(table):
        print(f"{table:<20} | TABLE MISSING")
        continue

    timestamp_col = find_column(
        table,
        [
            "timestamp",
            "time",
            "datetime",
            "created_at",
            "updated_at",
        ],
    )

    if timestamp_col is None:
        print(f"{table:<20} | NO TIMESTAMP COLUMN")
        continue

    rows = conn.execute(
        f"""
        SELECT COUNT(*) AS c
        FROM "{table}"
        WHERE rowid IN (
            SELECT rowid
            FROM "{table}"
            ORDER BY rowid DESC
            LIMIT 100
        )
        """
    ).fetchone()

    print(
        f"{table:<20} | "
        f"LAST 100 ROWS AVAILABLE={rows['c']}"
    )


# =====================================================================
# FINAL VERDICT
# =====================================================================

print()
print("=" * 90)
print("8. FINAL VERDICT")
print("=" * 90)

market_fresh = sum(
    x["status"] == "FRESH"
    for x in market_result.values()
)

positioning_fresh = sum(
    x["status"] == "FRESH"
    for x in positioning_result.values()
)

news_fresh = sum(
    x["status"] == "FRESH"
    for x in news_result.values()
)

print(
    f"MARKET       FRESH ASSETS     : "
    f"{market_fresh}/{len(ASSETS)}"
)

print(
    f"POSITIONING  FRESH ASSETS     : "
    f"{positioning_fresh}/{len(ASSETS)}"
)

print(
    f"NEWS         FRESH ASSETS     : "
    f"{news_fresh}/{len(ASSETS)}"
)

if (
    market_fresh == len(ASSETS)
    and positioning_fresh == len(ASSETS)
    and news_fresh == len(ASSETS)
):

    print()
    print("OVERALL STATUS : FUSION INPUTS HEALTHY")

else:

    print()
    print("OVERALL STATUS : FUSION INPUTS NOT FULLY HEALTHY")

print()
print("IMPORTANT : This audit is READ ONLY.")
print("IMPORTANT : No database modifications were performed.")
print("=" * 90)

conn.close()
